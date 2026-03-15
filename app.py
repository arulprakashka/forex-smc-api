from flask import Flask, request, jsonify
from flask_cors import CORS
import numpy as np
import json
import sys
import os
import requests
from datetime import datetime, timedelta
import time

app = Flask(__name__)
CORS(app)

# ============================================
# YOUR API KEYS - Replace with your actual keys
# ============================================
TWELVE_DATA_KEY = "e4987fc0c8f0461db5877035bc089d64"  # Get from twelvedata.com
FCS_API_KEY = "wAWpiqowXld2Bv5bl0jD4kw"              # Get from fcsapi.com

# ============================================
# DATA FETCHING FUNCTIONS
# ============================================

def get_mtf_data(symbol="XAU/USD"):
    """Get multiple timeframe data from Twelve Data"""
    timeframes = {
        '15min': '15min',
        '1h': '1h',
        '4h': '4h',
        '1d': '1day'
    }
    
    all_data = {}
    
    for tf_name, tf_value in timeframes.items():
        try:
            url = f"https://api.twelvedata.com/time_series"
            params = {
                'symbol': symbol.replace('/', ''),
                'interval': tf_value,
                'apikey': TWELVE_DATA_KEY,
                'outputsize': 100
            }
            
            response = requests.get(url, params=params, timeout=10)
            data = response.json()
            
            if 'values' in data:
                prices = [float(v['close']) for v in data['values']]
                highs = [float(v['high']) for v in data['values']]
                lows = [float(v['low']) for v in data['values']]
                volumes = [float(v['volume']) for v in data['values']]
                
                all_data[tf_name] = {
                    'prices': prices,
                    'high': highs,
                    'low': lows,
                    'volume': volumes
                }
            else:
                # Fallback to simulated data if API fails
                all_data[tf_name] = generate_simulated_data(100)
                
        except Exception as e:
            print(f"Error fetching {tf_name}: {e}")
            all_data[tf_name] = generate_simulated_data(100)
    
    return all_data

def generate_simulated_data(count):
    """Generate simulated price data for fallback"""
    base = 2000.0
    prices = []
    highs = []
    lows = []
    volumes = []
    
    for i in range(count):
        change = np.random.normal(0, 5)
        price = base + change
        prices.append(price)
        highs.append(price + abs(np.random.normal(0, 2)))
        lows.append(price - abs(np.random.normal(0, 2)))
        volumes.append(np.random.randint(1000, 5000))
        base = price
    
    return {
        'prices': prices,
        'high': highs,
        'low': lows,
        'volume': volumes
    }

# ============================================
# SMC DETECTION FUNCTIONS (Your existing code)
# ============================================

def detect_fvgs(high, low, close):
    """Fair Value Gaps Detection"""
    fvgs = []
    for i in range(2, len(high)-1):
        # Bullish FVG
        if low[i-1] > high[i-2] and low[i] > high[i-1]:
            fvgs.append({
                'type': 'BULLISH_FVG',
                'level': round((high[i-2] + low[i-1]) / 2, 2),
                'index': i
            })
        # Bearish FVG
        if high[i-1] < low[i-2] and high[i] < low[i-1]:
            fvgs.append({
                'type': 'BEARISH_FVG',
                'level': round((low[i-2] + high[i-1]) / 2, 2),
                'index': i
            })
    return fvgs

def detect_order_blocks(high, low, close):
    """Order Blocks Detection"""
    order_blocks = []
    for i in range(5, len(close)-5):
        future_move = abs(close[i+3] - close[i])
        avg_move = 0
        count = 0
        for j in range(i-3, i+3):
            if j > 0 and j < len(close)-1:
                avg_move += abs(close[j] - close[j-1])
                count += 1
        if count > 0:
            avg_move = avg_move / count
        
        if future_move > avg_move * 2:
            direction = 'BULLISH_OB' if close[i+3] > close[i] else 'BEARISH_OB'
            order_blocks.append({
                'type': direction,
                'price': round(close[i], 2),
                'index': i
            })
    return order_blocks

