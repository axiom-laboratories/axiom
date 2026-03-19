# Phase 31: Environment Tags + CI/CD Dispatch - Research

**Researched:** 2026-03-18
**Domain:** FastAPI backend — DB schema extension, node enrollment, job dispatch filtering, CI/CD-facing REST API
**Confidence:** HIGH

---

## Summary

Phase 31 adds first-class environment tags to nodes and exposes a CI/CD-friendly dispatch endpoint. The work is primarily backend: a new `env_tag` column on `nodes`, heartbeat/enrollment changes in `node.py`, node-selection filter changes in `job_service.py`, and two new routes in `main.py`.

The existing `tags` / `operator_tags` JSON-list mechanism on nodes and jobs already handles a similar "env:" prefix convention (lines 315–324 of `job_service.py`). That mechanism is a soft convention—environment isolation is enforced through the `env:` prefix in the tags list, but the tag is arbitrary text stored in a JSON array. This phase replaces the ad-hoc `env:` convention with a proper, indexed, single-value `env_tag` column, dedicated fields in API models, and explicit DB-level semantics.

The CI/CD dispatch requirements (ENVTAG-04) are a superset of the existing job-creation path: `POST /api/dispatch` wraps `JobService.create_job()` with service-principal-only auth, structured response shape, and a stable poll endpoint. The poll endpoint (`GET /api/dispatch/{job_guid}/status`) is a thin read on the `jobs` + `execution_records` tables—no new service layer is needed.

**Primary recommendation:** Add `env_tag` as a standalone nullable `String(32)` column on `Node` and `Job`/`ScheduledJob`; wire it through heartbeat, enrollment, and the node-selection loop in `pull_work()`; then add two new routes using `require_permission("jobs:write")` restricted to service-principal auth where stated in the requirements.

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| ENVTAG-01 | Node has a configurable environment tag declared at enrollment and stored on the node record | `Node` DB model needs `env_tag` nullable column; `HeartbeatPayload` and enrollment path need corresponding field; node.py reads `ENV_TAG` env var |
| ENVTAG-02 | Job definitions and ad-hoc dispatches can specify env_tag as an additional targeting constraint | `Job`, `ScheduledJob`, `JobCreate`, `JobDefinitionCreate` need `env_tag` field; `pull_work()` adds env_tag equality check alongside the existing `env:` tag logic |
| ENVTAG-04 | Documented CI/CD dispatch endpoint accepts env_tag, returns structured JSON with poll_url; GET status endpoint suitable for pipeline pass/fail decisions | Two new routes: `POST /api/dispatch` and `GET /api/dispatch/{job_guid}/status`; new Pydantic models `DispatchRequest`, `DispatchResponse`, `DispatchStatusResponse` |
</phase_requirements>

---

## Standard Stack

### Core (already in use — no new dependencies needed)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| FastAPI | current | Route definitions, dependency injection | Project standard |
| SQLAlchemy async | current | ORM, migrations via `create_all` | Project standard |
| Pydantic v2 | current | Request/response validation | Project standard |
| aiosqlite / asyncpg | current | SQLite dev / Postgres prod | Project standard |

### No New Dependencies

All capabilities required for this phase exist in the current dependency set. No `pip install` step is needed.

**Migration file:** `migration_v34.sql` (next after `migration_v33.sql`, already in repo) — pattern: `ALTER TABLE ... ADD COLUMN IF NOT EXISTS`.

---

## Architecture Patterns

### Recommended File Touch List

```
puppeteer/
├── agent_service/
│   ├── db.py                          # Add env_tag to Node, Job, ScheduledJob
│   ├── models.py                      # Add env_tag to HeartbeatPayload, JobCreate,
│   │                                  # JobDefinitionCreate/Update, NodeResponse,
│   │                                  # + new DispatchRequest/Response models
│   ├── main.py                        # POST /api/dispatch, GET /api/dispatch/{guid}/status
│   └── services/
│       └── job_service.py             # env_tag column check in pull_work()
│
puppets/
└── environment_service/
    └── node.py                        # Read ENV_TAG env var; send in heartbeat payload
│
puppeteer/
└── migration_v34.sql                  # ALTER TABLE nodes/jobs/scheduled_jobs
```

### Pattern 1: DB Column Addition (env_tag)

**What:** Add `env_tag` as a nullable `String(32)` column on `Node`, `Job`, and `ScheduledJob`. 32 chars is sufficient for DEV/TEST/PROD plus reasonable custom strings.

