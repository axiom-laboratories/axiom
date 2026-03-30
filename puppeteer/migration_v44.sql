-- migration_v44.sql — Phase 98: Dispatch Correctness
-- Adds composite index (status, created_at) for efficient job candidate scanning.
--
-- IMPORTANT: CREATE INDEX CONCURRENTLY cannot run inside a transaction block.
-- Do NOT use: psql -1 -f migration_v44.sql  (the -1 flag wraps in BEGIN/COMMIT)
-- Instead use: psql -f migration_v44.sql     (no transaction wrapper)
--
-- This index is safe for zero-downtime deployment — CONCURRENTLY does not hold
-- an exclusive table lock. It may take several seconds on large jobs tables.
--
-- Pre-flight check (run first to confirm jobs table exists):
--   SELECT COUNT(*) FROM jobs;
--
-- Apply:

CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_jobs_status_created_at
    ON jobs (status, created_at);

-- Validity confirmation (run after to confirm index exists):
--   SELECT indexname, indexdef
--   FROM pg_indexes
--   WHERE tablename = 'jobs' AND indexname = 'ix_jobs_status_created_at';
