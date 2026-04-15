---
phase: 146-workflow-data-model
plan: 02
type: summary
date_completed: 2026-04-15
duration_minutes: 45
tasks_completed: 3
files_modified: 3
commits: 3
requirements_met:
  - WORKFLOW-01
  - WORKFLOW-02
  - WORKFLOW-03
  - WORKFLOW-04
  - WORKFLOW-05
---

# Phase 146, Plan 02 — ORM Models & Service Layer Summary

## Objective

Implement the data layer and business logic for Workflow management:
- 5 ORM models (Workflow, WorkflowStep, WorkflowEdge, WorkflowParameter, WorkflowRun)
- 11 Pydantic request/response models
- Complete CRUD service with DAG validation (cycle detection, depth calculation)

## Completed Tasks

### Task 1: Add ORM Models to db.py
- **Status:** Complete
- **Commit:** `01fcd35`
- **Changes:**
  - Added `Workflow` table with id, name, created_by, created_at, updated_at, is_paused
  - Added `WorkflowStep` table with workflow_id FK, scheduled_job_id FK, node_type, config_json
  - Added `WorkflowEdge` table with workflow_id FK, from_step_id FK, to_step_id FK, branch_name
  - Added `WorkflowParameter` table with workflow_id FK, name, type, default_value
  - Added `WorkflowRun` table (Phase 147 stub) with workflow_id FK, status, trigger_type, etc.
  - All relationships defined with `back_populates` and cascade deletes
  - All IDs stored as str (UUID format) per project convention

### Task 2: Add Pydantic Models to models.py
- **Status:** Complete
- **Commit:** `79c7e10`
- **Changes:**
  - Added `WorkflowStepCreate` and `WorkflowStepResponse` models
  - Added `WorkflowEdgeCreate` and `WorkflowEdgeResponse` models
  - Added `WorkflowParameterCreate` and `WorkflowParameterResponse` models
  - Added `WorkflowCreate` model (steps[], edges[], parameters[] arrays)
  - Added `WorkflowUpdate` model (all fields optional for atomic replace)
  - Added `WorkflowResponse` model with full graph (steps[], edges[], parameters[])
  - Added `WorkflowValidationError` model with structured error fields
  - All models use `ConfigDict(from_attributes=True)` for ORM conversion

### Task 3: Implement WorkflowService with DAG Validation
- **Status:** Complete
- **Commit:** `f593a82`
- **Changes:**
  - Created `puppeteer/agent_service/services/workflow_service.py` (383 lines)
  - Implemented `validate_dag()` static method:
    - networkx.DiGraph-based cycle detection
    - Depth calculation using dag_longest_path() (max 30 levels)
    - Referential integrity validation (all edges reference valid steps)
  - Implemented `calculate_max_depth()` helper (returns longest path length)
  - Implemented full CRUD methods (all async):
    - `create()` — validates DAG, creates workflow + all steps/edges/params, returns full graph
    - `list()` — returns paginated list with metadata
    - `get()` — returns single workflow with full graph
    - `update()` — atomically deletes/inserts all steps/edges/params, validates DAG
    - `delete()` — checks for active WorkflowRun.status == "RUNNING", raises HTTP 409 if any exist
    - `fork()` — clones all steps/edges/params into new workflow, pauses source (is_paused=true)
  - Implemented `_to_response()` helper:
    - Converts Workflow ORM to WorkflowResponse
    - Includes nested steps[], edges[], parameters[] arrays
    - Queries last WorkflowRun for last_run_status
    - Computes step_count from len(workflow.steps)
  - HTTP error responses:
    - 422 (validation) with `{error, detail, cycle_path?, max_depth?, actual_depth?, edge?}`
    - 409 (conflict) for delete with active runs

## Architecture Decisions

### Data Model
- **Normalized schema** — no definition_json blob; source of truth is workflow_steps + workflow_edges tables
- **Full-graph API contract** — POST/PUT always sends complete steps[], edges[], parameters[] arrays
- **Atomic updates** — using nested transactions for delete/insert atomicity
- **Save-as-New** — fork operation atomically clones and pauses source

### Validation
- **Cycle detection** using networkx library (already in requirements.txt)
- **Depth limit** enforced at 30 levels (override from 10-level default)
- **Referential integrity** checked before save (all edge references validated)
- **Structured errors** with cycle_path, max_depth/actual_depth fields for UI highlighting

### Service Pattern
- All async methods take `db: AsyncSession`
- Validation before any write (HTTPException 422)
- Business logic conflicts return HTTP 409
- ORM → Pydantic conversion via `model_validate()` and `model_dump()`

## Files Modified

| File | Changes | Lines |
|------|---------|-------|
| `puppeteer/agent_service/db.py` | Added 5 ORM classes + List import | +66 |
| `puppeteer/agent_service/models.py` | Added 11 Pydantic models | +110 |
| `puppeteer/agent_service/services/workflow_service.py` | New file, complete service | +383 |

## Verification

All models import successfully without errors:
```bash
python -c "from puppeteer.agent_service.db import Workflow, WorkflowStep, WorkflowEdge, WorkflowParameter, WorkflowRun; print('ORM OK')"
python -c "from puppeteer.agent_service.models import WorkflowCreate, WorkflowResponse, WorkflowValidationError; print('Pydantic OK')"
```

WorkflowService syntax valid (networkx dependency will be available in Docker container).

## Dependencies

- `networkx>=3.6,<4.0` — already in puppeteer/requirements.txt
- SQLAlchemy 2.x async patterns (already in use across codebase)
- Pydantic v2 (already in use across codebase)

## Next Phase (146-03)

Plans 03 will wire the service into FastAPI routes:
- `POST /api/workflows` — create workflow
- `GET /api/workflows` — list workflows
- `GET /api/workflows/{id}` — get single workflow with full graph
- `PUT /api/workflows/{id}` — update workflow (full replace)
- `DELETE /api/workflows/{id}` — delete (with active run check)
- `POST /api/workflows/{id}/fork` — save-as-new (atomically pause source)
- `POST /api/workflows/validate` — standalone DAG validation (no save)

Plus authentication (current_user from JWT) and permission checks.

## Key Design Notes

- **No client-side step ID generation** — submitted step IDs in WorkflowCreate are temporary; DB generates real UUIDs and returns in response
- **Atomic fork** — source pause happens inside transaction; if commit fails, pause doesn't occur
- **Full graph always** — GET /api/workflows/{id} always returns complete steps[], edges[], parameters[] — no additional queries needed
- **service-layer validation** — node_type and parameter types are free strings; validation logic lives in service, not DB CHECK constraints (Phase 148 adds gate type validators)

## Deviations from Plan

None — plan executed exactly as written.

## Testing Notes

Phase 146-01 Wave 0 created test fixtures and stubs. This plan's tasks are integrated with those fixtures. Full test suite runs with:
```bash
cd puppeteer && pytest tests/test_workflow.py -x -v
```
