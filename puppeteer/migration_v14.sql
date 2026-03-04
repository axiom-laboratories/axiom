-- migration_v14.sql
-- Phase 1: Output Capture — add execution_records table
-- Safe to run on existing Postgres deployments (IF NOT EXISTS guards)
-- Fresh installs: handled automatically by SQLAlchemy create_all at startup

CREATE TABLE IF NOT EXISTS execution_records (
    id SERIAL PRIMARY KEY,
    job_guid VARCHAR NOT NULL,
    node_id VARCHAR,
    status VARCHAR NOT NULL,
    exit_code INTEGER,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    output_log TEXT,
    truncated BOOLEAN DEFAULT FALSE
);

CREATE INDEX IF NOT EXISTS ix_execution_records_job_guid
    ON execution_records (job_guid);
