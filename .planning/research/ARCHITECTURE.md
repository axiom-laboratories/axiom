# Architecture Research

**Domain:** Distributed pull-model job scheduler / task orchestration (FastAPI/SQLAlchemy)
**Researched:** 2026-03-04
**Confidence:** HIGH — based on direct codebase analysis + verified patterns from system design literature

---

## Standard Architecture

### System Overview (Current State)

```
CI/CD Pipeline / Dashboard User / Service Principal
          |
          | HTTPS + JWT / mTLS API Key
          v
┌─────────────────────────────────────────────────────────────┐
│                  Puppeteer (Control Plane)                   │
│                                                             │
│  ┌─────────────┐  ┌──────────────┐  ┌───────────────────┐  │
│  │   FastAPI   │  │  APScheduler │  │  WebSocket /ws    │  │
│  │  main.py   │  │  (cron jobs) │  │  (live dashboard) │  │
│  └──────┬──────┘  └──────┬───────┘  └───────────────────┘  │
│         │                │                                   │
│  ┌──────v────────────────v──────────────────────────────┐   │
│  │                  job_service.py                       │   │
│  │  create_job | pull_work | report_result | heartbeat  │   │
│  └──────────────────────┬───────────────────────────────┘   │
│                         │                                    │
│  ┌──────────────────────v───────────────────────────────┐   │
│  │               PostgreSQL / SQLite                     │   │
│  │  jobs | nodes | scheduled_jobs | audit_log | ...      │   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
          ^
          | mTLS (client cert signed by Root CA)
          | Poll /work/pull every N seconds
          |
┌─────────┴────────────────────────────────────────────────────┐
│  Puppet Node (stateless)                                     │
│  node.py → poll → runtime.py → container execution           │
│  → POST /work/{guid}/result (stdout, stderr, exit_code)      │
└─────────────────────────────────────────────────────────────┘
```

### System Overview (Target State — With New Capabilities)

```
CI/CD Pipeline
    |
    | POST /jobs  (Service Principal + mTLS API Key)
    | GET /jobs/{guid}/status  (polling for result)
    v
┌─────────────────────────────────────────────────────────────┐
│                  Puppeteer (Control Plane)                   │
│                                                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐  │
│  │   JobService │  │  RetryService │  │  DAGService       │  │
│  │  (existing)  │  │  (new)       │  │  (new)           │  │
│  └──────┬───────┘  └──────┬───────┘  └──────┬────────── ┘  │
│         │                 │                  │               │
│  ┌──────v─────────────────v──────────────────v───────────┐  │
│  │                  PostgreSQL / SQLite                   │  │
│  │                                                        │  │
│  │  jobs (existing)         execution_records (NEW)       │  │
│  │  job_dependencies (NEW)  node tags (existing, extend)  │  │
│  └────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
          ^
          | mTLS
          | POST /work/{guid}/result { stdout, stderr, exit_code }
          |
┌─────────┴─────────────────────────┐
│  Puppet Node (stateless)          │
│  Captures container stdout/stderr │
│  Reports full output on completion│
└───────────────────────────────────┘
```

### Component Responsibilities

| Component | Responsibility | Current State |
|-----------|----------------|---------------|
| `job_service.py` | Job assignment, pull_work, report_result, heartbeat | Exists — needs output capture extension |
| `RetryService` (new) | Retry state machine, backoff timers, failure escalation | Does not exist |
| `DAGService` (new) | Dependency graph evaluation, successor unblocking | Does not exist |
| `job_dependencies` table (new) | Edges: upstream_job_id → downstream_job_id | Does not exist |
| `execution_records` table (new) | Per-attempt history: stdout, stderr, exit_code, attempt# | Does not exist |
| `Node.tags` (existing) | JSON list — already holds tags | Exists, already used for targeting |
| `ResultReport` model (existing) | Carries job result back from node | Exists — needs stdout/stderr fields |

---

## Recommended Architecture

### 1. Job Output Capture

**Decision: Store stdout/stderr as TEXT columns in a new `execution_records` table. Do NOT use external blob storage.**

