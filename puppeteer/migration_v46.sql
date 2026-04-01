-- migration_v46.sql -- Phase 107: Schema Foundation + CRUD Completeness
-- Adds ecosystem enum to approved_ingredients, creates new tables for dep resolution + bundles.
-- Safe for existing deployments (IF NOT EXISTS / ADD COLUMN IF NOT EXISTS).
-- SQLite deployments get fresh schema from create_all; this file is for Postgres.

-- 1. Add ecosystem column to approved_ingredients
ALTER TABLE approved_ingredients ADD COLUMN IF NOT EXISTS ecosystem VARCHAR(20) NOT NULL DEFAULT 'PYPI';

-- 2. Create ingredient_dependencies table
CREATE TABLE IF NOT EXISTS ingredient_dependencies (
    id SERIAL PRIMARY KEY,
    parent_id VARCHAR(36) NOT NULL,
    child_id VARCHAR(36) NOT NULL,
    dependency_type VARCHAR(50) NOT NULL,
    version_constraint VARCHAR(255),
    ecosystem VARCHAR(20) NOT NULL,
    discovered_at TIMESTAMP DEFAULT NOW(),
    CONSTRAINT uq_ingredient_dep UNIQUE(parent_id, child_id, ecosystem)
);
CREATE INDEX IF NOT EXISTS ix_ingredient_deps_parent ON ingredient_dependencies(parent_id);
CREATE INDEX IF NOT EXISTS ix_ingredient_deps_child ON ingredient_dependencies(child_id);

-- 3. Create curated_bundles table
CREATE TABLE IF NOT EXISTS curated_bundles (
    id VARCHAR(36) PRIMARY KEY,
    name VARCHAR(255) UNIQUE NOT NULL,
    description TEXT,
    ecosystem VARCHAR(20) NOT NULL,
    os_family VARCHAR(50) NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    is_active BOOLEAN NOT NULL DEFAULT TRUE
);

-- 4. Create curated_bundle_items table
CREATE TABLE IF NOT EXISTS curated_bundle_items (
    id SERIAL PRIMARY KEY,
    bundle_id VARCHAR(36) NOT NULL,
    ingredient_name VARCHAR(255) NOT NULL,
    version_constraint VARCHAR(255) DEFAULT '*'
);
CREATE INDEX IF NOT EXISTS ix_bundle_items_bundle ON curated_bundle_items(bundle_id);
