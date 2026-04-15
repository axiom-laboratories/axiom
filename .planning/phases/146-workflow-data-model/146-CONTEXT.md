# Phase 146: Workflow Data Model - Context

**Gathered:** 2026-04-15
**Status:** Ready for planning

<domain>
## Phase Boundary

Database schema, CRUD API, DAG validation (cycle detection + depth check), and Save-as-New for Workflow definitions. This phase delivers the data layer and API surface for Workflows — no execution engine (Phase 147), no gate node logic (Phase 148), no triggers beyond the is_paused flag (Phase 149), no UI (Phase 150/151).

Requirements: WORKFLOW-01..05

</domain>

<decisions>
## Implementation Decisions

### Storage strategy
- **Normalized tables only** — `definition_json` blob is dropped from the `workflows` table
- Source of truth: `workflow_steps` + `workflow_edges` tables (fully queryable, no sync risk)
- Phase 147 BFS engine queries `workflow_steps`/`workflow_edges` directly — no JSON parsing at dispatch time
- `workflow_parameters` lives in its own table (not embedded in definition) — independently queryable by Phase 149 for WORKFLOW_PARAM_* injection

### Schema: node types and branch names
- `workflow_steps.node_type` — free string column, validated at service layer (not DB CHECK constraint). Allowed types for Phase 146: `SCRIPT`. Gate types (`IF_GATE`, `AND_JOIN`, `OR_GATE`, `PARALLEL`, `SIGNAL_WAIT`) added in Phase 148 without migration.
- `workflow_edges.branch_name` — nullable free string. NULL = unconditional edge. Non-null = named IF gate branch (convention: `true`/`false`). Validated at service layer in Phase 148.

### API contract shape
- **Full-graph in one request** — create and update both send the complete definition
- `POST /api/workflows` body: `{name, steps: [{id, scheduled_job_id, node_type, config_json}], edges: [{from_step_id, to_step_id, branch_name}], parameters: [{name, type, default_value}]}`
- `PUT /api/workflows/{id}` — full replace. Server atomically deletes all existing steps/edges/parameters and inserts the new set. DAG validation runs on the full incoming graph before any write.
- `GET /api/workflows/{id}` — returns full graph always: workflow metadata + nested `steps[]`, `edges[]`, `parameters[]`. One request is enough to render the DAG.
- `GET /api/workflows` (list) — returns metadata + counts (`step_count`, `last_run_status`), not full graph
- All IDs are UUIDs stored as String — consistent with `Job.id`, `ScheduledJob.id`, `Node.id`

### Save-as-New (WORKFLOW-05)
- Dedicated endpoint: `POST /api/workflows/{id}/fork`
- Request body: `{new_name: "..."}` (required — caller owns naming)
- Server atomically: (1) clones all steps/edges/parameters into new Workflow, (2) sets `source_workflow.is_paused = true` to prevent ghost cron execution
- `is_paused` flag added to `workflows` table. Pausing preserves the original `schedule_cron` expression — it's not nullified, just deactivated. User can explicitly re-enable if needed.
- Response: full new Workflow with `steps[]`, `edges[]`, `parameters[]` (same shape as GET /api/workflows/{id})

### Validation response design
- **Cycle detection failure** → HTTP 422 with structured error: `{error: "CYCLE_DETECTED", cycle_path: ["step_id_a", "step_id_b", "step_id_a"]}`
- **Depth limit exceeded** → HTTP 422: `{error: "DEPTH_LIMIT_EXCEEDED", max_depth: 30, actual_depth: N}`
- **Referential integrity failure** → HTTP 422: `{error: "INVALID_EDGE_REFERENCE", edge: {from_step_id, to_step_id}}`
- **Delete with active runs** → HTTP 409: `{error: "ACTIVE_RUNS_EXIST", active_run_ids: ["..."]}`
- **Standalone validate endpoint**: `POST /api/workflows/validate` — same body as POST /api/workflows, runs all validation (cycle, depth, referential integrity), returns validation errors without saving. Phase 151 visual editor calls this on every canvas change.

### Validations run at save time (and on /validate)
1. Cycle detection — networkx library (`networkx` added to `requirements.txt`)
2. Depth limit — max 30 levels (override from default 10)
3. Referential integrity — all `from_step_id`/`to_step_id` in edges must reference step IDs present in the submitted `steps[]`

### Claude's Discretion
- Exact Pydantic model names and field aliases
- Internal networkx implementation details (DiGraph vs MultiDiGraph)
- Whether `workflow_service.py` lives under `services/` (following existing pattern) or a new `workflow/` sub-package
- Migration file naming (next in sequence after `migration_v52.sql`)
- Test file structure and fixtures

</decisions>

<specifics>
## Specific Ideas

- The `is_paused` flag approach for Save-as-New is intentionally non-destructive — operators can re-enable the source workflow if they truly want both versions running
- The `/validate` endpoint is explicitly designed for the Phase 151 canvas to call on every change, so it must be fast (no writes, pure validation logic)
- Structured error responses with `cycle_path` let the Phase 150/151 UI highlight the exact offending nodes/edges

</specifics>

<code_context>
## Existing Code Insights

### Reusable Assets
- `Base` (`db.py:29`) — DeclarativeBase all new tables inherit from; `create_all` at startup handles new tables automatically
- Migration SQL pattern — `puppeteer/migration_v52.sql` is the most recent; next migration continues this sequence
- `ScheduledJob` (`db.py:79`) — the step unit; workflow steps FK to `scheduled_jobs.id`; no mutation of ScheduledJob allowed
- `Signal` (`db.py:238`) — existing signal table referenced by SIGNAL_WAIT gate in Phase 148
- `scheduler_service.py` — existing APScheduler integration; `is_active` and `schedule_cron` patterns to follow for cron pause/resume

### Established Patterns
- All model IDs: UUID stored as String primary key
- Service layer in `puppeteer/agent_service/services/` — new `workflow_service.py` goes here
- FastAPI routes in `main.py` — workflow routes added following existing `@app.get`/`@app.post` pattern
- HTTP 422 for validation errors (FastAPI default), HTTP 409 for business logic conflicts (used in Phase 129 pattern)
- `ActionResponse`/`ErrorResponse` Pydantic models established in Phase 129 — use for delete/fork responses

### Integration Points
- `db.py` — add 5 new ORM classes: `Workflow`, `WorkflowStep`, `WorkflowEdge`, `WorkflowParameter`, plus `is_paused` column on existing... wait — `Workflow` is a new table (not modifying ScheduledJob)
- `main.py` — add workflow router/routes (8-10 new endpoints)
- `requirements.txt` — add `networkx` (cycle detection)
- Migration SQL — new file for the 5 new tables

</code_context>

<deferred>
## Deferred Ideas

- WorkflowRun execution, BFS dispatch, status machine — Phase 147
- IF gate / AND/JOIN / OR / Parallel / Signal wait node type logic — Phase 148
- Cron trigger scheduling, webhook trigger config — Phase 149
- DAG visualization, run history UI — Phase 150
- Visual drag-drop editor — Phase 151

None — discussion stayed within Phase 146 scope.

</deferred>

---

*Phase: 146-workflow-data-model*
*Context gathered: 2026-04-15*
