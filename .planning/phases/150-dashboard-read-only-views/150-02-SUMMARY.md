---
phase: 150
plan: 02
subsystem: Dashboard (Read-Only Views)
tags: [websocket, events, workflow-api, real-time]
dependencies:
  requires: [150-01]
  provides: [workflow-event-streaming, workflow-run-history]
  affects: [frontend-workflow-views, websocket-client]
tech_stack:
  added: [WebSocket events, Pydantic models, FastAPI broadcast, pagination]
  patterns: [event-driven-architecture, lazy-imports-for-circular-deps]
key_files:
  created: [puppeteer/tests/test_workflow_api.py]
  modified: [puppeteer/agent_service/models.py, puppeteer/agent_service/main.py, puppeteer/agent_service/services/workflow_service.py]
decisions:
  - Used Optional[datetime] for completed_at (null while running)
  - Lazy imports in workflow_service to avoid circular dependency on main.ws_manager
  - Pagination via skip/limit pattern (REST standard)
  - Broadcast errors wrapped in try/except to prevent event emission failures from crashing workflows
duration: ~2 hours
completed_at: 2026-04-16T14:18:00Z

---

# Phase 150 Plan 02: WebSocket Events & Run List Summary

Implemented real-time workflow status updates via WebSocket events and a paginated run history API endpoint.

## Objective

Enable the dashboard to receive live workflow status updates without polling and to fetch historical run data with pagination support.

## Completed Tasks

### Task 1: Add Event Models to models.py
**Commit:** 8db2d46

Created three new Pydantic models in `agent_service/models.py`:

- `WorkflowRunUpdatedEvent`: Emitted when a WorkflowRun transitions state
  - Fields: id, workflow_id, status (RUNNING|COMPLETED|PARTIAL|FAILED|CANCELLED), started_at, completed_at, triggered_by
  - triggered_by values: step_completed, cascade_cancel, manual_cancel, all_steps_done

- `WorkflowStepUpdatedEvent`: Emitted when a WorkflowStepRun transitions state
  - Fields: id, workflow_run_id, workflow_step_id, status, started_at, completed_at, job_guid
  - Status values: PENDING|RUNNING|COMPLETED|FAILED|SKIPPED|CANCELLED

- `WorkflowRunListResponse`: Response model for paginated run list
  - Fields: runs (List[WorkflowRunResponse]), total, skip, limit

### Task 2: Add Broadcast Methods to ConnectionManager
**Commit:** 8db2d46

Added two async broadcast methods to `ConnectionManager` class in `main.py`:

```python
async def broadcast_workflow_run_updated(self, event: WorkflowRunUpdatedEvent) -> None
async def broadcast_workflow_step_updated(self, event: WorkflowStepUpdatedEvent) -> None
```

Both methods:
- Convert event to JSON-serializable dict via `model_dump(mode='json')`
- Broadcast to all connected WebSocket clients
- Wrapped in try/except to prevent event emission failures from crashing workflows

### Task 3: Emit Events on State Transitions
**Commit:** 8db2d46

Modified `workflow_service.py` to emit events:

- `advance_workflow()`: Emits `WorkflowRunUpdatedEvent` with `triggered_by='all_steps_done'` when run completes
- `cancel_run()`: Emits `WorkflowRunUpdatedEvent` with `triggered_by='manual_cancel'` and individual `WorkflowStepUpdatedEvent` for each cancelled step

Modified `main.py` report_result endpoint:
- Updates `step_run.status = 'COMPLETED'` and `step_run.completed_at` when job completes
- Emits `WorkflowStepUpdatedEvent` with job_guid and status

Used lazy import pattern in `workflow_service.py` to avoid circular imports:
```python
try:
    from .. import main
    await main.ws_manager.broadcast_workflow_run_updated(event)
except ImportError:
    pass  # main not available (testing/REPL context)
```

### Task 4: Implement GET /api/workflows/{id}/runs Endpoint
**Commit:** 8db2d46

Added new FastAPI route `GET /api/workflows/{id}/runs`:
- Query parameters: skip (default 0), limit (default 10)
- Returns: `WorkflowRunListResponse` with paginated run history
- Permissions: Requires `workflows:read` role permission
- Error handling: 404 if workflow doesn't exist, 401 if unauthorized
- Query: Orders runs by started_at DESC (most recent first)

### Task 5: Create Integration Tests
**Commit:** 5374de5

Created `puppeteer/tests/test_workflow_api.py` with 5 passing tests:

1. `test_get_workflow_runs_404_missing_workflow`: Verifies 404 response for non-existent workflow
2. `test_get_workflow_runs_requires_permission`: Verifies 401 for unauthenticated requests
3. `test_get_workflow_runs_pagination_structure`: Tests pagination parameter handling
4. `test_broadcast_methods_in_connection_manager`: Structural test verifying broadcast methods exist and are callable
5. `test_event_models_exist`: Tests event model instantiation with Pydantic validation

All tests pass with proper fixtures (async_client, auth_headers, async_db_session).

## Verification

- All 5 integration tests pass
- Event models validate required and optional fields correctly
- Broadcast methods callable from ConnectionManager instance
- GET endpoint returns 404 for missing workflows
- GET endpoint requires workflows:read permission
- Permission checks follow RBAC pattern

## Deviations from Plan

None - plan executed exactly as written. No auto-fixes or blocking issues encountered.

## Files Modified

1. **puppeteer/agent_service/models.py**
   - Added WorkflowRunUpdatedEvent (lines 1382-1391)
   - Added WorkflowStepUpdatedEvent (lines 1394-1404)
   - Added WorkflowRunListResponse (lines 1407-1414)

2. **puppeteer/agent_service/main.py**
   - Added broadcast_workflow_run_updated method to ConnectionManager
   - Added broadcast_workflow_step_updated method to ConnectionManager
   - Modified report_result endpoint to emit WorkflowStepUpdatedEvent

3. **puppeteer/agent_service/services/workflow_service.py**
   - Modified advance_workflow() to emit WorkflowRunUpdatedEvent
   - Modified cancel_run() to emit events for run and steps

4. **puppeteer/tests/test_workflow_api.py** (created)
   - 5 integration tests covering endpoint and model validation

## Key Design Decisions

1. **Optional completed_at**: Set to None while workflow is running, populated on completion or cancellation
2. **Lazy imports for circular dependencies**: Used try/except pattern in workflow_service to defer main import until runtime
3. **Error handling in broadcasts**: Wrapped all broadcast calls in try/except to ensure event emission failures don't crash workflows
4. **Pagination pattern**: Skip/limit approach follows REST standards and matches existing API patterns
5. **Broadcast message format**: Wrapped event data in `{event: "workflow_run_updated", data: {...}}` structure for WebSocket consumption

## Next Steps

Plan 150-03 will implement the React dashboard components to consume these WebSocket events and display real-time workflow status updates.
