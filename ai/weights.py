# ai/weights.py
import json
import os

WEIGHTS_FILE = "data/weights.json"
DEFAULT_WEIGHTS = {
    "BrainSMC": 1.0,
    "BrainICT": 1.0,
    "BrainWyckoff": 1.0,
    "BrainVSA": 1.0,
    "BrainOrderFlow": 1.5,
    "BrainFootprint": 1.2,
    "BrainAdvanced": 1.0,
}

def load_weights():
    if os.path.exists(WEIGHTS_FILE):
        with open(WEIGHTS_FILE, 'r') as f:
            return json.load(f)
    else:
        save_weights(DEFAULT_WEIGHTS)
        return DEFAULT_WEIGHTS

def save_weights(weights):
    os.makedirs(os.path.dirname(WEIGHTS_FILE), exist_ok=True)
    with open(WEIGHTS_FILE, 'w') as f:
        json.dump(weights, f, indent=2)

def update_weight(brain_name, outcome, confidence=1.0):
    weights = load_weights()
    current = weights.get(brain_name, 1.0)
    alpha = 0.02 if outcome else 0.05
    delta = alpha * (1 if outcome else -1) * (confidence if outcome else 1)
    new_weight = max(0.5, min(2.0, current + delta))
    weights[brain_name] = new_weight
    save_weights(weights)
    return new_weight
