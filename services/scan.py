"""
Scan pipeline: a leaf photo in, a disease result or an honest refusal out.

Why this is more than "run the model". The disease model is a small CNN trained on
PlantVillage lab photos (one leaf, plain background). Measured on real-world photos:

  * 69 PlantDoc photos of the 9 crops it can diagnose: right disease 3%, right crop 20%
    (random guessing inside the right crop would score 27%). Preprocessing does not
    change this.
  * Its confidence is useless: it says ~100% for tomato fruit, other crops and animals,
    so no confidence threshold can reject them (83% of such photos still got a
    diagnosis at a 0.5 threshold).

So the model's answer is only trusted after a general vision model (services/leaf_check.py)
has looked at the photo and the answers agree:

  1. Refuse photos with no usable leaf (blank, fruit, far away, blurry, not a plant).
  2. Refuse crops the model does not cover, and crops it cannot tell apart from healthy
     and sick (blueberry, raspberry, soybean, orange, squash have a single class).
  3. The crop in the photo must match the crop the model believes.
  4. "Healthy" is refused if the leaf shows clear symptoms, and a disease is refused if
     the leaf shows none.
  5. The model must be reasonably sure of its answer inside that crop.

Anything that survives is shown as a hint with a reliability warning, never as a diagnosis.
decide() is a pure function of the model's probabilities and the photo check, so every
rule can be tested without a model or a network.
"""
import logging
import os
from concurrent.futures import ThreadPoolExecutor

import numpy as np
from PIL import Image, ImageOps

from services import leaf_check
from services.disease import (
    CROP_CLASSES,
    CROP_KEYS,
    CROP_OF_CLASS,
    DIAGNOSABLE_CROPS,
    MIN_PREDICTION_CONFIDENCE,
    PLANT_DISEASE_CLASS_NAMES,
    crop_name,
    get_plant_disease_model,
    get_target_size,
    lookup_disease_info,
)

logger = logging.getLogger(__name__)

# The model's probability mass on the crop seen in the photo must be at least this.
CROP_AGREEMENT_MIN = float(os.environ.get("CROP_AGREEMENT_MIN", "0.5"))
# Without a photo check (LEAF_CHECK=optional or off) the model alone must be this sure.
UNVERIFIED_MIN_CONFIDENCE = float(os.environ.get("UNVERIFIED_MIN_CONFIDENCE", "0.9"))

MIN_PHOTO_SIDE_PIXELS = 64
BLANK_PHOTO_STD = 6.0  # luminance spread (0-255) below which a photo is treated as blank
MODEL_PRESHRINK_SIDE = 256  # PlantVillage photos are 256 px; larger photos are shrunk to this first

_executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="photo-check")

RELIABILITY_NOTE = (
    "Treat this as a hint, not a diagnosis. On photos taken outside a lab this scan often "
    "names the wrong disease. Show the leaf to your agriculture officer before spraying or treating."
)

# --- Refusals ------------------------------------------------------------------
# reason -> (kind, headline, message, advice). kind drives the screen: retake the photo,
# crop not covered, not sure, or try again later.

_RETAKE_ADVICE = "Photograph one leaf in daylight, close enough to fill the frame."
_OFFICER_ADVICE = "Show the leaf to your local agriculture officer or Krishi Vigyan Kendra."


