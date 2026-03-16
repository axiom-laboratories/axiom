-- migration_v19.sql
-- Milestone 3: Advanced Foundry — artifacts and approved_os tables

CREATE TABLE IF NOT EXISTS artifacts (
    id VARCHAR PRIMARY KEY,
    filename VARCHAR NOT NULL,
    content_type VARCHAR NOT NULL,
    sha256 VARCHAR NOT NULL,
    size_bytes INTEGER NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS approved_os (
    id SERIAL PRIMARY KEY,
    name VARCHAR UNIQUE NOT NULL,
    image_uri VARCHAR NOT NULL,
    os_family VARCHAR NOT NULL
);

-- Update capability_matrix to support artifacts
ALTER TABLE capability_matrix ADD COLUMN IF NOT EXISTS artifact_id VARCHAR REFERENCES artifacts(id);
