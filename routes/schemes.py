"""
Scheme Advisor blueprint: /api/schemes/*
"""
import json
import logging

from flask import Blueprint, request, jsonify

from services.gemini import (
    SCHEMES_SYSTEM_PROMPT,
    generate_gemini_reply,
    gemini_error_response,
)
from services.schemes_data import (
    get_government_schemes,
    scheme_by_id,
    qualify_farmer,
)

logger = logging.getLogger(__name__)

schemes_bp = Blueprint("schemes", __name__, url_prefix="/api/schemes")


@schemes_bp.route("", methods=["GET"])
def list_schemes():
    """Return curated government schemes JSON."""
    return jsonify({"schemes": get_government_schemes()})


@schemes_bp.route("/advise", methods=["POST"])
def advise():
    """Gemini advisor: eligibility and scheme recommendations."""
    try:
        data = request.get_json(silent=True) or {}
        message = (data.get("message") or "").strip()
        if not message:
            return jsonify({"error": "message is required"}), 400

        state = (data.get("state") or "not specified").strip()
        crop = (data.get("crop") or "not specified").strip()
        land = (data.get("land_acres") or "not specified").strip()

        schemes_context = json.dumps(get_government_schemes(), indent=2, ensure_ascii=False)
        profile_completeness = []
        if state.lower() in {"not specified", "india (general)", "all india / not sure"}:
            profile_completeness.append("state is not specific")
        if crop.lower() == "not specified":
            profile_completeness.append("crop is not specified")
        if land.lower() == "not specified":
            profile_completeness.append("land size is not specified")

        user_block = (
            f"Farmer profile: State={state}, Crop={crop}, Land (acres)={land}\n\n"
            f"Missing profile details: {', '.join(profile_completeness) if profile_completeness else 'none'}\n"
            "Matching rules: national schemes can apply across India if eligibility fits; "
            "state schemes should be recommended only when the farmer state matches or when clearly marked as a state-specific option.\n\n"
            f"Available schemes database:\n{schemes_context}\n\n"
            f"Farmer question:\n{message}"
        )

        # Always use environment API key
        reply = generate_gemini_reply(user_block, SCHEMES_SYSTEM_PROMPT)
        return jsonify({"response": reply, "ai_powered": True})
    except Exception as exc:
        logger.error(f"Schemes advise error: {exc}")
        return gemini_error_response(exc)


@schemes_bp.route("/<scheme_id>/explain", methods=["POST"])
def explain(scheme_id):
    """Gemini-generated detailed guide for one scheme."""
    try:
        scheme = scheme_by_id(scheme_id)
        if not scheme:
            return jsonify({"error": "Scheme not found"}), 404

        data = request.get_json(silent=True) or {}
        state = (data.get("state") or "India").strip()
        question = (data.get("question") or "Explain eligibility, documents, steps to apply, and benefits.").strip()

        user_block = (
            f"Scheme data:\n{json.dumps(scheme, indent=2, ensure_ascii=False)}\n\n"
            f"Farmer state: {state}\n"
            "If this is a state scheme and the farmer state does not match, clearly say it may not apply.\n"
            f"Specific request: {question}"
        )
        # Always use environment API key
        reply = generate_gemini_reply(user_block, SCHEMES_SYSTEM_PROMPT)
        return jsonify({
            "scheme": scheme,
            "response": reply,
            "ai_powered": True,
        })
    except Exception as exc:
        logger.error(f"Scheme explain error: {exc}")
        return gemini_error_response(exc)


@schemes_bp.route("/qualify", methods=["POST"])
def qualify():
    """
    Rule-based scheme eligibility check — no Gemini call needed.

    Request JSON:
        {
            "state": "Telangana",
            "crop": "Paddy",          (optional)
            "land_acres": "2.5",      (optional)
            "farmer_type": "landowner" (optional: landowner | tenant | any)
        }

    Returns matched schemes with reasons, without AI cost.
    """
    data = request.get_json(silent=True) or {}
    state = (data.get("state") or "").strip()

    profile = {
        "state": state,
        "crop": (data.get("crop") or "").strip(),
        "land_acres": (data.get("land_acres") or "").strip(),
        "farmer_type": (data.get("farmer_type") or "any").strip(),
    }

    matched = qualify_farmer(profile)

    profile_complete = bool(state) and state.lower() not in {
        "not specified", "india (general)", "all india / not sure", ""
    }

    return jsonify({
        "qualified_schemes": matched,
        "profile_complete": profile_complete,
        "total_matched": len(matched),
    })
