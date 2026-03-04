# Stack Research

**Domain:** Distributed job scheduling / task orchestration — adding output capture, retry, DAG dependencies, and CI/CD integration to an existing FastAPI/SQLAlchemy/APScheduler system
**Researched:** 2026-03-04
**Confidence:** HIGH (core libraries verified via official sources and PyPI; architectural decisions follow well-established patterns in the existing codebase)

---

## Context: What Already Exists

This is a milestone addition to an existing system. The stack below documents only what needs to be ADDED. Existing stack (do not change):

| Component | Current | Status |
|-----------|---------|--------|
| Backend | FastAPI (Python) | Locked |
| ORM | SQLAlchemy 2.x async (`asyncpg` / `aiosqlite`) | Locked |
| Scheduler | APScheduler 3.11.2 (`AsyncIOScheduler`) | Locked — stay on 3.x |
| DB | SQLite (dev) / PostgreSQL 15 (prod) | Locked |
| Auth | JWT + mTLS + Ed25519 signing | Locked — zero-trust |
| Schema mgmt | `create_all` + manual ALTER TABLE | Locked — no Alembic |

---

## Recommended Stack — New Additions

### Core Technologies

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| SQLAlchemy (existing) | 2.x (existing) | `JobExecution` history table — per-run records with stdout/stderr/exit_code/retry state | Already in stack; zero new dependency. Add a new `job_executions` table alongside existing `jobs` table. Standard pattern for job history. |
| APScheduler 3.x (existing) | 3.11.2 (existing) | Cron scheduling backbone | Stay on 3.x — 4.x is still alpha (4.0.0a6 as of April 2025, not production-ready). Do NOT upgrade. |
| tenacity | 9.1.4 | Retry policy execution — exponential backoff with jitter, configurable max attempts, async-native | The de-facto standard Python retry library. Supports `AsyncRetrying`, asyncio/Trio/Tornado. Has `wait_exponential`, `wait_random_exponential`, stop conditions, per-exception routing. Actively maintained (9.1.4 released Feb 2026). No external dependencies. |
| networkx | 3.x | DAG dependency resolution — topological sort for job dependency graphs | Pure Python graph library; `topological_sort()` and `is_directed_acyclic_graph()` built-in. Lightweight (no broker, no distributed infra). Ideal for in-process DAG validation at job creation time. The dependency graph lives in the DB; networkx resolves order at dispatch time. |

### Supporting Libraries

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `asyncio.create_subprocess_exec` | stdlib (Python 3.11+) | Capture stdout/stderr from node-executed scripts for the result-reporting path | Use in `node.py` (puppet agent) — wrap subprocess calls to collect output before reporting back via `/work/result`. No new dependency needed. |
| `aiosqlite` (existing) | existing | SQLite async for dev | Already present — new tables auto-created by `create_all`. |
| `asyncpg` (existing) | existing | PostgreSQL async for prod | Already present. |

### Development Tools

| Tool | Purpose | Notes |
|------|---------|-------|
| Migration SQL files | Manual schema evolution | Continue the `migration_vNN.sql` pattern. New tables: `job_executions`, columns on `jobs` (retry fields), columns on `nodes` (env_tag). |
| pytest + pytest-asyncio (existing) | Test new service logic | All new service functions (`retry_service.py`, DAG resolution) are async — use existing test infra. |

---

## Installation

```bash
# New runtime dependencies only (add to puppeteer/requirements.txt)
pip install tenacity==9.1.4
pip install networkx==3.4.2
```

No new infrastructure components (no Redis, no Celery, no broker). Everything runs in-process.

---

## Detailed Rationale Per Capability

### 1. Job Output Capture (stdout/stderr, exit codes, per-execution records)

**Pattern:** Introduce a `JobExecution` table (new SQLAlchemy model) as a child of `Job`. Each `Job` can have multiple `JobExecution` rows — one per attempt (including retries).

```
Job (existing)
  guid: PK
  status: PENDING | ASSIGNED | COMPLETED | FAILED
  retry_count: int (NEW column)
  max_retries: int (NEW column)
  retry_delay_seconds: int (NEW column)
  ...

JobExecution (NEW table)
  id: PK (autoincrement)
  job_guid: FK → jobs.guid
  attempt_number: int (1-indexed)
  node_id: str
  started_at: datetime
  completed_at: datetime
  exit_code: int nullable
  stdout: Text nullable
  stderr: Text nullable
  success: bool
  error_detail: Text nullable
```

**Node side** (`node.py` / `runtime.py`): The existing `ResultReport` model already carries `result` and `error_details`. Extend `ResultReport` to include `stdout`, `stderr`, and `exit_code` fields. The puppet node uses `asyncio.create_subprocess_exec` (or the direct subprocess path) and captures `communicate()` output — both stdout and stderr — before POSTing to `/work/result`.

