"""Tests for the shared translation cache and the cached translate_texts_with_gemini."""
import json
import os
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services import gemini, translation_cache as cache


class _CacheCase(unittest.TestCase):
  def setUp(self):
    self.dir = tempfile.TemporaryDirectory()
    self.path = os.path.join(self.dir.name, "sub", "cache.json")
    env = patch.dict(os.environ, {"TRANSLATION_CACHE_PATH": self.path})
    env.start()
    self.addCleanup(env.stop)
    self.addCleanup(self.dir.cleanup)
    cache.clear_memory()
    self.addCleanup(cache.clear_memory)


class ValidationTest(unittest.TestCase):
  def test_accepts_normal_translations(self):
    self.assertTrue(cache.is_valid_translation("Call 1800-123-4567 now", "अभी 1800-123-4567 पर कॉल करें"))
    self.assertTrue(cache.is_valid_translation("Hello {name}", "नमस्ते {name}"))

  def test_rejects_bad_translations(self):
    bad = [
      ("Hello", ""), ("Hello", "   "), ("Hello", None), ("Hello", 5),
      ("Hello", "x" * 500),                       # runaway output
      ("Call 1800-123-4567", "कॉल करें"),          # number dropped
      ("Pay Rs 6000", "भुगतान 7000"),              # number changed
      ("Hello {name}", "नमस्ते"),                  # placeholder dropped
    ]
    for source, out in bad:
      self.assertFalse(cache.is_valid_translation(source, out), (source, out))


class CacheStorageTest(_CacheCase):
  def test_round_trip_and_persistence_across_restarts(self):
    self.assertEqual(cache.put_many("Hindi", {"Home": "मुख्य पृष्ठ", "Weather": "मौसम"}), 2)
    self.assertEqual(cache.get_many("hindi", ["Home", "Other"]), {"Home": "मुख्य पृष्ठ"})  # language is case-insensitive
    cache.clear_memory()  # a new process would start with nothing in memory
    self.assertEqual(cache.get_many("Hindi", ["Weather"]), {"Weather": "मौसम"})
    with open(self.path, encoding="utf-8") as f:
      self.assertEqual(len(json.load(f)), 2)

  def test_languages_do_not_mix(self):
    cache.put_many("Hindi", {"Home": "मुख्य पृष्ठ"})
    self.assertEqual(cache.get_many("Telugu", ["Home"]), {})

  def test_invalid_translations_are_not_stored(self):
    self.assertEqual(cache.put_many("Hindi", {"Call 1800": "कॉल", "Home": ""}), 0)
    self.assertFalse(os.path.exists(self.path))

  def test_corrupt_file_is_ignored(self):
    os.makedirs(os.path.dirname(self.path))
    with open(self.path, "w", encoding="utf-8") as f:
      f.write("{not json")
    self.assertEqual(cache.get_many("Hindi", ["Home"]), {})
    self.assertEqual(cache.put_many("Hindi", {"Home": "घर"}), 1)


class TranslateWithCacheTest(_CacheCase):
  def _gemini_returns(self, translations):
    return patch.object(gemini, "generate_gemini_reply", return_value=json.dumps({"translations": translations}))

  def test_only_missing_strings_are_sent_and_results_are_cached(self):
    cache.put_many("Hindi", {"Home": "मुख्य पृष्ठ"})
    with self._gemini_returns(["मौसम"]) as ask:
      out = gemini.translate_texts_with_gemini(["Home", "Weather", "Home"], "Hindi")
    self.assertEqual(out, ["मुख्य पृष्ठ", "मौसम", "मुख्य पृष्ठ"])
    sent = json.loads(ask.call_args[0][0])["texts"]
    self.assertEqual(sent, ["Weather"])  # cached and duplicate strings are not sent again

    with patch.object(gemini, "generate_gemini_reply", side_effect=AssertionError("Gemini called")):
      self.assertEqual(gemini.translate_texts_with_gemini(["Weather", "Home"], "Hindi"), ["मौसम", "मुख्य पृष्ठ"])

  def test_cached_strings_still_translate_when_gemini_is_down(self):
    cache.put_many("Hindi", {"Home": "मुख्य पृष्ठ"})
    with patch.object(gemini, "generate_gemini_reply", side_effect=gemini.GeminiError("quota")):
      out = gemini.translate_texts_with_gemini(["Home", "Brand new text"], "Hindi")
    self.assertEqual(out, ["मुख्य पृष्ठ", "Brand new text"])  # untranslated text stays English

  def test_error_when_nothing_could_be_translated(self):
    with patch.object(gemini, "generate_gemini_reply", side_effect=gemini.GeminiError("quota")):
      with self.assertRaises(gemini.GeminiError):
        gemini.translate_texts_with_gemini(["Brand new text"], "Hindi")

  def test_bad_translations_stay_english_and_are_not_cached(self):
    with self._gemini_returns(["", "कॉल करें"]):
      out = gemini.translate_texts_with_gemini(["Home", "Call 1800-123-4567"], "Hindi")
    self.assertEqual(out, ["Home", "Call 1800-123-4567"])
    self.assertEqual(cache.get_many("Hindi", ["Home", "Call 1800-123-4567"]), {})

  def test_wrong_count_from_gemini_is_an_error(self):
    with self._gemini_returns(["one"]):
      with self.assertRaises(ValueError):
        gemini.translate_texts_with_gemini(["a", "b"], "Hindi")


if __name__ == "__main__":
  unittest.main()
