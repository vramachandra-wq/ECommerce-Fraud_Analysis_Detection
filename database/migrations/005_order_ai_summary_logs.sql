-- Append-only lifecycle log for AI / heuristic order-review summaries.
CREATE TABLE IF NOT EXISTS master.order_ai_summary_logs (
    log_id         BIGSERIAL PRIMARY KEY,
    created_at     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    order_id       VARCHAR(20),
    event          VARCHAR(64)  NOT NULL,
    level          VARCHAR(16)  NOT NULL DEFAULT 'INFO',
    message        TEXT         NOT NULL,
    source         VARCHAR(30),
    model_name     VARCHAR(100),
    input_tokens   INTEGER,
    output_tokens  INTEGER,
    details        JSONB
);

CREATE INDEX IF NOT EXISTS idx_order_ai_summary_logs_created_at
    ON master.order_ai_summary_logs (created_at DESC);

CREATE INDEX IF NOT EXISTS idx_order_ai_summary_logs_order_id
    ON master.order_ai_summary_logs (order_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_order_ai_summary_logs_event
    ON master.order_ai_summary_logs (event);
