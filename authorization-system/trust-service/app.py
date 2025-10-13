from flask import Flask, request, jsonify
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime
import os
import math

app = Flask(__name__)

# ================================
# CONFIG
# ================================
T_SCALE_MINUTES = int(os.getenv("T_SCALE_MINUTES", "2"))  # 1 giorno = 1440 min , attualmente settato a 2 minuti per testing

# ================================
# Connessione con il Postgres
# ================================
def get_conn():
    return psycopg2.connect(
        dbname="companydb",
        user="trust_user",
        password="trust_pass",
        host="postgres",
        port="5432"
    )

# ================================
# Healthcheck
# ================================
@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "trust-service up"}), 200


# ================================
# Registra evento (login_fail, login_success, ecc.)
# non avviene l'aggiornamento dello score
# ================================
@app.route("/event", methods=["POST"])
def register_event():
    data = request.get_json()
    username = data.get("username")
    event_type = data.get("event_type")

    if not username or not event_type:
        return jsonify({"error": "username and event_type required"}), 400

    conn = get_conn()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    try:
        # Recupera impatto associato all'evento
        cur.execute("SELECT impact FROM trust.event_types WHERE event_type = %s", (event_type,))
        event = cur.fetchone()
        if not event:
            return jsonify({"error": f"unknown event_type: {event_type}"}), 400
        impact = event["impact"]

        # Recupera utente
        cur.execute("SELECT user_id FROM trust.users WHERE username = %s", (username,))
        user = cur.fetchone()
        if not user:
            return jsonify({"error": f"user {username} not found"}), 404

        user_id = user["user_id"]

        # Inserisci l'evento
        cur.execute("""
            INSERT INTO trust.events (user_id, event_type, impact)
            VALUES (%s, %s, %s);
        """, (user_id, event_type, impact))

        conn.commit()

        return jsonify({
            "username": username,
            "event_type": event_type,
            "impact": impact,
            "message": "Event registered (score will change only in /score_dynamic)"
        }), 200

    except Exception as e:
        conn.rollback()
        return jsonify({"error": str(e)}), 500

    finally:
        cur.close()
        conn.close()


# ================================
# Recupera punteggio utente (per testing)
# ================================
@app.route("/score/<username>", methods=["GET"])
def get_score(username):
    conn = get_conn()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute("SELECT username, current_score FROM trust.users WHERE username = %s", (username,))
    user = cur.fetchone()
    cur.close()
    conn.close()

    if not user:
        return jsonify({"error": "user not found"}), 404
    return jsonify(user), 200


# ================================
# Calcola punteggio dinamico (solo calcolo, non aggiorna il Database)
# ================================
@app.route("/score_dynamic/<username>", methods=["GET"])
def get_dynamic_score(username):
    conn = get_conn()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    try:
        # Recupera utente
        cur.execute("SELECT user_id, initial_score FROM trust.users WHERE username = %s", (username,))
        user = cur.fetchone()
        if not user:
            return jsonify({"error": "user not found"}), 404

        # Recupera eventi
        cur.execute("""
            SELECT impact, occurred_at
            FROM trust.events
            WHERE user_id = %s
            ORDER BY occurred_at DESC;
        """, (user["user_id"],))
        events = cur.fetchall()

        # Calcolo con decadimento esponenziale
        now = datetime.utcnow()
        score = float(user["initial_score"])
        details = []

        for e in events:
            delta_min = (now - e["occurred_at"]).total_seconds() / 60.0
            weight = math.exp(-delta_min / T_SCALE_MINUTES)
            weighted_impact = e["impact"] * weight
            score += weighted_impact
            details.append({
                "impact": e["impact"],
                "minutes_ago": round(delta_min, 1),
                "weight": round(weight, 4),
                "weighted_impact": round(weighted_impact, 2)
            })

        return jsonify({
            "username": username,
            "score": round(score, 2),
            "T_scale": T_SCALE_MINUTES,
            "events_count": len(events),
            "details": details[-5:]  # ultimi 5 eventi
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

    finally:
        cur.close()
        conn.close()


# ================================
# Main
# ================================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)