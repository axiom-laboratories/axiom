-- migration_v16.sql
-- Phase 3: Execution History — indices and retention config
-- Safe to run on existing Postgres deployments (IF NOT EXISTS guards)

CREATE INDEX IF NOT EXISTS ix_execution_records_started_at 
    ON execution_records (started_at DESC);

CREATE INDEX IF NOT EXISTS ix_execution_records_node_started 
    ON execution_records (node_id, started_at DESC);

CREATE INDEX IF NOT EXISTS ix_execution_records_job_started 
    ON execution_records (job_guid, started_at DESC);

-- Seed history retention default (30 days)
INSERT INTO config (key, value)
VALUES ('history_retention_days', '30')
ON CONFLICT (key) DO NOTHING;
