-- migration_v18.sql
-- Phase 5: Job Dependencies — add depends_on to jobs
-- Safe to run on existing Postgres deployments (IF NOT EXISTS guards)

ALTER TABLE jobs ADD COLUMN IF NOT EXISTS depends_on TEXT;

-- Seed history:read permission for operators
INSERT INTO role_permissions (id, role, permission)
VALUES (md5(random()::text), 'operator', 'history:read')
ON CONFLICT (role, permission) DO NOTHING;

