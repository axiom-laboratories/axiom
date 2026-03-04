# Project Research Summary

**Project:** Master of Puppets — Job Output Capture, Retry, DAG Dependencies, CI/CD Integration
**Domain:** Distributed pull-model job scheduler / task orchestration (FastAPI/SQLAlchemy)
**Researched:** 2026-03-04
**Confidence:** HIGH

## Executive Summary

Master of Puppets already has a functioning, security-hardened orchestration platform. This milestone adds the production-readiness capabilities that prevent the system from feeling like a prototype: job output capture, retry policies, execution history, job dependency chaining, environment tag enforcement, and machine-friendly CI/CD integration. All four research streams agree on the same foundational sequence — output capture must come first because every other feature (retry audit trails, history timelines, dead letter queues, CI/CD result polling) is meaningless without knowing what a job printed and how it exited.

The recommended technical approach makes no architectural breaks with the existing codebase. Two new libraries (tenacity 9.1.4, networkx 3.4.2) and two new DB tables (execution\_records, job\_dependencies) carry the entire feature set. The retry model belongs on the orchestrator server — nodes are stateless and must never hold retry state. DAG dependency evaluation belongs inside the existing `pull_work` path rather than a background polling loop, which preserves transactional consistency and eliminates race conditions. The existing Service Principal auth, tag-matching logic, and APScheduler infrastructure are already sufficient; the gap is documentation and a clean CI-facing endpoint contract.

The two highest-priority risks are security, not engineering. First: CI/CD service principals granted `operator` role can register signing keys, which is a full bypass of the zero-trust model (OWASP CICD-SEC-5). A dedicated `ci` role with only `jobs:read` + `jobs:write` must be created before the CI/CD integration is documented. Second: the verification key bootstrap has a TOCTOU gap — nodes fetch the Ed25519 public key from the orchestrator without pinning, so a compromised orchestrator at enrollment time can install a rogue trust anchor. Both issues must be addressed in the phase where they become relevant, not deferred.

---

## Key Findings

### Recommended Stack

The existing stack is locked and correct. The additions are minimal: `tenacity 9.1.4` for exponential backoff formulas (used for orchestrator-internal resilience, not node-side retry — nodes are stateless) and `networkx 3.4.2` for DAG cycle detection at job creation time. Both are pure Python with no new infrastructure requirements. APScheduler stays on 3.x — version 4.x is still alpha (4.0.0a6) with a breaking API and no production readiness signals.

The schema additions follow the existing `create_all` + `migration_vNN.sql` pattern established by Sprints 8–13. SQLite dev environments will need fresh `jobs.db` teardowns or careful migration scripting since SQLite does not support `ALTER TABLE ... IF NOT EXISTS`.

**Core technologies (new additions only):**
- `tenacity 9.1.4`: retry backoff formulas on orchestrator-internal calls — pip install, no infra dependency
- `networkx 3.4.2`: DAG cycle detection at job creation time — pure Python, lightweight
- `execution_records` table: per-attempt stdout/stderr/exit_code storage — SQLAlchemy ORM, zero new dependency
- `job_dependencies` table: adjacency list for DAG edges — SQL, works identically on SQLite and Postgres
- `httpx` (already transitive): webhook callback POSTs in background tasks — no new install needed

**What not to use:**
- APScheduler 4.x — alpha, breaking API change from 3.x
- Celery — requires Redis/RabbitMQ broker, breaks pull model
- Prefect/Airflow/Dagster — full platform replacements, not embeddable extensions
- `retrying` / `backoff` libraries — unmaintained or less capable than tenacity

### Expected Features

The feature research compares this system against Airflow, Rundeck, Prefect, and BullMQ. The pattern is consistent: every production scheduler stores execution output, surfaces history, and retries with backoff. Missing these three makes the system feel unfinished regardless of its security advantages.

**Must have (table stakes) — this milestone's core deliverable:**
- Job output capture (stdout + stderr, buffered at completion) — debugging is impossible without it
- Exit code capture — enables non-blind retry decisions and debugging
- Execution history timeline — every scheduler ships this; absence signals prototype status
- Filter/search on execution history — history without search is unusable in production
- Retry policy (configurable count + exponential backoff + jitter) — table stakes for any infra tool
- Dead letter queue (DEAD\_LETTER status for exhausted retries) — completes the retry story cleanly
- Environment node tags (convention + UI badges) — operators running multiple environments expect this

