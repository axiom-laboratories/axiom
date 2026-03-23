---
phase: 53-scheduling-health-and-data-management
plan: "02"
subsystem: database
tags: [db, orm, migration, scheduling, execution-records, job-templates]
dependency_graph:
  requires: []
  provides: [ScheduledFireLog ORM model, JobTemplate ORM model, ExecutionRecord.pinned, ScheduledJob.allow_overlap, ScheduledJob.dispatch_timeout_minutes, Job.dispatch_timeout_minutes, migration_v43.sql]
  affects: [puppeteer/agent_service/db.py, puppeteer/migration_v43.sql]
tech_stack:
  added: []
  patterns: [SQLAlchemy mapped_column, create_all for fresh deployments, migration SQL for existing deployments]
key_files:
  created:
    - puppeteer/migration_v43.sql
  modified:
    - puppeteer/agent_service/db.py
decisions:
  - "ScheduledFireLog and JobTemplate appended after ExecutionRecord and before Signal — keeps new tables co-located with the models they support"
  - "allow_overlap default=False on ScheduledJob aligns with existing overlap guard behavior — no regression risk for existing deployments"
  - "migration_v43.sql uses IF NOT EXISTS guards on all DDL — safe to re-run on existing Postgres deployments"
  - "SQLite equivalents provided as comments — SQLite ALTER TABLE lacks IF NOT EXISTS column guard, so operator must uncomment manually"
metrics:
  duration: "84s"
  completed: "2026-03-23"
  tasks_completed: 2
  files_changed: 2
---

# Phase 53 Plan 02: DB Schema Foundation — ScheduledFireLog, JobTemplate, and Column Additions Summary

**One-liner:** Phase 53 DB foundation adding ScheduledFireLog and JobTemplate ORM models plus pinned/allow_overlap/dispatch_timeout_minutes columns with Postgres-safe migration SQL.

## What Was Built

Two tasks executed:

**Task 1 — db.py additions:**
- `ExecutionRecord.pinned` — Boolean, default False; allows users to pin execution records from being pruned (SRCH-09)
- `ScheduledJob.allow_overlap` — Boolean, default False; controls whether concurrent cron fires are permitted (SRCH-08)
- `ScheduledJob.dispatch_timeout_minutes` — Optional Integer; per-definition dispatch timeout (Phase 53)
- `Job.dispatch_timeout_minutes` — Optional Integer; per-job dispatch timeout inherited from scheduled job (Phase 53)
- `ScheduledFireLog` — new ORM model recording each APScheduler cron fire attempt with status (fired|skipped_draft|skipped_overlap) and composite index on (scheduled_job_id, expected_at) (VIS-05, VIS-06)
- `JobTemplate` — new ORM model for reusable job configurations with private/shared visibility (SRCH-06)

**Task 2 — migration_v43.sql:**
- 14 DDL statements covering all 5 schema changes
- ALTER TABLE guards use IF NOT EXISTS (Postgres) — safe to re-run
- SQLite equivalents provided as commented-out blocks
- Fresh deployments handled by existing `create_all` at startup

## Deviations from Plan

None — plan executed exactly as written.

## Self-Check

- [x] `puppeteer/agent_service/db.py` modified — verified via Python import
- [x] `puppeteer/migration_v43.sql` created — 14 DDL statements confirmed
- [x] All 5 new attributes importable and instantiable — `True` for all checks
- [x] Commits exist: `2354a32` (db.py), `451bb93` (migration_v43.sql)

## Self-Check: PASSED
