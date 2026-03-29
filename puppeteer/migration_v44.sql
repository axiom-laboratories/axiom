-- Phase 90: Job Script Versioning
-- Creates job_definition_versions table and adds definition_version_id to jobs

CREATE TABLE IF NOT EXISTS job_definition_versions (
    id VARCHAR PRIMARY KEY,
    job_def_id VARCHAR NOT NULL REFERENCES scheduled_jobs(id) ON DELETE CASCADE,
    version_number INTEGER NOT NULL,
    script_content TEXT NOT NULL,
    signature_id VARCHAR REFERENCES signatures(id) ON DELETE SET NULL,
    signature_payload TEXT,
    cron_expression VARCHAR,
    target_tags TEXT,
    target_node_id VARCHAR,
    runtime VARCHAR(32),
    max_retries INTEGER DEFAULT 0,
    backoff_multiplier FLOAT DEFAULT 2.0,
    change_summary VARCHAR,
    is_signed BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW(),
    created_by VARCHAR,
    CONSTRAINT uq_jobdef_version UNIQUE (job_def_id, version_number)
);

ALTER TABLE jobs ADD COLUMN IF NOT EXISTS definition_version_id VARCHAR REFERENCES job_definition_versions(id) ON DELETE SET NULL;

CREATE INDEX IF NOT EXISTS ix_jobdefver_job_def_id ON job_definition_versions (job_def_id);
CREATE INDEX IF NOT EXISTS ix_jobs_definition_version_id ON jobs (definition_version_id);
