-- Migration v52: Phase 124 - Add execution_mode column to nodes table
-- For existing Postgres deployments only (fresh deployments use create_all in db.py)

ALTER TABLE nodes ADD COLUMN IF NOT EXISTS execution_mode TEXT;