Rationale:
- PostgreSQL's TOAST storage automatically compresses and off-pages TEXT > 2KB, making large output storage efficient without additional infrastructure. Tested up to 1GB per column.
- SQLite supports TEXT of arbitrary size (also TOAST-equivalent). Both backends handle it identically from application code.
- This system targets homelab and internal enterprise — not petabyte-scale log aggregation. Job output is ephemeral and queryable; object storage (S3/GCS) adds operational complexity with no meaningful benefit at this scale.
- Output must be queryable by CI/CD polling (`GET /jobs/{guid}/output`). SQL text is directly filterable; blob references require a second lookup.
- The existing `Job.result` column already stores JSON text. Extending that pattern is idiomatic for this codebase.

**Output size limit:** Enforce a soft cap at the application layer — truncate at 1MB and append a marker. Do not rely on DB constraints (inconsistent across SQLite/Postgres).

**New table: `execution_records`**

```python
class ExecutionRecord(Base):
    __tablename__ = "execution_records"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    job_guid: Mapped[str] = mapped_column(String, nullable=False)   # FK to jobs.guid
    attempt_number: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    node_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    exit_code: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    stdout: Mapped[Optional[str]] = mapped_column(Text, nullable=True)   # TOAST-compressed
    stderr: Mapped[Optional[str]] = mapped_column(Text, nullable=True)   # TOAST-compressed
    status: Mapped[str] = mapped_column(String, nullable=False)   # COMPLETED, FAILED, RETRYING
    # Index: (job_guid, attempt_number) for history queries
```

**Migration:** New table, handled by `create_all` on fresh deployments. Existing deployments need `CREATE TABLE IF NOT EXISTS execution_records (...)`.

**Node-side change:** `ResultReport` model gains `stdout: Optional[str]` and `stderr: Optional[str]`. Node's `runtime.py` captures container output (already feasible — subprocess `stdout=PIPE, stderr=PIPE` or docker logs).

**Data flow:**
```
Node runs container → captures stdout/stderr → POST /work/{guid}/result
                                                   { success, stdout, stderr, exit_code }
                                                             |
                                               job_service.report_result()
                                                             |
                                               INSERT INTO execution_records
                                               UPDATE jobs.status
```

---

### 2. Execution History

**Decision: Separate `execution_records` table (above) — do NOT overload the `jobs` table.**

The current `jobs` table conflates the job specification (what to run, target, constraints) with execution state (who ran it, when, result). This creates problems when adding retry — a retried job produces multiple execution attempts. The clean separation is:

- `jobs` = the work item specification + lifecycle status (PENDING / ASSIGNED / COMPLETED / FAILED)
- `execution_records` = one row per execution attempt, with full output

**API additions:**
- `GET /jobs/{guid}/executions` — list all attempts for a job (sorted by attempt_number desc)
- `GET /jobs/{guid}/output` — shorthand for latest attempt stdout+stderr (dashboard "view logs" button)
- `GET /jobs/history?node_id=X&since=Y` — operational timeline query

**Dashboard implication:** Current `Jobs.tsx` fetches from `/jobs`. A new "Execution Detail" panel opens inline (not a new route) to show stdout/stderr for the selected job.

---

### 3. Retry State Machine

**Decision: Server-side state machine in `job_service.py` (or a thin `retry_service.py`). Do NOT put retry logic on nodes.**

Nodes are stateless. Retry state lives exclusively in the orchestrator. When `report_result` receives a failure, the server decides whether to retry — the node never knows.

**State transitions:**

```
PENDING
  |
  | (node pulls)
  v
ASSIGNED
  |
  | (node reports success)                   (node reports failure)
  v                                                    |
COMPLETED                          retry_count < max_retries?
                                           |              |
                                          YES             NO
                                           |              |
                              retry_delay computed    FAILED (terminal)
                              job reset to PENDING
                              after backoff_seconds
```

**Retry fields on `jobs` table (new columns):**

