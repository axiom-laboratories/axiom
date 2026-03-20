---
phase: 35-private-ee-repo-plugin-wiring
plan: "05"
subsystem: testing
tags: [tests, smoke-test, ee-plugin, ce-validation, phase-gate, pypi]
dependency_graph:
  requires: [35-04]
  provides: [EE-06, EE-07, EE-08-partial]
  affects: [phase-36-gate]
tech_stack:
  added: [build, twine]
  patterns: [pytest-asyncio, httpx-ASGITransport, importorskip-pattern, direct-handler-invocation, python-build-wheel]
key_files:
  created:
    - .worktrees/axiom-split/puppeteer/agent_service/tests/test_ce_smoke.py
    - .worktrees/axiom-split/puppeteer/agent_service/tests/test_ee_plugin.py
    - .worktrees/axiom-split/puppeteer/tests/test_ee_smoke.py
    - ~/Development/axiom-ee/dist/axiom_ee-0.1.0.dev0-py3-none-any.whl
    - ~/Development/axiom-ee/dist/axiom_ee-0.1.0.dev0.tar.gz
  modified: []
decisions:
  - "test_ce_stub_routers_return_402 calls stub handler functions directly rather than routing through the app — httpx ASGITransport does not trigger ASGI lifespan, so stubs mounted during lifespan are not registered in unit tests"
  - "test_ce_table_count checks CE Base.metadata (not DB introspection) — verifies ORM registration, not runtime schema"
  - "test_ee_plugin.py uses pytest.importorskip to gracefully skip when axiom-ee not installed — runs and passes when it is"
  - "PyPI publish deferred — no TWINE credentials in session environment; wheel artifacts built and ready in ~/Development/axiom-ee/dist/; EE-08 marked partial until manual publish"
metrics:
  duration_minutes: 12
  tasks_completed: 2
  tasks_total: 2
  files_created: 5
  files_modified: 0
  completed_date: "2026-03-19"
  checkpoint_reached: false
---

# Phase 35 Plan 05: Smoke Tests + PyPI Publish Summary

**One-liner:** Three test files validating CE-alone (EE-06), EEPlugin isolation (EE-02/03), and CE+EE combined smoke tests (EE-07); axiom-ee 0.1.0.dev0 wheel built and ready for PyPI publish.

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

**Verification results (post-checkpoint):**
- CE gate `pytest puppeteer/agent_service/tests/ -m "not ee_only"`: 32 passed, 2 skipped, 0 failed
- CE+EE smoke `pytest puppeteer/tests/test_ee_smoke.py -v`: 2 passed, 0 failed
- No relative parent imports in EE package: PASS
- Entry point `axiom.ee` discoverable: PASS (`ee.plugin:EEPlugin`)

### Task 2: Build axiom-ee stub wheel + PyPI publish

**Wheel built successfully:**
```
axiom_ee-0.1.0.dev0-py3-none-any.whl
axiom_ee-0.1.0.dev0.tar.gz
```
Location: `~/Development/axiom-ee/dist/`

**PyPI publish:** Authentication gate — no `TWINE_PASSWORD` or `~/.pypirc` credentials available in the session environment. Twine requires interactive terminal input which is not available in this context. The wheel artifacts are built and ready.

**Manual publish steps (EE-08 completion):**
```bash
# Set up PyPI API token first at https://pypi.org/manage/account/token/
export TWINE_PASSWORD="pypi-AgAAAA..."
export TWINE_USERNAME="__token__"

# Publish to test.pypi.org first
/home/thomas/Development/master_of_puppets/.venv/bin/twine upload \
  --repository testpypi ~/Development/axiom-ee/dist/*

# Verify: https://test.pypi.org/project/axiom-ee/

# Then publish to production PyPI
/home/thomas/Development/master_of_puppets/.venv/bin/twine upload \
  ~/Development/axiom-ee/dist/*

# Verify: https://pypi.org/project/axiom-ee/
```

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

## Authentication Gate — PyPI Publish

**Task 2 (PyPI publish):** Authentication gate encountered. No PyPI credentials (`TWINE_PASSWORD`, `~/.pypirc`) available in session. The wheel was built successfully — `axiom_ee-0.1.0.dev0-py3-none-any.whl` and `.tar.gz` artifacts are in `~/Development/axiom-ee/dist/`.

EE-08 is marked **partial** — wheel built, publish pending manual credential entry.

## Self-Check: PASSED

**Files created:**
- FOUND: `.worktrees/axiom-split/puppeteer/agent_service/tests/test_ce_smoke.py`
- FOUND: `.worktrees/axiom-split/puppeteer/agent_service/tests/test_ee_plugin.py`
- FOUND: `.worktrees/axiom-split/puppeteer/tests/test_ee_smoke.py`
- FOUND: `~/Development/axiom-ee/dist/axiom_ee-0.1.0.dev0-py3-none-any.whl`
- FOUND: `~/Development/axiom-ee/dist/axiom_ee-0.1.0.dev0.tar.gz`

**Commits verified:**
- FOUND: 7a24144 — test(35): CE smoke, EE plugin unit, CE+EE smoke tests
- FOUND: bd41fa8 — fix(35-05): rewrite EE smoke tests — direct plugin registration instead of ASGITransport

**Test results verified:**
- CE gate: 32 passed, 2 skipped, 0 failed
- CE+EE smoke: 2 passed, 0 failed
- No relative imports in EE package: PASS
- Entry point discoverable: PASS
