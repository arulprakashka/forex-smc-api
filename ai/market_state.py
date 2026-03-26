# ai/market_state.py
import numpy as np

def get_market_state(high, low, close, volume, features):
    if len(close) < 20:
        return "UNKNOWN"
    atr = np.mean([high[i]-low[i] for i in range(-20, 0)])
    avg_price = np.mean(close[-20:])
    vol_pct = atr / avg_price * 100
    total_patterns = (features.get('fvgs_bullish_count',0) + features.get('fvgs_bearish_count',0) +
                      features.get('ob_bullish_count',0) + features.get('ob_bearish_count',0))
    if vol_pct > 1.5:
        return "VOLATILE"
    elif vol_pct > 0.8:
        return "ACTIVE"
    else:
        return "QUIET"