```sql
ALTER TABLE jobs ADD COLUMN max_retries INTEGER DEFAULT 0;
ALTER TABLE jobs ADD COLUMN retry_count INTEGER DEFAULT 0;
ALTER TABLE jobs ADD COLUMN retry_delay_seconds INTEGER DEFAULT 60;
ALTER TABLE jobs ADD COLUMN retry_backoff TEXT DEFAULT 'exponential';  -- 'fixed' | 'exponential' | 'linear'
ALTER TABLE jobs ADD COLUMN next_retry_at TIMESTAMP NULL;
```

**Backoff computation in `report_result`:**

```python
def compute_next_retry(attempt: int, delay_base: int, strategy: str) -> int:
    if strategy == 'exponential':
        return delay_base * (2 ** (attempt - 1))   # 60s, 120s, 240s...
    elif strategy == 'linear':
        return delay_base * attempt                  # 60s, 120s, 180s...
    else:  # fixed
        return delay_base                            # always 60s
```

**Pull_work change:** The `pull_work` query gains a condition:
```sql
WHERE status = 'PENDING'
  AND (next_retry_at IS NULL OR next_retry_at <= NOW())
```

This prevents a backed-off job from being picked up before its delay expires. No scheduler loop needed — the check happens naturally at each poll.

**`ScheduledJobDefinition` retry policy:** Add `max_retries`, `retry_delay_seconds`, `retry_backoff` to `ScheduledJob` so policies flow through to spawned `Job` rows.

**Dead letter:** When `retry_count >= max_retries`, status = `FAILED` (permanent). The audit log records the terminal failure with attempt count. Dashboard can filter for `FAILED` jobs with `retry_count > 0` as a "exhausted retries" view.

---

### 4. DAG / Job Dependencies

**Decision: Adjacency list table `job_dependencies`. Evaluate readiness at dispatch time, not with a background poller.**

**Why adjacency list over recursive JSON:** SQL adjacency list is queryable, indexable, and works on both SQLite and Postgres. The DAG topology for this system will be shallow (2-5 levels) — no need for recursive CTEs or a graph database.

**New table: `job_dependencies`**

```python
class JobDependency(Base):
    __tablename__ = "job_dependencies"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    job_guid: Mapped[str] = mapped_column(String, nullable=False)        # downstream (waits for)
    depends_on_guid: Mapped[str] = mapped_column(String, nullable=False) # upstream (must complete first)
    # Unique constraint prevents duplicate edges
    __table_args__ = (UniqueConstraint("job_guid", "depends_on_guid"),)
```

**Dependency evaluation logic:**

```python
async def check_dependencies_met(job_guid: str, db: AsyncSession) -> bool:
    """Returns True if all upstream jobs for this job are COMPLETED."""
    deps = await db.execute(
        select(JobDependency.depends_on_guid)
        .where(JobDependency.job_guid == job_guid)
    )
    upstream_guids = [row[0] for row in deps.all()]
    if not upstream_guids:
        return True
    statuses = await db.execute(
        select(Job.status).where(Job.guid.in_(upstream_guids))
    )
    return all(s == 'COMPLETED' for (s,) in statuses.all())
```

**Pull_work integration:** Add dependency check before assigning. A job with unmet dependencies stays PENDING but never gets picked up:

```python
if not await check_dependencies_met(candidate.guid, db):
    continue
```

**Job creation API extension:** `POST /jobs` accepts an optional `depends_on: List[str]` field. The API validates that all listed GUIDs exist and are not already FAILED before inserting the dependency rows.

**Cycle detection:** On job creation with dependencies, run a simple DFS to reject cycles before inserting edges. Since this is a creation-time check (not a hot path), correctness > performance.

**Scheduled job dependencies:** Explicitly out of scope for the first iteration. Scheduled jobs spawn independent `Job` rows — cross-run dependencies are a V2 feature.

---

### 5. Environment Node Tags

**Decision: Keep tags as a JSON list on `Node.tags` (existing). Do NOT create a separate tags table. Add `environment` as a first-class field on `Node` for UI ergonomics.**

