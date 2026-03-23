-- migration_v43.sql — Phase 53: Scheduling Health and Data Management
-- Safe to re-run: all statements use IF NOT EXISTS or IF NOT EXISTS column guards
-- Apply to existing deployments; fresh deployments use create_all at startup

-- Part 1: ExecutionRecord pinning (SRCH-09)
-- PostgreSQL:
ALTER TABLE execution_records ADD COLUMN IF NOT EXISTS pinned BOOLEAN DEFAULT FALSE;
-- SQLite (uncomment if running SQLite locally):
-- ALTER TABLE execution_records ADD COLUMN pinned INTEGER DEFAULT 0;

-- Part 2: ScheduledJob overlap control + dispatch timeout (Phase 53)
-- allow_overlap default=FALSE aligns with existing overlap guard behavior (no regression)
-- PostgreSQL:
ALTER TABLE scheduled_jobs ADD COLUMN IF NOT EXISTS allow_overlap BOOLEAN DEFAULT FALSE;
ALTER TABLE scheduled_jobs ADD COLUMN IF NOT EXISTS dispatch_timeout_minutes INTEGER;
-- SQLite:
-- ALTER TABLE scheduled_jobs ADD COLUMN allow_overlap INTEGER DEFAULT 0;
-- ALTER TABLE scheduled_jobs ADD COLUMN dispatch_timeout_minutes INTEGER;

-- Part 3: Job dispatch timeout (Phase 53)
-- PostgreSQL:
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS dispatch_timeout_minutes INTEGER;
-- SQLite:
-- ALTER TABLE jobs ADD COLUMN dispatch_timeout_minutes INTEGER;

-- Part 4: New tables (create_all handles fresh deployments; this handles existing)
-- ScheduledFireLog: records each APScheduler cron fire attempt
CREATE TABLE IF NOT EXISTS scheduled_fire_log (
    id SERIAL PRIMARY KEY,
    scheduled_job_id VARCHAR NOT NULL,
    expected_at TIMESTAMP NOT NULL,
    status VARCHAR NOT NULL DEFAULT 'fired',
    created_at TIMESTAMP DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_fire_log_job_expected ON scheduled_fire_log(scheduled_job_id, expected_at);

-- JobTemplate: reusable job configurations (signing state excluded)
CREATE TABLE IF NOT EXISTS job_templates (
    id VARCHAR PRIMARY KEY,
    name VARCHAR NOT NULL,
    creator_id VARCHAR NOT NULL,
    visibility VARCHAR NOT NULL DEFAULT 'private',
    payload TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);

-- SQLite equivalents for new tables (comment out Postgres versions above):
-- CREATE TABLE IF NOT EXISTS scheduled_fire_log (
--     id INTEGER PRIMARY KEY AUTOINCREMENT,
--     scheduled_job_id VARCHAR NOT NULL,
--     expected_at TIMESTAMP NOT NULL,
--     status VARCHAR NOT NULL DEFAULT 'fired',
--     created_at TIMESTAMP
-- );
-- CREATE INDEX IF NOT EXISTS ix_fire_log_job_expected ON scheduled_fire_log(scheduled_job_id, expected_at);
-- CREATE TABLE IF NOT EXISTS job_templates (
--     id VARCHAR PRIMARY KEY,
--     name VARCHAR NOT NULL,
--     creator_id VARCHAR NOT NULL,
--     visibility VARCHAR NOT NULL DEFAULT 'private',
--     payload TEXT NOT NULL,
--     created_at TIMESTAMP
-- );
