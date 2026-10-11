"""
Gemini AI service: LLM integration, system prompts, translation, error helpers.
"""
import base64
import json
import logging
import os
import re
import time
import urllib.error
import urllib.parse
import urllib.request

from flask import jsonify

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# System prompts
# ---------------------------------------------------------------------------

AGRICULTURE_KEYWORDS = [
    "crop", "plant", "farming", "farmer", "agriculture", "agricultural", "harvest",
    "seed", "fertilizer", "pesticide", "irrigation", "soil", "disease", "pest",
    "yield", "cultivation", "sowing", "weather", "rainfall", "drought", "flood",
    "scheme", "subsidy", "loan", "credit", "insurance", "market", "price",
    "vegetable", "fruit", "grain", "wheat", "rice", "corn", "tomato", "potato",
    "organic", "compost", "manure", "weed", "blight", "rust", "mildew",
    "livestock", "cattle", "dairy", "poultry", "fishery", "aquaculture",
]

AGRO_SYSTEM_PROMPT = """You are an expert agriculture assistant for AgroVision, helping farmers with plant disease detection and agricultural guidance.

Provide accurate, practical advice on crops, diseases, government schemes, soil, irrigation, and Indian farming context when relevant.
Keep answers clear, practical, and farmer-friendly.

When giving advice:
- Start with the likely issue or direct answer. Do not open with a greeting.
- Give 3 to 5 clear action steps.
- Mention safety precautions for pesticides/fungicides.
- Suggest checking with a local agriculture officer for severe crop loss, chemical dosage, or official scheme eligibility.

Redirect non-agriculture questions politely."""

TRANSLATION_SYSTEM_PROMPT = """You are a precise UI translator for AgroVision, an agriculture app for farmers.

Translate each provided UI string into the requested target language.
Rules:
- Return only valid JSON with this exact shape: {"translations":["..."]}.
- Keep the same number and order of strings.
- Preserve numbers, URLs, placeholders like {name}, units, crop/scheme names, and brand name AgroVision.
- Keep translations short enough for buttons, menus, labels, and mobile screens.
- Do not add explanations."""

SCHEMES_SYSTEM_PROMPT = """You are an Indian government agricultural schemes advisor for AgroVision.

Use ONLY the scheme data provided in the user message. Do not invent benefit amounts, deadlines, portals, or rules.
If the farmer's profile is incomplete, still give useful matches and clearly mention what must be verified on the official portal or with the local agriculture office.

Format every answer exactly with these short sections:
## Best Matches
- Scheme name: why it fits this farmer, benefit, and one eligibility note.

## Documents To Keep Ready
- List only documents supported by the provided scheme data.

## How To Apply
- Give practical channel guidance such as official portal, bank, CSC, or agriculture office based on the scheme data.

## Important Checks
- Mention state-specific limits, land/tenant record checks, notified crop/area checks, bank KYC, or official verification as relevant.

Use plain farmer-friendly English, keep it concise, and prefer 2 to 4 recommended schemes unless the user asks for one specific scheme."""

# ---------------------------------------------------------------------------
# Gemini LLM call (REST)
# ---------------------------------------------------------------------------
# Uses the Gemini REST API through urllib rather than the Google SDK. urllib
# verifies TLS with the operating system's certificate store, which works on
# networks that inspect HTTPS (where the SDK's gRPC transport fails), and it
# keeps the request timeout under our control.

_GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
GEMINI_TIMEOUT_SECONDS = float(os.environ.get("GEMINI_TIMEOUT_SECONDS", "30"))
# "-latest" names are kept pointing at a current model by Google; fixed names such as
# gemini-2.0-flash get retired (they now answer 404). Quota is counted per model, so
# when one model's free allowance runs out the next one in this list can still answer.
DEFAULT_MODEL = "gemini-flash-latest"
_FALLBACK_MODELS = ["gemini-flash-latest", "gemini-flash-lite-latest"]

# Models that answered 429 (quota/rate limit) are skipped until this monotonic time,
# instead of paying for a failing call on every request.
_cooldown_until = {}
_COOLDOWN_MIN_SECONDS = 5.0
_COOLDOWN_MAX_SECONDS = 900.0  # re-check at least every 15 minutes, e.g. after a daily reset


