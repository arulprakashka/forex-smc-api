from flask import Flask, request, jsonify
from flask_cors import CORS
import numpy as np
import json

app = Flask(__name__)
CORS(app)

@app.route('/', methods=['GET'])
def home():
    return jsonify({
        'status': 'SMC/ICT API Ready',
        'message': 'Send POST request to /analyze with price data'
    })

@app.route('/analyze', methods=['POST'])
def analyze():
    try:
        data = request.json
        prices = data.get('prices', [])
        
        # Basic FVG detection
        fvgs = []
        for i in range(2, len(prices)-2):
            if prices[i] > prices[i-1] and prices[i] > prices[i+1]:
                fvgs.append({
                    'type': 'BULLISH',
                    'level': prices[i],
                    'index': i
                })
        
        return jsonify({
            'success': True,
            'fvgs_detected': len(fvgs),
            'fvgs': fvgs
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        })

if __name__ == '__main__':
    app.run()
