-- Phase 91: Output Validation
-- Run against existing PostgreSQL deployments (fresh installs handled by create_all)

ALTER TABLE scheduled_jobs ADD COLUMN IF NOT EXISTS validation_rules TEXT;
ALTER TABLE execution_records ADD COLUMN IF NOT EXISTS failure_reason VARCHAR(64);
