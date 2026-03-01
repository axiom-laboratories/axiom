-- Migration for v1.0 — Force Password Change
-- Run against your Postgres instance before restarting the agent.

BEGIN;

ALTER TABLE users ADD COLUMN IF NOT EXISTS must_change_password BOOLEAN NOT NULL DEFAULT FALSE;

COMMIT;
