import os
import logging
from flask import Flask, jsonify
from flask_cors import CORS

# Import blueprints
from routes.pages import pages_bp
from routes.assistant import assistant_bp
from routes.schemes import schemes_bp
from routes.detection import detection_bp
from routes.translation import translation_bp

def create_app():
    # --- CONFIGURATION ---
    app = Flask(__name__)

    # Enable CORS for frontend-backend communication
    CORS(app)

    # Configuration
    app.config["UPLOAD_FOLDER"] = "static/uploads"
    app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024  # 16MB Limit
    app.config["ALLOWED_EXTENSIONS"] = {'png', 'jpg', 'jpeg', 'webp'}

    # Setup Logging
    logging.basicConfig(level=logging.INFO)
    logger = app.logger
    logger.info("GEMINI_API_KEY will be accepted from request payloads or environment.")
    logger.info(f"GEMINI_MODEL configured: {os.environ.get('GEMINI_MODEL', 'gemini-1.0')}")

    # Ensure upload directory exists
    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

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

    @app.errorhandler(404)
    def page_not_found(error):
        from flask import render_template
        return render_template("index.html"), 404
        
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
    app.run(debug=True, host='0.0.0.0', port=5000)
