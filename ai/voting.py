# ai/voting.py
from .brains import (BrainSMC, BrainICT, BrainWyckoff, BrainVSA,
                     BrainOrderFlow, BrainFootprint, BrainAdvanced)
from .weights import load_weights
from .regime_selector import get_regime_weights
from .market_state import get_market_state

brains = [
    ("BrainSMC", BrainSMC()),
    ("BrainICT", BrainICT()),
    ("BrainWyckoff", BrainWyckoff()),
    ("BrainVSA", BrainVSA()),
    ("BrainOrderFlow", BrainOrderFlow()),
    ("BrainFootprint", BrainFootprint()),
    ("BrainAdvanced", BrainAdvanced())
]

def vote(features, high, low, close, volume, use_regime=True):
    base_weights = load_weights()
    current_regime = get_market_state(high, low, close, volume, features)
    regime_mult = get_regime_weights(current_regime) if use_regime else {}
    votes = []
    total_weight = 0
    for name, brain in brains:
        direction, conf = brain.predict(features)
        if direction != 0:
            w = base_weights.get(name, 1.0)
            w *= regime_mult.get(name, 1.0)
            votes.append((direction, conf * w))
            total_weight += w
    if not votes:
        return 0, 0, votes, current_regime
    total_bullish = sum(conf for d, conf in votes if d > 0)
    total_bearish = sum(conf for d, conf in votes if d < 0)
    if total_bullish > total_bearish:
        direction = 1
        confidence = min(100, total_bullish / total_weight * 100)
    elif total_bearish > total_bullish:
        direction = -1
        confidence = min(100, total_bearish / total_weight * 100)
    else:
        direction = 0
        confidence = 0
    return direction, confidence, votes, current_regime
