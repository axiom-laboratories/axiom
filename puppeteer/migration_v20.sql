-- migration_v20.sql
-- Milestone 3 Phase 2: Tamper Detection

-- Add template_id to tokens
ALTER TABLE tokens ADD COLUMN IF NOT EXISTS template_id VARCHAR;

-- Add security fields to nodes
ALTER TABLE nodes ADD COLUMN IF NOT EXISTS expected_capabilities TEXT;
ALTER TABLE nodes ADD COLUMN IF NOT EXISTS tamper_details TEXT;

-- Update status constraint/enum if applicable (SQLite/Postgres handled by app-level strings usually)
-- For existing deployments, ensure we can handle 'TAMPERED' status.
