"""
Shared translation cache.

Page text is translated by Gemini, but each (language, text) pair only needs translating
once for every visitor. Translations are kept in memory and written to a JSON file, so they
survive restarts and keep working when Gemini is down or over quota.
Only translations that pass is_valid_translation() are ever stored.
"""
import json
import logging
import os
import re
import threading

logger = logging.getLogger(__name__)

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MAX_ENTRIES = 50000
_SEPARATOR = "\x1f"
_DIGITS = re.compile(r"\d+")
_PLACEHOLDERS = re.compile(r"\{[^{}]*\}")

_lock = threading.Lock()
_entries = None  # loaded lazily from disk


def cache_path() -> str:
    return os.environ.get("TRANSLATION_CACHE_PATH") or os.path.join(_ROOT, "instance", "translation_cache.json")


def is_valid_translation(source: str, translated) -> bool:
    """Reject empty, runaway or number-changing translations, which would show farmers wrong text."""
    if not isinstance(translated, str) or not translated.strip():
        return False
    if len(translated) > max(60, 6 * len(source)):
        return False
    if not set(_DIGITS.findall(source)) <= set(_DIGITS.findall(translated)):
        return False  # a phone number, price or date changed
    return set(_PLACEHOLDERS.findall(source)) <= set(_PLACEHOLDERS.findall(translated))


def _load():
    global _entries
    if _entries is None:
        try:
            with open(cache_path(), encoding="utf-8") as f:
                data = json.load(f)
            _entries = data if isinstance(data, dict) else {}
        except (OSError, ValueError):
            _entries = {}
    return _entries


def _save(entries):
    path = cache_path()
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        tmp = path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(entries, f, ensure_ascii=False)
        os.replace(tmp, path)
    except OSError as exc:
        logger.warning(f"Could not save the translation cache: {exc}")


def _key(language: str, text: str) -> str:
    return language.strip().lower() + _SEPARATOR + text


def get_many(language: str, texts) -> dict:
    """{text: translation} for the texts that are already cached."""
    with _lock:
        entries = _load()
        return {t: entries[_key(language, t)] for t in texts if _key(language, t) in entries}


def put_many(language: str, pairs: dict):
    """Store {text: translation}; invalid translations are skipped. Returns how many were stored."""
    good = {t: v for t, v in pairs.items() if is_valid_translation(t, v)}
    if not good:
        return 0
    with _lock:
        entries = _load()
        for text, translated in good.items():
            entries[_key(language, text)] = translated
        while len(entries) > MAX_ENTRIES:
            entries.pop(next(iter(entries)))  # oldest first
        _save(entries)
    return len(good)


def clear_memory():
    """Forget the in-memory copy (the next call reloads the file). Used by tests."""
    global _entries
    with _lock:
        _entries = None
