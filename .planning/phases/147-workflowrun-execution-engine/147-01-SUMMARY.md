---
phase: 147-workflowrun-execution-engine
plan: 01
subsystem: workflow-execution-engine
tags: [schema, orm, pydantic, migration]
completed_at: 2026-04-15T21:11:44Z
duration_seconds: 49
requirements: [ENGINE-01, ENGINE-02, ENGINE-03, ENGINE-04, ENGINE-05, ENGINE-06, ENGINE-07]
decisions: []
deviations: []
---

# Phase 147 Plan 01: WorkflowRun Execution Schema — COMPLETE

WorkflowRun execution engine baseline: Per-step status tracking independent from Job execution, plus depth tracking for workflow-created job nesting (ENGINE-02).

## Summary

Created the database schema and Pydantic models for WorkflowRun execution engine:

- **WorkflowStepRun ORM** (`puppeteer/agent_service/db.py`): tracks per-step status (PENDING/RUNNING/COMPLETED/FAILED/SKIPPED/CANCELLED) with timestamps. Relationships to WorkflowRun and WorkflowStep with bidirectional back_populates.
- **Job extensions** (`puppeteer/agent_service/db.py`): Added workflow_step_run_id (nullable string FK) and depth (nullable int) columns for ENGINE-02 30-level depth override.
- **Pydantic models** (`puppeteer/agent_service/models.py`): WorkflowStepRunCreate + WorkflowStepRunResponse for API serialization. Updated WorkflowRunResponse to include step_runs field (List[WorkflowStepRunResponse]) for cascade status tracking.
- **Migration** (`puppeteer/migration_v54.sql`): Postgres + SQLite compatible DDL. Creates workflow_step_runs table with FKs to workflow_runs and workflow_steps. Adds columns to jobs table with indexes on common query patterns.

## Artifacts

| File | Change | Purpose |
|------|--------|---------|
| `puppeteer/agent_service/db.py` | NEW: WorkflowStepRun class + relationships | Per-step execution state machine |
| `puppeteer/agent_service/db.py` | NEW: Job.workflow_step_run_id, Job.depth | FK reference + nesting depth tracking |
| `puppeteer/agent_service/models.py` | NEW: WorkflowStepRunCreate, WorkflowStepRunResponse | API request/response models |
| `puppeteer/agent_service/models.py` | UPDATED: WorkflowRunResponse.step_runs | Cascade step status in run response |
| `puppeteer/migration_v54.sql` | NEW: Full schema migration | Existing deployment compatibility |

## Key Links

- **Job.workflow_step_run_id** → WorkflowStepRun.id (foreign key pattern: Phase 147 Plan 02 service layer will enforce)
- **Job.depth** → Used by ENGINE-02 override logic in dispatch_next_wave (Phase 147 Plan 02+)
- **WorkflowStepRun.status** → Values: PENDING, RUNNING, COMPLETED, FAILED, SKIPPED, CANCELLED (state machine for Phase 147 Plan 02)

## Verification

All artifacts verified:
- ORM models compile: `from agent_service.db import WorkflowStepRun, Job`
- Pydantic models compile: `from agent_service.models import WorkflowStepRunResponse, WorkflowRunResponse`
- Migration file syntax valid: CREATE TABLE, ALTER TABLE, indexes all present

## What's Next

Plan 02 (Service Layer): Implement dispatch_next_wave with depth-aware job creation and BFS state machine for WorkflowStepRun status transitions.

## Commits

- `048e82f`: feat(147-01): Add WorkflowStepRun ORM model and Job columns
- `9689f26`: feat(147-01): Add WorkflowStepRun Pydantic models
- `351e9f8`: feat(147-01): Add migration_v54.sql for WorkflowStepRun schema
