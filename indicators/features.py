# indicators/features.py
import numpy as np
from datetime import datetime

# ------------------------------------------------------------
# SMC PATTERNS
# ------------------------------------------------------------
def detect_fvgs(high, low, close):
    fvgs = {'bullish': [], 'bearish': []}
    for i in range(2, len(high)-1):
        if low[i-1] > high[i-2] and low[i] > high[i-1]:
            fvgs['bullish'].append({
                'level': round((high[i-2] + low[i-1])/2, 2),
                'top': round(high[i-2], 2),
                'bottom': round(low[i-1], 2),
                'index': i
            })
        if high[i-1] < low[i-2] and high[i] < low[i-1]:
            fvgs['bearish'].append({
                'level': round((low[i-2] + high[i-1])/2, 2),
                'top': round(low[i-2], 2),
                'bottom': round(high[i-1], 2),
                'index': i
            })
    return fvgs

def detect_order_blocks(high, low, close, volume):
    obs = {'bullish': [], 'bearish': []}
    for i in range(5, len(close)-5):
        future_move = abs(close[i+3] - close[i])
        past_vol = np.std(close[i-10:i]) if i >= 10 else 0.01
        if future_move > past_vol * 2:
            direction = 'bullish' if close[i+3] > close[i] else 'bearish'
            vol_confirmed = volume[i] > np.mean(volume[i-10:i]) * 1.3 if i >= 10 else False
            ob = {
                'price': round(close[i], 2),
                'high': round(high[i], 2),
                'low': round(low[i], 2),
                'volume': round(volume[i], 2),
                'confirmed': bool(vol_confirmed),
                'index': i
            }
            if direction == 'bullish':
                obs['bullish'].append(ob)
            else:
                obs['bearish'].append(ob)
    return obs

def detect_liquidity(high, low):
    liquidity = {'buyside': [], 'sellside': [], 'internal': []}
    for i in range(2, len(high)-2):
        if high[i] > high[i-1] and high[i] > high[i-2] and high[i] > high[i+1] and high[i] > high[i+2]:
            liquidity['buyside'].append({'price': round(high[i], 2), 'index': i, 'type': 'SWING_HIGH'})
        if low[i] < low[i-1] and low[i] < low[i-2] and low[i] < low[i+1] and low[i] < low[i+2]:
            liquidity['sellside'].append({'price': round(low[i], 2), 'index': i, 'type': 'SWING_LOW'})
        if i > 5:
            mid = (max(high[i-5:i]) + min(low[i-5:i])) / 2
            liquidity['internal'].append({'price': round(mid, 2), 'index': i, 'type': 'EQUILIBRIUM'})
    return liquidity

def detect_market_structure(high, low, close):
    structure = {'bos': [], 'mss': []}
    swing_highs, swing_lows = [], []
    for i in range(2, len(high)-2):
        if high[i] > high[i-1] and high[i] > high[i-2] and high[i] > high[i+1] and high[i] > high[i+2]:
            swing_highs.append({'price': high[i], 'index': i})
        if low[i] < low[i-1] and low[i] < low[i-2] and low[i] < low[i+1] and low[i] < low[i+2]:
            swing_lows.append({'price': low[i], 'index': i})
    for i in range(1, len(swing_highs)):
        if swing_highs[i]['price'] > swing_highs[i-1]['price']:
            structure['bos'].append({'type': 'BULLISH_BOS', 'level': round(swing_highs[i]['price'],2), 'index': swing_highs[i]['index']})
            structure['mss'].append({'type': 'BULLISH_MSS', 'level': round(swing_highs[i]['price'],2), 'index': swing_highs[i]['index']})
    for i in range(1, len(swing_lows)):
        if swing_lows[i]['price'] < swing_lows[i-1]['price']:
            structure['bos'].append({'type': 'BEARISH_BOS', 'level': round(swing_lows[i]['price'],2), 'index': swing_lows[i]['index']})
            structure['mss'].append({'type': 'BEARISH_MSS', 'level': round(swing_lows[i]['price'],2), 'index': swing_lows[i]['index']})
    return structure

