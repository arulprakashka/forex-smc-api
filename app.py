from flask import Flask, request, jsonify
from flask_cors import CORS
import numpy as np
import json
import sys
import os

app = Flask(__name__)
CORS(app)

@app.route('/', methods=['GET'])
def home():
    return jsonify({
        'status': 'SMC/ICT API Ready',
        'message': 'Send POST request to /analyze with price data',
        'python_version': sys.version
    })

@app.route('/analyze', methods=['POST'])
def analyze():
    try:
        data = request.json
        prices = data.get('prices', [])
        
        # Basic FVG detection
        fvgs = []
        for i in range(2, len(prices)-2):
            if len(prices) > i+1 and i-1 >= 0:
                if prices[i] > prices[i-1] and prices[i] > prices[i+1]:
                    fvgs.append({
                        'type': 'BULLISH',
                        'level': prices[i],
                        'index': i
                    })
        
        return jsonify({
            'success': True,
            'fvgs_detected': len(fvgs),
            'fvgs': fvgs,
            'data_points': len(prices)
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
