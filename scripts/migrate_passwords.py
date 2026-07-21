#!/usr/bin/env python3
"""
One-time password migration: widen customer password column and hash plain-text passwords.

Usage (from project root, with .venv active and DB running):
    python scripts/migrate_passwords.py

Existing demo passwords (password123, admin123, secure123, etc.) keep working after migration.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import psycopg2

from auth.passwords import hash_password, is_hashed
from config import DB_CONFIG

MIGRATION_SQL = ROOT / "migrations" / "001_password_hashing.sql"


def _migrate_table(cur, table: str, id_column: str) -> int:
    cur.execute(f"SELECT {id_column}, password FROM {table}")
    rows = cur.fetchall()
    updated = 0
    for row_id, stored in rows:
        if not stored or is_hashed(stored):
            continue
        cur.execute(
            f"UPDATE {table} SET password = %s WHERE {id_column} = %s",
            (hash_password(stored), row_id),
        )
        updated += 1
    return updated


def main() -> None:
    print("==> Password migration starting...")
    sql = MIGRATION_SQL.read_text(encoding="utf-8")

    with psycopg2.connect(**DB_CONFIG) as conn:
        with conn.cursor() as cur:
            cur.execute(sql)
            customers = _migrate_table(cur, "master.customers", "user_id")
            analysts = _migrate_table(cur, "master.analyst_users", "analyst_id")
        conn.commit()

    print(f"    Column migration applied from {MIGRATION_SQL.name}")
    print(f"    Hashed {customers} customer password(s)")
    print(f"    Hashed {analysts} analyst password(s)")
    print("==> Done. Restart app services and test login.")


if __name__ == "__main__":
    main()
