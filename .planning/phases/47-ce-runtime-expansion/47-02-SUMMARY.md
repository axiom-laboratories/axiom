---
phase: 47-ce-runtime-expansion
plan: "02"
subsystem: backend-api
tags: [runtime, validation, job-service, scheduler, migration, tdd]
dependency_graph:
  requires: [47-01]
  provides: [runtime-validation, display-type, scheduled-job-runtime, migration-v38]
  affects:
    - puppeteer/agent_service/models.py
    - puppeteer/agent_service/services/job_service.py
    - puppeteer/agent_service/db.py
    - puppeteer/agent_service/services/scheduler_service.py
    - puppeteer/migration_v38.sql
tech_stack:
  added: []
  patterns:
    - "Pydantic model_validator for cross-field validation (task_type + runtime)"
    - "Server-authoritative display_type computed from (task_type, runtime) — frontend never parses payload"
    - "Runtime merged into payload dict before encryption so node receives it inside the payload"
key_files:
  created:
    - puppeteer/migration_v38.sql
  modified:
    - puppeteer/agent_service/models.py
    - puppeteer/agent_service/services/job_service.py
    - puppeteer/agent_service/db.py
    - puppeteer/agent_service/services/scheduler_service.py
decisions:
  - "python_script task_type dropped entirely — model_validator raises 422 with clear migration message (RT-06 superseded by CONTEXT.md decision)"
  - "Runtime merged into payload dict (not a separate column on WorkResponse) so node.py reads it from payload as before"
  - "migration_v38.sql uses IF NOT EXISTS guards for both scheduled_jobs and jobs tables — safe to re-run"
metrics:
  duration: "~3 minutes"
  completed: "2026-03-22T16:56:00Z"
  tasks_completed: 2
  files_changed: 5
---

# Phase 47 Plan 02: CE Runtime Expansion — Backend API Wiring Summary

Pydantic model_validator enforces the unified `script` task_type at the API boundary; `_compute_display_type` returns server-authoritative display labels; `runtime` columns added to both DB tables; scheduler fires `task_type="script"` with runtime from `ScheduledJob.runtime`; migration SQL provided.

## What Was Built

### Task 1: Runtime validation in models.py (RT-04, RT-05) — commit 23979c1

Added `runtime: Optional[Literal["python", "bash", "powershell"]] = None` to `JobCreate`.

Added `@model_validator(mode="after")` named `validate_task_type_and_runtime` that:
- Raises `ValueError` if `task_type == "python_script"` with a clear migration message
- Raises `ValueError` if `task_type == "script"` and `runtime is None`
- Returns `self` on success

Added `display_type: Optional[str] = None` and `task_type: Optional[str] = None` to `JobResponse`.

Added `runtime: Optional[Literal[...]] = None` to `JobDefinitionCreate` and `JobDefinitionUpdate`.
Added `runtime: Optional[str] = None` to `JobDefinitionResponse`.

Added `Literal` to typing imports.

**Test result:** `test_invalid_runtime_rejected` GREEN.

### Task 2: display_type, runtime columns, scheduler update (RT-05, RT-07) — commit 5183005

**job_service.py:**
- `_compute_display_type(task_type, payload)` helper defined before `JobService` class: returns `"script (python)"` / `"script (bash)"` / `"script (powershell)"` or falls back to `task_type`
- `list_jobs` response dict includes `"task_type"` and `"display_type"` keys
- `create_job` builds `payload_dict = dict(job_req.payload)`, merges `runtime` in, then calls `encrypt_secrets(payload_dict)` — runtime travels inside the encrypted payload to the node
- `Job` row creation includes `runtime=job_req.runtime`

**db.py:**
- `Job.runtime: Mapped[Optional[str]]` — nullable, no default (runtime stored in payload too)
- `ScheduledJob.runtime: Mapped[Optional[str]]` — nullable, `default="python"`

**scheduler_service.py:**
- `execute_scheduled_job`: reads `runtime = getattr(s_job, 'runtime', None) or 'python'`; adds `"runtime"` key to `payload_dict`; creates `Job` with `task_type="script"` and `runtime=runtime`
- `create_job_definition`: sets `runtime=def_req.runtime or "python"` on new `ScheduledJob`
- `update_job_definition`: updates `job.runtime` if `update_req.runtime is not None`

**migration_v38.sql:**
```sql
-- migration_v38: Add runtime column to scheduled_jobs and jobs for multi-runtime support (RT-07)
ALTER TABLE scheduled_jobs ADD COLUMN IF NOT EXISTS runtime VARCHAR DEFAULT 'python';
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS runtime VARCHAR;
```

**Test results:** `test_display_type_computed_serverside` GREEN, `test_scheduled_job_runtime_field` GREEN. Full runtime expansion suite: 7/7 GREEN.

## Test Results

| Test | Status | Notes |
|------|--------|-------|
| test_containerfile_has_powershell | GREEN | RT-03 (pre-existing) |
| test_bash_job_accepted | GREEN | RT-01 (pre-existing) |
| test_powershell_job_accepted | GREEN | RT-02 (pre-existing) |
| test_node_script_execution | GREEN | RT-01/02 (pre-existing) |
| test_invalid_runtime_rejected | GREEN | RT-05 — new this plan |
| test_display_type_computed_serverside | GREEN | RT-04 — new this plan |
| test_scheduled_job_runtime_field | GREEN | RT-07 — new this plan |

## Deviations from Plan

None — plan executed exactly as written.

Pre-existing collection errors in other test files (`test_foundry_mirror.py`, `test_tools.py`, etc.) are EE-only features not present in CE `db.py` — out of scope and not caused by this plan's changes.

## Self-Check: PASSED
