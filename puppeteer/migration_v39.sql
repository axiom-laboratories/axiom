-- migration_v39.sql — Phase 49: Job name + created_by columns + pagination indexes
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS name VARCHAR;
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS created_by VARCHAR;

CREATE INDEX IF NOT EXISTS ix_jobs_name ON jobs(name);
CREATE INDEX IF NOT EXISTS ix_jobs_created_by ON jobs(created_by);
CREATE INDEX IF NOT EXISTS ix_jobs_created_at_guid ON jobs(created_at DESC, guid DESC);
