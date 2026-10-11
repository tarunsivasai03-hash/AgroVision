"""Small helpers shared by test modules."""
import numpy as np

from services.disease import PLANT_DISEASE_CLASS_NAMES


def grape_black_rot_probs():
  """Model output that is sure it is grape black rot, with the rest spread evenly."""
  vector = np.zeros(len(PLANT_DISEASE_CLASS_NAMES), dtype=np.float64)
  vector[PLANT_DISEASE_CLASS_NAMES.index("Grape___Black_rot")] = 0.97
  vector[vector == 0] = 0.03 / (len(vector) - 1)
  return vector
