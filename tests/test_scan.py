"""Tests for the scan pipeline (services/scan.py): every refusal rule and the happy path."""
import io
import os
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
from PIL import Image

from services import scan
from services.disease import CROP_KEYS, DIAGNOSABLE_CROPS, PLANT_DISEASE_CLASS_NAMES as LABELS
from services.leaf_check import PhotoCheck


def probs(**by_label):
  """Probability vector: the given classes get the given mass, the rest is spread evenly."""
  vector = np.zeros(len(LABELS), dtype=np.float64)
  for label, p in by_label.items():
    vector[LABELS.index(label.replace("__", "___"))] = p
  rest = [i for i in range(len(LABELS)) if vector[i] == 0]
  vector[rest] = max(0.0, 1.0 - vector.sum()) / len(rest)
  return vector


def check(crop="tomato", subject="leaf_closeup", certainty="high", symptoms="clear", plant_name=""):
  return PhotoCheck(subject=subject, crop=crop, crop_certainty=certainty, plant_name=plant_name, symptoms=symptoms)


def noisy_photo(size=(200, 160), seed=0):
  rng = np.random.RandomState(seed)
  return Image.fromarray((rng.rand(size[1], size[0], 3) * 255).astype("uint8"))


class AcceptedResultTest(unittest.TestCase):
  def test_confirmed_crop_and_agreeing_model_is_shown_with_warnings(self):
    r = scan.decide(probs(Tomato__Early_blight=0.9), check("tomato", symptoms="clear"), "required")
    self.assertEqual(r["status"], "ok")
    self.assertEqual((r["label"], r["disease"], r["crop"], r["verified"]), ("Diseased", "Early Blight (Tomato)", "tomato", True))
    self.assertTrue(r["cure"] and r["prevention"] and r["description"])
    self.assertIn(scan.RELIABILITY_NOTE, r["cautions"])
    self.assertEqual(len(r["alternatives"]), 3)
    self.assertTrue(all(a["class_id"].startswith("Tomato___") for a in r["alternatives"]))

  def test_healthy_result_lists_what_the_scan_knows(self):
    r = scan.decide(probs(Tomato__healthy=0.9), check("tomato", symptoms="none_visible"), "required")
    self.assertEqual((r["status"], r["label"]), ("ok", "Healthy"))
    self.assertIn("does not rule out", r["cautions"][0])
    self.assertIn("Early Blight", r["cautions"][0])
    self.assertNotIn("Healthy", ", ".join(r["known_conditions"]))

  def test_possible_symptoms_do_not_veto_either_answer(self):
    for label in ("Tomato__healthy", "Tomato__Early_blight"):
      r = scan.decide(probs(**{label: 0.9}), check("tomato", symptoms="possible"), "required")
      self.assertEqual(r["status"], "ok", label)

  def test_answer_is_taken_from_the_confirmed_crop_only(self):
    # Potato is the model's top class, but the photo is a tomato leaf and tomato holds 55% of the mass.
    with patch.object(scan, "MIN_PREDICTION_CONFIDENCE", 0.2):
      r = scan.decide(probs(Potato__Late_blight=0.4, Tomato__Early_blight=0.3, Tomato__Late_blight=0.25), check("tomato"), "required")
    self.assertEqual(r["status"], "ok")
    self.assertEqual(r["class_id"], "Tomato___Early_blight")


class PhotoRefusalTest(unittest.TestCase):
  def test_subjects_that_are_not_a_usable_leaf(self):
    expected = {"not_a_plant": "not_a_leaf", "no_leaf_visible": "no_leaf",
                "plant_or_field_far": "too_far", "too_blurry_or_dark": "poor_photo"}
    for subject, reason in expected.items():
      r = scan.decide(probs(Tomato__Early_blight=0.99), check("tomato", subject=subject), "required")
      self.assertEqual((r["status"], r["reason"], r["kind"]), ("rejected", reason, "retake"), subject)
      self.assertEqual(r["label"], "Uncertain")

  def test_other_plants_are_refused_by_name(self):
    r = scan.decide(probs(Corn__Common_rust_=0.99), check("other_plant", plant_name="rice"), "required")
    self.assertEqual((r["reason"], r["kind"], r["headline"]), ("unsupported_crop", "unsupported", "Rice isn't covered yet"))
    self.assertIn("rice", r["message"])
    self.assertIn("tomato", r["message"])          # tells the farmer what is covered
    self.assertNotIn("soybean", r["message"])      # ...and only what can really be diagnosed
    unnamed = scan.decide(probs(Corn__Common_rust_=0.99), check("other_plant"), "required")
    self.assertEqual(unnamed["headline"], "This crop isn't covered yet")

  def test_crops_with_a_single_class_cannot_be_diagnosed(self):
    r = scan.decide(probs(Soybean__healthy=0.99), check("soybean", symptoms="none_visible"), "required")
    self.assertEqual((r["reason"], r["kind"]), ("not_diagnosable", "unsupported"))
    self.assertIn("only healthy soybean leaves", r["message"])
    orange = scan.decide(probs(**{"Orange__Haunglongbing(Citrus_greening)": 0.99}), check("orange"), "required")
    self.assertIn("only orange leaves with citrus greening", orange["message"].lower())

  def test_the_nine_diagnosable_crops(self):
    self.assertEqual(DIAGNOSABLE_CROPS, {"apple", "bell_pepper", "cherry", "corn", "grape", "peach", "potato", "strawberry", "tomato"})
    self.assertEqual(set(CROP_KEYS) - DIAGNOSABLE_CROPS, {"blueberry", "orange", "raspberry", "soybean", "squash"})


