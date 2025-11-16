# 🔗 RAILWAY & FIREBASE URLs - QUICK REFERENCE

## ✅ WAS IST RICHTIG?

### Backend (Railway):

**Base URL:**
```
https://ai-chatbot-system-production-xxxx.up.railway.app
```

**Endpoints zum Testen (im Browser):**
```
✅ https://deine-url.railway.app/                    → API Info
✅ https://deine-url.railway.app/api/health          → Health Check
✅ https://deine-url.railway.app/api/personas        → Personas Liste
```

**Im Frontend Code (chatbot.js):**
```javascript
const API_BASE_URL = 'https://deine-url.railway.app/api';
//                                                    ^^^^
//                                              Endet mit /api !
```

---

## ❌ WAS IST FALSCH?

### Falsche URLs:

```javascript
// ❌ FALSCH - localhost funktioniert nicht online
const API_BASE_URL = 'http://localhost:5000/api';

// ❌ FALSCH - HTTP statt HTTPS
const API_BASE_URL = 'http://deine-url.railway.app/api';

// ❌ FALSCH - /api fehlt
const API_BASE_URL = 'https://deine-url.railway.app';

// ❌ FALSCH - Doppeltes /api
const API_BASE_URL = 'https://deine-url.railway.app/api/api';
```

---

## 📝 BEISPIEL (mit echter URL):

### Railway gibt dir:
```
https://ai-chatbot-system-production-1a2b.up.railway.app
```

### Im Browser testen:
```
Root:     https://ai-chatbot-system-production-1a2b.up.railway.app/
Health:   https://ai-chatbot-system-production-1a2b.up.railway.app/api/health
Personas: https://ai-chatbot-system-production-1a2b.up.railway.app/api/personas
```

### Im Frontend (chatbot.js):
```javascript
const API_BASE_URL = 'https://ai-chatbot-system-production-1a2b.up.railway.app/api';
```

### Axios macht dann:
```javascript
// Wenn du startChat aufrufst:
axios.post(`${API_BASE_URL}/chat/start`, {...})

// Wird zu:
axios.post('https://ai-chatbot-system-production-1a2b.up.railway.app/api/chat/start', {...})
                                                                       ^^^^^^^^^^^^^^^^
                                                                       Richtiger Endpoint!
```

---

## 🎯 DEINE AUFGABE:

1. **Railway URL finden:**
   - Railway Dashboard → Dein Projekt → Settings → Domains
   - Kopiere die URL (komplett!)

2. **Im Frontend eintragen:**
   ```javascript
   // ai_chatbot_frontend/src/api/chatbot.js
   const API_BASE_URL = 'https://DEINE-RAILWAY-URL.railway.app/api';
   ```

3. **Frontend neu deployen:**
   ```bash
   npm run build
   firebase deploy
   ```

4. **Testen:**
   - Firebase URL öffnen
   - Persona auswählen
   - Chat starten

---

## ✅ SCHNELLTEST:

### Backend Test (Railway):
```
Browser: https://DEINE-RAILWAY-URL.railway.app/api/health
Sollte zeigen: {"status":"ok","message":"AI Chatbot API läuft"}
```

### Frontend Test (Browser DevTools Console):
```javascript
fetch('https://DEINE-RAILWAY-URL.railway.app/api/health')
  .then(r => r.json())
  .then(d => console.log(d))
  .catch(e => console.error(e));
```

**Erwartung:** Keine Errors, Response mit "status":"ok"

---

## 🔒 SICHERHEIT:

**NUR in chatbot.js ändern:**
```javascript
const API_BASE_URL = 'https://...';  // ✅ OK
```

**NIEMALS im Code:**
```javascript
const API_KEY = 'AIza...';  // ❌ NIEMALS!
```

API Key bleibt in:
- ✅ Railway Environment Variables
- ✅ Lokale .env Datei
- ❌ NIEMALS in Git
- ❌ NIEMALS im Frontend Code

---

**Zusammenfassung:**
- Railway URL endet mit `/api` im Frontend Code
- Zum Testen im Browser: URL + `/api/health`
- Immer HTTPS, nie HTTP
- API Key nur in Railway Variables

