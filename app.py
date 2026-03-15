from flask import Flask, request, jsonify
from flask_cors import CORS
import numpy as np
import json
import sys
import os
from datetime import datetime

app = Flask(__name__)
CORS(app)

# ============================================
# SECTION 1: FVG DETECTION
# ============================================
def detect_fvgs(high, low, close):
    """Fair Value Gaps Detection"""
    fvgs = []
    for i in range(2, len(high)):
        if i >= len(high) or i >= len(low) or i >= len(close):
            continue
            
        # Bullish FVG (gap up)
        if low[i-1] > high[i-2] and low[i] > high[i-1]:
            fvgs.append({
                'type': 'BULLISH_FVG',
                'level': round((high[i-2] + low[i-1]) / 2, 5),
                'top': high[i-2],
                'bottom': low[i-1],
                'index': i,
                'status': 'ACTIVE'
            })
        # Bearish FVG (gap down)
        if high[i-1] < low[i-2] and high[i] < low[i-1]:
            fvgs.append({
                'type': 'BEARISH_FVG',
                'level': round((low[i-2] + high[i-1]) / 2, 5),
                'top': low[i-2],
                'bottom': high[i-1],
                'index': i,
                'status': 'ACTIVE'
            })
    return fvgs

# ============================================
# SECTION 2: ORDER BLOCKS DETECTION
# ============================================
def detect_order_blocks(high, low, close):
    """Order Blocks Detection"""
    order_blocks = []
    for i in range(5, len(close)-5):
        # Calculate move strength
        future_move = abs(close[i+3] - close[i])
        avg_move = 0
        count = 0
        for j in range(i-3, i+3):
            if j > 0 and j < len(close)-1:
                avg_move += abs(close[j] - close[j-1])
                count += 1
        if count > 0:
            avg_move = avg_move / count
        
        if future_move > avg_move * 2:  # Strong impulse
            direction = 'BULLISH_OB' if close[i+3] > close[i] else 'BEARISH_OB'
            order_blocks.append({
                'type': direction,
                'high': high[i],
                'low': low[i],
                'close': close[i],
                'index': i
            })
    return order_blocks

# ============================================
# SECTION 3: LIQUIDITY LEVELS
# ============================================
def detect_liquidity(high, low, close):
    """Liquidity Levels Detection"""
    liquidity = {'buyside': [], 'sellside': []}
    
    for i in range(2, len(close)-2):
        # Swing High (Buyside Liquidity)
        if high[i] > high[i-1] and high[i] > high[i-2] and \
           high[i] > high[i+1] and high[i] > high[i+2]:
            liquidity['buyside'].append({
                'price': high[i],
                'index': i,
                'taken': False
            })
        
        # Swing Low (Sellside Liquidity)
        if low[i] < low[i-1] and low[i] < low[i-2] and \
           low[i] < low[i+1] and low[i] < low[i+2]:
            liquidity['sellside'].append({
                'price': low[i],
                'index': i,
                'taken': False
            })
    return liquidity

# ============================================
# SECTION 4: MARKET STRUCTURE SHIFT
# ============================================
def detect_mss(high, low, close):
    """Market Structure Shift Detection"""
    structure = []
    mss_list = []
    
    for i in range(5, len(close)-5):
        recent_highs = 0
        recent_lows = 0
        for j in range(i-5, i):
            if j >= 0:
                recent_highs = max(recent_highs, high[j])
                if recent_lows == 0:
                    recent_lows = low[j]
                else:
                    recent_lows = min(recent_lows, low[j])
        
        # Check for shift
        if close[i] > recent_highs:  # Broke above
            structure.append({
                'type': 'BOS_BULLISH',
                'level': close[i],
                'index': i
            })
        
        elif close[i] < recent_lows:  # Broke below
            structure.append({
                'type': 'BOS_BEARISH',
                'level': close[i],
                'index': i
            })
    
    return structure, mss_list

