import os
import math
import json
from datetime import datetime
from flask import Flask, request, jsonify
import psycopg2
import psycopg2.extras

DB_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@postgres:5432/companydb")
T_SCALE_MINUTES = float(os.getenv("T_SCALE_MINUTES", "1440"))
PORT = int(os.getenv("PORT", "5000"))

app = Flask(__name__)

def get_conn():
    return psycopg2.connect(DB_URL)

def compute_score_for_user(conn, user_id):
    """
    Calcola il TSu per user_id usando eventi e event_types (decadimento esponenziale).
    Restituisce (score, initial_score).
    """
    cur = conn.cursor()
    cur.execute("SELECT initial_score FROM trust.users WHERE user_id = %s", (user_id,))
    row = cur.fetchone()
    if not row:
        return None, None
    initial_score = float(row[0])

    cur.execute("""
      SELECT COALESCE(e.impact, et.impact) as impact, e.occurred_at
      FROM trust.events e
      LEFT JOIN trust.event_types et ON e.event_type = et.event_type
      WHERE e.user_id = %s
    """, (user_id,))
    total = 0.0
    now = datetime.utcnow()
    for impact, occurred_at in cur.fetchall():
        if impact is None or occurred_at is None:
            continue
        minutes = (now - occurred_at).total_seconds() / 60.0
        weight = math.exp(- minutes / T_SCALE_MINUTES)
        total += float(impact) * weight

    score = initial_score + total

    # persist snapshot
    cur.execute("UPDATE trust.users SET current_score = %s, updated_at = now() WHERE user_id = %s",
                (score, user_id))
    cur.execute("INSERT INTO trust.score_history (user_id, score) VALUES (%s, %s)",
                (user_id, score))
    conn.commit()
    return score, initial_score

@app.route("/score/<username>", methods=["GET"])
def get_score(username):
    """
    Ritorna il punteggio aggiornato per username.
    """
    conn = get_conn()
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    cur.execute("SELECT user_id FROM trust.users WHERE username = %s", (username,))
    row = cur.fetchone()
    if not row:
        return jsonify({"error": "user not found"}), 404
    user_id = row["user_id"]
    score, initial = compute_score_for_user(conn, user_id)
    conn.close()
    return jsonify({"username": username, "initial_score": initial, "score": score})

@app.route("/events", methods=["POST"])
def post_event():
    """
    Body JSON:
    {
      "username": "mrossi",
      "event_type": "login_fail",
      "impact": optional int,
      "occurred_at": optional ISO timestamp
    }
    """
    data = request.get_json(force=True)
    username = data.get("username")
    if not username:
        return jsonify({"error": "username required"}), 400
    event_type = data.get("event_type")
    impact = data.get("impact")  # optional, if provided overrides event_types
    occurred_at = data.get("occurred_at")  # optional ISO string

    conn = get_conn()
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    cur.execute("SELECT user_id FROM trust.users WHERE username = %s", (username,))
    row = cur.fetchone()
    if not row:
        conn.close()
        return jsonify({"error": "user not found"}), 404
    user_id = row["user_id"]

    if occurred_at:
        try:
            occurred_at_ts = datetime.fromisoformat(occurred_at)
        except Exception:
            conn.close()
            return jsonify({"error": "invalid occurred_at format, use ISO"}), 400
    else:
        occurred_at_ts = datetime.utcnow()

    # Insert event
    if impact is None:
        cur.execute("INSERT INTO trust.events (user_id, event_type, occurred_at) VALUES (%s, %s, %s)",
                    (user_id, event_type, occurred_at_ts))
    else:
        cur.execute("INSERT INTO trust.events (user_id, event_type, impact, occurred_at) VALUES (%s, %s, %s, %s)",
                    (user_id, event_type, impact, occurred_at_ts))
    conn.commit()

    # Recompute immediately (synchronous). Could be async in production.
    score, initial = compute_score_for_user(conn, user_id)

    conn.close()
    return jsonify({"username": username, "score": score}), 201

@app.route("/recompute/<username>", methods=["POST"])
def recompute(username):
    conn = get_conn()
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    cur.execute("SELECT user_id FROM trust.users WHERE username = %s", (username,))
    row = cur.fetchone()
    if not row:
        conn.close()
        return jsonify({"error": "user not found"}), 404
    user_id = row["user_id"]
    score, initial = compute_score_for_user(conn, user_id)
    conn.close()
    return jsonify({"username": username, "score": score}), 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=PORT)
