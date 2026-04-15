# Feature Landscape: DAG Workflow Orchestration

**Domain:** Multi-job orchestration with conditional execution
**Researched:** 2026-04-15

---

## Table Stakes

Features users expect for a "workflow" product to feel complete.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| **DAG definition & storage** | Users need to define workflows visually or programmatically | Low | JSON schema in DB; canvas editor optional |
| **Job dispatch in dependency order** | Workflows must execute jobs according to graph topology | Med | Topological sort + BFS |
| **IF/branching gates** | Workflows need conditional logic (e.g., "deploy only if tests pass") | Med | Jinja2 template evaluation |
| **Webhook ingestion** | CI/CD integration requires external trigger mechanism | Med | HMAC-SHA256 verified endpoint |
| **Execution history & runs** | Users need visibility into workflow execution (when did it run, what failed) | Low | WorkflowRun + WorkflowRunStep tables |
| **Job result inspection** | Gate conditions read job output (exit code, stdout); users inspect this in UI | Low | Structured JSON result caching |
| **Cancellation cascade** | If a gate fails, downstream jobs must be skipped (not execute) | Low | Already exists for job chains; adapt for DAG |

---

## Differentiators

Features that set Master of Puppets DAG apart from competitors. Not expected, but valuable.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| **Canvas editor with drag-drop nodes** | Operator-friendly; no YAML/JSON editing required | High | React Flow library |
| **Test mode (dry-run)** | Preview dispatch order without signing/executing | Med | Gate evaluation on mock data |
| **Node capability matching** | Workflows route jobs to nodes with required capabilities (e.g., "Python 3.11 + Docker") | Med | Reuse existing job targeting logic |
| **Job template integration** | Drag job templates into canvas; auto-populate parameters | Med | Bind to existing ScheduledJob records |
| **Execution retry within workflow** | If a step fails, retry it without re-running entire workflow | Low | Existing job retry logic applies |
| **Parallel fan-out** | Multiple downstream jobs execute concurrently (not sequentially) | Low | Already supported by BFS (no edges = parallel) |
| **Cross-workflow dependencies** | Chain entire workflows together (workflow calls another workflow) | High | Recursive WorkflowRun dispatch; deferred to v2 |
| **Workflow versioning** | Edit workflow DAG without affecting in-flight runs (Airflow 3.0 pattern) | Med | Pin DAG snapshot at dispatch time |
| **Audit trail of gate conditions evaluated** | Track which conditions passed/failed and why (compliance) | Low | Store condition + result in WorkflowRunStep |

---

## Anti-Features

Features to explicitly NOT build.

| Anti-Feature | Why Avoid | What to Do Instead |
|--------------|-----------|-------------------|
| **Dynamic DAG generation** | Generates complexity (Airflow 2.x → 3.x migration issue); hard to visualize | Require explicit DAG definition; support variables/parameters instead |
| **Turing-complete condition language** | Security risk (eval); hard to audit | Restrict to Jinja2 with sandboxed context |
| **Workflow-global state** | Violates job isolation; breaks parallelism | Pass state via job result (structured JSON) |
| **Visual debugging in browser** | Would require live agent introspection (complex); operator latency sensitive | Provide execution logs and result inspection (existing) |
| **Workflow scheduling with cron** | Overlaps with APScheduler (existing); DAG cron = ScheduledJob + trigger | Use existing cron for root job, trigger workflow from that |
| **Resource reservation** | Complex multi-job resource planning; not part of MVP | Rely on per-job resource admission (existing) |

---

## Feature Dependencies

```
Foundation:
  - WorkflowRun (data model)
  - WorkflowRunStep (data model)
  - DAG JSON schema

Core Orchestration:
  - dispatch_workflow_run() → depends on: DAG + WorkflowRun model
  - _unblock_workflow_steps_after_job() → depends on: dispatch + job completion hook
  - _evaluate_gate_condition() → depends on: Jinja2 library

Webhook Trigger:
  - POST /api/workflows/{id}/trigger → depends on: dispatch_workflow_run

REST API:
  - GET/POST/PATCH/DELETE /api/workflows → depends on: data model
  - GET /api/workflows/{id}/runs → depends on: WorkflowRun model

Canvas UI:
  - DAG visual editor → depends on: REST API (CRUD)
  - Gate condition editor → depends on: _evaluate_gate_condition (backend)
  - Test mode → depends on: everything above
```

