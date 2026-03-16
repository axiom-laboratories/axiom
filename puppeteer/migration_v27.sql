-- migration_v27.sql: Job lifecycle status + push attribution
-- Adds status (DRAFT/ACTIVE/DEPRECATED/REVOKED) and pushed_by to scheduled_jobs.
-- Backfills existing rows to ACTIVE — they were created via dashboard and are live jobs.
-- Safe for existing deployments; new deployments handled by create_all.

ALTER TABLE scheduled_jobs ADD COLUMN IF NOT EXISTS status VARCHAR DEFAULT 'ACTIVE';
ALTER TABLE scheduled_jobs ADD COLUMN IF NOT EXISTS pushed_by VARCHAR NULL;

-- Backfill: existing dashboard-created jobs are live, not drafts
UPDATE scheduled_jobs SET status = 'ACTIVE' WHERE status IS NULL;

-- Index for dispatch query performance (scheduler reads status frequently)
CREATE INDEX IF NOT EXISTS ix_scheduled_jobs_status ON scheduled_jobs(status);
