-- Phase 2: User signing keys and API keys

CREATE TABLE IF NOT EXISTS user_signing_keys (
    id VARCHAR PRIMARY KEY,
    username VARCHAR NOT NULL REFERENCES users(username),
    name VARCHAR NOT NULL,
    public_key_pem TEXT NOT NULL,
    encrypted_private_key TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS user_api_keys (
    id VARCHAR PRIMARY KEY,
    username VARCHAR NOT NULL REFERENCES users(username),
    name VARCHAR NOT NULL,
    key_hash VARCHAR NOT NULL,
    key_prefix VARCHAR(12) NOT NULL,
    permissions TEXT,
    expires_at TIMESTAMP,
    last_used_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_user_api_keys_prefix ON user_api_keys(key_prefix);
CREATE INDEX IF NOT EXISTS idx_user_signing_keys_username ON user_signing_keys(username);
CREATE INDEX IF NOT EXISTS idx_user_api_keys_username ON user_api_keys(username);