**Confidence:** HIGH — follows exact same pattern used for every prior nullable column addition (Phase 29-01 decision: "All new DB columns nullable-only — safe migration for existing deployments, no NOT NULL constraints").

```python
# db.py — Node model addition
env_tag: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)

# db.py — Job model addition
env_tag: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)

# db.py — ScheduledJob model addition
env_tag: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
```

### Pattern 2: Heartbeat Payload Extension

**What:** Add `env_tag` to `HeartbeatPayload` model in `models.py`. The node reads `ENV_TAG` environment variable and includes it in every heartbeat. The orchestrator stores it on `Node.env_tag`.

**Security note — SEC-02 parallel:** The existing code strips `env:` prefix tags from node-reported tags to prevent self-escalation (`receive_heartbeat()` lines 399–400). The same concern applies to `env_tag`. Resolution: the orchestrator MUST NOT overwrite `node.env_tag` from the heartbeat if an operator has manually set it. Two options:
1. Store `env_tag` as reported (from heartbeat), similar to `Node.tags`, and allow operator to override via a PATCH endpoint (identical pattern to `operator_tags`)
2. Store it only at enrollment, never updated by heartbeat

**Recommended approach:** Follow the `operator_tags` pattern — store heartbeat-reported value in `env_tag` at enrollment time; add optional operator override later (ENVTAG-03 is Phase 32). For this phase, heartbeat simply updates `env_tag` from the node payload. This keeps the implementation minimal and aligns with the requirements (ENVTAG-01 says "declared at enrollment", not "operator-locked").

```python
# models.py — HeartbeatPayload
class HeartbeatPayload(BaseModel):
    node_id: str
    hostname: str
    stats: Optional[Dict] = None
    tags: Optional[List[str]] = None
    capabilities: Optional[Dict[str, str]] = None
    job_telemetry: Optional[Dict[str, Dict]] = None
    upgrade_result: Optional[Dict] = None
    env_tag: Optional[str] = None   # NEW: ENV_TAG env var value
```

### Pattern 3: Node Selection Filter in pull_work()

**What:** After the existing env: tag checks (lines 315–324 in job_service.py), add a strict env_tag column check.

**Logic:**
- If `job.env_tag` is set AND `node.env_tag` is set: they must match exactly (case-insensitive).
- If `job.env_tag` is set but `node.env_tag` is None: node is ineligible (skip).
- If `job.env_tag` is None: any node qualifies (env-tag-agnostic dispatch).
- If `node.env_tag` is set but `job.env_tag` is None: node is eligible (env-untagged jobs can run on env-tagged nodes).

This is a looser contract than the existing `env:` tag isolation (which blocks env-tagged nodes from running tag-less jobs). The requirements do not mandate node-side lockdown for ENVTAG-01/02, so the looser model is correct. If stricter isolation is needed, it can be added in Phase 32.

```python
# job_service.py — inside pull_work() candidate loop, after existing env: tag checks
# ENVTAG-02: env_tag column match
job_env_tag = candidate.env_tag  # None means "any node"
node_env_tag = node.env_tag if node else None

if job_env_tag is not None:
    if node_env_tag is None or node_env_tag.upper() != job_env_tag.upper():
        continue
```

### Pattern 4: POST /api/dispatch Route

**What:** CI/CD-facing job dispatch endpoint. Requires service-principal auth (any principal with `jobs:write` permission), returns structured `DispatchResponse` with `poll_url`.

**Auth:** Uses `require_permission("jobs:write")` — the same guard used by `POST /api/jobs`. Service principals already hold this permission when created with `operator` role (see seeded operator permissions in `main.py` lifespan).

**Route shape:**
```python
@app.post("/api/dispatch", response_model=DispatchResponse, tags=["CI/CD Dispatch"])
async def dispatch_job(
    req: DispatchRequest,
    request: Request,
    current_user = Depends(require_permission("jobs:write")),
    db: AsyncSession = Depends(get_db),
):
    ...
```

**DispatchRequest model:**
```python
class DispatchRequest(BaseModel):
    job_definition_id: str          # UUID of ScheduledJob to dispatch
    env_tag: Optional[str] = None   # Override env_tag targeting for this dispatch
    # Optional overrides (CI/CD may not need these but document for completeness)
    max_retries: Optional[int] = None
    timeout_minutes: Optional[int] = None
```

