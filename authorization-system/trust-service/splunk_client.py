# splunk_client.py
import os, time, requests, urllib3
from datetime import datetime
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

SPLUNK_BASE = os.getenv("SPLUNK_BASE", "https://splunk:8089").rstrip("/")
SPLUNK_VERIFY_TLS = os.getenv("SPLUNK_VERIFY_TLS", "false").lower() in ("1", "true", "yes", "on")
SPLUNK_TOKEN = os.getenv("SPLUNK_TOKEN", "").strip()
SPLUNK_USERNAME = os.getenv("SPLUNK_USERNAME", "admin")
SPLUNK_PASSWORD = os.getenv("SPLUNK_PASSWORD", "changeme123")


def _to_epoch(v):
    """
    Converte v in epoch (float).
    Accetta: numeri, stringhe numeriche, ISO-8601 (con o senza Z), formati comuni Splunk.
    """
    if v is None:
        return time.time()
    if isinstance(v, (int, float)):
        return float(v)

    s = str(v).strip()
    # Prova come numero
    try:
        return float(s)
    except Exception:
        pass

    # ISO-8601 (es. 2025-11-06T18:28:11.034+00:00 o con 'Z')
    try:
        s2 = s.replace("Z", "+00:00")
        return datetime.fromisoformat(s2).timestamp()
    except Exception:
        pass

    # Fallback formati comuni
    for fmt in ("%Y-%m-%dT%H:%M:%S.%f%z",
                "%Y-%m-%dT%H:%M:%S%z",
                "%m/%d/%Y %H:%M:%S.%f %z",
                "%m/%d/%Y %H:%M:%S %z"):
        try:
            return datetime.strptime(s, fmt).timestamp()
        except Exception:
            continue

    # Ultima spiaggia: adesso
    return time.time()


def _get_auth_headers():
    """
    Preferisci un token (Settings → Authentication tokens).
    Se non presente, login per sessionKey.
    """
    if SPLUNK_TOKEN:
        return {"Authorization": f"Splunk {SPLUNK_TOKEN}"}

    r = requests.post(
        f"{SPLUNK_BASE}/services/auth/login",
        data={"username": SPLUNK_USERNAME, "password": SPLUNK_PASSWORD, "output_mode": "json"},
        timeout=20, verify=SPLUNK_VERIFY_TLS
    )
    r.raise_for_status()
    sk = r.json()["sessionKey"]
    return {"Authorization": f"Splunk {sk}"}


def oneshot_search(spl: str, earliest="-24h", latest="now"):
    """
    Esegue una ricerca oneshot e ritorna una lista di dict (risultati).
    """
    headers = _get_auth_headers()
    data = {
        "search": spl if spl.strip().lower().startswith("search ") else f"search {spl}",
        "output_mode": "json",
        "earliest_time": earliest,
        "latest_time": latest,
    }
    r = requests.post(
        f"{SPLUNK_BASE}/services/search/jobs/oneshot",
        data=data, headers=headers, timeout=90, verify=SPLUNK_VERIFY_TLS
    )
    r.raise_for_status()
    obj = r.json()
    return obj.get("results", [])


def get_user_events(username: str, earliest="-24h", latest="now"):
    """
    Ritorna eventi “grezzi” dall’indice, senza stato locale.
    Normalizziamo alcuni campi lato SPL e poi in Python (user, event, _time, ecc.).
    """
    spl = f"""
index=zt (user="{username}" OR preferred_username="{username}" OR username="{username}")
| eval event=coalesce(event,type)
| eval event=lower(event)
| table _time event sourcetype src_ip user preferred_username username severity decision
"""
    results = oneshot_search(spl, earliest=earliest, latest=latest)
    out = []
    for r in results:
        # _time robusto
        r["_time"] = _to_epoch(r.get("_time"))
        # normalizza chiavi comuni
        r["event"] = (r.get("event") or "").lower()
        r["user"] = r.get("user") or r.get("preferred_username") or r.get("username") or ""
        r["src_ip"] = r.get("src_ip", "")
        r["sourcetype"] = r.get("sourcetype", "")
        out.append(r)
    return out
