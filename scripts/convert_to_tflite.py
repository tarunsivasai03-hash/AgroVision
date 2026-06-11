"""Convert plant_disease_model.h5 to TFLite for the Android app."""
import argparse
import json
import os

os.environ["TF_CPP_MIN_LOG_LEVEL"] = "2"

import h5py
import tensorflow as tf

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DEFAULT_H5 = os.path.join(ROOT, "plant_disease_model.h5")
DEFAULT_OUT = os.path.join(ROOT, "android-app", "app", "src", "main", "assets", "plant_disease_model.tflite")


def _rebuild_model_from_weights(model_path, num_classes):
    input_shape = (112, 112, 3)
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
                        if all(isinstance(x, int) for x in (h, w, c)):
                            input_shape = (h, w, c)
                if layers and layers[-1].get("class_name") == "Dense":
                    units = (layers[-1].get("config") or {}).get("units")
                    if isinstance(units, int):
                        num_classes = units
    except Exception:
        pass

    inputs = tf.keras.Input(shape=input_shape)
    base = tf.keras.applications.MobileNetV2(
        include_top=False, weights=None, input_tensor=inputs, input_shape=input_shape
    )
    x = tf.keras.layers.GlobalAveragePooling2D()(base.output)
    activation = "sigmoid" if num_classes == 1 else "softmax"
    outputs = tf.keras.layers.Dense(num_classes, activation=activation)(x)
    model = tf.keras.Model(inputs=inputs, outputs=outputs)
    model.load_weights(model_path, by_name=True, skip_mismatch=True)
    return model


def convert_h5_to_tflite(h5_path, tflite_path):
    model = None
    num_classes = 38
    try:
        model = tf.keras.models.load_model(h5_path, compile=False)
    except Exception:
        model = _rebuild_model_from_weights(h5_path, num_classes)

    converter = tf.lite.TFLiteConverter.from_keras_model(model)
    tflite_model = converter.convert()
    os.makedirs(os.path.dirname(tflite_path), exist_ok=True)
    with open(tflite_path, "wb") as f:
        f.write(tflite_model)
    print(f"Saved: {tflite_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Convert plant_disease_model.h5 to TFLite")
    parser.add_argument("--h5", default=DEFAULT_H5, help="Source .h5 path")
    parser.add_argument("--out", default=DEFAULT_OUT, help="Output .tflite path")
    args = parser.parse_args()
    if not os.path.exists(args.h5):
        raise SystemExit(f"Model not found: {args.h5}")
    convert_h5_to_tflite(args.h5, args.out)
