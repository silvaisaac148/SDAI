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
-- Row Level Security policies (Sprint 1-2: dev mode permisivo)
-- En producción restringir con auth.uid() / service_role
-- ============================================================

ALTER TABLE events          ENABLE ROW LEVEL SECURITY;
ALTER TABLE alerts          ENABLE ROW LEVEL SECURITY;
ALTER TABLE configurations  ENABLE ROW LEVEL SECURITY;

-- events: anon puede leer + insertar (sniffer registra)
DROP POLICY IF EXISTS "anon_read_events"   ON events;
DROP POLICY IF EXISTS "anon_write_events"  ON events;
CREATE POLICY "anon_read_events"  ON events  FOR SELECT TO anon USING (true);
CREATE POLICY "anon_write_events" ON events  FOR INSERT TO anon WITH CHECK (true);

-- alerts: anon puede leer + insertar + actualizar (notified flag)
DROP POLICY IF EXISTS "anon_read_alerts"   ON alerts;
DROP POLICY IF EXISTS "anon_write_alerts"  ON alerts;
DROP POLICY IF EXISTS "anon_update_alerts" ON alerts;
CREATE POLICY "anon_read_alerts"   ON alerts FOR SELECT TO anon USING (true);
CREATE POLICY "anon_write_alerts"  ON alerts FOR INSERT TO anon WITH CHECK (true);
CREATE POLICY "anon_update_alerts" ON alerts FOR UPDATE TO anon USING (true);

-- configurations: anon lee + upsert
DROP POLICY IF EXISTS "anon_read_configs"  ON configurations;
DROP POLICY IF EXISTS "anon_write_configs" ON configurations;
DROP POLICY IF EXISTS "anon_update_configs" ON configurations;
CREATE POLICY "anon_read_configs"   ON configurations FOR SELECT TO anon USING (true);
CREATE POLICY "anon_write_configs"  ON configurations FOR INSERT TO anon WITH CHECK (true);
CREATE POLICY "anon_update_configs" ON configurations FOR UPDATE TO anon USING (true);
