# ai/brains.py
import numpy as np

class BrainSMC:
    def predict(self, features):
        bullish = (features.get('fvgs_bullish_count', 0) + features.get('ob_bullish_count', 0) +
                   features.get('ms_bos_count', 0) + features.get('ms_mss_count', 0))
        bearish = (features.get('fvgs_bearish_count', 0) + features.get('ob_bearish_count', 0))
        total = bullish + bearish
        if total == 0:
            return 0, 0
        score = (bullish - bearish) / total
        return (1 if score > 0.2 else -1 if score < -0.2 else 0), abs(score) * 100

class BrainICT:
    def predict(self, features):
        bullish = (features.get('ote_long_count', 0) + features.get('silver_bullet_count', 0) +
                   features.get('kill_zones_count', 0) + features.get('judas_count', 0))
        bearish = (features.get('ote_short_count', 0) + features.get('judas_count', 0))
        total = bullish + bearish
        if total == 0:
            return 0, 0
        score = (bullish - bearish) / total
        return (1 if score > 0.2 else -1 if score < -0.2 else 0), abs(score) * 100

class BrainWyckoff:
    def predict(self, features):
        bullish = features.get('wyckoff_springs', 0)
        bearish = features.get('wyckoff_upthrusts', 0)
        total = bullish + bearish
        if total == 0:
            return 0, 0
        score = (bullish - bearish) / total
        return (1 if score > 0.2 else -1 if score < -0.2 else 0), abs(score) * 100

class BrainVSA:
    def predict(self, features):
        bullish = features.get('vsa_signals', 0) / 2
        bearish = features.get('vsa_signals', 0) / 2
        total = bullish + bearish + 1
        score = (bullish - bearish) / total
        return (1 if score > 0.2 else -1 if score < -0.2 else 0), abs(score) * 100

class BrainOrderFlow:
    def predict(self, features):
        vel = features.get('ofv_velocity', 0)
        if vel > 0.3:
            return 1, 80
        elif vel < -0.3:
            return -1, 80
        return 0, 0

class BrainFootprint:
    def predict(self, features):
        if features.get('footprint_signal', 0):
            return 1, 70
        return 0, 0

class BrainAdvanced:
    def predict(self, features):
        bullish = (features.get('stacked_bullish_stacks', 0) +
                   features.get('iceberg_count', 0) +
                   features.get('sweep_fvg_count', 0) +
                   (1 if features.get('cascade_level', 0) > 2 and features.get('vwap_signal_strength', 0) > 0 else 0))
        bearish = (features.get('stacked_bearish_stacks', 0) +
                   features.get('iceberg_count', 0) +
                   features.get('trap_signal', 0) +
                   (1 if features.get('cascade_level', 0) > 2 and features.get('vwap_signal_strength', 0) < 0 else 0))
        total = bullish + bearish
        if total == 0:
            return 0, 0
        score = (bullish - bearish) / total
        return (1 if score > 0.2 else -1 if score < -0.2 else 0), abs(score) * 100
