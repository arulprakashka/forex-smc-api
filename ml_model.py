# ml_model.py
import joblib
import os
import numpy as np

MODEL_PATH = "data/models/lstm_model.pkl"

class BrainML:
    def __init__(self):
        self.model = None
        if os.path.exists(MODEL_PATH):
            try:
                self.model = joblib.load(MODEL_PATH)
            except:
                pass
    def predict(self, features):
        if self.model is None:
            return 0, 0
        # Build feature vector (same order as training)
        feature_names = [...] # list from earlier
        X = np.array([features.get(name, 0) for name in feature_names]).reshape(1, -1)
        try:
            pred = self.model.predict(X)[0]
            direction = 1 if pred > 0.2 else -1 if pred < -0.2 else 0
            confidence = min(100, abs(pred) * 100)
            return direction, confidence
        except:
            return 0, 0
