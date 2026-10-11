"""
Disease detection blueprint: /predict
"""
import logging
import os
import time
import uuid

import numpy as np
from flask import Blueprint, request, jsonify, current_app
from PIL import Image

from services.disease import (
    allowed_file,
    get_plant_disease_model,
    get_target_size,
    get_plant_disease_classes,
    PLANT_DISEASE_CLASS_NAMES,
    lookup_disease_info,
    MIN_PREDICTION_CONFIDENCE,
)

logger = logging.getLogger(__name__)

detection_bp = Blueprint("detection", __name__)


UPLOAD_MAX_AGE_SECONDS = 24 * 3600


def _cleanup_old_uploads(folder):
    """Delete uploaded images older than 24h so the folder cannot grow forever."""
    cutoff = time.time() - UPLOAD_MAX_AGE_SECONDS
    try:
        for name in os.listdir(folder):
            path = os.path.join(folder, name)
            if name != ".gitkeep" and os.path.isfile(path) and os.path.getmtime(path) < cutoff:
                os.remove(path)
    except OSError as e:
        logger.warning(f"Upload cleanup failed: {e}")


@detection_bp.route("/predict", methods=["POST"])
def predict():
    """
    API Endpoint: Receives image -> Returns JSON Result
    """
    try:
        # 1. Validation
        if 'image' not in request.files:
            return jsonify({"error": "No file part"}), 400

        file = request.files['image']

        if file.filename == '':
            return jsonify({"error": "No selected file"}), 400

        if not allowed_file(file.filename):
            return jsonify({"error": "Invalid file type. Use JPG/PNG."}), 400

        # 2. Validate the image content before touching disk
        try:
            pil_image = Image.open(file.stream)
            pil_image.verify()
            file.stream.seek(0)
            pil_image = Image.open(file.stream).convert("RGB")
        except Exception as e:
            logger.error(f"Image validation failed: {e}")
            return jsonify({"error": "Invalid or corrupted image file."}), 400

        # 3. Secure save with an unguessable, collision-free name
        ext = file.filename.rsplit('.', 1)[1].lower()
        filename = f"{uuid.uuid4().hex}.{ext}"
        file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
        _cleanup_old_uploads(current_app.config['UPLOAD_FOLDER'])
        pil_image.save(file_path)
        logger.info(f"File saved: {file_path}")

        model = get_plant_disease_model()
        target_size = get_target_size()
        pil_image = pil_image.resize(target_size)
        img_array = np.asarray(pil_image, dtype=np.float32) / 255.0
        img_array = np.expand_dims(img_array, axis=0)

        # 4. Prediction
        logger.info("Running disease prediction...")
        try:
            pred = model.predict(img_array, verbose=0)
            logger.info(f"Prediction raw output shape: {pred.shape}")
        except Exception as e:
            logger.error(f"Prediction failed: {e}")
            return jsonify({"error": "Prediction failed"}), 500

        # Handle prediction output
        if isinstance(pred, list):
            pred = np.array(pred)

        pred = np.array(pred).flatten()

        # Check if it's a multi-class model (softmax) or binary (sigmoid)
        if len(pred) > 1:
            # Multi-class model - get the class with highest probability
            predicted_class_idx = int(np.argmax(pred))
            confidence = float(pred[predicted_class_idx])
            logger.info(f"Predicted class index: {predicted_class_idx}, Confidence: {confidence}")

            # Map class index to disease name
            disease_classes = get_plant_disease_classes()
            if disease_classes is not None and predicted_class_idx < len(disease_classes):
                disease_key = disease_classes[predicted_class_idx]
                logger.info(f"Using class name from model: {disease_key}")
            elif predicted_class_idx < len(PLANT_DISEASE_CLASS_NAMES):
                disease_key = PLANT_DISEASE_CLASS_NAMES[predicted_class_idx]
            else:
                disease_key = f"Class_{predicted_class_idx}"
                logger.warning(f"Class index {predicted_class_idx} out of range")

            if confidence < MIN_PREDICTION_CONFIDENCE:
                return jsonify({
                    "label": "Uncertain",
                    "confidence": round(confidence, 2),
                    "disease": "Unclear image",
                    "cure": "N/A",
                    "prevention": "Upload a clear, well-lit close-up of a single plant leaf filling most of the frame.",
                    "description": (
                        "The model could not classify this image confidently. "
                        "Ensure the photo shows plant foliage, not soil, tools, or non-plant objects."
                    ),
                    "image_url": f"/static/uploads/{filename}",
                    "is_plant": False,
                })

            disease_info = lookup_disease_info(disease_key)
            disease_name = disease_info.get("name", disease_key.replace("___", " ").replace("_", " "))
            label = "Healthy" if "healthy" in disease_key.lower() else "Diseased"

            extra_data = {
                "disease": disease_name,
                "cure": disease_info.get("cure", "N/A"),
                "prevention": disease_info.get("prevention", "N/A"),
                "description": disease_info.get("description", f"Detected disease: {disease_name}")
            }

        else:
            logger.error(f"Unsupported model output: {len(pred)} output(s)")
            return jsonify({"error": "Unsupported model output"}), 500

        # 5. Return JSON Response
        response = {
            "label": label,
            "confidence": round(confidence, 2),
            **extra_data,
            "image_url": f"/static/uploads/{filename}",
            "is_plant": True,
            "class_id": disease_key,
        }

        logger.info(f"Returning response: {response}")
        return jsonify(response)

    except Exception as e:
        logger.exception("Prediction Error")
        return jsonify({"error": "Internal Server Error"}), 500
