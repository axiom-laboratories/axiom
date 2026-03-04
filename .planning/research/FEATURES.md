# Feature Research

**Domain:** Distributed job scheduler / task orchestration (homelab + enterprise)
**Researched:** 2026-03-04
**Confidence:** HIGH (core patterns verified across Airflow, Rundeck, Prefect, Temporal, BullMQ, SQL Server Agent; MEDIUM for some CI/CD specifics)

---

## Context: What Already Exists

The system already has a functioning core. This research targets the *missing* capabilities
listed in PROJECT.md. Features are evaluated from the perspective of users who already have:
mTLS, signed jobs, container isolation, RBAC, cron scheduling, Foundry image builder,
node stats history, audit log, and service principals.

---

## Feature Landscape

### Table Stakes (Users Expect These)

Features users assume exist in any production job scheduler. Missing these means the product
feels like a prototype, not a production tool.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| **Job output capture (stdout + stderr)** | Every production scheduler stores execution output — PBS Pro, LSF, Jenkins, Rundeck, Airflow all do this. Without it, debugging failures is impossible. | MEDIUM | Output must flow from node back to orchestrator since nodes are stateless between polls. Store as Text column on Job or a separate `job_outputs` table. Apply a size cap (4–20 MB typical; GitLab default is 4 MB). Truncate from the top, preserve tail. |
| **Exit code capture** | Operators need to know if a job exited 0 or non-zero. Status FAILED covers this coarsely, but raw exit code is necessary for debugging scripts that exit intentionally with non-zero. | LOW | Add `exit_code` (nullable Int) to Job model. Nodes already report `success: bool` via `ResultReport` — extend to include exit code. |
| **Execution duration tracking** | Every scheduler shows "how long did this run?" Dashboard already computes this from `started_at`/`completed_at` but it is not surfaced in the Jobs view. | LOW | Already in DB; needs UI exposure. |
| **Execution history timeline** | Users expect to see past runs — at minimum: timestamp, node, duration, exit status. Rundeck, Jenkins, Airflow all provide this. | MEDIUM | Currently only the live jobs queue exists. Needs a separate view (or tab) showing historical executions, filterable by job definition, node, status, time range. Requires keeping completed Job rows (they are kept, just not well-surfaced). |
| **Filter/search execution history** | No production tool ships history without search. Minimum filters: date range, status (success/failure), job definition name, node. | MEDIUM | Backend: query parameters on `GET /jobs/history`. Frontend: filter bar with date picker, status multi-select, node selector. |
| **Retry on failure** | Any scheduler users compare to (cron with supervisord, Celery, Airflow, Temporal, BullMQ) retries failed jobs. Absent = jobs silently die on transient failures. | MEDIUM | Needs `retry_count`, `retry_max`, `retry_backoff`, `retry_delay_seconds` on ScheduledJob. On job failure, scheduler_service re-enqueues with incremented attempt counter. Must respect backoff strategy. |
| **Configurable retry count** | The number of retries must be operator-configurable per job definition, not system-wide. | LOW | Extend `JobDefinitionCreate`/`JobDefinitionUpdate` with `retry_max: int = 0`. Zero means no retries (safe default). |
| **Environment node tags (DEV/TEST/PROD)** | Any team running more than one environment expects nodes to be tagged by environment and job targeting to respect those tags. Nodes already support `tags` (JSON list) but no UI convention enforces DEV/TEST/PROD semantics. | LOW | This is mostly a convention + UI concern. The tag system already supports this. Needs: (1) documented convention, (2) dashboard to show environment distribution, (3) CI/CD integration that sends the right environment tag as part of the dispatch payload. |
| **Machine-friendly job dispatch API** | Service principals + API keys already exist. What is missing is documented, stable, CI/CD-optimized endpoints that return immediately with a job GUID and allow polling for result. | LOW | The POST /jobs endpoint already accepts API key auth. What is needed: (1) documented stable API contract, (2) a `GET /jobs/{guid}/result` that blocks briefly or returns 202 while pending, (3) clear error shapes. |
| **Output retention policy (configurable)** | Operators need to prevent the output table from growing unbounded. SQL Server Agent defaults to 1000 rows total/100 per job. Harness caps at 5000 lines. GitLab caps at 4 MB. | MEDIUM | System-level config: max output size per job (bytes), max execution history rows (total and per job definition). Prune via background task (APScheduler already available). Flag similar to MIN-6 (SQLite compat needed). |