# ============================================
# SECTION 5: ICT OPTIMAL TRADE ENTRY
# ============================================
def detect_ote(high, low, close):
    """Optimal Trade Entry - Fibonacci Levels"""
    ote_zones = []
    
    for i in range(20, len(close)):
        swing_high = 0
        swing_low = 0
        for j in range(i-20, i):
            if j >= 0:
                swing_high = max(swing_high, high[j])
                if swing_low == 0:
                    swing_low = low[j]
                else:
                    swing_low = min(swing_low, low[j])
        
        if swing_high > swing_low:
            range_size = swing_high - swing_low
            
            # OTE zones (62-70% retracement)
            ote_low = swing_high - (range_size * 0.70)
            ote_high = swing_high - (range_size * 0.62)
            
            ote_zones.append({
                'type': 'OTE_LONG',
                'entry_min': round(ote_low, 5),
                'entry_max': round(ote_high, 5),
                'stop': swing_low,
                'target': swing_high,
                'index': i
            })
    
    return ote_zones

# ============================================
# SECTION 6: BREAKER BLOCKS
# ============================================
def detect_breakers(high, low, close):
    """Breaker Blocks Detection"""
    breakers = []
    
    for i in range(10, len(close)-10):
        prev_high = 0
        prev_low = 0
        for j in range(i-10, i):
            if j >= 0:
                prev_high = max(prev_high, high[j])
                if prev_low == 0:
                    prev_low = low[j]
                else:
                    prev_low = min(prev_low, low[j])
        
        # Check if price broke and flipped
        if close[i] > prev_high:  # Broke above
            for j in range(i+1, min(i+20, len(close))):
                if prev_high <= close[j] <= prev_high * 1.01:
                    breakers.append({
                        'type': 'BREAKER_BULLISH',
                        'entry': prev_high,
                        'stop': prev_low,
                        'index': j
                    })
                    break
        
        elif close[i] < prev_low:  # Broke below
            for j in range(i+1, min(i+20, len(close))):
                if prev_low >= close[j] >= prev_low * 0.99:
                    breakers.append({
                        'type': 'BREAKER_BEARISH',
                        'entry': prev_low,
                        'stop': prev_high,
                        'index': j
                    })
                    break
    
    return breakers

# ============================================
# SECTION 7: MAIN ANALYZE ENDPOINT
# ============================================
@app.route('/', methods=['GET'])
def home():
    return jsonify({
        'status': 'SMC/ICT API Ready',
        'message': 'Send POST request to /analyze with price data',
        'python_version': sys.version,
        'endpoints': ['/analyze - POST with price data'],
        'patterns': ['FVG', 'Order Blocks', 'Liquidity', 'MSS', 'OTE', 'Breaker Blocks']
    })

@app.route('/analyze', methods=['POST'])
def analyze():
    try:
        data = request.get_json()
        prices = data.get('prices', [])
        
        if len(prices) < 10:
            return jsonify({
                'success': False,
                'error': 'Need at least 10 price points',
                'received': len(prices)
            })
        
        # Create synthetic high/low from prices
        high = prices
        low = [p * 0.998 for p in prices]  # Approximate low
        close = prices
        
        # Detect all patterns
        fvgs = detect_fvgs(high, low, close)
        order_blocks = detect_order_blocks(high, low, close)
        liquidity = detect_liquidity(high, low, close)
        structure, mss = detect_mss(high, low, close)
        ote_zones = detect_ote(high, low, close)
        breakers = detect_breakers(high, low, close)
        
        # Generate entry signals
        signals = []
        if len(fvgs) > 0 and len(order_blocks) > 0:
            signals.append({
                'type': 'BUY_SIGNAL',
                'confidence': 'HIGH',
                'reason': ['FVG', 'Order Block'],
                'entry': fvgs[-1]['level']
            })
        
        return jsonify({
            'success': True,
            'data_points': len(prices),
            'patterns': {
                'fvgs': {
                    'count': len(fvgs),
                    'data': fvgs[-3:] if len(fvgs) > 3 else fvgs
                },
                'order_blocks': {
                    'count': len(order_blocks),
                    'data': order_blocks[-3:] if len(order_blocks) > 3 else order_blocks
                },
                'liquidity': {
                    'buyside': len(liquidity['buyside']),
                    'sellside': len(liquidity['sellside'])
                },
                'market_structure': {
                    'count': len(structure),
                    'data': structure[-3:] if len(structure) > 3 else structure
                },
                'ote_zones': {
                    'count': len(ote_zones),
                    'data': ote_zones[-2:] if len(ote_zones) > 2 else ote_zones
                },
                'breakers': {
                    'count': len(breakers),
                    'data': breakers[-2:] if len(breakers) > 2 else breakers
                }
            },
            'signals': signals,
            'analysis_time': str(datetime.now())
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'error_type': type(e).__name__
        })

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
