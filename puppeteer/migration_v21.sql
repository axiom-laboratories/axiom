-- migration_v21.sql
-- Milestone 3 Phase 3: Hot-Upgrade Engine

-- Add upgrade tracking to nodes
ALTER TABLE nodes ADD COLUMN IF NOT EXISTS pending_upgrade TEXT;
ALTER TABLE nodes ADD COLUMN IF NOT EXISTS upgrade_history TEXT;
