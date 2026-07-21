-- Migration 002: add dedicated delay_minutes column to master.rule_master.
-- Decouples hold-delay from time_interval_value/unit (which remains purely
-- the velocity/lookback window for R002-R010). Idempotent, safe to re-run.

ALTER TABLE master.rule_master
    ADD COLUMN IF NOT EXISTS delay_minutes INT DEFAULT 60;

UPDATE master.rule_master
SET delay_minutes = 180
WHERE rule_id = 'R001';

UPDATE master.rule_master
SET delay_minutes = 60
WHERE rule_id <> 'R001';
