-- migration_v17.sql
-- Phase 4: Environment Tags — add operator_tags to nodes
-- Safe to run on existing Postgres deployments (IF NOT EXISTS guards)

ALTER TABLE nodes ADD COLUMN IF NOT EXISTS operator_tags TEXT;
