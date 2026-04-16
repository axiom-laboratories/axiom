-- Migration v55: Gate Node Support
-- Enables gate nodes (which have no associated job) to coexist with SCRIPT steps
-- Adds result_json column for IF gate condition evaluation

-- Make scheduled_job_id nullable to allow gate nodes without jobs
ALTER TABLE workflow_steps
ALTER COLUMN scheduled_job_id DROP NOT NULL;

-- Add result_json column to store step execution output for IF gate evaluation
ALTER TABLE workflow_step_runs
ADD COLUMN IF NOT EXISTS result_json TEXT;
