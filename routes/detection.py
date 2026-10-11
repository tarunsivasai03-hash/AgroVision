"""
Disease detection blueprint: /api/predict (and the legacy /predict)

The route only validates the upload. Photos are analysed in memory and never stored. Everything that decides what to tell the
farmer lives in services/scan.py.
"""
import logging

from flask import Blueprint, request, jsonify
from PIL import Image

from extensions import limiter, PREDICT_LIMIT
from services.disease import allowed_file
from services.scan import analyze_photo

logger = logging.getLogger(__name__)

detection_bp = Blueprint("detection", __name__)


# Image formats accepted, detected from the file content rather than its name.
IMAGE_FORMATS = ("JPEG", "PNG", "WEBP")


@detection_bp.route("/api/predict", methods=["POST"])
@detection_bp.route("/predict", methods=["POST"])  # legacy path, kept for existing clients
@limiter.limit(PREDICT_LIMIT)
def predict():
    """
    Receives a leaf photo and returns JSON: either {"status": "ok", ...} with a result to show
    as a hint, or {"status": "rejected", "reason": ..., "headline": ..., "message": ...} when the
    scan should not name a disease (see services/scan.py for the reasons).
    """
    try:
        # 1. Validation
        if 'image' not in request.files:
            return jsonify({"error": "No file part"}), 400

        file = request.files['image']

        if file.filename == '':
            return jsonify({"error": "No selected file"}), 400

        if not allowed_file(file.filename):
            return jsonify({"error": "Invalid file type. Use JPG, PNG or WEBP."}), 400

        # 2. Validate the image content before touching disk
        try:
            probe = Image.open(file.stream)
            image_format = probe.format
            probe.verify()
            file.stream.seek(0)
            pil_image = Image.open(file.stream)
            pil_image.load()  # keeps EXIF, so the phone's rotation can be applied later
        except Exception as e:
            logger.error(f"Image validation failed: {e}")
            return jsonify({"error": "Invalid or corrupted image file."}), 400
        if image_format not in IMAGE_FORMATS:
            return jsonify({"error": "Invalid file type. Use JPG, PNG or WEBP."}), 400

        # 3. Analyse (in memory; nothing is written to disk)
        result = analyze_photo(pil_image)
        logger.info(f"Scan: {result['status']} {result.get('reason') or result.get('class_id')}")
        return jsonify(result)

    except Exception:
        logger.exception("Prediction Error")
        return jsonify({"error": "Internal Server Error"}), 500
