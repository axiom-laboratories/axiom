-- Phase 167-02: Vault secret resolution in job dispatch
-- Add columns to jobs table to support secret resolution

-- Add use_vault_secrets flag (default FALSE)
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS use_vault_secrets BOOLEAN NOT NULL DEFAULT FALSE;

-- Add vault_secrets JSON list of secret names to resolve
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS vault_secrets TEXT;

-- No additional indexes needed — these columns are small and accessed only during pull_work
