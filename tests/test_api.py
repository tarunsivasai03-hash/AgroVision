"""
Integration tests for AgroVision Flask API.
Run: python -m unittest tests.test_api -v
"""
import io
import os
import sys
import unittest
import unittest.mock
from unittest.mock import patch

# Project root on path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PIL import Image


def _make_test_image(size=(112, 112), color=(34, 139, 34)):
  img = Image.new("RGB", size, color)
  buf = io.BytesIO()
  img.save(buf, format="JPEG")
  buf.seek(0)
  return buf


class AgroVisionAPITest(unittest.TestCase):
  @classmethod
  def setUpClass(cls):
    os.environ.setdefault("GEMINI_API_KEY", "test-key-for-unit-tests")
    # Scans must never reach Gemini from tests; the tests that need a photo check supply their own.
    cls._env = patch.dict(os.environ, {"LEAF_CHECK": "off"})
    cls._env.start()
    from app import app
    from extensions import limiter
    cls.app = app
    cls.limiter = limiter
    limiter.enabled = False  # enabled only in the dedicated rate-limit test
    cls.client = app.test_client()

  @classmethod
  def tearDownClass(cls):
    cls._env.stop()

  def test_health_endpoint(self):
    r = self.client.get("/api/health")
    self.assertEqual(r.status_code, 200)
    data = r.get_json()
    self.assertEqual(data["status"], "ok")
    self.assertEqual(data["disease_classes"], 38)
    self.assertEqual(data["disease_database_entries"], 38)
    self.assertTrue(data["model_file_present"])
    self.assertEqual(len(data["diagnosable_crops"]), 9)
    self.assertNotIn("soybean", data["diagnosable_crops"])
    self.assertEqual(set(data["photo_check"]), {"mode", "ready"})

  def test_disease_database_covers_all_labels(self):
    from services.disease import DISEASE_DATABASE, PLANT_DISEASE_CLASS_NAMES
    missing = [x for x in PLANT_DISEASE_CLASS_NAMES if x not in DISEASE_DATABASE]
    self.assertEqual(missing, [], f"Missing DB keys: {missing}")

  def test_label_order_matches_the_models_training_order(self):
    """
    The model's outputs follow the alphabetical order of the original PlantVillage folder
    names. plant_disease_labels.json once had the two Cherry classes swapped, so every
    cherry result was backwards (checked on 250 PlantVillage photos: 0/20 cherry leaves
    right with the swap, 20/20 without). Keep the file in that order, and keep the
    Android copy identical, since it must follow the same order.
    """
    import json
    import re
    from services.disease import PLANT_DISEASE_CLASS_NAMES

    def original_name(label):
      label = label.replace("Cherry___", "Cherry_(including_sour)___").replace("Corn___", "Corn_(maize)___")
      label = label.replace("Pepper,bell", "Pepper,_bell")
      return re.sub(r"(Esca|Leaf_blight|Haunglongbing)\(", r"\1_(", label)

    original = [original_name(label) for label in PLANT_DISEASE_CLASS_NAMES]
    self.assertEqual(original, sorted(original))

    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    android = os.path.join(root, "android-app", "app", "src", "main", "assets", "plant_disease_labels.json")
    with open(android, encoding="utf-8") as f:
      self.assertEqual(json.load(f), PLANT_DISEASE_CLASS_NAMES)

  def test_predict_requires_image(self):
    r = self.client.post("/predict")
    self.assertEqual(r.status_code, 400)

  @unittest.skipUnless(
    os.path.exists(os.path.join(os.path.dirname(os.path.dirname(__file__)), "plant_disease_model.h5")),
    "plant_disease_model.h5 not found",
  )
  def test_predict_refuses_a_blank_photo(self):
    r = self.client.post(
      "/predict",
      data={"image": (_make_test_image(), "test_leaf.jpg")},  # one flat green colour
      content_type="multipart/form-data",
    )
    self.assertEqual(r.status_code, 200, r.get_data(as_text=True))
    data = r.get_json()
    self.assertEqual((data["status"], data["reason"], data["kind"]), ("rejected", "photo_unusable", "retake"))
    for field in ("headline", "message", "advice", "label"):
      self.assertTrue(data[field], field)
    self.assertEqual(data["label"], "Uncertain")  # what older clients look at

  def test_chat_requires_message(self):
    r = self.client.post("/api/chat", json={})
    self.assertEqual(r.status_code, 400)

  def test_chat_non_agriculture(self):
    r = self.client.post("/api/chat", json={"message": "What is the capital of France?"})
    self.assertEqual(r.status_code, 200)
    data = r.get_json()
    self.assertFalse(data.get("is_agriculture", True))

  @patch("routes.assistant.generate_gemini_reply", return_value="Tomatoes need full sun and regular watering.")
  def test_chat_agriculture_mocked(self, _mock_gemini):
    r = self.client.post("/api/chat", json={"message": "How do I grow tomatoes?"})
    self.assertEqual(r.status_code, 200)
    data = r.get_json()
    self.assertTrue(data.get("is_agriculture"))
    self.assertIn("tomato", data["response"].lower())

  def test_schemes_list(self):
    r = self.client.get("/api/schemes")
    self.assertEqual(r.status_code, 200)
    data = r.get_json()
    self.assertGreaterEqual(len(data["schemes"]), 6)
    self.assertEqual(data["schemes"][0]["id"], "pm-kisan")

  @patch("routes.schemes.generate_gemini_reply", return_value="You may qualify for PM-KISAN and crop insurance.")
  def test_schemes_advise_mocked(self, _mock):
    r = self.client.post(
      "/api/schemes/advise",
      json={"message": "I have 2 acres in Telangana", "state": "Telangana"},
    )
    self.assertEqual(r.status_code, 200)
    self.assertIn("PM-KISAN", r.get_json()["response"])
    
  def test_schemes_qualify_rule_based(self):
    r = self.client.post(
      "/api/schemes/qualify",
      json={"state": "Telangana", "land_acres": "2", "farmer_type": "tenant"}
    )
    self.assertEqual(r.status_code, 200)
    data = r.get_json()
    self.assertTrue(data["profile_complete"])
    self.assertGreater(data["total_matched"], 0)
    
    # PM-KISAN is national, should be in there
    matched_ids = [s["id"] for s in data["qualified_schemes"]]
    self.assertIn("pm-kisan", matched_ids)
    
    # Should contain tenant specific reasons for tenant farmers
    # Let's just check the structure is correct
    first_scheme = data["qualified_schemes"][0]
    self.assertIn("name", first_scheme)
    self.assertIn("match_reason", first_scheme)
    self.assertIn("benefit", first_scheme)

  @patch("routes.translation.translate_texts_with_gemini", return_value=["Hola", "Agricultura"])
  def test_translate_page_mocked(self, _mock):
    r = self.client.post(
      "/api/translate-page",
      json={"target_language": "Spanish", "texts": ["Hello", "Agriculture"]},
    )
    self.assertEqual(r.status_code, 200)
    data = r.get_json()
    self.assertTrue(data["ai_powered"])
    self.assertEqual(data["translations"], ["Hola", "Agricultura"])

  def test_predict_rejects_corrupt_image(self):
    r = self.client.post(
      "/predict",
      data={"image": (io.BytesIO(b"not an image"), "leaf.jpg")},
      content_type="multipart/form-data",
    )
    self.assertEqual(r.status_code, 400)
    self.assertNotIn("details", r.get_json())

  def test_photos_are_never_written_to_disk(self):
    import numpy as np
    from services import scan
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    def snapshot():
      found = set()
      for folder, _dirs, files in os.walk(root):
        if ".git" in folder.split(os.sep) or "android-app" in folder.split(os.sep) or "__pycache__" in folder:
          continue
        found.update(os.path.join(folder, f) for f in files)
      return found

    buf = io.BytesIO()
    Image.fromarray((np.random.RandomState(4).rand(150, 150, 3) * 255).astype("uint8")).save(buf, format="JPEG")
    buf.seek(0)
    before = snapshot()
    with patch.object(scan, "class_probabilities", return_value=np.full(38, 1 / 38)):
      r = self.client.post("/api/predict", data={"image": (buf, "leaf.jpg")}, content_type="multipart/form-data")
    self.assertEqual(r.status_code, 200)
    self.assertEqual(snapshot() - before, set())
    self.assertNotIn("image_url", r.get_json())

  @patch("routes.assistant.generate_gemini_reply", side_effect=RuntimeError("secret internal detail"))
  def test_chat_fallback_is_flagged_not_ai(self, _mock):
    r = self.client.post("/api/chat", json={"message": "how to irrigate my crop"})
    self.assertEqual(r.status_code, 200)
    data = r.get_json()
    self.assertFalse(data["ai_powered"])
    self.assertNotIn("secret internal detail", data["response"])

  @patch("routes.schemes.generate_gemini_reply", side_effect=RuntimeError("boom"))
  def test_schemes_advise_fallback_flagged(self, _mock):
    r = self.client.post("/api/schemes/advise", json={"message": "help"})
    data = r.get_json()
    self.assertFalse(data["ai_powered"])
    self.assertTrue(data["fallback"])

  # --- medium/low audit fixes ---

  def test_state_aliases_normalize_to_slugs(self):
    from services.schemes_data import _normalize_state
    for raw in ("UP", "Uttar Pradesh", "uttar-pradesh", " uttar   pradesh "):
      self.assertEqual(_normalize_state(raw), "uttar-pradesh")
    self.assertEqual(_normalize_state("AP"), "andhra-pradesh")
    self.assertEqual(_normalize_state("TS"), "telangana")

  def test_qualify_accepts_numeric_land_and_rejects_text(self):
    r = self.client.post("/api/schemes/qualify", json={"state": "AP", "land_acres": 2.5})
    self.assertEqual(r.status_code, 200)
    ids = [s["id"] for s in r.get_json()["qualified_schemes"]]
    self.assertIn("ysr-rythu-bharosa", ids)      # Andhra Pradesh scheme
    self.assertNotIn("rythu-bandhu", ids)        # Telangana scheme
    r = self.client.post("/api/schemes/qualify", json={"state": "AP", "land_acres": "lots"})
    self.assertEqual(r.status_code, 400)
    r = self.client.post("/api/schemes/qualify", json={"state": "AP", "land_acres": "not specified"})
    self.assertEqual(r.status_code, 200)

  def test_chat_filter_uses_whole_words(self):
    from routes.assistant import is_agriculture_question
    self.assertFalse(is_agriculture_question("tell me about breast implants"))
    self.assertFalse(is_agriculture_question("🙂 tell me a joke"))
    self.assertTrue(is_agriculture_question("my tomatoes have spots"))
    self.assertTrue(is_agriculture_question("मेरी फसल"))  # Hindi: "my crop"

  @patch("routes.translation.translate_texts_with_gemini", return_value=["Hola"])
  def test_translate_ignores_client_api_key(self, mock_translate):
    r = self.client.post(
      "/api/translate-page",
      json={"target_language": "Spanish", "texts": ["Hello"], "gemini_api_key": "attacker-key"},
    )
    self.assertEqual(r.status_code, 200)
    mock_translate.assert_called_once_with(["Hello"], "Spanish")

  @patch("routes.translation.translate_texts_with_gemini", side_effect=RuntimeError("down"))
  def test_translate_failure_is_503(self, _mock):
    r = self.client.post("/api/translate-page", json={"target_language": "Hindi", "texts": ["Hello"]})
    self.assertEqual(r.status_code, 503)
    self.assertFalse(r.get_json()["ai_powered"])

  def test_unknown_api_path_returns_json_404(self):
    r = self.client.get("/api/does-not-exist")
    self.assertEqual(r.status_code, 404)
    self.assertEqual(r.get_json()["error"], "Not found")
    r = self.client.get("/no-such-page")
    self.assertEqual(r.status_code, 404)
    self.assertIn("text/html", r.content_type)

  @unittest.skipUnless(
    os.path.exists(os.path.join(os.path.dirname(os.path.dirname(__file__)), "plant_disease_model.h5")),
    "plant_disease_model.h5 not found",
  )
  def test_api_predict_reads_the_real_image_format_and_returns_a_checked_result(self):
    from services import scan
    from services.leaf_check import PhotoCheck
    import numpy as np
    from tests.helpers import grape_black_rot_probs
    buf = io.BytesIO()
    rng = np.random.RandomState(0)
    Image.fromarray((rng.rand(120, 140, 3) * 255).astype("uint8")).save(buf, format="PNG")
    buf.seek(0)
    check = PhotoCheck("leaf_closeup", "grape", "high", "", "clear")
    with patch.dict(os.environ, {"LEAF_CHECK": "required"}),          patch.object(scan, "class_probabilities", return_value=grape_black_rot_probs()),          patch.object(scan.leaf_check, "check_photo", return_value=check):
      r = self.client.post(
        "/api/predict",
        data={"image": (buf, "leaf.jpg")},  # PNG content with a .jpg name
        content_type="multipart/form-data",
      )
    self.assertEqual(r.status_code, 200, r.get_data(as_text=True))
    data = r.get_json()
    self.assertNotIn("image_url", data)
    self.assertEqual((data["status"], data["class_id"], data["verified"]), ("ok", "Grape___Black_rot", True))
    self.assertEqual(len(data["alternatives"]), 3)
    self.assertTrue(data["cautions"])

  @unittest.skipUnless(
    os.path.exists(os.path.join(os.path.dirname(os.path.dirname(__file__)), "plant_disease_model.h5")),
    "plant_disease_model.h5 not found",
  )
  def test_predict_runs_the_real_model_when_the_photo_check_is_off(self):
    import numpy as np
    buf = io.BytesIO()
    Image.fromarray((np.random.RandomState(2).rand(300, 400, 3) * 255).astype("uint8")).save(buf, format="JPEG")
    buf.seek(0)
    r = self.client.post("/api/predict", data={"image": (buf, "leaf.jpg")}, content_type="multipart/form-data")
    self.assertEqual(r.status_code, 200, r.get_data(as_text=True))
    data = r.get_json()
    self.assertIn(data["status"], ("ok", "rejected"))
    if data["status"] == "ok":
      self.assertFalse(data["verified"])  # nothing checked the crop
      self.assertEqual(len(data["alternatives"]), 3)

  def test_api_predict_refuses_other_crops_and_unreachable_checks(self):
    from services import scan
    from services.leaf_check import PhotoCheck
    import numpy as np
    from tests.helpers import grape_black_rot_probs

    def upload():
      buf = io.BytesIO()
      Image.fromarray((np.random.RandomState(1).rand(120, 140, 3) * 255).astype("uint8")).save(buf, format="JPEG")
      buf.seek(0)
      return {"image": (buf, "leaf.jpg")}

    rice = PhotoCheck("leaf_closeup", "other_plant", "high", "rice", "none_visible")
    cases = [(rice, "unsupported_crop"), (None, "check_unavailable")]
    for check, reason in cases:
      with patch.dict(os.environ, {"LEAF_CHECK": "required"}),            patch.object(scan, "class_probabilities", return_value=grape_black_rot_probs()),            patch.object(scan.leaf_check, "check_photo", return_value=check):
        r = self.client.post("/api/predict", data=upload(), content_type="multipart/form-data")
      self.assertEqual(r.status_code, 200)
      data = r.get_json()
      self.assertEqual((data["status"], data["reason"]), ("rejected", reason))
      self.assertNotIn("class_id", data)  # no disease is named

  def test_predict_rejects_unsupported_image_format(self):
    buf = io.BytesIO()
    Image.new("RGB", (32, 32)).save(buf, format="GIF")
    buf.seek(0)
    r = self.client.post(
      "/api/predict",
      data={"image": (buf, "leaf.png")},
      content_type="multipart/form-data",
    )
    self.assertEqual(r.status_code, 400)

  @patch("routes.assistant.generate_gemini_reply", return_value="ok")
  def test_chat_is_rate_limited(self, _mock):
    self.limiter.enabled = True
    self.limiter.reset()
    try:
      codes = [
        self.client.post("/api/chat", json={"message": "crop advice"}).status_code
        for _ in range(11)
      ]
    finally:
      self.limiter.enabled = False
      self.limiter.reset()
    self.assertEqual(codes[:10], [200] * 10)
    self.assertEqual(codes[10], 429)


