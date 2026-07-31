"""Schema helpers for master.system_audit_log (DB system audit trail)."""

from __future__ import annotations

SYSTEM_AUDIT_DDL = """
CREATE TABLE IF NOT EXISTS master.system_audit_log (
    audit_id       BIGSERIAL PRIMARY KEY,
    created_at     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    actor_type     VARCHAR(32)  NOT NULL DEFAULT 'system',
    actor_id       VARCHAR(128),
    actor_name     VARCHAR(255),
    action         VARCHAR(64)  NOT NULL,
    resource_type  VARCHAR(64),
    resource_id    VARCHAR(128),
    outcome        VARCHAR(32)  NOT NULL DEFAULT 'success',
    details        JSONB,
    ip_address     VARCHAR(64),
    request_path   VARCHAR(512)
);
"""

SYSTEM_AUDIT_INDEXES = [
    """
    CREATE INDEX IF NOT EXISTS idx_system_audit_created_at
        ON master.system_audit_log (created_at DESC)
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_system_audit_action
        ON master.system_audit_log (action)
    """,
]


def ensure_system_audit_table(cur) -> None:
    """Create master.system_audit_log if missing (safe to call repeatedly)."""
    cur.execute(SYSTEM_AUDIT_DDL)
    for stmt in SYSTEM_AUDIT_INDEXES:
        cur.execute(stmt)
