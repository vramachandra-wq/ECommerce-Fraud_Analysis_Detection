-- Analyst notification email for backlog / alert digests.
ALTER TABLE master.analyst_users
    ADD COLUMN IF NOT EXISTS email VARCHAR(255);

COMMENT ON COLUMN master.analyst_users.email IS
    'Notification email for backlog and alert digests (POC / ops use).';
