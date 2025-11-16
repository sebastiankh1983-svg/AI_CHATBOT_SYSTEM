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
            resp = requests.post(url, json=payload or {}, headers=HEADERS, timeout=15)
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
    start_url = API + "/chat/start"
    send_url = API + "/chat/send"

    start_payload = {"persona_key": "1", "session_name": "DiagnoseSession"}
    start_res = check_endpoint("CHAT_START", start_url, method="POST", payload=start_payload)

    send_res = None
    if start_res.get("ok") and start_res.get("status_code") == 200:
        time.sleep(1)  # minimale Verzögerung
        send_payload = {"message": "Diagnose-Testnachricht"}
        send_res = check_endpoint("CHAT_SEND", send_url, method="POST", payload=send_payload)
    else:
        send_res = {"name": "CHAT_SEND", "skipped": True, "reason": "Start fehlgeschlagen"}

    history_res = check_endpoint("CHAT_HISTORY", API + "/chat/history", method="GET")
    return [start_res, send_res, history_res]


def main():
    print("===== RAILWAY DIAGNOSE START =====")
    print(f"Basis URL: {BASE_URL}")
    print(f"API Base: {API}\n")

    results = [check_endpoint(name, url, m) for (name, url, m) in ENDPOINTS]
    chat_sequence = run_chat_flow()

    all_results = results + chat_sequence

    problems = []
    for r in all_results:
        if r.get("error") or (r.get("status_code") and r.get("status_code") >= 400):
            problems.append(r)

    print("\n--- DETAILAUSGABE ---")
    for r in all_results:
        print(f"\n[{r['name']}] {r.get('url','')} status={r.get('status_code')} ok={r.get('ok')} error={r.get('error')}")
        print(pretty(r.get('data')))

    print("\n--- ZUSAMMENFASSUNG ---")
    if not problems:
        print("✅ Keine Fehler erkannt – Backend scheint erreichbar und funktionsfähig.")
    else:
        print(f"❌ {len(problems)} Problem(e) erkannt:")
        for p in problems:
            print(f" - {p['name']}: status={p.get('status_code')} error={p.get('error')} data={str(p.get('data'))[:120]}")

    # Handlungstipps
    print("\n--- EMPFOHLENE NÄCHSTE SCHRITTE ---")
    if any(r['name'] == 'CHAT_START' and (r.get('status_code') == 500) for r in all_results):
        print("• Prüfe GOOGLE_API_KEY in Railway Variables – fehlt oder ungültig.")
    if any(r['name'] == 'CHAT_START' and (r.get('status_code') == 400) for r in all_results):
        print("• Prüfe persona_key oder session_name aus dem Frontend.")
    if any(r['name'] == 'CHAT_SEND' and (r.get('status_code') == 400) for r in all_results):
        print("• SEND ohne aktiven Chat – Reihenfolge im Frontend korrigieren.")
    if any(r.get('error') for r in all_results):
        print("• Netzwerk- oder Timeoutfehler – Domain / API_BASE_URL / CORS prüfen.")

    print("\n===== RAILWAY DIAGNOSE ENDE =====")


if __name__ == "__main__":
    main()

