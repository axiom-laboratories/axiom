---
gsd_state_version: 1.0
milestone: v1.0
milestone_name: milestone
status: completed
last_updated: "2026-04-16T12:04:29.453Z"
progress:
  total_phases: 69
  completed_phases: 67
  total_plans: 180
  completed_plans: 187
  percent: 100
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-04-15)

**Core value:** Jobs run reliably — on the right node, when scheduled, with their output captured — without any step in the chain weakening the security model.

**Current focus:** v23.0 DAG & Workflow Orchestration — 6-phase rollout beginning with Phase 146 (Workflow Data Model).

## Current Position

**Phase:** 149 (Triggers & Parameter Injection) — IN PROGRESS
**Plan:** 149-03 (API Routes: Triggers & Webhooks) — COMPLETED
**Status:** Phase 149 Plan 03 execution complete — API endpoints for manual trigger, webhook CRUD, HMAC trigger validation, cron parameter validation
**Progress:** [██████████] 100%

## Roadmap Summary

**v23.0 Roadmap Created:** 2026-04-15  
**Total requirements mapped:** 32/32 ✓  
**Total phases:** 6  
**Granularity:** Fine (clean requirement grouping per phase)

### Phase Structure

| Phase | Goal | Requirements | Success Criteria | Status |
|-------|------|--------------|------------------|--------|
| 146 | Workflow data model with DAG validation | WORKFLOW-01..05 (5) | Create/list/update/delete Workflows; cycle detection; Save-as-New pauses cron | ✅ Complete |
| 147 | WorkflowRun execution engine with atomicity | ENGINE-01..07 (7) | BFS dispatch; SELECT...FOR UPDATE guards; status machine (RUNNING/COMPLETED/PARTIAL/FAILED/CANCELLED); cascade failure | ✅ Complete |
| 148 | Gate node types (IF, AND/JOIN, OR, parallel, signal) | GATE-01..06 (6) | IF gate result.json evaluation; AND/JOIN synchronization; OR routing; parallel fan-out; Signal wait | ✅ Complete |
| 149 | Triggers + parameter injection | TRIGGER-01..05, PARAMS-01..02 (7) | Manual trigger with params; cron scheduling; webhook with HMAC/nonce; env var injection | 🔨 In Progress (Plan 01 ✅) |
| 150 | Dashboard read-only UI | UI-01..05 (5) | DAG visualization (elkjs); live status overlay (WebSocket); run history; step logs; unified schedule | Pending |
| 151 | Visual DAG editor | UI-06..07 (2) | Canvas drag-drop; real-time validation; IF gate inline config | Pending |

## Requirement Coverage

**Phase 146 (Workflow Data Model):** WORKFLOW-01, WORKFLOW-02, WORKFLOW-03, WORKFLOW-04, WORKFLOW-05 — ✅ Complete  
**Phase 147 (Execution Engine):** ENGINE-01, ENGINE-02, ENGINE-03, ENGINE-04, ENGINE-05, ENGINE-06, ENGINE-07 — ✅ Complete  
**Phase 148 (Gate Node Types):** GATE-01, GATE-02, GATE-03, GATE-04, GATE-05, GATE-06 — ✅ Complete  
**Phase 149 (Triggers & Parameters):** TRIGGER-01 (✅), TRIGGER-02 (✅), TRIGGER-03 (✅), TRIGGER-04 (✅), TRIGGER-05 (✅), PARAMS-01 (✅), PARAMS-02 (🔨) — In Progress (Plans 1-3 complete)  
**Phase 150 (Read-Only UI):** UI-01, UI-02, UI-03, UI-04, UI-05 — Pending  
**Phase 151 (Visual Editor):** UI-06, UI-07 — Pending  

**Total:** 22/32 ✓

## Key Architectural Decisions

**2026-04-15 — v23.0 DAG/Workflow Orchestration Roadmap**
- Parameter passing: WORKFLOW_PARAM_* env vars (NOT template substitution — preserves Ed25519 signatures)
- IF gate structured output: /tmp/axiom/result.json result file (NOT last-line stdout — immune to logging noise)
- Unmatched IF gate: FAILED + cascade cancellation (no partial-route branching)
- Webhook triggers: included in v23.0 scope (Phase 149)
- Concurrency guards: SELECT...FOR UPDATE on BFS cascade to prevent duplicate dispatch from concurrent step completions
- Depth limit: 30 levels for workflow-instantiated jobs (override from 10-level default)
- Save-as-New: auto-pauses original cron trigger to prevent ghost execution (Phase 146 + 149)
- Cycle detection: networkx library (add to requirements.txt in Phase 146)
- Visual editor npm: @xyflow/react v12.8.3, elkjs v0.11.1, zustand v5.4.0 (Phase 151 only)

## Database Schema (New Tables)

- `workflows` (id, name, created_by, created_at, updated_at, definition_json)
- `workflow_steps` (id, workflow_id, scheduled_job_id, node_type, config_json)
- `workflow_edges` (id, workflow_id, from_step_id, to_step_id, branch_name)
- `workflow_runs` (id, workflow_id, status, started_at, completed_at, trigger_type, triggered_by)
- `workflow_run_steps` (id, workflow_run_id, workflow_step_id, status, job_id, result_json)
- `workflow_parameters` (id, workflow_id, name, type, default_value)
- `webhook_nonces` (id, workflow_id, nonce_hash, expires_at)

## Critical Concurrency Safeguards

**Phase 147 (ENGINE-03) is CRITICAL:** Must use `SELECT...FOR UPDATE` transaction locks to prevent race conditions when multiple steps complete concurrently. Explicitly called out in research findings as a high-priority pitfall mitigation.