**Orchestrator side**: `job_service.report_result()` writes a new `JobExecution` row on every call (each call = one attempt). `Job.status` reflects the overall outcome; `JobExecution` rows are the per-attempt audit trail.

**Why this design over alternatives:**
- Storing output in `Job.result` (current) is a single JSON blob — loses attempt-level detail on retries
- A separate `JobExecution` table is the standard job queue pattern (used by Sidekiq, Celery, Faktory, etc.)
- Keeps stdout/stderr out of the `jobs` table (prevents row bloat, allows pruning old execution records independently)

**Confidence:** HIGH — this is the canonical SQL schema pattern for job execution history.

### 2. Retry Policies (count + backoff)

**Pattern:** Store retry configuration on the `Job` (and `ScheduledJob` for definitions). Add a `RetryService` that uses tenacity internally OR implement retry as pure orchestrator logic — the simpler approach given the pull model.

**Recommended approach — orchestrator-side retry without tenacity decorator:**

Because the execution happens on a remote node (not in the orchestrator's process), tenacity's decorator pattern does not apply directly. Instead:

1. Node reports `success=False` to `/work/result`
2. `job_service.report_result()` checks `job.retry_count < job.max_retries`
3. If retries remain: create a new `PENDING` job (cloning payload + incrementing `attempt_number`), set a `scheduled_after` timestamp using backoff formula
4. The pull loop in `pull_work()` skips jobs where `created_at < scheduled_after` (a new nullable column)

**Backoff formula (implement inline, no library needed):**
```python
delay = min(base_delay * (2 ** attempt_number), max_delay)  # exponential cap
delay += random.uniform(0, delay * 0.1)  # 10% jitter
```

**Tenacity still useful for:** Retrying the orchestrator's own DB calls or HTTP calls to internal services (e.g., if foundry build requests need resilience). Add as a decorator on those functions.

**Fields to add to `Job` table:**
```
retry_count: int DEFAULT 0        -- how many retries have been attempted
max_retries: int DEFAULT 0        -- 0 = no retry
retry_backoff: str DEFAULT 'exponential'  -- 'fixed' | 'exponential'
retry_delay_base: int DEFAULT 30  -- seconds
scheduled_after: datetime nullable  -- null = run immediately; set on retry delay
```

**Fields to add to `ScheduledJob` table:**
```
max_retries: int DEFAULT 0
retry_backoff: str DEFAULT 'exponential'
retry_delay_base: int DEFAULT 30
```

**Confidence:** HIGH — this pattern (re-queue on failure with backoff column) is standard in job queue systems that use a DB as the queue.

### 3. Job Dependencies (DAG-style)

**Pattern:** Store dependency edges in a `JobDependency` table. Validate DAGs using networkx at definition time. Enforce at dispatch time in `pull_work()`.

```
JobDependency (NEW table)
  id: PK
  job_guid: str FK → jobs.guid       -- the job that depends on upstream
  depends_on_guid: str FK → jobs.guid -- must be COMPLETED before job_guid can run
```

**Dispatch enforcement in `pull_work()`:**
- Before assigning a job, check `JobDependency` — if any `depends_on_guid` is not COMPLETED, skip (leave PENDING)
- This is a simple `SELECT COUNT(*) WHERE job_guid=? AND depends_on_guid NOT IN (SELECT guid FROM jobs WHERE status='COMPLETED')` check

**DAG validation at creation time:**
```python
import networkx as nx

def validate_dag(existing_edges: list[tuple], new_edge: tuple) -> bool:
    G = nx.DiGraph()
    G.add_edges_from(existing_edges + [new_edge])
    return nx.is_directed_acyclic_graph(G)
```

This prevents cycles at the API level (HTTP 400 if adding a dependency would create a cycle).

**Scope note:** DAG dependencies apply to ad-hoc `Job` instances. For `ScheduledJob` definitions, support a `depends_on_definition_id` field — when the scheduler fires job B, it checks if the most recent execution of job A (for the same cron window) succeeded.

**Why networkx over alternatives:**
- networkx is a pure-Python graph library with zero external dependencies
- `is_directed_acyclic_graph()` and `topological_sort()` are production-ready, well-tested stdlib-grade operations
- No need for Airflow, Prefect, or Dagster — those are full orchestration platforms that would replace, not extend, this system
- Celery has DAG support (chains/chords/groups) but requires a message broker (Redis/RabbitMQ) — incompatible with the pull model and adds significant operational complexity

**Confidence:** HIGH for the DB schema pattern; HIGH for networkx for cycle detection; MEDIUM for the scheduled-job dependency logic (needs careful design of "most recent successful run" semantics).

### 4. Environment Node Tags (DEV/TEST/PROD)

**Pattern:** Extend the existing `tags` field on `Node` with a reserved namespace convention. No new DB columns needed immediately.

**Current state:** `Node.tags` is a JSON list of strings (e.g., `["gpu", "linux"]`). Nodes report tags at heartbeat time.

**Addition:** Standardize on reserved environment tag values: `env:dev`, `env:test`, `env:prod`. The existing tag-matching logic in `pull_work()` already handles arbitrary tag requirements — jobs that set `target_tags: ["env:prod"]` will only run on nodes that have `"env:prod"` in their tag set.

**Node-side:** Add `ENV_TAG` env var to node compose files. Node reports `["env:dev"]` (or whatever) in heartbeat tags. Zero code change needed in the matching logic.

**Optional UI enhancement:** Dashboard can render `env:*` tags with color coding (green=prod, amber=test, blue=dev) by detecting the `env:` prefix.

**CI/CD promotion pattern:** A DEV → TEST → PROD pipeline is implemented as:
1. CI system dispatches job with `target_tags: ["env:dev"]`
2. On success (webhook from orchestrator or polling `/jobs/{guid}`), CI dispatches next job with `target_tags: ["env:test"]`
3. On success, dispatch to `target_tags: ["env:prod"]`

**Confidence:** HIGH — the existing tag infrastructure already supports this; this is purely a convention/documentation addition.

### 5. CI/CD API Integration

**Pattern:** Existing service principal + API key auth is already machine-friendly. The additions are:
1. A synchronous job dispatch endpoint with a predictable polling URL
2. A webhook callback option (POST to caller URL on job completion)
3. OpenAPI-documented examples in the existing `/docs` route

**Concrete additions needed:**

**`POST /api/v1/jobs/dispatch`** (new alias, same as existing `POST /jobs` but with richer response):
```json
{
  "guid": "...",
  "status": "PENDING",
  "poll_url": "https://host/jobs/{guid}",
  "estimated_start": "...",
  "target_tags": ["env:prod"]
}
```

**`GET /api/v1/jobs/{guid}/output`** (new endpoint):
Returns the latest `JobExecution` record for the job — stdout, stderr, exit_code, attempt_number.

**`POST /jobs` with `callback_url` field** (extension to `JobCreate`):
When job completes, orchestrator POSTs to `callback_url` with job status and output. Implement as a FastAPI background task using `httpx` (already available as a dependency of FastAPI/Starlette).

**Auth:** CI/CD systems authenticate with service principal client_id/client_secret (already implemented in Sprint 10). No new auth mechanism needed.

**OpenAPI webhooks:** FastAPI 0.99+ supports `@app.webhooks.post()` for documenting outbound webhook events in the OpenAPI schema. Use this for documenting the callback payload shape.

**Confidence:** HIGH — the existing service principal system is exactly right for this. The implementation is additive to existing endpoints.

---

## Alternatives Considered

| Recommended | Alternative | Why Not |
|-------------|-------------|---------|
| In-process DAG with networkx + DB edges | Celery chains/chords | Requires Redis/RabbitMQ broker; breaks the pull model; adds operational complexity out of proportion to the feature |
| In-process DAG with networkx + DB edges | Prefect embedded | Prefect is a full orchestration platform — replaces rather than extends this system; adds 10+ new dependencies; not embeddable |
| In-process DAG with networkx + DB edges | Airflow | Same problem as Prefect, plus Airflow requires its own DB and scheduler process |
| APScheduler 3.11.2 (stay) | APScheduler 4.x upgrade | 4.x is still alpha (4.0.0a6) as of April 2025. API is incompatible with 3.x. Breaking change: `add_job()` semantics changed, concept of "job" split into Task/Schedule/Job. Not production-ready. |
| Orchestrator-side retry re-queue | tenacity decorator on execution | Execution happens on remote node — decorator pattern can't retry remote subprocess. Orchestrator re-queue is the correct pattern for distributed job systems. |
| `env:prod` tag convention | Separate `environment` column on Node | The existing tag matching already works; a new column would duplicate functionality. Convention is simpler and already supported by the dispatch logic. |
| httpx for webhook callbacks | aiohttp | httpx is already a transitive dependency of FastAPI/Starlette. No new dependency needed. |
| JobExecution child table | Extending Job.result JSON | Result JSON is a single blob — loses per-attempt granularity needed for retry audit trail. Separate table is the correct normalization. |

---

## What NOT to Use

| Avoid | Why | Use Instead |
|-------|-----|-------------|
| APScheduler 4.x | Still alpha (4.0.0a6, April 2025). Breaking API changes from 3.x. No DAG support added. Not worth migration risk for an in-flight production system. | Stay on APScheduler 3.11.2 |
| Celery | Requires broker (Redis/RabbitMQ). Fundamentally incompatible with pull model — Celery pushes work to workers, this system needs nodes to poll. Adding Celery would require a full architecture change. | APScheduler 3.x + custom orchestrator-side retry logic |
| Prefect / Dagster / Airflow | Full platform replacements, not embeddable extensions. Each requires its own scheduler process, DB, and UI. 10x operational complexity for DAG features that can be implemented with 50 lines of networkx. | networkx for DAG validation + DB edge table for dependency tracking |
| `retrying` library | Unmaintained since 2016. tenacity is its active fork. | tenacity 9.1.4 |
| `backoff` library | Less capable than tenacity (no async support, fewer strategies). | tenacity 9.1.4 |
| Storing stdout/stderr in `Job.result` JSON | Row bloat; loses per-attempt history on retries; no pruning path. | Separate `JobExecution` table with FK to jobs |
| APScheduler `SQLAlchemyJobStore` for production schedules | The project manages `ScheduledJob` records in its own table (not APScheduler's internal job store). The existing `SchedulerService.sync_scheduler()` pattern of syncing DB → APScheduler in-memory is correct and must be preserved. | Continue using MemoryJobStore for APScheduler + custom `ScheduledJob` table for persistence |

---

## Stack Patterns by Variant

**If retry delay is less than the node poll interval (~5 seconds):**
- Use `scheduled_after = NOW()` (immediate retry), not a delay — no point in a delay smaller than the poll interval

**If job has no max_retries set (max_retries = 0):**
- Behave exactly as today — one attempt, FAILED on failure. Zero code-path change for existing jobs.

**If a DAG dependency chain has a failing upstream:**
- Downstream jobs remain PENDING indefinitely (they never get dispatched)
- Add a `DAG_BLOCKED` status or timeout policy in a follow-up milestone — out of scope here

**If callback_url is set on a job:**
- Orchestrator fires background task on `report_result()` using `httpx.AsyncClient().post(callback_url, json=payload)`
- Failure to deliver callback should not fail the job — log and move on

**If the node is SQLite (dev):**
- All new tables (`job_executions`, `job_dependencies`) use `create_all` — no migration needed for fresh installs
- Existing dev installs: run `migration_v14.sql` (manual ALTER TABLE pattern, same as all previous migrations)

---

## Version Compatibility

| Package | Compatible With | Notes |
|---------|-----------------|-------|
| tenacity 9.1.4 | Python 3.10+ | Requires Python 3.10 minimum. Project is running 3.11+ (FastAPI + asyncpg both require 3.10+). Compatible. |
| networkx 3.4.2 | Python 3.10+ | Pure Python. No C extensions. Works on SQLite and Postgres hosts equally. |
| APScheduler 3.11.2 | asyncio, SQLAlchemy 2.x | Confirmed compatible with existing `AsyncIOScheduler` usage. |

---

## Sources

- APScheduler PyPI page (https://pypi.org/project/APScheduler/) — confirmed 3.11.2 is current stable; 4.0.0a6 is latest alpha (not production-ready). Confidence: HIGH.
- APScheduler 3.x User Guide (https://apscheduler.readthedocs.io/en/3.x/userguide.html) — confirmed SQLAlchemyJobStore supports both SQLite and PostgreSQL. Confidence: HIGH.
- APScheduler 4.x master docs (https://apscheduler.readthedocs.io/en/master/userguide.html) — confirmed no native DAG/dependency support in 4.x. Confidence: HIGH.
- tenacity PyPI (https://pypi.org/project/tenacity/) — confirmed 9.1.4 stable (Feb 2026), Python 3.10+ requirement. Confidence: HIGH.
- tenacity GitHub (https://github.com/jd/tenacity) — confirmed `AsyncRetrying`, full async support for asyncio/Trio/Tornado, `wait_exponential`, `wait_random_exponential`, `retry_if_exception_type`. Confidence: HIGH.
- NetworkX DAG docs (https://networkx.org/nx-guides/content/algorithms/dag/index.html) — confirmed `is_directed_acyclic_graph()` and `topological_sort()` APIs. Confidence: HIGH.
- FastAPI OpenAPI webhooks (https://fastapi.tiangolo.com/advanced/openapi-webhooks/) — confirmed `@app.webhooks.post()` available in FastAPI 0.99+. Confidence: HIGH.
- WebSearch: APScheduler vs Celery comparison (multiple sources) — confirmed Celery requires broker, pull-model incompatible. Confidence: MEDIUM.
- WebSearch: Python retry libraries 2025 — confirmed tenacity is de-facto standard, `retrying` and `backoff` are not recommended. Confidence: MEDIUM.

---

*Stack research for: Master of Puppets — job output capture, retry, DAG dependencies, CI/CD integration milestone*
*Researched: 2026-03-04*
