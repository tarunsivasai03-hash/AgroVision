"""
Gemini AI service: LLM integration, system prompts, translation, error helpers.
"""
import json
import logging
import os

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
- Start with the likely issue or direct answer.
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
# Gemini LLM call
# ---------------------------------------------------------------------------

def generate_gemini_reply(user_message: str, system_prompt=None, api_key=None, model_name=None) -> str:
    """Call Gemini with request-provided or environment API key and current model IDs."""
    api_key = (api_key or os.environ.get("GEMINI_API_KEY", "")).strip()

    if not api_key:
        raise ValueError("GEMINI_API_KEY is required. Provide it in your request payload or environment.")

    genai = None
    use_new_sdk = False
    try:
        from google import genai as genai_module
        genai = genai_module
        use_new_sdk = True
    except ImportError:
        try:
            import google.generativeai as genai_module
            genai = genai_module
        except ImportError as e:
            logger.warning(f"Failed to import Gemini SDK: {e}")
            raise ImportError(
                "Gemini SDK not installed. Install google.generativeai or google.genai and restart the server."
            ) from e

    prompt = f"{(system_prompt or AGRO_SYSTEM_PROMPT)}\n\nUser Question: {user_message}\n\nAssistant Response:"
    preferred = (model_name or os.environ.get("GEMINI_MODEL", "gemini-1.0")).strip()
    model_candidates = [
        preferred,
        "gemini-2.5-flash",
        "gemini-2.0-flash",
        "gemini-1.5-flash",
        "gemini-2.5-mini",
        "gemini-2.0-mini",
        "gemini-1.5-mini",
        "gemini-1.0",
        "gemini-1.0-mini",
    ]
    model_candidates = [m for m in dict.fromkeys(model_candidates) if m]

    last_error = None

    if use_new_sdk:
        try:
            client = genai.Client(api_key=api_key)
        except TypeError:
            client = genai.Client()

        for model_name in model_candidates:
            try:
                response = client.generate_text(model=model_name, prompt=prompt)
                if hasattr(response, "text") and response.text:
                    return response.text.strip()
                if isinstance(response, dict):
                    text = response.get("text") or response.get("output", {}).get("text")
                    if text:
                        return str(text).strip()
            except Exception as exc:
                last_error = exc
                logger.warning(f"Gemini model '{model_name}' failed: {exc}")
        raise RuntimeError(
            "Gemini request failed for all model candidates." +
            (f" Last error: {last_error}" if last_error else "")
        ) from last_error

    genai.configure(api_key=api_key)
    available_models = []
    if hasattr(genai, "list_models"):
        try:
            models = genai.list_models()
            for model in models:
                if isinstance(model, dict):
                    raw_name = model.get("name") or model.get("id") or ""
                else:
                    raw_name = getattr(model, "name", None) or getattr(model, "id", None) or ""
                # Normalize: list_models returns "models/gemini-..." but candidates use "gemini-..."
                short_name = raw_name.split("/")[-1] if "/" in raw_name else raw_name
                available_models.append(short_name)
        except Exception as exc:
            logger.info(f"Could not list Gemini models: {exc}")

    for model_name in model_candidates:
        if available_models and model_name not in available_models:
            continue
        try:
            model = genai.GenerativeModel(model_name)
            response = model.generate_content(prompt)
            if hasattr(response, "text") and response.text:
                return response.text.strip()
            if getattr(response, "candidates", None):
                parts = response.candidates[0].content.parts
                if parts and hasattr(parts[0], "text"):
                    return parts[0].text.strip()
            return str(response).strip()
        except Exception as exc:
            last_error = exc
            logger.warning(f"Gemini model '{model_name}' failed: {exc}")

    # If available_models filtering skipped all candidates but none actually errored,
    # retry without filtering before giving up.
    if available_models and last_error is None:
        logger.info("All model candidates were filtered out by list_models. Retrying without filter.")
        for model_name in model_candidates:
            try:
                model = genai.GenerativeModel(model_name)
                response = model.generate_content(prompt)
                if hasattr(response, "text") and response.text:
                    return response.text.strip()
                if getattr(response, "candidates", None):
                    parts = response.candidates[0].content.parts
                    if parts and hasattr(parts[0], "text"):
                        return parts[0].text.strip()
                return str(response).strip()
            except Exception as exc:
                last_error = exc
                logger.warning(f"Gemini model '{model_name}' (unfiltered retry) failed: {exc}")

    raise RuntimeError(
        "Gemini request failed for all model candidates." +
        (f" Last error: {last_error}" if last_error else "")
    ) from last_error


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
    """Translate a list of strings using Gemini."""
    payload = {
        "target_language": target_language,
        "texts": texts,
    }
    reply = generate_gemini_reply(
        json.dumps(payload, ensure_ascii=False),
        TRANSLATION_SYSTEM_PROMPT,
        api_key=api_key,
    )
    parsed = extract_json_object(reply)
    translations = parsed.get("translations")
    if not isinstance(translations, list) or len(translations) != len(texts):
        raise ValueError("Translation response did not match requested text count.")
    return [str(item) for item in translations]


# ---------------------------------------------------------------------------
# Error response helper (shared across routes)
# ---------------------------------------------------------------------------

def gemini_error_response(exc: Exception):
    """Return a dummy response for Gemini failures instead of error messages."""
    logger.error(f"Gemini service error (using fallback): {exc}")
    
    # Return a dummy response instead of error
    dummy_response = """
## General Agricultural Support & Schemes

I'm currently in offline/demo mode, but here's important information about government support for Indian farmers:

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
