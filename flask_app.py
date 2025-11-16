"""
🚀 AI CHATBOT PROJEKT - FLASK API VERSION
=============================================

Dies ist die REST API Version des Chatbots für das Web Frontend.

Hauptunterschiede zum Console-Bot:
- Verwendet Flask statt Console-Input/Output
- Endpoints statt direkter Funktionsaufrufe
- JSON statt Print-Statements
- CORS enabled für Frontend Communication

Installation:
    pip install flask flask-cors

Starten:
    python flask_app.py
    → Server läuft auf http://localhost:5000
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

# Flask App erstellen
app = Flask(__name__)

# CORS konfigurieren für Firebase Frontend
CORS(app, resources={
    r"/api/*": {
        "origins": ["*"],  # Erlaubt alle Origins (Firebase, localhost, etc.)
        "methods": ["GET", "POST", "OPTIONS"],
        "allow_headers": ["Content-Type", "Authorization"],
        "supports_credentials": False
    }
})

# CORS Headers für alle Responses
@app.after_request
def after_request(response):
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
    response.headers.add('Access-Control-Allow-Methods', 'GET,POST,OPTIONS')
    return response

# Konfiguration
API_KEY = os.getenv('GOOGLE_API_KEY')
DB_NAME = 'chatbot_conversations.db'

# Globale Variablen für aktive Chat-Session
active_chat = None
current_persona = None
current_session_name = None

# ============================================================================
# DATABASE FUNCTIONS (von chatbot.py übernommen)
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
        - Gib konkrete Beispiele und Use Cases
        - Denk in Daten und Statistiken
        - Stelle Gegenfragen für besseres Verständnis''',
        'temperature': 0.3,
        'top_p': 0.8,
        'top_k': 40
    },
    '2': {
        'name': 'Creative Storyteller',
        'instruction': '''Du bist ein kreativer Storyteller und Autor.
        - Schreibe kreative, emotional ansprechende Geschichten
        - Verwende vielfältige Vokabeln und poetische Sprache
        - Sei mutig mit ungewöhnlichen Ideen
        - Baue Spannung und Emotionen auf
        - Erschaffe einzigartige Charaktere und Welten''',
        'temperature': 0.9,
        'top_p': 0.95,
        'top_k': 100
    },
    '3': {
        'name': 'Technical Code Assistant',
        'instruction': '''Du bist ein Senior Software Engineer und Code Expert.
        - Schreib präzisen, produktiven Code
        - Erkläre Code-Logik detailliert
        - Gib Best Practices und Optimierungen
        - Warne vor häufigen Fallstricken
        - Verwende exakte Syntax und Standards''',
        'temperature': 0.2,
        'top_p': 0.7,
        'top_k': 30
    },
    '4': {
        'name': 'Business Consultant',
        'instruction': '''Du bist ein Unternehmensberater mit Fokus auf Business Strategy.
        - Gib strategische Ratschläge für Geschäftsfragen
        - Balance zwischen Kreativität und praktischer Umsetzung
        - Denk in ROI, KPIs und Business Metriken
        - Stelle Fragen zur Geschäftssituation
        - Gib konkrete Handlungsempfehlungen''',
        'temperature': 0.4,
        'top_p': 0.85,
        'top_k': 50
    }
}


# ============================================================================
# API ENDPOINTS
# ============================================================================

@app.route('/', methods=['GET'])
def root():
    """Root Endpoint - Zeigt verfügbare API Endpoints"""
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
        },
        'documentation': 'https://github.com/sebastiankh1983-svg/AI_CHATBOT_SYSTEM'
    })
# ============================================================================

@app.route('/api/health', methods=['GET'])
def health():
    """Health Check - Ist der Server erreichbar?"""
    return jsonify({
        'status': 'ok',
        'message': 'AI Chatbot API läuft'
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

    return jsonify({
        'personas': personas_list
    })


@app.route('/api/chat/start', methods=['POST'])
def start_chat():
    """
    Startet einen neuen Chat

    Request Body:
    {
        "persona_key": "1",
        "session_name": "Mein Chat"
    }
    """
    global active_chat, current_persona, current_session_name

    try:
        data = request.json
        persona_key = data.get('persona_key')
        session_name = data.get('session_name')

        if persona_key not in PERSONAS:
            return jsonify({'error': 'Ungültige Persona'}), 400

        if not session_name:
            return jsonify({'error': 'Session Name erforderlich'}), 400

        # Persona laden
        persona = PERSONAS[persona_key]
        current_persona = persona_key
        current_session_name = session_name

        # GenerativeModel erstellen
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

        # Chat Session starten
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
    """
    Sendet eine Nachricht an den AI

    Request Body:
    {
        "message": "Hallo Bot"
    }
    """
    global active_chat

    try:
        if not active_chat:
            return jsonify({'error': 'Kein Chat aktiv'}), 400

        data = request.json
        message = data.get('message')

        if not message:
            return jsonify({'error': 'Nachricht erforderlich'}), 400

        # Message an AI senden
        response = active_chat.send_message(message)
        finish_reason = response.candidates[0].finish_reason

        if finish_reason == 1:  # STOP
            return jsonify({
                'status': 'success',
                'message': response.text,
                'finish_reason': 'STOP'
            })

        elif finish_reason == 2:  # MAX_TOKENS
            text = response.candidates[0].content.parts[0].text if response.candidates[0].content.parts else ""
            return jsonify({
                'status': 'success',
                'message': text,
                'finish_reason': 'MAX_TOKENS',
                'warning': 'Antwort wurde gekürzt'
            })

        elif finish_reason == 3:  # SAFETY
            return jsonify({
                'status': 'blocked',
                'message': 'Antwort wurde aus Sicherheitsgründen blockiert',
                'finish_reason': 'SAFETY'
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
    """Gibt die aktuelle Chat-History zurück"""
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
    """Speichert den aktuellen Chat in die Datenbank"""
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
            'message': f'Chat gespeichert',
            'conversation_id': conversation_id
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/conversations', methods=['GET'])
def get_conversations():
    """Gibt alle gespeicherten Conversations zurück"""
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
    """Gibt Details einer bestimmten Conversation zurück"""
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


# ============================================================================
# ERROR HANDLING
# ============================================================================

@app.errorhandler(404)
def not_found(error):
    """404 Error Handler"""
    return jsonify({'error': 'Endpoint nicht gefunden'}), 404


@app.errorhandler(500)
def internal_error(error):
    """500 Error Handler"""
    return jsonify({'error': 'Interner Server Error'}), 500


# ============================================================================
# MAIN
# ============================================================================

if __name__ == '__main__':
    # API Key überprüfen
    if not API_KEY:
        print("❌ FEHLER: API_KEY nicht in .env gefunden!")
        exit(1)

    # Gemini API konfigurieren
    genai.configure(api_key=API_KEY)

    # Datenbank erstellen
    create_database()
    print("✅ Datenbank initialisiert")

    # Flask App starten
    print("🚀 Flask API startet auf http://localhost:5000")
    print("📝 Endpoints:")
    print("   GET  /api/health")
    print("   GET  /api/personas")
    print("   POST /api/chat/start")
    print("   POST /api/chat/send")
    print("   GET  /api/chat/history")
    print("   POST /api/chat/save")
    print("   GET  /api/conversations")
    print("   GET  /api/conversations/<id>")
    print("\n✅ Server bereit! Drücke Ctrl+C zum Beenden.\n")

    # Railway-kompatibel: Nutze PORT Environment Variable
    port = int(os.getenv('PORT', 5000))
    app.run(debug=False, host='0.0.0.0', port=port)