def _refusal_text(reason: str, crop: str = None, plant_name: str = "") -> tuple:
    covered = ", ".join(crop_name(c) for c in sorted(DIAGNOSABLE_CROPS))
    if reason == "photo_unusable":
        return ("retake", "This photo can't be read", "It is too small or has almost no detail.",
                "Take a new photo of one leaf in daylight, close enough to fill the frame.")
    if reason == "not_a_leaf":
        return ("retake", "This doesn't look like a leaf", "The photo seems to show something else.", _RETAKE_ADVICE)
    if reason == "no_leaf":
        return ("retake", "No leaf in this photo", "It shows fruit, a flower or a stem, not a leaf.",
                "Photograph one leaf, ideally one with spots or colour changes.")
    if reason == "too_far":
        return ("retake", "Move closer to the leaf", "The photo shows the whole plant or field.",
                "Hold the camera about 20 cm from one leaf so it fills the frame.")
    if reason == "poor_photo":
        return ("retake", "The photo is too blurry or dark", "The scan can't see enough detail.",
                "Take it again in daylight and hold the camera steady.")
    if reason == "unsupported_crop":
        what = f"a {plant_name} leaf" if plant_name else "a crop the scan doesn't know"
        title = f"{plant_name.capitalize()} isn't covered yet" if plant_name else "This crop isn't covered yet"
        return ("unsupported", title, f"This looks like {what}. The scan only checks {covered}.", _OFFICER_ADVICE)
    if reason == "not_diagnosable":
        only = PLANT_DISEASE_CLASS_NAMES[CROP_CLASSES[crop][0]]
        seen = (f"only healthy {crop_name(crop)} leaves" if "healthy" in only.lower()
                else f"only {crop_name(crop)} leaves with {lookup_disease_info(only)['name'].lower()}")
        return ("unsupported", f"Can't check {crop_name(crop)} yet",
                f"The scan has only seen {seen}, so it can't tell healthy leaves from sick ones.", _OFFICER_ADVICE)
    if reason == "crop_mismatch":
        return ("unsure", "Not sure about this leaf",
                f"The photo looks like a {crop_name(crop)} leaf, but the scan's answer doesn't fit {crop_name(crop)}, so it would probably be wrong.",
                "Take a clear close-up of the affected part of the leaf, or " + _OFFICER_ADVICE[0].lower() + _OFFICER_ADVICE[1:])
    if reason == "crop_unclear":
        return ("unsure", "Can't tell which crop this is", "The leaf has no clear features for the scan to go on.",
                "Photograph one whole leaf, with its stem if you can, in daylight.")
    if reason == "symptoms_vs_healthy":
        return ("unsure", "Not sure about this leaf",
                "The scan found no disease, but the leaf has marks that look like damage.",
                "Don't rely on a healthy result for this leaf. " + _OFFICER_ADVICE)
    if reason == "no_symptoms_vs_disease":
        return ("unsure", "Not sure about this leaf",
                "The scan suggests a disease, but the leaf shows no clear marks.",
                "Take another photo of the part of the leaf that looks affected.")
    if reason == "low_confidence":
        return ("unsure", "Not sure about this leaf",
                "The scan couldn't match this leaf to a known problem with enough certainty.",
                "Take a clear close-up in daylight, or " + _OFFICER_ADVICE[0].lower() + _OFFICER_ADVICE[1:])
    if reason == "check_unavailable":
        return ("unavailable", "Can't check this photo right now",
                "The photo check is not available, so the scan won't give a result.",
                "Try again later. You can still show the leaf to your local agriculture officer.")
    raise ValueError(f"unknown refusal reason: {reason}")


def refuse(reason: str, crop: str = None, plant_name: str = "", alternatives: list = None) -> dict:
    kind, headline, message, advice = _refusal_text(reason, crop, plant_name)
    return {
        "status": "rejected",
        "reason": reason,
        "kind": kind,
        "headline": headline,
        "message": message,
        "advice": advice,
        "label": "Uncertain",
        "is_plant": reason not in ("not_a_leaf", "photo_unusable"),
        "confidence": None,
        "crop": crop,
        "plant_name": plant_name,
        "alternatives": alternatives or [],
        # fields that older clients read
        "disease": headline,
        "description": message,
        "cure": "N/A",
        "prevention": advice,
    }


# --- Photo preparation -----------------------------------------------------------

def prepare_photo(image: Image.Image) -> Image.Image:
    """Apply the phone's rotation (EXIF) and convert to RGB."""
    return ImageOps.exif_transpose(image).convert("RGB")


def photo_problem(image: Image.Image):
    """'photo_unusable' if the photo is too small or blank to be worth analysing."""
    if min(image.size) < MIN_PHOTO_SIDE_PIXELS:
        return "photo_unusable"
    spread = float(np.asarray(image.convert("L").resize((64, 64)), dtype=np.float32).std())
    return "photo_unusable" if spread < BLANK_PHOTO_STD else None


def preprocess(image: Image.Image) -> np.ndarray:
    """
    The model's input, built the way its training images were: nearest-neighbour resize to the
    model's size, scaled to 0-1. (On 250 PlantVillage photos this scores 90%, against 83% for
    the bicubic resize used before; raw 0-255 or -1..1 scaling collapse to under 30%.)
    Large photos are first shrunk with smoothing, because nearest-neighbour on a 4000 px photo
    would skip almost every pixel.
    """
    width, height = get_target_size()
    if max(image.size) > MODEL_PRESHRINK_SIDE:
        image = image.resize((MODEL_PRESHRINK_SIDE, MODEL_PRESHRINK_SIDE), Image.BILINEAR)
    image = image.resize((width, height), Image.NEAREST)
    return np.asarray(image, dtype=np.float32)[None] / 255.0


def class_probabilities(image: Image.Image) -> np.ndarray:
    model = get_plant_disease_model()
    return np.asarray(model(preprocess(image), training=False))[0]


# --- Decision --------------------------------------------------------------------

def crop_masses(probs: np.ndarray) -> dict:
    """How much of the model's probability sits on each crop."""
    return {crop: float(probs[indices].sum()) for crop, indices in CROP_CLASSES.items()}


def _match(probs: np.ndarray, index: int) -> dict:
    label = PLANT_DISEASE_CLASS_NAMES[index]
    return {"class_id": label, "disease": lookup_disease_info(label)["name"], "confidence": round(float(probs[index]), 2)}


