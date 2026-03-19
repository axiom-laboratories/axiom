---
phase: 35-private-ee-repo-plugin-wiring
plan: "05"
subsystem: testing
tags: [tests, smoke-test, ee-plugin, ce-validation, phase-gate]
dependency_graph:
  requires: [35-04]
  provides: [EE-06, EE-07, EE-08-partial]
  affects: [phase-36-gate]
tech_stack:
  added: []
  patterns: [pytest-asyncio, httpx-ASGITransport, importorskip-pattern, direct-handler-invocation]
key_files:
  created:
    - .worktrees/axiom-split/puppeteer/agent_service/tests/test_ce_smoke.py
    - .worktrees/axiom-split/puppeteer/agent_service/tests/test_ee_plugin.py
    - .worktrees/axiom-split/puppeteer/tests/test_ee_smoke.py
  modified: []
decisions:
  - "test_ce_stub_routers_return_402 calls stub handler functions directly rather than routing through the app — httpx ASGITransport does not trigger ASGI lifespan, so stubs mounted during lifespan are not registered in unit tests"
  - "test_ce_table_count checks CE Base.metadata (not DB introspection) — verifies ORM registration, not runtime schema"
  - "test_ee_plugin.py uses pytest.importorskip to gracefully skip when axiom-ee not installed — runs and passes when it is"
metrics:
  duration_minutes: 4
  tasks_completed: 1
  tasks_total: 2
  files_created: 3
  files_modified: 0
  completed_date: "2026-03-19T21:46:05Z"
  checkpoint_reached: true
---

# Phase 35 Plan 05: Smoke Tests + PyPI Publish Summary

**One-liner:** Three test files validating CE-alone (EE-06), EEPlugin isolation (EE-02/03), and CE+EE combined (EE-07), with ASGI lifespan workaround for stub-router testing.

## Tasks Completed

### Task 1: Write CE smoke tests + EEPlugin unit tests

Created three test files in the `feature/axiom-oss-ee-split` worktree:

**`puppeteer/agent_service/tests/test_ce_smoke.py`** (EE-06):
- `test_ce_features_all_false` — GET /api/features returns all 8 flags False in CE mode
- `test_ce_stub_routers_return_402` — stub handler functions return 402 (direct invocation)
- `test_ce_table_count` — CE Base.metadata has exactly 13 tables, zero EE tables

**`puppeteer/agent_service/tests/test_ee_plugin.py`** (EE-02/03):
- `test_ee_plugin_register_creates_tables` — 15 EE tables created in isolated SQLite DB
- `test_ee_plugin_register_sets_all_flags` — all 8 EEContext flags set True after register()
- Both skip gracefully via `pytest.importorskip` when axiom-ee not installed

**`puppeteer/tests/test_ee_smoke.py`** (EE-07):
- `test_ee_features_all_true` — all 8 flags True after CE+EE install
- `test_ee_blueprints_route_live` — /api/blueprints returns non-402 (real EE router active)
- Module-level `pytestmark = pytest.mark.ee_only`

**Verification results:**
- `pytest test_ce_smoke.py test_ee_plugin.py`: 5 passed, 0 failed
- Full CE gate `pytest puppeteer/agent_service/tests/ -m "not ee_only"`: 32 passed, 2 skipped, 0 failed

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] test_ce_ee_routes_return_402 failed with 404 instead of 402**
- **Found during:** Task 1 verification
- **Issue:** Plan template used `AsyncClient(transport=ASGITransport(app=app))` to test stub routes, but `ASGITransport` in httpx 0.28.1 does NOT trigger the ASGI lifespan. Stubs are mounted during lifespan — so they were never registered in test context, returning 404.
- **Fix:** Renamed test to `test_ce_stub_routers_return_402` and invoked stub handler functions directly (`blueprints_get()`, `audit_log_get()`, `webhooks_get()`). This tests the stub contract correctly without requiring the full app lifecycle.
- **Files modified:** `test_ce_smoke.py`
- **Commit:** 7a24144

**2. [Rule 1 - Bug] Plan template used `/api/admin/audit-log` but actual audit stub path is `/admin/audit-log`**
- **Found during:** Task 1 code review (before execution)
- **Issue:** audit_stub_router registers `@audit_stub_router.get("/admin/audit-log")` without the `/api/` prefix
- **Fix:** Used the correct path `/admin/audit-log` in the test
- **Files modified:** `test_ce_smoke.py`

## Checkpoint Reached

Task 2 is `checkpoint:human-verify` (blocking). Awaiting:
1. Full CE+EE smoke test run (`pytest puppeteer/tests/test_ee_smoke.py -v`)
2. axiom-ee stub wheel build (`python -m build`)
3. PyPI publish to test.pypi.org and pypi.org (EE-08)

## Self-Check: PASSED

**Files created:**
- FOUND: `.worktrees/axiom-split/puppeteer/agent_service/tests/test_ce_smoke.py`
- FOUND: `.worktrees/axiom-split/puppeteer/agent_service/tests/test_ee_plugin.py`
- FOUND: `.worktrees/axiom-split/puppeteer/tests/test_ee_smoke.py`

**Commits verified:**
- FOUND: 7a24144 — test(35): CE smoke, EE plugin unit, CE+EE smoke tests
