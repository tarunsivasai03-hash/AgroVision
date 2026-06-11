"""
Pages blueprint: HTML template routes, health check, and weather API.
"""
import logging
import os

from flask import Blueprint, render_template, request, jsonify

from services.weather import fetch_openweather
from services.disease import PLANT_DISEASE_CLASS_NAMES, DISEASE_DATABASE, get_target_size
from services.schemes_data import get_government_schemes

logger = logging.getLogger(__name__)

pages_bp = Blueprint("pages", __name__)


# --- HTML page routes ---

@pages_bp.route("/")
def home():
    return render_template("index.html")


@pages_bp.route("/detect")
def detect():
    return render_template("detect.html")


@pages_bp.route("/schemes")
def schemes():
    return render_template("schemes.html")


@pages_bp.route("/weather")
def weather():
    return render_template("weather.html")


@pages_bp.route("/voice")
def voice():
    return render_template("voice.html")


@pages_bp.route("/chatbot")
def chatbot():
    return render_template("chatbot.html")


# --- API: Health check ---

@pages_bp.route("/api/health")
def health():
    """Health check for monitoring and integration tests."""
    _ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    model_ok = os.path.exists(os.path.join(_ROOT, "plant_disease_model.h5"))
    chat_ok = bool(os.environ.get("GEMINI_API_KEY", "").strip())
    return jsonify({
        "status": "ok",
        "model_file_present": model_ok,
        "disease_classes": len(PLANT_DISEASE_CLASS_NAMES),
        "disease_database_entries": len(DISEASE_DATABASE),
        "chat_configured": chat_ok,
        "schemes_count": len(get_government_schemes()),
        "input_size": list(get_target_size()),
    })


# --- API: Weather ---

@pages_bp.route("/api/weather", methods=["GET"])
def api_weather():
    location = (request.args.get("location") or "India").strip()
    if not location:
        return jsonify({"error": "location query parameter is required."}), 400
    try:
        weather_data = fetch_openweather(location)
        return jsonify({"weather": weather_data})
    except Exception as exc:
        logger.error(f"Weather API error: {exc}")
        return jsonify({"error": str(exc)}), 400