def detect_breaker_blocks(high, low, close):
    breakers = {'bullish': [], 'bearish': []}
    for i in range(10, len(close)-10):
        prev_high = max(high[i-10:i]); prev_low = min(low[i-10:i])
        if close[i] > prev_high:
            for j in range(i+1, min(i+15, len(close))):
                if prev_high >= close[j] >= prev_high * 0.99:
                    breakers['bullish'].append({
                        'entry': round(prev_high,2),
                        'stop': round(prev_low,2),
                        'target': round(high[i]*1.02,2),
                        'index': j
                    })
                    break
        if close[i] < prev_low:
            for j in range(i+1, min(i+15, len(close))):
                if prev_low <= close[j] <= prev_low * 1.01:
                    breakers['bearish'].append({
                        'entry': round(prev_low,2),
                        'stop': round(prev_high,2),
                        'target': round(low[i]*0.98,2),
                        'index': j
                    })
                    break
    return breakers

def detect_inducement(high, low, close):
    inducements = {'bullish': [], 'bearish': []}
    for i in range(5, len(close)-5):
        if low[i] < min(low[i-5:i]) and close[i+1] > low[i]:
            inducements['bullish'].append({'level': round(low[i],2), 'index': i, 'target': round(high[i]*1.02,2)})
        if high[i] > max(high[i-5:i]) and close[i+1] < high[i]:
            inducements['bearish'].append({'level': round(high[i],2), 'index': i, 'target': round(low[i]*0.98,2)})
    return inducements

def detect_equilibrium(high, low, close):
    eq_zones = []
    for i in range(20, len(close)):
        vwap = np.mean(close[i-20:i])
        std = np.std(close[i-20:i])
        eq_zones.append({'mean': round(vwap,2), 'upper': round(vwap+std,2), 'lower': round(vwap-std,2), 'index': i})
    return eq_zones[-5:] if eq_zones else []

def detect_ote(high, low):
    ote = {'long': [], 'short': []}
    for i in range(30, len(high)):
        swing_high = max(high[i-30:i]); swing_low = min(low[i-30:i])
        if swing_high > swing_low:
            range_size = swing_high - swing_low
            ote['long'].append({
                'entry_min': round(swing_high - range_size*0.70,2),
                'entry_max': round(swing_high - range_size*0.62,2),
                'stop': round(swing_low,2),
                'target': round(swing_high,2)
            })
            ote['short'].append({
                'entry_min': round(swing_low + range_size*0.62,2),
                'entry_max': round(swing_low + range_size*0.70,2),
                'stop': round(swing_high,2),
                'target': round(swing_low,2)
            })
    return ote

# ------------------------------------------------------------
# ICT PATTERNS
# ------------------------------------------------------------
def detect_silver_bullet(times, high, low):
    silver = []
    for i in range(len(times)-10):
        try:
            tstr = times[i] if i<len(times) else ''
            hour = 0
            if isinstance(tstr, str) and ':' in tstr:
                hour = int(tstr.split()[1].split(':')[0]) if ' ' in tstr else int(tstr.split(':')[0])
            else:
                hour = i % 24
            if 10 <= hour <= 11:
                silver.append({
                    'time': str(tstr),
                    'high': round(max(high[i:i+5]),2),
                    'low': round(min(low[i:i+5]),2)
                })
        except:
            pass
    return silver[-3:] if silver else []

def detect_kill_zones(times):
    zones = []
    for i, ts in enumerate(times[:100]):
        try:
            tstr = ts if isinstance(ts, str) else ''
            hour = 0
            if isinstance(tstr, str) and ':' in tstr:
                hour = int(tstr.split()[1].split(':')[0]) if ' ' in tstr else int(tstr.split(':')[0])
            else:
                hour = i % 24
            if 2 <= hour <= 5:
                zones.append({'zone':'LONDON_OPEN','time':str(ts),'index':i})
            elif 7 <= hour <= 10:
                zones.append({'zone':'NY_OPEN','time':str(ts),'index':i})
            elif 11 <= hour <= 12:
                zones.append({'zone':'LONDON_CLOSE','time':str(ts),'index':i})
            elif 19 <= hour <= 22:
                zones.append({'zone':'ASIA_SESSION','time':str(ts),'index':i})
        except:
            pass
    return zones[-10:] if zones else []

