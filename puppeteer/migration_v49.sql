-- Migration v49: Add memory_limit and cpu_limit columns to jobs table
-- For existing Postgres deployments only (fresh deployments use create_all in db.py)

ALTER TABLE jobs ADD COLUMN IF NOT EXISTS memory_limit VARCHAR(255);
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS cpu_limit VARCHAR(255);
