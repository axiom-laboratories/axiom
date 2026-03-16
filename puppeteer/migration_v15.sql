-- migration_v15.sql
-- Phase 2: Retry Policy — new columns on jobs and scheduled_jobs
-- Safe to run on existing Postgres deployments (IF NOT EXISTS guards)
-- Fresh installs: handled automatically by SQLAlchemy create_all at startup

-- NOTE: The IF NOT EXISTS syntax is Postgres-only. For local SQLite dev, 
-- the workflow is: delete jobs.db and let create_all rebuild it on next server start.

ALTER TABLE jobs ADD COLUMN IF NOT EXISTS max_retries INTEGER DEFAULT 0;
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS retry_count INTEGER DEFAULT 0;
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS retry_after TIMESTAMP;
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS backoff_multiplier FLOAT DEFAULT 2.0;
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS timeout_minutes INTEGER;

ALTER TABLE scheduled_jobs ADD COLUMN IF NOT EXISTS max_retries INTEGER DEFAULT 0;
ALTER TABLE scheduled_jobs ADD COLUMN IF NOT EXISTS backoff_multiplier FLOAT DEFAULT 2.0;
ALTER TABLE scheduled_jobs ADD COLUMN IF NOT EXISTS timeout_minutes INTEGER;

-- Seed global zombie timeout default if not already present
INSERT INTO config (key, value)
VALUES ('zombie_timeout_minutes', '30')
ON CONFLICT (key) DO NOTHING;
