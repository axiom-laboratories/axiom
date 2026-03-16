-- migration_v22.sql
-- Milestone 3 Phase 4: Persist base_os_family on nodes

ALTER TABLE nodes ADD COLUMN IF NOT EXISTS base_os_family VARCHAR;
