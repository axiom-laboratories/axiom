-- Phase 51-02: Add originating_guid column to jobs table (JOB-05 resubmit traceability)
-- Run on existing PostgreSQL deployments. SQLite (dev/test) handled by create_all at startup.

ALTER TABLE jobs ADD COLUMN IF NOT EXISTS originating_guid VARCHAR;
