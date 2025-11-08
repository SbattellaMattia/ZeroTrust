import os, time, math
from flask import Flask, jsonify, request
import splunk_client
import scoring  # usa la tua mappa impatti e baseline

T_SCALE_MINUTES = float(os.getenv("T_SCALE_MINUTES", "1440"))
WINDOW_MIN = float(os.getenv("WINDOW_MIN", "1440"))  # finestra log, es. 24h

app = Flask(__name__)

# --- Orario lavorativo (default: lun-ven, 06:00–22:00, fuso = UTC) ---
WORK_START_HOUR = int(os.getenv("WORK_START_HOUR", "6"))      # 0..23
WORK_END_HOUR   = int(os.getenv("WORK_END_HOUR",   "22"))     # 0..23 (non incluso se vuoi intervallo chiuso-aperto)
WORKDAYS        = os.getenv("WORKDAYS", "0,1,2,3,4")          # 0=Lun ... 6=Dom (ISO), default Lun–Ven
TZ_OFFSET_MIN   = int(os.getenv("WORK_TZ_OFFSET_MIN", "60"))   # Rome UTC+1 = +60 minuti

_WORKDAYS_SET = {int(x) for x in WORKDAYS.split(",") if x.strip() != ""}

def _is_work_time(epoch_seconds: float) -> bool:
    """
    Ritorna True se ts cade in un giorno/orario lavorativo.
    Usiamo UTC+offset (WORK_TZ_OFFSET_MIN) per il controllo.
    """
    ts = float(epoch_seconds)
    ts_shifted = ts + TZ_OFFSET_MIN * 60
    tt = time.gmtime(ts_shifted)  # struct_time in “UTC+offset”
    wd = (tt.tm_wday)  # 0=Mon .. 6=Sun (ISO)
    if wd not in _WORKDAYS_SET:
        return False
    hour = tt.tm_hour
    # intervallo chiuso-aperto [start, end) tipico
    return (WORK_START_HOUR <= hour < WORK_END_HOUR)


@app.get("/score_dynamic/<username>")
def score_dynamic(username):
    base = scoring.get_baseline_for(username)
    now = time.time()

    # pzionale limite superiore temporale (epoch secondi)
    latest_ts = request.args.get("latest_ts", type=float)
    earliest = f"-{int(WINDOW_MIN)}m"

    events = splunk_client.get_user_events(
        username, earliest=earliest, latest="now"
    )
    events.sort(key=lambda e: float(e.get("_time", e.get("ts", now))))

    # Se latest_ts è passato, tieni solo gli eventi con _time <= latest_ts
    if latest_ts:
        events = [e for e in events if float(e.get("_time", now)) <= latest_ts]

    score = base
    details = []
    fails = 0

    for ev in events:
        event_norm = scoring.normalize_event(ev.get("event"), sourcetype=ev.get("sourcetype"))
        if event_norm == "login_failed":
            fails += 1
            if fails % 3 == 0:
                event_norm = "login_failed_streak3"
        elif event_norm == "login_success":
            fails = 0

        impact = scoring.event_impact(
            event=event_norm,
            sourcetype=ev.get("sourcetype"),
            severity=ev.get("severity"),
            decision=ev.get("decision"),
        )

        ts_ev = float(ev.get("_time", now))
        if event_norm == "login_success":
            if not _is_work_time(ts_ev):
                impact = scoring.IMPACTS.get("login_off_hours", 0)
                event_norm = "login_off_hours"
        

        minutes_ago = max((now - ts_ev) / 60.0, 0.0)
        weight = math.exp(-minutes_ago / T_SCALE_MINUTES)
        weighted = float(impact) * weight
        score += weighted

        details.append({
            "event": event_norm,
            "impact": impact,
            "minutes_ago": round(minutes_ago, 1),
            "weight": round(weight, 4),
            "weighted_impact": round(weighted, 2),
            "src_ip": ev.get("src_ip"),
            "sourcetype": ev.get("sourcetype"),
        })

    return jsonify({
        "user": username,
        "baseline": base,
        "score": round(score, 2),
        "T_scale_minutes": T_SCALE_MINUTES,
        "window_minutes": WINDOW_MIN,
        "events_total": len(events),
        "details": details
    }), 200

@app.get("/healthz")
def healthz():
    return jsonify({"status": "ok"}), 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port =int(os.getenv("PORT", "5000")), debug=False)
