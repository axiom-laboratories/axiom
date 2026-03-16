-- migration_v24.sql
-- Milestone 4 Phase 2: Conditional Triggers — signals table

CREATE TABLE IF NOT EXISTS signals (
    name VARCHAR PRIMARY KEY,
    payload TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