The existing system already supports `target_tags` on jobs and `tags` on nodes. The current implementation is correct — arbitrary string tags with subset matching in `pull_work`. This is the Kubernetes label/selector model (nodeSelector) and it is the right approach.

**What needs to change:** The dashboard has no way to set `environment` on a node — it's just a string inside the opaque `tags` JSON. The fix is a convention, not a schema change:

1. Document the reserved tag values: `env:dev`, `env:test`, `env:prod` (namespaced to avoid collision with other tags like `gpu`, `linux`).
2. Add a node configuration endpoint `PATCH /nodes/{node_id}/config` that accepts `tags: List[str]` alongside concurrency/memory limits.
3. Surface the environment badge in the Nodes dashboard view (parse `env:*` tags to color-code nodes).

**CI/CD environment promotion pattern:**
```
Job dispatched with target_tags: ["env:dev"]
  → only nodes tagged "env:dev" pick it up
  → on success, CI dispatches follow-up job with target_tags: ["env:test"]
  → orchestrator's DAG dependency links them
```

This is the correct model — the orchestrator enforces environment routing, the pipeline triggers the chain. No special "environment promotion" feature needed beyond dependencies + tags.

**No schema migration required for tags** — the mechanism is already in place.

---

### 6. CI/CD Integration

**Decision: HTTP 202 + polling endpoint. Do NOT add webhooks as a V1 requirement.**

The system already has all ingredients for machine-friendly CI/CD integration. The gap is documentation and a clean status polling surface.

**Auth for CI/CD:** Use Service Principals (already implemented in Sprint 10). CI pipeline holds `client_id` + `client_secret`, exchanges for JWT at `/auth/service-principal/token`, then uses JWT for subsequent requests. The JWT-on-header flow works with existing auth middleware without any changes.

**Job dispatch flow:**
```
1. CI: POST /auth/service-principal/token  → { access_token }
2. CI: POST /jobs { task_type, payload, target_tags: ["env:prod"], depends_on: [...] }
        → HTTP 202 { guid: "abc123" }
3. CI: poll GET /jobs/abc123/status  (respecting Retry-After hint in response)
        → { status: "PENDING" | "ASSIGNED" | "COMPLETED" | "FAILED", ... }
4. CI: on COMPLETED → GET /jobs/abc123/output  → { stdout, stderr, exit_code }
```

**New API endpoints needed:**
- `GET /jobs/{guid}/status` — minimal status response (status, node_id, started_at, completed_at, duration)
- `GET /jobs/{guid}/output` — stdout, stderr, exit_code from latest execution_record

**Retry-After header:** When a job is PENDING or ASSIGNED, include `Retry-After: 5` (seconds) in the status response. CI runners that respect this avoid hammering the endpoint.

**Signing requirement for CI/CD jobs:** The existing security model requires all job scripts to be Ed25519-signed. CI pipelines must have access to a signing key. This is correct — do not add a bypass. The operator tooling (`admin_signer.py`) already handles signing. CI should sign scripts at build time and pass `signature`/`signature_id` in the job payload.

**Webhook callbacks (V2):** Implement outbound webhook delivery after CI/CD pull-polling is validated. When implemented: client provides `callback_url` at job creation, orchestrator POSTs `{ guid, status, exit_code }` on completion. Validate webhook URLs against an allowlist (prevent SSRF). Sign webhook payloads with an HMAC key the client verifies. Do not implement in V1 — the pull model is simpler and sufficient.

---

## Data Flow

### Job Execution with Output Capture

