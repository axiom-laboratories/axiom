---
phase: 91-output-validation
plan: "03"
subsystem: executions-router
tags: [bug-fix, serialization, output-validation, tdd, gap-closure]
dependency_graph:
  requires: ["91-02"]
  provides: ["VALD-02", "VALD-03"]
  affects: ["executions_router", "test_output_validation"]
tech_stack:
  added: []
  patterns: ["TDD red-green", "mock-based FastAPI test via TestClient"]
key_files:
  created: []
  modified:
    - puppeteer/agent_service/ee/routers/executions_router.py
    - puppeteer/tests/test_output_validation.py
decisions:
  - "Used importlib.util to load executions_router from file path directly, bypassing ee/routers/__init__.py which has a pre-existing Blueprint import error in foundry_router — this avoids touching unrelated code while still exercising the router under test"
  - "Test uses MagicMock for ExecutionRecord and AsyncMock for DB session — no real DB needed for serialization unit test"
metrics:
  duration: "2 minutes"
  completed: "2026-03-30"
  tasks_completed: 1
  files_modified: 2
  commits: 2
---

# Phase 91 Plan 03: Executions Router failure_reason Wiring Summary

**One-liner:** Wired `failure_reason=r.failure_reason` into all three execution response paths in `executions_router.py` to close the serialization gap that always returned `null` for the field despite it being correctly stored in the DB.

## What Was Done

The `ExecutionRecord.failure_reason` column (set by `job_service.process_result()` when a validation rule fails) was never forwarded by the EE executions router. The `ExecutionRecordResponse` Pydantic model already had `failure_reason: Optional[str] = None` — it was simply never populated. Three minimal additions fixed this:

1. **`list_executions()`** (line 99): `failure_reason=r.failure_reason,` added to `ExecutionRecordResponse(...)` constructor after `runtime=job_runtime,`
2. **`get_execution()`** (line 146): `failure_reason=r.failure_reason,` added to the single-record `ExecutionRecordResponse` return after `attestation_verified=r.attestation_verified,`
3. **`list_job_executions()`** (line 225): `"failure_reason": r.failure_reason,` added to the raw dict comprehension after `"attestation_verified": r.attestation_verified,`

A TDD test (`test_failure_reason_serialized_in_list_executions`) was written first (RED), confirmed failing with the correct assertion error, then made green by the implementation.

## Commits

| Hash | Type | Description |
|------|------|-------------|
| 6f8877f | test | RED: failing test for failure_reason serialization |
| 1e5c268 | feat | GREEN: forward failure_reason in all three response paths |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Pre-existing Blueprint import error in ee/routers/__init__.py**
- **Found during:** Writing the test — `import agent_service.ee.routers.executions_router` triggered `__init__.py` which imported `foundry_router` which crashes with `cannot import name 'Blueprint' from 'agent_service.db'`
- **Fix:** Used `importlib.util.spec_from_file_location` to load `executions_router.py` directly from its file path, bypassing `__init__.py` entirely. The pre-existing `foundry_router` error was not touched.
- **Files modified:** `puppeteer/tests/test_output_validation.py` (test import strategy only)
- **Commit:** 6f8877f

## Self-Check: PASSED

Files exist:
- `puppeteer/agent_service/ee/routers/executions_router.py` — modified
- `puppeteer/tests/test_output_validation.py` — modified

Commits exist:
- 6f8877f (test RED)
- 1e5c268 (feat GREEN)

Three wiring points confirmed via `grep`:
- Line 99: `failure_reason=r.failure_reason,` (list_executions)
- Line 146: `failure_reason=r.failure_reason,` (get_execution)
- Line 225: `"failure_reason": r.failure_reason,` (list_job_executions)

All 7 tests in `test_output_validation.py` pass.

Requirements closed: VALD-02, VALD-03. Phase 91 gap fully closed.
