-- migration_v47.sql -- Phase 114: Curated Bundles + Starter Templates
-- Adds ecosystem column to curated_bundle_items (per-item ecosystem support)
-- Adds is_starter column to puppet_templates (starter template immutability flag)
-- Safe for existing deployments (IF NOT EXISTS / ADD COLUMN IF NOT EXISTS).
-- SQLite deployments get fresh schema from create_all; this file is for Postgres.

-- 1. Add ecosystem column to curated_bundle_items
-- Default to PYPI for existing items (can be overridden per item)
ALTER TABLE curated_bundle_items ADD COLUMN IF NOT EXISTS ecosystem VARCHAR(20) NOT NULL DEFAULT 'PYPI';

-- 2. Add is_starter column to puppet_templates
-- False by default; set to true only for pre-seeded starter templates
ALTER TABLE puppet_templates ADD COLUMN IF NOT EXISTS is_starter BOOLEAN NOT NULL DEFAULT FALSE;