---

## MVP Recommendation

**Prioritize (Phase 1–3, ~6 days):**
1. WorkflowRun data model & BFS orchestrator (core logic)
2. Webhook ingest with HMAC-SHA256 (CI/CD enabler)
3. REST CRUD for workflow definitions (operational necessity)
4. Gate conditions with Jinja2 (core feature)

**Defer to v2 (Post-MVP):**
- Canvas editor (can use raw JSON POST for v1; operators export DAG from other tools)
- Workflow versioning (simple: pin DAG at dispatch time; explicit versioning later)
- Parallel fan-out optimization (works without optimization; BFS is concurrent-safe)
- Cross-workflow dependencies (recursive dispatch; architectural complexity)

**Deliverable:** Operators can POST `/api/workflows` with DAG JSON, trigger via webhook (e.g., GitHub Actions), inspect runs in dashboard. No canvas UI in MVP.

---

## User Workflows

### Workflow 1: Multi-Stage Deployment (via Webhook)

```
CI/CD Pipeline (GitHub Actions) triggers:
  POST https://agent:8001/api/workflows/deploy-main/trigger
  X-MOP-Webhook-Signature: sha256=<hmac>
  Body: {"version": "v1.2.3", "timestamp": 1713188400}

Server dispatches WorkflowRun:
  - step_1_validate (lint code)
  - step_2_test (unit tests)
  - step_3_gate (if step_2 exit_code == 0)
  - step_4_build (docker build)
  - step_5_deploy_staging (deploy if not gate)
  - step_6_smoke_test (test staging)
  - step_7_gate_deploy (if smoke test passes)
  - step_8_deploy_prod (final deployment)

Operator watches in Dashboard:
  - WorkflowRun live progress
  - Gate conditions and why they passed/failed
  - Job stdout/stderr inline
  - Can click "Pause at next gate" to inspect before prod deploy
```

### Workflow 2: Data Pipeline with Retries (Manual Trigger)

```
Operator POSTs /api/workflows/daily-etl/trigger (manual dispatch)

Server dispatches:
  - step_1_extract (query remote API)
  - step_2_gate (if exit_code == 0, continue; if timeout, retry entire workflow)
  - step_3_transform (Spark job)
  - step_4_load (write to warehouse)
  - step_5_audit (validate row counts match)

If step_1 fails (network timeout), existing job retry logic retries step_1.
Once step_1 succeeds, gate evaluates and unblocks step_2, etc.
Operator can inspect audit results in step_5 result JSON (structured output).
```

### Workflow 3: Parallel Testing (Fan-out)

```
DAG structure:
  step_1_checkout (serial)
    ↓
  step_2_test_python (parallel ↙ ↓ ↘ step_2_test_golang, step_2_test_rust)
    ↓
  step_3_gate (all tests must pass)
    ↓
  step_4_publish (serial)

BFS dispatch sends step_2_test_python, step_2_test_golang, step_2_test_rust
simultaneously to eligible nodes (all have capabilities).
Gate waits for all three to complete (all(upstream.status in ["COMPLETED", "SKIPPED"])).
```

---

## Success Metrics

- **MVP ready when:** Operators can define workflows in JSON, trigger via webhook, and inspect runs
- **v2 ready when:** Canvas editor ships (usability boost) + workflow versioning (deployment safety)
- **Mature when:** Cross-workflow dependencies + parallel optimization (scale to 1000+ step workflows)

---

## Open Questions

1. **Workflow parameters:** Should workflows accept input variables (e.g., `{"version": "v1.2.3"}` in webhook payload)? Where does this data flow?
   - *Likely answer:* Yes; pass via `trigger_payload` JSON, make available in gate conditions as `{{ params.version }}`

2. **Webhook retry policy:** If webhook dispatch fails (network error), should caller retry, or is fire-and-forget?
   - *Likely answer:* Fire-and-forget (like GitHub webhooks); caller responsible for retries

3. **Step timeout:** Can an individual step timeout, or only the entire workflow?
   - *Likely answer:* Inherit from job timeout (existing); each step inherits its job definition's timeout

4. **Output data passing:** Can downstream jobs access upstream job output directly (not just gate evaluation)?
   - *Likely answer:* v1 = gate evaluation only; v2 = inject result as env var or file
