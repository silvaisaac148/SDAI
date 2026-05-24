-- ============================================================
-- SDAI · Migración Sprint 8 (pre-producción)
-- Idempotente: puedes correrla varias veces sin romper datos existentes.
-- Pegar en: Supabase Dashboard → SQL Editor → New query → Run.
--
-- Esta migración hace tres cosas:
--   1. Crea la tabla `users` (analistas con bcrypt password_hash + role).
--   2. Endurece las RLS policies: solo el service_role (backend FastAPI) accede.
--   3. (Opcional) Deja preparado el bloque dev_anon para entornos locales.
-- ============================================================

-- --------------------------------------------------------
-- 1) Tabla users (analistas SOC con bcrypt)
-- --------------------------------------------------------
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

-- --------------------------------------------------------
-- 2) Endurecer RLS — borrar policies anon permisivas previas
-- --------------------------------------------------------
DROP POLICY IF EXISTS "anon_read_events"    ON events;
DROP POLICY IF EXISTS "anon_write_events"   ON events;
DROP POLICY IF EXISTS "anon_read_alerts"    ON alerts;
DROP POLICY IF EXISTS "anon_write_alerts"   ON alerts;
DROP POLICY IF EXISTS "anon_update_alerts"  ON alerts;
DROP POLICY IF EXISTS "anon_read_configs"   ON configurations;
DROP POLICY IF EXISTS "anon_write_configs"  ON configurations;
DROP POLICY IF EXISTS "anon_update_configs" ON configurations;

-- --------------------------------------------------------
-- 3) Policies productivas: solo service_role (backend)
-- --------------------------------------------------------
DROP POLICY IF EXISTS "svc_all_events"  ON events;
CREATE POLICY "svc_all_events"  ON events          FOR ALL TO service_role USING (true) WITH CHECK (true);

DROP POLICY IF EXISTS "svc_all_alerts"  ON alerts;
CREATE POLICY "svc_all_alerts"  ON alerts          FOR ALL TO service_role USING (true) WITH CHECK (true);

DROP POLICY IF EXISTS "svc_all_configs" ON configurations;
CREATE POLICY "svc_all_configs" ON configurations  FOR ALL TO service_role USING (true) WITH CHECK (true);

DROP POLICY IF EXISTS "svc_all_users"   ON users;
CREATE POLICY "svc_all_users"   ON users           FOR ALL TO service_role USING (true) WITH CHECK (true);

-- --------------------------------------------------------
-- 4) (OPCIONAL · DEV ONLY) Volver a abrir el acceso anon
--    Descomenta este bloque solo si tu .env usa SUPABASE_KEY=<anon_key> y
--    NO tienes la service_role key configurada todavía. Vuelve a comentarlo
--    antes de exponer el sistema fuera de localhost.
-- --------------------------------------------------------
-- DROP POLICY IF EXISTS "anon_dev_events"  ON events;
-- DROP POLICY IF EXISTS "anon_dev_alerts"  ON alerts;
-- DROP POLICY IF EXISTS "anon_dev_configs" ON configurations;
-- CREATE POLICY "anon_dev_events"  ON events         FOR ALL TO anon USING (true) WITH CHECK (true);
-- CREATE POLICY "anon_dev_alerts"  ON alerts         FOR ALL TO anon USING (true) WITH CHECK (true);
-- CREATE POLICY "anon_dev_configs" ON configurations FOR ALL TO anon USING (true) WITH CHECK (true);

-- --------------------------------------------------------
-- 5) Verificación rápida
-- --------------------------------------------------------
-- SELECT tablename, policyname, roles FROM pg_policies
--   WHERE schemaname = 'public' ORDER BY tablename, policyname;
