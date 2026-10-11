# AgroVision - Setup and troubleshooting

See `README.md` for what the project does and how the leaf scan decides. This guide covers installing and fixing problems.

## 1. Install

Python 3.11 or newer. From the project folder:

```bash
pip install -r requirements.txt
```

`requirements.txt` pins the tested versions (Flask, TensorFlow, Pillow, Flask-Limiter and others). Gemini is called directly over HTTPS, so no Google SDK is needed.

## 2. Configure

```bash
copy .env.example .env
```

Set at least `GEMINI_API_KEY` (from [Google AI Studio](https://aistudio.google.com/apikey)). Optional: `OPENWEATHER_API_KEY` for real weather. All settings are listed in `.env.example`. Restart the server after editing `.env`.

## 3. Run

```bash
python app.py
```

Or double-click `START_SERVER.bat`. Open http://127.0.0.1:5000. Pages: `/` home, `/detect` leaf scan, `/schemes`, `/weather`, `/voice` phone helpline, `/chatbot`.

The server listens on `127.0.0.1` only. To let a phone on your Wi-Fi reach it, start it with `FLASK_HOST=0.0.0.0` (PowerShell: `$env:FLASK_HOST="0.0.0.0"; python app.py`). For production use a real server, for example `waitress-serve --listen=0.0.0.0:5000 app:app`.

## 4. Check it works

```bash
python -m pytest tests -q
```

or double-click `run_tests.bat`. Visit http://127.0.0.1:5000/api/health to see the model, the photo-check mode and the list of diagnosable crops.

## Troubleshooting

**The leaf scan says "Can't check this photo right now".** The default `LEAF_CHECK=required` refuses scans when the Gemini photo check cannot run. Check that `GEMINI_API_KEY` is set and valid, that the machine is online, and the Gemini quota (below). `LEAF_CHECK=optional` shows the model's answer marked "not verified" instead; `LEAF_CHECK=off` never contacts Gemini. Both are less safe, because the model alone cannot tell a leaf from fruit.

**Chat, scheme guides or translation fall back to canned text, or fail.** Usually the Gemini free quota (about 20 requests per day per model) is used up. The log shows `HTTP 429`. AgroVision then tries `gemini-flash-latest` and `gemini-flash-lite-latest`. If all are used up, wait for the daily reset or enable billing. Do not set `GEMINI_MODEL` to a retired name such as `gemini-2.0-flash` (it answers 404). Use `gemini-flash-latest`.

**Gemini or `git` fails with a certificate error on Windows.** Some antivirus or network software inspects HTTPS. AgroVision calls Gemini with Python's standard library, which uses the Windows certificate store, and usually works. For git, try `git -c http.sslBackend=schannel push`.

**Module not found.** `pip install -r requirements.txt` again, in the same Python you run the app with.

**Model file not found.** `plant_disease_model.h5` must be in the project root.

**Port 5000 in use.** Start with `PORT=5001` (PowerShell: `$env:PORT="5001"; python app.py`).

**Weather shows "Sample data".** `OPENWEATHER_API_KEY` is missing or invalid, or the place name was not found.

**A page changes language slowly the first time.** Translations come from Gemini and are then cached in `instance/translation_cache.json`, so later visits are instant. Text that could not be translated stays in English.

## Notes

- Uploaded photos are never saved. They are analysed in memory.
- The first scan after starting the server is slower while the model loads.
- Android: see the Android section of `README.md`. The app scans on the phone without the photo check.
