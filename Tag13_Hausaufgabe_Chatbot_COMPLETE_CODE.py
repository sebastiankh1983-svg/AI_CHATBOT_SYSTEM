"""
AI Chatbot mit Gemini API - Vollständige Implementierung
========================================================
Features:
- Chat Memory (Session-basiert)
- SQLite Database Persistence
- Multiple Personas
- Advanced Parameters (Temperature, top_p, top_k, max_output_tokens)
- Error Handling
- Conversation History Management
"""

import google.generativeai as genai
import sqlite3
import json
from datetime import datetime
import os

# ============================================================================
# CONFIGURATION
# ============================================================================

API_KEY = os.getenv('GOOGLE_API_KEY', '')  # API-Key wird jetzt aus Umgebungsvariable gelesen
DB_NAME = 'chatbot_conversations.db'

# ============================================================================
# DATABASE FUNCTIONS
# ============================================================================

def create_database():
    """Erstellt die SQLite Datenbank und Tabellen"""
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
    print("✓ Datenbank erfolgreich erstellt/geladen")


def save_conversation(session_name, persona, history):
    """Speichert eine Conversation in die Datenbank"""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    timestamp = datetime.now().isoformat()

    # Insert conversation
    cursor.execute('''
        INSERT INTO conversations (session_name, persona, created_at, updated_at)
        VALUES (?, ?, ?, ?)
    ''', (session_name, persona, timestamp, timestamp))

    conversation_id = cursor.lastrowid

    # Insert all messages from history
    for message in history:
        role = message.role  # 'user' or 'model'
        content = message.parts[0].text
        cursor.execute('''
            INSERT INTO messages (conversation_id, role, content, timestamp)
            VALUES (?, ?, ?, ?)
        ''', (conversation_id, role, content, timestamp))

    conn.commit()
    conn.close()
    print(f"✓ Conversation '{session_name}' gespeichert (ID: {conversation_id})")
    return conversation_id


def load_conversations():
    """Lädt alle gespeicherten Conversations"""
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
    """Lädt die Message History einer bestimmten Conversation"""
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
# CHATBOT CLASS
# ============================================================================

