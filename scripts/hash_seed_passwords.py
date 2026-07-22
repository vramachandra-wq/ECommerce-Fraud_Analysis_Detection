"""
Hash any remaining plain-text passwords in the live database with bcrypt.

Also rewrites seed passwords in schema.sql when demo plain-text values are present.

Usage (from project root, with DB running):
    .\\.venv\\Scripts\\python.exe scripts\\hash_seed_passwords.py
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from auth.passwords import hash_password, is_hashed  # noqa: E402
from config import DB_CONFIG  # noqa: E402

# Fixed bcrypt hashes for demo passwords (verified with bcrypt.checkpw).
SEED_HASHES = {
    "password123": "$2b$12$xdvpMwOvkSNbx52B6ivkWOF/VFF05ypX7.soxzfqc7yNi4kq0M2Iu",
    "admin123": "$2b$12$Q.arocV656a25pUqXLUgaOD6eK5qyHolrmRo5wYVoRiR.Bykxx7P2",
    "secure123": "$2b$12$CWwcbw1UZs91FV7G0XuecO9m8yipGkHQ6POmHRXIGx5e5cXN91Lr.",
}


def update_schema_sql() -> None:
    schema = ROOT / "init_scripts" / "ecommerce_fraud" / "schema.sql"
    text = schema.read_text(encoding="utf-8")
    counts = {}
    for plain, hashed in SEED_HASHES.items():
        needle = f"'{plain}'"
        counts[plain] = text.count(needle)
        if counts[plain]:
            text = text.replace(needle, f"'{hashed}'")
    if any(counts.values()):
        schema.write_text(text, encoding="utf-8")
    print("schema.sql plaintext replacements:", counts)


def _hash_table(cur, table: str, id_column: str) -> int:
    cur.execute(f"SELECT {id_column}, password FROM {table}")
    updated = 0
    for row_id, stored in cur.fetchall():
        if not stored or is_hashed(stored):
            continue
        new_hash = SEED_HASHES.get(stored, hash_password(stored))
        cur.execute(
            f"UPDATE {table} SET password = %s WHERE {id_column} = %s",
            (new_hash, row_id),
        )
        updated += 1
    return updated


def update_live_database() -> None:
    import psycopg2

    with psycopg2.connect(**DB_CONFIG) as conn:
        with conn.cursor() as cur:
            customers = _hash_table(cur, "master.customers", "user_id")
            analysts = _hash_table(cur, "master.analyst_users", "analyst_id")
        conn.commit()
    print(f"Live DB hashed: {customers} customer(s), {analysts} analyst(s)")


if __name__ == "__main__":
    update_schema_sql()
    try:
        update_live_database()
    except Exception as exc:  # noqa: BLE001
        print(f"Live DB update skipped/failed: {exc}")
        sys.exit(1)
