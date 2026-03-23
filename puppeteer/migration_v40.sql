-- Phase 51: Job resubmit traceability
-- For PostgreSQL (production): IF NOT EXISTS guard
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS originating_guid VARCHAR;
-- For SQLite (local dev): run manually if column absent (SQLite has no IF NOT EXISTS on ALTER)
-- sqlite3 jobs.db "ALTER TABLE jobs ADD COLUMN originating_guid TEXT;"
