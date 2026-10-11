"""
Disease detection service: model loading, prediction helpers, label/database access.
"""
import json
import logging
import os

import numpy as np

logger = logging.getLogger(__name__)

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_LABELS_PATH = os.path.join(_ROOT, "plant_disease_labels.json")
_DB_PATH = os.path.join(_ROOT, "disease_database.json")

with open(_LABELS_PATH, encoding="utf-8") as _labels_file:
    PLANT_DISEASE_CLASS_NAMES = json.load(_labels_file)

with open(_DB_PATH, encoding="utf-8") as _db_file:
    DISEASE_DATABASE = json.load(_db_file)

_missing_db = [label for label in PLANT_DISEASE_CLASS_NAMES if label not in DISEASE_DATABASE]
if _missing_db:
    raise RuntimeError(f"disease_database.json missing entries for: {_missing_db}")

# Minimum softmax confidence to accept a prediction
MIN_PREDICTION_CONFIDENCE = 0.15

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'webp'}

# --- Lazy-loaded ML model state ---
_plant_disease_model = None
_plant_disease_target_size = (112, 112)  # (width, height) — must match trained model
_plant_disease_classes = None  # Will be populated from model


def allowed_file(filename: str) -> bool:
    """Security check for file extension."""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def get_target_size():
    """Return current model target size (width, height)."""
    return _plant_disease_target_size


def get_plant_disease_classes():
    """Return model class names if extracted, else None."""
    return _plant_disease_classes


def lookup_disease_info(disease_key: str) -> dict:
    """Return cure/prevention/description for a model class label."""
    info = DISEASE_DATABASE.get(disease_key)
    if info:
        return info
    crop = disease_key.split("___")[0].replace(",", " ").replace("_", " ").strip().title()
    if "healthy" in disease_key.lower():
        return {
            "name": f"Healthy {crop}",
            "cure": "N/A",
            "prevention": f"Continue good care for {crop}: proper watering, balanced fertilizer, and regular scouting.",
            "description": f"No significant disease symptoms detected on this {crop} sample.",
        }
    return {
        "name": disease_key.replace("___", " → ").replace("_", " "),
        "cure": "Consult a local agronomist for crop-specific treatment.",
        "prevention": "Use certified seed, rotate crops, and remove infected plant debris.",
        "description": f"Detected condition: {disease_key.replace('___', ' ')}",
    }


def _rebuild_plant_disease_model_from_weights(model_path):
    """Rebuild plant disease model and load weights by name."""
    import h5py
    import tensorflow as tf

    # Infer input shape from saved config
    input_shape = (112, 112, 3)
    num_classes = len(PLANT_DISEASE_CLASS_NAMES)

    try:
        with h5py.File(model_path, "r") as f:
            mc = f.attrs.get("model_config")
            if mc is not None:
                mc = mc.decode("utf-8") if hasattr(mc, "decode") else mc
                data = json.loads(mc)
                layers = (data.get("config") or {}).get("layers") or []
                if layers and layers[0].get("class_name") == "InputLayer":
                    bs = (layers[0].get("config") or {}).get("batch_shape")
                    if isinstance(bs, list) and len(bs) == 4:
                        h, w, c = bs[1], bs[2], bs[3]
                        if isinstance(h, int) and isinstance(w, int) and isinstance(c, int):
                            input_shape = (h, w, c)

                # Try to infer number of classes from last layer
                if layers:
                    last_layer = layers[-1]
                    if last_layer.get("class_name") == "Dense":
                        units = (last_layer.get("config") or {}).get("units")
                        if isinstance(units, int):
                            num_classes = units
    except Exception as e:
        logger.warning(f"Could not fully infer model structure: {e}")

    # Default to common architecture if we can't infer
    if num_classes is None:
        num_classes = 38  # Common number for plant disease models

    inputs = tf.keras.Input(shape=input_shape)
    base = tf.keras.applications.MobileNetV2(
        include_top=False,
        weights=None,
        input_tensor=inputs,
        input_shape=input_shape
    )
    x = base.output
    x = tf.keras.layers.GlobalAveragePooling2D()(x)
    outputs = tf.keras.layers.Dense(num_classes, activation="softmax")(x)
    model = tf.keras.Model(inputs=inputs, outputs=outputs)

    try:
        model.load_weights(model_path, by_name=True, skip_mismatch=True)
    except Exception as e:
        logger.warning(f"Could not load weights by name: {e}")
        raise

    return model


