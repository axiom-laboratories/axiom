# Phase 147: WorkflowRun Execution Engine - Context

**Gathered:** 2026-04-15
**Status:** Ready for planning

<domain>
## Phase Boundary

BFS dispatch engine that drives WorkflowRun execution — creating step-level Jobs in topological order, tracking per-step status in a new WorkflowStepRun table, managing the WorkflowRun state machine (RUNNING → COMPLETED/PARTIAL/FAILED/CANCELLED), and cascade-handling cancellation.

Requirements: WorkflowRun execution engine, step tracking, status state machine, cascade cancellation. No gate node logic (Phase 148), no trigger scheduling beyond a manual POST (Phase 149), no dashboard UI (Phase 150/151).

</domain>

<decisions>
## Implementation Decisions

### WorkflowStepRun table
- New table `workflow_step_runs` with columns: id (UUID String PK), workflow_run_id (FK → workflow_runs.id), workflow_step_id (FK → workflow_steps.id), status, started_at (nullable DateTime), completed_at (nullable DateTime), created_at
- **Status values**: PENDING / RUNNING / COMPLETED / FAILED / SKIPPED / CANCELLED — SKIPPED reserved for Phase 148 IF gate branches; CANCELLED for cascade
- **Job link**: add `workflow_step_run_id` FK column to the existing `Job` table. BFS engine sets it when dispatching a step's job. Phase 150 can query `SELECT * FROM jobs WHERE workflow_step_run_id = X`
- **Result**: no result blob on WorkflowStepRun — operators follow the job_guid FK to `Job.result`. No data duplication
- **No retry tracking in Phase 147**: one Job per step execution, no retry loop. Retry is a Phase 148+ concern

### BFS advance trigger
- **Hook in `report_result`**: when a node calls `POST /work/{guid}/result`, the handler checks if `job.workflow_step_run_id` is set. If yes, calls `WorkflowService.advance_workflow(run_id, db)` after updating the job status
- **Engine location**: `advance_workflow()` and `dispatch_next_wave()` added to existing `WorkflowService` class in `workflow_service.py`. Keeps all workflow logic in one service, following the `JobService` pattern
- **Concurrency guard**: before dispatching a step, atomically update `WorkflowStepRun.status = 'RUNNING' WHERE status = 'PENDING'`. If 0 rows updated, another concurrent advance already claimed it — skip. Works with both SQLite and Postgres (no `SELECT FOR UPDATE`)
- **Wave parallelism**: all steps whose predecessors are COMPLETED get dispatched in the same DB transaction. Full DAG parallelism — jobs execute concurrently on different nodes

### PARTIAL vs FAILED state machine
- **Independent branches continue**: a step failure blocks its downstream descendants but not unrelated branches. Engine continues dispatching eligible steps in other branches
- **Terminal conditions**:
  - `COMPLETED` — every WorkflowStepRun reached COMPLETED
  - `PARTIAL` — at least one COMPLETED, at least one FAILED (remainder SKIPPED or CANCELLED due to failure cascade)
  - `FAILED` — no steps reached COMPLETED (all FAILED or were CANCELLED before running)
- **Run completion check**: after each step transitions to a terminal status, count WorkflowStepRuns still in PENDING or RUNNING. If 0 → compute final status and write `WorkflowRun.status` + `completed_at`. Simple, correct, no topology re-analysis

### Run creation & cancellation API
- **Trigger a run**: `POST /api/workflow-runs` body `{workflow_id, parameters: {key: value}}` (parameters optional — overrides defaults from `workflow_parameters` table). Server validates workflow exists and is not paused, creates `WorkflowRun` (status=RUNNING), dispatches first BFS wave immediately
- **Cancel a run**: `POST /api/workflow-runs/{id}/cancel` — dedicated action endpoint, follows existing `/jobs/{guid}/cancel` pattern. Returns updated WorkflowRun with status=CANCELLED
- **Cancellation scope**: set `WorkflowRun.status = CANCELLED`. Engine blocks any further step dispatches. Jobs already ASSIGNED on nodes run to completion — nodes have no interrupt mechanism. When those jobs report results, the advance hook sees the run is CANCELLED and takes no action. PENDING WorkflowStepRuns transition to CANCELLED

### Claude's Discretion
- Exact Pydantic model names for WorkflowStepRun responses
- Whether `advance_workflow` is async-safe to call inline in `report_result` or needs `asyncio.create_task`
- Migration file naming (next after migration_v53.sql or whatever is latest)
- Test structure and fixtures

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `WorkflowRun` (db.py:524) — already exists with id, workflow_id, status, started_at, completed_at, trigger_type, triggered_by, created_at. Phase 147 fills in the execution logic
- `WorkflowStep` (db.py:487) — step definitions with scheduled_job_id FK. BFS engine queries these to build the dispatch graph
- `WorkflowEdge` (db.py:500) — edges with from_step_id/to_step_id/branch_name. BFS uses these for predecessor checking
- `WorkflowService.validate_dag()` — already uses networkx DiGraph. BFS can reuse the same graph construction logic to determine dispatch order
- `JobService.report_result()` — the hook point. Existing flow: update job status → check dependencies → commit. Workflow advance inserts after the job status update
- `Job.workflow_step_run_id` — new nullable String column to add to `jobs` table

### Established Patterns
- Service methods are async (`async def`) using `AsyncSession` — follow same pattern for `advance_workflow`
- UUID String PKs throughout — WorkflowStepRun.id is also UUID String
- `create_all` at startup handles new tables automatically — no migration needed for fresh installs; migration SQL needed for existing deployments
- HTTP 409 for business logic conflicts (e.g., trying to start a run on a paused workflow)
- `ActionResponse` Pydantic model (from Phase 129) — use for cancel response alongside full WorkflowRun

### Integration Points
- `main.py` `report_result` route (line ~1835) — add workflow advance call after `JobService.report_result`
- `db.py` — add `WorkflowStepRun` ORM class; add `workflow_step_run_id` nullable String column to `Job` model
- `workflow_service.py` — add `start_run()`, `advance_workflow()`, `dispatch_next_wave()`, `cancel_run()` methods
- `main.py` — add `POST /api/workflow-runs` and `POST /api/workflow-runs/{id}/cancel` routes

</code_context>

<specifics>
## Specific Ideas

- The CAS concurrency guard (update WHERE status='PENDING') is the explicit preference — avoids SELECT FOR UPDATE which breaks SQLite dev setup
- "Let running Jobs finish" on cancellation is intentional — nodes have no kill signal, so cancellation is a soft stop on future dispatches, not a hard interrupt
- PARTIAL is a meaningful distinct state — operators need to know "some steps succeeded, some failed" vs "nothing succeeded"

</specifics>

<deferred>
## Deferred Ideas

- IF gate / AND/JOIN / OR / Parallel fan-out / Signal wait gate logic — Phase 148
- Cron trigger scheduling, webhook trigger — Phase 149 (manual POST trigger implemented in Phase 147)
- DAG visualization, run history UI, step logs view — Phase 150
- Per-step retry logic — Phase 148+ concern
- Fail-fast mode (configurable per-workflow) — future consideration, not Phase 147

</deferred>

---

*Phase: 147-workflowrun-execution-engine*
*Context gathered: 2026-04-15*
