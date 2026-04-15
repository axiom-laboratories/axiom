# Feature Landscape: DAG/Workflow Orchestration for Axiom

**Domain:** Distributed job orchestration with visual workflow authoring  
**Researched:** 2026-04-15  
**Scope:** Features for workflow/DAG milestone building on top of existing single-job orchestration  

---

## Executive Summary

Axiom's workflow orchestration layer extends the existing job dependency engine (`depends_on`, `BLOCKED`/`COMPLETED`/`FAILED`, cascade cancellation) with visual workflow definition, parameter injection, and conditional branching. 

This research identifies three feature categories:

- **Table Stakes:** Visual DAG monitoring, parameterized workflows, conditional branching (IF gates), step-level execution history
- **Differentiators:** Workflow versioning with immutable job snapshots, partial failure handling with explicit PARTIAL state, structured output contracts for reliable conditional routing
- **Anti-Features:** Template string interpolation (breaks cryptographic job signing), loose parameter passing (RCE vector), unvalidated DAG definitions (DoS and deadlock risks)

The design doc's Phase 1a/1b/2 strategy aligns with industry patterns, but **Phase 1b must pivot from template substitution to environment variable injection** to preserve Ed25519 signature integrity. This is non-negotiable: nodes verify script content cryptographically, and any orchestrator-side rendering breaks the trust model.

---

## Table Stakes

Features users expect without question. Missing = product feels incomplete for DAG use cases.

| Feature | Why Expected | Complexity | Implementation Notes |
|---------|--------------|-------------|----------------------|
| **Visual DAG Editor (Read-Only First)** | Users need to see workflow structure as a directed graph, not as raw JSON | Medium | Use Dagre layout algorithm; node colours reflect status (PENDING/RUNNING/COMPLETED/FAILED/CANCELLED); existing job detail drawer opens on node click |
| **Parameterized Workflows** | ETL pipelines must be reusable across different dates, client IDs, environments without duplicating logic | Medium | Parameters passed via `WORKFLOW_PARAM_*` environment variables (NOT template substitution). Params injected by node at runtime into container environment before script execution. Signature covers raw `ScheduledJob.script_content` only, not rendered version. |
| **Conditional Branching (IF Gates)** | Workflows need to route to different steps based on job results (e.g., "if validation passed, load; if validation failed, alert and reprocess") | Medium | IF gate evaluates structured output from upstream job. Structured output written by script to `/tmp/axiom/result.json` (file-based contract, not stdout parsing). Node captures this and returns as `result.structured_output`. Supports operators: `eq`, `neq`, `gt`, `lt`, `gte`, `lte`, `contains`, `exists`, `is_null`. First-match evaluation; fallthrough/default branch optional. |
| **Step-Level Execution History** | Operators must see which steps ran, which failed, and why—without reconstructing from job queue | High | `WorkflowRunStep` table links each step in a workflow run to its instantiated `Job`. Query endpoint returns step details: name, status, job GUID, start time, duration, stdout/stderr. Export as CSV or JSON. |
| **WorkflowRun Rollup Status** | Dashboard must show workflow-level health (RUNNING/COMPLETED/PARTIAL/FAILED/CANCELLED), not just individual job status | Medium | Rollup triggered whenever any job in run reaches terminal state. Walk `WorkflowRunStep` records and re-evaluate: COMPLETED if all steps done and no unhandled failures; PARTIAL if failures handled by FAILED-condition downstream steps; FAILED if unhandled failure exists; CANCELLED if run cancelled manually. Update `WorkflowRun.status` and `completed_at`. |
| **Unified Schedule View** | Operators need a single timeline showing upcoming cron executions from both `ScheduledJob` and `Workflow` records | Medium | Single sorted list by next trigger time, mixing `ScheduledJob` and `Workflow` entries. Type badge shows JOB vs FLOW. Last run status uses distinct colours: green (COMPLETED), amber (PARTIAL), red (FAILED). |
| **Manual Trigger** | Workflows must be triggerable on-demand with parameters supplied at runtime | Low | API endpoint `POST /workflows/{id}/run` accepts `params` dict validated against `Workflow.params_schema`. Creates `WorkflowRun` record. Dispatches all PENDING steps immediately. |
| **Execution Timeout per WorkflowRun** | Prevent runaway workflows from consuming resources indefinitely | Low | `WorkflowRun.timeout_seconds` field. Background task checks `now() > triggered_at + timeout_seconds`; if exceeded, mark run `CANCELLED` and cascade-cancel all non-terminal steps. |