class GeminiChatbot:
    """AI Chatbot mit Memory und Advanced Parameters"""

    # Persona Konfigurationen
    PERSONAS = {
        '1': {
            'name': 'Data Analyst Expert',
            'instruction': 'Du bist ein erfahrener Data Analyst mit 10 Jahren Erfahrung. Du erklärst Datenanalyse-Konzepte klar und präzise, gibst praktische Tipps und verwendest Beispiele aus der Business-Welt.',
            'temp': 0.3,
            'top_p': 0.8,
            'top_k': 40
        },
        '2': {
            'name': 'Creative Storyteller',
            'instruction': 'Du bist ein kreativer Storyteller. Du erzählst spannende Geschichten, verwendest bildhafte Sprache und machst jede Antwort zu einem kleinen Abenteuer.',
            'temp': 0.9,
            'top_p': 0.95,
            'top_k': 100
        },
        '3': {
            'name': 'Technical Code Assistant',
            'instruction': 'Du bist ein technischer Coding-Assistent. Du schreibst sauberen, gut dokumentierten Code, erklärst Best Practices und hilfst bei Debugging. Du verwendest hauptsächlich Python.',
            'temp': 0.2,
            'top_p': 0.7,
            'top_k': 30
        },
        '4': {
            'name': 'Business Consultant',
            'instruction': 'Du bist ein Business Consultant mit Fokus auf AI und Data-Driven Decisions. Du denkst strategisch, gibst Business-Empfehlungen und erklärst den ROI von AI-Projekten.',
            'temp': 0.4,
            'top_p': 0.85,
            'top_k': 50
        }
    }

    def __init__(self, api_key):
        """Initialisiert den Chatbot"""
        genai.configure(api_key=api_key)
        self.chat = None
        self.current_persona = None
        self.session_name = None

    def start_new_chat(self, persona_key, session_name):
        """Startet einen neuen Chat mit gewählter Persona"""
        if persona_key not in self.PERSONAS:
            print("❌ Ungültige Persona!")
            return False

        persona = self.PERSONAS[persona_key]
        self.current_persona = persona_key
        self.session_name = session_name

        # Create model with persona configuration
        # Use gemini-2.0-flash for reliable max_output_tokens support
        model = genai.GenerativeModel(
            'gemini-2.0-flash',
            system_instruction=persona['instruction'],
            generation_config={
                'temperature': persona['temp'],
                'top_p': persona['top_p'],
                'top_k': persona['top_k'],
                'max_output_tokens': 500  # Works with 2.0-flash
            }
        )

        # Start chat session
        self.chat = model.start_chat(history=[])

        print(f"\n{'='*60}")
        print(f"✓ Chat gestartet mit: {persona['name']}")
        print(f"  Session: {session_name}")
        print(f"  Temperature: {persona['temp']} | top_p: {persona['top_p']} | top_k: {persona['top_k']}")
        print(f"{'='*60}\n")

        return True

    def send_message(self, message):
        """Sendet eine Nachricht und gibt die Antwort zurück"""
        if not self.chat:
            print("❌ Kein aktiver Chat! Starte zuerst einen neuen Chat.")
            return None

        try:
            response = self.chat.send_message(message)

            # Error handling - check finish_reason
            if response.candidates[0].finish_reason == 1:
                # SUCCESS
                return response.text
            elif response.candidates[0].finish_reason == 2:
                # MAX_TOKENS reached
                if response.candidates[0].content.parts:
                    text = response.candidates[0].content.parts[0].text
                    print("\n⚠️  Antwort wurde gekürzt (MAX_TOKENS erreicht)\n")
                    return text
                else:
                    return "❌ Keine Antwort generiert (Token-Limit)"
            else:
                return f"❌ Fehler: finish_reason = {response.candidates[0].finish_reason}"

        except Exception as e:
            return f"❌ Error: {str(e)}"

    def show_history(self):
        """Zeigt die aktuelle Chat History"""
        if not self.chat:
            print("❌ Kein aktiver Chat!")
            return

        print(f"\n{'='*60}")
        print(f"CHAT HISTORY - Session: {self.session_name}")
        print(f"{'='*60}\n")

        for i, message in enumerate(self.chat.history, 1):
            role = "USER" if message.role == "user" else "AI"
            content = message.parts[0].text

            # Truncate long messages for display
            if len(content) > 200:
                content_preview = content[:200] + "..."
            else:
                content_preview = content

            print(f"{i}. [{role}]")
            print(f"   {content_preview}\n")

    def save_current_chat(self):
        """Speichert den aktuellen Chat in die Datenbank"""
        if not self.chat or not self.chat.history:
            print("❌ Kein Chat zum Speichern vorhanden!")
            return

        persona_name = self.PERSONAS[self.current_persona]['name']
        save_conversation(self.session_name, persona_name, self.chat.history)


# ============================================================================
# MENU SYSTEM
# ============================================================================

def show_main_menu():
    """Zeigt das Hauptmenü"""
    print("\n" + "="*60)
    print("     AI CHATBOT - GEMINI API")
    print("="*60)
    print("\n1. Neuen Chat starten")
    print("2. Gespeicherte Conversations anzeigen")
    print("3. Programm beenden")
    print("\nWähle eine Option: ", end="")


def show_persona_menu():
    """Zeigt das Persona-Auswahlmenü"""
    print("\n" + "="*60)
    print("     PERSONA AUSWAHL")
    print("="*60)
    print("\n1. Data Analyst Expert (temp=0.3, fokussiert)")
    print("2. Creative Storyteller (temp=0.9, kreativ)")
    print("3. Technical Code Assistant (temp=0.2, präzise)")
    print("4. Business Consultant (temp=0.4, strategisch)")
    print("\nWähle eine Persona: ", end="")