class WeatherServiceTest(unittest.TestCase):
  def test_sample_data_is_flagged_without_key(self):
    from services import weather
    with patch.dict(os.environ, {"OPENWEATHER_API_KEY": ""}):
      data = weather.fetch_openweather("Guntur")
    self.assertTrue(data["is_sample"])
    self.assertEqual(data["location"], "Guntur")
    self.assertEqual(len(data["forecast"]), 5)

  def test_unknown_place_is_a_clear_error(self):
    import urllib.error
    from services import weather
    not_found = urllib.error.HTTPError("url", 404, "Not Found", {}, None)
    with patch.dict(os.environ, {"OPENWEATHER_API_KEY": "k"}),          patch.object(weather, "_download_json", side_effect=not_found):
      with self.assertRaisesRegex(ValueError, "Could not find a place"):
        weather.fetch_openweather("Gunturr")

  def test_coordinates_are_queried_by_lat_lon(self):
    from services.weather import _location_query
    self.assertEqual(_location_query("17.69,83.22"), "lat=17.69&lon=83.22")
    self.assertEqual(_location_query("Guntur"), "q=Guntur")

  def test_daily_forecast_and_alerts(self):
    from services.weather import _daily_forecast, _farm_alerts
    day = 86400
    entries = [
      {"dt": i * 10800, "main": {"temp_min": 30, "temp_max": 41}, "pop": 0.9,
       "rain": {"3h": 5}, "wind": {"speed": 3}, "weather": [{"description": "moderate rain"}]}
      for i in range(8)
    ] + [
      {"dt": day + i * 10800, "main": {"temp_min": 20, "temp_max": 25}, "pop": 0.1,
       "wind": {"speed": 2}, "weather": [{"description": "clear sky"}]}
      for i in range(8)
    ]
    days = _daily_forecast({"list": entries, "city": {"timezone": 0}})
    self.assertEqual(len(days), 2)
    self.assertEqual(days[0]["rain_mm"], 40)
    self.assertEqual(days[0]["condition"], "Moderate Rain")
    events = {a["event"] for a in _farm_alerts(days)}
    self.assertEqual(events, {"Heavy Rain", "Heat"})



