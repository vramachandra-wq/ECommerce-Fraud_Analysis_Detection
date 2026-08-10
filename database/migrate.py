"""Apply numbered SQL migrations under database/migrations/.

Tracks applied files in master.schema_migrations so upgrades are idempotent.
CREATE IF NOT EXISTS / ADD COLUMN IF NOT EXISTS statements remain safe to re-run.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Iterable, List, Sequence, Tuple

logger = logging.getLogger(__name__)

MIGRATIONS_DIR = Path(__file__).resolve().parent / "migrations"

SCHEMA_MIGRATIONS_DDL = """
CREATE TABLE IF NOT EXISTS master.schema_migrations (
    filename   VARCHAR(255) PRIMARY KEY,
    applied_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
"""


def _list_migration_files(directory: Path = MIGRATIONS_DIR) -> List[Path]:
    if not directory.is_dir():
        return []
    return sorted(p for p in directory.glob("*.sql") if p.is_file())


def _applied_filenames(cur) -> set[str]:
    cur.execute(
        """
        SELECT filename FROM master.schema_migrations
        """
    )
    return {str(row[0]) for row in cur.fetchall()}


def apply_sql_migrations(
    cur,
    *,
    directory: Path = MIGRATIONS_DIR,
    filenames: Sequence[str] | None = None,
) -> Tuple[List[str], List[str]]:
    """
    Apply pending ``*.sql`` migrations in lexical order.

    Returns ``(applied, skipped)`` filename lists.
    """
    cur.execute("CREATE SCHEMA IF NOT EXISTS master")
    cur.execute(SCHEMA_MIGRATIONS_DDL)

    applied_before = _applied_filenames(cur)
    pending: Iterable[Path]
    if filenames is not None:
        pending = [directory / name for name in filenames]
    else:
        pending = _list_migration_files(directory)

    newly_applied: List[str] = []
    skipped: List[str] = []

    for path in pending:
        name = path.name
        if name in applied_before:
            skipped.append(name)
            continue
        if not path.is_file():
            raise FileNotFoundError(f"Migration file not found: {path}")
        sql = path.read_text(encoding="utf-8")
        logger.info("Applying database migration %s", name)
        cur.execute(sql)
        cur.execute(
            """
            INSERT INTO master.schema_migrations (filename)
            VALUES (%s)
            ON CONFLICT (filename) DO NOTHING
            """,
            (name,),
        )
        newly_applied.append(name)

    return newly_applied, skipped