**Should have (competitive differentiators):**
- Retry audit trail — per-attempt execution records with individual outputs (not just the last attempt)
- Output retention policy — automated pruning prevents runaway disk growth for high-frequency jobs
- CI/CD webhook endpoint + stable API contract documentation
- Linear job dependency chaining ("depends on" field with scheduler enforcement)

**Defer to v2+:**
- Real-time output streaming — HIGH complexity, conflicts with pull architecture's statelessness
- Full visual DAG editor — an anti-feature; Airflow's own editor was not shipped at Airflow Summit 2026
- Fan-out/fan-in patterns — only needed if linear chaining proves insufficient in practice
- Environment promotion workflow documentation — requires the full milestone to be complete first

### Architecture Approach

The architecture adds two new services (`RetryService`, `DAGService`) alongside the existing `job_service.py`, and two new tables (`execution_records`, `job_dependencies`). Output capture flows from the node's subprocess capture through the extended `ResultReport` model into a dedicated `execution_records` row written inside the same transaction as the `jobs` status update. Retry state lives entirely on the orchestrator — nodes are stateless and report every outcome immediately. Dependency evaluation happens inside `pull_work`, not a background poller, which eliminates TOCTOU races and adds no latency.

**Major components:**
1. `ExecutionRecord` (new DB table) — one row per execution attempt; holds stdout, stderr, exit\_code, attempt\_number; parent `jobs` row holds aggregate status
2. `RetryService` / `retry logic in job_service` (new) — server-side state machine; computes backoff, resets job to PENDING, manages `next_retry_at` column; reaper task handles zombie ASSIGNED jobs
3. `JobDependency` (new DB table) — adjacency list; evaluated transactionally inside `pull_work`; cycle detection via DFS at creation/edit time
4. `GET /jobs/{guid}/status` + `GET /jobs/{guid}/output` (new endpoints) — the CI/CD polling surface; returns `Retry-After` header on PENDING/ASSIGNED state
5. `ci` role (new RBAC role) — `jobs:read` + `jobs:write` only; no `signatures:write` or `foundry:write`

**Build order is strictly constrained by data dependencies:**
Output capture → execution records table → retry state machine → DAG dependencies → CI/CD endpoints → environment tags (independent, can ship any phase)

### Critical Pitfalls

1. **Zombie ASSIGNED jobs (Critical, Availability)** — A node crashes mid-execution; job stays ASSIGNED forever; retry never triggers because the job never transitions to FAILED. Prevention: implement a reaper APScheduler task that queries `status=ASSIGNED AND started_at < NOW() - timeout` and reclaims jobs back to PENDING. Must ship with retry in the same phase — retry is useless without the reaper.

2. **CI/CD principal with `operator` role bypasses zero-trust (Critical, Security)** — An `operator` role includes `signatures:write`. A compromised CI pipeline can register its own Ed25519 key and sign arbitrary scripts for execution on all nodes. Prevention: create a dedicated `ci` role with only `jobs:read` + `jobs:write`. Make key registration admin-only. This must be done before the CI/CD integration is documented.

3. **Output bloat kills the database (Critical, Infrastructure)** — Storing full stdout/stderr in `Job.result` JSON causes `list_jobs` to fetch multi-KB blobs for every row. A runaway job printing 50 MB fills SQLite WAL files. Prevention: hard cap output at the node side (1 MB default, configurable); store in a separate `execution_records` table (not `jobs.result`); never include full output in list endpoints.

4. **Verification key TOCTOU on bootstrap (Critical, Security)** — Nodes fetch the Ed25519 public key from the orchestrator over HTTPS without pinning. A compromised orchestrator at enrollment time serves a rogue key, installing a permanent backdoor into the node's trust chain. Prevention: include the verification key PEM or its fingerprint in the `JOIN_TOKEN` payload; node rejects if fetched key does not match.

5. **Retry on non-retriable failures (High, Correctness + Security)** — A job with an invalid signature retried 3 times wastes resources, clutters the audit log, and masks a potential security event. Prevention: classify failures as retriable (node crash, resource timeout) vs. non-retriable (signature verification failure, permission denied, explicit exit codes). Security rejections must never be silently retried.

---

## Implications for Roadmap

Based on the combined research, the build order is tightly constrained by data dependencies. The architecture research documents the exact sequence; the features research confirms the logical groupings; the pitfalls research identifies which phases carry the highest risk and need the most defensive design.

### Phase 1: Output Capture Foundation

**Rationale:** Every subsequent feature depends on knowing what a job printed and how it exited. This is the unblocking dependency for retry, history, CI/CD result polling, and the dead letter queue. It must come first.

