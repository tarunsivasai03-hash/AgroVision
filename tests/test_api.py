"""
Integration tests for AgroVision Flask API.
Run: python -m unittest tests.test_api -v
"""
import io
import os
import sys
import unittest
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
    from app import app
    cls.app = app
    cls.client = app.test_client()

  def test_health_endpoint(self):
    r = self.client.get("/api/health")
    self.assertEqual(r.status_code, 200)
    data = r.get_json()
    self.assertEqual(data["status"], "ok")
    self.assertEqual(data["disease_classes"], 38)
    self.assertEqual(data["disease_database_entries"], 38)
    self.assertTrue(data["model_file_present"])

  def test_disease_database_covers_all_labels(self):
    from services.disease import DISEASE_DATABASE, PLANT_DISEASE_CLASS_NAMES
    missing = [x for x in PLANT_DISEASE_CLASS_NAMES if x not in DISEASE_DATABASE]
    self.assertEqual(missing, [], f"Missing DB keys: {missing}")

  def test_predict_requires_image(self):
    r = self.client.post("/predict")
    self.assertEqual(r.status_code, 400)

  @unittest.skipUnless(
    os.path.exists(os.path.join(os.path.dirname(os.path.dirname(__file__)), "plant_disease_model.h5")),
    "plant_disease_model.h5 not found",
  )
  def test_predict_with_synthetic_leaf_image(self):
    buf = _make_test_image()
    r = self.client.post(
      "/predict",
      data={"image": (buf, "test_leaf.jpg")},
      content_type="multipart/form-data",
    )
    self.assertEqual(r.status_code, 200, r.get_data(as_text=True))
    data = r.get_json()
    self.assertIn("label", data)
    self.assertIn("confidence", data)
    self.assertIn("disease", data)
    self.assertIn("cure", data)
    self.assertIn("prevention", data)
    self.assertIn("description", data)
    self.assertIn("is_plant", data)
    self.assertIn(data["label"], ("Healthy", "Diseased", "Uncertain"))

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


if __name__ == "__main__":
  unittest.main()