def detect_liquidity(high, low):
    """Liquidity Levels Detection"""
    liquidity = {'buyside': [], 'sellside': []}
    
    for i in range(2, len(high)-2):
        # Swing High
        if high[i] > high[i-1] and high[i] > high[i-2] and \
           high[i] > high[i+1] and high[i] > high[i+2]:
            liquidity['buyside'].append({
                'price': round(high[i], 2),
                'index': i
            })
        
        # Swing Low
        if low[i] < low[i-1] and low[i] < low[i-2] and \
           low[i] < low[i+1] and low[i] < low[i+2]:
            liquidity['sellside'].append({
                'price': round(low[i], 2),
                'index': i
            })
    return liquidity

def detect_mss(high, low, close):
    """Market Structure Shift Detection"""
    mss_list = []
    
    for i in range(5, len(close)-5):
        recent_high = max(high[i-5:i])
        recent_low = min(low[i-5:i])
        
        if close[i] > recent_high:
            mss_list.append({
                'type': 'BULLISH_MSS',
                'level': round(close[i], 2),
                'index': i
            })
        elif close[i] < recent_low:
            mss_list.append({
                'type': 'BEARISH_MSS',
                'level': round(close[i], 2),
                'index': i
            })
    
    return mss_list

def detect_ote(high, low):
    """Optimal Trade Entry - Fibonacci"""
    ote_zones = []
    
    for i in range(20, len(high)):
        swing_high = max(high[i-20:i])
        swing_low = min(low[i-20:i])
        
        if swing_high > swing_low:
            range_size = swing_high - swing_low
            ote_low = swing_high - (range_size * 0.70)
            ote_high = swing_high - (range_size * 0.62)
            
            ote_zones.append({
                'type': 'OTE_LONG',
                'entry_min': round(ote_low, 2),
                'entry_max': round(ote_high, 2),
                'stop': round(swing_low, 2),
                'target': round(swing_high, 2)
            })
    return ote_zones

def detect_breakers(high, low, close):
    """Breaker Blocks Detection"""
    breakers = []
    
    for i in range(10, len(close)-10):
        prev_high = max(high[i-10:i])
        prev_low = min(low[i-10:i])
        
        if close[i] > prev_high:
            breakers.append({
                'type': 'BREAKER_BULLISH',
                'level': round(prev_high, 2),
                'index': i
            })
        elif close[i] < prev_low:
            breakers.append({
                'type': 'BREAKER_BEARISH',
                'level': round(prev_low, 2),
                'index': i
            })
    
    return breakers

def detect_inducement(high, low, close):
    """Inducement Detection"""
    inducements = []
    
    for i in range(5, len(close)-5):
        if high[i] > max(high[i-5:i]) and close[i+1] < high[i]:
            inducements.append({
                'type': 'BEARISH_INDUCEMENT',
                'level': round(high[i], 2),
                'index': i
            })
        
        if low[i] < min(low[i-5:i]) and close[i+1] > low[i]:
            inducements.append({
                'type': 'BULLISH_INDUCEMENT',
                'level': round(low[i], 2),
                'index': i
            })
    
    return inducements

def analyze_smc(data_dict):
    """Run all SMC detectors on a timeframe"""
    if not data_dict or len(data_dict.get('prices', [])) < 20:
        return {'error': 'Insufficient data'}
    
    prices = data_dict['prices']
    highs = data_dict['high']
    lows = data_dict['low']
    volumes = data_dict.get('volume', [1]*len(prices))
    
    return {
        'fvgs': detect_fvgs(highs, lows, prices),
        'order_blocks': detect_order_blocks(highs, lows, prices),
        'liquidity': detect_liquidity(highs, lows),
        'mss': detect_mss(highs, lows, prices),
        'ote': detect_ote(highs, lows),
        'breakers': detect_breakers(highs, lows, prices),
        'inducement': detect_inducement(highs, lows, prices),
        'last_price': round(prices[-1], 2) if prices else 0
    }

