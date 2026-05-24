-- SDAI - Sistema Detección Alertas Intrusiones
-- Sprint 1-2: Esquema base Supabase (PostgreSQL)
-- Ejecutar en Supabase SQL Editor

-- Eventos crudos de red (todo paquete capturado relevante)
CREATE TABLE IF NOT EXISTS events (
  id          BIGSERIAL PRIMARY KEY,
  timestamp   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  src_ip      INET,
  dst_ip      INET,
  protocol    TEXT NOT NULL,
  src_port    INTEGER,
  dst_port    INTEGER,
  flags       TEXT,
  length      INTEGER,
  raw_data    JSONB
);

CREATE INDEX IF NOT EXISTS idx_events_timestamp ON events (timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_events_src_ip    ON events (src_ip);

-- Alertas generadas por motor detección (Sprint 3-4 las llenará)
CREATE TABLE IF NOT EXISTS alerts (
  id           BIGSERIAL PRIMARY KEY,
  event_id     BIGINT REFERENCES events(id) ON DELETE CASCADE,
  threat_type  TEXT NOT NULL,        -- port_scan | brute_force | malicious_ip | dos
  severity     TEXT NOT NULL CHECK (severity IN ('baja','media','alta')),
  description  TEXT,
  notified     BOOLEAN NOT NULL DEFAULT FALSE,
  created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  country      TEXT,
  city         TEXT,
  latitude     DOUBLE PRECISION,
  longitude    DOUBLE PRECISION
);

CREATE INDEX IF NOT EXISTS idx_alerts_country   ON alerts (country);

CREATE INDEX IF NOT EXISTS idx_alerts_created  ON alerts (created_at DESC);
CREATE INDEX IF NOT EXISTS idx_alerts_severity ON alerts (severity);

-- Configuración runtime (umbrales, flags, blacklists)
CREATE TABLE IF NOT EXISTS configurations (
  key         TEXT PRIMARY KEY,
  value       JSONB NOT NULL,
  updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Seed config inicial
INSERT INTO configurations (key, value) VALUES
  ('port_scan_threshold',  '{"ports_per_minute": 20}'::jsonb),
  ('brute_force_threshold','{"failed_attempts": 5, "window_seconds": 60}'::jsonb),
  ('dos_threshold',        '{"packets_per_second": 500}'::jsonb),
  ('blacklist_ips',        '[]'::jsonb)
ON CONFLICT (key) DO NOTHING;

-- ============================================================
-- Sprint 7-8: Usuarios analistas (sesión por cookie HMAC firmada)
-- Contraseñas guardadas con bcrypt ($2b$...). Nunca en texto plano.
-- ============================================================
CREATE TABLE IF NOT EXISTS users (
  id              BIGSERIAL PRIMARY KEY,
  username        TEXT UNIQUE NOT NULL,
  password_hash   TEXT NOT NULL,
  role            TEXT NOT NULL DEFAULT 'admin' CHECK (role IN ('admin','viewer')),
  active          BOOLEAN NOT NULL DEFAULT TRUE,
  created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  last_login_at   TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_users_username ON users (username);

ALTER TABLE users ENABLE ROW LEVEL SECURITY;
-- Login flow runs server-side with service role, so no anon policies are exposed.

-- ============================================================
-- Row Level Security
-- Production posture: only the service_role key (used by the FastAPI backend)
-- can read/write. The anon key — typically exposed to browsers — gets nothing.
-- For dev convenience the legacy anon policies are dropped explicitly so
-- re-running this script on an old DB tightens it instead of staying permissive.
-- ============================================================

ALTER TABLE events          ENABLE ROW LEVEL SECURITY;
ALTER TABLE alerts          ENABLE ROW LEVEL SECURITY;
ALTER TABLE configurations  ENABLE ROW LEVEL SECURITY;

-- Drop any pre-existing permissive anon policies (idempotent migration)
DROP POLICY IF EXISTS "anon_read_events"    ON events;
DROP POLICY IF EXISTS "anon_write_events"   ON events;
DROP POLICY IF EXISTS "anon_read_alerts"    ON alerts;
DROP POLICY IF EXISTS "anon_write_alerts"   ON alerts;
DROP POLICY IF EXISTS "anon_update_alerts"  ON alerts;
DROP POLICY IF EXISTS "anon_read_configs"   ON configurations;
DROP POLICY IF EXISTS "anon_write_configs"  ON configurations;
DROP POLICY IF EXISTS "anon_update_configs" ON configurations;

-- events: only service_role (backend) reads + inserts
DROP POLICY IF EXISTS "svc_all_events" ON events;
CREATE POLICY "svc_all_events" ON events
  FOR ALL TO service_role USING (true) WITH CHECK (true);

-- alerts: only service_role
DROP POLICY IF EXISTS "svc_all_alerts" ON alerts;
CREATE POLICY "svc_all_alerts" ON alerts
  FOR ALL TO service_role USING (true) WITH CHECK (true);

-- configurations: only service_role
DROP POLICY IF EXISTS "svc_all_configs" ON configurations;
CREATE POLICY "svc_all_configs" ON configurations
  FOR ALL TO service_role USING (true) WITH CHECK (true);

-- users: only service_role (passwords never leave the server)
DROP POLICY IF EXISTS "svc_all_users" ON users;
CREATE POLICY "svc_all_users" ON users
  FOR ALL TO service_role USING (true) WITH CHECK (true);

-- ============================================================
-- Dev-mode override (OPTIONAL):
--   If you must use the anon key locally (no service_role configured), uncomment
--   the block below. NEVER leave this enabled in production — it makes the API
--   key shipped to the browser able to read all alerts/events.
--
-- CREATE POLICY "anon_dev_events"  ON events          FOR ALL TO anon USING (true) WITH CHECK (true);
-- CREATE POLICY "anon_dev_alerts"  ON alerts          FOR ALL TO anon USING (true) WITH CHECK (true);
-- CREATE POLICY "anon_dev_configs" ON configurations  FOR ALL TO anon USING (true) WITH CHECK (true);
-- ============================================================
