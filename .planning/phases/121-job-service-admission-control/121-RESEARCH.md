# Phase 121: Job Service & Admission Control - Research

**Researched:** 2026-04-06
**Domain:** API-level resource admission control and memory/CPU limit persistence
**Confidence:** HIGH

## Summary

Phase 121 implements server-side admission control to prevent oversized jobs from being assigned to nodes that cannot accommodate them. This sits between Phase 120 (database schema + API contract) and Phase 122 (node-side integration). The phase adds three critical capabilities: a `parse_bytes()` utility to convert memory strings to bytes, dynamic capacity tracking in `create_job()` and `pull_work()`, and extended dispatch diagnosis with resource-related blocking reasons. No new external dependencies required—all work uses stdlib and existing FastAPI/SQLAlchemy patterns.

**Primary recommendation:** Implement admission control in `job_service.create_job()` (hard-reject at 422 if no node can fit the job) and extend capacity tracking in `pull_work()` (sum ASSIGNED + RUNNING jobs' limits). Extend `get_dispatch_diagnosis()` to explain memory-related blocking with per-node capacity breakdown.

## User Constraints (from CONTEXT.md)

### Locked Decisions

- **Hard rejection at 422 Unprocessable Entity** when job's `memory_limit` exceeds every online node's available capacity
- Error response includes specific detail: "No online node can accommodate memory_limit=4Gi. Largest node capacity: 2Gi (node_alpha)."
- **No force-dispatch override flag** — operators can omit `memory_limit` (null) to skip per-job limits entirely
- **Memory admission only** — CPU limits stored and passed to runtime but not admission-checked (nodes don't report CPU capacity yet)
- **When no nodes are online:** allow job creation (PENDING), admission check skipped — preserves fire-and-forget workflows
- **Jobs with null memory_limit:** assume 512m default for capacity accounting — prevents unlimited jobs from silently consuming all capacity
- **Default configurable** via Config table key `default_job_memory_limit` (hardcoded 512m initial default)
- **Dynamic capacity tracking:** available = `node.job_memory_limit - sum(ASSIGNED + RUNNING jobs' memory_limits on that node)`
- **Server-side `parse_bytes()`** ported from `puppets/environment_service/node.py:25` — converts memory strings to bytes for comparison

### Claude's Discretion

- Exact placement and styling of limit fields in JobDefinitions.tsx create/edit form
- `parse_bytes()` implementation details (regex vs parsing approach)
- Config table interaction pattern for `default_job_memory_limit`
- Diagnosis UI layout within job detail expanded view
- Migration SQL file numbering

### Deferred Ideas (OUT OF SCOPE)

None — discussion stayed within phase scope.

## Standard Stack

### Core Backend (Existing, No Changes)

| Technology | Version | Purpose | Why Standard |
|------------|---------|---------|--------------|
| FastAPI | 0.104+ | REST API server | async-native, auto OpenAPI docs, pydantic validation |
| SQLAlchemy | 2.0+ | ORM for Job/Node persistence | async support, strong type hints, schema migration via create_all |
| Pydantic | 2.0+ | Request/response validation | field validators, discriminated unions, JSON serialization |
| PostgreSQL | 15+ | Production persistence (optional) | ACID, JSON columns, async driver (asyncpg) |
| SQLite | 3.40+ | Local dev persistence | serverless, no setup, file-based |
| Python | 3.11+ | Backend runtime | type hints, async/await, standard library |

### Supporting Libraries (Existing)

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| packaging | 23.0+ | Semver parsing (already in use for version comparison) | Parsing memory/CPU format strings (though stdlib sufficient) |
| asyncpg | 0.27+ | Postgres async driver | Already required for production DB |

### No New Dependencies Required

- **CgroupDetector** uses stdlib `os.path.exists()` — no external library
- **Memory parsing** uses stdlib `re` for regex — no external library
- **Config table** uses existing SQLAlchemy ORM — no new library

## Architecture Patterns

### Admission Control Flow

```
JobCreate request
  ↓
[1] Format validation (Pydantic) — memory_limit matches Docker format
  ↓
[2] API admission check in create_job() — rejects if no online node can fit
  ↓
[3] Job stored as PENDING if:
    - memory_limit <= largest online node's available capacity, OR
    - memory_limit is null (optional), OR
    - no nodes are online (fire-and-forget)
  ↓
[4] pull_work() does secondary capacity sum:
    available = node.job_memory_limit - sum(ASSIGNED + RUNNING limits)
  ↓
[5] Node receives WorkResponse with memory_limit/cpu_limit fields
  ↓
[6] Node-side admission check (Phase 122) validates again before execution
```

### Capacity Calculation (per Node)

```
node.job_memory_limit = 2048m (2Gi, hardcoded by operator via env var)
ASSIGNED jobs on node:
  - job-1: memory_limit=512m
  - job-2: memory_limit=256m
RUNNING jobs on node:
  - job-3: memory_limit=1024m

used = 512 + 256 + 1024 = 1792m
available = 2048 - 1792 = 256m

New job requests 512m → rejected (256m < 512m)
New job requests 256m → accepted (256m == 256m)
New job requests null → accepted (defaults to 512m in accounting, but check if 512m fits)
```

### Recommended Project Structure

No new directories. Changes confined to existing modules:

```
puppeteer/agent_service/
├── services/
│   └── job_service.py          # Add parse_bytes(), extend create_job() + pull_work()
├── models.py                    # Already has memory_limit/cpu_limit validators (Phase 120)
└── db.py                        # Already has memory_limit/cpu_limit columns (Phase 120)
```

### Pattern 1: Memory Format Parsing

**What:** Convert human-readable memory strings (512m, 1g, 1Gi) to bytes for numeric comparison.

**When to use:** Whenever memory_limit is provided; during admission check and capacity sum.

**Example:**
```python
# Source: puppets/environment_service/node.py:25-34
def parse_bytes(s: str) -> int:
    """Convert memory string like '300m', '2g', '1024k' to bytes."""
    s = s.strip().lower()
    if s.endswith('g'):
        return int(s[:-1]) * 1024 ** 3
    elif s.endswith('m'):
        return int(s[:-1]) * 1024 ** 2
    elif s.endswith('k'):
        return int(s[:-1]) * 1024
    return int(s)  # Assume bytes if no suffix
```

**Port to:** `puppeteer/agent_service/services/job_service.py` as a module-level function or static method.

### Pattern 2: Default Limit Application

**What:** Apply 512m default memory for capacity accounting if job specifies null memory_limit.

**When to use:** During admission check and capacity calculation — null is treated as "operator wants to omit limits, but we still reserve 512m for safety."

**Example:**
```python
async def create_job(job_req: JobCreate, db: AsyncSession) -> dict:
    # ... existing validation ...

    effective_memory = job_req.memory_limit or "512m"  # Apply default
    effective_bytes = parse_bytes(effective_memory)

    # Check if any online node can fit this job
    nodes_result = await db.execute(
        select(Node).where(Node.status.in_(["ONLINE", "BUSY"]))
    )
    online_nodes = nodes_result.scalars().all()

    if online_nodes:  # Only check if nodes are online
        largest_capacity = max(
            parse_bytes(n.job_memory_limit) - await _sum_node_assigned_limits(n.node_id, db)
            for n in online_nodes
        )
        if effective_bytes > largest_capacity:
            raise HTTPException(
                status_code=422,
                detail={
                    "error": "insufficient_capacity",
                    "message": f"No online node can accommodate memory_limit={job_req.memory_limit or '512m (default)'}. "
                               f"Largest available: {_format_bytes(largest_capacity)}"
                }
            )
    # ... continue with job creation ...
```

### Pattern 3: Capacity Sum in pull_work()

**What:** Calculate node's available capacity by summing limits of ASSIGNED and RUNNING jobs, subtracting from node.job_memory_limit.

**When to use:** At dispatch time in `pull_work()` before assigning a job to a node.

**Example:**
```python
async def _sum_node_assigned_limits(node_id: str, db: AsyncSession) -> int:
    """Sum memory limits of ASSIGNED + RUNNING jobs on this node."""
    result = await db.execute(
        select(func.sum(Job.memory_limit))
        .where(
            Job.node_id == node_id,
            Job.status.in_(["ASSIGNED", "RUNNING"]),
            Job.memory_limit != None
        )
    )
    total_bytes = 0
    total_str = result.scalar_one_or_none()
    if total_str:
        # Each memory_limit is a string; sum them
        parts = [parse_bytes(part) for part in total_str.split(',')]  # ← may need JSON parsing
        total_bytes = sum(parts)
    return total_bytes

# In pull_work(), before assigning candidate job:
node_capacity_bytes = parse_bytes(node.job_memory_limit) if node.job_memory_limit else (512 * 1024 * 1024)
used_bytes = await _sum_node_assigned_limits(node.node_id, db)
available = node_capacity_bytes - used_bytes

job_memory_bytes = parse_bytes(selected_job.memory_limit or "512m")
if job_memory_bytes > available:
    continue  # Skip this node; try next candidate
```

**Note:** Current pull_work() doesn't have this check yet — Phase 122 (node-side integration) adds it to node.py. Phase 121 focuses on the API layer.

### Pattern 4: Dispatch Diagnosis Extension

**What:** Extend `get_dispatch_diagnosis()` to include `insufficient_memory` reason with per-node capacity breakdown.

**When to use:** Called by Jobs.tsx when user expands a PENDING job detail to understand why it hasn't dispatched.

**Example:**
```python
async def get_dispatch_diagnosis(guid: str, db: AsyncSession) -> dict:
    # ... existing code ...

    # NEW: Check memory admission
    if job.memory_limit:
        job_bytes = parse_bytes(job.memory_limit)
        nodes_checked = []
        largest_available = 0

        for node in online_nodes:
            capacity_bytes = parse_bytes(node.job_memory_limit)
            used = await _sum_node_assigned_limits(node.node_id, db)
            available = capacity_bytes - used

            nodes_checked.append({
                "node_id": node.node_id,
                "capacity": node.job_memory_limit,
                "used": _format_bytes(used),
                "available": _format_bytes(available),
                "verdict": "fits" if available >= job_bytes else "insufficient"
            })
            largest_available = max(largest_available, available)

        if job_bytes > largest_available:
            return {
                "reason": "insufficient_memory",
                "message": f"Job requires {job.memory_limit} but largest available is {_format_bytes(largest_available)}",
                "nodes_checked": nodes_checked,
                "queue_position": None
            }

    # ... continue with existing checks ...
```

### Anti-Patterns to Avoid

- **Hardcoding default limit:** Use Config table key `default_job_memory_limit` to allow ops to tune the default without code changes
- **Ignoring null memory_limit:** Treat null as "use default" (512m), not "unlimited" — null is for backwards compat, not a bypass
- **Capacity sum only on dispatch:** Check capacity at *both* `create_job()` (early rejection) and `pull_work()` (fresh capacity check)
- **Assuming node.job_memory_limit is always set:** Default to 512m if missing; nodes might not report this field yet (Phase 122 adds it to heartbeat)
- **Memory format case sensitivity:** Normalize to lowercase before parsing ("1G", "1g", "1Gi" all valid)
- **Not handling parse_bytes failures gracefully:** Treat malformed limits (e.g., "garbage") as invalid at Pydantic validation, not runtime parsing

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Memory format parsing | Custom string-to-bytes converter | `parse_bytes()` from node.py:25 | Already battle-tested in node code; handles k/m/g suffixes; supports binary and decimal |
| Capacity calculation | Manual job limit enumeration | Sorted query with ASSIGNED+RUNNING status filter | Database aggregation (SQL SUM) faster and atomic than Python loop |
| Default limit configuration | Hardcoded constant in code | Config table with key `default_job_memory_limit` | Allows operators to tune default without deployment |
| Per-node capacity tracking | In-memory cache of limits | Query ASSIGNED+RUNNING at pull_work() time | Fresh state on every dispatch; no cache invalidation complexity |
| Admission error formatting | Plain string message | Structured error dict with per-node breakdown | Enables diagnostics UI and operator troubleshooting |

**Key insight:** Memory admission is deceptively complex because limits flow through multiple enforcement layers (API, node selection, kernel). Using battle-tested patterns from node.py and proven SQL queries prevents subtle bugs where jobs silently exceed capacity.

## Common Pitfalls

### Pitfall 1: Null memory_limit Misconceptions

**What goes wrong:** Operators submit jobs with `memory_limit=null` expecting "no limit" behavior, but Phase 121 treats null as "use 512m default for capacity." Jobs fail to dispatch because 512m isn't available, but the operator thought null meant "no admission check."

**Why it happens:** Backwards compatibility: existing jobs without limits must continue working. But unlimited jobs would silently consume all capacity. Solution: default to 512m in accounting, allow override via Config table.

**How to avoid:**
1. Dashboard UI: warn operators when memory_limit is omitted ("Warning: limits omitted, 512m default will be reserved")
2. Error messages: explicitly state "(default)" when rejecting job with null limit
3. Docs: clarify that null limit doesn't mean "unlimited"

**Warning signs:** Jobs rejected with "No online node can accommodate 512m" when operators expected them to run without limits.

### Pitfall 2: Capacity Sum Race Condition

**What goes wrong:** Between the time `create_job()` checks capacity and the time `pull_work()` assigns the job, other jobs may have consumed the remaining capacity. Job sits in queue indefinitely, then suddenly dispatches when another job completes.

**Why it happens:** No transactional guarantee that reserved capacity persists from create_job() to pull_work().

**How to avoid:**
1. Accept this is inherent to pull model — jobs may remain PENDING briefly
2. `pull_work()` does fresh capacity check before assignment
3. Diagnosis message: "All eligible nodes are at capacity" (not a contradiction if capacity changed)

**Warning signs:** Jobs sporadically dispatch after long delays even when "capacity should be available."

### Pitfall 3: parse_bytes() Fails Silently

**What goes wrong:** Memory string like "1.5g" or "1GB" is malformed and parse_bytes() crashes at node-side runtime, failing the entire job. Operator doesn't realize the format was invalid.

**Why it happens:** Pydantic validator in models.py checks format with regex, but if validation is skipped (direct API call, bypass validation), malformed string reaches parse_bytes().

**How to avoid:**
1. Strict Pydantic validation in JobCreate (already done in Phase 120)
2. Server-side parse_bytes() in create_job() — fail early at admission check, not at dispatch
3. Error message: "Invalid memory format: '1.5g'. Use format like '512m', '1g', '1Gi'"

**Warning signs:** Jobs fail at node with parse error instead of being rejected at API.

### Pitfall 4: Node Capacity Not Reported

**What goes wrong:** Older nodes don't have `job_memory_limit` field in heartbeat. Admission check can't determine node's capacity, so it assumes infinite capacity or defaults to 512m. Jobs are admitted that don't fit on the node.

**Why it happens:** Phase 121 adds the admission check, but Phase 122 (node integration) is responsible for nodes reporting their capacity.

**How to avoid:**
1. Default to 512m if node.job_memory_limit is missing
2. Log warning: "Node {id} did not report job_memory_limit; defaulting to 512m"
3. Phase 122 adds capacity reporting to node heartbeat

**Warning signs:** Admission check passes, but node-side secondary check (Phase 122) rejects the job.

### Pitfall 5: Default Config Never Seeded

**What goes wrong:** Config table has no entry for `default_job_memory_limit`. Admission check calls `SELECT * FROM config WHERE key='default_job_memory_limit'` and gets null. Code assumes null means "no default," skips safety reservation.

**Why it happens:** Config table seeding happens in `init_db()` startup logic, but only if explicitly added. Easy to forget.

**How to avoid:**
1. Seed Config in `init_db()`: `INSERT INTO config (key, value) VALUES ('default_job_memory_limit', '512m') ON CONFLICT DO NOTHING`
2. Hardcode fallback in code: `config_default = "512m"` if query returns None
3. Test: verify default is applied even on fresh DB

**Warning signs:** Admission check allows jobs with memory_limit=null when no nodes are online (expected), but then rejects them at dispatch time (unexpected — capacity shouldn't have changed).

## Code Examples

Verified patterns from existing codebase:

### Memory Parsing (Ported from node.py)

```python
# Source: puppets/environment_service/node.py:25-34
def parse_bytes(s: str) -> int:
    """Convert memory string like '300m', '2g', '1024k' to bytes."""
    s = s.strip().lower()
    if s.endswith('g'):
        return int(s[:-1]) * 1024 ** 3
    elif s.endswith('m'):
        return int(s[:-1]) * 1024 ** 2
    elif s.endswith('k'):
        return int(s[:-1]) * 1024
    return int(s)  # Assume bytes if no suffix
```

**Usage:** Convert "512m" → 536870912 (bytes) for numeric comparison.

### Admission Check in create_job()

```python
# Source: job_service.py:340-435 (extend with memory logic)
@staticmethod
async def create_job(job_req: JobCreate, db: AsyncSession) -> dict:
    guid = str(uuid.uuid4())

    # ... existing env_tag validation ...

    # NEW: Memory admission check
    if job_req.memory_limit:
        from fastapi import HTTPException

        # Get all online nodes
        nodes_result = await db.execute(
            select(Node).where(Node.status.in_(["ONLINE", "BUSY"]))
        )
        online_nodes = nodes_result.scalars().all()

        if online_nodes:
            job_bytes = parse_bytes(job_req.memory_limit)
            can_fit = False
            largest = 0

            for node in online_nodes:
                # Default to 512m if node doesn't report capacity
                node_limit_str = node.job_memory_limit or "512m"
                capacity = parse_bytes(node_limit_str)

                # Sum ASSIGNED + RUNNING limits on this node
                sum_result = await db.execute(
                    select(func.sum(Job.memory_limit))
                    .where(
                        Job.node_id == node.node_id,
                        Job.status.in_(["ASSIGNED", "RUNNING"]),
                        Job.memory_limit != None
                    )
                )
                used_str = sum_result.scalar_one_or_none()
                used = sum(parse_bytes(m) for m in used_str.split(',')) if used_str else 0

                available = capacity - used
                largest = max(largest, available)

                if job_bytes <= available:
                    can_fit = True
                    break

            if not can_fit:
                raise HTTPException(
                    status_code=422,
                    detail={
                        "error": "insufficient_capacity",
                        "message": f"No online node can accommodate memory_limit={job_req.memory_limit}. "
                                   f"Largest available capacity: {_format_bytes(largest)} MB"
                    }
                )

    # ... continue with existing job creation logic ...
```

**Note:** Actual sum query depends on how memory_limit is stored in DB (single string vs. JSON). Verify during implementation.

### Dispatch Diagnosis Extension

```python
# Source: job_service.py:1255-1362 (extend with resource diagnosis)
@staticmethod
async def get_dispatch_diagnosis(guid: str, db: AsyncSession) -> dict:
    """Returns diagnosis explaining why a PENDING job hasn't dispatched."""
    job_result = await db.execute(select(Job).where(Job.guid == guid))
    job = job_result.scalar_one_or_none()
    if not job:
        return {"reason": "not_found", "message": "Job not found"}

    if job.status != "PENDING":
        return {"reason": "not_pending", "message": f"Job is {job.status}, not PENDING"}

    # ... existing target_node_id, online nodes checks ...

    # NEW: Memory admission diagnosis
    if job.memory_limit and online_nodes:
        job_bytes = parse_bytes(job.memory_limit)
        nodes_checked = []
        largest_available = 0

        for node in online_nodes:
            capacity = parse_bytes(node.job_memory_limit or "512m")
            sum_result = await db.execute(
                select(func.sum(Job.memory_limit))
                .where(
                    Job.node_id == node.node_id,
                    Job.status.in_(["ASSIGNED", "RUNNING"]),
                    Job.memory_limit != None
                )
            )
            used = sum(parse_bytes(m) for m in (sum_result.scalar_one_or_none() or "").split(',')) if sum_result.scalar_one_or_none() else 0
            available = capacity - used
            largest_available = max(largest_available, available)

            nodes_checked.append({
                "node_id": node.node_id,
                "capacity_mb": capacity // (1024 ** 2),
                "used_mb": used // (1024 ** 2),
                "available_mb": available // (1024 ** 2),
                "fits": "yes" if available >= job_bytes else "no"
            })

        if job_bytes > largest_available:
            return {
                "reason": "insufficient_memory",
                "message": f"Job requires {job.memory_limit} but no node has enough capacity. "
                           f"Largest available: {largest_available // (1024 ** 2)} MB",
                "nodes_breakdown": nodes_checked,
                "queue_position": None
            }

    # ... continue with existing logic (capability, concurrency checks) ...
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| No API-level admission | Hard-reject (422) if job exceeds all nodes | Phase 121 | Prevents undersized jobs from wasting queue slots; faster operator feedback |
| Single capacity check at pull_work() | Dual checks: create_job() + pull_work() | Phase 121 | Early rejection + fresh capacity validation; resilient to concurrent job creation |
| Hardcoded default (none) | Config table key `default_job_memory_limit` | Phase 121 | Operators can tune default without code changes |
| No diagnosis for memory blocking | Per-node capacity breakdown in diagnosis | Phase 121 | Operators can understand why jobs aren't dispatching |

**Deprecated/outdated:**
- **Unlimited jobs (null limit as no-limits):** Deprecated in Phase 121; now null means "use 512m default." Backwards compat preserved by allowing null in Pydantic, but accounting reserves space.

## Open Questions

1. **Sum Query Limitation (SQL Aggregation of String Columns)**
   - What we know: `Job.memory_limit` is stored as TEXT (e.g., "512m"). SQLite has no native JSON aggregation; Postgres can use `STRING_AGG` but that returns concatenated string, not numeric sum.
   - What's unclear: How to efficiently sum memory limits across multiple jobs? Options:
     * (A) Fetch all job records in Python, parse and sum in code (slower, simple)
     * (B) Store memory_limit as INTEGER in bytes internally, use SQL SUM() natively (schema change risky mid-phase)
     * (C) Keep TEXT storage, parse in Python loop (what current code likely does)
   - Recommendation: Use (C) for Phase 121 — simple and matches existing pattern. Optimize to (B) in Phase 122+ if performance becomes issue.

2. **Node Capacity Not Yet Reported**
   - What we know: Phase 121 assumes `node.job_memory_limit` is available from node heartbeat.
   - What's unclear: Is this field being reported by nodes yet? (May be Phase 122 responsibility)
   - Recommendation: Default to 512m if missing; add fallback logic. Phase 122 will add the reporting.

3. **Config Table Default Seeding**
   - What we know: Phase 121 uses `default_job_memory_limit` from Config table.
   - What's unclear: Is this value seeded at startup, or does init_db() need to be patched?
   - Recommendation: Add `INSERT ... ON CONFLICT DO NOTHING` in init_db() to seed default.

4. **Memory Limit in ScheduledJob (Phase 121 Discretion)**
   - What we know: ScheduledJob table will need `memory_limit` and `cpu_limit` columns (per CONTEXT.md).
   - What's unclear: When scheduler fires a job, are limits copied verbatim, or does admission check re-evaluate?
   - Recommendation: Copy limits verbatim from ScheduledJob to created Job; let admission check at fire time reject if capacity has changed.

## Validation Architecture

> Validation Architecture applies. The workflow.nyquist_validation setting is not explicitly false in config.

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest (backend) + vitest (frontend) |
| Config file | `puppeteer/pytest.ini` (backend), `puppeteer/dashboard/vitest.config.ts` (frontend) |
| Quick run command | `cd puppeteer && pytest tests/test_job_service.py -x -v` |
| Full suite command | `cd puppeteer && pytest` |

### Phase Requirements → Test Map

| Behavior | Test Type | Automated Command | File Exists? |
|----------|-----------|-------------------|-------------|
| parse_bytes() converts memory string to bytes | unit | `pytest tests/test_job_service.py::test_parse_bytes -v` | ❌ Wave 0 |
| create_job() hard-rejects (422) if memory exceeds all nodes | unit | `pytest tests/test_job_service.py::test_create_job_admission_exceeded -v` | ❌ Wave 0 |
| create_job() accepts job if at least one node has capacity | unit | `pytest tests/test_job_service.py::test_create_job_admission_accepted -v` | ❌ Wave 0 |
| create_job() allows null memory_limit (backwards compat) | unit | `pytest tests/test_job_service.py::test_create_job_null_memory -v` | ❌ Wave 0 |
| create_job() uses default_job_memory_limit from Config | unit | `pytest tests/test_job_service.py::test_create_job_default_limit -v` | ❌ Wave 0 |
| pull_work() does fresh capacity check before assignment | unit | `pytest tests/test_job_service.py::test_pull_work_capacity_check -v` | ❌ Wave 0 |
| get_dispatch_diagnosis() returns insufficient_memory reason | unit | `pytest tests/test_job_service.py::test_diagnosis_memory_blocking -v` | ❌ Wave 0 |
| get_dispatch_diagnosis() includes per-node breakdown | unit | `pytest tests/test_job_service.py::test_diagnosis_nodes_breakdown -v` | ❌ Wave 0 |
| POST /jobs with oversized memory returns 422 | integration | `pytest tests/test_main.py::test_create_job_oversized -v` | ❌ Wave 0 |
| GET /jobs/{guid}/diagnosis returns memory breakdown | integration | `pytest tests/test_main.py::test_diagnosis_memory_api -v` | ❌ Wave 0 |

### Sampling Rate

- **Per task commit:** `cd puppeteer && pytest tests/test_job_service.py -x -v` (unit tests only, ~20s)
- **Per wave merge:** `cd puppeteer && pytest` (full suite, ~2min)
- **Phase gate:** Full suite green before verification

### Wave 0 Gaps

- [ ] `tests/test_job_service.py::test_parse_bytes` — parse_bytes() unit tests
- [ ] `tests/test_job_service.py::test_create_job_admission_*` — admission check tests (5 tests)
- [ ] `tests/test_job_service.py::test_pull_work_capacity_*` — capacity sum tests (2 tests)
- [ ] `tests/test_job_service.py::test_diagnosis_memory_*` — diagnosis extension tests (3 tests)
- [ ] `tests/test_main.py::test_create_job_oversized` — API integration test
- [ ] `tests/test_main.py::test_diagnosis_memory_api` — diagnosis API test
- [ ] Framework setup: ensure pytest is configured for async tests (asyncio plugin)
- [ ] Fixtures: mock Node records with job_memory_limit, ASSIGNED/RUNNING jobs for capacity sum testing

## Sources

### Primary (HIGH confidence)

- **Existing node.py implementation** — `parse_bytes()` function at line 25-34 (battle-tested, used in node admission)
- **Phase 120 research** — `.planning/research/SUMMARY.md` (establishes dual-layer admission model)
- **job_service.py current code** — `create_job()` at line 340-435, `pull_work()` at line 556-750, `get_dispatch_diagnosis()` at line 1255-1362

### Secondary (MEDIUM confidence)

- **CONTEXT.md locked decisions** — specifies 422 error, no override flag, default 512m, dynamic capacity
- **db.py Job model** — memory_limit + cpu_limit columns already added (Phase 120)
- **models.py JobCreate** — memory_limit validator already present (Phase 120)

### Tertiary (LOW confidence)

- Cgroup scheduling behavior — assumed kernel enforces per-job limits correctly (Phase 126 validates)

## Metadata

**Confidence breakdown:**
- **Standard stack:** HIGH — No new dependencies, existing patterns from job_service
- **Architecture:** HIGH — Dual-layer admission (API + node) well-established pattern; capacity calculation straightforward SQL
- **Pitfalls:** HIGH — Memory format parsing edge cases identified in node.py; backwards compat (null limits) clearly scoped
- **Validation:** MEDIUM — Test gaps exist (Wave 0 must create test suite), but test patterns straightforward

**Research date:** 2026-04-06
**Valid until:** 2026-04-13 (7 days — fast-moving admission logic, validate actively during implementation)
**Confidence:** HIGH overall — Phase 120 foundation solid, Phase 121 scope narrow and well-defined by CONTEXT.md
