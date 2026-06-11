# Security

## API keys

- Store `GEMINI_API_KEY` only in `.env` (see `.env.example`).
- `.env` is gitignored — do not force-add or commit it.
- Never paste API keys into `app.py`, templates, or Android source.

## If a key was exposed

1. Revoke or regenerate the key in [Google AI Studio](https://aistudio.google.com/apikey).
2. Update `.env` with the new key.
3. If the key was pushed to GitHub, treat it as compromised even after deletion from history.

## Android chat

The app calls your Flask server (`/api/chat`); the Gemini key stays on the server, not in the APK.
