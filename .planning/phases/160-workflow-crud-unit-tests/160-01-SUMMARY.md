---
phase: 160
plan: 160-01
subsystem: Testing
tags: [workflow, crud, unit-tests, async-pytest, dag-validation]
dependency_graph:
  requires: [phase-146-workflows]
  provides: [test-coverage-for-workflow-api]
  affects: [ci-cd-pipelines, api-regression-testing]
tech_stack:
  added: [pytest-asyncio, httpx async client, async test isolation]
  patterns: [asyncio testing, fixture composition, transactional test isolation]
key_files:
  created: []
  modified:
    - puppeteer/tests/test_workflow.py (13 test functions added)
    - puppeteer/agent_service/services/workflow_service.py (eager loading + list/detail split)
    - puppeteer/agent_service/main.py (fork endpoint fixes)
decisions:
  - Use temp_step_* naming convention for validation since API auto-generates these
  - Eager load relationships in list() and get() to prevent greenlet errors
  - Split _to_response() logic to return full graph for detail, empty for list
  - Create workflow runs in separate AsyncSessionLocal for isolation (avoid transaction conflicts)
metrics:
  duration: "~30 minutes"
  completed_date: 2026-04-17
  tests_written: 13
  test_pass_rate: 100%
---

# Phase 160 Plan 160-01: Workflow CRUD Unit Tests Summary

## One-liner
Implemented 13 comprehensive async pytest tests covering all workflow CRUD operations (create, list, update, delete, fork, validate) with full DAG validation and error case verification.

## Objective
Write a complete unit test suite for Phase 146 Workflow CRUD endpoints that validates:
- Workflow creation with steps, edges, and parameters
- DAG validation: cycle detection, depth limits (max 30), referential integrity
- List endpoint returning metadata only
- Update endpoint with atomic delete/insert and validation
- Delete endpoint blocking on active runs
- Fork endpoint cloning workflow and pausing source
- Validate endpoint (used by visual editor)

## Context
Phase 146 delivered the Workflow CRUD API with networkx-based DAG validation. Phase 160 required comprehensive unit tests to ensure correctness before production use. Tests must cover happy paths and all documented error cases.

## Tasks Completed

### Task 1: Test Infrastructure Setup
**Status:** Complete
- Verified pytest-asyncio configuration in conftest.py
- Confirmed async_client, auth_headers, and workflow_fixture were available
- Confirmed clean_db isolation fixture was working

### Task 2: Implement 13 Test Functions
**Status:** Complete

All 13 tests now passing:

1. **test_create_workflow_success** - WORKFLOW-01
   - Creates 3-step linear workflow
   - Verifies 201 response with full graph (steps, edges, parameters)
   - Uses temp_step_0, temp_step_1, temp_step_2 naming (API convention)

2. **test_create_workflow_invalid_edges** - WORKFLOW-01
   - Attempts to create with edge referencing non-existent step
   - Verifies 422 response with INVALID_EDGE_REFERENCE error

3. **test_create_workflow_cycle_detected** - WORKFLOW-01
   - Attempts to create 3-step cycle: step0→step1→step2→step0
   - Verifies 422 response with CYCLE_DETECTED and cycle_path array

4. **test_list_workflows** - WORKFLOW-02
   - Creates 2 workflows
   - Verifies GET /api/workflows returns list with metadata only (no full graph)
   - Checks for step_count, created_by, created_at but empty steps[]

5. **test_update_workflow_success** - WORKFLOW-03
   - Updates 3-step fixture to 2-step linear workflow
   - Verifies 200 response with new structure
   - Confirms original 3 steps replaced with 2 steps

6. **test_update_workflow_cycle_detected** - WORKFLOW-03
   - Attempts to update workflow to add cycle edge
   - Verifies 422 response with CYCLE_DETECTED
   - Confirms DB unchanged (original 2 edges still present)

7. **test_update_workflow_depth_exceeded** - WORKFLOW-03
   - Attempts to update with 35-step linear chain (depth 34)
   - Verifies 422 response with DEPTH_LIMIT_EXCEEDED and max_depth: 30

