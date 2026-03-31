-- migration_v45.sql — Add must_change_password column to users table
-- Required for admin/admin cold-start with forced first-login password change.
-- Safe to run on existing deployments — IF NOT EXISTS prevents errors on fresh DBs.

ALTER TABLE users ADD COLUMN IF NOT EXISTS must_change_password BOOLEAN NOT NULL DEFAULT FALSE;