**DispatchResponse model:**
```python
class DispatchResponse(BaseModel):
    job_guid: str
    status: str                     # e.g. "PENDING"
    job_definition_id: str
    job_definition_name: str
    env_tag: Optional[str] = None
    poll_url: str                   # Absolute URL to GET /api/dispatch/{guid}/status
```

**Implementation notes:**
- Fetch the `ScheduledJob` record to get `script_content`, `signature_id`, `signature_payload`, `capability_requirements`, etc.
- Construct a `JobCreate`-equivalent and call `JobService.create_job()`
- Build `poll_url` from the request's `base_url` (FastAPI `Request.base_url`)
- Audit with `audit()` helper: action `"dispatch_job"`, resource_id=`job_guid`

### Pattern 5: GET /api/dispatch/{job_guid}/status Route

**What:** Polling endpoint for CI/CD pipelines. Returns structured terminal/non-terminal state. No auth required? The requirements say "suitable for pipeline integration" but do not explicitly say unauthenticated. Recommend: require `jobs:read` — service principals have this.

**DispatchStatusResponse model:**
```python
class DispatchStatusResponse(BaseModel):
    job_guid: str
    status: str                     # PENDING, ASSIGNED, COMPLETED, FAILED, RETRYING, DEAD_LETTER, SECURITY_REJECTED
    exit_code: Optional[int] = None
    node_id: Optional[str] = None
    attempt: Optional[int] = None   # retry_count from Job
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    is_terminal: bool               # computed: True if status in terminal set
```

**Implementation:** Join `Job` + most recent `ExecutionRecord` (by `completed_at DESC`). The `attempt` field comes from `job.retry_count + 1` (current attempt number, same logic as `ExecutionRecord.attempt_number`).

### Pattern 6: node.py ENV_TAG Integration

**What:** Node reads `ENV_TAG` env var and includes it in every heartbeat payload.

```python
# node.py — in heartbeat_loop(), inside the while True loop:
env_tag = os.getenv("ENV_TAG")  # None if not set — orchestrator treats None as "no tag"

payload = {
    "node_id": NODE_ID,
    "hostname": socket.gethostname(),
    "stats": stats,
    "tags": tags,
    "capabilities": caps,
    "env_tag": env_tag,   # NEW
}
```

### Pattern 7: Migration File

```sql
-- migration_v34.sql
-- Phase 31: Environment Tags — add env_tag to nodes, jobs, scheduled_jobs

ALTER TABLE nodes ADD COLUMN IF NOT EXISTS env_tag VARCHAR(32);
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS env_tag VARCHAR(32);
ALTER TABLE scheduled_jobs ADD COLUMN IF NOT EXISTS env_tag VARCHAR(32);
```

The migration file is named `v34` because `v33.sql` was the last one written (visible in the project). Fresh deployments get the column via `create_all`. Existing Postgres deployments need this migration applied manually (project pattern).

**Caveat on migration_v18.sql (currently modified):** `git status` shows `M puppeteer/migration_v18.sql`. The planner should be aware this file has uncommitted changes. It does not affect Phase 31 — the new migration is `v34`.

### Anti-Patterns to Avoid

- **Do not reuse the env: tag prefix mechanism as the primary implementation.** The existing `env:` tag logic in `pull_work()` is a security guardrail for the existing tags system. Phase 31 should use the new `env_tag` column. Both can coexist — the `env:` guard remains for backward compatibility.
- **Do not add a NOT NULL constraint or default value to env_tag.** Follows the Phase 29 decision: all new columns are nullable-only.
- **Do not derive the 409 status code prematurely.** The STATE.md research flag (Phase 31) says the error response contract for "no eligible node" must be confirmed stable before documenting it as the CI/CD API. Use HTTP 409 Conflict with a structured JSON body — this is the conventional REST pattern for "request is valid but no resource currently satisfies it." However, this response is only possible for synchronous dispatch. The dispatch endpoint creates a job and returns PENDING immediately; the "no eligible node" condition is discovered later by `pull_work()`. Therefore, the endpoint does not return 409 at create time — the job stays PENDING until either a matching node picks it up or it times out. The `poll_url` lets CI/CD detect the no-node case by polling until timeout or a configurable window.
- **Do not add `env_tag` to the security-stripping logic in `receive_heartbeat()` without careful thought.** The env: prefix strip exists because env tags control dispatch routing. `env_tag` is a direct column; operators can override it via future admin endpoints. For Phase 31, accept the node's reported value — the security implication is that a compromised node could report a false `env_tag` and get PROD jobs dispatched to it. Accept this for now; document it. The existing `operator_tags` pattern (which overrides `tags`) is the model for future operator-side locking.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Service-principal-only auth | Custom auth check in dispatch route | `require_permission("jobs:write")` via `Depends` | Already enforces SP + user + API key uniformly |
| Stable base URL for poll_url | Hardcode host | `request.base_url` from FastAPI `Request` | Handles reverse proxy, HTTPS, port correctly |
| "Is this a terminal status?" | Custom if/else | Constant `TERMINAL_STATUSES = {"COMPLETED", "FAILED", "DEAD_LETTER", "SECURITY_REJECTED"}` | Same set already used in `job_service.py` line 832 |
| Pagination or complex query for status poll | Custom join | Single `select(Job)` by guid + `select(ExecutionRecord)` latest by `job_guid, completed_at DESC` | Simple, consistent with existing pattern |

