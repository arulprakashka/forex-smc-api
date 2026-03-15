from flask import Flask, jsonify
import os
import sys

app = Flask(__name__)

@app.route('/')
def home():
    return jsonify({
        'status': 'SMC/ICT API Ready',
        'message': 'Server is running on Render',
        'python': sys.version,
        'port': os.environ.get('PORT', 'Not set')
    })

@app.route('/health')
def health():
    return jsonify({'status': 'healthy'})

if __name__ == '__main__':
    # Render uses PORT environment variable
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port, debug=False)
