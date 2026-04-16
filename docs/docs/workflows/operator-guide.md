# Workflow Operator Guide

Learn how to operate and monitor workflows in Axiom at runtime.

This guide explains observable workflow behaviour, status transitions, how cancellation propagates, and how to monitor workflows via API and dashboard. For system architecture and internals, see the Developer Guide.

## Workflow Execution Status

Workflows transition through five main states during execution:

| Status | When Set | Behavior | Transitions To |
|--------|----------|----------|----------------|
| **RUNNING** | On first step dispatch | At least one step is PENDING, ASSIGNED, or RUNNING; execution actively progressing | COMPLETED, PARTIAL, FAILED, CANCELLED |
| **COMPLETED** | When last step reports success | All steps succeeded; all gates passed without failures; entire DAG reached terminal state | (terminal) |
| **PARTIAL** | During final status consolidation | Some branches failed but failures were isolated by IF gates; main execution path completed normally | (terminal) |
| **FAILED** | When a non-isolated step fails | A critical step failed with no IF gate to absorb the failure; all downstream steps cascaded as CANCELLED | (terminal) |
| **CANCELLED** | User explicitly cancelled via API/dashboard | Workflow execution aborted; ASSIGNED/RUNNING steps are terminated; PENDING steps marked CANCELLED | (terminal) |

### Understanding Status Transitions

**COMPLETED:** All steps succeeded normally. Every branch through the DAG completed successfully. No failures, no conditional branches taken to failure paths.

**PARTIAL:** An IF gate took a failure branch, isolating the failure. The upstream step failed, but the IF gate handled it by routing to a failure-handling branch (e.g., a Rollback or Cleanup step). Downstream steps after the gate continue normally. This is **expected and normal** for conditional workflows.

**FAILED:** A step failed without isolation by a gate. All downstream steps were automatically cancelled by the cascade mechanism. Operators should investigate FAILED runs immediately — this indicates an unexpected error in the pipeline.

**PARTIAL is not a bug.** It's the intended outcome when conditional logic is properly set up.

## Cascade Cancellation (Failure Propagation)

When a step fails, the system automatically cancels all downstream PENDING steps unless the failure is isolated by a gate.

### Linear Pipeline (No Gates)

```
A (success) → B (success) → C (success)
Workflow status: COMPLETED

A (FAILED) → B (CANCELLED) → C (CANCELLED)
Workflow status: FAILED
```

When A fails, B and C are immediately marked CANCELLED because A's failure has no isolation gate to contain it.

### Pipeline with IF Gate (Conditional Branching)

```
A (success) → IF Gate → [Success Branch] → B (success) → C (success)
                        └─ [Failure Branch] → Rollback (success)
Workflow status: PARTIAL

A (FAILED) → IF Gate (takes failure branch) → Rollback (success) → C (success)
Workflow status: PARTIAL
```

When A fails, the IF Gate evaluates its condition against A's failure result. The gate routes to the failure branch (Rollback runs instead of B). Since the gate absorbed the failure, B is NOT cascaded as CANCELLED; instead, execution continues with C after Rollback completes.

### Key Rules for Cascade Cancellation

- **Isolation gates** (IF_GATE with a failure branch, AND_JOIN, OR_GATE) **break cascade chains**. A failure absorbed by these gates does not propagate downstream.
- **Linear steps** without isolation gates form **cascade chains**. A single failure cancels everything downstream.
- To monitor cascade behaviour: View the DAG in the dashboard; crossed-out steps (CANCELLED status) indicate failed dependencies.

## Gate Execution Semantics

Gates do not execute jobs; they control flow topology. Each gate type has specific semantics:

### IF_GATE

Evaluates conditions against the `result.json` from the upstream step. If **ALL** conditions match, execution takes the primary branch. If any condition fails, execution takes the failure branch (if defined). Routes to exactly one branch — never both.

**Use when:** You need conditional logic based on a previous step's output. Example: "If data quality check passes, load to production; otherwise, load to staging."

### AND_JOIN

Waits for **ALL** incoming branches to complete before releasing downstream steps. If any incoming branch fails or is cancelled, the AND_JOIN marks itself FAILED (unless isolated by another gate above it). Propagates failure from any branch.

**Use when:** Multiple parallel branches must all succeed before proceeding. Example: "Wait for all parallel data exports to complete, then consolidate results."

### OR_GATE

Releases downstream steps as soon as **ANY** incoming branch completes. Other branches are automatically marked SKIPPED (not needed). No waiting for other branches.

**Use when:** Only one of multiple branches is needed, and execution should proceed as soon as one succeeds. Example: "Try endpoint A; if it fails, try endpoint B. Use whichever succeeds first."

### PARALLEL

Fans out to multiple independent downstream branches; all execute **concurrently**. Releases all downstream children simultaneously. Not a synchronization point — just a topology fan-out.

**Use when:** Multiple independent tasks should run in parallel. Example: "Download files from three cloud providers in parallel, each to its own branch."

### SIGNAL_WAIT

