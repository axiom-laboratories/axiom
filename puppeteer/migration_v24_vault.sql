-- Phase 167: HashiCorp Vault Integration (EE)
-- Create vault_config table for Vault connection settings
-- secret_id column holds Fernet-encrypted AppRole secret (see security.py cipher_suite)

CREATE TABLE IF NOT EXISTS vault_config (
    id VARCHAR(36) PRIMARY KEY,
    vault_address VARCHAR(512) NOT NULL,
    role_id VARCHAR(255) NOT NULL,
    secret_id TEXT NOT NULL,  -- Fernet-encrypted at rest
    mount_path VARCHAR(255) NOT NULL DEFAULT 'secret',
    namespace VARCHAR(255),  -- NULL for non-Enterprise Vaults
    provider_type VARCHAR(32) NOT NULL DEFAULT 'vault',  -- D-15: extensible for future backends
    enabled BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- No unique constraints: at most one row in practice, but schema allows flexibility for future multi-config
-- Index on enabled for fast filtering in startup/dispatch logic
CREATE INDEX IF NOT EXISTS ix_vault_config_enabled ON vault_config(enabled);