```
POST /jobs (CI/CD or Dashboard)
    |
    v
job_service.create_job()
    → INSERT INTO jobs (status=PENDING, max_retries=N, ...)
    → INSERT INTO job_dependencies (if depends_on provided)
    → return { guid }
    |
    v
Node polls /work/pull
    |
    v
job_service.pull_work()
    → check dependencies met
    → check concurrency limit
    → check tags + capabilities + memory
    → UPDATE jobs SET status=ASSIGNED, started_at=NOW()
    → return WorkResponse { guid, payload, memory_limit }
    |
    v
Node executes container
    → captures stdout, stderr, exit_code
    |
    v
POST /work/{guid}/result { success, stdout, stderr, exit_code }
    |
    v
job_service.report_result()
    → INSERT INTO execution_records (attempt_number, stdout, stderr, exit_code, status)
    → if success:
        UPDATE jobs SET status=COMPLETED
        → trigger: check if any job_dependencies.depends_on_guid=guid
          → those downstream jobs remain PENDING but become eligible for pull
    → if failure AND retry_count < max_retries:
        UPDATE jobs SET status=PENDING, retry_count+=1, next_retry_at=NOW()+backoff
    → if failure AND retry_count >= max_retries:
        UPDATE jobs SET status=FAILED
        → audit_log entry
```

### CI/CD Status Polling

```
CI: GET /jobs/{guid}/status
    |
    v
job_service.get_job_status(guid)
    → SELECT jobs WHERE guid=X
    → return { status, node_id, started_at, completed_at, duration_seconds }
    → include Retry-After: 5 header if status in (PENDING, ASSIGNED)
    |
    → if COMPLETED: CI fetches /jobs/{guid}/output
         → SELECT execution_records WHERE job_guid=X ORDER BY attempt_number DESC LIMIT 1
         → return { stdout, stderr, exit_code }
```

---

## DB Schema Changes Summary

| Change | Table | Type | Migration |
|--------|-------|------|-----------|
| Add `execution_records` table | New | CREATE TABLE | `CREATE TABLE IF NOT EXISTS` for existing DBs |
| Add `job_dependencies` table | New | CREATE TABLE | `CREATE TABLE IF NOT EXISTS` for existing DBs |
| Add `max_retries`, `retry_count`, `retry_delay_seconds`, `retry_backoff`, `next_retry_at` | `jobs` | ALTER | `ALTER TABLE jobs ADD COLUMN IF NOT EXISTS` (Postgres) / recreation for SQLite |
| Add `max_retries`, `retry_delay_seconds`, `retry_backoff` | `scheduled_jobs` | ALTER | Same as above |
| Add `stdout`, `stderr`, `exit_code` | `ResultReport` Pydantic model | Model change | No DB change — `jobs.result` stays, output goes to `execution_records` |
| Add `depends_on` | `JobCreate` Pydantic model | Model change | No DB change |

**SQLite ALTER TABLE caveat:** SQLite does not support `ADD COLUMN IF NOT EXISTS`. For dev environments, the safest approach is to delete `jobs.db` on first run of new code (tolerable for dev, never for prod). For production, a `migration_v14.sql` with Postgres-style `IF NOT EXISTS` guards is the pattern established by this codebase.

---

## Build Order / Phase Dependencies

The six features have interdependencies that constrain build order:

```
1. ResultReport stdout/stderr capture (node-side + API model)
        ↓
2. execution_records table + report_result stores output
        ↓
3. GET /jobs/{guid}/output + GET /jobs/{guid}/executions endpoints
        ↓
4. Retry state machine (uses execution_records.attempt_number)
        ↓
5. DAG dependencies (depends_on at job creation, dependency check in pull_work)
        ↓
6. CI/CD integration endpoints (wraps all of above with clean CI-facing surface)
        |
        (parallel with 1-6, no dependency)
7. Environment tag conventions + PATCH /nodes/{id}/config for tag management
```

**Rationale:**
- Output capture must come first — retry and execution history are meaningless without knowing what the job printed.
- Execution records table is the foundation for retry (attempt numbering) and history display.
- Retry must precede DAG — DAG successor triggering needs to know if a parent genuinely completed vs. will be retried.
- CI/CD integration is the top-level consumer — it assembles job dispatch + dependency + status polling into a coherent external API. Build it last so the surfaces it wraps are stable.
- Environment tags are independent of the execution pipeline and can ship in any phase.

---

## Security Implications

### Output Capture Security

