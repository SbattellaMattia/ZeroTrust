-- ./postgres/init/init.sql
-- Schema per Trust Score

CREATE SCHEMA IF NOT EXISTS trust;

-- users: utente con score
CREATE TABLE IF NOT EXISTS trust.users (
  user_id SERIAL PRIMARY KEY,
  username TEXT UNIQUE NOT NULL,
  initial_score NUMERIC NOT NULL DEFAULT 80,
  current_score NUMERIC,
  updated_at TIMESTAMP DEFAULT now()
);

-- event_types: mapping evento -> impatto (dati configurabili)
CREATE TABLE IF NOT EXISTS trust.event_types (
  event_type TEXT PRIMARY KEY,
  impact INT NOT NULL
);

-- events: eventi grezzi
CREATE TABLE IF NOT EXISTS trust.events (
  event_id SERIAL PRIMARY KEY,
  user_id INT REFERENCES trust.users(user_id) ON DELETE CASCADE,
  event_type TEXT REFERENCES trust.event_types(event_type),
  impact INT,                 -- opzionale: sovrascrive event_types.impact
  occurred_at TIMESTAMP NOT NULL DEFAULT now()
);

-- score history (storico snapshot)
CREATE TABLE IF NOT EXISTS trust.score_history (
  id SERIAL PRIMARY KEY,
  user_id INT REFERENCES trust.users(user_id),
  score NUMERIC NOT NULL,
  computed_at TIMESTAMP NOT NULL DEFAULT now()
);

-- Indici utili
CREATE INDEX IF NOT EXISTS idx_trust_events_user ON trust.events(user_id);
CREATE INDEX IF NOT EXISTS idx_trust_events_time ON trust.events(occurred_at);

-- Insert valori di esempio per event_types
INSERT INTO trust.event_types (event_type, impact) VALUES
  ('login_success', 0),
  ('login_fail', -5),
  ('login_unknown_ip', -10),
  ('mfa_success', 5),
  ('suspicious_activity', -20)
ON CONFLICT (event_type) DO NOTHING;

-- Esempio utenti
INSERT INTO trust.users (username, initial_score, current_score) VALUES
  ('mrossi', 80, 80),
  ('lbianchi', 80, 80)
ON CONFLICT (username) DO NOTHING;

-- Facoltativo: crea un DB role per il Trust Service (user: root)
DO
$$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'trust_user') THEN
    CREATE ROLE trust_user LOGIN PASSWORD 'trust_pass';
    GRANT CONNECT ON DATABASE companydb TO trust_user;
    GRANT USAGE ON SCHEMA trust TO trust_user;
    GRANT SELECT, INSERT, UPDATE ON ALL TABLES IN SCHEMA trust TO trust_user;
    ALTER DEFAULT PRIVILEGES IN SCHEMA trust
      GRANT SELECT, INSERT, UPDATE ON TABLES TO trust_user;
  END IF;
END
$$;