---

## Differentiators

Features that set Axiom apart. Not expected by default, but valued once present.

| Feature | Value Proposition | Complexity | Implementation Notes |
|---------|-------------------|------------|----------------------|
| **Workflow Versioning with Immutable Job Snapshots** | Workflows reference a specific `version_id` or `content_hash` of each `ScheduledJob` step, preventing silent regressions when job definitions are edited | High | Add `version_id` (UUID) and `content_hash` (SHA256 of script) to `ScheduledJob`. Workflows store `{"step_id": "extract", "scheduled_job_version_id": "uuid-v1", ...}`. Editing a job creates a new version; existing workflows stay pinned to old version. UI shows "Update available" badge and explicit "Upgrade to v2" action. Prevents "I edited the job to fix a bug in Workflow A but it silently broke Workflow B" operational hazard. |
| **Partial Failure Handling as Explicit PARTIAL State** | Distinguish between "workflow failed unexpectedly" (red, requires action) and "workflow handled its error cases correctly" (amber, expected state). Enables operators to set different alert thresholds and SLA tracking. | Low | Implement WorkflowRun status rollup as documented in design doc §6. PARTIAL is not a failure state—it means failures were anticipated and handled by downstream FAILED-condition branches. Colour UI distinctly from FAILED. |
| **Rerun from Failure Point** | After a workflow fails at step 5 of 10, rerun only steps 5–10 instead of the entire workflow—saves time and cost | Medium | `POST /workflows/{id}/run?rerun_from_step=step_id` creates new `WorkflowRun` with same params but skips COMPLETED/PARTIAL steps and re-dispatches from the specified step. Requires careful dependency graph analysis to ensure upstream state is valid. Mark reruns with `parent_run_id` for traceability. |
| **Run History with Comparison** | Dashboard shows all past runs of a workflow with side-by-side comparison of params, duration, status, and cost | Medium | Query endpoint `GET /workflows/{id}/runs` with pagination, filtering by date range and status. Run detail view shows all steps, duration per step, cost per step (if nodes report resource usage), and param values at trigger time. |
| **Workflow Export/Import as YAML/JSON** | Operators can version workflows alongside code, use template inheritance, and share workflows across deployments | Medium | Serialize `Workflow.steps`, `params_schema`, `trigger_config` as YAML/JSON. `POST /workflows/import` deserializes and validates before saving. Solves "I want to define workflows in Git and deploy via CI/CD" pattern. |
| **Scheduled Workflow Dryrun** | Before committing a workflow to production schedule, run it once with test params to validate DAG structure and script content | Low | API endpoint `POST /workflows/{id}/dryrun?params={...}` executes the workflow once, creates a `WorkflowRun` with `dryrun=true` flag (excluded from metrics), and returns the run history for inspection. UI shows dryrun results before "Activate Schedule" button becomes enabled. |
| **Fan-In Gate (AND/OR semantics)** | Explicitly model when a workflow step waits for multiple upstream branches to complete (AND) or proceeds when any branch completes (OR) | Low | Canvas UI represents AND/OR gates as first-class node types. Under the hood, AND gate becomes a step with multiple `depends_on` entries; OR gate uses `condition: "ANY"`. Simplifies DAG authoring for parallel patterns. |
| **Parallel Fan-Out with Concurrency Limit** | When a step triggers multiple parallel steps, limit how many run simultaneously to prevent thundering herd on shared resources | Medium | `WorkflowRun.max_concurrent_steps` field. Scheduler enforces: only dispatch N steps at a time, even if more are unblocked. Queue remaining steps and dispatch as earlier ones complete. Prevents "100 parallel data ingestion jobs all hitting the same API at once and causing cascading failures." |

---

## Anti-Features

