# AgroVision Android App (Offline AI)

Native Kotlin app using **TensorFlow Lite** for on-device plant disease detection.

## Setup

1. Ensure `plant_disease_model.tflite` is in `app/src/main/assets/` (generated from the root `.h5` model).
2. From the project root, convert the model if needed:
   ```bash
   python scripts/convert_to_tflite.py
   ```
3. Open `android-app` in Android Studio, sync Gradle, and run on a device or emulator.

## Features

- **Offline** disease inference with `plant_disease_model.tflite` (112×112, 38 classes)
- **Online AI chat** — calls the same Flask `/api/chat` + Gemini as the website (not keyword rules)
- Photo picker and camera capture
- Government schemes list, TTS, and multi-language UI (EN / HI / TE)

Chat requires the Flask server running on your PC and `GEMINI_API_KEY` in the project `.env` file.
