-- Multi-item order support + per-line rule outcomes
CREATE TABLE IF NOT EXISTS master.order_items (
    order_item_id BIGSERIAL PRIMARY KEY,
    order_id      VARCHAR(20)  NOT NULL,
    line_no       INTEGER      NOT NULL,
    product_id    VARCHAR(64)  NOT NULL,
    product_name  VARCHAR(255) NOT NULL,
    category      VARCHAR(128),
    quantity      INTEGER      NOT NULL CHECK (quantity >= 1),
    unit_price    NUMERIC(12, 2) NOT NULL,
    line_amount   NUMERIC(12, 2) NOT NULL,
    line_status   VARCHAR(32),
    flagged_reason TEXT,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_order_items_order_id
    ON master.order_items (order_id);

ALTER TABLE master.order_items ADD COLUMN IF NOT EXISTS line_status VARCHAR(32);
ALTER TABLE master.order_items ADD COLUMN IF NOT EXISTS flagged_reason TEXT;
