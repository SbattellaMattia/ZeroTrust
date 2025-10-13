-- ./postgres/init/init.sql
-- Schema Zero Trust
CREATE SCHEMA IF NOT EXISTS trust;

-- ========================================
-- 1. USERS - Profili utente
-- ========================================
CREATE TABLE IF NOT EXISTS trust.users (
    user_id SERIAL PRIMARY KEY,
    username VARCHAR(255) UNIQUE NOT NULL,
    initial_score INTEGER NOT NULL DEFAULT 80,
    current_score INTEGER NOT NULL DEFAULT 80,  -- snapshot opzionale
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_users_username ON trust.users(username);

-- ========================================
-- 2. EVENT_TYPES - Catalogo eventi
-- ========================================
CREATE TABLE IF NOT EXISTS trust.event_types (
    event_type VARCHAR(50) PRIMARY KEY,
    impact INTEGER NOT NULL,
    description TEXT,
    severity VARCHAR(20) CHECK (severity IN ('low', 'medium', 'high', 'critical'))
);

-- ========================================
-- 3. EVENTS - Log eventi (append-only)
-- ========================================
CREATE TABLE IF NOT EXISTS trust.events (
    event_id BIGSERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES trust.users(user_id) ON DELETE CASCADE,
    event_type VARCHAR(50) NOT NULL REFERENCES trust.event_types(event_type),
    impact INTEGER NOT NULL,        -- snapshot impact al momento evento
    occurred_at TIMESTAMP NOT NULL DEFAULT NOW(),
    source_ip INET,                 -- IP sorgente
    user_agent TEXT,                -- Browser/client
    metadata JSONB                  -- Dati extra opzionali
);

CREATE INDEX IF NOT EXISTS idx_events_user_time ON trust.events(user_id, occurred_at DESC);
CREATE INDEX IF NOT EXISTS idx_events_type ON trust.events(event_type);
CREATE INDEX IF NOT EXISTS idx_events_occurred ON trust.events(occurred_at DESC);

-- ========================================
-- 4. SCORE_SNAPSHOTS - Storico (opzionale)
-- ========================================
CREATE TABLE IF NOT EXISTS trust.score_snapshots (
    snapshot_id BIGSERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES trust.users(user_id) ON DELETE CASCADE,
    score INTEGER NOT NULL,
    snapshot_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_snapshots_user_time ON trust.score_snapshots(user_id, snapshot_at DESC);

-- ========================================
-- POPOLAMENTO DATI
-- ========================================

-- Event types con severity
INSERT INTO trust.event_types (event_type, impact, description, severity) VALUES
    ('login_success', 2, 'Login riuscito in orario lavorativo', 'low'),
    ('login_fail', -10, 'Tre login falliti consecutivi', 'medium'),
    ('login_off_hours', -10, 'Login fuori orario lavorativo', 'medium'),
    ('suspicious_ip', -15, 'Accesso da IP sospetto', 'high'),
    ('mfa_enabled', 10, 'MFA attivato', 'low'),
    ('password_change', 5, 'Password cambiata', 'low'),
    ('brute_force_detected', -30, 'Account bloccato per troppi tentativi', 'critical'),
    ('session_hijack_detected', -50, 'Possibile session hijacking', 'critical')
ON CONFLICT (event_type) DO NOTHING;

-- Utenti demo
INSERT INTO trust.users (username, initial_score, current_score) VALUES
  ('admin', 100, 100),
  ('mrossi', 80, 80),
  ('lbianchi', 60, 60),
  ('mrhacker', 10, 10)
ON CONFLICT (username) DO NOTHING;

-- ========================================
-- PERMESSI UTENTE DB
-- ========================================
DO
$$
DECLARE
  r RECORD;
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'trust_user') THEN
    CREATE ROLE trust_user LOGIN PASSWORD 'trust_pass';

    -- Permessi connessione e schema
    GRANT CONNECT ON DATABASE companydb TO trust_user;
    GRANT USAGE ON SCHEMA trust TO trust_user;

    -- Permessi su tabelle esistenti
    GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA trust TO trust_user;
    
    -- Permessi su tabelle future
    ALTER DEFAULT PRIVILEGES IN SCHEMA trust
      GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO trust_user;

    -- Permessi sequences (per SERIAL/BIGSERIAL)
    GRANT USAGE, SELECT, UPDATE ON ALL SEQUENCES IN SCHEMA trust TO trust_user;
    ALTER DEFAULT PRIVILEGES IN SCHEMA trust
      GRANT USAGE, SELECT, UPDATE ON SEQUENCES TO trust_user;

  END IF;
END
$$;
