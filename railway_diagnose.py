import sys
import time
import json
import requests

BASE_URL = "https://aichatbotsystem-production-adc4.up.railway.app"  # Deine aktuelle Railway Domain
API = BASE_URL + "/api"

ENDPOINTS = [
    ("PING", API + "/ping", "GET"),
    ("HEALTH", API + "/health", "GET"),
    ("PERSONAS", API + "/personas", "GET"),
    ("CAPABILITIES", API + "/capabilities", "GET"),
    ("DEBUG_SESSION", API + "/debug-session", "GET"),
    ("DIAGNOSTIC", API + "/diagnostic", "GET"),
]

HEADERS = {"Content-Type": "application/json"}


def pretty(obj):
    try:
        return json.dumps(obj, indent=2, ensure_ascii=False)
    except Exception:
        return str(obj)


def check_endpoint(name, url, method="GET", payload=None):
    try:
        if method == "GET":
            resp = requests.get(url, timeout=10)
        elif method == "POST":
            resp = requests.post(url, json=payload or {}, headers=HEADERS, timeout=30)
        else:
            return {"name": name, "error": f"Nicht unterstützte Methode {method}"}
        data = None
        try:
            data = resp.json()
        except Exception:
            data = resp.text
        return {
            "name": name,
            "url": url,
            "status_code": resp.status_code,
            "ok": resp.ok,
            "data": data
        }
    except requests.exceptions.RequestException as e:
        return {"name": name, "url": url, "error": str(e)}


def run_chat_flow():
    """Testet Multi-Session Flow mit session_id."""
    start_url = API + "/chat/start"
    send_url = API + "/chat/send"

    start_payload = {"persona_key": "1", "session_name": "DiagnoseSession"}
    start_res = check_endpoint("CHAT_START", start_url, method="POST", payload=start_payload)

    session_id = None
    if start_res and start_res.get("ok") and start_res.get("status_code") == 200:
        session_id = start_res.get("data", {}).get("session_id")

    send_res1 = None
    send_res2 = None
    session_history_res = None

    if session_id:
        time.sleep(1)
        send_payload1 = {"message": "Diagnose-Testnachricht", "session_id": session_id}
        send_res1 = check_endpoint("CHAT_SEND_1", send_url, method="POST", payload=send_payload1)
        time.sleep(1)
        send_payload2 = {"message": "Zweite Nachricht", "session_id": session_id}
        send_res2 = check_endpoint("CHAT_SEND_2", send_url, method="POST", payload=send_payload2)
        session_history_res = check_endpoint("SESSION_HISTORY", API + f"/chat/session/{session_id}/history", method="GET")
    else:
        send_res1 = {"name": "CHAT_SEND_1", "skipped": True, "reason": "Keine session_id"}
        send_res2 = {"name": "CHAT_SEND_2", "skipped": True, "reason": "Keine session_id"}
        session_history_res = {"name": "SESSION_HISTORY", "skipped": True, "reason": "Keine session_id"}

    history_res = check_endpoint("GLOBAL_HISTORY", API + "/chat/history", method="GET")

    # Rückgabe garantiert nur Dicts
    return [start_res or {"name": "CHAT_START", "error": "start_res None"},
            send_res1,
            send_res2,
            session_history_res,
            history_res or {"name": "GLOBAL_HISTORY", "error": "history_res None"}]


def main():
    print("===== RAILWAY DIAGNOSE START =====")
    print(f"Basis URL: {BASE_URL}")
    print(f"API Base: {API}\n")

    results = [check_endpoint(name, url, m) for (name, url, m) in ENDPOINTS]
    chat_sequence = run_chat_flow()

    all_results = results + chat_sequence

    problems = []
    for r in all_results:
        if not isinstance(r, dict):
            continue
        if r.get("error") or (r.get("status_code") and r.get("status_code") >= 400):
            problems.append(r)

    print("\n--- DETAILAUSGABE ---")
    for r in all_results:
        print(f"\n[{r['name']}] {r.get('url','')} status={r.get('status_code')} ok={r.get('ok')} error={r.get('error')}")
        print(pretty(r.get('data')))

    print("\n--- ZUSAMMENFASSUNG ---")
    if not problems:
        print("✅ Keine Fehler erkannt – Basisfunktionalität läuft.")
    else:
        print(f"❌ {len(problems)} Problem(e) erkannt:")
        for p in problems:
            print(f" - {p['name']}: status={p.get('status_code')} error={p.get('error')} data={str(p.get('data'))[:160]}")

    # Handlungstipps gezielt
    print("\n--- EMPFOHLENE NÄCHSTE SCHRITTE ---")
    start_res = next((r for r in all_results if r['name'] == 'CHAT_START'), None)
    if start_res and start_res.get('status_code') == 200:
        sid = start_res.get('data', {}).get('session_id')
        print(f"• session_id erhalten: {sid}")
    if any(r['name'].startswith('CHAT_SEND') and r.get('status_code') == 400 for r in all_results):
        print("• SEND 400: Prüfe ob session_id korrekt im Payload übergeben wird.")
    if any(r['name'] == 'CHAT_START' and r.get('status_code') == 500 for r in all_results):
        print("• START 500: GOOGLE_API_KEY auf Railway prüfen.")
    if any(r['name'].startswith('CHAT_SEND') and r.get('status_code') == 500 for r in all_results):
        print("• SEND 500: Antwortverarbeitung oder Gemini API Problem – Logs ansehen.")
    if any(r['name'] == 'SESSION_HISTORY' and r.get('status_code') == 404 for r in all_results):
        print("• SESSION_HISTORY 404: session_id im Frontend verloren – State Management prüfen.")

    print("\n===== RAILWAY DIAGNOSE ENDE =====")


if __name__ == "__main__":
    main()
