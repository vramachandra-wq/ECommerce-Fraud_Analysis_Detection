-- System-wide audit trail (logins, orders, rules, blacklists, permissions, …)
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

CREATE INDEX IF NOT EXISTS idx_system_audit_created_at
    ON master.system_audit_log (created_at DESC);

CREATE INDEX IF NOT EXISTS idx_system_audit_action
    ON master.system_audit_log (action);