def _top_matches(probs: np.ndarray, indices, count: int = 3) -> list:
    ranked = sorted(indices, key=lambda i: probs[i], reverse=True)[:count]
    return [_match(probs, i) for i in ranked]


def known_conditions(crop: str) -> list:
    """The problems the scan can recognise for a crop (not counting 'healthy')."""
    names = []
    for index in CROP_CLASSES[crop]:
        label = PLANT_DISEASE_CLASS_NAMES[index]
        if "healthy" in label.lower():
            continue
        name = lookup_disease_info(label)["name"]
        suffix = f" ({crop_name(crop)})"
        names.append(name[: -len(suffix)] if name.lower().endswith(suffix) else name)
    return names


def _photo_check_refusal(check):
    """Refusal for what the photo check says about the photo itself, or None to carry on."""
    by_subject = {"not_a_plant": "not_a_leaf", "no_leaf_visible": "no_leaf",
                  "plant_or_field_far": "too_far", "too_blurry_or_dark": "poor_photo"}
    if check.subject in by_subject:
        return refuse(by_subject[check.subject], plant_name=check.plant_name)
    if check.crop == "other_plant":
        return refuse("unsupported_crop", plant_name=check.plant_name)
    if check.crop in CROP_KEYS and check.crop_certainty != "low" and check.crop not in DIAGNOSABLE_CROPS:
        return refuse("not_diagnosable", crop=check.crop)
    return None


def _confirmed_crop(check):
    """The crop the photo check is sure about, or None."""
    if check and check.crop in DIAGNOSABLE_CROPS and check.crop_certainty != "low":
        return check.crop
    return None


def decide(probs: np.ndarray, check, mode: str) -> dict:
    """
    Turn the model's probabilities and the photo check (None if unavailable) into the final result.
    mode: 'required' refuses when there is no photo check; 'optional' and 'off' go ahead without
    one, with a stricter confidence bar and a warning.
    """
    if check is not None:
        refusal = _photo_check_refusal(check)
        if refusal:
            return refusal
    elif mode == "required":
        return refuse("check_unavailable")

    crop = _confirmed_crop(check)
    if crop is None and check is not None and mode == "required":
        return refuse("crop_unclear")

    if crop is not None:
        if crop_masses(probs)[crop] < CROP_AGREEMENT_MIN:
            return refuse("crop_mismatch", crop=crop)
        indices = CROP_CLASSES[crop]
        best = max(indices, key=lambda i: probs[i])
        needed = MIN_PREDICTION_CONFIDENCE
    else:
        best = int(np.argmax(probs))
        crop = CROP_OF_CLASS[best]
        indices = CROP_CLASSES[crop]
        needed = UNVERIFIED_MIN_CONFIDENCE
        if crop not in DIAGNOSABLE_CROPS:
            return refuse("low_confidence")

    label = PLANT_DISEASE_CLASS_NAMES[best]
    is_healthy = "healthy" in label.lower()
    if check is not None:
        if is_healthy and check.symptoms == "clear":
            return refuse("symptoms_vs_healthy", crop=crop)
        if not is_healthy and check.symptoms == "none_visible":
            return refuse("no_symptoms_vs_disease", crop=crop)
    if probs[best] < needed:
        return refuse("low_confidence", crop=crop, alternatives=_top_matches(probs, indices))

    verified = _confirmed_crop(check) is not None
    cautions = [RELIABILITY_NOTE]
    if not verified:
        cautions.insert(0, "The crop could not be confirmed from the photo, so this may be a different crop altogether.")
    if is_healthy:
        cautions.insert(0, f"No problem the scan knows was found. For {crop_name(crop)} it only knows: "
                           f"{', '.join(known_conditions(crop))}. A healthy result does not rule out other diseases, pests or lack of nutrients.")

    info = lookup_disease_info(label)
    return {
        "status": "ok",
        "label": "Healthy" if is_healthy else "Diseased",
        "disease": info.get("name", label),
        "description": info.get("description", ""),
        "cure": info.get("cure", "N/A"),
        "prevention": info.get("prevention", "N/A"),
        "confidence": round(float(probs[best]), 2),
        "class_id": label,
        "crop": crop,
        "crop_name": crop_name(crop),
        "verified": verified,
        "is_plant": True,
        "cautions": cautions,
        "alternatives": _top_matches(probs, indices),
        "known_conditions": known_conditions(crop),
    }


def analyze_photo(image: Image.Image) -> dict:
    """Run the whole pipeline on a photo."""
    image = prepare_photo(image)
    problem = photo_problem(image)
    if problem:
        return refuse(problem)

    mode = leaf_check.check_mode()
    # Ask Gemini about the photo while the model runs.
    pending = _executor.submit(leaf_check.check_photo, image) if mode != "off" else None
    probs = class_probabilities(image)
    check = pending.result() if pending else None
    return decide(probs, check, mode)
