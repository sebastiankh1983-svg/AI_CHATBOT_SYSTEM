"""
🤖 AI CHATBOT PROJEKT - TEIL 1: DATABASE LAYER
===============================================

In diesem Teil erstellen wir die Datenbank und alle DB-Funktionen.
Das ist wie das "Gedächtnis" unseres Chatbots.

Wichtige Konzepte:
- SQLite: Embedded Database (passt in eine .db Datei)
- 2 Tabellen: conversations (Chats) und messages (Einzelne Nachrichten)
- Foreign Keys: Verlinken messages zu conversations
"""

import sqlite3
from datetime import datetime
import os
import google.generativeai as genai
from dotenv import load_dotenv

# .env Datei laden für API Key
load_dotenv()

# Datenbank-Name
DB_NAME = 'chatbot_conversations.db'

# API Key aus .env laden
API_KEY = os.getenv('GOOGLE_API_KEY')


# ============================================================================
# SCHRITT 1: create_database() - Datenbank und Tabellen erstellen
# ============================================================================

def create_database():
    """
    Erstellt die SQLite Datenbank und die benötigten Tabellen.

    Tabelle 1: conversations
    ├─ id: Eindeutige ID (Primary Key)
    ├─ session_name: Name der Chat-Session (z.B. "Customer Support Chat")
    ├─ persona: Welche AI-Persönlichkeit (z.B. "Data Analyst Expert")
    ├─ created_at: Wann wurde der Chat erstellt
    └─ updated_at: Wann wurde der Chat zuletzt aktualisiert

    Tabelle 2: messages
    ├─ id: Eindeutige ID (Primary Key)
    ├─ conversation_id: Welcher Chat (Foreign Key → conversations.id)
    ├─ role: Wer hat geschrieben ("user" oder "model/AI")
    ├─ content: Der Text der Nachricht
    └─ timestamp: Wann wurde die Nachricht gesendet
    """

    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()

        # Tabelle 1: conversations - Speichert Chat-Informationen
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS conversations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_name TEXT NOT NULL,
                persona TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        ''')
        print("✅ Tabelle 'conversations' erstellt")

        # Tabelle 2: messages - Speichert alle Nachrichten
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
        print("✅ Tabelle 'messages' erstellt")

        conn.commit()
        conn.close()
        print("✅ Datenbank erfolgreich erstellt!\n")

        return True

    except Exception as e:
        print(f"❌ Fehler beim Erstellen der Datenbank: {e}")
        return False


# ============================================================================
# SCHRITT 2: save_conversation() - Chat speichern
# ============================================================================

def save_conversation(session_name, persona, history):
    """
    Speichert eine komplette Chat-Conversation in die Datenbank.

    Prozess:
    1. Erstelle einen neuen Eintrag in conversations-Tabelle
    2. Erhalte die conversation_id
    3. Speichere alle Messages mit dieser ID

    Parameter:
    - session_name: Name für diese Chat-Session
    - persona: Welche AI-Persönlichkeit wurde verwendet
    - history: Liste aller Messages aus self.chat.history

    Returns:
    - conversation_id: Die ID des gespeicherten Chats
    """

    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()

        timestamp = datetime.now().isoformat()

        # Schritt 1: Neue Conversation erstellen
        cursor.execute('''
            INSERT INTO conversations (session_name, persona, created_at, updated_at)
            VALUES (?, ?, ?, ?)
        ''', (session_name, persona, timestamp, timestamp))

        # Schritt 2: conversation_id erhalten
        conversation_id = cursor.lastrowid
        print(f"✅ Neue Conversation erstellt (ID: {conversation_id})")

        # Schritt 3: Alle Messages speichern
        message_count = 0
        for message in history:
            role = message.role  # 'user' oder 'model'
            content = message.parts[0].text

            cursor.execute('''
                INSERT INTO messages (conversation_id, role, content, timestamp)
                VALUES (?, ?, ?, ?)
            ''', (conversation_id, role, content, timestamp))

            message_count += 1

        conn.commit()
        conn.close()

        print(f"✅ {message_count} Messages gespeichert")
        print(f"✅ Conversation '{session_name}' erfolgreich gespeichert!\n")

        return conversation_id

    except Exception as e:
        print(f"❌ Fehler beim Speichern: {e}")
        return None


# ============================================================================
# SCHRITT 3: load_conversations() - Alle Chats laden
# ============================================================================

def load_conversations():
    """
    Lädt alle gespeicherten Conversations aus der Datenbank.

    SQL Query erklärt:
    - SELECT: Welche Spalten wir wollen (id, session_name, persona, dates)
    - FROM conversations: Aus welcher Tabelle
    - ORDER BY updated_at DESC: Neueste Chats zuerst

    Returns:
    - Liste von Tuples: [(id, session_name, persona, created_at, updated_at), ...]
    """

    try:
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

    except Exception as e:
        print(f"❌ Fehler beim Laden: {e}")
        return []


# ============================================================================
# SCHRITT 4: load_conversation_history() - Messages eines Chats laden
# ============================================================================

def load_conversation_history(conversation_id):
    """
    Lädt alle Messages einer bestimmten Conversation.

    Parameter:
    - conversation_id: Die ID der Conversation, die wir laden wollen

    Returns:
    - Liste von Tuples: [(role, content), ...]
    """

    try:
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

    except Exception as e:
        print(f"❌ Fehler beim Laden der History: {e}")
        return []


# ============================================================================
# TEIL 2: GEMINICHATBOT CLASS - Die Hauptklasse des Chatbots
# ============================================================================

class GeminiChatbot:
    """
    AI Chatbot mit Gemini API, Memory und Database Persistence.

    Diese Klasse verwaltet:
    - Chat-Sessions mit verschiedenen Personas
    - Conversation Memory (chat.history)
    - API Parameter (Temperature, top_p, top_k, max_output_tokens)
    - Error Handling für API-Responses
    """

    # 🎭 PERSONAS - 4 verschiedene AI-Persönlichkeiten
    PERSONAS = {
        '1': {
            'name': 'Data Analyst Expert',
            'instruction': '''Du bist ein erfahrener Data Analyst mit 10 Jahren Erfahrung.
            - Antworte präzise, faktenbasiert und detailliert
            - Verwende Fachbegriffe, aber erkläre sie
            - Gib konkrete Beispiele und Use Cases
            - Denk in Daten und Statistiken
            - Stelle Gegenfragen für besseres Verständnis''',
            'temperature': 0.3,    # Sehr fokussiert
            'top_p': 0.8,          # Standard Vokabular
            'top_k': 40            # Kleine Auswahl
        },

        '2': {
            'name': 'Creative Storyteller',
            'instruction': '''Du bist ein kreativer Storyteller und Autor.
            - Schreibe kreative, emotional ansprechende Geschichten
            - Verwende vielfältige Vokabeln und poetische Sprache
            - Sei mutig mit ungewöhnlichen Ideen
            - Baue Spannung und Emotionen auf
            - Erschaffe einzigartige Charaktere und Welten''',
            'temperature': 0.9,    # Sehr kreativ
            'top_p': 0.95,         # Breites Vokabular
            'top_k': 100           # Große Auswahl
        },

        '3': {
            'name': 'Technical Code Assistant',
            'instruction': '''Du bist ein Senior Software Engineer und Code Expert.
            - Schreib präzisen, produktiven Code
            - Erkläre Code-Logik detailliert
            - Gib Best Practices und Optimierungen
            - Warne vor häufigen Fallstricken
            - Verwende exakte Syntax und Standards''',
            'temperature': 0.2,    # Sehr deterministisch
            'top_p': 0.7,          # Technisches Vokabular
            'top_k': 30            # Sehr fokussiert
        },

        '4': {
            'name': 'Business Consultant',
            'instruction': '''Du bist ein Unternehmensberater mit Fokus auf Business Strategy.
            - Gib strategische Ratschläge für Geschäftsfragen
            - Balance zwischen Kreativität und praktischer Umsetzung
            - Denk in ROI, KPIs und Business Metriken
            - Stelle Fragen zur Geschäftssituation
            - Gib konkrete Handlungsempfehlungen''',
            'temperature': 0.4,    # Ausgewogen
            'top_p': 0.85,         # Business-Sprache
            'top_k': 50            # Medium Range
        }
    }

    def __init__(self, api_key):
        """
        Initialisiert den Chatbot mit dem API Key.

        Parameter:
        - api_key: Google Generative AI API Key
        """
        genai.configure(api_key=api_key)
        self.chat = None
        self.current_persona = None
        self.session_name = None
        print("✅ Chatbot initialisiert\n")

    def start_new_chat(self, persona_key, session_name):
        """
        Startet eine neue Chat-Session mit einer bestimmten Persona.

        Was passiert hier:
        1. Persona-Config laden
        2. GenerativeModel mit Parametern erstellen
        3. Chat-Session starten (leere History)

        Parameter:
        - persona_key: Key aus PERSONAS (1, 2, 3 oder 4)
        - session_name: Name dieser Chat-Session (z.B. "Mein erstes Gespräch")

        Returns:
        - True wenn erfolgreich, False wenn fehler
        """
        try:
            # Schritt 1: Persona laden
            if persona_key not in self.PERSONAS:
                print(f"❌ Persona '{persona_key}' existiert nicht!")
                return False

            persona = self.PERSONAS[persona_key]
            self.current_persona = persona_key
            self.session_name = session_name

            print(f"🎭 Persona: {persona['name']}")
            print(f"📝 Session: {session_name}")
            print("-" * 70)

            # Schritt 2: GenerativeModel mit Parametern erstellen
            # WICHTIG: gemini-2.0-flash hat korrekte max_output_tokens!
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

            # Schritt 3: Chat-Session starten mit leerer History
            self.chat = model.start_chat(history=[])

            print(f"✅ Chat gestartet! Gib 'exit' ein um zu beenden.\n")
            return True

        except Exception as e:
            print(f"❌ Fehler beim Starten des Chats: {e}")
            return False

    def send_message(self, message):
        """
        Sendet eine Nachricht an Gemini und gibt die Antwort zurück.

        Was passiert:
        1. Message an API senden
        2. finish_reason überprüfen (STOP, MAX_TOKENS, SAFETY, etc.)
        3. Antwort zurückgeben oder Fehler melden

        Parameter:
        - message: Der Text, den wir senden

        Returns:
        - String: Die Antwort des Bots

        finish_reason Codes:
        - 1 = STOP (erfolg, normale Antwort)
        - 2 = MAX_TOKENS (Antwort wurde gekürzt)
        - 3 = SAFETY (Content Filter blockierte)
        - 4 = RECITATION (Copyright-Problem)
        """
        try:
            if not self.chat:
                return "❌ Kein Chat aktiv. Starte zuerst einen neuen Chat!"

            # API Request senden
            response = self.chat.send_message(message)

            # finish_reason überprüfen
            finish_reason = response.candidates[0].finish_reason

            if finish_reason == 1:  # STOP - erfolg
                return response.text

            elif finish_reason == 2:  # MAX_TOKENS - gekürzt
                text = response.candidates[0].content.parts[0].text if response.candidates[0].content.parts else ""
                if text:
                    print("\n⚠️  [WARNUNG] Antwort wurde gekürzt (MAX_TOKENS Limit erreicht)\n")
                    return text
                else:
                    return "❌ Keine Antwort (Token-Limit)"

            elif finish_reason == 3:  # SAFETY - blockiert
                return "⚠️  Antwort wurde aus Sicherheitsgründen blockiert"

            elif finish_reason == 4:  # RECITATION - Copyright
                return "⚠️  Antwort konnte nicht gegeben werden (Copyright-Problem)"

            else:
                return f"❌ Unbekannter Fehler (finish_reason={finish_reason})"

        except Exception as e:
            return f"❌ API Error: {str(e)}"

    def show_history(self):
        """
        Zeigt die komplette Chat-History formatiert.

        Was passiert:
        - Iteriere über self.chat.history
        - Zeige jede Message mit role (USER/AI) und content
        - Truncate lange Nachrichten (> 200 Zeichen) für bessere Übersicht
        """
        if not self.chat or not self.chat.history:
            print("❌ Keine Chat-History vorhanden\n")
            return

        print("\n" + "=" * 70)
        print(f"📜 CHAT HISTORY - {self.session_name}")
        print("=" * 70 + "\n")

        for i, message in enumerate(self.chat.history, 1):
            role = "👤 USER" if message.role == "user" else "🤖 AI"
            content = message.parts[0].text

            # Truncate lange Nachrichten für bessere Lesbarkeit
            if len(content) > 200:
                content_preview = content[:200] + "\n   [...gekürzt...]"
            else:
                content_preview = content

            print(f"{i}. [{role}]")
            print(f"   {content_preview}\n")

        print("=" * 70 + "\n")

    def save_current_chat(self):
        """
        Speichert den aktuellen Chat in die SQLite Datenbank.

        Was passiert:
        - Nutzt die save_conversation() Funktion
        - Übergibt session_name, persona und chat.history
        - Speichert alle Messages in der Datenbank

        Returns:
        - conversation_id wenn erfolgreich, None wenn fehler
        """
        try:
            if not self.chat:
                print("❌ Kein Chat zu speichern")
                return None

            # Get persona name
            persona_name = self.PERSONAS[self.current_persona]['name']

            # Speichern in Datenbank
            conversation_id = save_conversation(
                self.session_name,
                persona_name,
                self.chat.history
            )

            return conversation_id

        except Exception as e:
            print(f"❌ Fehler beim Speichern: {e}")
            return None


# ============================================================================
# TEIL 3: MENU SYSTEM - Benutzerinteraktion
# ============================================================================

def show_main_menu():
    """
    Zeigt das Hauptmenü des Chatbots.

    Optionen:
    1. Neuen Chat starten
    2. Gespeicherte Conversations anzeigen
    3. Programm beenden
    """
    print("\n" + "="*70)
    print("🤖 AI CHATBOT SYSTEM - HAUPTMENÜ")
    print("="*70)
    print("\n1️⃣  Neuen Chat starten")
    print("2️⃣  Gespeicherte Conversations anzeigen")
    print("3️⃣  Programm beenden")
    print("\n" + "-"*70)
    choice = input("Wähle eine Option (1-3): ").strip()
    return choice


def show_persona_menu():
    """
    Zeigt die verfügbaren Personas zum Auswählen.

    Der Nutzer wählt eine Persona für seinen Chat.
    """
    print("\n" + "="*70)
    print("🎭 PERSONA AUSWÄHLEN")
    print("="*70)

    for key, persona in GeminiChatbot.PERSONAS.items():
        print(f"{key}. {persona['name']}")
        print(f"   Temperature: {persona['temperature']} | top_p: {persona['top_p']} | top_k: {persona['top_k']}")
        print()

    print("-"*70)
    choice = input("Wähle eine Persona (1-4): ").strip()
    return choice


def get_session_name():
    """
    Fragt den Nutzer nach einem Namen für die Chat-Session.

    Returns:
    - String: Name der Session (z.B. "Mein erstes Gespräch")
    """
    print()
    session_name = input("Gib der Session einen Namen (z.B. 'Data Analysis Chat'): ").strip()
    if not session_name:
        session_name = f"Chat_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    return session_name


def run_chat_session(chatbot):
    """
    Führt eine interaktive Chat-Session aus.

    Befehle:
    - Normaler Text: Wird an den AI gesendet
    - 'history': Zeigt den Chat-Verlauf
    - 'save': Speichert den aktuellen Chat
    - 'exit': Beendet den Chat (mit Option zum Speichern)
    - 'menu': Zurück zum Hauptmenü

    Parameter:
    - chatbot: Die GeminiChatbot Instanz
    """
    print("\n" + "="*70)
    print("💬 CHAT GESTARTET")
    print("="*70)
    print("Tipps:")
    print("  - Gib 'history' ein um den Chat-Verlauf zu sehen")
    print("  - Gib 'save' ein um den Chat zu speichern")
    print("  - Gib 'exit' ein um zu beenden")
    print("="*70 + "\n")

    while True:
        try:
            user_input = input("👤 Du: ").strip()

            # Keine leere Eingabe
            if not user_input:
                continue

            # Befehl: history
            if user_input.lower() == 'history':
                chatbot.show_history()
                continue

            # Befehl: save
            if user_input.lower() == 'save':
                conversation_id = chatbot.save_current_chat()
                if conversation_id:
                    print(f"✅ Chat gespeichert (ID: {conversation_id})\n")
                continue

            # Befehl: menu
            if user_input.lower() == 'menu':
                print("↩️  Zurück zum Hauptmenü...\n")
                break

            # Befehl: exit
            if user_input.lower() == 'exit':
                save_choice = input("\n💾 Möchtest du den Chat speichern? (j/n): ").strip().lower()
                if save_choice == 'j':
                    conversation_id = chatbot.save_current_chat()
                    if conversation_id:
                        print(f"✅ Chat gespeichert (ID: {conversation_id})")
                print("👋 Chatbot beendet.\n")
                break

            # Normaler Message an AI
            print("\n🤖 Bot: ", end="", flush=True)
            response = chatbot.send_message(user_input)
            print(response)
            print()

        except KeyboardInterrupt:
            print("\n\n👋 Chat abgebrochen.")
            break
        except Exception as e:
            print(f"❌ Fehler: {e}\n")


def show_saved_conversations():
    """
    Zeigt alle gespeicherten Conversations aus der Datenbank.

    Der Nutzer kann eine Conversation auswählen um Details zu sehen.
    """
    conversations = load_conversations()

    if not conversations:
        print("\n❌ Keine gespeicherten Conversations vorhanden.\n")
        return

    print("\n" + "="*70)
    print("📚 GESPEICHERTE CONVERSATIONS")
    print("="*70 + "\n")

    for i, (conv_id, session_name, persona, created_at, updated_at) in enumerate(conversations, 1):
        # Formatiere die Timestamps schöner
        created_date = created_at.split('T')[0]
        created_time = created_at.split('T')[1][:5]

        print(f"{i}. {session_name}")
        print(f"   ID: {conv_id} | Persona: {persona}")
        print(f"   Erstellt: {created_date} {created_time}")
        print()

    print("-"*70)
    try:
        choice = input("Wähle eine Conversation um Details zu sehen (oder Enter zum Zurückgehen): ").strip()
        if choice.isdigit() and 1 <= int(choice) <= len(conversations):
            conv_id = conversations[int(choice) - 1][0]
            show_conversation_detail(conv_id)
    except Exception as e:
        print(f"❌ Fehler: {e}")


def show_conversation_detail(conversation_id):
    """
    Zeigt Details und alle Messages einer Conversation.

    Parameter:
    - conversation_id: Die ID der Conversation
    """
    messages = load_conversation_history(conversation_id)

    print("\n" + "="*70)
    print(f"📜 CONVERSATION DETAIL (ID: {conversation_id})")
    print("="*70 + "\n")

    for i, (role, content) in enumerate(messages, 1):
        role_display = "👤 USER" if role == "user" else "🤖 AI"

        # Truncate lange Inhalte
        if len(content) > 300:
            content_display = content[:300] + "\n   [...gekürzt...]"
        else:
            content_display = content

        print(f"{i}. [{role_display}]")
        print(f"   {content_display}\n")

    print("="*70 + "\n")


def main():
    """
    Hauptprogramm - Zentrale Kontrolle des Chatbots.

    Flow:
    1. Datenbank erstellen
    2. Chatbot initialisieren
    3. Hauptmenü-Loop zeigen
    4. Je nach Auswahl: Chat starten oder Conversations anzeigen
    """
    # Datenbank initialisieren
    create_database()

    # Chatbot mit API Key initialisieren
    if not API_KEY:
        print("❌ FEHLER: API_KEY nicht in .env gefunden!")
        print("   → Bitte API_KEY in .env eintragen")
        return

    chatbot = GeminiChatbot(API_KEY)

    # Hauptmenü-Loop
    while True:
        choice = show_main_menu()

        if choice == '1':
            # Neuen Chat starten
            persona_choice = show_persona_menu()

            if persona_choice not in GeminiChatbot.PERSONAS:
                print("❌ Ungültige Persona!\n")
                continue

            session_name = get_session_name()

            # Chat starten
            if chatbot.start_new_chat(persona_choice, session_name):
                run_chat_session(chatbot)

        elif choice == '2':
            # Gespeicherte Conversations anzeigen
            show_saved_conversations()

        elif choice == '3':
            # Programm beenden
            print("\n👋 Auf Wiedersehen!\n")
            break

        else:
            print("❌ Ungültige Option!\n")


# ============================================================================
# TEST: Alle Funktionen testen
# ============================================================================

if __name__ == "__main__":
    main()