def show_chat_menu():
    """Zeigt das Chat-Menü"""
    print("\n--- Chat Optionen ---")
    print("• Schreibe deine Nachricht")
    print("• 'history' - Zeige Chat History")
    print("• 'save' - Speichere Chat")
    print("• 'exit' - Chat beenden")
    print("\n> ", end="")


def show_saved_conversations():
    """Zeigt alle gespeicherten Conversations"""
    conversations = load_conversations()

    if not conversations:
        print("\n❌ Keine gespeicherten Conversations gefunden!")
        return

    print("\n" + "="*60)
    print("     GESPEICHERTE CONVERSATIONS")
    print("="*60)

    print(f"\n{'ID':<5} {'Session Name':<25} {'Persona':<20} {'Datum':<20}")
    print("-" * 70)

    for conv in conversations:
        conv_id, session_name, persona, created_at, updated_at = conv
        # Format datetime for display
        date_obj = datetime.fromisoformat(created_at)
        date_str = date_obj.strftime("%Y-%m-%d %H:%M")

        print(f"{conv_id:<5} {session_name:<25} {persona:<20} {date_str:<20}")

    # Ask if user wants to view a specific conversation
    print("\nMöchtest du eine Conversation anzeigen? (ID eingeben oder 0 für zurück): ", end="")
    choice = input().strip()

    if choice != '0' and choice.isdigit():
        show_conversation_detail(int(choice))


def show_conversation_detail(conversation_id):
    """Zeigt die Details einer gespeicherten Conversation"""
    messages = load_conversation_history(conversation_id)

    if not messages:
        print(f"\n❌ Keine Messages für Conversation {conversation_id} gefunden!")
        return

    print(f"\n{'='*60}")
    print(f"CONVERSATION DETAIL - ID: {conversation_id}")
    print(f"{'='*60}\n")

    for i, (role, content, timestamp) in enumerate(messages, 1):
        role_display = "USER" if role == "user" else "AI"
        print(f"{i}. [{role_display}]")
        print(f"   {content}\n")

    input("\nDrücke Enter um fortzufahren...")


def run_chat_session(chatbot):
    """Führt eine Chat-Session aus"""
    print("\n")

    while True:
        show_chat_menu()
        user_input = input().strip()

        if user_input.lower() == 'exit':
            # Ask if user wants to save before exiting
            print("\nMöchtest du den Chat speichern? (j/n): ", end="")
            save_choice = input().strip().lower()
            if save_choice == 'j':
                chatbot.save_current_chat()
            print("\n✓ Chat beendet")
            break

        elif user_input.lower() == 'history':
            chatbot.show_history()

        elif user_input.lower() == 'save':
            chatbot.save_current_chat()

        elif user_input:
            # Send message to AI
            print("\n[AI]:")
            response = chatbot.send_message(user_input)
            if response:
                print(response)


# ============================================================================
# MAIN PROGRAM
# ============================================================================

def main():
    """Hauptprogramm"""
    # Initialize database
    create_database()

    # Initialize chatbot
    chatbot = GeminiChatbot(API_KEY)

    while True:
        show_main_menu()
        choice = input().strip()

        if choice == '1':
            # Start new chat
            show_persona_menu()
            persona_choice = input().strip()

            if persona_choice in ['1', '2', '3', '4']:
                print("\nGib einen Session-Namen ein: ", end="")
                session_name = input().strip()

                if session_name:
                    if chatbot.start_new_chat(persona_choice, session_name):
                        run_chat_session(chatbot)
                else:
                    print("❌ Session-Name darf nicht leer sein!")
            else:
                print("❌ Ungültige Auswahl!")

        elif choice == '2':
            # Show saved conversations
            show_saved_conversations()

        elif choice == '3':
            # Exit program
            print("\n" + "="*60)
            print("     Auf Wiedersehen! 👋")
            print("="*60 + "\n")
            break

        else:
            print("❌ Ungültige Auswahl!")


if __name__ == "__main__":
    main()
