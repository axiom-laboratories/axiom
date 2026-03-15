-- migration_v29.sql: Add mirroring columns to approved_ingredients
-- Safe to re-run on existing Postgres deployments (IF NOT EXISTS guards).
ALTER TABLE approved_ingredients ADD COLUMN IF NOT EXISTS mirror_status VARCHAR(50) DEFAULT 'PENDING';
ALTER TABLE approved_ingredients ADD COLUMN IF NOT EXISTS mirror_path VARCHAR(255);
ALTER TABLE approved_ingredients ADD COLUMN IF NOT EXISTS mirror_log TEXT;
ALTER TABLE approved_ingredients ADD COLUMN IF NOT EXISTS is_active BOOLEAN DEFAULT TRUE;
