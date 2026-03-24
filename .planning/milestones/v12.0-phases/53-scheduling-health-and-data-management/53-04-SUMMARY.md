---
phase: 53-scheduling-health-and-data-management
plan: "04"
subsystem: backend-api
tags: [job-templates, execution-pinning, retention-config, csv-export, tdd]
dependency_graph:
  requires: [53-01, 53-02]
  provides: [SRCH-06, SRCH-07, SRCH-08, SRCH-09, SRCH-10]
  affects: [puppeteer/agent_service/main.py, puppeteer/agent_service/models.py]
tech_stack:
  added: []
  patterns: [tdd-red-green, fastapi-route, dependency-override-testing, streaming-csv]
key_files:
  created:
    - puppeteer/tests/test_job_templates.py
    - puppeteer/tests/test_retention.py
    - puppeteer/tests/test_execution_export.py
  modified:
    - puppeteer/agent_service/main.py
    - puppeteer/agent_service/models.py
decisions:
  - "SimpleNamespace used for fake User objects in tests — SQLAlchemy ORM objects cannot be instantiated via __new__ without a mapper context"
  - "EXEC_CSV_HEADERS defined as module-level constant in main.py — imported by test_execution_export.py for header assertion"
  - "test_pruner_respects_pinned patches db_module.AsyncSessionLocal with a context manager mock — keeps test isolated to in-memory DB"
  - "RetentionConfigUpdate model added to models.py alongside JobTemplateCreate/Response/Update — collocated by feature group"
metrics:
  duration: "3min"
  completed_date: "2026-03-23"
  tasks_completed: 2
  files_modified: 5
---

# Phase 53 Plan 04: Job Templates, Pin/Unpin, Retention Config, and CSV Export Summary

Job templates CRUD with signing-field stripping, execution record pin/unpin with audit logging, admin retention config endpoints, and per-job execution CSV export — all with 5 passing TDD tests.

## What Was Built

### Task 1: Job Templates CRUD (SRCH-06, SRCH-07)

Added to `models.py`:
- `SIGNING_FIELDS` set constant (`signature_id`, `signature_payload`, `signature_hmac`)
- `JobTemplateCreate` Pydantic model (name, visibility, payload)
- `JobTemplateResponse` Pydantic model (id, name, creator_id, visibility, payload, created_at)
- `JobTemplateUpdate` Pydantic model (optional name, visibility)

Added to `main.py`:
- `POST /job-templates` (jobs:write) — creates template, strips signing fields from payload
- `GET /job-templates` (jobs:read) — returns shared templates + caller's private templates
- `GET /job-templates/{id}` (jobs:read) — single template with visibility enforcement
- `PATCH /job-templates/{id}` (jobs:write) — update name/visibility; 403 for non-creator non-admin
- `DELETE /job-templates/{id}` (jobs:write) — hard delete; 403 for non-creator non-admin

### Task 2: Pin/Unpin, Retention Config, CSV Export (SRCH-08, SRCH-09, SRCH-10)

Added to `models.py`:
- `RetentionConfigUpdate` Pydantic model (retention_days: int)

Added to `main.py`:
- `EXEC_CSV_HEADERS` constant (9 columns: job_guid, node_id, status, exit_code, started_at, completed_at, duration_s, attempt_number, pinned)
- `PATCH /executions/{id}/pin` (jobs:write) — sets pinned=True + writes audit log
- `PATCH /executions/{id}/unpin` (jobs:write) — sets pinned=False + writes audit log
- `GET /admin/retention` (users:write) — returns retention_days + eligible_count + pinned_count
- `PATCH /admin/retention` (users:write) — upserts execution_retention_days in Config table
- `GET /jobs/{guid}/executions/export` (jobs:read) — streams CSV of all execution records for a job

## Tests

All 5 tests pass:

| Test | File | Covers |
|------|------|--------|
| test_create_template | test_job_templates.py | POST /job-templates, signing field stripping |
| test_template_visibility | test_job_templates.py | private/shared visibility enforcement |
| test_pruner_respects_pinned | test_retention.py | prune_execution_history skips pinned records |
| test_pin_unpin | test_retention.py | PATCH pin/unpin sets flag correctly |
| test_csv_export | test_execution_export.py | CSV headers and content-type correct |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] SQLAlchemy ORM User cannot be instantiated via __new__**
- **Found during:** Task 1 GREEN phase (first test run)
- **Issue:** `User.__new__(User)` raised `AttributeError: 'NoneType' object has no attribute 'set'` because SQLAlchemy mapped columns require an instrumented instance
- **Fix:** Replaced with `types.SimpleNamespace(username=..., role=..., token_version=0)` — a plain Python namespace that satisfies all attribute accesses in the route handlers
- **Files modified:** `puppeteer/tests/test_job_templates.py`
- **Commit:** c3dd35c

## Self-Check: PASSED

All files exist:
- puppeteer/agent_service/models.py — FOUND
- puppeteer/agent_service/main.py — FOUND
- puppeteer/tests/test_job_templates.py — FOUND
- puppeteer/tests/test_retention.py — FOUND
- puppeteer/tests/test_execution_export.py — FOUND

All commits exist:
- c3dd35c: feat(53-04): implement job templates CRUD routes and passing tests — FOUND
- 52c3c48: feat(53-04): implement pin/unpin, retention config, CSV export with passing tests — FOUND
