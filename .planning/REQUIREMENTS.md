# Requirements — v23.0 DAG & Workflow Orchestration

**Milestone:** v23.0
**Status:** Active
**Last updated:** 2026-04-16

---

## v1 Requirements

### WORKFLOW — Core Data Model

- [x] **WORKFLOW-01**: User can create a named Workflow composed of ScheduledJob steps connected by directed dependency edges (Phase 146 Plan 02-03)
- [x] **WORKFLOW-02**: User can list all Workflow definitions with step count, trigger config, and last-run status (Phase 146 Plan 02-03)
- [x] **WORKFLOW-03**: User can update a Workflow definition (steps, edges, parameters); system re-validates DAG on save (cycle detection, depth check) (Phase 146 Plan 02-03)
- [x] **WORKFLOW-04**: User can delete a Workflow definition (blocked if active WorkflowRuns exist) (Phase 146 Plan 02-03)
- [x] **WORKFLOW-05**: System auto-pauses an existing cron schedule when user executes "Save as New" from a scheduled Workflow to prevent ghost execution (Phase 146 Plan 02-03)

### ENGINE — Execution Engine

- [x] **ENGINE-01**: System dispatches WorkflowRun steps in topological order (BFS), releasing each step only after its dependencies complete
- [x] **ENGINE-02**: System overrides the 10-level job depth limit to 30 levels for workflow-instantiated jobs
- [x] **ENGINE-03**: System uses atomic concurrency guards (SELECT...FOR UPDATE) when processing concurrent step completions to prevent duplicate dispatch
- [x] **ENGINE-04**: System tracks WorkflowRun status as one of: RUNNING / COMPLETED / PARTIAL / FAILED / CANCELLED
- [x] **ENGINE-05**: System propagates a step's FAILED status to all downstream PENDING steps (cascade cancel)
- [x] **ENGINE-06**: System marks WorkflowRun as PARTIAL when failures are absorbed by FAILED-branch steps rather than causing global FAILED
- [x] **ENGINE-07**: User can cancel a running WorkflowRun; system actively aborts ASSIGNED/RUNNING step jobs and marks all PENDING steps CANCELLED

### GATE — Conditional & Fan-out Node Types

- [x] **GATE-01**: IF gate evaluates conditions against structured output from `/tmp/axiom/result.json` using operators: `eq`, `neq`, `gt`, `lt`, `contains`, `exists`
- [x] **GATE-02**: IF gate routes to the first matching branch; unmatched IF gate marks step FAILED and cascades cancellation downstream
- [x] **GATE-03**: AND/JOIN gate releases downstream steps only when all incoming branches have completed
- [x] **GATE-04**: OR gate releases downstream steps when any single incoming branch completes
- [x] **GATE-05**: Parallel fan-out node dispatches multiple independent downstream branches concurrently
- [x] **GATE-06**: Signal wait node pauses workflow execution until a named signal is posted via the existing Signal mechanism

### TRIGGER — Workflow Triggers

- [x] **TRIGGER-01**: User can manually trigger a WorkflowRun from the dashboard, supplying parameter values at trigger time
- [x] **TRIGGER-02**: User can schedule a Workflow on a cron expression (APScheduler); schedule auto-pauses on "Save as New"
- [x] **TRIGGER-03**: User can configure a webhook endpoint for a Workflow (`POST /api/webhooks/{id}/trigger`)
- [x] **TRIGGER-04**: Webhook endpoint validates HMAC-SHA256 signature, timestamp freshness (±5 min), and nonce uniqueness (24h dedup) before triggering a run
- [x] **TRIGGER-05**: Webhook events failing validation (bad signature, stale timestamp, replayed nonce) are rejected HTTP 400 and audit-logged

### PARAMS — Parameter Injection

- [x] **PARAMS-01**: User can define named parameters on a Workflow definition (name, type, optional default value)
- [x] **PARAMS-02**: System injects runtime parameter values as `WORKFLOW_PARAM_<NAME>` environment variables into each step's container; signed script content is never modified

### UI — Dashboard Interface

- [x] **UI-01**: User can view a read-only auto-layout DAG visualization of a Workflow's step graph (elkjs layered layout)
- [x] **UI-02**: Live step execution status is overlaid on the DAG visualization during an active WorkflowRun (colour-coded by status)
- [x] **UI-03**: User can view the run history for a Workflow (list of WorkflowRuns with trigger type, status, started/completed, duration)
- [x] **UI-04**: User can drill into a WorkflowRunStep to view its job output, logs, and `result.json` structured output
- [x] **UI-05**: Unified schedule view shows ScheduledJob (JOB badge) and Workflow (FLOW badge) entries together with next-run time and last-run status (Phase 154 Plan 01, completed 2026-04-16)
- [x] **UI-06**: User can compose a Workflow visually by dragging ScheduledJob steps onto a canvas and connecting them with directed edges
- [x] **UI-07**: Canvas validates the DAG in real-time: highlights cycles, warns on depth approaching 30, and exposes IF gate condition configuration inline

---

## Future Requirements (deferred from v23.0)

- Workflow execution analytics + critical path tracing (v24.0+)
- Rerun from failure point — restart a WorkflowRun from the first failed step (v24.0+)
- Cross-workflow dependencies — workflows calling other workflows (v24.0+)
- Advanced IF gate logic — AND/OR nested conditions in a single gate (v24.0+)
- Dryrun mode — simulate execution without dispatching real jobs (v24.0+)
- Run history comparison — diff two WorkflowRuns side-by-side (v24.0+)
- WORKFLOW_PARAM_* injection accessible to downstream IF gate condition context (v24.0+)

---

## Out of Scope

- **Airflow/Prefect/Dagster integration** — Axiom is the execution engine; external orchestrators would duplicate the job model and break Ed25519 signing
- **Redis/Celery queue** — Background task execution via FastAPI BackgroundTasks is sufficient for MVP; graduated to ARQ only if concurrency exceeds 100 concurrent runs/hr
- **Custom seccomp profiles** — Host-level configuration; addressed in ops documentation, not platform code
- **Conda full-channel sync** — High storage footprint; defer unless data science ICP is confirmed
- **Temporal/Argo-style workflow DSL** — Axiom uses JSON DAG definition stored in DB; no external DSL file format

---

## Traceability

| Phase | Name | Requirements |
|-------|------|-------------|
| 146 | Workflow Data Model | WORKFLOW-01, WORKFLOW-02, WORKFLOW-03, WORKFLOW-04, WORKFLOW-05 |
| 147 | WorkflowRun Execution Engine | ENGINE-01, ENGINE-02, ENGINE-03, ENGINE-04, ENGINE-05, ENGINE-06, ENGINE-07 |
| 148 | Gate Node Types | GATE-01, GATE-02, GATE-03, GATE-04, GATE-05, GATE-06 |
| 149 | Triggers & Parameter Injection | TRIGGER-01, TRIGGER-02, TRIGGER-03, TRIGGER-04, TRIGGER-05, PARAMS-01, PARAMS-02 |
| 150 | Dashboard Read-Only Views | UI-01, UI-02, UI-03, UI-04, UI-05 |
| 151 | Visual DAG Editor | UI-06, UI-07 |
| 153 | Verify Gate Node Types | GATE-01, GATE-02, GATE-03, GATE-04, GATE-05, GATE-06 (gap closure — verification) |
| 154 | Unified Schedule View | UI-05 (gap closure — deferred from Phase 150) |
| 155 | Visual DAG Editor | UI-06, UI-07 (gap closure — Phase 151 implementation) |

**Coverage:** 32/32 requirements mapped ✓