def detect_power_of_3(high, low, close):
    power3 = []
    for i in range(50, len(close)-30):
        pre = max(high[i-20:i]) - min(low[i-20:i])
        mid = max(high[i:i+15]) - min(low[i:i+15])
        post = max(high[i+15:i+30]) - min(low[i+15:i+30])
        if mid < pre * 0.4 and post > pre * 1.6:
            direction = 'UP' if close[i+25] > close[i-15] else 'DOWN'
            power3.append({
                'type':'POWER_OF_3',
                'accumulation':i-20,
                'manipulation':i,
                'distribution':i+15,
                'direction':direction
            })
    return power3[-3:] if power3 else []

def detect_judas_swing(high, low, close):
    judas = []
    for i in range(20, len(close)-10):
        recent_high = max(high[i-10:i]); recent_low = min(low[i-10:i])
        if high[i] > recent_high * 1.005 and close[i+1] < high[i]:
            judas.append({
                'type':'JUDAS_SHORT',
                'entry':round(high[i],2),
                'stop':round(high[i]*1.005,2),
                'target':round(recent_low,2),
                'index':i
            })
        if low[i] < recent_low * 0.995 and close[i+1] > low[i]:
            judas.append({
                'type':'JUDAS_LONG',
                'entry':round(low[i],2),
                'stop':round(low[i]*0.995,2),
                'target':round(recent_high,2),
                'index':i
            })
    return judas[-5:] if judas else []

def detect_turtle_soup(high, low, close):
    soup = []
    for i in range(20, len(close)-5):
        ph = max(high[i-20:i]); pl = min(low[i-20:i])
        if close[i] > ph and close[i+1] < ph:
            soup.append({
                'type':'TURTLE_SOUP_SHORT',
                'entry':round(ph,2),
                'stop':round(ph*1.01,2),
                'target':round(pl,2),
                'index':i
            })
        if close[i] < pl and close[i+1] > pl:
            soup.append({
                'type':'TURTLE_SOUP_LONG',
                'entry':round(pl,2),
                'stop':round(pl*0.99,2),
                'target':round(ph,2),
                'index':i
            })
    return soup[-5:] if soup else []

# ------------------------------------------------------------
# WYCKOFF, VSA, ORDER FLOW, ETC.
# ------------------------------------------------------------
def detect_wyckoff(high, low, close, volume):
    wyckoff = {'phases':[],'springs':[],'upthrusts':[]}
    for i in range(50, len(close)):
        if volume[i] > np.mean(volume[i-20:i])*2.5:
            wyckoff['phases'].append({
                'phase':'A_CLIMAX',
                'type':'SELLING' if close[i]<close[i-1] else 'BUYING',
                'price':round(close[i],2),
                'index':i
            })
        rw = max(high[i-30:i]) - min(low[i-30:i])
        ar = np.mean([max(high[j-10:j])-min(low[j-10:j]) for j in range(i-30,i)]) if i>=30 else 0
        if rw < ar * 0.6 and ar>0:
            wyckoff['phases'].append({
                'phase':'B_CAUSE',
                'high':round(max(high[i-30:i]),2),
                'low':round(min(low[i-30:i]),2),
                'index':i
            })
        if low[i] < min(low[i-10:i-5]) and close[i] > low[i]:
            wyckoff['springs'].append({'price':round(low[i],2),'index':i})
        if high[i] > max(high[i-10:i-5]) and close[i] < high[i]:
            wyckoff['upthrusts'].append({'price':round(high[i],2),'index':i})
    return wyckoff

def detect_vsa(high, low, close, volume):
    vsa = []
    for i in range(1, len(close)):
        spread = high[i] - low[i]
        avg_spread = np.mean([high[j]-low[j] for j in range(max(0,i-10),i)]) if i>=10 else spread
        avg_vol = np.mean(volume[max(0,i-10):i]) if i>=10 else volume[i]
        if spread > avg_spread * 1.8 and volume[i] > avg_vol * 1.8:
            vsa.append({
                'type':'STRONG_MOVE',
                'direction':'UP' if close[i]>close[i-1] else 'DOWN',
                'index':i
            })
        if spread < avg_spread * 0.5 and volume[i] > avg_vol * 1.5:
            vsa.append({'type':'ABSORPTION','index':i})
    return vsa[-10:] if vsa else []

