#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from flask import Flask, request, jsonify
from flask_cors import CORS
import numpy as np
import json
import sys
import os
import requests
from datetime import datetime, timedelta
import time
import yfinance as yf
import pandas as pd

# ============================================
# CUSTOM JSON ENCODER (FIX FOR bool ERROR)
# ============================================
class CustomJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, np.integer):
            return int(obj)
        elif isinstance(obj, np.floating):
            return float(obj)
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        elif isinstance(obj, np.bool_):
            return bool(obj)
        elif isinstance(obj, datetime):
            return obj.isoformat()
        elif isinstance(obj, pd.Timestamp):
            return obj.isoformat()
        elif isinstance(obj, pd.Series):
            return obj.tolist()
        elif isinstance(obj, pd.DataFrame):
            return obj.to_dict('records')
        return super().default(obj)

app = Flask(__name__)
app.json_encoder = CustomJSONEncoder
CORS(app)

# ============================================
# API KEYS (Optional - Yahoo is primary)
# ============================================
TWELVE_DATA_KEY = "e4987fc0c8f0461db5877035bc089d64"  # Optional backup
FCS_API_KEY = "wAWpiqowXld2Bv5bl0jD4kw"              # Optional backup

# ============================================
# HELPER FUNCTION TO CONVERT NUMPY TYPES
# ============================================
def convert_numpy(obj):
    """Convert numpy types to Python native types"""
    if isinstance(obj, dict):
        return {k: convert_numpy(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [convert_numpy(i) for i in obj]
    elif isinstance(obj, tuple):
        return tuple(convert_numpy(i) for i in obj)
    elif isinstance(obj, np.integer):
        return int(obj)
    elif isinstance(obj, np.floating):
        return float(obj)
    elif isinstance(obj, np.ndarray):
        return obj.tolist()
    elif isinstance(obj, np.bool_):
        return bool(obj)
    elif isinstance(obj, datetime):
        return obj.isoformat()
    elif isinstance(obj, pd.Timestamp):
        return obj.isoformat()
    elif isinstance(obj, pd.Series):
        return obj.tolist()
    elif isinstance(obj, pd.DataFrame):
        return obj.to_dict('records')
    return obj

# ============================================
# YAHOO FINANCE DATA FETCHING (PRIMARY)
# ============================================

def fetch_from_yahoo(symbol="GC=F", interval="1h", days=30):
    """Primary data source - Yahoo Finance (FREE, UNLIMITED)"""
    
    period_map = {
        '1m': '1d',
        '5m': '5d',
        '15m': '1mo',
        '30m': '1mo',
        '1h': '1mo',
        '4h': '3mo',
        '1d': '6mo',
        '1wk': '1y'
    }
    
    interval_map = {
        '1m': '1m',
        '5m': '5m',
        '15m': '15m',
        '30m': '30m',
        '1h': '1h',
        '4h': '1h',  # Yahoo doesn't have 4h, use 1h and aggregate
        '1d': '1d',
        '1wk': '1wk'
    }
    
    period = period_map.get(interval, '1mo')
    yf_interval = interval_map.get(interval, '1h')
    
    try:
        ticker = yf.Ticker(symbol)
        data = ticker.history(period=period, interval=yf_interval)
        
        if data.empty:
            return None
        
        # For 4h, aggregate 4x 1h candles
        if interval == '4h' and len(data) >= 4:
            aggregated = []
            for i in range(0, len(data)-3, 4):
                chunk = data.iloc[i:i+4]
                aggregated.append({
                    'open': float(chunk['Open'].iloc[0]),
                    'high': float(chunk['High'].max()),
                    'low': float(chunk['Low'].min()),
                    'close': float(chunk['Close'].iloc[-1]),
                    'volume': int(chunk['Volume'].sum()),
                    'time': str(chunk.index[-1])
                })
            
            return {
                'prices': [float(c['close']) for c in aggregated],
                'high': [float(c['high']) for c in aggregated],
                'low': [float(c['low']) for c in aggregated],
                'open': [float(c['open']) for c in aggregated],
                'volume': [int(c['volume']) for c in aggregated],
                'time': [c['time'] for c in aggregated],
                'source': 'yahoo'
            }
        
        # Normal data
        return {
            'prices': [float(x) for x in data['Close'].tolist()],
            'high': [float(x) for x in data['High'].tolist()],
            'low': [float(x) for x in data['Low'].tolist()],
            'open': [float(x) for x in data['Open'].tolist()],
            'volume': [int(x) for x in data['Volume'].tolist()],
            'time': data.index.strftime('%Y-%m-%d %H:%M').tolist(),
            'source': 'yahoo'
        }
    except Exception as e:
        print(f"Yahoo error: {e}")
        return None

# ============================================
# BACKUP API FUNCTIONS (Twelve Data)
# ============================================

def fetch_from_twelvedata(symbol="XAU/USD", interval="1h"):
    """Backup data source - Twelve Data"""
    if TWELVE_DATA_KEY == "e4987fc0c8f0461db5877035bc089d64":
        return None
        
    url = f"https://api.twelvedata.com/time_series"
    params = {
        'symbol': symbol.replace('/', ''),
        'interval': interval,
        'apikey': TWELVE_DATA_KEY,
        'outputsize': 500
    }
    
    try:
        response = requests.get(url, params=params, timeout=10)
        data = response.json()
        
        if 'values' in data:
            return {
                'prices': [float(v['close']) for v in data['values']],
                'high': [float(v['high']) for v in data['values']],
                'low': [float(v['low']) for v in data['values']],
                'open': [float(v['open']) for v in data['values']],
                'volume': [float(v['volume']) for v in data['values']],
                'time': [v['datetime'] for v in data['values']],
                'source': 'twelvedata'
            }
    except:
        pass
    return None

# ============================================
# MASTER DATA FETCH FUNCTION
# ============================================

def get_mtf_data(symbol="XAU/USD"):
    """Get multi-timeframe data (Primary: Yahoo, Backup: Twelve Data)"""
    
    # Map symbol to Yahoo format
    if symbol == "XAU/USD":
        yahoo_symbol = "GC=F"
    elif symbol.endswith("=X"):
        yahoo_symbol = symbol
    else:
        yahoo_symbol = symbol.replace('/', '') + "=X"
    
    timeframes = [
        '1m', '5m', '15m', '30m', '1h', '4h', '1d', '1wk'
    ]
    
    all_data = {}
    
    for tf in timeframes:
        data = None
        
        # Try Yahoo first
        data = fetch_from_yahoo(yahoo_symbol, tf)
        
        # If Yahoo fails, try Twelve Data
        if not data and TWELVE_DATA_KEY != "YOUR_TWELVE_DATA_API_KEY":
            data = fetch_from_twelvedata(symbol, tf)
        
        # If both fail, generate simulated data
        if not data:
            data = generate_simulated_data(200)
            data['source'] = 'simulated'
        
        if data:
            all_data[tf] = data
    
    return all_data

def generate_simulated_data(count):
    """Generate simulated data for fallback"""
    base = 2000.0
    prices = []
    highs = []
    lows = []
    opens = []
    volumes = []
    
    for i in range(count):
        change = float(np.random.normal(0, 3))
        price = base + change
        prices.append(float(price))
        opens.append(float(base))
        highs.append(float(price + abs(float(np.random.normal(0, 2)))))
        lows.append(float(price - abs(float(np.random.normal(0, 2)))))
        volumes.append(int(np.random.randint(1000, 10000)))
        base = price
    
    return {
        'prices': prices,
        'high': highs,
        'low': lows,
        'open': opens,
        'volume': volumes,
        'time': [f"2026-01-01 {i%24:02d}:{i%60:02d}" for i in range(count)]
    }

# ============================================
# SMC PATTERN DETECTION FUNCTIONS
# ============================================

def detect_fvgs(high, low, close):
    """Fair Value Gaps"""
    fvgs = {'bullish': [], 'bearish': []}
    
    for i in range(2, len(high)-1):
        if low[i-1] > high[i-2] and low[i] > high[i-1]:
            fvgs['bullish'].append({
                'level': float(round((high[i-2] + low[i-1]) / 2, 2)),
                'top': float(round(high[i-2], 2)),
                'bottom': float(round(low[i-1], 2)),
                'index': int(i)
            })
        
        if high[i-1] < low[i-2] and high[i] < low[i-1]:
            fvgs['bearish'].append({
                'level': float(round((low[i-2] + high[i-1]) / 2, 2)),
                'top': float(round(low[i-2], 2)),
                'bottom': float(round(high[i-1], 2)),
                'index': int(i)
            })
    
    return fvgs

def detect_order_blocks(high, low, close, volume):
    """Order Blocks"""
    obs = {'bullish': [], 'bearish': []}
    
    for i in range(5, len(close)-5):
        future_move = float(abs(close[i+3] - close[i]))
        past_volatility = float(np.std(close[i-10:i])) if i >= 10 else 0.01
        
        if future_move > past_volatility * 2:
            direction = 'bullish' if close[i+3] > close[i] else 'bearish'
            vol_confirmed = bool(volume[i] > np.mean(volume[i-10:i]) * 1.3) if i >= 10 else False
            
            ob = {
                'price': float(round(close[i], 2)),
                'high': float(round(high[i], 2)),
                'low': float(round(low[i], 2)),
                'volume': float(round(volume[i], 2)),
                'confirmed': bool(vol_confirmed),
                'index': int(i)
            }
            
            if direction == 'bullish':
                obs['bullish'].append(ob)
            else:
                obs['bearish'].append(ob)
    
    return obs

def detect_liquidity(high, low):
    """Liquidity Levels"""
    liquidity = {'buyside': [], 'sellside': [], 'internal': []}
    
    for i in range(2, len(high)-2):
        if high[i] > high[i-1] and high[i] > high[i-2] and \
           high[i] > high[i+1] and high[i] > high[i+2]:
            liquidity['buyside'].append({
                'price': float(round(high[i], 2)),
                'index': int(i),
                'type': 'SWING_HIGH'
            })
        
        if low[i] < low[i-1] and low[i] < low[i-2] and \
           low[i] < low[i+1] and low[i] < low[i+2]:
            liquidity['sellside'].append({
                'price': float(round(low[i], 2)),
                'index': int(i),
                'type': 'SWING_LOW'
            })
        
        if i > 5:
            range_high = float(max(high[i-5:i]))
            range_low = float(min(low[i-5:i]))
            mid = float((range_high + range_low) / 2)
            liquidity['internal'].append({
                'price': float(round(mid, 2)),
                'index': int(i),
                'type': 'EQUALIBRIUM'
            })
    
    return liquidity

def detect_market_structure(high, low, close):
    """Market Structure - BOS, MSS"""
    structure = {'bos': [], 'mss': []}
    
    swing_highs = []
    swing_lows = []
    
    for i in range(2, len(high)-2):
        if high[i] > high[i-1] and high[i] > high[i-2] and \
           high[i] > high[i+1] and high[i] > high[i+2]:
            swing_highs.append({'price': float(high[i]), 'index': int(i)})
        
        if low[i] < low[i-1] and low[i] < low[i-2] and \
           low[i] < low[i+1] and low[i] < low[i+2]:
            swing_lows.append({'price': float(low[i]), 'index': int(i)})
    
    for i in range(1, len(swing_highs)):
        if swing_highs[i]['price'] > swing_highs[i-1]['price']:
            structure['bos'].append({
                'type': 'BULLISH_BOS',
                'level': float(round(swing_highs[i]['price'], 2)),
                'index': int(swing_highs[i]['index'])
            })
            structure['mss'].append({
                'type': 'BULLISH_MSS',
                'level': float(round(swing_highs[i]['price'], 2)),
                'index': int(swing_highs[i]['index'])
            })
    
    for i in range(1, len(swing_lows)):
        if swing_lows[i]['price'] < swing_lows[i-1]['price']:
            structure['bos'].append({
                'type': 'BEARISH_BOS',
                'level': float(round(swing_lows[i]['price'], 2)),
                'index': int(swing_lows[i]['index'])
            })
            structure['mss'].append({
                'type': 'BEARISH_MSS',
                'level': float(round(swing_lows[i]['price'], 2)),
                'index': int(swing_lows[i]['index'])
            })
    
    return structure

def detect_breaker_blocks(high, low, close):
    """Breaker Blocks"""
    breakers = {'bullish': [], 'bearish': []}
    
    for i in range(10, len(close)-10):
        prev_high = float(max(high[i-10:i]))
        prev_low = float(min(low[i-10:i]))
        
        if close[i] > prev_high:
            for j in range(i+1, min(i+15, len(close))):
                if prev_high >= close[j] >= prev_high * 0.99:
                    breakers['bullish'].append({
                        'entry': float(round(prev_high, 2)),
                        'stop': float(round(prev_low, 2)),
                        'target': float(round(high[i] * 1.02, 2)),
                        'index': int(j)
                    })
                    break
        
        if close[i] < prev_low:
            for j in range(i+1, min(i+15, len(close))):
                if prev_low <= close[j] <= prev_low * 1.01:
                    breakers['bearish'].append({
                        'entry': float(round(prev_low, 2)),
                        'stop': float(round(prev_high, 2)),
                        'target': float(round(low[i] * 0.98, 2)),
                        'index': int(j)
                    })
                    break
    
    return breakers

def detect_inducement(high, low, close):
    """Inducement"""
    inducements = {'bullish': [], 'bearish': []}
    
    for i in range(5, len(close)-5):
        if low[i] < min(low[i-5:i]) and close[i+1] > low[i]:
            inducements['bullish'].append({
                'level': float(round(low[i], 2)),
                'index': int(i),
                'target': float(round(high[i] * 1.02, 2))
            })
        
        if high[i] > max(high[i-5:i]) and close[i+1] < high[i]:
            inducements['bearish'].append({
                'level': float(round(high[i], 2)),
                'index': int(i),
                'target': float(round(low[i] * 0.98, 2))
            })
    
    return inducements

def detect_equilibrium(high, low, close):
    """Equilibrium"""
    eq_zones = []
    
    for i in range(20, len(close)):
        vwap = float(np.mean(close[i-20:i]))
        std = float(np.std(close[i-20:i]))
        
        eq_zones.append({
            'mean': float(round(vwap, 2)),
            'upper': float(round(vwap + std, 2)),
            'lower': float(round(vwap - std, 2)),
            'index': int(i)
        })
    
    return eq_zones[-5:] if eq_zones else []

def detect_ote(high, low):
    """Optimal Trade Entry"""
    ote = {'long': [], 'short': []}
    
    for i in range(30, len(high)):
        swing_high = float(max(high[i-30:i]))
        swing_low = float(min(low[i-30:i]))
        
        if swing_high > swing_low:
            range_size = float(swing_high - swing_low)
            ote_long_low = float(swing_high - (range_size * 0.70))
            ote_long_high = float(swing_high - (range_size * 0.62))
            ote_short_low = float(swing_low + (range_size * 0.62))
            ote_short_high = float(swing_low + (range_size * 0.70))
            
            ote['long'].append({
                'entry_min': float(round(ote_long_low, 2)),
                'entry_max': float(round(ote_long_high, 2)),
                'stop': float(round(swing_low, 2)),
                'target': float(round(swing_high, 2))
            })
            
            ote['short'].append({
                'entry_min': float(round(ote_short_low, 2)),
                'entry_max': float(round(ote_short_high, 2)),
                'stop': float(round(swing_high, 2)),
                'target': float(round(swing_low, 2))
            })
    
    return ote

def detect_silver_bullet(times, high, low):
    """Silver Bullet (10-11 AM)"""
    silver = []
    
    for i in range(len(times)-10):
        try:
            time_str = times[i] if i < len(times) else ""
            hour = 0
            if isinstance(time_str, str) and ':' in time_str:
                if ' ' in time_str:
                    hour = int(time_str.split()[1].split(':')[0])
                else:
                    hour = int(time_str.split(':')[0])
            else:
                hour = i % 24
            
            if 10 <= hour <= 11:
                zone_high = float(max(high[i:i+5]))
                zone_low = float(min(low[i:i+5]))
                silver.append({
                    'time': str(time_str),
                    'high': float(round(zone_high, 2)),
                    'low': float(round(zone_low, 2))
                })
        except:
            pass
    
    return silver[-3:] if silver else []

def detect_kill_zones(times):
    """Kill Zones"""
    zones = []
    
    for i, ts in enumerate(times[:100]):
        try:
            time_str = ts if isinstance(ts, str) else ""
            hour = 0
            if isinstance(time_str, str) and ':' in time_str:
                if ' ' in time_str:
                    hour = int(time_str.split()[1].split(':')[0])
                else:
                    hour = int(time_str.split(':')[0])
            else:
                hour = i % 24
            
            if 2 <= hour <= 5:
                zones.append({'zone': 'LONDON_OPEN', 'time': str(ts), 'index': int(i)})
            elif 7 <= hour <= 10:
                zones.append({'zone': 'NY_OPEN', 'time': str(ts), 'index': int(i)})
            elif 11 <= hour <= 12:
                zones.append({'zone': 'LONDON_CLOSE', 'time': str(ts), 'index': int(i)})
            elif 19 <= hour <= 22:
                zones.append({'zone': 'ASIA_SESSION', 'time': str(ts), 'index': int(i)})
        except:
            pass
    
    return zones[-10:] if zones else []

def detect_power_of_3(high, low, close):
    """Power of 3"""
    power3 = []
    
    for i in range(50, len(close)-30):
        pre_range = float(max(high[i-20:i]) - min(low[i-20:i]))
        mid_range = float(max(high[i:i+15]) - min(low[i:i+15]))
        post_range = float(max(high[i+15:i+30]) - min(low[i+15:i+30]))
        
        if mid_range < pre_range * 0.4 and post_range > pre_range * 1.6:
            direction = 'UP' if close[i+25] > close[i-15] else 'DOWN'
            power3.append({
                'type': 'POWER_OF_3',
                'accumulation': int(i-20),
                'manipulation': int(i),
                'distribution': int(i+15),
                'direction': direction
            })
    
    return power3[-3:] if power3 else []

def detect_judas_swing(high, low, close):
    """Judas Swing"""
    judas = []
    
    for i in range(20, len(close)-10):
        recent_high = float(max(high[i-10:i]))
        recent_low = float(min(low[i-10:i]))
        
        if high[i] > recent_high * 1.005 and close[i+1] < high[i]:
            judas.append({
                'type': 'JUDAS_SHORT',
                'entry': float(round(high[i], 2)),
                'stop': float(round(high[i] * 1.005, 2)),
                'target': float(round(recent_low, 2)),
                'index': int(i)
            })
        
        if low[i] < recent_low * 0.995 and close[i+1] > low[i]:
            judas.append({
                'type': 'JUDAS_LONG',
                'entry': float(round(low[i], 2)),
                'stop': float(round(low[i] * 0.995, 2)),
                'target': float(round(recent_high, 2)),
                'index': int(i)
            })
    
    return judas[-5:] if judas else []

def detect_turtle_soup(high, low, close):
    """Turtle Soup"""
    soup = []
    
    for i in range(20, len(close)-5):
        period_high = float(max(high[i-20:i]))
        period_low = float(min(low[i-20:i]))
        
        if close[i] > period_high and close[i+1] < period_high:
            soup.append({
                'type': 'TURTLE_SOUP_SHORT',
                'entry': float(round(period_high, 2)),
                'stop': float(round(period_high * 1.01, 2)),
                'target': float(round(period_low, 2)),
                'index': int(i)
            })
        
        if close[i] < period_low and close[i+1] > period_low:
            soup.append({
                'type': 'TURTLE_SOUP_LONG',
                'entry': float(round(period_low, 2)),
                'stop': float(round(period_low * 0.99, 2)),
                'target': float(round(period_high, 2)),
                'index': int(i)
            })
    
    return soup[-5:] if soup else []

def detect_wyckoff(high, low, close, volume):
    """Wyckoff Method"""
    wyckoff = {'phases': [], 'springs': [], 'upthrusts': []}
    
    for i in range(50, len(close)):
        if volume[i] > float(np.mean(volume[i-20:i]) * 2.5):
            wyckoff['phases'].append({
                'phase': 'A_CLIMAX',
                'type': 'SELLING' if close[i] < close[i-1] else 'BUYING',
                'price': float(round(close[i], 2)),
                'index': int(i)
            })
        
        range_width = float(max(high[i-30:i]) - min(low[i-30:i]))
        avg_range = float(np.mean([max(high[j-10:j]) - min(low[j-10:j]) for j in range(i-30, i)])) if i >= 30 else 0
        
        if range_width < avg_range * 0.6 and avg_range > 0:
            wyckoff['phases'].append({
                'phase': 'B_CAUSE',
                'high': float(round(max(high[i-30:i]), 2)),
                'low': float(round(min(low[i-30:i]), 2)),
                'index': int(i)
            })
        
        if low[i] < min(low[i-10:i-5]) and close[i] > low[i]:
            wyckoff['springs'].append({
                'price': float(round(low[i], 2)),
                'index': int(i)
            })
        
        if high[i] > max(high[i-10:i-5]) and close[i] < high[i]:
            wyckoff['upthrusts'].append({
                'price': float(round(high[i], 2)),
                'index': int(i)
            })
    
    return wyckoff

def detect_vsa(high, low, close, volume):
    """Volume Spread Analysis"""
    vsa = []
    
    for i in range(1, len(close)):
        spread = float(high[i] - low[i])
        avg_spread = float(np.mean([high[j] - low[j] for j in range(max(0, i-10), i)])) if i >= 10 else spread
        avg_volume = float(np.mean(volume[max(0, i-10):i])) if i >= 10 else volume[i]
        
        if spread > avg_spread * 1.8 and volume[i] > avg_volume * 1.8:
            vsa.append({
                'type': 'STRONG_MOVE',
                'direction': 'UP' if close[i] > close[i-1] else 'DOWN',
                'index': int(i)
            })
        
        if spread < avg_spread * 0.5 and volume[i] > avg_volume * 1.5:
            vsa.append({
                'type': 'ABSORPTION',
                'index': int(i)
            })
    
    return vsa[-10:] if vsa else []

def detect_smart_money_reversal(high, low, close, volume):
    """Smart Money Reversal"""
    reversals = []
    
    for i in range(5, len(close)-5):
        if close[i] > close[i-1] and close[i-1] < close[i-2] and \
           volume[i] > volume[i-1] * 1.4:
            reversals.append({
                'type': 'SMR_BULLISH',
                'entry': float(round(low[i-1], 2)),
                'stop': float(round(low[i-2], 2)),
                'target': float(round(high[i] * 1.02, 2)),
                'index': int(i)
            })
        
        if close[i] < close[i-1] and close[i-1] > close[i-2] and \
           volume[i] > volume[i-1] * 1.4:
            reversals.append({
                'type': 'SMR_BEARISH',
                'entry': float(round(high[i-1], 2)),
                'stop': float(round(high[i-2], 2)),
                'target': float(round(low[i] * 0.98, 2)),
                'index': int(i)
            })
    
    return reversals[-5:] if reversals else []

def detect_order_flow(high, low, close, volume):
    """Institutional Order Flow"""
    flow = []
    
    for i in range(20, len(close)):
        delta = float(close[i] - (high[i] + low[i])/2)
        cumulative_delta = float(np.sum([close[j] - (high[j] + low[j])/2 for j in range(i-20, i)])) if i >= 20 else delta
        
        if abs(delta) > float(np.std([close[j] - (high[j] + low[j])/2 for j in range(i-20, i)])) * 2:
            direction = 'BUYING' if delta > 0 else 'SELLING'
            flow.append({
                'type': f'INSTITUTIONAL_{direction}',
                'delta': float(round(delta, 2)),
                'cumulative_delta': float(round(cumulative_delta, 2)),
                'index': int(i)
            })
    
    return flow[-10:] if flow else []

def analyze_volume_profile(volume, price):
    """Volume Profile"""
    vol_profile = []
    
    for i in range(len(volume)-20):
        vol_cluster = float(np.sum(volume[i:i+20]))
        price_cluster = float(np.mean(price[i:i+20]))
        vol_profile.append({
            'price': float(round(price_cluster, 2)),
            'volume': float(round(vol_cluster, 2))
        })
    
    return vol_profile[-5:] if vol_profile else []

# ============================================
# BACKTESTING ENGINE
# ============================================

def backtest_strategy(high, low, close, volume, days=30):
    """Complete backtesting"""
    results = {
        'trades': 0,
        'wins': 0,
        'losses': 0,
        'win_rate': 0.0,
        'profit_factor': 0.0,
        'total_profit': 0.0,
        'max_drawdown': 0.0
    }
    
    profits = []
    equity_curve = [1000.0]
    
    for i in range(100, len(close)-50, 10):
        fvgs = detect_fvgs(high[i-100:i], low[i-100:i], close[i-100:i])
        obs = detect_order_blocks(high[i-100:i], low[i-100:i], close[i-100:i], volume[i-100:i])
        
        signal = None
        if len(fvgs['bullish']) > 0 and len(obs['bullish']) > 0:
            signal = 'BUY'
        elif len(fvgs['bearish']) > 0 and len(obs['bearish']) > 0:
            signal = 'SELL'
        
        if signal:
            results['trades'] += 1
            entry = float(close[i])
            target = entry * 1.01 if signal == 'BUY' else entry * 0.99
            stop = entry * 0.99 if signal == 'BUY' else entry * 1.01
            
            future_prices = close[i:i+20]
            trade_result = 0
            for price in future_prices:
                if (signal == 'BUY' and price >= target) or (signal == 'SELL' and price <= target):
                    trade_result = 1
                    results['wins'] += 1
                    profits.append(1)
                    equity_curve.append(equity_curve[-1] * 1.01)
                    break
                if (signal == 'BUY' and price <= stop) or (signal == 'SELL' and price >= stop):
                    trade_result = -1
                    results['losses'] += 1
                    profits.append(-1)
                    equity_curve.append(equity_curve[-1] * 0.99)
                    break
    
    if results['trades'] > 0:
        results['win_rate'] = float(round((results['wins'] / results['trades']) * 100, 2))
        if len(profits) > 0:
            wins_sum = float(sum([p for p in profits if p > 0]))
            losses_sum = float(abs(sum([p for p in profits if p < 0])))
            results['profit_factor'] = float(round(wins_sum / losses_sum if losses_sum > 0 else wins_sum, 2))
            results['total_profit'] = float(round(((equity_curve[-1] / equity_curve[0]) - 1) * 100, 2))
            
            peak = equity_curve[0]
            max_dd = 0.0
            for value in equity_curve:
                if value > peak:
                    peak = value
                dd = (peak - value) / peak * 100
                if dd > max_dd:
                    max_dd = dd
            results['max_drawdown'] = float(round(max_dd, 2))
    
    return results

# ============================================
# CONFLUENCE CALCULATOR
# ============================================

def calculate_confluence(mtf_analysis):
    """Calculate confluence across timeframes"""
    scores = {}
    total_score = 0.0
    tf_count = 0
    
    for tf, analysis in mtf_analysis.items():
        score = 0.0
        signals = []
        
        fvgs = analysis.get('fvgs', {})
        obs = analysis.get('order_blocks', {})
        mss = analysis.get('market_structure', {})
        
        fvg_count = len(fvgs.get('bullish', [])) + len(fvgs.get('bearish', []))
        ob_count = len(obs.get('bullish', [])) + len(obs.get('bearish', []))
        mss_count = len(mss.get('bos', []))
        
        score += fvg_count * 5
        score += ob_count * 8
        score += mss_count * 10
        
        if fvg_count > 0:
            signals.append('FVG')
        if ob_count > 0:
            signals.append('OB')
        if mss_count > 0:
            signals.append('MSS')
        
        scores[tf] = {
            'score': float(min(score, 100)),
            'signals': signals
        }
        total_score += float(min(score, 100))
        tf_count += 1
    
    overall = float(total_score / tf_count) if tf_count > 0 else 0.0
    
    bullish_count = 0
    bearish_count = 0
    
    for analysis in mtf_analysis.values():
        if analysis.get('ote', {}).get('long'):
            bullish_count += 1
        if analysis.get('ote', {}).get('short'):
            bearish_count += 1
    
    bias = 'NEUTRAL'
    if bullish_count > bearish_count * 1.5:
        bias = 'BULLISH'
    elif bearish_count > bullish_count * 1.5:
        bias = 'BEARISH'
    
    return {
        'per_timeframe': scores,
        'overall': float(round(overall, 2)),
        'bias': bias,
        'strength': 'STRONG' if overall >= 70 else 'MODERATE' if overall >= 40 else 'WEAK'
    }

# ============================================
# MAIN ANALYZE FUNCTION
# ============================================

def analyze_all_patterns(data_dict):
    """Run all pattern detectors"""
    if not data_dict or len(data_dict.get('prices', [])) < 50:
        return {'error': 'Insufficient data'}
    
    prices = [float(x) for x in data_dict['prices']]
    highs = [float(x) for x in data_dict['high']]
    lows = [float(x) for x in data_dict['low']]
    opens = [float(x) for x in data_dict.get('open', prices)]
    volumes = [float(x) for x in data_dict.get('volume', [1000] * len(prices))]
    times = data_dict.get('time', [f"2026-01-01 {i%24:02d}:{i%60:02d}" for i in range(len(prices))])
    
    return {
        'fvgs': detect_fvgs(highs, lows, prices),
        'order_blocks': detect_order_blocks(highs, lows, prices, volumes),
        'liquidity': detect_liquidity(highs, lows),
        'market_structure': detect_market_structure(highs, lows, prices),
        'breaker_blocks': detect_breaker_blocks(highs, lows, prices),
        'inducement': detect_inducement(highs, lows, prices),
        'equilibrium': detect_equilibrium(highs, lows, prices),
        'ote': detect_ote(highs, lows),
        'silver_bullet': detect_silver_bullet(times, highs, lows),
        'kill_zones': detect_kill_zones(times),
        'power_of_3': detect_power_of_3(highs, lows, prices),
        'judas_swing': detect_judas_swing(highs, lows, prices),
        'turtle_soup': detect_turtle_soup(highs, lows, prices),
        'wyckoff': detect_wyckoff(highs, lows, prices, volumes),
        'vsa': detect_vsa(highs, lows, prices, volumes),
        'smart_money_reversal': detect_smart_money_reversal(highs, lows, prices, volumes),
        'order_flow': detect_order_flow(highs, lows, prices, volumes),
        'volume_profile': analyze_volume_profile(volumes, prices),
        'last_price': float(round(prices[-1], 2)) if prices else 0.0,
        'timestamp': str(datetime.now())
    }

# ============================================
# API ENDPOINTS
# ============================================

@app.route('/', methods=['GET'])
def home():
    return convert_numpy(jsonify({
        'status': 'FOREX SMC/ICT PRO API',
        'version': '3.0',
        'features': [
            'SMC: FVG, Order Blocks, Liquidity, MSS, Breaker Blocks, Inducement',
            'ICT: OTE, Silver Bullet, Kill Zones, Power of 3, Judas Swing',
            'Wyckoff: Phases, Springs, Upthrusts',
            'VSA: Volume Spread Analysis',
            'SMT: Turtle Soup, Equilibrium',
            'Order Flow Analysis',
            'Multi-timeframe (8 timeframes)',
            'Volume Profile',
            'Backtesting Engine',
            'Confluence Scoring',
            'Real-time Signals'
        ],
        'total_patterns': 20,
        'data_sources': ['Yahoo Finance (Primary)', 'Twelve Data (Backup)'],
        'endpoints': {
            '/analyze/pro': 'POST - Full analysis all patterns',
            '/analyze/symbol/<symbol>': 'GET - Quick analysis',
            '/backtest': 'POST - Run backtest',
            '/health': 'GET - Health check'
        }
    }))

@app.route('/analyze/pro', methods=['POST'])
def analyze_pro():
    """Complete analysis with all patterns"""
    try:
        data = request.get_json()
        symbol = data.get('symbol', 'XAU/USD')
        
        mtf_data = get_mtf_data(symbol)
        
        mtf_analysis = {}
        for tf, tf_data in mtf_data.items():
            mtf_analysis[tf] = analyze_all_patterns(tf_data)
        
        confluence = calculate_confluence(mtf_analysis)
        
        backtest = {}
        if '1h' in mtf_data:
            h1_data = mtf_data['1h']
            backtest = backtest_strategy(
                h1_data['high'], h1_data['low'], 
                h1_data['prices'], h1_data['volume'], 30
            )
        
        final_score = float(confluence['overall'])
        if backtest.get('win_rate', 0) > 60:
            final_score = float(min(100, final_score + 10))
        
        signal = 'STRONG_BUY' if final_score >= 75 and confluence['bias'] == 'BULLISH' else \
                'BUY' if final_score >= 55 and confluence['bias'] == 'BULLISH' else \
                'NEUTRAL' if final_score >= 35 else \
                'SELL' if final_score >= 20 and confluence['bias'] == 'BEARISH' else \
                'STRONG_SELL' if final_score < 20 and confluence['bias'] == 'BEARISH' else 'NEUTRAL'
        
        entry_price = float(mtf_analysis.get('1h', {}).get('last_price', 0))
        entry = {
            'price': float(round(entry_price, 2)),
            'stop_loss': float(round(entry_price * 0.995, 2)) if 'BUY' in signal else float(round(entry_price * 1.005, 2)),
            'take_profit_1': float(round(entry_price * 1.01, 2)) if 'BUY' in signal else float(round(entry_price * 0.99, 2)),
            'take_profit_2': float(round(entry_price * 1.02, 2)) if 'BUY' in signal else float(round(entry_price * 0.98, 2)),
            'take_profit_3': float(round(entry_price * 1.03, 2)) if 'BUY' in signal else float(round(entry_price * 0.97, 2))
        }
        
        result = {
            'success': True,
            'symbol': symbol,
            'timestamp': str(datetime.now()),
            'current_price': float(round(entry_price, 2)),
            'mtf_analysis': mtf_analysis,
            'confluence': confluence,
            'backtest': backtest,
            'final_score': float(round(final_score, 2)),
            'signal': signal,
            'entry': entry,
            'risk_reward': '1:3',
            'confidence': 'HIGH' if final_score >= 70 else 'MEDIUM' if final_score >= 40 else 'LOW',
            'data_sources': list(set([tf_data.get('source', 'unknown') for tf_data in mtf_data.values()]))
        }
        
        return convert_numpy(jsonify(result))
        
    except Exception as e:
        return convert_numpy(jsonify({
            'success': False,
            'error': str(e)
        }))

@app.route('/analyze/symbol/<symbol>', methods=['GET'])
def analyze_symbol(symbol):
    """Quick analysis for a symbol"""
    try:
        data = get_mtf_data(symbol.upper())
        analysis = analyze_all_patterns(data.get('1h', {}))
        return convert_numpy(jsonify({
            'success': True,
            'symbol': symbol.upper(),
            'analysis': analysis
        }))
    except Exception as e:
        return convert_numpy(jsonify({'success': False, 'error': str(e)}))

@app.route('/backtest', methods=['POST'])
def run_backtest():
    """Run backtest"""
    try:
        data = request.get_json()
        symbol = data.get('symbol', 'XAU/USD')
        days = data.get('days', 30)
        
        hist_data = get_mtf_data(symbol)
        h1_data = hist_data.get('1h', {})
        
        if not h1_data:
            return convert_numpy(jsonify({'success': False, 'error': 'No data for backtest'}))
        
        results = backtest_strategy(
            h1_data['high'], h1_data['low'],
            h1_data['prices'], h1_data['volume'],
            days
        )
        
        return convert_numpy(jsonify({
            'success': True,
            'symbol': symbol,
            'days': days,
            'results': results
        }))
        
    except Exception as e:
        return convert_numpy(jsonify({'success': False, 'error': str(e)}))

@app.route('/health', methods=['GET'])
def health():
    return convert_numpy(jsonify({
        'status': 'healthy',
        'timestamp': str(datetime.now()),
        'data_sources': {
            'yahoo': 'active',
            'twelvedata': 'configured' if TWELVE_DATA_KEY != "YOUR_TWELVE_DATA_API_KEY" else 'optional',
            'fcsapi': 'configured' if FCS_API_KEY != "YOUR_FCS_API_KEY" else 'optional'
        }
    }))

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port, debug=False)