### Differentiators (Competitive Advantage)

Features that distinguish this system from commodity cron replacements and position it
competitively against Rundeck/Airflow for security-first deployments.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| **Exponential backoff retry with jitter** | Most homelab schedulers offer "retry N times" but not "retry with exponential backoff + jitter". BullMQ and Temporal do this; Airflow does it via task config. Jitter prevents thundering herd when many jobs fail simultaneously (e.g., shared database goes down). | MEDIUM | Strategies: immediate, linear, exponential (2^attempt * base_delay). Add jitter as ±20% of computed delay. Cap at configurable max delay. |
| **Dead letter / permanent-failure queue** | After max retries, job moves to a "dead letter" state (separate from FAILED). Operators can inspect, re-queue manually, or discard. Temporal and BullMQ treat this as standard; Airflow calls it "zombie" detection. | MEDIUM | New status: `DEAD_LETTER`. Dashboard view for dead-letter jobs distinct from ordinary failures. Manual re-queue button. This closes the loop on the retry system. |
| **Output streaming (WebSocket-backed)** | Buffered output shown after job completes is table stakes. Streaming output in near-real-time while a job is running is a differentiator. The system already has a WebSocket infrastructure (`/ws`). The pattern: nodes stream output lines back via heartbeat extensions or a dedicated output chunk endpoint, orchestrator forwards via WebSocket to dashboard. | HIGH | Implementation path: node POSTs output chunks to `/work/{guid}/output` during execution (small HTTP calls fit the pull model); orchestrator buffers and broadcasts via existing WebSocket. Alternatively, batch output at completion and use polling from UI during "RUNNING" state (simpler, lower value). The streaming path is a strong differentiator; the polling path is table stakes. |
| **Job dependency (sequential chaining)** | Job B runs only after Job A succeeds. Not a full DAG — just a linear "run-after" dependency. Full DAG editors are complex and a known anti-feature trap (see below). Linear chaining covers 80% of real use cases: DB backup → verify → notify. | HIGH | Data model: `ScheduledJob.depends_on_job_id` (nullable FK). Scheduler evaluates dependencies before enqueuing. Failure of upstream blocks downstream (configurable: fail-fast vs. skip). UI: simple "depends on" selector in job definition editor. |
| **Explicit retry audit trail** | Each retry attempt is recorded as a separate execution record with its own output, exit code, and attempt number. Users can see "attempt 1 failed with exit 1, attempt 2 failed with exit 137 (OOM), attempt 3 succeeded". This is not standard in simpler schedulers. | MEDIUM | `job_executions` table (separate from `jobs`): `job_guid`, `attempt`, `node_id`, `exit_code`, `output`, `started_at`, `completed_at`, `status`. The parent `jobs` row holds the aggregate status. |
| **CI/CD webhook endpoint with async result polling** | GitHub Actions / GitLab CI can trigger a job dispatch and poll for completion. The pattern: POST /jobs returns 202 + GUID immediately. CI polls GET /jobs/{guid}/status until terminal state. This is what Rundeck's Jenkins plugin does. Since service principals already exist, the auth story is complete — only the endpoint contract and documentation are missing. | LOW | Primarily documentation + minor API additions. The difficult part (auth) is already done. Add: `GET /jobs/{guid}/status` with 200 (pending/running) vs 200 (complete) distinction, and `GET /jobs/{guid}/result` for output. Write an example GitHub Actions workflow step using `curl` + polling loop. |
| **Environment promotion workflow documentation** | Targeting DEV nodes is easy (tag filter). Promoting a job definition from DEV to PROD is harder: it requires re-signing with the PROD signing key, updating target tags. Document this as a canonical workflow with a CI/CD example. The system already supports everything technically; no new code is needed — just documented patterns and a UI affordance that shows which environments a job definition targets. | LOW | Add environment badges to JobDefinitions view. Write a "promotion guide" in Docs.tsx. |