class ConsistencyRefusalTest(unittest.TestCase):
  def test_model_that_believes_another_crop_is_not_trusted(self):
    # The photo is an apple leaf; the model is sure it is a peach leaf (what it did on a real apple photo).
    r = scan.decide(probs(Peach__Bacterial_spot=1.0), check("apple"), "required")
    self.assertEqual((r["reason"], r["kind"], r["crop"]), ("crop_mismatch", "unsure", "apple"))
    self.assertIn("apple", r["message"])
    self.assertEqual(r["alternatives"], [])

  def test_healthy_answer_for_a_leaf_with_clear_symptoms(self):
    r = scan.decide(probs(Tomato__healthy=0.95), check("tomato", symptoms="clear"), "required")
    self.assertEqual(r["reason"], "symptoms_vs_healthy")

  def test_disease_answer_for_a_leaf_without_symptoms(self):
    r = scan.decide(probs(Tomato__Late_blight=0.95), check("tomato", symptoms="none_visible"), "required")
    self.assertEqual(r["reason"], "no_symptoms_vs_disease")

  def test_low_confidence_shows_the_closest_matches(self):
    r = scan.decide(probs(Tomato__Early_blight=0.4, Tomato__Late_blight=0.3, Tomato__Leaf_Mold=0.2), check("tomato"), "required")
    self.assertEqual((r["status"], r["reason"]), ("rejected", "low_confidence"))
    self.assertEqual([a["class_id"] for a in r["alternatives"]],
                     ["Tomato___Early_blight", "Tomato___Late_blight", "Tomato___Leaf_Mold"])


class WithoutPhotoCheckTest(unittest.TestCase):
  def test_required_mode_refuses_instead_of_guessing(self):
    r = scan.decide(probs(Tomato__Early_blight=0.99), None, "required")
    self.assertEqual((r["reason"], r["kind"]), ("check_unavailable", "unavailable"))

  def test_optional_and_off_modes_show_a_stricter_unverified_answer(self):
    for mode in ("optional", "off"):
      sure = scan.decide(probs(Tomato__Early_blight=0.95), None, mode)
      self.assertEqual((sure["status"], sure["verified"]), ("ok", False), mode)
      self.assertIn("could not be confirmed", sure["cautions"][0])
      unsure = scan.decide(probs(Tomato__Early_blight=0.8), None, mode)
      self.assertEqual(unsure["reason"], "low_confidence", mode)

  def test_unverified_answer_for_a_crop_that_cannot_be_diagnosed_is_refused(self):
    self.assertEqual(scan.decide(probs(Soybean__healthy=0.99), None, "off")["status"], "rejected")

  def test_unclear_crop(self):
    unclear = check("cannot_tell")
    self.assertEqual(scan.decide(probs(Tomato__Early_blight=0.99), unclear, "required")["reason"], "crop_unclear")
    optional = scan.decide(probs(Tomato__Early_blight=0.95), unclear, "optional")
    self.assertEqual((optional["status"], optional["verified"]), ("ok", False))
    low = check("tomato", certainty="low")
    self.assertEqual(scan.decide(probs(Tomato__Early_blight=0.99), low, "required")["reason"], "crop_unclear")


