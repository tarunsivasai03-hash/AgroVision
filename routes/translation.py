"""
Translation blueprint: /api/translate-page
"""
import logging

from flask import Blueprint, request, jsonify

from extensions import limiter, TRANSLATE_LIMIT
from services.gemini import translate_texts_with_gemini

logger = logging.getLogger(__name__)

translation_bp = Blueprint("translation", __name__, url_prefix="/api")


@translation_bp.route("/translate-page", methods=["POST"])
@limiter.limit(TRANSLATE_LIMIT)
def translate_page():
    """Translate visible page strings with Gemini for any requested language."""
    try:
        data = request.get_json(silent=True) or {}
        target_language = (data.get("target_language") or "").strip()
        texts = data.get("texts") or []

        if not target_language:
            return jsonify({"error": "target_language is required"}), 400
        if not isinstance(texts, list) or not texts:
            return jsonify({"error": "texts must be a non-empty list"}), 400

        clean_texts = [str(t).strip() for t in texts if str(t).strip()]
        if len(clean_texts) != len(texts):
            return jsonify({"error": "texts cannot contain empty values"}), 400
        if len(clean_texts) > 160:
            return jsonify({"error": "Too many strings. Send at most 160 at once."}), 400
        if sum(len(t) for t in clean_texts) > 12000:
            return jsonify({"error": "Translation payload is too large."}), 400

        translations = translate_texts_with_gemini(clean_texts, target_language)
        return jsonify({
            "target_language": target_language,
            "translations": translations,
            "ai_powered": True,
        })
    except Exception as exc:
        logger.error(f"Page translation error: {exc}")
        return jsonify({"error": "Translation is unavailable right now.", "ai_powered": False}), 503
