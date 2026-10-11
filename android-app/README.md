# AgroVision Android app

Native Kotlin app. It checks a leaf photo on the phone with a **TensorFlow Lite** model and uses the AgroVision server for schemes and the chat assistant.

## Run it

1. Make sure `app/src/main/assets/plant_disease_model.tflite` exists. If you changed the `.h5` model, make a new one from the project root:
   ```bash
   python scripts/convert_to_tflite.py
   ```
2. Open the `android-app` folder in Android Studio and wait for Gradle to sync.
3. Run on an emulator or a phone.

The Schemes and Ask tabs need the server (`python app.py` in the project root):

- **Emulator:** nothing to change. The app reaches your PC at `http://10.0.2.2:5000`.
- **Phone on the same Wi-Fi:** set `api_base_url` in `app/src/main/res/values/config.xml` to your PC's address (for example `http://192.168.0.15:5000`) and start the server with `FLASK_HOST=0.0.0.0`.

## Screens

| Tab | What it does |
|-----|--------------|
| Leaf | Take or choose a photo, check it on the phone, read the result aloud. Works offline. |
| Schemes | Government schemes from the server, a "describe your farm" advisor, and an "Explain simply" button on every scheme. |
| Helpline | One-tap call to the helpline number. |
| Ask | Chat with the same Gemini assistant as the website, with starter questions. |

The language button (top right) switches between English, Hindi and Telugu and is remembered. The look follows the system light or dark setting and uses the website's colours.

## How far to trust the leaf check

The model was trained on clean lab photos and is often wrong on field photos. The app therefore:

- shows a weak answer as **Not sure**, and never shows a percentage;
- refuses crops the model knows only one condition for (it cannot tell healthy from sick for those);
- labels every answer a hint and lists other possibilities.

It does **not** have the website's extra checks (a photo check that the right crop is in view), because those need Gemini.

## Technical notes

- Input is resized the same way as the website: shrink large photos to 256 px smoothly, then nearest-neighbour to 112 px, then divide by 255. Camera photos are rotated upright from their EXIF data first.
- `plant_disease_labels.json` must match the website's copy exactly (a test on the server side checks the order).
- Photos stay on the phone.