class RefusalTextTest(unittest.TestCase):
  def test_every_reason_has_complete_text(self):
    reasons = ("photo_unusable", "not_a_leaf", "no_leaf", "too_far", "poor_photo", "unsupported_crop", "not_diagnosable",
               "crop_mismatch", "crop_unclear", "symptoms_vs_healthy", "no_symptoms_vs_disease", "low_confidence", "check_unavailable")
    for reason in reasons:
      r = scan.refuse(reason, crop="soybean", plant_name="rice")
      self.assertIn(r["kind"], ("retake", "unsupported", "unsure", "unavailable"), reason)
      for field in ("headline", "message", "advice"):
        self.assertTrue(r[field].strip(), f"{reason}.{field}")
      self.assertEqual((r["disease"], r["description"], r["prevention"]), (r["headline"], r["message"], r["advice"]))
    with self.assertRaises(ValueError):
      scan.refuse("made_up")


class PhotoPreparationTest(unittest.TestCase):
  def test_tiny_and_blank_photos_are_unusable_but_noise_is_not(self):
    self.assertEqual(scan.photo_problem(noisy_photo((32, 32))), "photo_unusable")
    self.assertEqual(scan.photo_problem(Image.new("RGB", (300, 300), (60, 130, 50))), "photo_unusable")
    self.assertIsNone(scan.photo_problem(noisy_photo((300, 200))))

  def test_phone_rotation_is_applied(self):
    exif = Image.Exif()
    exif[0x0112] = 6  # rotate 90 degrees
    buffer = io.BytesIO()
    noisy_photo((300, 200)).save(buffer, format="JPEG", exif=exif)
    buffer.seek(0)
    self.assertEqual(scan.prepare_photo(Image.open(buffer)).size, (200, 300))

  def test_model_input_shape_and_range(self):
    for size in ((112, 112), (200, 160), (4000, 3000)):
      x = scan.preprocess(Image.new("RGB", size, (255, 0, 128)))
      self.assertEqual(x.shape, (1, 112, 112, 3), size)
      self.assertEqual(x.dtype, np.float32)
      self.assertAlmostEqual(float(x.max()), 1.0, places=5)

  def test_resize_is_nearest_neighbour(self):
    # A native-size photo must reach the model unchanged (no smoothing).
    photo = noisy_photo((112, 112), seed=3)
    np.testing.assert_allclose(scan.preprocess(photo)[0], np.asarray(photo, dtype=np.float32) / 255.0)


class AnalyzePhotoTest(unittest.TestCase):
  def test_unusable_photo_never_reaches_the_model_or_gemini(self):
    with patch.object(scan, "class_probabilities", side_effect=AssertionError("model called")), \
         patch.object(scan.leaf_check, "check_photo", side_effect=AssertionError("gemini called")):
      r = scan.analyze_photo(Image.new("RGB", (300, 300), (10, 10, 10)))
    self.assertEqual(r["reason"], "photo_unusable")

  def test_photo_check_and_model_are_combined(self):
    photo = noisy_photo()
    with patch.dict(os.environ, {"LEAF_CHECK": "required"}), \
         patch.object(scan, "class_probabilities", return_value=probs(Grape__Black_rot=0.97)), \
         patch.object(scan.leaf_check, "check_photo", return_value=check("grape")) as ask:
      r = scan.analyze_photo(photo)
    ask.assert_called_once()
    self.assertEqual((r["status"], r["class_id"], r["verified"]), ("ok", "Grape___Black_rot", True))

  def test_check_is_skipped_when_off(self):
    with patch.dict(os.environ, {"LEAF_CHECK": "off"}), \
         patch.object(scan, "class_probabilities", return_value=probs(Grape__Black_rot=0.97)), \
         patch.object(scan.leaf_check, "check_photo", side_effect=AssertionError("gemini called")):
      r = scan.analyze_photo(noisy_photo())
    self.assertEqual((r["status"], r["verified"]), ("ok", False))

  def test_required_mode_with_unreachable_gemini_refuses(self):
    with patch.dict(os.environ, {"LEAF_CHECK": "required"}), \
         patch.object(scan, "class_probabilities", return_value=probs(Grape__Black_rot=0.97)), \
         patch.object(scan.leaf_check, "check_photo", return_value=None):
      r = scan.analyze_photo(noisy_photo())
    self.assertEqual(r["reason"], "check_unavailable")


class KnownConditionsTest(unittest.TestCase):
  def test_names_drop_the_crop_suffix_and_the_healthy_class(self):
    tomato = scan.known_conditions("tomato")
    self.assertEqual(len(tomato), 9)
    self.assertIn("Early Blight", tomato)
    self.assertIn("Esca (Black Measles)", scan.known_conditions("grape"))
    for crop in DIAGNOSABLE_CROPS:
      self.assertTrue(scan.known_conditions(crop), crop)


if __name__ == "__main__":
  unittest.main()