class GeminiError(RuntimeError):
    """Gemini could not produce an answer."""


def _call_gemini(model: str, api_key: str, system_prompt: str, user_message: str, *,
                 image_jpeg: bytes = None, schema: dict = None, timeout: float = None) -> str:
    """One generateContent call. With `schema`, Gemini is forced to answer in that JSON shape."""
    parts = [{"text": user_message}]
    if image_jpeg is not None:
        parts.append({"inline_data": {"mime_type": "image/jpeg", "data": base64.b64encode(image_jpeg).decode("ascii")}})
    body = {
        "system_instruction": {"parts": [{"text": system_prompt}]},
        "contents": [{"role": "user", "parts": parts}],
    }
    if schema is not None:
        body["generationConfig"] = {
            "responseMimeType": "application/json",
            "responseSchema": schema,
            "temperature": 0,
        }
    request = urllib.request.Request(
        _GEMINI_URL.format(model=urllib.parse.quote(model, safe="-._")),
        data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json", "x-goog-api-key": api_key},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=timeout or GEMINI_TIMEOUT_SECONDS) as response:
        data = json.loads(response.read().decode("utf-8"))

    candidates = data.get("candidates") or []
    parts = ((candidates[0].get("content") or {}).get("parts") or []) if candidates else []
    text = "".join(part.get("text", "") for part in parts).strip()
    if not text:
        reason = candidates[0].get("finishReason") if candidates else (data.get("promptFeedback") or {}).get("blockReason")
        raise GeminiError(f"Gemini returned no text (reason: {reason or 'unknown'}).")
    return text


def _retry_after_seconds(error_body: str) -> float:
    """Seconds Gemini asks us to wait, from text like 'Please retry in 11h23m17.03s'."""
    match = re.search(r"retry in (?:(\d+)h)?(?:(\d+)m)?(?:([\d.]+)s)?", error_body or "")
    if not match or not any(match.groups()):
        return _COOLDOWN_MIN_SECONDS
    hours, minutes, seconds = (float(g) if g else 0.0 for g in match.groups())
    return hours * 3600 + minutes * 60 + seconds


def _generate(system_prompt: str, user_message: str, api_key=None, model_name=None, **call_options) -> str:
    """Try the configured model, then known fallbacks, until one returns text."""
    api_key = (api_key or os.environ.get("GEMINI_API_KEY", "")).strip()
    if not api_key:
        raise GeminiError("GEMINI_API_KEY is not set.")

    preferred = (model_name or os.environ.get("GEMINI_MODEL", DEFAULT_MODEL)).strip()
    models = [m for m in dict.fromkeys([preferred, *_FALLBACK_MODELS]) if m]

    last_error = None
    for model in models:
        if _cooldown_until.get(model, 0) > time.monotonic():
            last_error = last_error or GeminiError(f"{model} is over its quota for now")
            continue
        try:
            return _call_gemini(model, api_key, system_prompt, user_message, **call_options)
        except urllib.error.HTTPError as exc:
            last_error = exc
            logger.warning(f"Gemini model '{model}' failed: HTTP {exc.code}")
            if exc.code == 429:
                wait = _retry_after_seconds(exc.read().decode("utf-8", "replace"))
                _cooldown_until[model] = time.monotonic() + min(max(wait, _COOLDOWN_MIN_SECONDS), _COOLDOWN_MAX_SECONDS)
            # A bad key or bad request will fail the same way on every model.
            if exc.code in (400, 401, 403):
                break
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            last_error = exc
            logger.warning(f"Gemini model '{model}' unreachable: {type(exc).__name__}")
            break  # network problem: other models won't do better
        except GeminiError as exc:
            last_error = exc
            logger.warning(f"Gemini model '{model}': {exc}")

    raise GeminiError(f"Gemini request failed: {last_error}") from last_error


def generate_gemini_reply(user_message: str, system_prompt=None, api_key=None, model_name=None) -> str:
    """Ask Gemini for a text reply."""
    return _generate(system_prompt or AGRO_SYSTEM_PROMPT, user_message, api_key, model_name)


def generate_gemini_json(user_message: str, system_prompt: str, schema: dict, image_jpeg: bytes = None,
                         api_key=None, model_name=None, timeout: float = None) -> dict:
    """Ask Gemini (optionally about an image) for an answer that matches a JSON schema."""
    text = _generate(system_prompt, user_message, api_key, model_name,
                     image_jpeg=image_jpeg, schema=schema, timeout=timeout)
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise GeminiError("Gemini did not return valid JSON.") from exc
    if not isinstance(data, dict):
        raise GeminiError("Gemini returned JSON that is not an object.")
    return data


# ---------------------------------------------------------------------------
# Translation helper
# ---------------------------------------------------------------------------

def extract_json_object(text: str) -> dict:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.strip("`")
        cleaned = cleaned.replace("json\n", "", 1).replace("JSON\n", "", 1).strip()
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start != -1 and end != -1 and end > start:
            return json.loads(cleaned[start:end + 1])
        raise


def translate_texts_with_gemini(texts, target_language: str, api_key=None):
    """
    Translate a list of strings. Cached translations are reused, only the missing strings go to
    Gemini, and only translations that pass validation are kept. Strings that could not be
    translated come back unchanged (English), so one bad string never blanks a page.
    Raises only when nothing at all could be translated.
    """
    from services import translation_cache  # local import: the cache is optional for callers of this module

    cached = translation_cache.get_many(target_language, texts)
    missing = list(dict.fromkeys(t for t in texts if t not in cached))

    fresh = {}
    if missing:
        payload = {"target_language": target_language, "texts": missing}
        try:
            reply = generate_gemini_reply(
                json.dumps(payload, ensure_ascii=False), TRANSLATION_SYSTEM_PROMPT, api_key=api_key)
            translations = extract_json_object(reply).get("translations")
            if not isinstance(translations, list) or len(translations) != len(missing):
                raise ValueError("Translation response did not match requested text count.")
            fresh = {src: str(out) for src, out in zip(missing, translations)}
            translation_cache.put_many(target_language, fresh)
        except Exception:
            if not cached:
                raise
            logger.warning("Translation service unavailable; using cached translations only.")
            fresh = {}

    result = []
    for text in texts:
        out = cached.get(text) or (fresh.get(text) if translation_cache.is_valid_translation(text, fresh.get(text)) else None)
        result.append(out or text)
    return result


# ---------------------------------------------------------------------------
# Error response helper (shared across routes)
# ---------------------------------------------------------------------------

def gemini_error_response(exc: Exception):
    """Return a dummy response for Gemini failures instead of error messages."""
    logger.error(f"Gemini service error (using fallback): {exc}")
    
    # Return a dummy response instead of error
    dummy_response = """
## General Agricultural Support & Schemes

> **AI assistant unavailable right now.** The text below is general, pre-written information, not advice tailored to your question.

Here's important information about government support for Indian farmers:

### Key Government Schemes
- **PM-KISAN**: Direct income support of ₹6,000/year in 3 installments
- **Pradhan Mantri Fasal Bima Yojana (PMFBY)**: Crop insurance for weather risks and yield losses
- **Soil Health Card Scheme**: Free soil testing and nutrient management recommendations
- **State-specific subsidies**: Check with your local agriculture office for crop-specific support

### Steps to Apply
1. Visit your nearest CSC (Common Service Center) or agriculture office
2. Prepare documents: Land records, Aadhar, bank account details
3. Verify eligibility for schemes in your state
4. Submit application through official portal or authorized centers
5. Follow up for approval and fund transfer

### Important Notes
- Eligibility varies by state, crop, and land size
- Some schemes are for all farmers, others for specific groups
- Always apply through official channels to avoid fraud
- Contact local agriculture extension officer for personalized guidance

**For detailed information, visit your state's agriculture department website or the official scheme portals.**
"""
    
    return jsonify({
        "response": dummy_response,
        "ai_powered": False,
        "fallback": True,
    }), 200
