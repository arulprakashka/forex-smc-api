from flask import Flask, jsonify
import sys

app = Flask(__name__)

@app.route('/')
def home():
    return jsonify({
        'status': 'API Ready',
        'python': sys.version
    })

if __name__ == '__main__':
    app.run()