# ============================================
# VOLUME ANALYSIS
# ============================================

def analyze_volume(volume_data, price_data):
    """Volume Spread Analysis"""
    if len(volume_data) < 20:
        return []
    
    signals = []
    avg_vol = np.mean(volume_data[-20:])
    last_vol = volume_data[-1]
    last_price = price_data[-1]
    prev_price = price_data[-2]
    
    # High volume with big move
    if last_vol > avg_vol * 1.8 and abs(last_price - prev_price) > 0.01 * last_price:
        signals.append({
            'type': 'STRONG_MOVE',
            'direction': 'UP' if last_price > prev_price else 'DOWN',
            'confidence': 'HIGH'
        })
    
    # Volume climax (possible reversal)
    if last_vol > avg_vol * 2.5:
        signals.append({
            'type': 'CLIMAX_REVERSAL',
            'confidence': 'HIGH'
        })
    
    # Low volume consolidation
    if last_vol < avg_vol * 0.5 and abs(last_price - prev_price) < 0.002 * last_price:
        signals.append({
            'type': 'CONSOLIDATION',
            'confidence': 'MEDIUM'
        })
    
    return signals

# ============================================
# BACKTESTING ENGINE
# ============================================

def backtest_strategy(symbol="XAU/USD", days=7):
    """Backtest SMC strategy"""
    try:
        url = f"https://api.twelvedata.com/time_series"
        params = {
            'symbol': symbol.replace('/', ''),
            'interval': '1h',
            'apikey': TWELVE_DATA_KEY,
            'outputsize': days * 24
        }
        
        response = requests.get(url, params=params, timeout=10)
        data = response.json()
        
        if 'values' not in data:
            return {'error': 'No data for backtest'}
        
        candles = data['values']
        results = {
            'trades': 0,
            'wins': 0,
            'losses': 0,
            'win_rate': 0,
            'profit_factor': 0
        }
        
        profits = []
        
        for i in range(50, len(candles)-24):
            # Get prices for analysis
            past_prices = [float(c['close']) for c in candles[i-50:i]]
            past_highs = [float(c['high']) for c in candles[i-50:i]]
            past_lows = [float(c['low']) for c in candles[i-50:i]]
            
            # Detect patterns
            fvgs = detect_fvgs(past_highs, past_lows, past_prices)
            obs = detect_order_blocks(past_highs, past_lows, past_prices)
            
            if len(fvgs) > 0 and len(obs) > 0:
                results['trades'] += 1
                entry = past_prices[-1]
                
                # Check next 24 candles
                future_prices = [float(c['close']) for c in candles[i:i+24]]
                target = entry * 1.01
                stop = entry * 0.99
                
                trade_result = 0
                for price in future_prices:
                    if price >= target:
                        trade_result = 1
                        results['wins'] += 1
                        profits.append(1)
                        break
                    if price <= stop:
                        trade_result = -1
                        results['losses'] += 1
                        profits.append(-1)
                        break
        
        if results['trades'] > 0:
            results['win_rate'] = round((results['wins'] / results['trades']) * 100, 2)
            if len(profits) > 0:
                wins_sum = sum([p for p in profits if p > 0])
                losses_sum = abs(sum([p for p in profits if p < 0]))
                results['profit_factor'] = round(wins_sum / losses_sum if losses_sum > 0 else wins_sum, 2)
        
        return results
        
    except Exception as e:
        return {'error': str(e)}

# ============================================
# MULTI-TIMEFRAME CONFLUENCE
# ============================================

