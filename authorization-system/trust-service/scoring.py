import math
import os

import time
import os
from typing import Optional

def get_baseline_for(username: str) -> float:
    # baseline fissa
    return float(os.getenv("TS_BASELINE", "80"))




# --- aggiungi/amplia la mappa ---
IMPACTS = {
    "login_success": +5,
    "login_fail": -2,
    "login_failed": -4,           
    "login_off_hours": -2,
    "login_failed_streak3": -30,
}

BASELINE = 80
TAU_SECONDS = 24 * 3600  # decadimento 24h
T_SCALE_MINUTES = float(os.getenv("T_SCALE_MINUTES", "2"))  # 1440 per 1 giorno


def normalize_event(event: str | None, sourcetype: str | None = "") -> str:
    e  = (event or "").strip().lower().replace("-", "_")
    st = (sourcetype or "").strip().lower()
    if st.startswith("keycloak"):
        if e in {"login", "code_to_token"}:
            return "login_success"
        if "error" in e or e in {"login_error"}:
            return "login_failed"
    return e

def event_impact(event: str,
                 sourcetype: str | None = None,
                 severity: str | None = None,
                 decision: str | None = None) -> float:
    ev = normalize_event(event, sourcetype)
    if ev in IMPACTS:
        return float(IMPACTS[ev])
    # (heuristic extra opzionali per snort/envoy, se ti servono)
    return 0.0