def detect_smart_money_reversal(high, low, close, volume):
    reversals = []
    for i in range(5, len(close)-5):
        if close[i] > close[i-1] and close[i-1] < close[i-2] and volume[i] > volume[i-1]*1.4:
            reversals.append({
                'type':'SMR_BULLISH',
                'entry':round(low[i-1],2),
                'stop':round(low[i-2],2),
                'target':round(high[i]*1.02,2),
                'index':i
            })
        if close[i] < close[i-1] and close[i-1] > close[i-2] and volume[i] > volume[i-1]*1.4:
            reversals.append({
                'type':'SMR_BEARISH',
                'entry':round(high[i-1],2),
                'stop':round(high[i-2],2),
                'target':round(low[i]*0.98,2),
                'index':i
            })
    return reversals[-5:] if reversals else []

def detect_order_flow(high, low, close, volume):
    flow = []
    for i in range(20, len(close)):
        delta = close[i] - (high[i]+low[i])/2
        cum_delta = np.sum([close[j] - (high[j]+low[j])/2 for j in range(i-20,i)]) if i>=20 else delta
        std = np.std([close[j] - (high[j]+low[j])/2 for j in range(i-20,i)]) if i>=20 else 1
        if abs(delta) > std * 2:
            direction = 'BUYING' if delta>0 else 'SELLING'
            flow.append({
                'type':f'INSTITUTIONAL_{direction}',
                'delta':round(delta,2),
                'cumulative_delta':round(cum_delta,2),
                'index':i
            })
    return flow[-10:] if flow else []

def analyze_volume_profile(volume, price):
    vp = []
    for i in range(len(volume)-20):
        vp.append({
            'price':round(np.mean(price[i:i+20]),2),
            'volume':round(np.sum(volume[i:i+20]),2)
        })
    return vp[-5:] if vp else []

# ------------------------------------------------------------
# ADVANCED PATTERNS (Stacked Imbalance, Iceberg, VWAP Clouds, etc.)
# ------------------------------------------------------------
def detect_stacked_imbalance(volume, price, high, low):
    if len(volume)<30:
        return {'bullish_stacks':[],'bearish_stacks':[],'max_stack_count':0}
    v_series = np.array(volume[-100:])
    p_series = np.array(price[-100:])
    h_series = np.array(high[-100:])
    l_series = np.array(low[-100:])
    price_min, price_max = min(l_series), max(h_series)
    bin_size = (price_max - price_min)/20 if price_max>price_min else 1
    levels = {}
    for i in range(len(p_series)):
        level = int((p_series[i] - price_min)/bin_size)
        if level not in levels:
            levels[level] = {'buy':0,'sell':0,'price':p_series[i]}
        if p_series[i] > (h_series[i]+l_series[i])/2:
            levels[level]['buy'] += v_series[i]
        else:
            levels[level]['sell'] += v_series[i]
    imbalances = []
    for lvl, d in levels.items():
        total = d['buy']+d['sell']
        if total>0:
            ratio = abs(d['buy']-d['sell'])/total
            if ratio>0.6:
                imbalances.append({
                    'level':lvl,
                    'price':round(d['price'],2),
                    'type':'BULLISH' if d['buy']>d['sell'] else 'BEARISH',
                    'ratio':ratio
                })
    imbalances.sort(key=lambda x:x['level'])
    bullish_stacks, bearish_stacks = [], []
    cur_stack, cur_type = [], None
    for imb in imbalances:
        if not cur_stack:
            cur_stack.append(imb); cur_type=imb['type']
        elif imb['type']==cur_type and imb['level']==cur_stack[-1]['level']+1:
            cur_stack.append(imb)
        else:
            if len(cur_stack)>=2:
                stack = {
                    'type':cur_type,
                    'stack_count':len(cur_stack),
                    'price_start':cur_stack[0]['price'],
                    'price_end':cur_stack[-1]['price'],
                    'avg_ratio':round(sum(x['ratio'] for x in cur_stack)/len(cur_stack),2)
                }
                if cur_type=='BULLISH':
                    bullish_stacks.append(stack)
                else:
                    bearish_stacks.append(stack)
            cur_stack=[imb]; cur_type=imb['type']
    if len(cur_stack)>=2:
        stack = {
            'type':cur_type,
            'stack_count':len(cur_stack),
            'price_start':cur_stack[0]['price'],
            'price_end':cur_stack[-1]['price'],
            'avg_ratio':round(sum(x['ratio'] for x in cur_stack)/len(cur_stack),2)
        }
        if cur_type=='BULLISH':
            bullish_stacks.append(stack)
        else:
            bearish_stacks.append(stack)
    max_stack = max([s['stack_count'] for s in bullish_stacks+bearish_stacks]) if bullish_stacks or bearish_stacks else 0
    signal, conf = None,0
    if max_stack>=3:
        strongest = max(bullish_stacks+bearish_stacks, key=lambda x:x['stack_count'])
        signal = f"{strongest['type']}_STACKED_IMBALANCE"
        conf = 75 + min(5*(strongest['stack_count']-3),20)
    return {
        'bullish_stacks':bullish_stacks,
        'bearish_stacks':bearish_stacks,
        'max_stack_count':max_stack,
        'signal':signal,
        'confidence':conf
    }

