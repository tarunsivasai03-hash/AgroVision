"""
Shared Flask extensions, created here so blueprints can import them
without a circular import on app.py.
"""
import os

from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

# Per-client-IP limits, applied only to the expensive endpoints (no default
# limit, so page loads and static files are never throttled). In-memory storage is fine for a single process;
# set RATELIMIT_STORAGE_URI (e.g. redis://...) when running several workers.
limiter = Limiter(
    key_func=get_remote_address,
    storage_uri=os.environ.get("RATELIMIT_STORAGE_URI", "memory://"),
)

# Limits for endpoints that cost money (Gemini) or heavy compute (TensorFlow).
AI_LIMIT = os.environ.get("AI_RATE_LIMIT", "10 per minute;100 per day")
# One page can need several translation batches, so this is looser.
TRANSLATE_LIMIT = os.environ.get("TRANSLATE_RATE_LIMIT", "30 per minute;500 per day")
PREDICT_LIMIT = os.environ.get("PREDICT_RATE_LIMIT", "10 per minute")
