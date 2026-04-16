-- Migration v55: Workflow Triggers & Parameter Injection

-- Add cron scheduling support to Workflow
ALTER TABLE workflows
ADD COLUMN IF NOT EXISTS schedule_cron TEXT;

-- Add trigger audit trail to WorkflowRun
ALTER TABLE workflow_runs
ADD COLUMN IF NOT EXISTS trigger_type VARCHAR(50);

ALTER TABLE workflow_runs
ADD COLUMN IF NOT EXISTS triggered_by VARCHAR(255);

-- Add parameter snapshot to WorkflowRun
ALTER TABLE workflow_runs
ADD COLUMN IF NOT EXISTS parameters_json TEXT;

-- Create webhook table for unauthenticated trigger endpoints
CREATE TABLE IF NOT EXISTS workflow_webhooks (
    id VARCHAR(36) PRIMARY KEY,
    workflow_id VARCHAR(36) NOT NULL,
    name VARCHAR(255) NOT NULL,
    secret_hash VARCHAR(255) NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (workflow_id) REFERENCES workflows(id) ON DELETE CASCADE
);

-- Index for quick webhook lookup by workflow_id
CREATE INDEX IF NOT EXISTS idx_workflow_webhooks_workflow_id
ON workflow_webhooks(workflow_id);
