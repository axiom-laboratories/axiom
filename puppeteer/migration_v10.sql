-- Migration for v1.0 — Force Password Change + Session Invalidation
-- Run against your Postgres instance before restarting the agent.

BEGIN;

ALTER TABLE users ADD COLUMN IF NOT EXISTS must_change_password BOOLEAN NOT NULL DEFAULT FALSE;
ALTER TABLE users ADD COLUMN IF NOT EXISTS token_version INTEGER NOT NULL DEFAULT 0;

-- Grant foundry:write and signatures:write to the operator role if not already present.
-- These were missing from the initial seed (WARN-5 fix).
INSERT INTO role_permissions (id, role, permission)
    VALUES
        (md5(random()::text), 'operator', 'foundry:write'),
        (md5(random()::text), 'operator', 'signatures:write')
    ON CONFLICT (role, permission) DO NOTHING;

COMMIT;
