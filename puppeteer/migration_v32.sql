-- migration_v32.sql: Phase 29 — Output capture + retry attempt linking columns
-- Safe to re-run (IF NOT EXISTS / nullable columns only)

ALTER TABLE execution_records ADD COLUMN IF NOT EXISTS stdout TEXT;
ALTER TABLE execution_records ADD COLUMN IF NOT EXISTS stderr TEXT;
ALTER TABLE execution_records ADD COLUMN IF NOT EXISTS script_hash VARCHAR(64);
ALTER TABLE execution_records ADD COLUMN IF NOT EXISTS hash_mismatch BOOLEAN DEFAULT FALSE;
ALTER TABLE execution_records ADD COLUMN IF NOT EXISTS attempt_number INTEGER;
ALTER TABLE execution_records ADD COLUMN IF NOT EXISTS job_run_id VARCHAR(36);

ALTER TABLE jobs ADD COLUMN IF NOT EXISTS job_run_id VARCHAR(36);
