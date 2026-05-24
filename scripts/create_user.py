"""Bootstrap analyst user generator for SDAI.

Generates a bcrypt password hash + ready-to-paste SQL for the Supabase `users`
table. Optionally inserts the row directly via the configured Supabase client.

Usage examples:
    python scripts/create_user.py                       # interactive prompts
    python scripts/create_user.py analista1             # ask password
    python scripts/create_user.py analista1 --role viewer
    python scripts/create_user.py analista1 --insert    # insert + print SQL

The script never logs the plaintext password.
"""
from __future__ import annotations

import argparse
import getpass
import sys
from pathlib import Path

# Make `app.*` importable when run from project root.
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "backend"))

from app.routers.auth import hash_password  # noqa: E402
from app.db.supabase_client import get_client, execute_with_retry  # noqa: E402


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Create or refresh an SDAI analyst user")
    p.add_argument("username", nargs="?", help="Username for the new analyst (prompted if omitted)")
    p.add_argument("--role", choices=("admin", "viewer"), default="admin",
                   help="Role to assign (default: admin)")
    p.add_argument("--insert", action="store_true",
                   help="Also INSERT the row into Supabase using the configured SUPABASE_KEY")
    return p.parse_args()


def main() -> int:
    args = parse_args()
    username = (args.username or input("Username: ")).strip()
    if not username:
        print("ERROR: username is required", file=sys.stderr)
        return 2

    password = getpass.getpass("Password: ")
    confirm = getpass.getpass("Confirm : ")
    if password != confirm:
        print("ERROR: passwords do not match", file=sys.stderr)
        return 2
    if len(password) < 12:
        print("WARNING: password shorter than 12 chars — consider a stronger value.", file=sys.stderr)

    pw_hash = hash_password(password)
    sql = (
        "INSERT INTO users (username, password_hash, role) VALUES (\n"
        f"  '{username}',\n"
        f"  '{pw_hash}',\n"
        f"  '{args.role}'\n"
        ")\n"
        "ON CONFLICT (username) DO UPDATE\n"
        "  SET password_hash = EXCLUDED.password_hash,\n"
        "      role          = EXCLUDED.role,\n"
        "      active        = TRUE;\n"
    )

    print("\n--- Paste in Supabase SQL Editor ---")
    print(sql)
    print("------------------------------------")

    if args.insert:
        client = get_client()
        if client is None:
            print("Supabase client not configured (.env missing SUPABASE_URL/SUPABASE_KEY).",
                  file=sys.stderr)
            return 1
        try:
            execute_with_retry(
                lambda c: c.table("users").upsert({
                    "username": username,
                    "password_hash": pw_hash,
                    "role": args.role,
                    "active": True,
                }, on_conflict="username")
            )
            print(f"User '{username}' upserted into Supabase ({args.role}).")
        except Exception as e:
            print(f"Supabase insert failed: {e}", file=sys.stderr)
            return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