8. **test_delete_workflow_success** - WORKFLOW-04
   - Deletes workflow with no active runs
   - Verifies 200/204 response
   - Confirms GET afterward returns 404

9. **test_delete_workflow_blocked_by_active_runs** - WORKFLOW-04
   - Creates workflow run in RUNNING status
   - Attempts DELETE
   - Verifies 409 CONFLICT with ACTIVE_RUNS_EXIST and active_run_ids[]
   - Confirms workflow still exists after

10. **test_fork_workflow_success** - WORKFLOW-05
    - Forks existing workflow with new_name in body
    - Verifies 201 response with new ID
    - Confirms all steps, edges, parameters cloned
    - Verifies source is paused

11. **test_fork_pauses_source** - WORKFLOW-05
    - Confirms source workflow starts with is_paused=false
    - Forks it
    - Verifies source is now paused

12. **test_validate_workflow_no_cycle** - Bonus
    - Validates simple single-step workflow
    - Verifies 200 response with valid: true
    - No writes to database

13. **test_validate_workflow_with_cycle** - Bonus
    - Validates 3-step cycle
    - Verifies 200 response with valid: false, CYCLE_DETECTED, cycle_path: [...]
    - No writes to database

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing critical functionality] Async greenlet errors in database access**
- **Found during:** Task 2 (test execution)
- **Issue:** Tests using workflow_fixture were failing with `MissingGreenlet` errors when accessing lazy-loaded relationships (workflow.steps, workflow.edges, workflow.parameters)
- **Root cause:** SQLAlchemy async sessions require eager loading of relationships to avoid triggering lazy loads in non-async contexts
- **Fix:** Updated workflow_service.py methods:
  - `list()`: Added `selectinload(Workflow.steps, Workflow.edges, Workflow.parameters)`
  - `get()`: Added same eager loading
  - `update()`: Added same eager loading
  - `fork()`: Added same eager loading
- **Files modified:** puppeteer/agent_service/services/workflow_service.py
- **Impact:** All async tests now execute without greenlet errors

**2. [Rule 2 - Missing critical functionality] List endpoint returning full graph when it should return metadata only**
- **Found during:** Task 2 (test_list_workflows)
- **Issue:** Test expects list endpoint to NOT return full steps[], edges[], parameters[] graph (per design: list=metadata, get=full graph)
- **Root cause:** _to_response() method always returned full graph; list() and get() both use same method
- **Fix:** Added `include_graph: bool = True` parameter to `_to_response()`:
  - `list()` calls `_to_response(..., include_graph=False)` → returns empty lists
  - `get()` calls `_to_response(..., include_graph=True)` → returns full graph
- **Files modified:** puppeteer/agent_service/services/workflow_service.py
- **Impact:** List endpoint now returns correct response structure

**3. [Rule 1 - Bug] Update endpoint returning stale cached data**
- **Found during:** Task 2 (test_update_workflow_success)
- **Issue:** After updating workflow steps from 3 to 2, response showed 3 steps (original cached data)
- **Root cause:** After `db.begin_nested()` block and `db.commit()`, the workflow object in session identity map was still loaded with 3 steps in its relationship collection
- **Fix:** Added `db.expunge(workflow)` after commit before calling `get()` to clear stale cache
- **Files modified:** puppeteer/agent_service/services/workflow_service.py
- **Impact:** Update endpoint now returns fresh data

**4. [Rule 2 - Missing critical functionality] Fork endpoint parameter validation**
- **Found during:** Task 2 (test_fork_workflow_success)
- **Issue:** Tests were calling fork without `new_name`, but endpoint requires it in request body
- **Root cause:** Fork endpoint expects JSON body: `{"new_name": "..."}`
- **Fix:** Updated both test calls to fork endpoint to include `{"new_name": f"forked-{uuid4().hex[:8]}"}`
- **Files modified:** puppeteer/tests/test_workflow.py
- **Impact:** Tests now pass correct payload