Pattern:
```python
# When step completion triggers downstream unblock
async with db.transaction(isolation='serializable'):
    step = await Step.get(step_id).for_update()
    # Process unblock atomically
    await dispatch_dependents(step)
```

## Previous Milestone

**v22.0 Security Hardening — COMPLETE (2026-04-15)**

Archive: `.planning/milestones/v22.0-ROADMAP.md`
Phases: 132–145 (14 phases, 165 plans total across all milestones)

**Key deliverables:**
- Container hardening: non-root execution, cap_drop ALL, no-new-privileges, resource limits, socket mount, Podman support
- EE licence protection: Ed25519 wheel manifest verification, HMAC-SHA256 boot log, entry point whitelist, wheel signing tool
- Nyquist validation: 100% test coverage across all 14 phases

## Phase 148 Completion Summary

**Phase 148: Gate Node Types — COMPLETE (2026-04-16)**

Delivered: 4 plans + 4 waves of execution

**Plan 148-01 (Wave 1):** GateEvaluationService with condition evaluation methods
- resolve_field(): dot-path JSON traversal
- evaluate_condition(): 6 operators (eq, neq, gt, lt, contains, exists)
- evaluate_conditions(): AND aggregation
- evaluate_if_gate(): branch routing with fallthrough

**Plan 148-02 (Wave 2):** Gate node dispatch integration
- Gate node types: IF_GATE, AND_JOIN, OR_GATE, PARALLEL, SIGNAL_WAIT
- Dispatch logic: handle gates in BFS traversal
- Branch skipping: mark non-matching branches as SKIPPED
- Result JSON evaluation for IF gates

**Plan 148-03 (Wave 3):** SIGNAL_WAIT blocking and wakeup
- advance_signal_wait(): find all RUNNING SIGNAL_WAIT steps, match by signal_name, mark COMPLETED
- Signal endpoint integration: fire_signal() calls advance_signal_wait() synchronously
- Cancellation safety: SIGNAL_WAIT steps marked CANCELLED before signal arrival prevents wakeup

**Plan 148-04 (Wave 4):** Comprehensive test suite
- 22 unit tests for GateEvaluationService (all operators, edge cases, nested paths)
- 11 integration tests from Phase 147 verified passing (dispatch, concurrency, signal wakeup, cascade)
- Total: 33 passing tests covering GATE-01 through GATE-06

**All tests passing:** 33/33 ✓

## Phase 149 Progress

**Phase 149: Triggers & Parameter Injection — IN PROGRESS (2026-04-16)**

**Plan 149-01 (Wave 1) - COMPLETE:** Database Schema & Pydantic Models
- Workflow.schedule_cron: TEXT column for cron expressions (gates with is_paused)
- WorkflowRun.trigger_type/triggered_by/parameters_json: audit trail and parameter snapshot
- WorkflowWebhook ORM: id, workflow_id FK, name, secret_hash (bcrypt), secret_plaintext (Fernet-encrypted), created_at
- migration_v55.sql: idempotent ALTER TABLE and CREATE TABLE statements
- Pydantic models: WorkflowCreate/Update/Response updated; WorkflowWebhookCreate/Response added
- Requirements satisfied: TRIGGER-01 (cron gates), TRIGGER-02 (webhook table), PARAMS-01 (parameter snapshot)

**Plan 149-02 (Wave 2) - COMPLETE:** Service Layer (Workflows, Webhooks, Cron Scheduling)
- WorkflowService.start_run(): parameter merging, env var injection, trigger metadata
- WorkflowService.dispatch_next_wave(): BFS dispatch with gate node handling
- SchedulerService: APScheduler integration, cron job sync, scheduled trigger creation
- Security helpers: hash_webhook_secret (bcrypt), verify_webhook_signature (HMAC-SHA256)
- Requirements satisfied: TRIGGER-02 (webhook helpers), PARAMS-02 (env var injection)

**Plan 149-03 (Wave 3) - COMPLETE:** API Endpoints (Triggers, Webhooks, Validation)
- POST /api/workflow-runs: manual trigger with parameter overrides (JWT auth, 201 response)
- POST /api/workflows/{id}/webhooks: webhook creation with plaintext secret return (201, Fernet encryption)
- GET /api/workflows/{id}/webhooks: webhook listing (secret=None for security)
- DELETE /api/workflows/{id}/webhooks/{webhook_id}: webhook revocation (204 response)
- POST /api/webhooks/{webhook_id}/trigger: unauthenticated HMAC trigger (202, run_id response)
- PATCH /api/workflows/{id}: cron parameter validation (422 if required params lack defaults)
- Requirements satisfied: TRIGGER-01 (manual trigger), TRIGGER-03 (webhook CRUD), TRIGGER-04 (HMAC validation), TRIGGER-05 (validation errors)

**Requirements Progress:** 6/7 complete (TRIGGER-01, TRIGGER-02, TRIGGER-03, TRIGGER-04, TRIGGER-05, PARAMS-01); PARAMS-02 pending

## Next Steps

1. **Phase 149 Plan 02:** Implement APScheduler integration, webhook trigger endpoint, HMAC verification, parameter injection
2. **Phase 149 Plan 03+:** API endpoints for workflow CRUD with triggers, run history, parameter validation
3. **Phase 150 Planning:** `/gsd:plan-phase 150` to build read-only DAG UI (visualization, live status, logs)
4. **Phase 151 Planning:** `/gsd:plan-phase 151` to implement visual DAG editor (canvas, drag-drop)

**Remaining work:** Phase 149 (3+ more plans), Phase 150 (3-4 plans), Phase 151 (2 plans) = ~8-10 plans to ship v23.0 complete.
