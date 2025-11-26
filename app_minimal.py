"""
Minimal Flask App für Railway - CORS optimiert
"""
from flask import Flask, jsonify, request  # request ergänzt
from flask_cors import CORS
import os
import logging

APP_VERSION = "minimal-1.1"

# Logging konfigurieren (Gunicorn leitet stdout/stderr in Logs weiter)
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logging.info(f"🚀 Starte app_minimal Version {APP_VERSION}")

ALLOWED_ORIGINS = [
    "https://ai-chatbot-system-c8204.web.app",
    "https://ai-chatbot-system-c8204.firebaseapp.com",
    "http://localhost:3000",
    "http://127.0.0.1:3000"
]

app = Flask(__name__)

# ✅ OPTIMIERTE CORS-KONFIGURATION
# WICHTIG: supports_credentials muss False sein, wenn withCredentials im Frontend nicht genutzt wird
CORS(app, resources={
    r"/api/*": {
        "origins": ALLOWED_ORIGINS,
        "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        "allow_headers": ["Content-Type", "Authorization"],
        "supports_credentials": False,  # ❗ Auf False gesetzt
        "max_age": 3600
    }
})
logging.info("CORS aktiviert für Origins: %s", ALLOWED_ORIGINS)

@app.route('/')
def root():
    return jsonify({
        'status': 'online',
        'message': 'Minimal Test App läuft',
        'version': APP_VERSION,
        'origins': ALLOWED_ORIGINS
    })

@app.route('/api/health')
def health():
    return jsonify({
        'status': 'ok',
        'message': 'Health endpoint funktioniert',
        'cors_origin': request.headers.get('Origin', 'None'),
        'version': APP_VERSION
    })

# Debug-Endpoint zur Einsicht in Header & Environment
@app.route('/api/debug')
def debug():
    return jsonify({
        'version': APP_VERSION,
        'request_headers': {k: v for k, v in request.headers.items()},
        'env_PORT': os.getenv('PORT'),
        'env_FLASK_ENV': os.getenv('FLASK_ENV'),
        'allowed_origins': ALLOWED_ORIGINS
    })

@app.route('/api/test')
def test():
    return jsonify({
        'test': 'success',
        'message': 'Test endpoint funktioniert'
    })

@app.route('/api/personas')
def get_personas():
    personas = [
        {
            'key': '1',
            'name': 'Data Analyst Expert',
            'temperature': 0.3,
            'top_p': 0.8,
            'top_k': 40
        },
        {
            'key': '2',
            'name': 'Creative Storyteller',
            'temperature': 0.9,
            'top_p': 0.95,
            'top_k': 100
        },
        {
            'key': '3',
            'name': 'Technical Code Assistant',
            'temperature': 0.2,
            'top_p': 0.7,
            'top_k': 30
        },
        {
            'key': '4',
            'name': 'Business Consultant',
            'temperature': 0.4,
            'top_p': 0.85,
            'top_k': 50
        }
    ]
    return jsonify({'personas': personas})

# 🧪 CORS-Test Endpunkt
@app.route('/api/cors-test', methods=['GET', 'OPTIONS'])
def cors_test():
    return jsonify({
        'message': 'CORS works!',
        'origin': request.headers.get('Origin'),
        'method': request.method,
        'allowed_origins': ALLOWED_ORIGINS
    }), 200

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    logging.info(f"Lokaler Entwicklungsstart auf Port {port}")
    app.run(host='0.0.0.0', port=port)
