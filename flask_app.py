"""
🚀 AI CHATBOT PROJEKT - FLASK API VERSION (Railway-optimiert)
===============================================================

Production-ready Flask API mit Application Factory Pattern.
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
import os
from dotenv import load_dotenv
import google.generativeai as genai
from datetime import datetime
import sqlite3
import logging
import uuid

# .env laden
load_dotenv()

# Konfiguration
API_KEY = os.getenv('GOOGLE_API_KEY')
DB_NAME = 'chatbot_conversations.db'

# Globale Variablen für aktive Chat-Session
active_chat = None
current_persona = None
current_session_name = None
# Multi-Session Speicher
sessions = {}  # session_id -> {'chat': chat_obj, 'persona': persona_key, 'session_name': str}


# ============================================================================
# DATABASE FUNCTIONS
# ============================================================================

def create_database():
    """Erstellt Datenbank falls noch nicht vorhanden"""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS conversations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_name TEXT NOT NULL,
            persona TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            conversation_id INTEGER NOT NULL,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            timestamp TEXT NOT NULL,
            FOREIGN KEY (conversation_id) REFERENCES conversations (id)
        )
    ''')

    conn.commit()
    conn.close()


def save_conversation(session_name, persona, history):
    """Speichert Conversation in Datenbank"""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    timestamp = datetime.now().isoformat()

    cursor.execute('''
        INSERT INTO conversations (session_name, persona, created_at, updated_at)
        VALUES (?, ?, ?, ?)
    ''', (session_name, persona, timestamp, timestamp))

    conversation_id = cursor.lastrowid

    for message in history:
        role = message.role
        content = message.parts[0].text
        cursor.execute('''
            INSERT INTO messages (conversation_id, role, content, timestamp)
            VALUES (?, ?, ?, ?)
        ''', (conversation_id, role, content, timestamp))

    conn.commit()
    conn.close()

    return conversation_id


def load_conversations():
    """Lädt alle Conversations"""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute('''
        SELECT id, session_name, persona, created_at, updated_at
        FROM conversations
        ORDER BY updated_at DESC
    ''')

    conversations = cursor.fetchall()
    conn.close()

    return conversations


def load_conversation_history(conversation_id):
    """Lädt Messages einer Conversation inkl. Timestamp"""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute('''
        SELECT role, content, timestamp
        FROM messages
        WHERE conversation_id = ?
        ORDER BY timestamp ASC
    ''', (conversation_id,))

    messages = cursor.fetchall()
    conn.close()

    return messages


# ============================================================================
# PERSONAS KONFIGURATION
# ============================================================================

PERSONAS = {
    '1': {
        'name': 'Data Analyst Expert',
        'instruction': '''Du bist ein erfahrener Data Analyst mit 10 Jahren Erfahrung.
        - Antworte präzise, faktenbasiert und detailliert
        - Verwende Fachbegriffe, aber erkläre sie
        - Gib konkrete Beispiele und Use Cases''',
        'temperature': 0.3,
        'top_p': 0.8,
        'top_k': 40
    },
    '2': {
        'name': 'Creative Storyteller',
        'instruction': '''Du bist ein kreativer Storyteller und Autor.
        - Schreibe kreative, emotional ansprechende Geschichten
        - Verwende vielfältige Vokabeln und poetische Sprache''',
        'temperature': 0.9,
        'top_p': 0.95,
        'top_k': 100
    },
    '3': {
        'name': 'Technical Code Assistant',
        'instruction': '''Du bist ein Senior Software Engineer und Code Expert.
        - Schreib präzisen, produktiven Code
        - Erkläre Code-Logik detailliert''',
        'temperature': 0.2,
        'top_p': 0.7,
        'top_k': 30
    },
    '4': {
        'name': 'Business Consultant',
        'instruction': '''Du bist ein Unternehmensberater mit Fokus auf Business Strategy.
        - Gib strategische Ratschläge für Geschäftsfragen
        - Denk in ROI, KPIs und Business Metriken''',
        'temperature': 0.4,
        'top_p': 0.85,
        'top_k': 50
    }
}


# ============================================================================
# APPLICATION FACTORY
# ============================================================================

def create_app():
    """Application Factory - erstellt und konfiguriert Flask App"""

    app = Flask(__name__)

    # ===================== CORS KONFIGURATION =====================
    # Erlaubte Origins für Production (Firebase Hosting + lokale Entwicklung)
    allowed_origins = [
        "https://ai-chatbot-system-c8204.web.app",
        "https://ai-chatbot-system-c8204.firebaseapp.com",
        "http://localhost:3000",
        "http://127.0.0.1:3000"
    ]
    # Wenn FLASK_ENV=development gesetzt ist → alle Origins erlauben (lokales Debugging)
    #if os.getenv("FLASK_ENV") == "development":
        #allowed_origins = "*"

    CORS(
        app,
        resources={r"/api*": {
            "origins": allowed_origins,
            "methods": ["GET", "POST", "OPTIONS"],
            "allow_headers": ["Content-Type"],
            "supports_credentials": False,
            "max_age": 3600  # Preflight-Ergebnis für 1h cachen
        }}
    )
    # HINWEIS: Kein after_request mehr nötig – flask-cors setzt die Header.

    # ===================== API INITIALISIERUNG =====================
    if API_KEY:
        genai.configure(api_key=API_KEY)
        print("✅ Gemini API konfiguriert")
    else:
        print("⚠️  WARNUNG: GOOGLE_API_KEY nicht gefunden!")

    # ===================== DATENBANK =====================
    try:
        create_database()
        print("✅ Datenbank initialisiert")
    except Exception as e:
        print(f"⚠️  Datenbank-Fehler: {e}")

    # ===================== DEBUG / CORS TEST ENDPOINT =====================
    @app.route('/api/cors-test', methods=['GET', 'OPTIONS'])
    def cors_test():
        return jsonify({
            "message": "CORS OK",
            "origin": request.headers.get('Origin'),
            "method": request.method,
            "allowed_origins": allowed_origins if allowed_origins != "*" else "* (development)"
        }), 200

    # ========================================================================
    # ROUTES
    # ========================================================================

    @app.route('/', methods=['GET'])
    def root():
        """Root Endpoint"""
        return jsonify({
            'status': 'online',
            'message': 'AI Chatbot API ist online!',
            'version': '1.0',
            'endpoints': {
                'health': '/api/health',
                'personas': '/api/personas',
                'chat_start': '/api/chat/start (POST)',
                'chat_send': '/api/chat/send (POST)',
                'chat_history': '/api/chat/history (GET)',
                'chat_save': '/api/chat/save (POST)',
                'conversations': '/api/conversations (GET)',
                'conversation_detail': '/api/conversations/<id> (GET)'
            }
        })

    @app.route('/api/health', methods=['GET', 'HEAD'])
    def health():
        """Health Check (GET & HEAD)"""
        if request.method == 'HEAD':
            return ('', 200)
        return jsonify({
            'status': 'ok',
            'message': 'AI Chatbot API läuft',
            'api_key_configured': bool(API_KEY),
            'capabilities_endpoint': '/api/capabilities'
        })

    @app.route('/api/ping', methods=['GET'])
    def ping():
        """Minimaler schneller Ping ohne externe Abhängigkeiten"""
        return jsonify({'pong': True})

    @app.route('/api/personas', methods=['GET'])
    def get_personas():
        """Gibt alle verfügbaren Personas zurück"""
        personas_list = []
        for key, persona in PERSONAS.items():
            personas_list.append({
                'key': key,
                'name': persona['name'],
                'temperature': persona['temperature'],
                'top_p': persona['top_p'],
                'top_k': persona['top_k']
            })

        return jsonify({'personas': personas_list})

    @app.route('/api/capabilities', methods=['GET'])
    def capabilities():
        # Multi-Session jetzt aktiv
        return jsonify({
            'chat': True,
            'personas': True,
            'persistence': True,
            'multi_session': True,
            'gemini': bool(API_KEY),
            'version': '1.1'
        })

    # ============================================================================
    # RATE LIMITING (einfach, In-Memory)
    # ============================================================================

    # Max. Anzahl Requests pro IP und Endpoint pro Zeitfenster
    RATE_LIMIT_WINDOW_SECONDS = 60  # 1 Minute
    RATE_LIMIT_MAX_START = 5        # max. 5 /api/chat/start Aufrufe pro Minute
    RATE_LIMIT_MAX_SEND = 20        # max. 20 /api/chat/send Aufrufe pro Minute

    rate_limit_store = {
        'start': {},  # ip -> [timestamps]
        'send': {},   # ip -> [timestamps]
    }


    def _clean_old_timestamps(timestamps, window_seconds):
        """Entfernt Timestamps, die außerhalb des Zeitfensters liegen."""
        now = datetime.now().timestamp()
        return [ts for ts in timestamps if now - ts <= window_seconds]


    def check_rate_limit(kind: str, ip: str) -> bool:
        """Prüft und aktualisiert das Rate-Limit.

        kind: 'start' oder 'send'
        ip:   IP-Adresse des Clients

        Rückgabe: True = erlaubt, False = Limit überschritten
        """
        if kind not in rate_limit_store:
            return True

        now = datetime.now().timestamp()
        timestamps = rate_limit_store[kind].get(ip, [])
        timestamps = _clean_old_timestamps(timestamps, RATE_LIMIT_WINDOW_SECONDS)

        if kind == 'start':
            limit = RATE_LIMIT_MAX_START
        else:
            limit = RATE_LIMIT_MAX_SEND

        if len(timestamps) >= limit:
            return False

        timestamps.append(now)
        rate_limit_store[kind][ip] = timestamps
        return True


    @app.route('/api/chat/start', methods=['POST'])
    def api_chat_start():
        client_ip = request.headers.get('X-Forwarded-For', request.remote_addr)
        if not check_rate_limit('start', client_ip):
            return jsonify({
                'status': 'error',
                'error': 'rate_limited',
                'message': 'Zu viele Start-Anfragen. Bitte warte einen Moment und versuche es erneut.'
            }), 429

        global active_chat, current_persona, current_session_name, sessions
        try:
            if not API_KEY:
                return error_response('API Key nicht konfiguriert', 500, code='MISSING_API_KEY')
            data = request.json or {}
            persona_key = data.get('persona_key')
            session_name = data.get('session_name')
            if persona_key not in PERSONAS:
                return error_response('Ungültige Persona', 400, code='INVALID_PERSONA')
            if not session_name:
                return error_response('Session Name erforderlich', 400, code='MISSING_SESSION_NAME')
            persona = PERSONAS[persona_key]
            temperature = persona.get('temperature')
            model = genai.GenerativeModel(
                'gemini-2.0-flash',
                system_instruction=persona['instruction'],
                generation_config={
                    'temperature': temperature,
                    'top_p': persona['top_p'],
                    'top_k': persona['top_k'],
                    'max_output_tokens': 500
                }
            )
            chat_obj = model.start_chat(history=[])
            session_id = str(uuid.uuid4())
            sessions[session_id] = {
                'chat': chat_obj,
                'persona': persona_key,
                'session_name': session_name
            }
            active_chat = chat_obj
            current_persona = persona_key
            current_session_name = session_name
            logging.info(f"Chat gestartet (session_id={session_id}) Persona={persona['name']} SessionName={session_name}")
            return jsonify({
                'status': 'success',
                'message': f'Chat gestartet mit {persona["name"]}',
                'persona': persona['name'],
                'session_name': session_name,
                'session_id': session_id,
                'conversation_id': session_id  # hinzugefügt
            })
        except Exception as e:
            logging.error("Fehler beim Starten des Chats: %s", e)
            return error_response(str(e), 500, code='START_EXCEPTION')

    @app.route('/api/chat/send', methods=['POST'])
    def api_chat_send():
        client_ip = request.headers.get('X-Forwarded-For', request.remote_addr)
        if not check_rate_limit('send', client_ip):
            return jsonify({
                'status': 'error',
                'error': 'rate_limited',
                'message': 'Zu viele Nachrichten in kurzer Zeit. Bitte etwas langsamer senden.'
            }), 429

        global sessions, active_chat
        try:
            data = request.json or {}
            message = data.get('message')
            session_id = data.get('session_id')
            if not message:
                return error_response('Nachricht erforderlich', 400, code='MISSING_MESSAGE')
            chat_ref = None
            if session_id:
                sess = sessions.get(session_id)
                if not sess:
                    return error_response('Unbekannte session_id', 404, code='UNKNOWN_SESSION')
                chat_ref = sess['chat']
            else:
                chat_ref = active_chat
            if not chat_ref:
                return error_response('Kein aktiver Chat – zuerst /api/chat/start aufrufen', 400, code='NO_ACTIVE_CHAT')
            response = chat_ref.send_message(message)
            candidate = response.candidates[0]
            fr = candidate.finish_reason
            if fr == 1:
                return jsonify({'status': 'success', 'message': response.text, 'finish_reason': 'STOP', 'session_id': session_id, 'conversation_id': session_id})
            elif fr == 2:
                text = candidate.content.parts[0].text if candidate.content.parts else ""
                return jsonify({'status': 'success', 'message': text, 'finish_reason': 'MAX_TOKENS', 'warning': 'Antwort gekürzt', 'session_id': session_id, 'conversation_id': session_id})
            elif fr == 3:
                return error_response('Antwort blockiert (Safety)', 403, code='SAFETY_BLOCK')
            elif fr == 4:
                return error_response('Antwort blockiert (Recitation)', 403, code='RECITATION_BLOCK')
            else:
                return error_response(f'Unbekannte finish_reason={fr}', 500, code='UNKNOWN_FINISH_REASON')
        except Exception as e:
            logging.error("Fehler beim Senden: %s", e)
            return error_response(str(e), 500, code='SEND_EXCEPTION')

    @app.route('/api/chat/history', methods=['GET'])
    def get_chat_history():
        """Gibt Chat-History zurück (alias: messages)"""
        global active_chat
        try:
            if not active_chat:
                return jsonify({'history': [], 'messages': []})
            history = []
            for message in active_chat.history:
                history.append({'role': message.role, 'content': message.parts[0].text})
            return jsonify({'history': history, 'messages': history})
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    @app.route('/api/chat/save', methods=['POST'])
    def save_chat():
        """Speichert den aktuellen Chat"""
        global active_chat, current_persona, current_session_name

        try:
            if not active_chat or not current_persona or not current_session_name:
                return jsonify({'error': 'Kein aktiver Chat zum Speichern'}), 400

            persona_name = PERSONAS[current_persona]['name']
            conversation_id = save_conversation(
                current_session_name,
                persona_name,
                active_chat.history
            )

            return jsonify({
                'status': 'success',
                'message': 'Chat gespeichert',
                'conversation_id': conversation_id
            })

        except Exception as e:
            return jsonify({'error': str(e)}), 500

    @app.route('/api/conversations', methods=['GET'])
    def get_conversations():
        """Gibt alle Conversations zurück"""
        try:
            conversations = load_conversations()

            conversations_list = []
            for conv_id, session_name, persona, created_at, updated_at in conversations:
                conversations_list.append({
                    'id': conv_id,
                    'session_name': session_name,
                    'persona': persona,
                    'created_at': created_at,
                    'updated_at': updated_at
                })

            return jsonify({'conversations': conversations_list})

        except Exception as e:
            return jsonify({'error': str(e)}), 500

    @app.route('/api/conversations/<int:conversation_id>', methods=['GET'])
    def get_conversation_detail(conversation_id):
        """Gibt Details einer Conversation zurück"""
        try:
            messages = load_conversation_history(conversation_id)

            messages_list = []
            for role, content, timestamp in messages:
                messages_list.append({
                    'role': role,
                    'content': content,
                    'timestamp': timestamp
                })

            return jsonify({
                'id': conversation_id,
                'messages': messages_list
            })

        except Exception as e:
            logging.error("Fehler beim Laden der Conversation %s: %s", conversation_id, e)
            return jsonify({'error': str(e)}), 500

    @app.route('/api/chat/session/<session_id>/history', methods=['GET'])
    def session_history(session_id):
        sess = sessions.get(session_id)
        if not sess:
            return error_response('Unbekannte session_id', 404, code='UNKNOWN_SESSION')
        history_list = []
        for m in sess['chat'].history:
            history_list.append({'role': m.role, 'content': m.parts[0].text})
        return jsonify({
            'session_id': session_id,
            'history': history_list,
            'messages': history_list,
            'persona': PERSONAS[sess['persona']]['name'],
            'session_name': sess['session_name']
        })

    @app.route('/api/debug-session', methods=['GET'])
    def debug_session():
        return jsonify({
            'active': active_chat is not None,
            'current_persona': current_persona,
            'current_session_name': current_session_name,
            'history_length': len(active_chat.history) if active_chat else 0,
            'sessions_count': len(sessions),
            'session_ids': list(sessions.keys())[:10]
        })

    @app.route('/api/diagnostic', methods=['GET'])
    def diagnostic():
        """Erweiterter Diagnose-Endpunkt für Frontend Debugging"""
        return jsonify({
            'active_chat': active_chat is not None,
            'current_persona': current_persona,
            'current_session_name': current_session_name,
            'history_length': len(active_chat.history) if active_chat else 0,
            'personas_available': list(PERSONAS.keys()),
            'api_key_present': bool(API_KEY)
        })

    @app.route('/api/chat', methods=['POST', 'OPTIONS'])
    def chat_router():
        global sessions, active_chat, current_persona, current_session_name
        if request.method == 'OPTIONS':
            return ('', 204)
        data = request.json or {}
        persona_key = data.get('persona_key')
        session_name = data.get('session_name')
        incoming_message = data.get('message')
        session_id = data.get('session_id')
        if persona_key and session_name and incoming_message:
            if persona_key not in PERSONAS:
                return error_response('Ungültige Persona', 400, code='INVALID_PERSONA')
            if not API_KEY:
                return error_response('API Key nicht konfiguriert', 500, code='MISSING_API_KEY')
            temperature = PERSONAS[persona_key]['temperature']
            try:
                model = genai.GenerativeModel(
                    'gemini-2.0-flash',
                    system_instruction=PERSONAS[persona_key]['instruction'],
                    generation_config={
                        'temperature': temperature,
                        'top_p': PERSONAS[persona_key]['top_p'],
                        'top_k': PERSONAS[persona_key]['top_k'],
                        'max_output_tokens': 500
                    }
                )
                chat_obj = model.start_chat(history=[])
                new_session_id = str(uuid.uuid4())
                sessions[new_session_id] = {'chat': chat_obj, 'persona': persona_key, 'session_name': session_name}
                active_chat = chat_obj
                current_persona = persona_key
                current_session_name = session_name
                response = chat_obj.send_message(incoming_message)
                candidate = response.candidates[0]
                fr = candidate.finish_reason
                if fr == 1:
                    return jsonify({'status': 'success', 'mode': 'start+send', 'message': response.text, 'session_id': new_session_id, 'conversation_id': new_session_id})
                elif fr == 2:
                    txt = candidate.content.parts[0].text if candidate.content.parts else ''
                    return jsonify({'status': 'success', 'mode': 'start+send', 'message': txt, 'warning': 'Antwort gekürzt', 'finish_reason': 'MAX_TOKENS', 'session_id': new_session_id, 'conversation_id': new_session_id})
                elif fr == 3:
                    return error_response('Antwort blockiert (Safety)', 403, code='SAFETY_BLOCK')
                elif fr == 4:
                    return error_response('Antwort blockiert (Recitation)', 403, code='RECITATION_BLOCK')
                else:
                    return error_response(f'Unbekannte finish_reason={fr}', 500, code='UNKNOWN_FINISH_REASON')
            except Exception as e:
                return error_response(str(e), 500, code='START_SEND_EXCEPTION')
        if persona_key and session_name and not incoming_message:
            start_resp = start_chat()
            return start_resp
        if incoming_message and (session_id or (not persona_key and not session_name)):
            if session_id:
                if session_id not in sessions:
                    return error_response('Unbekannte session_id', 404, code='UNKNOWN_SESSION')
                chat_obj = sessions[session_id]['chat']
            else:
                chat_obj = active_chat
            if not chat_obj:
                return error_response('Kein aktiver Chat', 400, code='NO_ACTIVE_CHAT')
            try:
                response = chat_obj.send_message(incoming_message)
                candidate = response.candidates[0]
                fr = candidate.finish_reason
                if fr == 1:
                    return jsonify({'status': 'success', 'mode': 'send', 'message': response.text, 'session_id': session_id, 'conversation_id': session_id})
                elif fr == 2:
                    txt = candidate.content.parts[0].text if candidate.content.parts else ''
                    return jsonify({'status': 'success', 'mode': 'send', 'message': txt, 'finish_reason': 'MAX_TOKENS', 'warning': 'Antwort gekürzt', 'session_id': session_id, 'conversation_id': session_id})
                elif fr == 3:
                    return error_response('Antwort blockiert (Safety)', 403, code='SAFETY_BLOCK')
                elif fr == 4:
                    return error_response('Antwort blockiert (Recitation)', 403, code='RECITATION_BLOCK')
                else:
                    return error_response(f'Unbekannte finish_reason={fr}', 500, code='UNKNOWN_FINISH_REASON')
            except Exception as e:
                return error_response(str(e), 500, code='SEND_EXCEPTION')
        return error_response('Ungültiger Request Body für /api/chat', 400, code='INVALID_CHAT_BODY')

    @app.errorhandler(404)
    def not_found(error):
        """404 Error Handler"""
        return jsonify({'error': 'Endpoint nicht gefunden'}), 404

    @app.errorhandler(500)
    def internal_error(error):
        """500 Error Handler"""
        return jsonify({'error': 'Interner Server Error'}), 500

    # Helper für einheitliche Fehlerantworten
    def error_response(message, status_code=400, code=None, extra=None):
        payload = {
            'status': 'error',
            'message': message,
            'http_status': status_code
        }
        if code is not None:
            payload['code'] = code
        if extra:
            payload['extra'] = extra
        return jsonify(payload), status_code

    # Request Logging für Diagnose (nur Basisdaten)
    @app.before_request
    def log_request_info():
        print(f"➡️ {request.method} {request.path} origin={request.headers.get('Origin')} content_type={request.headers.get('Content-Type')}")

    return app


# ============================================================================
# APP INSTANCE für Gunicorn
# ============================================================================

# Diese Zeile ist WICHTIG für Gunicorn!
app = create_app()


# ============================================================================
# MAIN (nur für lokales Development)
# ============================================================================

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    print("🚀 Flask API startet auf Port", port)
    app.run(debug=False, host='0.0.0.0', port=port)
