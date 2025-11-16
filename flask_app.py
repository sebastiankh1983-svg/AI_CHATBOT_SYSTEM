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

# .env laden
load_dotenv()

# Konfiguration
API_KEY = os.getenv('GOOGLE_API_KEY')
DB_NAME = 'chatbot_conversations.db'

# Globale Variablen für aktive Chat-Session
active_chat = None
current_persona = None
current_session_name = None


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
    """Lädt Messages einer Conversation"""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute('''
        SELECT role, content
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

    # CORS konfigurieren
    CORS(app, resources={
        r"/*": {
            "origins": "*",
            "methods": ["GET", "POST", "OPTIONS"],
            "allow_headers": ["Content-Type", "Authorization"]
        }
    })

    # CORS Headers
    @app.after_request
    def after_request(response):
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
        response.headers.add('Access-Control-Allow-Methods', 'GET,POST,OPTIONS')
        return response

    # API initialisieren
    if API_KEY:
        genai.configure(api_key=API_KEY)
        print("✅ Gemini API konfiguriert")
    else:
        print("⚠️  WARNUNG: GOOGLE_API_KEY nicht gefunden!")

    # Datenbank initialisieren
    try:
        create_database()
        print("✅ Datenbank initialisiert")
    except Exception as e:
        print(f"⚠️  Datenbank-Fehler: {e}")

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

    @app.route('/api/health', methods=['GET'])
    def health():
        """Health Check"""
        return jsonify({
            'status': 'ok',
            'message': 'AI Chatbot API läuft',
            'api_key_configured': bool(API_KEY)
        })

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

    @app.route('/api/chat/start', methods=['POST'])
    def start_chat():
        """Startet einen neuen Chat"""
        global active_chat, current_persona, current_session_name

        try:
            data = request.json
            persona_key = data.get('persona_key')
            session_name = data.get('session_name')

            if persona_key not in PERSONAS:
                return jsonify({'error': 'Ungültige Persona'}), 400

            if not session_name:
                return jsonify({'error': 'Session Name erforderlich'}), 400

            persona = PERSONAS[persona_key]
            current_persona = persona_key
            current_session_name = session_name

            model = genai.GenerativeModel(
                'gemini-2.0-flash',
                system_instruction=persona['instruction'],
                generation_config={
                    'temperature': persona['temperature'],
                    'top_p': persona['top_p'],
                    'top_k': persona['top_k'],
                    'max_output_tokens': 500
                }
            )

            active_chat = model.start_chat(history=[])

            return jsonify({
                'status': 'success',
                'message': f'Chat gestartet mit {persona["name"]}',
                'persona': persona['name'],
                'session_name': session_name
            })

        except Exception as e:
            return jsonify({'error': str(e)}), 500

    @app.route('/api/chat/send', methods=['POST'])
    def send_message():
        """Sendet eine Nachricht"""
        global active_chat

        try:
            if not active_chat:
                return jsonify({'error': 'Kein Chat aktiv'}), 400

            data = request.json
            message = data.get('message')

            if not message:
                return jsonify({'error': 'Nachricht erforderlich'}), 400

            response = active_chat.send_message(message)
            finish_reason = response.candidates[0].finish_reason

            if finish_reason == 1:
                return jsonify({
                    'status': 'success',
                    'message': response.text,
                    'finish_reason': 'STOP'
                })
            elif finish_reason == 2:
                text = response.candidates[0].content.parts[0].text if response.candidates[0].content.parts else ""
                return jsonify({
                    'status': 'success',
                    'message': text,
                    'finish_reason': 'MAX_TOKENS',
                    'warning': 'Antwort wurde gekürzt'
                })
            else:
                return jsonify({
                    'status': 'error',
                    'message': f'Fehler: finish_reason={finish_reason}'
                }), 500

        except Exception as e:
            return jsonify({'error': str(e)}), 500

    @app.route('/api/chat/history', methods=['GET'])
    def get_chat_history():
        """Gibt Chat-History zurück"""
        global active_chat

        try:
            if not active_chat:
                return jsonify({'history': []})

            history = []
            for message in active_chat.history:
                history.append({
                    'role': message.role,
                    'content': message.parts[0].text
                })

            return jsonify({'history': history})

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
            for role, content in messages:
                messages_list.append({
                    'role': role,
                    'content': content
                })

            return jsonify({
                'id': conversation_id,
                'messages': messages_list
            })

        except Exception as e:
            return jsonify({'error': str(e)}), 500

    @app.errorhandler(404)
    def not_found(error):
        """404 Error Handler"""
        return jsonify({'error': 'Endpoint nicht gefunden'}), 404

    @app.errorhandler(500)
    def internal_error(error):
        """500 Error Handler"""
        return jsonify({'error': 'Interner Server Error'}), 500

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