Complexity that backfires. Explicitly avoid.

| Anti-Feature | Why Avoid | What to Do Instead |
|--------------|-----------|-------------------|
| **Template String Substitution in Script Content** | FATAL FLAW: nodes verify Ed25519 signatures on exact script content. Any orchestrator-side `{{ }}` rendering changes the content, causing 100% of parameterized jobs to be rejected as `SECURITY_REJECTED`. Also introduces RCE vector: param value `"); import os; os.system('rm /') #` breaks out of string literals. | **Environment Variable Injection:** Keep `ScheduledJob.script_content` immutable. Pass workflow params as JSON in `job.payload.workflow_params`. Node maps params to env vars (`AXIOM_PARAM_TARGET_DATE="2026-04-11"`) before execution. Script reads from `$AXIOM_PARAM_*` at runtime. Signature covers raw template, params are data. Implemented in Phase 1b per design doc correction. |
| **Stdout Parsing for Structured Output** | Last-line-of-stdout parsing is brittle: third-party libraries emit warnings, debug logs, deprecation notices to stdout on exit. Any such output after the "final" JSON breaks the IF gate parser and crashes conditional routing silently and intermittently. | **File-Based Structured Output Contract:** Scripts write structured output to `/tmp/axiom/result.json` (designated file). Node captures this file natively and returns as `result.structured_output` in job result payload. Hard contract, immune to logging frameworks. Move this to Phase 1 (foundational for IF gates). |
| **Unvalidated DAG Definitions** | Accept any workflow JSON without cycle detection or depth limits. Results: (1) cyclic DAGs (A→B→A) hang indefinitely, (2) 50-step pipelines exceed 10-level depth cap and fail at runtime, (3) 100-step parallel fan-outs DOS the orchestrator and worker nodes simultaneously. | **Validation at Save Time:** Implement BFS/DFS cycle detection when workflow is saved. Reject cyclic definitions immediately with clear error. Enforce max step count (e.g., 50 steps per workflow). Enforce max concurrent jobs per WorkflowRun to prevent thundering herd. Evaluate depth at authoring time and flag workflows that exceed typical limits (but allow trusted WorkflowRun flag to bypass DoS cap). |
| **"Warning on Edit" Without Enforcement** | Editing a `ScheduledJob` used by 5 workflows with a warning prompt creates silent regressions: operator forgets to disable old cron schedule or misses that Workflow B will break. "Warning shown" is not the same as "operator understood consequences." | **Immutable Job Versioning:** Editing a `ScheduledJob` creates a new version; existing workflows stay pinned to old version. Workflows require explicit "Upgrade to v2" action to adopt new version. Auto-disable old cron schedule on "Save as New" (don't prompt—prevent ghost executions). Creates audit trail of which workflows use which versions. |
| **Unmatched IF Gate Cascades to Failure** | If no condition matches and there is no fallthrough branch, treat as FAILED and cascade-cancel downstream steps. This destroys the entire rest of the workflow for what is likely an authoring error (operator forgot to define a branch). | **IF Gate Enters WARNING State:** Unmatched gate pauses the WorkflowRun in WARNING state. Alert fires to notify operator. Operator manually inspects the upstream job output and chooses which branch to take via API action. Prevents unintended destruction of downstream steps. |
| **Shallow Dependency Depth Cap** | Existing 10-level cap is DoS protection for raw job submission. For workflows, 10 levels is too shallow: Extract→Decrypt→Validate→Cleanse→Format→Enrich→Aggregate→Push→Audit→Notify is already 10. Adding one IF gate exceeds the cap. | **Workflow-Specific Depth Validation:** Workflows bypass the 10-level runtime cap (trusted `WorkflowRun` flag). Instead, perform cycle detection + depth validation at authoring time. Flag workflows that exceed typical limits (e.g., 50 steps) with a warning but allow them if intentional. Prevents DoS via raw job submission while enabling complex ETL workflows. |
| **Single Execution Plan per Run** | Hard-code execution path at trigger time. If an IF gate result changes operational requirements mid-run, operator must cancel the run and restart—destroying partial progress. | **Deferred IF Gate Routing (Future):** At phase 3b+, allow IF gates to remain unresolved until the upstream job completes, then route dynamically. Requires stronger state machine but enables "smart" workflows that adapt to runtime results. Keep as future enhancement; implement hard routing first. |

---

## Feature Dependencies

| Feature | Depends On | Why |
|---------|-----------|-----|
| IF gate (conditional branching) | Structured output contract (file-based `/tmp/axiom/result.json`) | Must have deterministic, reliable way to extract routing data from job output |
| IF gate | Phase 1a (WorkflowRun + WorkflowRunStep tables) | Need to track which step is which and store branch decision in run history |
| Workflow versioning | Job versioning (version_id, content_hash on ScheduledJob) | Workflows must pin to specific job versions, not float to latest |
| Rerun from failure point | Run history UI + step-level execution tracking | Must know which steps COMPLETED vs FAILED to determine valid restart points |
| Unified schedule view | Phase 2 (Workflow template entity with cron config) | Must query both ScheduledJob and Workflow tables for next trigger times |
| Parallel fan-out with concurrency limit | Phase 1a (WorkflowRun entity) | Must coordinate max concurrent dispatch at the run level, not task level |
| Manual trigger | Phase 1b (parameter injection) | Must accept runtime params and validate against params_schema |

---

## MVP Recommendation

**Prioritize Phase 1a + 1b + 2 completely before Phase 3 visual authoring.**

### Minimum Viable Feature Set

**Phase 1a + 1b + 2 (Delivery target: 4–6 weeks)**
1. `WorkflowRun` + `WorkflowRunStep` tables with status rollup
2. `WORKFLOW_PARAM_*` environment variable injection (NOT template substitution)
3. `Workflow` template entity: steps JSONB, params_schema, trigger_config
4. Manual trigger API endpoint with param validation
5. Scheduled execution via APScheduler (reuse existing scheduler + add Workflow query target)
6. Unified schedule view showing `ScheduledJob` + `Workflow` entries
7. Read-only DAG visualiser using Dagre (immediate operational value, no edit capability)
8. `/tmp/axiom/result.json` contract for structured output (foundational for IF gates)
9. Step-level execution history with stdout/stderr in job detail drawer

**Defer to Phase 3b (Delivery target: weeks 7–10)**
1. Visual authoring canvas (drag-drop, edge drawing)
2. IF gate runtime evaluation logic
3. AND/OR/JOIN gates as explicit canvas nodes
4. Parallel fan-out with concurrency limiting

### Features to Defer Beyond This Milestone

- Workflow versioning (requires ScheduledJob version infrastructure first)
- Rerun from failure point (implement run history UI first; routing logic is Phase 3b work)
- Workflow export/import as YAML/JSON (nice-to-have; not blocking production use)
- Dryrun mode (implement after core execution is stable)
- Workflow comparison view (implement after run history is solid)

---

## Complexity Assessment

| Area | Complexity | Notes |
|------|-----------|-------|
| **Data Model** | Low–Medium | Three new tables (`workflow_run`, `workflow_run_step`, `workflow`); foreign keys to existing `Job` and `ScheduledJob`; status rollup logic is BFS traversal, well-understood |
| **Parameter Injection** | Low | Fetch `WorkflowRun.params` → map to env vars → pass to node. Node injects before script execution. No orchestrator-side rendering. Reuses existing job dispatch path. |
| **Structured Output Contract** | Low | Node already captures stdout/stderr per job. Add file mount at `/tmp/axiom/result.json`; node reads and returns in result payload. No new execution mode needed. |
| **Scheduler Integration** | Low | Add second query target in APScheduler loop: `ScheduledJob` (existing) + `Workflow` with `trigger_config.type="cron"` (new). Route to appropriate handler. Reuse trigger_service instantiation pattern. |
| **Status Rollup** | Medium | Implement as background task or event-driven: whenever job reaches terminal state, query `WorkflowRunStep` for the run, evaluate rules, update `WorkflowRun.status` and `completed_at`. Need to handle race conditions (multiple jobs completing simultaneously). |
| **IF Gate Routing** | Medium | Parse structured output JSON, evaluate condition expression against it, follow branch. Requires condition expression evaluator (simple: no Jinja2, just basic operators like `eq`, `neq`, `gt`, `contains`). |
| **Unified Schedule View** | Medium | Query `ScheduledJob` for next N cron fires, query `Workflow` for next N cron fires, merge, sort by next trigger time, paginate. Schema union of both types' response fields. |
| **Read-Only DAG Visualiser** | Medium | Dagre layout algorithm (well-maintained JS library), node colouring by status, click-to-detail interaction. Reuses existing job detail drawer. No new backend work beyond exposing step/edge data via API. |
| **Visual Authoring Canvas** | High | Drag-drop node creation, edge drawing with condition editor, validation on save, live preview of rendered JSONB. Requires significant React state management and canvas interaction handling. |

---

## Axiom-Specific Considerations

### Signature Integrity (Critical)

The design doc's Phase 1b must use **environment variable injection, not template substitution**. This is non-negotiable:

- Nodes verify Ed25519 signatures on exact script content (`Script.content == signed.content`)
- Any orchestrator-side rendering of `{{ param }}` changes the content hash → signature fails
- 100% of parameterized workflow jobs would be `SECURITY_REJECTED`
- Environment variables avoid this: script stays signed, params are runtime data
- This also eliminates RCE vector from malicious param values breaking string literals

The design doc already correctly identifies this flaw in the adversarial reviews. Ensure Phase 1b implementation uses env vars, not `{{ }}` substitution.

### Reuse of Existing Dependency Engine

Axiom's existing primitives handle 95% of DAG orchestration:
- `depends_on` field with `COMPLETED`, `FAILED`, `ANY` condition types
- Cascade cancellation via `_cancel_dependents` BFS
- Transitive unblocking via `_unblock_dependents`
- Job signing and verification on every execution
- Execution record with stdout/stderr/exit code

The workflow engine is a **second trigger mechanism** alongside cron. No refactoring of the job engine itself is needed. Workflows instantiate jobs and wire dependencies exactly like scheduled execution does today.

### Container Execution for Isolation

Axiom runs all jobs in ephemeral containers (Docker/Podman). This is a security strength for workflows:
- IF gates can safely write `/tmp/axiom/result.json` without worrying about cross-job interference
- Parameter injection via env vars is standard container practice
- No new execution modes needed; reuse existing `runtime.py`

### Concurrency and Resource Limits

Axiom already supports per-job resource limits (`memory_limit`, `cpu_limit`). For workflows:
- `WorkflowRun.max_concurrent_steps` prevents thundering herd of parallel steps
- Scheduler enforces: dispatch N steps at a time, queue remainder
- Reuses existing node admission control logic

---

## Sources

- [Airflow vs Dagster vs Prefect: Which Workflow Orchestrator Should You Choose in 2026?](https://bix-tech.com/airflow-vs-dagster-vs-prefect-which-workflow-orchestrator-should-you-choose-in-2026/)
- [Rerun Airflow DAGs and tasks - Astronomer Documentation](https://www.astronomer.io/docs/learn/rerunning-dags/)
- [DAG Versioning and DAG Bundles - Astronomer Documentation](https://www.astronomer.io/docs/learn/airflow-dag-versioning/)
- [Handling Failures - Orkes Conductor Documentation](https://orkes.io/content/error-handling/)
- [The Complete Guide to Workflow Orchestration](https://kairntech.com/blog/articles/the-complete-guide-to-workflow-orchestration/)
- [Retry, Timeout, and Dead Letter Handling in Orchestration](https://bugfree.ai/knowledge-hub/retry-timeout-dead-letter-handling-orchestration)
- [AI Workflow Monitoring in Production: The Complete Observability Guide for 2026](https://www.evaligo.com/blog/ai-workflow-monitoring-production-observability-guide/)
- [LLM Workflows: Patterns, Tools & Production Architecture (2026)](https://www.morphllm.com/llm-workflows)
- [25 Workflow Automation and Process Agent Patterns on AWS](https://buildwithaws.substack.com/p/25-workflow-automation-and-process)
