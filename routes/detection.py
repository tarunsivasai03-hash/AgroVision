"""
Disease detection blueprint: /predict
"""
import logging
import os
from datetime import datetime

import numpy as np
from flask import Blueprint, request, jsonify, current_app
from werkzeug.utils import secure_filename
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

        # 2. Secure Save
        filename = secure_filename(f"{datetime.now().strftime('%H%M%S')}_{file.filename}")
        file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
        file.save(file_path)

        logger.info(f"File saved: {file_path}")

        # 3. Load Disease Model & Preprocess
        logger.info("Loading disease model...")
        model = get_plant_disease_model()
        target_size = get_target_size()
        logger.info(f"Disease model loaded. Target size: {target_size}")

        # Preprocess image from disk
        logger.info(f"Preprocessing image: {file_path}")
        try:
            pil_image = Image.open(file_path).convert("RGB")
            pil_image = pil_image.resize(target_size)
            img_array = np.asarray(pil_image, dtype=np.float32) / 255.0
            img_array = np.expand_dims(img_array, axis=0)
            logger.info(f"Image preprocessed. Shape: {img_array.shape}")
        except Exception as e:
            logger.error(f"Image preprocessing failed: {e}")
            return jsonify({"error": "Image processing failed", "details": str(e)}), 400

        # 4. Prediction
        logger.info("Running disease prediction...")
        try:
            pred = model.predict(img_array, verbose=0)
            logger.info(f"Prediction raw output shape: {pred.shape}")
        except Exception as e:
            logger.error(f"Prediction failed: {e}")
            return jsonify({"error": "Prediction failed", "details": str(e)}), 500

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
            return jsonify({
                "error": "Unsupported model output",
                "details": f"Expected multi-class softmax, got {len(pred)} output(s)."
            }), 500

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
        logger.error(f"Prediction Error: {e}")
        return jsonify({"error": "Internal Server Error", "details": str(e)}), 500