- **Stdout/stderr may contain secrets.** The existing `mask_secrets()` helper in `security.py` runs on job payloads. It must also run on stdout/stderr before storage in `execution_records`. Add a post-execution scrub step in `report_result`.
- **Access control for output:** `GET /jobs/{guid}/output` must be gated on `jobs:read` permission. Viewers can see job status but not raw output — consider a separate `jobs:output` permission for sensitive environments.
- **Output size DoS:** A malicious or runaway job could send gigabytes of stdout. Enforce a hard 1MB truncation on the node side before POSTing. Add a 413 check server-side.

### DAG Security

- **Dependency injection:** A CI/CD caller with `jobs:write` could chain a job to depend on a job they do not own, gaining execution ordering influence. For V1, accept this — all jobs run as the same execution context. Document it. If multi-tenancy becomes a requirement, add owner checks on `depends_on` GUIDs.
- **Cycle attacks:** A malicious actor with API access could attempt to create cycles. Cycle detection at creation time (DFS) is mandatory, not optional.

### CI/CD Integration Security

- **Service Principals are the correct auth mechanism** — they already exist, already enforce RBAC, already have expiry. Do not add a bypass.
- **Signing requirement stays.** The CI pipeline must sign scripts. This is the key property of the security model. The workflow is: operator generates signing keypair → uploads public key to Signatures → CI pipeline has private key in its secret store → signs scripts before dispatch.
- **Webhook callbacks (V2 concern):** If webhooks are added later, callback URLs must be validated against an operator-configured allowlist to prevent SSRF. Webhook payloads must be HMAC-signed so the receiver can verify authenticity.
- **mTLS for CI/CD:** The orchestrator's REST API is behind Caddy + Cloudflare. CI/CD callers use HTTPS + JWT (Service Principal flow). mTLS is reserved for node-to-orchestrator communication. Do not require mTLS from CI/CD callers — it creates an unacceptable operational burden for external pipeline systems.

---

## Anti-Patterns to Avoid

### Anti-Pattern 1: Putting Retry Logic on Nodes

**What people do:** Node detects failure, retries locally N times before reporting.
**Why it's wrong:** Nodes are stateless. The orchestrator loses visibility into attempts. Audit trail is broken. If the node crashes mid-retry, attempts are silently lost.
**Do this instead:** Node reports every failure immediately. Server decides whether to reschedule.

### Anti-Pattern 2: Storing stdout/stderr in `jobs.result` JSON

**What people do:** Append stdout as a key in the existing JSON result blob.
**Why it's wrong:** The `jobs` table is a hot table scanned for PENDING/ASSIGNED jobs. Adding multi-KB TEXT to it bloats scans. PostgreSQL TOAST helps but the data is inline until the column is excluded from SELECT.
**Do this instead:** Separate `execution_records` table. `jobs.result` stays as a small structured JSON summary; full output lives in `execution_records.stdout`.

### Anti-Pattern 3: Background Poller for DAG Resolution

**What people do:** A cron loop every N seconds scans all PENDING jobs with dependencies and unblocks them.
**Why it's wrong:** Adds latency between upstream completion and downstream pickup. Adds an always-running process. Creates a race condition if multiple orchestrator instances are running.
**Do this instead:** Check dependency readiness inside `pull_work` — each poll is a natural trigger point. Zero latency, no background loop, transactionally consistent.

### Anti-Pattern 4: Webhooks Before Pull Polling

**What people do:** Add outbound webhook delivery before validating the pull-polling pattern.
**Why it's wrong:** Webhooks require the CI system to expose an HTTPS endpoint to the orchestrator — this reverses the network trust direction and may not be possible in all deployment topologies. The existing pull model works for CI/CD too.
**Do this instead:** Implement `GET /jobs/{guid}/status` with `Retry-After` hints. Let the pipeline poll. Add webhooks in V2 if operators request them.

### Anti-Pattern 5: Schema Migrations Without SQLite/Postgres Parity

