# Models

The active disease model lives at the project root:

- `plant_disease_model.h5` — Flask backend (`/predict`)
- `android-app/app/src/main/assets/plant_disease_model.tflite` — Android offline inference

Regenerate TFLite after updating the H5 file:

```bash
python scripts/convert_to_tflite.py
```