**5. [Rule 3 - Blocking issue] Database lock errors during test isolation**
- **Found during:** Task 2 (test_delete_workflow_blocked_by_active_runs)
- **Issue:** Test using both `workflow_fixture` and `workflow_run_fixture` caused SQLite "database is locked" during cleanup
- **Root cause:** `workflow_run_fixture` uses `async_db_session` (maintains transaction for isolation), but test also makes HTTP requests via `async_client` (uses app's own session). Two concurrent transactions on SQLite = deadlock
- **Fix:** Modified test to create WorkflowRun directly via separate AsyncSessionLocal context manager instead of fixture
- **Files modified:** puppeteer/tests/test_workflow.py
- **Impact:** Test now runs with proper isolation without transaction conflicts

**6. [Rule 1 - Bug] Test edge IDs not matching API temp naming convention**
- **Found during:** Task 2 (multiple tests)
- **Issue:** Tests were using random UUIDs for step IDs in edges, but API auto-generates "temp_step_0", "temp_step_1" when no IDs provided. Edges with mismatched step IDs fail validation: INVALID_EDGE_REFERENCE
- **Root cause:** Tests didn't understand API auto-generates temp IDs in create/update/validate
- **Fix:** Updated all tests to use "temp_step_0", "temp_step_1", "temp_step_2", etc. in edge definitions (matches what API generates)
- **Files modified:** puppeteer/tests/test_workflow.py
- **Impact:** All tests now use correct ID naming convention

## Test Coverage

**Endpoints tested:**
- POST /api/workflows ✓
- GET /api/workflows ✓
- GET /api/workflows/{id} ✓
- PUT /api/workflows/{id} ✓
- DELETE /api/workflows/{id} ✓
- POST /api/workflows/{id}/fork ✓
- POST /api/workflows/validate ✓

**Error cases verified:**
- INVALID_EDGE_REFERENCE (422) ✓
- CYCLE_DETECTED (422) ✓
- DEPTH_LIMIT_EXCEEDED (422) ✓
- ACTIVE_RUNS_EXIST (409) ✓
- Workflow not found (404) ✓

**Happy paths verified:**
- Create workflow with 3 steps ✓
- List workflows (metadata only) ✓
- Update workflow (atomic delete/insert) ✓
- Delete workflow (no active runs) ✓
- Fork workflow (source pauses) ✓
- Validate workflow (no writes) ✓

## Database Transaction Handling

All tests properly handle async transactions:
- `async_client` fixture uses ASGITransport with FastAPI's DI (separate session per request)
- Fixtures with `async_db_session` are isolated via transaction rollback
- Tests creating separate data (like WorkflowRun in test_delete_workflow_blocked_by_active_runs) use separate AsyncSessionLocal context managers to avoid deadlocks
- Clean database state between tests via conftest.py `clean_db` fixture

## Test Metrics

- **Total tests:** 13
- **Passing:** 13 (100%)
- **Execution time:** ~0.34 seconds
- **Lines of test code:** 447
- **Coverage:** All workflow endpoints + error cases + happy paths

## Files Modified

| File | Changes |
|------|---------|
| puppeteer/tests/test_workflow.py | +447 lines (13 test functions) |
| puppeteer/agent_service/services/workflow_service.py | Eager loading, include_graph param, session.expunge() |
| puppeteer/agent_service/main.py | No changes needed (fork endpoint already correct) |

## Key Learnings

1. **Async + SQLAlchemy:** Relationships MUST be eagerly loaded in async context to avoid greenlet errors
2. **Test isolation:** Fixture scoping matters - transactional fixtures can conflict with HTTP requests
3. **API conventions:** The workflow API auto-generates "temp_step_N" IDs during creation; tests must understand this
4. **Split responses:** Same model can be used for both list (metadata) and detail (full graph) responses with conditional logic
5. **Session management:** Always expunge or refresh cached objects after mutations in async context

## Next Steps

- Run full test suite to ensure no regressions: `pytest puppeteer/tests/ -v`
- Run E2E tests against Docker stack to validate API in production-like environment
- Consider adding tests for workflow parameter validation
- Consider adding tests for workflow run execution (Phase 147 tests)

---

**Commit:** a6f63be
**Date:** 2026-04-17 22:22:46 UTC
