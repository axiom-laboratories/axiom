-- Migration v53: Phase 146 - Workflow data model
-- Creates 5 normalized workflow tables (no JSON blobs)
-- For existing Postgres deployments only (fresh deployments use create_all in db.py)

CREATE TABLE IF NOT EXISTS workflows (
    id VARCHAR PRIMARY KEY,
    name VARCHAR NOT NULL,
    created_by VARCHAR NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP,
    is_paused BOOLEAN NOT NULL DEFAULT FALSE,
    UNIQUE (name)
);

CREATE TABLE IF NOT EXISTS workflow_steps (
    id VARCHAR PRIMARY KEY,
    workflow_id VARCHAR NOT NULL,
    scheduled_job_id VARCHAR NOT NULL,
    node_type VARCHAR NOT NULL,
    config_json TEXT,
    FOREIGN KEY (workflow_id) REFERENCES workflows(id) ON DELETE CASCADE,
    FOREIGN KEY (scheduled_job_id) REFERENCES scheduled_jobs(id) ON DELETE RESTRICT
);

CREATE INDEX IF NOT EXISTS ix_workflow_steps_workflow_id ON workflow_steps(workflow_id);

CREATE TABLE IF NOT EXISTS workflow_edges (
    id VARCHAR PRIMARY KEY,
    workflow_id VARCHAR NOT NULL,
    from_step_id VARCHAR NOT NULL,
    to_step_id VARCHAR NOT NULL,
    branch_name VARCHAR,
    FOREIGN KEY (workflow_id) REFERENCES workflows(id) ON DELETE CASCADE,
    FOREIGN KEY (from_step_id) REFERENCES workflow_steps(id) ON DELETE CASCADE,
    FOREIGN KEY (to_step_id) REFERENCES workflow_steps(id) ON DELETE CASCADE,
    UNIQUE (from_step_id, to_step_id, workflow_id)
);

CREATE INDEX IF NOT EXISTS ix_workflow_edges_workflow_id ON workflow_edges(workflow_id);
CREATE INDEX IF NOT EXISTS ix_workflow_edges_from_step ON workflow_edges(from_step_id);
CREATE INDEX IF NOT EXISTS ix_workflow_edges_to_step ON workflow_edges(to_step_id);

CREATE TABLE IF NOT EXISTS workflow_parameters (
    id VARCHAR PRIMARY KEY,
    workflow_id VARCHAR NOT NULL,
    name VARCHAR NOT NULL,
    type VARCHAR NOT NULL,
    default_value VARCHAR,
    FOREIGN KEY (workflow_id) REFERENCES workflows(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS ix_workflow_parameters_workflow_id ON workflow_parameters(workflow_id);
