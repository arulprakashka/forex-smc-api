from flask import Flask, request, jsonify
from flask_cors import CORS
import json

app = Flask(__name__)
CORS(app)

@app.route('/')
def home():
    return jsonify({
        'status': 'API Ready',
        'message': 'Send POST to /analyze'
    })

@app.route('/analyze', methods=['POST'])
def analyze():
    try:
        data = request.get_json()
        return jsonify({
            'success': True,
            'received': data
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        })

if __name__ == '__main__':
    app.run()
