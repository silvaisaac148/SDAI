"""Verify Supabase schema: required tables + GeoIP columns + seed configs.

Usage:
    python scripts/verify_schema.py
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.append(str(ROOT))
sys.path.append(str(ROOT / "backend"))

from app.db.supabase_client import get_client, execute_with_retry

REQUIRED_TABLES = ("events", "alerts", "configurations")
REQUIRED_ALERT_COLS = ("country", "city", "latitude", "longitude")
REQUIRED_CONFIG_KEYS = (
    "port_scan_threshold",
    "brute_force_threshold",
    "dos_threshold",
    "blacklist_ips",
)

SCHEMA_PATH = ROOT / "db" / "schema.sql"
MIGRATION_PATH = ROOT / "db" / "migration_geoip.sql"


def check_table(table: str) -> tuple[bool, str]:
    try:
        execute_with_retry(lambda c: c.table(table).select("*").limit(1))
        return True, "OK"
    except Exception as e:
        return False, str(e)


def check_alert_geo_columns() -> tuple[bool, str]:
    try:
        execute_with_retry(lambda c: c.table("alerts").select(",".join(REQUIRED_ALERT_COLS)).limit(1))
        return True, "OK"
    except Exception as e:
        return False, str(e)


def check_configurations() -> tuple[bool, list[str]]:
    try:
        res = execute_with_retry(lambda c: c.table("configurations").select("key"))
        existing = {r["key"] for r in (res.data or [])}
        missing = [k for k in REQUIRED_CONFIG_KEYS if k not in existing]
        return len(missing) == 0, missing
    except Exception as e:
        return False, [str(e)]


def main() -> int:
    client = get_client()
    if client is None:
        print("[X] Supabase client not available. Verifica .env (SUPABASE_URL, SUPABASE_KEY).")
        return 2

    ok = True
    print(f"Verificando schema en Supabase...\n")

    print("Tablas requeridas:")
    for t in REQUIRED_TABLES:
        passed, msg = check_table(t)
        print(f"  - {t:<16} {'OK' if passed else 'FALTA'}  {msg if not passed else ''}")
        if not passed:
            ok = False

    print("\nColumnas GeoIP en alerts:")
    passed, msg = check_alert_geo_columns()
    print(f"  - {','.join(REQUIRED_ALERT_COLS)}: {'OK' if passed else 'FALTAN'}")
    if not passed:
        print(f"    Detalle: {msg}")
        print(f"    Aplicar SQL en Supabase: {MIGRATION_PATH}")
        ok = False

    print("\nSeed de configurations:")
    passed, missing = check_configurations()
    if passed:
        print(f"  - 4/4 keys presentes")
    else:
        print(f"  - FALTAN: {missing}")
        ok = False

    print("\n" + ("[OK] Schema verificado correctamente." if ok else "[!] Hay diferencias — aplica los SQL faltantes en el SQL Editor de Supabase."))
    if not ok:
        print(f"\nSchema base:     {SCHEMA_PATH}")
        print(f"Migración GeoIP: {MIGRATION_PATH}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
