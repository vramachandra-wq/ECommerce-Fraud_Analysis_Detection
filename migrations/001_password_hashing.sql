-- Run once on existing databases before deploying password-hash auth code.
-- Safe to re-run: widening VARCHAR is idempotent.

ALTER TABLE master.customers
    ALTER COLUMN password TYPE VARCHAR(255);
