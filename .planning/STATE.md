---
gsd_state_version: 1.0
milestone: v1.0
milestone_name: milestone
status: completed
last_updated: "2026-04-15T21:26:52.658Z"
progress:
  total_phases: 67
  completed_phases: 66
  total_plans: 172
  completed_plans: 181
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-04-15)

**Core value:** Jobs run reliably — on the right node, when scheduled, with their output captured — without any step in the chain weakening the security model.

**Current focus:** v23.0 DAG & Workflow Orchestration — 6-phase rollout beginning with Phase 146 (Workflow Data Model).

## Current Position

**Phase:** 148 (Gate Node Types) — CONTEXT READY
**Plan:** Not yet planned
**Status:** Phase 148 context gathered — ready for /gsd:plan-phase 148
**Progress:** 2/6 phases complete (148 context done, planning next)

## Roadmap Summary

**v23.0 Roadmap Created:** 2026-04-15  
**Total requirements mapped:** 32/32 ✓  
**Total phases:** 6  
**Granularity:** Fine (clean requirement grouping per phase)

### Phase Structure

| Phase | Goal | Requirements | Success Criteria |
|-------|------|--------------|------------------|
| 146 | Workflow data model with DAG validation | WORKFLOW-01..05 (5) | Create/list/update/delete Workflows; cycle detection; Save-as-New pauses cron |
| 147 | WorkflowRun execution engine with atomicity | ENGINE-01..07 (7) | BFS dispatch; SELECT...FOR UPDATE guards; status machine (RUNNING/COMPLETED/PARTIAL/FAILED/CANCELLED); cascade failure |
| 148 | Gate node types (IF, AND/JOIN, OR, parallel, signal) | GATE-01..06 (6) | IF gate result.json evaluation; AND/JOIN synchronization; OR routing; parallel fan-out; Signal wait |
| 149 | Triggers + parameter injection | TRIGGER-01..05, PARAMS-01..02 (7) | Manual trigger with params; cron scheduling; webhook with HMAC/nonce; env var injection |
| 150 | Dashboard read-only UI | UI-01..05 (5) | DAG visualization (elkjs); live status overlay (WebSocket); run history; step logs; unified schedule |
| 151 | Visual DAG editor | UI-06..07 (2) | Canvas drag-drop; real-time validation; IF gate inline config |

## Requirement Coverage

**Phase 146 (Workflow Data Model):** WORKFLOW-01, WORKFLOW-02, WORKFLOW-03, WORKFLOW-04, WORKFLOW-05  
**Phase 147 (Execution Engine):** ENGINE-01, ENGINE-02, ENGINE-03, ENGINE-04, ENGINE-05, ENGINE-06, ENGINE-07  
**Phase 148 (Gate Node Types):** GATE-01, GATE-02, GATE-03, GATE-04, GATE-05, GATE-06  
**Phase 149 (Triggers & Parameters):** TRIGGER-01, TRIGGER-02, TRIGGER-03, TRIGGER-04, TRIGGER-05, PARAMS-01, PARAMS-02  
**Phase 150 (Read-Only UI):** UI-01, UI-02, UI-03, UI-04, UI-05  
**Phase 151 (Visual Editor):** UI-06, UI-07  

**Total:** 32/32 ✓

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

## Next Steps

1. `/gsd:plan-phase 146` to break Phase 146 (Workflow Data Model) into executable plans
2. Each phase depends on previous: 146 → 147 → 148 → 149 → 150 → 151
3. Gate phases (148) and Trigger phase (149) can be planned in parallel but execute sequentially after Phase 147
4. UI phases (150, 151) execute after Phase 149 to ensure backend completeness
