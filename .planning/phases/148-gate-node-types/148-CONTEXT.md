# Phase 148: Gate Node Types - Context

**Gathered:** 2026-04-15
**Status:** Ready for planning

<domain>
## Phase Boundary

Add 5 gate node types to the BFS execution engine: IF_GATE, AND_JOIN, OR_GATE, PARALLEL, SIGNAL_WAIT. These control routing, synchronization, fan-out, and signal-based blocking within workflow runs. Script execution, the existing BFS dispatch loop, and the WorkflowRun lifecycle are not changed — only the handling of these specific node_type values is added.

</domain>

<decisions>
## Implementation Decisions

### Gate nodes without scripts (scheduled_job_id)
- `WorkflowStep.scheduled_job_id` becomes nullable FK — NULL means structural gate node with no job
- Migration required (ALTER TABLE) — this is a schema change on an existing column
- PARALLEL is structural/virtual: marks its own `WorkflowStepRun` COMPLETED immediately without dispatching a job; BFS naturally fans out to all outgoing edges in the next wave
- AND/JOIN predecessor scope: all steps that have a direct outgoing edge to the AND/JOIN node

### IF gate condition schema
- Conditions stored in `config_json` as: `{"branches": {"true": [{"field": "x", "op": "eq", "value": "y"}, ...], "false": [...]}}`
- Multiple conditions per branch use AND logic (all must match)
- Supported operators: `eq`, `neq`, `gt`, `lt`, `contains`, `exists` (from REQUIREMENTS.md GATE-01)
- `field` is a dot-path into the result JSON (e.g. `"exit_code"`, `"data.status"`)
- Branches evaluated in order; first matching branch is taken; no match → step FAILED, cascade
- IF_GATE is never dispatched as a job — evaluated inline in `advance_workflow()` when the upstream SCRIPT step completes
- result.json transport: node populates `ResultReport.result: Optional[Dict]` from `/tmp/axiom/result.json` after execution; server reads it during `advance_workflow()`
- Persistence: add `result_json: Mapped[Optional[str]]` (nullable Text column) to `WorkflowStepRun`; server writes it when processing the result report; used for IF gate evaluation and future Phase 150 UI step log display

### AND/JOIN failure and SKIPPED semantics
- AND/JOIN: fails immediately when any predecessor reaches FAILED or CANCELLED — does not wait for remaining predecessors
- Not-taken branches (branches not selected by IF_GATE or OR_GATE): steps on those branches are marked SKIPPED
- SKIPPED is distinct from CANCELLED (operator-stopped) — SKIPPED = branch not taken by gate logic
- OR_GATE: when any one incoming branch completes, mark all PENDING step runs on non-triggering branches SKIPPED immediately (eager, at OR completion time — not lazy)

### Signal wait wakeup
- `SIGNAL_WAIT` step stores its signal name as `{"signal_name": "deploy-approved"}` in `config_json` (consistent with IF gate using config_json for all gate configuration)
- Wakeup mechanism: direct synchronous `advance_workflow()` call from the signal creation endpoint — same pattern as `report_result`; signal endpoint checks if any RUNNING SIGNAL_WAIT step in any active run is waiting on that signal name, then advances
- No timeout in Phase 148 — SIGNAL_WAIT steps block indefinitely until the signal arrives or the run is cancelled
- Run cancellation: RUNNING SIGNAL_WAIT steps get status CANCELLED when the run is cancelled (existing cancel_run path handles this)

### Claude's Discretion
- Exact dot-path parsing implementation for IF gate field resolution
- Internal helper method names and factoring within workflow_service.py
- Error message text for unmatched IF gate branches

</decisions>

<specifics>
## Specific Ideas

- CAS guard pattern from Phase 147 (`UPDATE WHERE status='PENDING'`, check rowcount) should be extended to gate node status transitions to prevent race conditions
- Phase 147 reserved `branch_name IS NULL` for unconditional edges only — Phase 148 will add processing for non-null branch_name edges in the BFS
- The `advance_workflow()` entry point is the natural place for all gate evaluation — it already runs after every step completion

</specifics>

<code_context>
## Existing Code Insights

### Reusable Assets
- `dispatch_next_wave()` in `workflow_service.py`: BFS dispatch loop — extend to skip structural gate nodes (PARALLEL, AND_JOIN, OR_GATE, IF_GATE, SIGNAL_WAIT) and handle them inline
- `advance_workflow()` in `workflow_service.py`: central post-completion hook — add gate evaluation here
- `Signal` table (`db.py` ~line 240): `name` (PK), `payload` (nullable JSON Text), `created_at` — already exists, just needs wiring to `advance_workflow()`
- `ResultReport.result: Optional[Dict]` (`models.py` line 200): already accepts arbitrary dict — reuse for result.json transport from node
- CAS pattern: `UPDATE workflow_step_runs SET status='RUNNING' WHERE id=? AND status='PENDING'` — apply same guard to gate transitions

### Established Patterns
- `branch_name IS NULL` = unconditional edge (Phase 147); non-null = named IF/OR branch
- `config_json` (nullable Text on WorkflowStep): JSON field used for gate configuration — already established in Phase 146 data model
- `WorkflowStepRun.status` enum: PENDING / RUNNING / COMPLETED / FAILED / SKIPPED / CANCELLED — SKIPPED already in enum, just unused

### Integration Points
- `db.py` `WorkflowStep.scheduled_job_id`: change `nullable=False` to `nullable=True` — requires migration SQL
- `db.py` `WorkflowStepRun`: add `result_json: Mapped[Optional[str]]` column — `create_all` handles new column on fresh DBs; migration SQL needed for existing deployments
- Signal creation endpoint in `main.py`: add `advance_workflow()` call after signal is persisted
- `report_result` endpoint in `main.py`: populate `WorkflowStepRun.result_json` from `ResultReport.result` before calling `advance_workflow()`

</code_context>

<deferred>
## Deferred Ideas

- Timeout support for SIGNAL_WAIT — Phase 149+ if needed
- UI visualization of gate nodes and branch paths — Phase 150 (Workflow UI)
- Nested workflow invocation as a gate type — out of scope for v23.0
- AND/JOIN partial-failure recovery (retry individual branches) — out of scope

</deferred>

---

*Phase: 148-gate-node-types*
*Context gathered: 2026-04-15*