def get_plant_disease_model():
    """Load and cache the plant disease model."""
    global _plant_disease_model, _plant_disease_target_size, _plant_disease_classes

    if _plant_disease_model is not None:
        return _plant_disease_model

    model_path = os.path.join(_ROOT, "plant_disease_model.h5")
    if not os.path.exists(model_path):
        raise FileNotFoundError(f"Plant disease model not found: {model_path}")

    import tensorflow as tf
    logger.info(f"Attempting to load disease model from: {model_path}")

    # Try direct load first
    try:
        model = tf.keras.models.load_model(
            model_path,
            compile=False,
            custom_objects={'MobileNetV2': tf.keras.applications.MobileNetV2}
        )
        logger.info("✅ Disease model loaded successfully!")
    except Exception as e:
        error_str = str(e)
        logger.warning(f"Direct load failed with: {error_str[:200]}")

        if 'Unknown argument' in error_str or 'name' in error_str.lower():
            try:
                logger.info("Attempting alternative loading method...")
                model = tf.keras.models.load_model(model_path, compile=True)
                logger.info("✅ Disease model loaded with compile=True!")
            except Exception as e2:
                logger.info("Falling back to weight-based rebuild...")
                try:
                    model = _rebuild_plant_disease_model_from_weights(model_path)
                    logger.info("✅ Disease model rebuilt successfully from weights!")
                except Exception as rebuild_error:
                    logger.error(f"Rebuild also failed: {str(rebuild_error)[:200]}")
                    raise Exception(f"Failed to load disease model via all methods. Last error: {str(rebuild_error)[:200]}")
        else:
            logger.info("Falling back to weight-based rebuild...")
            try:
                model = _rebuild_plant_disease_model_from_weights(model_path)
                logger.info("✅ Disease model rebuilt successfully from weights!")
            except Exception as rebuild_error:
                logger.error(f"Rebuild also failed: {str(rebuild_error)[:200]}")
                raise Exception(f"Failed to load disease model via both methods. Direct: {error_str[:100]}, Rebuild: {str(rebuild_error)[:100]}")

    # Infer target size
    try:
        input_shape = model.input_shape
        if isinstance(input_shape, list):
            input_shape = input_shape[0]
        h, w = input_shape[1], input_shape[2]
        if isinstance(h, int) and isinstance(w, int) and h > 0 and w > 0:
            _plant_disease_target_size = (w, h)
            logger.info(f"✅ Inferred disease model target size: {_plant_disease_target_size}")
    except Exception as e:
        logger.warning(f"Could not infer target size: {e}. Using default (112, 112)")
        _plant_disease_target_size = (112, 112)

    # Try to get class names from model
    try:
        output_shape = model.output_shape
        if isinstance(output_shape, list):
            output_shape = output_shape[0]
        num_classes = output_shape[-1] if output_shape else None
        logger.info(f"✅ Disease model has {num_classes} output classes")

        # Try to extract class names from model metadata if available
        try:
            if hasattr(model, 'class_names'):
                _plant_disease_classes = model.class_names
                logger.info(f"✅ Found class names in model: {len(_plant_disease_classes)} classes")
            elif hasattr(model, 'config') and 'class_names' in model.config:
                _plant_disease_classes = model.config['class_names']
                logger.info(f"✅ Found class names in model config: {len(_plant_disease_classes)} classes")
        except Exception as e:
            logger.warning(f"Could not extract class names from model: {e}")
    except Exception as e:
        logger.warning(f"Could not infer number of classes: {e}")

    _plant_disease_model = model
    logger.info(f"✅ Plant disease model ready. Target size: {_plant_disease_target_size}")
    return _plant_disease_model