**What people do:** Use `ALTER TABLE ... IF NOT EXISTS` (Postgres syntax) in migration scripts without testing SQLite.
**Why it's wrong:** SQLite does not support `IF NOT EXISTS` in `ALTER TABLE`. Dev environments break silently.
**Do this instead:** Wrap SQLite-incompatible migrations in a backend check, or use the established pattern: delete `jobs.db` for dev fresh starts, write migration SQL with Postgres `IF NOT EXISTS` for prod, document SQLite dev teardown procedure in CLAUDE.md.

---

## Scaling Considerations

| Scale | Architecture Adjustment |
|-------|-------------------------|
| 1-50 nodes, hundreds of jobs/day | Current SQLite + monolith is fine. No changes needed. |
| 50-500 nodes, thousands of jobs/day | Postgres required (already supported). Index `jobs(status, created_at)` and `execution_records(job_guid)`. |
| 500+ nodes, tens of thousands of jobs/day | `pull_work` becomes a bottleneck (row lock contention on PENDING jobs). Add `SELECT ... FOR UPDATE SKIP LOCKED` query pattern in Postgres. SQLite must be dropped at this scale. |
| 1000+ nodes | Consider read replica for dashboard queries, write-primary for job assignment. WebSocket fan-out becomes the next bottleneck — consider Redis pub/sub for broadcast. |

**First bottleneck for this system:** The `pull_work` scan across PENDING jobs with N=50 candidates per poll. With hundreds of nodes polling every 3-5 seconds, this is O(nodes * candidates) queries per second against the jobs table. The fix is `SELECT ... FOR UPDATE SKIP LOCKED` (Postgres 9.5+) — safe to add as an optimization without breaking existing behavior.

---

## Integration Points

### Internal Boundaries

| Boundary | Communication | Notes |
|----------|---------------|-------|
| `job_service.py` ↔ `execution_records` | Direct SQLAlchemy ORM | Same session, same transaction as job status update |
| `pull_work` ↔ `job_dependencies` | SQL sub-query | Must be in same transaction to avoid TOCTOU race |
| `scheduler_service.py` → `job_service.create_job` | Direct function call | Retry policy copied from ScheduledJob to spawned Job |
| `report_result` → DAG successor check | Query + status update | Single transaction: mark complete + notify successors in one commit |

### External Integration

| Surface | Pattern | Auth |
|---------|---------|------|
| CI/CD job dispatch | `POST /jobs` → HTTP 202 + poll `GET /jobs/{guid}/status` | Service Principal JWT |
| Dashboard job output viewer | `GET /jobs/{guid}/output` | User JWT with `jobs:read` |
| Webhook delivery (V2) | Outbound POST to operator-configured URL | HMAC-signed payload |

---

## Sources

- Codebase analysis: `puppeteer/agent_service/db.py`, `job_service.py`, `models.py` (direct read, HIGH confidence)
- [Design a Distributed Job Scheduler - AlgoMaster](https://blog.algomaster.io/p/design-a-distributed-job-scheduler) — execution history schema patterns (MEDIUM confidence)
- [Asynchronous Operations in REST APIs - Zuplo](https://zuplo.com/learning-center/asynchronous-operations-in-rest-apis-managing-long-running-tasks) — HTTP 202 + polling + webhook patterns (MEDIUM confidence)
- [PostgreSQL TOAST and BLOBs - EDB](https://www.enterprisedb.com/postgres-tutorials/postgresql-toast-and-working-blobsclobs-explained) — TEXT column storage characteristics (HIGH confidence)
- [Kubernetes Labels and Selectors](https://kubernetes.io/docs/concepts/overview/working-with-objects/labels/) — tag/selector scheduling model (HIGH confidence)
- [AWS Prescriptive Guidance: Retry with Backoff](https://docs.aws.amazon.com/prescriptive-guidance/latest/cloud-design-patterns/retry-backoff.html) — exponential backoff state machine (HIGH confidence)

---
*Architecture research for: Master of Puppets — job output capture, execution history, retry, DAG dependencies, environment tags, CI/CD integration*
*Researched: 2026-03-04*
