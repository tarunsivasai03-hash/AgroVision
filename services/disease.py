"""
Disease detection service: model loading, prediction helpers, label/database access.
"""
import json
import logging
import os
import threading

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

# --- Which crops the model covers, and how well ---------------------------------
# The model was trained on a fixed list of crop/disease classes ("Tomato___Early_blight").
# Everything below is derived from that label file, so it follows the labels if the
# model is ever retrained with more crops or classes.

def _crop_key(label: str) -> str:
    base = label.split("___")[0]
    return "bell_pepper" if base == "Pepper,bell" else base.lower().replace(" ", "_")


CROP_OF_CLASS = [_crop_key(label) for label in PLANT_DISEASE_CLASS_NAMES]
CROP_CLASSES = {}  # crop key -> indices of that crop's classes
for _index, _crop in enumerate(CROP_OF_CLASS):
    CROP_CLASSES.setdefault(_crop, []).append(_index)
CROP_KEYS = tuple(CROP_CLASSES)

# A crop can only be diagnosed if the model has seen at least two outcomes for it.
# Blueberry, raspberry and soybean have a single "healthy" class (any leaf is
# "healthy"); orange and squash have a single disease class (any leaf has it).
# For those the answer never depends on the photo, so it would mislead.
DIAGNOSABLE_CROPS = frozenset(c for c, idx in CROP_CLASSES.items() if len(idx) >= 2)


def crop_name(crop: str) -> str:
    """Plain-language crop name for messages, e.g. "bell pepper"."""
    return crop.replace("_", " ")


# Minimum softmax confidence to accept a prediction. With 38 classes a uniform
# guess is ~0.03, so anything below this is treated as "uncertain".
MIN_PREDICTION_CONFIDENCE = float(os.environ.get("MIN_PREDICTION_CONFIDENCE", "0.5"))

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'webp'}

# --- Lazy-loaded ML model state ---
_plant_disease_model = None
_plant_disease_target_size = (112, 112)  # (width, height) — must match trained model
_model_lock = threading.Lock()


def allowed_file(filename: str) -> bool:
    """Security check for file extension."""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def get_target_size():
    """Return current model target size (width, height)."""
    return _plant_disease_target_size


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


def _input_shape_from_h5(model_path):
    """Read the input shape from the saved model config, defaulting to 112x112x3."""
    import h5py

    try:
        with h5py.File(model_path, "r") as f:
            config = f.attrs.get("model_config")
            if config is None:
                return (112, 112, 3)
            config = config.decode("utf-8") if hasattr(config, "decode") else config
            layers = (json.loads(config).get("config") or {}).get("layers") or []
            if layers and layers[0].get("class_name") == "InputLayer":
                shape = (layers[0].get("config") or {}).get("batch_shape")
                if isinstance(shape, list) and len(shape) == 4 and all(isinstance(v, int) for v in shape[1:]):
                    return tuple(shape[1:])
    except Exception as e:
        logger.warning(f"Could not read input shape from model file: {e}")
    return (112, 112, 3)


def _rebuild_plant_disease_model_from_weights(model_path):
    """
    Rebuild the MobileNetV2 classifier and load weights strictly.

    Used only when the saved architecture cannot be deserialised (e.g. a Keras
    version mismatch). Any layer mismatch raises instead of silently leaving
    random weights, which would produce confident garbage predictions.
    """
    import tensorflow as tf

    input_shape = _input_shape_from_h5(model_path)
    inputs = tf.keras.Input(shape=input_shape)
    base = tf.keras.applications.MobileNetV2(include_top=False, weights=None, input_tensor=inputs)
    x = tf.keras.layers.GlobalAveragePooling2D()(base.output)
    outputs = tf.keras.layers.Dense(len(PLANT_DISEASE_CLASS_NAMES), activation="softmax")(x)
    model = tf.keras.Model(inputs=inputs, outputs=outputs)
    model.load_weights(model_path)
    return model


def _load_model_from_disk(model_path):
    import tensorflow as tf

    try:
        return tf.keras.models.load_model(model_path, compile=False)
    except Exception as e:
        logger.warning(f"Direct model load failed ({str(e)[:200]}); rebuilding from weights.")
    try:
        return _rebuild_plant_disease_model_from_weights(model_path)
    except Exception as e:
        raise RuntimeError(f"Could not load plant disease model: {str(e)[:200]}") from e


def get_plant_disease_model():
    """Load (once, thread-safely) and cache the plant disease model."""
    global _plant_disease_model, _plant_disease_target_size

    if _plant_disease_model is not None:
        return _plant_disease_model

    with _model_lock:
        if _plant_disease_model is not None:
            return _plant_disease_model

        model_path = os.path.join(_ROOT, "plant_disease_model.h5")
        if not os.path.exists(model_path):
            raise FileNotFoundError(f"Plant disease model not found: {model_path}")

        logger.info(f"Loading disease model from: {model_path}")
        model = _load_model_from_disk(model_path)

        output_shape = model.output_shape[0] if isinstance(model.output_shape, list) else model.output_shape
        if output_shape[-1] != len(PLANT_DISEASE_CLASS_NAMES):
            raise RuntimeError(
                f"Model has {output_shape[-1]} output classes but plant_disease_labels.json "
                f"has {len(PLANT_DISEASE_CLASS_NAMES)} labels."
            )

        input_shape = model.input_shape[0] if isinstance(model.input_shape, list) else model.input_shape
        h, w = input_shape[1], input_shape[2]
        if isinstance(h, int) and isinstance(w, int) and h > 0 and w > 0:
            _plant_disease_target_size = (w, h)

        _plant_disease_model = model
        logger.info(f"Plant disease model ready. Target size: {_plant_disease_target_size}")
        return _plant_disease_model
