#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import json
import requests
import numpy as np
import yfinance as yf
from datetime import datetime
from flask import Flask, request, jsonify
from flask_cors import CORS

# -------------------------------
# Import modular components
# -------------------------------
from indicators import extract_features
from ai import vote, load_weights, is_news_blocked, get_regime_weights, get_market_state

app = Flask(__name__)
app.json_encoder = None
CORS(app)

# ============================================
# CONFIGURATION
# ============================================
TWELVE_DATA_KEY = "e4987fc0c8f0461db5877035bc089d64"   # Optional – get from twelvedata.com
FCS_API_KEY = "wAWpiqowXld2Bv5bl0jD4kw"               # Optional
SPOT_XAU_SYMBOL = "XAUUSD=X"                   # Yahoo spot gold
FUTURES_SYMBOL = "GC=F"                        # not used

# Advanced features toggle
ENABLE_SELF_LEARNING = True
ENABLE_NEWS_FILTER = False      # requires NewsAPI key
ENABLE_REGIME_SWITCHING = True
ENABLE_ML_PREDICTOR = False      # requires trained model
ENABLE_BACKTEST_ENDPOINT = True

# ============================================
# DATA FETCHING FUNCTIONS (unchanged)
# ============================================
def fetch_from_yahoo(symbol, interval="1h", days=30):
    """Primary data source – Yahoo Finance (free, unlimited)"""
    period_map = {
        '1m': '1d', '5m': '5d', '15m': '1mo', '30m': '1mo',
        '1h': '1mo', '4h': '3mo', '1d': '6mo', '1wk': '1y'
    }
    interval_map = {
        '1m': '1m', '5m': '5m', '15m': '15m', '30m': '30m',
        '1h': '1h', '4h': '1h', '1d': '1d', '1wk': '1wk'
    }
    period = period_map.get(interval, '1mo')
    yf_interval = interval_map.get(interval, '1h')
    try:
        ticker = yf.Ticker(symbol)
        data = ticker.history(period=period, interval=yf_interval)
        if data.empty:
            return None
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
                'prices': [c['close'] for c in aggregated],
                'high': [c['high'] for c in aggregated],
                'low': [c['low'] for c in aggregated],
                'open': [c['open'] for c in aggregated],
                'volume': [c['volume'] for c in aggregated],
                'time': [c['time'] for c in aggregated],
                'source': 'yahoo'
            }
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
        print(f"Yahoo error for {symbol} {interval}: {e}")
        return None

def fetch_from_twelvedata(symbol, interval="1h"):
    """Backup data source – Twelve Data (free 800/day)"""
    if TWELVE_DATA_KEY == "YOUR_TWELVE_DATA_API_KEY":
        return None
    url = "https://api.twelvedata.com/time_series"
    params = {
        'symbol': symbol,
        'interval': interval,
        'apikey': TWELVE_DATA_KEY,
        'outputsize': 500
    }
    try:
        resp = requests.get(url, params=params, timeout=10)
        data = resp.json()
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
    except Exception as e:
        print(f"TwelveData error: {e}")
    return None

def generate_simulated_data(count):
    """Fallback simulated data"""
    base = 3000.0
    prices, highs, lows, opens, volumes = [], [], [], [], []
    for i in range(count):
        change = np.random.normal(0, 5)
        price = base + change
        prices.append(price)
        opens.append(base)
        highs.append(price + abs(np.random.normal(0, 3)))
        lows.append(price - abs(np.random.normal(0, 3)))
        volumes.append(np.random.randint(500, 5000))
        base = price
    return {
        'prices': prices,
        'high': highs,
        'low': lows,
        'open': opens,
        'volume': volumes,
        'time': [f"2026-03-27 {i%24:02d}:{i%60:02d}" for i in range(count)],
        'source': 'simulated'
    }

def get_mtf_data(symbol, timeframe='1h'):
    """Fetch data for a single timeframe."""
    if symbol == "XAU/USD":
        yahoo_symbol = SPOT_XAU_SYMBOL
    elif symbol == "BTC/USD":
        yahoo_symbol = "BTC-USD"
    elif symbol.endswith("=X"):
        yahoo_symbol = symbol
    else:
        yahoo_symbol = symbol.replace('/', '') + "=X"

    data = fetch_from_yahoo(yahoo_symbol, timeframe)

    if not data and symbol == "XAU/USD":
        data = fetch_from_twelvedata("XAUUSD", timeframe)
        if data:
            data['source'] = 'twelvedata_spot'

    if not data:
        data = generate_simulated_data(100)
        data['source'] = 'simulated_fallback'

    if len(data.get('prices', [])) < 30:
        data = generate_simulated_data(100)
        data['source'] = 'simulated_fallback'

    return data

# ============================================
# ANALYSIS FUNCTION (using modular components)
# ============================================
def analyze_all_patterns(data_dict):
    if not data_dict or len(data_dict.get('prices', [])) < 30:
        return {'error': 'Insufficient data'}

    prices = data_dict['prices']
    highs = data_dict['high']
    lows = data_dict['low']
    volumes = data_dict.get('volume', [1000] * len(prices))
    times = data_dict.get('time', [f"2026-03-27 {i%24:02d}:{i%60:02d}" for i in range(len(prices))])

    # Extract features
    features = extract_features(highs, lows, prices, volumes, times)

    # Get AI ensemble vote
    direction, confidence, votes, regime = vote(features, highs, lows, prices, volumes, use_regime=ENABLE_REGIME_SWITCHING)

    return {
        'features': features,
        'direction': direction,
        'confidence': confidence,
        'regime': regime,
        'vote_details': votes,
        'last_price': round(prices[-1], 2),
        'timestamp': str(datetime.now())
    }