Pauses execution until an external signal (named) is posted via the Signal mechanism. When the signal arrives, execution continues to the next step.

**Use when:** Workflow must wait for an external approval or event. Example: "Execute deployment preview, pause for human approval via signal, then run full deployment."

## Phase 149 Features: Triggers & Parameters

### Workflow Triggers

Workflows can be triggered in three ways:

- **MANUAL:** User clicks 'Trigger Run' on the dashboard (Phase 151, UI shipping soon). API: `POST /api/workflows/{id}/runs`
- **CRON:** Scheduled via cron expression defined on the workflow. APScheduler manages the schedule; runs execute automatically at the configured times.
- **WEBHOOK:** External system POSTs to `/api/webhooks/{webhook_id}/trigger`. Signature must be valid: HMAC-SHA256, timestamp within ±5 minutes, nonce not seen in the last 24 hours.

### Parameter Injection

Workflows can define named parameters (string, integer) with optional defaults. At dispatch time, parameters are resolved from WorkflowParameter rows and injected as `WORKFLOW_PARAM_<NAME>` environment variables.

- **Each step's job sees the same parameter values** — scripts are immutable; parameters are injected at runtime via env vars.
- **Example:** Workflow parameter `target_env` → each step's job receives env var `WORKFLOW_PARAM_target_env=production`.
- **Source of truth:** Parameter values are stored in the `parameters_json` field of WorkflowRun for audit trail.

## Monitoring via Dashboard

### Workflows List

The **Workflows** view shows all defined workflows with metadata:
- Workflow name and status of the last run
- Last run timestamp (when it completed)
- Next scheduled run (if cron is configured)
- Click any row to navigate to the WorkflowDetail view

### Workflow Detail

The **WorkflowDetail** view shows the workflow definition and execution history:
- Visual DAG showing steps and connections (read-only)
- Run history: paginated list of all runs, sorted by recency
- Click any run to drill into the WorkflowRunDetail overlay

### Workflow Run Detail

The **WorkflowRunDetail** overlay (on top of the DAG) shows live execution status:
- **DAG with status colors:** Steps are coloured RUNNING (blue), COMPLETED (green), FAILED (red), CANCELLED (grey), SKIPPED (faded)
- **Step log drawer:** Click any step to see logs (from the underlying job) and the step's result.json
- **Real-time updates:** WebSocket broadcasts status changes; no page refresh needed
- **Status badge:** Shows the run's overall status (RUNNING, COMPLETED, PARTIAL, FAILED, CANCELLED)

## Monitoring via API

### REST Endpoints

- **`GET /api/workflows`** — List all workflows (paginated)
- **`GET /api/workflows/{id}`** — Get workflow details (steps, edges, parameters)
- **`GET /api/workflows/{id}/runs`** — List runs for a workflow (paginated)
- **`GET /api/workflows/{id}/runs/{run_id}`** — Get run status and all step statuses
- **`GET /api/executions/{job_guid}/logs`** — Get logs for a specific job (step run)

### WebSocket Real-Time Updates

Connect to `/ws?token=<jwt>` and listen for:
- **`workflow_run_updated`** — Emitted when a run transitions status (RUNNING→COMPLETED, etc.)
- **`workflow_step_updated`** — Emitted when a step transitions status (PENDING→RUNNING, RUNNING→COMPLETED, etc.)

Polling alternative: Call `GET /api/workflows/{id}/runs/{run_id}` every 5-10 seconds for status updates.

## Common Operator Tasks

### Viewing Current Execution Status

**Dashboard:** Workflows → click a workflow → click a run → live DAG shows status colours
**API:** `GET /api/workflows/{id}/runs/{run_id}` returns full run + step statuses

### Cancelling a Running Workflow

**Dashboard:** Workflows → click a run → Cancel button
**API:** `DELETE /api/workflows/{id}/runs/{run_id}`

Cascades CANCELLED status to all PENDING/RUNNING steps.

### Re-triggering a Failed Workflow

Currently: Manual re-trigger from dashboard (Phase 151 UI). No automatic retry yet.
**API:** `POST /api/workflows/{id}/runs` with optional parameter overrides

### Debugging a FAILED vs PARTIAL Status

- **PARTIAL = expected.** At least one branch took a failure path (controlled by IF gate). The workflow executed correctly.
- **FAILED = unexpected.** A non-isolated step failed; downstream steps cascaded. Check the DAG to see which step failed; click it in the log drawer to view error details.

### Checking Webhook Signature Issues

If webhook events are rejected (400 Bad Request):
1. Verify HMAC-SHA256 signature: `HMAC-SHA256(secret, payload + timestamp)` matches the `X-Signature` header
2. Check timestamp freshness: Event timestamp must be within ±5 minutes of current time
3. Check nonce uniqueness: Event nonce must not have been seen in the last 24 hours (deduplication prevents replay attacks)

Contact support if signature generation is unclear — most webhook providers (AWS, GitHub, etc.) have standard HMAC libraries.
