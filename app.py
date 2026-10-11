import os
import logging
from dotenv import load_dotenv

load_dotenv()

from flask import Flask, jsonify, render_template, request
from flask_cors import CORS

from extensions import limiter
from services.gemini import DEFAULT_MODEL

# Import blueprints
from routes.pages import pages_bp
from routes.assistant import assistant_bp
from routes.schemes import schemes_bp
from routes.detection import detection_bp
from routes.translation import translation_bp

def create_app():
    # --- CONFIGURATION ---
    app = Flask(__name__)

    # The web UI is same-origin and the Android app is not subject to CORS, so
    # cross-origin API access is off unless origins are listed explicitly,
    # e.g. CORS_ORIGINS=https://example.com,https://admin.example.com
    cors_origins = [o.strip() for o in os.environ.get("CORS_ORIGINS", "").split(",") if o.strip()]
    if cors_origins:
        CORS(app, resources={r"/api/*": {"origins": cors_origins}})

    limiter.init_app(app)

    # Configuration
    app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024  # 16MB Limit
    app.config["ALLOWED_EXTENSIONS"] = {'png', 'jpg', 'jpeg', 'webp'}

    # Setup Logging
    logging.basicConfig(level=logging.INFO)
    logger = app.logger
    if not os.environ.get("GEMINI_API_KEY", "").strip():
        logger.warning("GEMINI_API_KEY is not set; AI features will use offline fallback text.")
    logger.info(f"GEMINI_MODEL configured: {os.environ.get('GEMINI_MODEL', DEFAULT_MODEL)}")

    # --- REGISTER BLUEPRINTS ---
    app.register_blueprint(pages_bp)
    app.register_blueprint(assistant_bp)
    app.register_blueprint(schemes_bp)
    app.register_blueprint(detection_bp)
    app.register_blueprint(translation_bp)

    # --- ERROR HANDLERS ---
    @app.errorhandler(413)
    def request_entity_too_large(error):
        return jsonify({"error": "File too large (Max 16MB)"}), 413

    @app.errorhandler(429)
    def too_many_requests(error):
        return jsonify({"error": "Too many requests. Please wait a minute and try again."}), 429

    def _is_api_request():
        return request.path.startswith("/api/") or request.path == "/predict"

    @app.errorhandler(404)
    def page_not_found(error):
        if _is_api_request():
            return jsonify({"error": "Not found"}), 404
        return render_template("index.html"), 404

    @app.errorhandler(405)
    def method_not_allowed(error):
        if _is_api_request():
            return jsonify({"error": "Method not allowed"}), 405
        return error

    return app

app = create_app()

if __name__ == "__main__":
    # Enable debug for development, set to False in production
    print("=" * 50)
    print("AgroVision - Starting Server")
    print("=" * 50)
    print("Server running at: http://127.0.0.1:5000")
    print("Disease Detection: http://127.0.0.1:5000/detect")
    print("Government Schemes: http://127.0.0.1:5000/schemes")
    print("Chatbot: http://127.0.0.1:5000/chatbot")
    print("=" * 50)
    app.run(
        debug=os.environ.get('FLASK_DEBUG', '0') == '1',
        host=os.environ.get('FLASK_HOST', '127.0.0.1'),
        port=int(os.environ.get('PORT', '5000')),
    )
