-- Migration 001: default ON_HOLD delay = 60 minutes; P2 iPhone rule (R001) = 180 minutes.
-- Idempotent, safe to re-run.

UPDATE master.rule_master
SET time_interval_value = 180,
    time_interval_unit   = 'MINUTE'
WHERE rule_id = 'R001';

UPDATE master.rule_master
SET time_interval_value = 60,
    time_interval_unit   = 'MINUTE'
WHERE UPPER(action) = 'HOLD'
  AND rule_id <> 'R001';
