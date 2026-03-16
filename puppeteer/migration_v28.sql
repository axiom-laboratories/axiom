-- migration_v28.sql: Smelter Registry & Compliance Tracking

CREATE TABLE IF NOT EXISTS approved_ingredients (
    id VARCHAR(36) PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    version_constraint VARCHAR(255) NOT NULL,
    sha256 VARCHAR(64),
    os_family VARCHAR(50) NOT NULL,
    is_vulnerable BOOLEAN DEFAULT FALSE,
    vulnerability_report TEXT, -- JSON as text
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

ALTER TABLE puppet_templates ADD COLUMN is_compliant BOOLEAN DEFAULT TRUE;