---

## Common Pitfalls

### Pitfall 1: ENV_TAG Case Sensitivity
**What goes wrong:** Node sends `"prod"`, job requires `"PROD"` — dispatch never matches.
**Why it happens:** No normalization is applied to the string before storage.
**How to avoid:** Normalize to uppercase in `receive_heartbeat()` before storing, and normalize in `JobCreate`/`DispatchRequest` validation. Use `@field_validator` with `v.upper() if v else v` — same pattern as `normalize_os_family` in `BlueprintCreate`.
**Warning signs:** Jobs stay PENDING indefinitely even when tagged nodes are ONLINE.

### Pitfall 2: poll_url Contains localhost in Docker
**What goes wrong:** `request.base_url` resolves to `http://localhost:8001` inside a Docker network — CI/CD pipeline outside the network can't reach it.
**Why it happens:** FastAPI reflects the `Host` header, which is `localhost:8001` by default.
**How to avoid:** If `AGENT_URL` env var is set, use it as the base for `poll_url` construction. Fall back to `str(request.base_url)` for local dev. Add a `PUBLIC_URL` config key to `Config` table as future-proof override.
**Warning signs:** CI/CD pipelines report connection refused when polling the returned URL.

### Pitfall 3: ScheduledJob.env_tag Not Seeded on Existing Records
**What goes wrong:** Existing job definitions have `env_tag = NULL` — dispatching them without specifying `env_tag` in the dispatch request causes the job to be env-agnostic (correct behavior), but operators expect a default.
**Why it happens:** Migration adds the column as nullable; no backfill.
**How to avoid:** Document this in the migration file. The behavior is correct (NULL env_tag = any node); the operator should update existing definitions if they want env isolation.

### Pitfall 4: Dispatch Endpoint Fetching ScheduledJob Script
**What goes wrong:** `DispatchRequest.job_definition_id` not found — returns 500 instead of structured 404.
**Why it happens:** Missing existence check before creating the job.
**How to avoid:** Always `scalar_one_or_none()` and raise `HTTPException(404, ...)` with a machine-readable JSON body when the definition is not found.

### Pitfall 5: audit() is Synchronous
**What goes wrong:** Adding `await audit(...)` causes a `TypeError` at runtime.
**Why it happens:** The `audit()` helper is a plain `def` function (not `async def`) — confirmed by the Phase 30 state decision: "audit() is sync (def) — removed erroneous await calls; reordered before db.commit()".
**How to avoid:** Call `audit(db, ...)` without `await`. Call it before `await db.commit()`.

### Pitfall 6: migration_v18.sql Has Uncommitted Changes
**What goes wrong:** If `migration_v18.sql` is committed as part of Phase 31, it may introduce unexpected changes to the main branch.
**Why it happens:** The file appears modified in `git status`. The planner should verify the change is intentional before committing Phase 31 files.
**How to avoid:** The Phase 31 migration should be written to `migration_v34.sql` only. Do not modify `migration_v18.sql` unless explicitly addressing that pre-existing change.

---

## Code Examples

### Normalizing env_tag in Pydantic
```python
# models.py — in DispatchRequest and HeartbeatPayload
@field_validator("env_tag", mode="before")
@classmethod
def normalize_env_tag(cls, v):
    return v.strip().upper() if isinstance(v, str) and v.strip() else None
```