def detect_iceberg_orders(volume, price):
    if len(volume)<20:
        return []
    icebergs = []
    v_series = np.array(volume[-100:])
    p_series = np.array(price[-100:])
    for i in range(10, len(v_series)-5):
        avg = np.mean(v_series[max(0,i-20):i])
        if avg==0:
            continue
        vol_ratio = v_series[i]/avg
        price_range = max(p_series[i-5:i+5]) - min(p_series[i-5:i+5])
        avg_range = np.mean([abs(p_series[j]-p_series[j-1]) for j in range(i-5,i)]) if i>5 else price_range
        if vol_ratio > 2.0 and price_range < avg_range * 1.5:
            icebergs.append({
                'type':'ICEBERG_ABSORPTION',
                'price':round(p_series[i],2),
                'volume':int(v_series[i]),
                'vol_ratio':round(vol_ratio,2),
                'index':i+(len(volume)-100),
                'confidence':'HIGH' if vol_ratio>3 else 'MEDIUM'
            })
    for i in range(1, len(v_series)):
        avg = np.mean(v_series[max(0,i-10):i])
        if avg>0 and v_series[i] > avg*2.5:
            price_change = abs(p_series[i]-p_series[i-1])
            if price_change < 0.001 * p_series[i]:
                icebergs.append({
                    'type':'ICEBERG_HIDDEN',
                    'price':round(p_series[i],2),
                    'volume':int(v_series[i]),
                    'index':i+(len(volume)-100),
                    'confidence':'MEDIUM'
                })
    return icebergs[-5:]

def detect_vwap_clouds(high, low, close, volume):
    if len(close)<20:
        return {'levels':{},'signal':None}
    cum_pv, cum_vol = 0,0
    vwap_vals = []
    for i in range(len(close)):
        tp = (high[i]+low[i]+close[i])/3
        cum_pv += tp*volume[i]
        cum_vol += volume[i]
        if cum_vol>0:
            vwap_vals.append(cum_pv/cum_vol)
    if len(vwap_vals)<20:
        return {'levels':{},'signal':None}
    vwap_series = np.array(vwap_vals[-50:])
    std = np.std(vwap_series)
    cur_vwap = vwap_vals[-1]
    cur_price = close[-1]
    levels = {
        'vwap':round(cur_vwap,2),
        'plus_1σ':round(cur_vwap+std,2),
        'plus_2σ':round(cur_vwap+std*2,2),
        'plus_3σ':round(cur_vwap+std*3,2),
        'minus_1σ':round(cur_vwap-std,2),
        'minus_2σ':round(cur_vwap-std*2,2),
        'minus_3σ':round(cur_vwap-std*3,2)
    }
    dist = abs(cur_price-cur_vwap)/cur_vwap*100
    if 
