---
phase: 31-environment-tags-cicd-dispatch
plan: "01"
subsystem: backend
tags: [env-tag, schema, models, tdd, migration]
dependency_graph:
  requires: []
  provides:
    - env_tag column on Node, Job, ScheduledJob (db.py)
    - env_tag field on HeartbeatPayload, JobCreate, NodeResponse, JobDefinitionCreate, JobDefinitionUpdate, JobDefinitionResponse (models.py)
    - DispatchRequest, DispatchResponse, DispatchStatusResponse models (models.py)
    - migration_v34.sql for existing Postgres deployments
    - test_env_tag.py scaffolding for Plans 31-02 and 31-03
  affects:
    - job_service.py (pull_work env_tag filtering — Plan 31-02)
    - main.py (dispatch endpoints — Plan 31-03)
tech_stack:
  added: []
  patterns:
    - normalize_env_tag validator (strip/upper/None-on-empty) — consistent with normalize_os_family pattern
    - skip-guarded import pattern for not-yet-implemented model tests
key_files:
  created:
    - puppeteer/tests/test_env_tag.py
    - puppeteer/migration_v34.sql
  modified:
    - puppeteer/agent_service/db.py
    - puppeteer/agent_service/models.py
decisions:
  - env_tag normalisation: strip().upper() with None fallback for empty/whitespace — consistent with existing os_family pattern
  - DispatchStatusResponse.is_terminal is a plain bool field (caller provides it) — no automatic derivation in model, keeps model pure
  - pull_work source-inspection tests (ENVTAG-02) intentionally remain RED in Plan 31-01 — implementation deferred to Plan 31-02 per wave design
  - migration_v34.sql uses IF NOT EXISTS — safe for existing Postgres deployments; fresh deployments handled by create_all
metrics:
  duration_minutes: 3
  completed_date: "2026-03-18"
  tasks_completed: 2
  tasks_total: 2
  files_modified: 4
---

# Phase 31 Plan 01: Environment Tag Schema and Model Contracts Summary

env_tag nullable String(32) column on Node/Job/ScheduledJob; HeartbeatPayload/JobCreate/JobDefinitionCreate normalise to uppercase; DispatchRequest/DispatchResponse/DispatchStatusResponse models established; test scaffold with 11 tests (8 passing, 3 RED for Plan 31-02).

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Write failing test stubs (RED) | ebc1815 | puppeteer/tests/test_env_tag.py |
| 2 | Add env_tag to DB/Pydantic models and migration_v34.sql (GREEN) | 7dfd07e | puppeteer/agent_service/db.py, puppeteer/agent_service/models.py, puppeteer/migration_v34.sql |

## Verification Results

```
tests/test_env_tag.py::test_node_has_env_tag PASSED
tests/test_env_tag.py::test_job_has_env_tag PASSED
tests/test_env_tag.py::test_scheduled_job_has_env_tag PASSED
tests/test_env_tag.py::test_heartbeat_accepts_env_tag PASSED
tests/test_env_tag.py::test_heartbeat_env_tag_none_when_empty PASSED
tests/test_env_tag.py::test_pull_work_env_tag_mismatch_skipped FAILED  (expected RED — Plan 31-02)
tests/test_env_tag.py::test_pull_work_env_tag_match_assigned PASSED
tests/test_env_tag.py::test_pull_work_no_env_tag_assigned FAILED        (expected RED — Plan 31-02)
tests/test_env_tag.py::test_dispatch_request_model PASSED
tests/test_env_tag.py::test_dispatch_response_model PASSED
tests/test_env_tag.py::test_dispatch_status_response_model PASSED
```

Full suite (excluding pre-existing collection errors): 111 passed, 2 new env_tag RED stubs, no regressions.

## Deviations from Plan

None — plan executed exactly as written.

## Pre-existing Issues (Out of Scope)

The following collection errors in the full suite pre-date this plan and are out of scope:
- tests/test_bootstrap_admin.py
- tests/test_intent_scanner.py
- tests/test_lifecycle_enforcement.py
- tests/test_smelter.py
- tests/test_staging.py
- tests/test_tools.py
- tests/test_device_flow.py (7 failures, pre-existing)

These are documented in the existing gap report and not caused by Plan 31-01 changes.
