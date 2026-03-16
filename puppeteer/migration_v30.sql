-- migration_v30.sql: Image Lifecycle & BOM tracking

ALTER TABLE puppet_templates ADD COLUMN status VARCHAR(50) DEFAULT 'DRAFT';
ALTER TABLE puppet_templates ADD COLUMN bom_captured BOOLEAN DEFAULT FALSE;

CREATE TABLE IF NOT EXISTS image_boms (
    id VARCHAR(36) PRIMARY KEY,
    template_id VARCHAR(36) NOT NULL,
    raw_data_json TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (template_id) REFERENCES puppet_templates(id)
);

CREATE TABLE IF NOT EXISTS package_index (
    id VARCHAR(36) PRIMARY KEY,
    template_id VARCHAR(36) NOT NULL,
    name VARCHAR(255) NOT NULL,
    version VARCHAR(50) NOT NULL,
    type VARCHAR(20) NOT NULL, -- 'pip' or 'apt'
    FOREIGN KEY (template_id) REFERENCES puppet_templates(id)
);

CREATE INDEX idx_pkg_name_version ON package_index(name, version);