### Anti-Features (Commonly Requested, Often Problematic)

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|-----------------|-------------|
| **Full visual DAG editor** | Users see Airflow's graph view and want drag-and-drop dependency building | DAG editors are enormously complex to build correctly. Airflow's own community acknowledged the DAG editor was a years-long weak point (Airflow Summit 2026 had a talk titled "Demo: Reducing the lines, a visual DAG editor" — still not shipped in 3.1). Rendering large graphs in React/ReactFlow is a known scalability problem (Dagster blog: "novel challenges delivering excellent UX when the UI renders enormous graphs"). For this system's security model, DAGs also create a problem: each node in a DAG must be a signed job definition — the editor would need to know the signing story for each task. This is infeasible without a signing UX redesign. | Simple linear "depends on" selector for sequential chains. For fan-out/fan-in, expose a code-defined JSON format that operators can construct and version-control — same pattern Kestra uses with declarative YAML. |
| **Real-time streaming output for all jobs** | Operators want to watch jobs run like a terminal | True streaming requires the node to maintain an open connection or frequently POST chunks back, which conflicts with the pull architecture's simplicity. The pull model was deliberately chosen to avoid inbound firewall rules on nodes. Forcing streaming requires nodes to either hold a connection open (breaking statelessness) or bombard the orchestrator with tiny HTTP POSTs (network overhead). | Buffered output delivered at job completion is sufficient for 95% of use cases. Offer a configurable "output chunk interval" (e.g., node POSTs output every 30 seconds for long-running jobs) as an opt-in, not default. |
| **Per-job secrets injection at dispatch time** | Operators want to pass database passwords, API tokens, etc. when dispatching a job | The PROJECT.md explicitly scopes this out: "no built-in secrets management beyond Fernet-at-rest — use external vault for production secrets". Implementing secrets injection requires: secure transport (mTLS handles this), storage at rest (Fernet handles this already for node credentials), and audit of secret access. The risk is that operators start storing production credentials in job payloads, which were never designed to be secrets-safe. | Document the pattern of injecting secrets via environment variables on the node (set in the node's compose file), not via job dispatch payloads. For dynamic secrets, document integration with Vault via the node's environment. |
| **Job script versioning / SCM built-in** | Users want Git-like history of script changes | Script versioning creates a false sense of security. The system's actual provenance model is Ed25519 signing: the signature IS the version + authorship attestation. A separate versioning system alongside signing creates confusion about which is authoritative. It also means building a diff viewer, branch model, etc. — a significant scope expansion. | Document that job definitions should be authored and version-controlled in Git, then uploaded + signed via the admin_signer tool. The audit log already records who changed what and when. |
| **Unlimited output retention** | "Just keep everything forever" | Unbounded output storage will degrade query performance for SQLite users (homelab), and create runaway disk usage for high-frequency jobs. A job that runs every minute and produces 100 KB of output accumulates 144 MB/day. | Configurable retention policy: max output bytes per job, max history rows per job definition, TTL for completed job records. Default to sensible limits (e.g., 50 last runs per definition, 1 MB max per output). |
| **Push-based node dispatch** | "Can the orchestrator push work directly to nodes for lower latency?" | The pull architecture is a security design decision, not a performance trade-off. Push would require the orchestrator to initiate TCP connections to nodes, requiring inbound firewall rules on every node. The nodes were deliberately designed to work across NAT and hostile networks. Reversing this would undermine the entire deployment model. | If lower latency is needed, reduce the node poll interval (currently configurable). Nodes can poll every 1–2 seconds for interactive workloads without significant load. |

---

## Feature Dependencies

```
[Exit code capture]
    └──enables──> [Retry policy] (retry decisions require exit code, not just boolean success)
                      └──enables──> [Dead letter queue] (requires knowing when max retries exhausted)
                                        └──enhances──> [Retry audit trail] (DLQ is only useful with full retry history)

[Job output capture] (buffered)
    └──enables──> [Execution history timeline] (history is useless without output)
    └──enables──> [Output streaming] (streaming is an enhancement of buffered capture)
    └──enables──> [Output retention policy] (policy only needed once output is stored)

[Execution history timeline]
    └──requires──> [Job output capture]
    └──enables──> [Filter/search execution history]

[Environment node tags convention]
    └──enables──> [CI/CD webhook endpoint] (CI must know which tag to target)
    └──enables──> [Environment promotion workflow]

[Service principals (already built)]
    └──enables──> [CI/CD webhook endpoint] (auth story complete)
    └──enables──> [Machine-friendly job dispatch API]

[Job dependency (linear chaining)]
    └──requires──> [Execution history timeline] (dependency logic must check prior job outcome)
    └──conflicts──> [Full visual DAG editor] (build one, not both — editor is anti-feature)

[Output streaming]
    └──requires──> [Job output capture] (buffered capture must exist first)
    └──conflicts──> [Pull architecture simplicity] (high-frequency POSTing adds overhead)
```

### Dependency Notes

- **Retry requires exit code capture:** The retry policy must distinguish transient failures
  (exit 1 — script error, retriable) from infrastructure failures (node crashed, retriable)
  from explicit non-retriable failures (exit 42 — "do not retry" signal). Without exit code,
  all retries are blind.

- **Dead letter queue requires retry system:** A DLQ is meaningless without a retry system —
  the DLQ is defined as "where jobs go after exhausting retries". Build retry first.

- **Execution history requires output storage:** A history view that shows "job ran" without
  any output is unhelpful. Both features must ship together.

- **CI/CD integration requires no new auth infrastructure:** Service principals already
  provide the machine auth story (client_id + client_secret → JWT). The CI/CD integration
  work is documentation + endpoint contract, not new authentication code.

- **Linear job chaining conflicts with full DAG editor:** Building both creates confusion
  about which is authoritative. The linear chain covers 80% of real dependency use cases
  and is compatible with the signing model. The full DAG editor is an anti-feature for
  this system's constraints.

---

## MVP Definition

This is a subsequent milestone on an existing system, not a greenfield MVP. "MVP" here means
the minimum set of features that makes this milestone deliverable and useful.

### Launch With (Milestone v1)

These features form a cohesive, working set. Each depends on the previous.

- [ ] **Exit code capture** — extend `ResultReport` and `Job` model; LOW complexity; unblocks everything else
- [ ] **Job output capture (buffered)** — node reports stdout+stderr at completion; stored in DB with size cap; MEDIUM complexity
- [ ] **Execution history timeline** — `GET /jobs/history` endpoint + Jobs History view in dashboard; MEDIUM complexity
- [ ] **Filter/search execution history** — filter bar (status, date, node, job definition); MEDIUM complexity
- [ ] **Retry policy (configurable count + exponential backoff)** — extends job definitions; MEDIUM complexity
- [ ] **Dead letter queue** — new status + DLQ view; MEDIUM complexity; completes the retry story
- [ ] **Environment tags (convention + UI badges)** — LOW complexity; mostly documentation + badge rendering

### Add After Validation (v1.x)

- [ ] **Retry audit trail** — per-attempt execution records in `job_executions` table — add after base retry is working
- [ ] **Output retention policy** — background pruning job — add once output storage is in place and actual sizes are known
- [ ] **CI/CD webhook endpoint + documentation** — endpoint contract + example GitHub Actions step — add when environment tags are stable
- [ ] **Linear job dependency chaining** — "depends on" field + scheduler logic — deferred because it requires reliable execution history first

### Future Consideration (v2+)

- [ ] **Output streaming (real-time chunks)** — HIGH complexity, conflicts with pull simplicity; defer until base output capture is proven reliable
- [ ] **Environment promotion workflow documentation** — documents a process that requires the full milestone to be complete
- [ ] **Fan-out / fan-in patterns** — code-defined (JSON/YAML) parallel job groups — only needed if linear chaining proves insufficient

---

## Feature Prioritization Matrix

| Feature | User Value | Implementation Cost | Priority |
|---------|------------|---------------------|----------|
| Exit code capture | HIGH | LOW | P1 |
| Job output capture (buffered) | HIGH | MEDIUM | P1 |
| Execution history timeline | HIGH | MEDIUM | P1 |
| Filter/search history | HIGH | MEDIUM | P1 |
| Retry policy (count + backoff) | HIGH | MEDIUM | P1 |
| Dead letter queue | HIGH | MEDIUM | P1 |
| Environment tags (convention + badges) | MEDIUM | LOW | P1 |
| Retry audit trail (per-attempt records) | HIGH | MEDIUM | P2 |
| Output retention policy | MEDIUM | MEDIUM | P2 |
| CI/CD webhook endpoint + docs | HIGH | LOW | P2 |
| Linear job dependency chaining | MEDIUM | HIGH | P2 |
| Output streaming (real-time) | MEDIUM | HIGH | P3 |
| Environment promotion documentation | LOW | LOW | P3 |
| Fan-out / fan-in patterns | LOW | HIGH | P3 |

**Priority key:**
- P1: Must have for this milestone to deliver value
- P2: Should have, add when P1 set is proven working
- P3: Nice to have, future milestone

---

## Competitor Feature Analysis

| Feature | Airflow | Rundeck | Prefect | This System |
|---------|---------|---------|---------|-------------|
| Job output capture | Yes (stored per task) | Yes (linked file + inline) | Yes (configurable result storage) | Planned: buffered at completion |
| Execution history | Yes (grid + calendar views) | Yes (activity page, 13 statuses, bulk delete) | Yes (flow runs timeline) | Planned: history endpoint + view |
| History filtering | Yes (DAG, date, state) | Yes (time range, job, user, node, status) | Yes (state, start/end, tags) | Planned: status, date, node, definition |
| Retry policy | Yes (per-task, configurable) | Yes (max retries) | Yes (with exponential backoff) | Planned: count + exponential backoff + jitter |
| Dead letter queue | Partial (zombie detection, manual re-run) | No native DLQ (manual inspection) | No native DLQ | Planned: explicit DEAD_LETTER status + view |
| Job dependencies | Yes (full DAG, cross-DAG) | Partial (job chains via options) | Yes (dynamic DAG) | Planned: linear "depends on" only |
| Visual DAG editor | Beta (Airflow Summit 2026 demo, not shipped) | No | No | Anti-feature: will NOT build |
| CI/CD integration | Yes (Airflow REST API + triggers) | Yes (Rundeck-Jenkins plugin, webhooks) | Yes (REST API + webhooks) | Planned: stable endpoint contract + example |
| Environment tags | Yes (pools, connections, DAG tags) | Yes (node filter tags) | Yes (work pools with env labels) | Exists (node tags); needs convention + promotion docs |
| Output streaming | No (buffered per task) | No (buffered to file) | Partial (real-time UI polling) | Anti-feature for now: pull model conflict |
| Machine auth (service accounts) | Yes (API with token) | Yes (API tokens) | Yes (service accounts) | Already built (service principals + API keys) |
| Output size limits | Yes (configurable) | Yes (file-based, disk limit) | Yes (configurable per result block) | Planned: configurable byte cap, pruning |

---

## Implementation Notes for This System Specifically

### Output Capture Architecture

The pull model means the node cannot push a stream to the orchestrator. Two practical approaches:

**Option A (Recommended for v1): Batch at completion.**
Node finishes job, captures stdout+stderr in memory (up to size cap), includes in `ResultReport`
alongside `exit_code`. Orchestrator stores in `job_outputs` table. Simple, fits existing model.
Size cap: 2 MB default, configurable via `Config` table key `job_output_max_bytes`.

**Option B (Streaming, v2+): Periodic chunk POSTs.**
Node POSTs output chunks to `/work/{guid}/output` every N seconds while running. Orchestrator
appends chunks to buffer, broadcasts via existing WebSocket. N should be operator-configurable
(e.g., 10s–60s). This preserves the pull architecture's security properties while providing
near-real-time visibility for long-running jobs.

### Retry Architecture

Retry logic lives in `scheduler_service.py`. When a job completes with `success=False`:
1. Check `retry_max` on the parent `ScheduledJob`.
2. If `attempt < retry_max`: compute delay using selected strategy, schedule re-enqueue.
3. If `attempt == retry_max`: mark job `DEAD_LETTER`, stop.

Backoff strategies (configurable per job definition):
- `immediate`: retry at once (no delay)
- `linear`: delay = `retry_delay_seconds * attempt`
- `exponential`: delay = `min(retry_delay_seconds * 2^(attempt-1), max_retry_delay_seconds)`
- Apply ±20% jitter to all non-immediate strategies.

Job model additions: `retry_max` (int, default 0), `retry_count` (int, current attempt),
`retry_strategy` (str: immediate/linear/exponential), `retry_delay_seconds` (int, default 60),
`max_retry_delay_seconds` (int, default 3600).

### Execution History Table

The existing `jobs` table keeps all records. For history, a separate `job_executions` table
is preferable to keep parent job rows lean:

```
job_executions:
  id (PK), job_guid (FK→jobs.guid), attempt (int),
  node_id, exit_code, output_text, output_truncated (bool),
  started_at, completed_at, status
```

This cleanly separates "job intent" (jobs table) from "execution record" (job_executions).
The `jobs` table status reflects the aggregate (SUCCEEDED, FAILED, DEAD_LETTER, PENDING).

### CI/CD Integration Contract

The recommended stable contract for CI/CD consumers (GitHub Actions, GitLab CI, scripts):

```
POST /jobs                          → 202 { guid, status: "PENDING" }
GET  /jobs/{guid}/status            → 200 { guid, status, attempt, node_id }
GET  /jobs/{guid}/result            → 200 { guid, status, exit_code, output, duration_seconds }
                                      (returns 202 if still PENDING/RUNNING)
```

Auth: service principal client_credentials flow (already implemented).
Documentation should include a cURL polling loop example and a GitHub Actions step template.

---

## Sources

- [Rundeck Activity Page Docs](https://docs.rundeck.com/docs/manual/08-activity.html) — execution history features, 13 statuses, bulk delete, saved filters
- [Airflow 3.1.0 Blog: Human-Centered Workflows](https://airflow.apache.org/blog/airflow-3.1.0/) — DAG grid, Gantt, calendar view, real-time updates
- [Workflow Orchestration Platforms Comparison 2025](https://procycons.com/en/blogs/workflow-orchestration-platforms-comparison-2025/) — Kestra, Temporal, Prefect, Airflow feature comparison
- [BullMQ Retrying Failing Jobs](https://docs.bullmq.io/guide/retrying-failing-jobs) — exponential backoff formula, jitter, DLQ patterns
- [Queue-Based Exponential Backoff — DEV Community](https://dev.to/andreparis/queue-based-exponential-backoff-a-resilient-retry-pattern-for-distributed-systems-37f3) — thundering herd prevention
- [Dead Letter Queues: Complete Guide — swenotes](https://swenotes.com/2025/09/25/dead-letter-queues-dlq-the-complete-developer-friendly-guide/) — DLQ patterns, retry conditions
- [System Design: Distributed Job Scheduler — algomaster.io](https://blog.algomaster.io/p/design-a-distributed-job-scheduler) — job_executions schema, status states
- [SSE vs WebSockets vs Long Polling 2025 — DEV Community](https://dev.to/haraf/server-sent-events-sse-vs-websockets-vs-long-polling-whats-best-in-2025-5ep8) — streaming architecture trade-offs
- [Harness Deployment Logs and Limitations](https://developer.harness.io/docs/continuous-delivery/manage-deployments/deployment-logs-and-limitations/) — 5000 line cap, truncation behavior
- [GitLab CI job log size limit fix](https://datawookie.dev/blog/2021/07/fixing-truncated-logs-on-gitlab-ci-cd/) — 4 MB default, configurable runner output_limit
- [Airflow Summit 2026: Visual DAG Editor Demo](https://airflowsummit.org/sessions/demo-visual-dag-editor/) — visual DAG editor still not shipped
- [Dagster: Scaling DAG Visualization to 10K+ Assets](https://dagster.io/blog/scaling-dag-visualization) — ReactFlow graph rendering complexity at scale
- [GitHub Repository Dispatch for External Triggers](https://oneuptime.com/blog/post/2025-12-20-repository-dispatch-github-actions/view) — CI/CD integration patterns
- [State of Open Source Workflow Orchestration 2025](https://www.pracdata.io/p/state-of-workflow-orchestration-ecosystem-2025) — ecosystem landscape

---

*Feature research for: distributed job scheduler / task orchestration*
*Researched: 2026-03-04*
