-- Migration v50: Add resource limit columns to nodes and scheduled_jobs tables
-- For existing Postgres deployments only (fresh deployments use create_all in db.py)

-- Add memory and CPU limit columns to nodes table (Phase 121-02)
ALTER TABLE nodes ADD COLUMN IF NOT EXISTS job_memory_limit VARCHAR(255);
ALTER TABLE nodes ADD COLUMN IF NOT EXISTS job_cpu_limit VARCHAR(255);

-- Add memory and CPU limit columns to scheduled_jobs table (Phase 121-02)
ALTER TABLE scheduled_jobs ADD COLUMN IF NOT EXISTS memory_limit VARCHAR(255);
ALTER TABLE scheduled_jobs ADD COLUMN IF NOT EXISTS cpu_limit VARCHAR(255);
