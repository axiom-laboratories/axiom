-- Phase 147: WorkflowRun Execution Engine
-- Adds WorkflowStepRun table, workflow_step_run_id FK to Job table, and depth column to Job

-- Create workflow_step_runs table
CREATE TABLE IF NOT EXISTS workflow_step_runs (
    id VARCHAR(36) PRIMARY KEY,
    workflow_run_id VARCHAR(36) NOT NULL,
    workflow_step_id VARCHAR(36) NOT NULL,
    status VARCHAR(50) NOT NULL,
    started_at TIMESTAMP NULL,
    completed_at TIMESTAMP NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (workflow_run_id) REFERENCES workflow_runs(id),
    FOREIGN KEY (workflow_step_id) REFERENCES workflow_steps(id)
);

-- Add workflow_step_run_id FK column to Job table
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS workflow_step_run_id VARCHAR(36);

-- Add depth column to Job table (for ENGINE-02 30-level override)
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS depth INTEGER;

-- Foreign key constraint for workflow_step_run_id (with ON DELETE SET NULL for safety)
-- Note: SQLite does not support ADD CONSTRAINT IF NOT EXISTS, so this is Postgres-only syntax
-- For SQLite, the constraint is optional; application enforces referential integrity
-- ALTER TABLE jobs ADD CONSTRAINT IF NOT EXISTS fk_jobs_workflow_step_run FOREIGN KEY (workflow_step_run_id) REFERENCES workflow_step_runs(id) ON DELETE SET NULL;

-- Indexes for common queries
CREATE INDEX IF NOT EXISTS idx_wsr_run_id ON workflow_step_runs(workflow_run_id);
CREATE INDEX IF NOT EXISTS idx_wsr_step_id ON workflow_step_runs(workflow_step_id);
CREATE INDEX IF NOT EXISTS idx_wsr_status ON workflow_step_runs(status);
CREATE INDEX IF NOT EXISTS idx_job_wsr ON jobs(workflow_step_run_id);
CREATE INDEX IF NOT EXISTS idx_job_depth ON jobs(depth);
