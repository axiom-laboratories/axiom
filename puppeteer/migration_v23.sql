-- migration_v23.sql
-- Milestone 4: Automation — triggers table

CREATE TABLE IF NOT EXISTS triggers (
    id VARCHAR PRIMARY KEY,
    slug VARCHAR UNIQUE NOT NULL,
    name VARCHAR NOT NULL,
    job_definition_id VARCHAR NOT NULL REFERENCES scheduled_jobs(id),
    secret_token VARCHAR NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
