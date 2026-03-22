-- migration_v38: Add runtime column to scheduled_jobs and jobs for multi-runtime support (RT-07)
ALTER TABLE scheduled_jobs ADD COLUMN IF NOT EXISTS runtime VARCHAR DEFAULT 'python';
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS runtime VARCHAR;
