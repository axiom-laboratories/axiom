-- migration_v37: Add signature_hmac column for HMAC integrity on signature_payload (SEC-02)
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS signature_hmac VARCHAR(64);