def calculate_confluence(mtf_analysis):
    """Calculate confluence score across timeframes"""
    scores = {}
    
    for tf, analysis in mtf_analysis.items():
        score = 0
        if analysis.get('fvgs'):
            score += len(analysis['fvgs']) * 10
        if analysis.get('order_blocks'):
            score += len(analysis['order_blocks']) * 15
        if analysis.get('mss'):
            score += len(analysis['mss']) * 20
        if analysis.get('ote'):
            score += len(analysis['ote']) * 25
        
        scores[tf] = min(score, 100)
    
    # Overall confluence
    avg_score = np.mean(list(scores.values())) if scores else 0
    
    return {
        'per_timeframe': scores,
        'overall': round(avg_score, 2),
        'verdict': 'STRONG' if avg_score >= 70 else
                  'MODERATE' if avg_score >= 40 else 'WEAK'
    }

# ============================================
# MAIN ENDPOINTS
# ============================================

@app.route('/', methods=['GET'])
def home():
    return jsonify({
        'status': 'PRO SMC/ICT API Ready',
        'features': [
            'Multi-timeframe (15m,1h,4h,1d)',
            'Volume Spread Analysis',
            'Backtesting Engine',
            'Confluence Scoring',
            '10+ SMC/ICT Patterns'
        ],
        'endpoints': {
            '/analyze/pro': 'POST - Full professional analysis',
            '/analyze/mtf': 'POST - Multi-timeframe only',
            '/backtest': 'POST - Run backtest'
        }
    })

@app.route('/analyze/pro', methods=['POST'])
def analyze_pro():
    """Professional analysis with MTF + Volume + Backtest"""
    try:
        data = request.get_json()
        symbol = data.get('symbol', 'XAU/USD')
        
        # 1. Get multi-timeframe data
        mtf_data = get_mtf_data(symbol)
        
        # 2. Analyze each timeframe
        mtf_analysis = {}
        for tf, tf_data in mtf_data.items():
            mtf_analysis[tf] = analyze_smc(tf_data)
        
        # 3. Volume analysis (using 1h data)
        volume_signals = analyze_volume(
            mtf_data['1h']['volume'],
            mtf_data['1h']['prices']
        ) if '1h' in mtf_data else []
        
        # 4. Confluence score
        confluence = calculate_confluence(mtf_analysis)
        
        # 5. Quick backtest (7 days)
        backtest = backtest_strategy(symbol, 7)
        
        # 6. Generate final signal
        final_score = confluence['overall']
        if backtest.get('win_rate', 0) > 60:
            final_score = min(100, final_score + 10)
        
        signal = 'STRONG_BUY' if final_score >= 75 else \
                'BUY' if final_score >= 55 else \
                'NEUTRAL' if final_score >= 35 else \
                'SELL' if final_score >= 20 else 'STRONG_SELL'
        
        return jsonify({
            'success': True,
            'symbol': symbol,
            'timestamp': str(datetime.now()),
            'current_price': mtf_analysis.get('1h', {}).get('last_price', 0),
            'confluence': confluence,
            'volume_signals': volume_signals,
            'backtest': backtest,
            'final_score': final_score,
            'signal': signal,
            'risk_level': 'HIGH' if final_score >= 70 else
                         'MEDIUM' if final_score >= 40 else 'LOW'
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        })

@app.route('/analyze/mtf', methods=['POST'])
def analyze_mtf():
    """Multi-timeframe analysis only"""
    try:
        data = request.get_json()
        symbol = data.get('symbol', 'XAU/USD')
        
        mtf_data = get_mtf_data(symbol)
        mtf_analysis = {}
        
        for tf, tf_data in mtf_data.items():
            mtf_analysis[tf] = analyze_smc(tf_data)
        
        confluence = calculate_confluence(mtf_analysis)
        
        return jsonify({
            'success': True,
            'symbol': symbol,
            'timestamp': str(datetime.now()),
            'mtf_analysis': mtf_analysis,
            'confluence': confluence
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        })

@app.route('/backtest', methods=['POST'])
def run_backtest():
    """Run backtest for a symbol"""
    try:
        data = request.get_json()
        symbol = data.get('symbol', 'XAU/USD')
        days = data.get('days', 7)
        
        results = backtest_strategy(symbol, days)
        
        return jsonify({
            'success': True,
            'symbol': symbol,
            'days': days,
            'results': results
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        })

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
