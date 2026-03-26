---
phase: 66-backend-code-fixes
plan: "02"
subsystem: backend-ee
tags: [ce-gating, execution-history, ee-plugin, fastapi]
dependency_graph:
  requires: []
  provides: [CODE-04]
  affects: [ee/__init__.py, main.py, ee/interfaces/executions.py, ee/routers/executions_router.py]
tech_stack:
  added: []
  patterns: [CE-stub-router, EE-plugin-router, EEContext-flag]
key_files:
  created:
    - puppeteer/agent_service/ee/interfaces/executions.py
    - puppeteer/agent_service/ee/routers/executions_router.py
  modified:
    - puppeteer/agent_service/ee/__init__.py
    - puppeteer/agent_service/main.py
    - puppeteer/agent_service/tests/test_ce_smoke.py
decisions:
  - "stub handlers with path parameters tested with dummy args (id=1, guid='test') rather than no-arg call"
  - "executions flag added to /api/features endpoint fallback dict and ctx response path"
metrics:
  duration_minutes: 10
  tasks_completed: 2
  tasks_total: 2
  files_changed: 5
  completed_at: "2026-03-25T21:59:44Z"
requirements_closed: [CODE-04]
---

# Phase 66 Plan 02: CE-gate Execution History Routes Summary

CE-gated all 7 execution-history API routes with 402-returning stubs; moved real implementations to EE router file; fixed pre-existing test_ce_table_count assertion (13 -> 15).

## What Was Built

### Task 1: CE stub + EE router files

`ee/interfaces/executions.py` — `execution_stub_router` with 7 stub handlers, each returning HTTP 402 with the standard EE upgrade message. Handler names are unique and use `_stub` suffix.

`ee/routers/executions_router.py` — `executions_router` with all 7 real implementations moved verbatim from `main.py`. Per-job handler renamed `list_job_executions` (was `list_executions`) to resolve the duplicate function name that existed in main.py.

### Task 2: Wire, remove, test

`ee/__init__.py`:
- `executions: bool = False` added to `EEContext` dataclass
- `execution_stub_router` imported and mounted in `_mount_ce_stubs()`
- Logger updated: "mounted 7 stub routers"

`main.py`:
- All 7 execution routes removed (3 in the Execution History block, 1 per-job executions handler, 2 pin/unpin, 1 CSV export)
- `executions` key added to `/api/features` response (both fallback dict and ctx path)

`test_ce_smoke.py`:
- `"executions"` added to `ee_flags` list in `test_ce_features_all_false`
- All 7 stub handlers asserted to return 402 in `test_ce_stub_routers_return_402`
- Table count corrected: `assert len(ce_tables) == 15` (was 13)

## Test Results

```
agent_service/tests/test_ce_smoke.py::test_ce_features_all_false  PASSED
agent_service/tests/test_ce_smoke.py::test_ce_stub_routers_return_402  PASSED
agent_service/tests/test_ce_smoke.py::test_ce_table_count  PASSED
```

Full suite: 69 passed, 2 skipped, 11 pre-existing failures (EE plugin tests + model/job_service tests unrelated to this plan).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing] /api/features endpoint missing executions flag**
- **Found during:** Task 2 test run
- **Issue:** `test_ce_features_all_false` failed because GET /api/features didn't include `executions` in the response. The plan specified updating `EEContext` and `_mount_ce_stubs` but didn't explicitly call out the features endpoint.
- **Fix:** Added `"executions": False` to the fallback dict and `"executions": ctx.executions` to the ctx response in `main.py`.
- **Files modified:** `puppeteer/agent_service/main.py`
- **Commit:** ed8e666

**2. [Rule 1 - Bug] Path-param stub handlers called with no args in test**
- **Found during:** Task 2 test authoring
- **Issue:** The plan suggested a simple `for handler in (...): await handler()` loop, but handlers with path parameters (`id: int`, `exec_id: int`, `guid: str`) cannot be called with no arguments.
- **Fix:** Split the test loop — no-param handlers in the for loop, path-param handlers tested individually with dummy values.
- **Files modified:** `puppeteer/agent_service/tests/test_ce_smoke.py`
- **Commit:** ed8e666

## Self-Check: PASSED

- FOUND: `puppeteer/agent_service/ee/interfaces/executions.py`
- FOUND: `puppeteer/agent_service/ee/routers/executions_router.py`
- FOUND: `.planning/phases/66-backend-code-fixes/66-02-SUMMARY.md`
- FOUND commit: 20410b9 (Task 1)
- FOUND commit: ed8e666 (Task 2)
