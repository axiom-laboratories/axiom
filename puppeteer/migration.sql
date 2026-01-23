-- Migration for v0.8 Concurrent Jobs (PostgreSQL / SQLite Compatible)
-- Run this against your existing 'jobs.db' or Postgres instance.

-- 1. Add concurrency_limit (Default 5)
ALTER TABLE nodes ADD COLUMN concurrency_limit INTEGER DEFAULT 5;

-- 2. Add job_memory_limit (Default '512m')
ALTER TABLE nodes ADD COLUMN job_memory_limit VARCHAR DEFAULT '512m';