class GeminiClientTest(unittest.TestCase):
  """services.gemini talks to the REST API; these tests stub out urlopen."""

  def _response(self, payload):
    import json
    resp = unittest.mock.MagicMock()
    resp.read.return_value = json.dumps(payload).encode("utf-8")
    resp.__enter__.return_value = resp
    return resp

  def _http_error(self, code):
    import urllib.error
    return urllib.error.HTTPError("url", code, "error", {}, None)

  def test_returns_text_and_sends_key_in_header(self):
    from services import gemini
    ok = self._response({"candidates": [{"content": {"parts": [{"text": "Use neem oil."}]}}]})
    with patch.dict(os.environ, {"GEMINI_API_KEY": "k", "GEMINI_MODEL": "gemini-2.5-flash"}),          patch.object(gemini.urllib.request, "urlopen", return_value=ok) as urlopen:
      self.assertEqual(gemini.generate_gemini_reply("aphids?"), "Use neem oil.")
    request = urlopen.call_args[0][0]
    self.assertEqual(request.get_header("X-goog-api-key"), "k")
    self.assertNotIn("key=", request.full_url)

  def test_unknown_model_falls_back_to_next(self):
    from services import gemini
    ok = self._response({"candidates": [{"content": {"parts": [{"text": "ok"}]}}]})
    with patch.dict(os.environ, {"GEMINI_API_KEY": "k", "GEMINI_MODEL": "gemini-old"}),          patch.object(gemini.urllib.request, "urlopen", side_effect=[self._http_error(404), ok]) as urlopen:
      self.assertEqual(gemini.generate_gemini_reply("hi"), "ok")
    self.assertEqual(urlopen.call_count, 2)

  def test_bad_key_does_not_retry_other_models(self):
    from services import gemini
    with patch.dict(os.environ, {"GEMINI_API_KEY": "bad"}),          patch.object(gemini.urllib.request, "urlopen", side_effect=self._http_error(403)) as urlopen:
      with self.assertRaises(gemini.GeminiError):
        gemini.generate_gemini_reply("hi")
    self.assertEqual(urlopen.call_count, 1)

  def test_missing_key_raises(self):
    from services import gemini
    with patch.dict(os.environ, {"GEMINI_API_KEY": ""}):
      with self.assertRaises(gemini.GeminiError):
        gemini.generate_gemini_reply("hi")


if __name__ == "__main__":
  unittest.main()
