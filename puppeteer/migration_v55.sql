-- Migration v55: Add workflow execution columns to jobs table (Phase 147)
ALTER TABLE jobs ADD COLUMN workflow_step_run_id VARCHAR NULL;
ALTER TABLE jobs ADD COLUMN depth INTEGER NULL;
