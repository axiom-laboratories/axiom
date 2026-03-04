-- Migration v13: Add updated_at to scheduled_jobs
ALTER TABLE scheduled_jobs ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP;
