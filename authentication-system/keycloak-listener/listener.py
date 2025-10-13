import requests
import time
import os
from datetime import datetime
import pytz  # fuso orario italiano
import psycopg2
from psycopg2.extras import RealDictCursor

# === CONFIG ===
KEYCLOAK_BASE = os.getenv("KEYCLOAK_BASE", "http://keycloak:8081")
KEYCLOAK_REALM = os.getenv("KEYCLOAK_REALM", "zerotrust")
KEYCLOAK_ADMIN_USER = os.getenv("KEYCLOAK_ADMIN_USER", "admin")
KEYCLOAK_ADMIN_PASS = os.getenv("KEYCLOAK_ADMIN_PASS", "admin")
KEYCLOAK_TOKEN_REFRESH_MINS = int(os.getenv("TOKEN_REFRESH_MINS", "4"))

POLL_INTERVAL = int(os.getenv("POLL_INTERVAL", "10"))

DB_HOST = os.getenv("DB_HOST", "postgres")
DB_NAME = os.getenv("DB_NAME", "companydb")
DB_USER = os.getenv("DB_USER", "trust_user")
DB_PASS = os.getenv("DB_PASS", "trust_pass")


WORK_START = 6   # ora inizio lavoro
WORK_END = 22     # ora fine lavoro

print(f" Keycloak Listener (work-hour aware, local time)")
print(f" BASE={KEYCLOAK_BASE} | REALM={KEYCLOAK_REALM} | POLL={POLL_INTERVAL}s | REFRESH={KEYCLOAK_TOKEN_REFRESH_MINS}m")


# === Connessione DB ===
def get_db_conn():
    return psycopg2.connect(
        host=DB_HOST,
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASS
    )

# === Prende token admin per controllare log del Realm ZeroTrust ===
def get_token():
    url = f"{KEYCLOAK_BASE}/realms/master/protocol/openid-connect/token"
    data = {
        "client_id": "admin-cli",
        "grant_type": "password",
        "username": KEYCLOAK_ADMIN_USER,
        "password": KEYCLOAK_ADMIN_PASS,
    }
    print(" Requesting admin token...")
    r = requests.post(url, data=data, timeout=5)
    r.raise_for_status()
    print(f" Token acquired ({r.status_code})")
    return r.json()["access_token"]

def get_events(token):
    url = f"{KEYCLOAK_BASE}/admin/realms/{ KEYCLOAK_REALM}/events"
    headers = {"Authorization": f"Bearer {token}"}
    r = requests.get(url, headers=headers, timeout=5)
    r.raise_for_status()
    return r.json()

# === Scrivi evento nel DB ===
def save_event_to_db(username, event_type, source_ip=None):
    conn = get_db_conn()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    try:
        # 1. Recupera utente
        cur.execute("SELECT user_id FROM trust.users WHERE username = %s", (username,))
        user = cur.fetchone()
        
        if not user:
            print(f" User: {username} not found")
            return
        else:
            user_id = user["user_id"]
        
        # 2. Recupera impact da event_types
        cur.execute("SELECT impact FROM trust.event_types WHERE event_type = %s", (event_type,))
        event_def = cur.fetchone()
        
        if not event_def:
            print(f" WARNING: unknown event_type '{event_type}', skipping")
            return
        
        impact = event_def["impact"]
        
        # 3. Inserisci evento
        cur.execute("""
            INSERT INTO trust.events (user_id, event_type, impact, source_ip, occurred_at)
            VALUES (%s, %s, %s, %s, NOW())
        """, (user_id, event_type, impact, source_ip))
        
        conn.commit()
        print(f" Saved event: {username} → {event_type} (impact={impact})")
        
    except Exception as e:
        conn.rollback()
        print(f" DB error: {e}")
    finally:
        cur.close()
        conn.close()

# === Gestione login con orario ===
def handle_login_event(username, source_ip=None):
    tz = pytz.timezone("Europe/Rome")
    now = datetime.now(tz)
    hour = now.hour

    if WORK_START <= hour < WORK_END:
        event_type = "login_success"
        print(f" {username} logged in during work hours ({hour}:00)")
    else:
        event_type = "login_off_hours"
        print(f" {username} logged in outside work hours ({hour}:00)")

    save_event_to_db(username, event_type, source_ip)


# === MAIN LOOP ===
if __name__ == "__main__":
    token = get_token()
    token_acquired = time.time()
    user_fails = {}

    # ignora eventi vecchi ( per evitare duplicati )
    try:
        existing = get_events(token)
        last_check = max(e["time"] for e in existing) if existing else 0
        print(f" Ignoring {len(existing)} pre-existing events (last time={last_check})")
    except Exception:
        last_check = 0
        print(" Could not pre-fetch events, starting fresh.")

    while True:
        try:
            # Refresh token periodico
            if time.time() - token_acquired >  KEYCLOAK_TOKEN_REFRESH_MINS * 60:
                print(" Refreshing token...")
                token = get_token()
                token_acquired = time.time()

            events = get_events(token)
            new_events = [e for e in events if e["time"] > last_check]
            if new_events:
                last_check = max(e["time"] for e in new_events)
            else:
                time.sleep(POLL_INTERVAL)
                continue

            for e in new_events:
                etype = e.get("type")
                username = e.get("details", {}).get("username") or e.get("userId")
                if not username or not etype:
                    continue

                #=========================================
                # Eventi possibili
                #=========================================
                match etype:

                    case "LOGIN_ERROR":
                        user_fails[username] = user_fails.get(username, 0) + 1
                        print(f" {username} login error ({user_fails[username]%3}/3)")
                        if not (user_fails[username]%3):
                            print(f" {username} reached 3 consecutive login errors → save to DB")
                            save_event_to_db(username, "login_fail", e.get("ipAddress"))  
                            user_fails[username] = 0
                        if user_fails[username] == 10:
                            save_event_to_db(username, "brute_force_detected", e.get("ipAddress"))
                            user_fails[username] = 0 

                    case "LOGIN":
                        handle_login_event(username, e.get("ipAddress"))
                        user_fails[username] = 0 

                    case _:
                        #default
                        print(f"Event type {etype} unknown")

            time.sleep(POLL_INTERVAL)

        except requests.exceptions.HTTPError as ex:
            if "401" in str(ex):
                print(" Token expired → refreshing...")
                token = get_token()
                token_acquired = time.time()
            else:
                print(f" HTTP error: {ex}")
            time.sleep(POLL_INTERVAL)

        except Exception as e:
            print(f" General error: {e}")
            time.sleep(POLL_INTERVAL)