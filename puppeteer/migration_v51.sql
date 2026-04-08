-- Migration v51: Add cgroup detection columns to nodes table
-- For existing Postgres deployments only (fresh deployments use create_all in db.py)

ALTER TABLE nodes ADD COLUMN IF NOT EXISTS detected_cgroup_version VARCHAR(255);
ALTER TABLE nodes ADD COLUMN IF NOT EXISTS cgroup_raw TEXT;