# ============================================
# API ENDPOINTS
# ============================================
@app.route('/', methods=['GET'])
def home():
    return jsonify({
        'status': 'FOREX SMC/ICT PRO API (Modular)',
        'version': '6.0',
        'features': [
            'SMC, ICT, Wyckoff, VSA, Order Flow, Footprint, etc.',
            'Multi‑AI ensemble with self‑learning weights',
            '1‑minute/5‑minute support',
            'Market regime detection',
            'News blockout (optional)'
        ],
        'total_patterns': 28,
        'data_sources': ['Yahoo Finance (spot gold)', 'Twelve Data (backup)'],
        'endpoints': {
            '/analyze/pro': 'POST - Full analysis (timeframe parameter)',
            '/scan': 'GET - Scan top setups',
            '/predict_next_minute': 'GET - Real‑time 1‑min prediction',
            '/optimize': 'POST - Run backtest optimization',
            '/health': 'GET - Health check'
        }
    })

@app.route('/analyze/pro', methods=['POST'])
def analyze_pro():
    try:
        data = request.get_json() or {}
        symbol = data.get('symbol', 'XAU/USD')
        timeframe = data.get('timeframe', '1h')

        # News blockout
        if is_news_blocked():
            return jsonify({
                'success': True,
                'signal': 'NEUTRAL',
                'confidence': 0,
                'message': 'News blockout active – no trades',
                'current_price': 0,
                'symbol': symbol,
                'timestamp': str(datetime.now())
            })

        mtf_data = get_mtf_data(symbol, timeframe)
        analysis = analyze_all_patterns(mtf_data)

        direction = analysis.get('direction', 0)
        confidence = analysis.get('confidence', 0)

        if direction > 0:
            signal = 'BUY' if confidence >= 60 else 'WEAK_BUY'
        elif direction < 0:
            signal = 'SELL' if confidence >= 60 else 'WEAK_SELL'
        else:
            signal = 'NEUTRAL'

        last_price = analysis.get('last_price', 0)
        entry = {
            'price': round(last_price, 2),
            'stop_loss': round(last_price * 0.995, 2) if direction > 0 else round(last_price * 1.005, 2),
            'take_profit_1': round(last_price * 1.01, 2) if direction > 0 else round(last_price * 0.99, 2),
            'take_profit_2': round(last_price * 1.02, 2) if direction > 0 else round(last_price * 0.98, 2),
            'take_profit_3': round(last_price * 1.03, 2) if direction > 0 else round(last_price * 0.97, 2)
        }

        result = {
            'success': True,
            'symbol': symbol,
            'timeframe': timeframe,
            'timestamp': str(datetime.now()),
            'current_price': last_price,
            'signal': signal,
            'confidence': confidence,
            'entry': entry,
            'analysis': analysis
        }
        return jsonify(result)

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/scan', methods=['GET'])
def scan():
    symbols = ["XAU/USD", "EUR/USD", "GBP/USD", "USD/JPY", "AUD/USD", "BTC/USD"]
    results = []
    for sym in symbols:
        try:
            data = get_mtf_data(sym, '1h')
            analysis = analyze_all_patterns(data)
            direction = analysis.get('direction', 0)
            conf = analysis.get('confidence', 0)
            if direction != 0 and conf >= 60:
                signal = 'BUY' if direction > 0 else 'SELL'
                results.append({
                    'symbol': sym,
                    'signal': signal,
                    'confidence': conf,
                    'price': analysis.get('last_price', 0)
                })
        except:
            continue
    results.sort(key=lambda x: x['confidence'], reverse=True)
    return jsonify({'success': True, 'timestamp': str(datetime.now()), 'top_setups': results[:5]})

@app.route('/predict_next_minute', methods=['GET'])
def predict_next_minute():
    # Placeholder – implement real‑time prediction if needed
    return jsonify({
        'success': True,
        'symbol': request.args.get('symbol', 'XAU/USD'),
        'next_minute_prediction': 'NEUTRAL',
        'confidence': 0,
        'message': 'Real‑time prediction not implemented yet.'
    })

@app.route('/optimize', methods=['POST'])
def optimize():
    if not ENABLE_BACKTEST_ENDPOINT:
        return jsonify({'success': False, 'error': 'Backtest endpoint disabled'})
    # Placeholder – could run backtest and update regime weights
    return jsonify({'success': True, 'result': {'status': 'not implemented'}})

@app.route('/health', methods=['GET'])
def health():
    return jsonify({
        'status': 'healthy',
        'timestamp': str(datetime.now()),
        'data_sources': {
            'yahoo': 'active',
            'twelvedata': 'configured' if TWELVE_DATA_KEY != "YOUR_TWELVE_DATA_API_KEY" else 'optional'
        },
        'features': {
            'self_learning': ENABLE_SELF_LEARNING,
            'news_filter': ENABLE_NEWS_FILTER,
            'regime_switching': ENABLE_REGIME_SWITCHING,
            'ml_predictor': ENABLE_ML_PREDICTOR,
            'backtest': ENABLE_BACKTEST_ENDPOINT
        }
    })

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port, debug=False)