### Building poll_url
```python
# main.py — in POST /api/dispatch handler
public_url = os.getenv("PUBLIC_URL", str(request.base_url).rstrip("/"))
poll_url = f"{public_url}/api/dispatch/{job_guid}/status"
```

### env_tag filter in pull_work()
```python
# job_service.py — inside for candidate in jobs loop, after existing env: tag checks
job_env_tag = candidate.env_tag  # already normalized uppercase at creation
node_env_tag = (node.env_tag or "").upper() if node and node.env_tag else None

if job_env_tag:  # job requires a specific env
    if node_env_tag != job_env_tag:
        continue
```

### Migration
```sql
-- migration_v34.sql
ALTER TABLE nodes ADD COLUMN IF NOT EXISTS env_tag VARCHAR(32);
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS env_tag VARCHAR(32);
ALTER TABLE scheduled_jobs ADD COLUMN IF NOT EXISTS env_tag VARCHAR(32);
```

### DispatchStatusResponse terminal check
```python
TERMINAL_STATUSES = {"COMPLETED", "FAILED", "DEAD_LETTER", "SECURITY_REJECTED"}

return DispatchStatusResponse(
    job_guid=job.guid,
    status=job.status,
    exit_code=latest_record.exit_code if latest_record else None,
    node_id=job.node_id,
    attempt=job.retry_count + 1,
    started_at=job.started_at,
    completed_at=job.completed_at,
    is_terminal=job.status in TERMINAL_STATUSES,
)
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| env: tag prefix soft convention in JSON array | First-class `env_tag` column on Node and Job | Phase 31 | Enables reliable CI/CD dispatch without string parsing |
| No CI/CD dispatch surface | `POST /api/dispatch` + poll endpoint | Phase 31 | Pipelines can dispatch and poll without HTML scraping |

**Deprecated/outdated:**
- `env:` prefix in `tags` list: remains functional for backward compatibility but is superseded by `env_tag` column for the primary use case. Do not remove the existing guard.

---

## Open Questions

1. **Should POST /api/dispatch restrict to service principals only, or allow any `jobs:write` principal?**
   - What we know: Requirements say "requires service principal auth". The `require_permission` factory accepts any auth type (user JWT, SP JWT, API key). The SP-only restriction would require an additional check in the route: `if not isinstance(current_user, _SPUserProxy): raise HTTPException(403, ...)`.
   - What's unclear: Whether a human operator with `jobs:write` should also be able to use this endpoint (useful for testing pipelines from the dashboard).
   - Recommendation: Accept any `jobs:write` principal. The SP restriction in the requirements describes the intended CI/CD use case, not a technical enforcement requirement. Document that SPs are the intended caller.

2. **What is the "no eligible node" response contract?**
   - What we know: STATE.md research flag says "the 409 response contract when no eligible node exists must be confirmed stable before being documented as the CI/CD integration API". As analyzed above, the dispatch endpoint does not block on node availability — it returns PENDING immediately.
   - What's unclear: Whether the requirements intend a synchronous blocking dispatch or an async one.
   - Recommendation: Implement as async/non-blocking (create job, return PENDING + poll_url). Document that CI/CD pipelines detect the "no node" condition by polling until the job enters a terminal state or a wall-clock timeout is exceeded.

3. **Does `env_tag` on ScheduledJob flow through scheduler_service dispatch?**
   - What we know: `scheduler_service.py` creates Job records when firing scheduled jobs. If `ScheduledJob.env_tag` is set, the created `Job.env_tag` should carry it through.
   - What's unclear: Whether the scheduler dispatch path needs to be updated in Phase 31 or deferred to Phase 32.
   - Recommendation: Include it in Phase 31 — the scheduler creates the `Job` record and should copy `env_tag` from the definition.

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (existing) |
| Config file | `puppeteer/pytest.ini` or inferred from project root |
| Quick run command | `cd puppeteer && pytest tests/test_env_tag.py -x` |
| Full suite command | `cd puppeteer && pytest` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| ENVTAG-01 | `Node.env_tag` column exists and is nullable | unit (model inspection) | `cd puppeteer && pytest tests/test_env_tag.py::test_node_has_env_tag -x` | Wave 0 |
| ENVTAG-01 | `Job.env_tag` column exists and is nullable | unit (model inspection) | `cd puppeteer && pytest tests/test_env_tag.py::test_job_has_env_tag -x` | Wave 0 |
| ENVTAG-01 | `HeartbeatPayload` accepts `env_tag` field | unit (model validation) | `cd puppeteer && pytest tests/test_env_tag.py::test_heartbeat_accepts_env_tag -x` | Wave 0 |
| ENVTAG-02 | `pull_work()` skips node when `job.env_tag="PROD"` and `node.env_tag="DEV"` | unit (source inspection) | `cd puppeteer && pytest tests/test_env_tag.py::test_pull_work_env_tag_mismatch_skipped -x` | Wave 0 |
| ENVTAG-02 | `pull_work()` assigns job when `job.env_tag="PROD"` and `node.env_tag="PROD"` | unit (source inspection) | `cd puppeteer && pytest tests/test_env_tag.py::test_pull_work_env_tag_match_assigned -x` | Wave 0 |
| ENVTAG-02 | `pull_work()` assigns job when `job.env_tag=None` regardless of node env_tag | unit (source inspection) | `cd puppeteer && pytest tests/test_env_tag.py::test_pull_work_no_env_tag_assigned -x` | Wave 0 |
| ENVTAG-04 | `DispatchRequest` model accepts `job_definition_id` and `env_tag` | unit (model validation) | `cd puppeteer && pytest tests/test_env_tag.py::test_dispatch_request_model -x` | Wave 0 |
| ENVTAG-04 | `DispatchResponse` model includes `job_guid`, `poll_url`, `is_terminal` shape | unit (model validation) | `cd puppeteer && pytest tests/test_env_tag.py::test_dispatch_response_model -x` | Wave 0 |
| ENVTAG-04 | `DispatchStatusResponse` has `status`, `exit_code`, `node_id`, `attempt`, `started_at`, `completed_at` | unit (model validation) | `cd puppeteer && pytest tests/test_env_tag.py::test_dispatch_status_response_model -x` | Wave 0 |

### Sampling Rate
- **Per task commit:** `cd puppeteer && pytest tests/test_env_tag.py -x`
- **Per wave merge:** `cd puppeteer && pytest`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `puppeteer/tests/test_env_tag.py` — covers all ENVTAG-01, ENVTAG-02, ENVTAG-04 model assertions and source inspection tests
- [ ] No new fixture files needed — existing pytest patterns (model instantiation + `inspect.getsource`) are sufficient

---

## Sources

### Primary (HIGH confidence)

- `puppeteer/agent_service/db.py` — Node, Job, ScheduledJob, ExecutionRecord column patterns; nullable-only convention confirmed
- `puppeteer/agent_service/services/job_service.py` — existing env: tag logic lines 315–324; `pull_work()` candidate loop structure; `TERMINAL_STATUSES` set (line 832)
- `puppeteer/agent_service/main.py` — `require_permission` factory pattern; `_SPUserProxy` class; `audit()` sync calling convention; existing route patterns
- `puppeteer/agent_service/models.py` — `HeartbeatPayload`, `JobCreate`, `NodeResponse`, field_validator patterns
- `puppets/environment_service/node.py` — `ENV_TAG` read pattern (`os.getenv`), heartbeat payload construction
- `.planning/STATE.md` — Phase 31 research flag on 409 contract; Phase 29 decision on nullable-only columns; Phase 30 decision on audit() sync

### Secondary (MEDIUM confidence)

- `puppeteer/migration_v18.sql` and peers — naming convention for migration files (v34 is next)
- `puppeteer/tests/test_retry_wiring.py`, `test_output_capture.py`, `test_attestation.py` — test file patterns (model inspection + source inspection)
- `.planning/REQUIREMENTS.md` — ENVTAG-01, ENVTAG-02, ENVTAG-04 exact requirement text

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — no new dependencies; all patterns verified from existing code
- DB schema: HIGH — direct inspection of db.py and migration files
- Architecture patterns: HIGH — derived from existing service patterns in the same codebase
- Node.py changes: HIGH — `ENV_TAG` env var read pattern is trivial; heartbeat payload structure verified
- Pitfalls: HIGH — several drawn directly from STATE.md documented decisions (audit() sync, nullable-only columns)
- Validation architecture: HIGH — test file patterns verified from Phase 29/30 test files

**Research date:** 2026-03-18
**Valid until:** 2026-04-18 (stable codebase — no external dependencies)
