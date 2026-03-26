# ai/regime_selector.py
import json
import os

REGIME_FILE = "data/regime_performance.json"
DEFAULT_REGIME_PERF = {
    "VOLATILE": {"BrainOrderFlow": 1.6, "BrainSMC": 1.2, "BrainAdvanced": 1.4},
    "ACTIVE": {"BrainOrderFlow": 1.3, "BrainSMC": 1.1, "BrainAdvanced": 1.2},
    "QUIET": {"BrainWyckoff": 1.3, "BrainVSA": 1.1, "BrainFootprint": 1.2}
}

def load_regime_perf():
    if os.path.exists(REGIME_FILE):
        with open(REGIME_FILE, 'r') as f:
            return json.load(f)
    else:
        save_regime_perf(DEFAULT_REGIME_PERF)
        return DEFAULT_REGIME_PERF

def save_regime_perf(perf):
    os.makedirs(os.path.dirname(REGIME_FILE), exist_ok=True)
    with open(REGIME_FILE, 'w') as f:
        json.dump(perf, f, indent=2)

def get_regime_weights(regime):
    perf = load_regime_perf()
    return perf.get(regime, {})