**Delivers:**
- Extended `ResultReport` model with `stdout`, `stderr`, `exit_code` fields
- New `execution_records` SQLAlchemy table
- Node-side output capture (subprocess `PIPE`, size cap at 1 MB before POST)
- `GET /jobs/{guid}/output` endpoint (latest execution attempt)
- `GET /jobs/{guid}/executions` endpoint (all attempts, sorted by attempt\_number desc)
- Output preview in job detail pane in dashboard (no full blob rendering)

**Addresses:** Job output capture, exit code capture, execution duration exposure (table stakes P1 from FEATURES.md)

**Avoids:**
- Output bloat pitfall — schema designed correctly before any output lands
- Avoid including full `result` blob in `list_jobs` from day one
- Apply 1 MB truncation at node, `truncated: bool` flag in result

**Research flag:** Standard pattern, well-documented. Skip research-phase. Follow ARCHITECTURE.md schema exactly.

---

### Phase 2: Retry Policy and Zombie Reaper

**Rationale:** Retry without output capture is meaningless (you can't see why it failed). Retry without the zombie reaper is dangerous (ASSIGNED jobs from crashed nodes never enter the retry loop). These two must ship together in one phase.

**Delivers:**
- New columns on `jobs`: `max_retries`, `retry_count`, `retry_delay_seconds`, `retry_backoff`, `next_retry_at`
- New columns on `scheduled_jobs`: `max_retries`, `retry_delay_seconds`, `retry_backoff`
- Retry state machine in `job_service.report_result()` — re-queues to PENDING with backoff, or transitions to FAILED (terminal)
- Zombie reaper APScheduler task — reclaims ASSIGNED jobs older than `max_runtime_seconds` (default 10 min)
- `next_retry_at` filter added to `pull_work` query
- Dead letter view in dashboard: filter for `FAILED` jobs with `retry_count > 0` and `retry_count >= max_retries`
- Failure classification: non-retriable codes (signature failure → never retry; resource limit → retriable)
- Jitter on all non-immediate retry strategies (±20% of computed delay, prevents thundering herd)
- `migration_v14.sql` for existing Postgres deployments

**Addresses:** Retry policy, dead letter queue, configurable retry count, exponential backoff + jitter (P1 from FEATURES.md)

**Avoids:**
- Retry on non-retriable failures — implement failure classification in this phase
- Zombie jobs — reaper is mandatory in this phase, not deferred
- Thundering herd — jitter is mandatory, not optional

**Research flag:** Retry state machine is a well-documented pattern. Zombie reaper is straightforward APScheduler task. Skip research-phase.

---

### Phase 3: Execution History and Retry Audit Trail

**Rationale:** Once execution records exist (Phase 1) and retry produces multiple attempts (Phase 2), the dashboard needs to surface this data. The history timeline and per-attempt audit trail become meaningful together.

**Delivers:**
- `GET /jobs/history` endpoint with filter parameters: `node_id`, `since`, `until`, `status`, `job_definition_id`
- Execution History view in dashboard (filterable list of past runs with node, duration, status, exit code)
- Per-attempt drill-down panel: "attempt 1 → FAILED (exit 1, 2026-03-04 09:01)", "attempt 2 → COMPLETED"
- Output retention pruning (background APScheduler task): max 50 execution records per job definition, 1 MB max per output; configurable via Config table
- Output size display with truncation indicator ("output truncated at 1 MB — full output unavailable")

**Addresses:** Execution history timeline, filter/search history, retry audit trail, output retention policy (P1 and P2 from FEATURES.md)

**Avoids:**
- Full stdout rendering in list views — show preview only, paginate on demand
- Unbounded output retention — pruning ships in this phase, not deferred until disk fills

**Research flag:** History endpoint is a standard REST pattern. Pruning task is straightforward APScheduler work. Skip research-phase.

---

### Phase 4: Environment Tags and CI/CD Integration

**Rationale:** These two are paired because environment tags define the routing model that CI/CD pipelines use to target environments. The `ci` role must be defined before the integration is documented (to avoid the over-privilege pitfall). Environment tag enforcement at the node level (not just advisory) is a prerequisite for a trustworthy promotion model.

**Delivers:**
- Reserved tag convention documented: `env:dev`, `env:test`, `env:prod`
- `PATCH /nodes/{node_id}/config` endpoint — accepts `tags: List[str]`, `require_tag_match: bool`
- `require_tag_match` enforcement in node's secondary admission check (`node.py`) — PROD nodes reject untagged jobs
- Environment badges in Nodes dashboard view (color-coded: green=prod, amber=test, blue=dev)
- Tag selector dropdown on job dispatch form (populated from active nodes' current tags)
- New `ci` RBAC role seeded: `jobs:read` + `jobs:write` only
- `GET /jobs/{guid}/status` endpoint with `Retry-After` header (5s) for PENDING/ASSIGNED state
- CI/CD integration documentation: cURL polling loop example, GitHub Actions step template
- Service principal rotation guidance: `expires_at` requirement, rotation procedure
- `migration_v15.sql` for existing deployments

**Addresses:** Environment node tags, machine-friendly job dispatch API, CI/CD webhook endpoint + docs (P1 and P2 from FEATURES.md)

**Avoids:**
- CI principal over-privilege — `ci` role created and documented before integration is written up
- Environment tags advisory-only — `require_tag_match` enforced at node level
- Long-lived CI API keys — `expires_at` documented as required

**Research flag:** Needs careful review of the existing RBAC seeding code before implementing the `ci` role. The `require_tag_match` enforcement in `node.py` is new logic that needs a targeted test case. No research-phase needed for the endpoint patterns — standard REST contract.

---

### Phase 5: Job Dependency Chaining

**Rationale:** Dependencies require a reliable execution history (Phase 3) to evaluate whether upstream jobs genuinely completed vs. will be retried. The DAG evaluation must happen inside `pull_work` for correctness, and cycle detection must run on every mutation (not just creation) to prevent scheduler deadlock.

**Delivers:**
- New `job_dependencies` SQLAlchemy table (adjacency list with UniqueConstraint)
- `depends_on: List[str]` field on `JobCreate` — validated on creation, cycle-checked
- Cycle detection (DFS) runs on every dependency add or edit, returns HTTP 400 on cycle
- Dependency readiness check inside `pull_work` — single atomic query, same transaction as assignment
- No background DAG poller — check happens at pull time (eliminates fan-in race condition)
- "depends on" selector in job dispatch form (dashboard)
- Simple dependency chain visualization in job detail pane (ASCII or react-flow fallback)
- Audit log entries for all dependency mutations
- Fan-in correctness: atomic DB check rather than application-level read-then-write

**Addresses:** Linear job dependency chaining (P2 from FEATURES.md)

**Avoids:**
- DAG cycle via edit — cycle detection on every mutation, not just creation
- Fan-in race condition — atomic DB check, not concurrent application reads
- Background poller — dependency evaluation inside `pull_work` only
- Building a visual DAG editor — anti-feature, explicitly excluded

**Research flag:** The fan-in correctness under concurrent load deserves a specific load test before this phase is considered done. The adjacency list pattern is well-documented. Cycle detection (DFS) is straightforward. No research-phase needed.

---

### Phase Ordering Rationale

- Output capture first because every other feature references execution output or exit codes. Building retry without it means retry decisions are blind.
- Retry and reaper together because a zombie reaper without retry is incomplete, and retry without a reaper leaves crashed-node jobs permanently ASSIGNED (unreachable by the retry system).
- History third because it requires execution records (Phase 1) to be populated and multiple retry attempts (Phase 2) to be meaningful. Pruning ships here to prevent runaway growth.
- CI/CD and environment tags together because they share the `ci` role prerequisite and the tag convention is the mechanism CI pipelines use to target environments. Documenting CI before defining the `ci` role guarantees the over-privilege pitfall.
- Dependencies last because they require reliable history (to check upstream completion) and retry semantics (to distinguish "completed" from "will be retried") to work correctly.

### Research Flags

Phases with standard, well-documented patterns — skip research-phase during planning:
- **Phase 1 (Output Capture):** schema and data flow are clear from ARCHITECTURE.md; no novel decisions
- **Phase 2 (Retry + Reaper):** state machine pattern is well-established; APScheduler task is routine
- **Phase 3 (History + Pruning):** REST filter pattern and background pruning are standard work

Phases that need targeted review before implementation begins:
- **Phase 4 (CI/CD + Tags):** The `require_tag_match` enforcement in `node.py` is new admission logic on the node side. Test cases for "PROD node rejects untagged job" and "CI principal cannot call `POST /admin/signatures`" should be written before implementation starts, not after. The `ci` role seeding must be validated against the existing RBAC seeder to ensure ON CONFLICT handling is correct.
- **Phase 5 (Dependencies):** Fan-in correctness under concurrent load is not exercised by unit tests — needs a specific concurrency test. The interaction between retry state and dependency evaluation ("upstream job is PENDING retry — is that COMPLETED?") needs explicit design before coding.

---

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | All library choices verified via PyPI and official docs; no novel dependencies; all version compatibility confirmed |
| Features | HIGH | Cross-referenced against Airflow, Rundeck, Prefect, BullMQ, Temporal; feature dependencies mapped; anti-features explicitly called out |
| Architecture | HIGH | Based on direct codebase analysis of `db.py`, `job_service.py`, `models.py`; patterns from system design literature are secondary confirmation |
| Pitfalls | HIGH | Critical pitfalls sourced from OWASP CI/CD top 10, Airflow/Dask GitHub issues, and direct codebase inspection; all are real, documented failure modes |

**Overall confidence: HIGH**

### Gaps to Address

- **Scheduled-job cross-run dependencies:** ARCHITECTURE.md defers "most recent successful run" semantics for scheduled job dependencies to V2. If the product requires that a cron job B only fires if the most recent run of cron job A succeeded, this needs explicit design before Phase 5 is scoped. Treat as a gap to validate with the product owner at roadmap time.

- **APScheduler misfire behavior under load:** `misfire_grace_time` defaults to 1 second. For high-frequency jobs or a system under load, jobs scheduled for a time in the recent past are silently skipped. The fix (set `misfire_grace_time` to 5 minutes) is a one-line change but must be validated in the existing `scheduler_service.py`. Check this during Phase 2 scope.

- **SQLite ALTER TABLE compat for new retry columns:** SQLite does not support `ALTER TABLE jobs ADD COLUMN IF NOT EXISTS`. For dev environments, the established pattern (delete `jobs.db` + `create_all`) handles new tables but not new columns on existing tables. Confirm the dev teardown procedure is documented in CLAUDE.md before Phase 2 ships.

- **Verification key TOCTOU resolution approach:** PITFALLS.md identifies two options (pin hash in JOIN\_TOKEN or include PEM directly). The JOIN\_TOKEN format change is a breaking change for nodes already enrolled. Decide on the approach and document it before Phase 4 (when bootstrap security is revisited for CI/CD docs). This may require a forced re-enrollment cycle for existing nodes.

---

## Sources

### Primary (HIGH confidence)
- Direct codebase analysis: `puppeteer/agent_service/db.py`, `job_service.py`, `models.py`, `puppets/environment_service/node.py`
- APScheduler 3.x User Guide (https://apscheduler.readthedocs.io/en/3.x/userguide.html)
- tenacity PyPI + GitHub (https://pypi.org/project/tenacity/, https://github.com/jd/tenacity) — 9.1.4 stable
- NetworkX DAG docs (https://networkx.org/nx-guides/content/algorithms/dag/index.html)
- OWASP CI/CD Security Top 10 — CICD-SEC-5 (https://owasp.org/www-project-top-10-ci-cd-security-risks/CICD-SEC-05-Insufficient-PBAC)
- PostgreSQL TOAST docs (https://www.enterprisedb.com/postgres-tutorials/postgresql-toast-and-working-blobsclobs-explained)
- Kubernetes Labels and Selectors (https://kubernetes.io/docs/concepts/overview/working-with-objects/labels/)

### Secondary (MEDIUM confidence)
- System design literature: AlgoMaster distributed job scheduler (https://blog.algomaster.io/p/design-a-distributed-job-scheduler)
- BullMQ retrying failing jobs (https://docs.bullmq.io/guide/retrying-failing-jobs)
- AWS Prescriptive Guidance: Retry with Backoff (https://docs.aws.amazon.com/prescriptive-guidance/latest/cloud-design-patterns/retry-backoff.html)
- Apache Airflow issue #25765 — DAG deadlock from circular dependency (https://github.com/apache/airflow/issues/25765)
- Dask distributed issue #8576 — fan-in race condition (https://github.com/dask/distributed/issues/8576)
- Rundeck activity docs (https://docs.rundeck.com/docs/manual/08-activity.html)
- Airflow 3.1.0 blog (https://airflow.apache.org/blog/airflow-3.1.0/)

### Tertiary (LOW confidence)
- Competitor feature comparisons (procycons.com, pracdata.io) — general landscape only, not relied upon for implementation decisions
- WebSearch: APScheduler vs Celery — confirms broker requirement for Celery; broad community consensus

---

*Research completed: 2026-03-04*
*Ready for roadmap: yes*
