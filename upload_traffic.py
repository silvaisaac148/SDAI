"""Insert traffic.jsonl packets into Supabase events table, then show them."""

import json
import sys
from pathlib import Path
from dotenv import load_dotenv
import os

ROOT = Path(__file__).parent
load_dotenv(ROOT / ".env")

SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "")

if not SUPABASE_URL or not SUPABASE_KEY:
    print("ERROR: SUPABASE_URL / SUPABASE_KEY no encontrados en .env")
    sys.exit(1)

from supabase import create_client
client = create_client(SUPABASE_URL, SUPABASE_KEY)

JSONL = ROOT / "traffic.jsonl"
with open(JSONL, encoding="utf-8") as f:
    packets = [json.loads(l) for l in f if l.strip()]

print("\n" + "=" * 65)
print("  SDAI -- INSERT eventos en Supabase  (%d paquetes)" % len(packets))
print("=" * 65)

rows = []
for p in packets:
    rows.append({
        "timestamp": p["timestamp"],
        "src_ip":    p["src_ip"],
        "dst_ip":    p["dst_ip"],
        "protocol":  p["protocol"],
        "src_port":  p["src_port"],
        "dst_port":  p["dst_port"],
        "flags":     p["flags"],
        "length":    p["length"],
        "raw_data":  p,
    })

# Batch insert
resp = client.table("events").insert(rows).execute()
inserted = len(resp.data) if resp.data else 0
print("  Insertados: %d filas" % inserted)

# Fetch back last 60 events
print("\n-- ULTIMOS 60 EVENTOS EN SUPABASE ------------------------------")
result = client.table("events").select(
    "id,timestamp,src_ip,dst_ip,protocol,src_port,dst_port,length"
).order("timestamp", desc=True).limit(60).execute()

rows_fetched = result.data or []
print("  %-6s  %-25s  %-8s  %-18s  %-18s  %s" % (
    "ID", "TIMESTAMP", "PROTO", "SRC", "DST", "LEN"
))
print("  " + "-" * 90)
for r in rows_fetched:
    src = "%s:%s" % (r["src_ip"], r["src_port"] or "-")
    dst = "%s:%s" % (r["dst_ip"], r["dst_port"] or "-")
    ts  = r["timestamp"][:19].replace("T", " ")
    print("  %-6s  %-25s  %-8s  %-22s  %-22s  %s" % (
        r["id"], ts, r["protocol"], src, dst, r["length"]
    ))

print()
print("  Total en tabla: %d" % len(rows_fetched))
print("=" * 65)
print()
