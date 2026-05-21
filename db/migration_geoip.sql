-- ============================================================
-- MIGRACIÓN DE GEOLOCALIZACIÓN (GeoIP) - SDAI
-- ============================================================
-- Ejecuta este script en el SQL Editor de tu Dashboard de Supabase
-- para añadir las columnas geográficas a la tabla 'alerts'.
-- ============================================================

-- Añadir columnas para almacenar información de geolocalización
ALTER TABLE alerts ADD COLUMN IF NOT EXISTS country TEXT;
ALTER TABLE alerts ADD COLUMN IF NOT EXISTS city TEXT;
ALTER TABLE alerts ADD COLUMN IF NOT EXISTS latitude DOUBLE PRECISION;
ALTER TABLE alerts ADD COLUMN IF NOT EXISTS longitude DOUBLE PRECISION;

-- Crear un índice para optimizar búsquedas por país (útil para analíticas)
CREATE INDEX IF NOT EXISTS idx_alerts_country ON alerts (country);

COMMENT ON COLUMN alerts.country IS 'Nombre del país de procedencia de la dirección IP atacante';
COMMENT ON COLUMN alerts.city IS 'Nombre de la ciudad de procedencia de la dirección IP atacante';
COMMENT ON COLUMN alerts.latitude IS 'Coordenada de latitud de la ubicación del atacante';
COMMENT ON COLUMN alerts.longitude IS 'Coordenada de longitud de la ubicación del atacante';
