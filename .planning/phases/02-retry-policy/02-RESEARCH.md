# Phase 2: Retry Policy - Research

**Researched:** 2026-03-05
**Domain:** Job retry lifecycle, exponential backoff, zombie detection, SQLAlchemy async patterns, React status UI
**Confidence:** HIGH

## Summary

Phase 2 wires retry logic into the existing job lifecycle. The code is well-understood — all integration points are identified in the CONTEXT.md and verified against current source. The primary technical work is: (1) extend DB models with retry columns, (2) modify `report_result()` to classify failures and apply backoff, (3) inject zombie reaper at the top of `pull_work()`, (4) add cron overlap guard in `execute_scheduled_job()`, (5) surface retry state in the Jobs dashboard.

The design is intentionally server-side-only for backoff tracking. Nodes send a `retriable` flag but don't implement retry logic themselves — the server controls all retry scheduling. This is correct: nodes are stateless workers; retry policy is an orchestration concern.

**Primary recommendation:** Implement retry logic in `job_service.py` with pure datetime arithmetic for backoff (`retry_after = utcnow() + timedelta(seconds=delay)`). No additional libraries needed. All patterns fit cleanly into the existing SQLAlchemy async session model.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Retry scope:**
- `max_retries` lives on both `ScheduledJob` definitions AND individual `Job` rows — all jobs carry a retry policy regardless of origin
- Retries use the same GUID: the original Job row is reset to PENDING with `retry_count` incremented; each attempt writes its own `ExecutionRecord`
- New columns on `Job`: `max_retries` (int, default 0), `retry_count` (int, default 0), `retry_after` (DateTime nullable), `backoff_multiplier` (float, default 2.0), `timeout_minutes` (int nullable)
- New columns on `ScheduledJob`: `max_retries` (int, default 0), `backoff_multiplier` (float, default 2.0), `timeout_minutes` (int nullable)
- When all retries exhausted → job moves to `DEAD_LETTER` terminal status (distinct from `FAILED`)

**Failure classification:**
- Node explicitly flags retriability in `ResultReport`: add `retriable: Optional[bool]` field
- Default (field absent) → non-retriable — existing nodes that don't send the flag will not retry
- `SECURITY_REJECTED` → always non-retriable
- Manual cancellation → always terminal; no retries
- Cron overlap prevention: check if most recent Job from that `ScheduledJob` definition is still PENDING, ASSIGNED, or RETRYING — if so skip the new instance and log to audit

**Zombie timeout:**
- Global Config table default (`zombie_timeout_minutes`, default 30 min) + per-job override via `Job.timeout_minutes` (null = use global)
- Zombie detection runs inline at `pull_work()`: scan ASSIGNED jobs on the polling node past their timeout before selecting new work
- Zombie reclaim counts as a retry attempt: `retry_count` incremented; if retries exhausted → DEAD_LETTER; if retries remain → reset to PENDING with backoff applied
- Zombie reclaim writes an ExecutionRecord with status `ZOMBIE_REAPED` and no output log

**Dashboard retry UX:**
- Jobs waiting in backoff show status `RETRYING` — distinct from `PENDING` and `FAILED`
- Attempt column in the job table: shows `2/3` for current attempt out of max. Blank for `max_retries = 0`
- Job detail panel shows: `retry_after` countdown, full attempt history linked to ExecutionRecords
- `DEAD_LETTER` gets its own filter chip in the status bar (dark red / maroon) — separate from FAILED
- Retry button on DEAD_LETTER and FAILED jobs: operator can manually re-queue (resets `retry_count` to 0, clears `retry_after`, sets status to PENDING). Requires `jobs:write` permission.

### Claude's Discretion
- Exact backoff formula (base formula: `backoff_multiplier ^ retry_count` seconds, with jitter ±20%)
- Initial backoff delay for retry_count = 1 (suggest: 30s)
- Cap on maximum backoff interval (suggest: 1 hour)
- Exact color values for RETRYING and DEAD_LETTER status badges
- Whether RETRYING status is included in the server-side status filter (it should be)

### Deferred Ideas (OUT OF SCOPE)
- Notifications when a job hits DEAD_LETTER (NOTF-01 requirement — Phase 2 backlog / v2)
- Per-exit-code retry classification as an alternative to the `retriable` flag
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| RETR-01 | Job definition can specify a maximum retry count (0 = no retries) | `max_retries` column on `Job` and `ScheduledJob`; inherited at job creation time; `retry_count` column tracks current attempt |
| RETR-02 | Retries use exponential backoff with jitter (not immediate re-queue) | `retry_after` DateTime column; backoff computed as `backoff_multiplier ^ retry_count` seconds with ±20% jitter; `pull_work()` skips RETRYING jobs where `retry_after > utcnow()` |
| RETR-03 | System classifies failures as transient (retry) vs permanent (dead letter) | `retriable: Optional[bool]` field on `ResultReport`; default absent=non-retriable; `SECURITY_REJECTED` always non-retriable; `DEAD_LETTER` terminal status |
| RETR-04 | Zombie jobs (assigned but never reported back) are reaped and rescheduled | Zombie scan runs inline at top of `pull_work()`; checks ASSIGNED jobs on polling node with timeout exceeded; reclaim counts as retry attempt |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| SQLAlchemy async | Already in use | ORM update/query for retry columns | Already the project ORM — no new dependencies |
| Python `datetime` / `timedelta` | stdlib | Backoff delay calculation, zombie timeout comparison | No external library needed for arithmetic on UTC datetimes |
| Python `random` | stdlib | ±20% jitter on backoff delay | Stdlib, no overhead |
| APScheduler | Already in use | Cron scheduling that fires `execute_scheduled_job` | Already the project scheduler |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| Pydantic Optional fields | Already in use | `retriable: Optional[bool] = None` on `ResultReport` | Backward-compatible extension — existing nodes omitting the field get non-retriable default |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Inline datetime arithmetic for backoff | Celery / Redis queue | Celery is a full task queue — way more infrastructure than needed; datetime in DB column is sufficient for this polling model |
| Config table for zombie_timeout_minutes | Hardcoded constant | Config table already exists and is the established pattern |
| Same GUID on retry | New GUID per retry | New GUID would break ExecutionRecord history linkage and make the dashboard confusing |

**Installation:** No new packages required. All needed libraries are already present.

## Architecture Patterns

### Recommended Project Structure

No new files needed. All changes are within existing files:

```
puppeteer/
├── agent_service/
│   ├── db.py                    # Add retry columns to Job, ScheduledJob
│   ├── models.py                # Add retriable to ResultReport, retry fields to JobCreate/WorkResponse
│   ├── services/
│   │   ├── job_service.py       # report_result retry logic + zombie reaper in pull_work
│   │   └── scheduler_service.py # execute_scheduled_job cron overlap guard
│   └── main.py                  # POST /jobs/{guid}/retry endpoint
├── dashboard/src/views/
│   └── Jobs.tsx                 # RETRYING/DEAD_LETTER status chips, attempt column, retry button
└── migration_v15.sql            # ALTER TABLE for existing deployments
```

### Pattern 1: Retry Decision in report_result()

**What:** After writing the ExecutionRecord, check `retriable` flag and retry policy to decide whether to reset to PENDING (with backoff) or move to DEAD_LETTER.

**When to use:** Every time a job reports failure (not success, not security_rejected with manual-cancel guard).

```python
# In job_service.py — report_result(), after writing ExecutionRecord
# Source: existing project pattern, extended per CONTEXT.md decisions

if not report.success and not report.security_rejected:
    # Determine if retriable
    is_retriable = report.retriable is True  # None (absent) = non-retriable per decision

    if is_retriable and job.max_retries > 0 and job.retry_count < job.max_retries:
        job.retry_count += 1
        # Backoff: multiplier^retry_count seconds, capped at 3600s, ±20% jitter
        import random
        base_delay = (job.backoff_multiplier ** job.retry_count)
        base_delay = min(base_delay, 3600)
        jitter = base_delay * 0.2
        delay = base_delay + random.uniform(-jitter, jitter)
        job.retry_after = datetime.utcnow() + timedelta(seconds=max(delay, 1))
        job.status = "RETRYING"
        job.node_id = None       # Release from current node
        job.completed_at = None  # Reset for next attempt
    else:
        # Exhausted or non-retriable
        if is_retriable and job.max_retries > 0:
            job.status = "DEAD_LETTER"
        else:
            job.status = "FAILED"  # Non-retriable: stays FAILED (still manually re-queueable)
```

### Pattern 2: Backoff-Aware Job Selection in pull_work()

**What:** When selecting PENDING jobs for assignment, the query must include RETRYING jobs whose `retry_after` has passed — and must exclude RETRYING jobs still waiting.

**When to use:** Inside `pull_work()` in the job selection query.

```python
# In job_service.py — pull_work(), step 3 (job selection)
# Change status filter from just 'PENDING' to include eligible RETRYING jobs

from sqlalchemy import or_

result = await db.execute(
    select(Job).where(
        or_(
            Job.status == 'PENDING',
            and_(
                Job.status == 'RETRYING',
                or_(Job.retry_after == None, Job.retry_after <= datetime.utcnow())
            )
        )
    ).where(
        (Job.node_id == None) | (Job.node_id == node_id)
    ).order_by(Job.created_at.asc()).limit(50)
)
```

### Pattern 3: Zombie Reaper at Top of pull_work()

**What:** Before selecting a new job, scan all ASSIGNED jobs on the polling node that exceed their timeout. Reclaim each as a retry attempt.

**When to use:** Beginning of `pull_work()`, before the concurrency count check.

```python
# In job_service.py — pull_work(), BEFORE step 2 (concurrency check)
# Fetch global zombie timeout from Config table

async def _get_zombie_timeout(db: AsyncSession) -> int:
    from ..db import Config
    result = await db.execute(select(Config).where(Config.key == 'zombie_timeout_minutes'))
    cfg = result.scalar_one_or_none()
    return int(cfg.value) if cfg else 30  # default 30 min

# In pull_work():
zombie_timeout_minutes = await _get_zombie_timeout(db)
cutoff = datetime.utcnow() - timedelta(minutes=zombie_timeout_minutes)

zombie_result = await db.execute(
    select(Job).where(
        Job.status == 'ASSIGNED',
        Job.node_id == node_id,
        Job.started_at < cutoff,
        # Per-job override: if timeout_minutes set, use it
    )
)
zombie_jobs = zombie_result.scalars().all()

for zombie in zombie_jobs:
    # Determine effective timeout for this job
    effective_timeout = zombie.timeout_minutes or zombie_timeout_minutes
    job_cutoff = datetime.utcnow() - timedelta(minutes=effective_timeout)
    if zombie.started_at >= job_cutoff:
        continue  # Not yet timed out per per-job override

    zombie.retry_count += 1
    # Write ZOMBIE_REAPED execution record (no output)
    db.add(ExecutionRecord(
        job_guid=zombie.guid,
        node_id=zombie.node_id,
        status="ZOMBIE_REAPED",
        started_at=zombie.started_at,
        completed_at=datetime.utcnow(),
    ))

    if zombie.max_retries > 0 and zombie.retry_count <= zombie.max_retries:
        # Retry with backoff
        import random
        base_delay = (zombie.backoff_multiplier ** zombie.retry_count)
        base_delay = min(base_delay, 3600)
        jitter = base_delay * 0.2
        delay = base_delay + random.uniform(-jitter, jitter)
        zombie.retry_after = datetime.utcnow() + timedelta(seconds=max(delay, 1))
        zombie.status = "RETRYING"
        zombie.node_id = None
    else:
        zombie.status = "DEAD_LETTER" if zombie.max_retries > 0 else "FAILED"
        zombie.completed_at = datetime.utcnow()

await db.flush()  # Persist zombie changes before proceeding to job selection
```

### Pattern 4: Cron Overlap Guard in execute_scheduled_job()

**What:** Before creating a new Job from a cron trigger, check if the most recent Job from this `ScheduledJob` is still active. If so, skip and audit-log the skip.

**When to use:** At the start of `execute_scheduled_job()`, after fetching the ScheduledJob.

```python
# In scheduler_service.py — execute_scheduled_job(), after fetching s_job

# Check for active (non-terminal) job from this definition
from sqlalchemy import desc as _desc
recent_result = await session.execute(
    select(Job)
    .where(Job.scheduled_job_id == s_job.id)
    .where(Job.status.in_(["PENDING", "ASSIGNED", "RETRYING"]))
    .order_by(_desc(Job.created_at))
    .limit(1)
)
active_job = recent_result.scalar_one_or_none()

if active_job:
    logger.warning(
        f"Skipping cron fire for '{s_job.name}' — previous job {active_job.guid} "
        f"still active (status: {active_job.status})"
    )
    # Audit log the skip
    from ..db import AuditLog
    session.add(AuditLog(
        username="scheduler",
        action="job:cron_skip",
        resource_id=s_job.id,
        detail=f"Skipped fire; job {active_job.guid} still {active_job.status}",
    ))
    await session.commit()
    return
```

### Pattern 5: Manual Retry Endpoint

**What:** `POST /jobs/{guid}/retry` resets a FAILED or DEAD_LETTER job back to PENDING. Requires `jobs:write`.

```python
# In main.py — new route, alongside the cancel route

@app.post("/jobs/{guid}/retry")
async def retry_job(
    guid: str,
    current_user: User = Depends(require_permission("jobs:write")),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(Job).where(Job.guid == guid))
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if job.status not in ("FAILED", "DEAD_LETTER"):
        raise HTTPException(status_code=409, detail=f"Cannot retry job with status {job.status}")
    job.status = "PENDING"
    job.retry_count = 0
    job.retry_after = None
    job.node_id = None
    job.completed_at = None
    audit(db, current_user, "job:retry", guid)
    await db.commit()
    await ws_manager.broadcast("job:updated", {"guid": guid, "status": "PENDING"})
    return {"status": "PENDING", "guid": guid}
```

### Pattern 6: Frontend Status Extensions

**What:** RETRYING (amber) and DEAD_LETTER (dark red/maroon) must be added to `getStatusVariant()`, `StatusIcon`, the filter `<Select>`, and the stats counts. An "Attempt" column is added to the table.

```typescript
// In Jobs.tsx — extend getStatusVariant()
case 'retrying': return 'warning';    // amber — new shadcn variant or custom class
case 'dead_letter': return 'deadletter';  // dark red/maroon — custom

// In StatusIcon:
case 'retrying': return <RefreshCw className="h-4 w-4 text-amber-500 animate-spin" />;
case 'dead_letter': return <Skull className="h-4 w-4 text-rose-800" />;

// In the status Select filter — add after security_rejected:
<SelectItem value="retrying">Retrying</SelectItem>
<SelectItem value="dead_letter">Dead Letter</SelectItem>
```

For the Attempt column, `Job` interface needs `retry_count?: number` and `max_retries?: number`. Display as `{retry_count}/{max_retries}` when `max_retries > 0`, blank otherwise.

For the `retry_after` countdown in the Job detail panel: a simple `useEffect` tick every second to compute "Next attempt in Xm Ys" from `retry_after` ISO timestamp.

### Anti-Patterns to Avoid

- **Polling RETRYING from a background thread:** The design is pull-based — nodes check `retry_after` at poll time, not a background scheduler. Don't add an APScheduler job to re-queue retrying jobs.
- **Storing retry config in JSON payload:** Retry columns are first-class scalar DB columns, not embedded in the payload JSON blob.
- **Creating a new GUID per retry attempt:** Same GUID links all ExecutionRecords together. New GUID = broken history.
- **Querying Config table inside the job selection loop:** Fetch zombie timeout once per `pull_work()` call, not once per candidate job.
- **Importing `random` at call site:** Import at module top in `job_service.py`.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Backoff delay calculation | Custom scheduler / task queue | `datetime.utcnow() + timedelta(seconds=...)` stored in `retry_after` column | The pull model means nodes check eligibility at poll time; no push mechanism needed |
| Jitter | Statistical distribution library | `random.uniform(-0.2*delay, 0.2*delay)` | ±20% uniform jitter is standard practice and trivially implemented |
| Zombie detection background poller | APScheduler job firing every N minutes | Inline check at top of `pull_work()` | The design decision avoids a background poller to prevent TOCTOU races and reduce complexity |
| Config lookup caching | Redis / memcached | Re-fetch from Config table on each `pull_work()` call | Poll frequency is a few times per second at most; a single SELECT by PK is negligible |

**Key insight:** The existing pull model eliminates the need for any "wake up and re-queue" mechanism. A job in RETRYING status with `retry_after` in the past is indistinguishable from PENDING at assignment time — it just needs to be included in the eligibility query.

## Common Pitfalls

### Pitfall 1: RETRYING Jobs Not Eligible for Assignment
**What goes wrong:** `pull_work()` query filters only `status == 'PENDING'`. RETRYING jobs with elapsed `retry_after` are never picked up.
**Why it happens:** Easy to forget to extend the status filter when adding the RETRYING status.
**How to avoid:** The job selection WHERE clause must explicitly include `OR (status='RETRYING' AND (retry_after IS NULL OR retry_after <= NOW()))`.
**Warning signs:** Jobs stuck in RETRYING forever; no progress despite elapsed backoff time.

### Pitfall 2: Zombie Reaper Uses Global Timeout for All Jobs
**What goes wrong:** All zombies are reaped with `zombie_timeout_minutes` even when `Job.timeout_minutes` is set to a different value.
**Why it happens:** Per-job override stored as nullable int — easy to forget the None check.
**How to avoid:** Effective timeout = `zombie.timeout_minutes or global_timeout`. Apply per-job cutoff in the reaper loop.
**Warning signs:** Fast jobs (short `timeout_minutes`) not reaped promptly; slow jobs reaped too early.

### Pitfall 3: Retry Count Incremented on DEAD_LETTER
**What goes wrong:** `retry_count` is incremented one more time when transitioning to DEAD_LETTER, making the final count off by one.
**Why it happens:** Zombie reaper or report_result increments before checking if retries are exhausted.
**How to avoid:** Check `retry_count < max_retries` BEFORE incrementing. The increment should be the first step; exhaustion check compares `retry_count <= max_retries` after increment.
**Warning signs:** A job with `max_retries=3` shows `4/3` in the UI.

### Pitfall 4: Migration Breaks SQLite Dev Environment
**What goes wrong:** `ALTER TABLE jobs ADD COLUMN IF NOT EXISTS` is Postgres syntax. SQLite does not support `IF NOT EXISTS` on `ALTER TABLE ADD COLUMN`.
**Why it happens:** Noted in STATE.md blockers — SQLite ALTER TABLE limitation.
**How to avoid:** Dev workflow = delete `jobs.db` and let `create_all` rebuild. Document this. Migration SQL is Postgres-only. Alternatively, catch the OperationalError in a setup script.
**Warning signs:** Errors on `ALTER TABLE` when testing locally against SQLite.

### Pitfall 5: Cron Overlap Query Hits Wrong Terminal Statuses
**What goes wrong:** The overlap guard checks for `status IN ('PENDING', 'ASSIGNED', 'RETRYING')` but accidentally includes `FAILED` or `DEAD_LETTER`, causing cron jobs to be silently skipped forever once a job has failed.
**Why it happens:** Terminal vs active statuses can be confused.
**How to avoid:** Active statuses are exactly: `PENDING`, `ASSIGNED`, `RETRYING`. Terminal statuses are: `COMPLETED`, `FAILED`, `CANCELLED`, `SECURITY_REJECTED`, `DEAD_LETTER`. Overlap guard must only check active statuses.
**Warning signs:** Cron-scheduled jobs stop firing entirely after one failure.

### Pitfall 6: APScheduler misfire_grace_time on High-Frequency Crons
**What goes wrong:** APScheduler default `misfire_grace_time` is 1 second. Under load (server startup, DB slowness), cron fires can be skipped silently.
**Why it happens:** Documented in STATE.md blockers for Phase 2.
**How to avoid:** Set `misfire_grace_time` explicitly when adding jobs in `sync_scheduler()`. A value of 60 seconds is reasonable for most job definitions. Log misfires.
**Warning signs:** Cron jobs not firing on schedule under load; no audit events.

### Pitfall 7: Manual Retry Clears retry_count but Not retry_after
**What goes wrong:** Operator clicks Retry. Job goes back to PENDING but `retry_after` is still set, causing it to remain unassignable.
**Why it happens:** `retry_after` must be explicitly cleared (set to None) on manual retry.
**How to avoid:** The `POST /jobs/{guid}/retry` handler must set `retry_after = None` as part of the reset.
**Warning signs:** Manually retried jobs stuck in PENDING forever.

## Code Examples

Verified patterns from existing project source:

### DB Column Addition (SQLAlchemy mapped_column pattern)
```python
# Source: puppeteer/agent_service/db.py — existing pattern
# Add to Job class:
max_retries: Mapped[int] = mapped_column(Integer, default=0)
retry_count: Mapped[int] = mapped_column(Integer, default=0)
retry_after: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
backoff_multiplier: Mapped[float] = mapped_column(Float, default=2.0)
timeout_minutes: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

# Add to ScheduledJob class:
max_retries: Mapped[int] = mapped_column(Integer, default=0)
backoff_multiplier: Mapped[float] = mapped_column(Float, default=2.0)
timeout_minutes: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
```

Note: `default=0` and `default=2.0` use Python-level defaults only (no `server_default`). This matches the established pattern from `01-01` decision: `truncated uses Python-level default=False only — no server_default (SQLite compat)`.

### Migration SQL Pattern (from migration_v14.sql)
```sql
-- migration_v15.sql
-- Phase 2: Retry Policy — new columns on jobs and scheduled_jobs
-- Safe to run on existing Postgres deployments (IF NOT EXISTS guards)
-- Fresh installs: handled automatically by SQLAlchemy create_all at startup

ALTER TABLE jobs ADD COLUMN IF NOT EXISTS max_retries INTEGER DEFAULT 0;
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS retry_count INTEGER DEFAULT 0;
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS retry_after TIMESTAMP;
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS backoff_multiplier FLOAT DEFAULT 2.0;
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS timeout_minutes INTEGER;

ALTER TABLE scheduled_jobs ADD COLUMN IF NOT EXISTS max_retries INTEGER DEFAULT 0;
ALTER TABLE scheduled_jobs ADD COLUMN IF NOT EXISTS backoff_multiplier FLOAT DEFAULT 2.0;
ALTER TABLE scheduled_jobs ADD COLUMN IF NOT EXISTS timeout_minutes INTEGER;

-- Seed global zombie timeout default if not present
INSERT INTO config (key, value)
VALUES ('zombie_timeout_minutes', '30')
ON CONFLICT (key) DO NOTHING;
```

### ResultReport Extension (Pydantic backward-compatible pattern)
```python
# Source: puppeteer/agent_service/models.py — extend ResultReport
# Per 01-01 decision: "ResultReport extended with Optional fields — existing nodes omitting continue to work"
class ResultReport(BaseModel):
    result: Optional[Dict] = None
    error_details: Optional[Dict] = None
    success: bool
    output_log: Optional[List[Dict[str, str]]] = None
    exit_code: Optional[int] = None
    security_rejected: bool = False
    retriable: Optional[bool] = None  # None = non-retriable (default); True = retry eligible
```

### Job Propagation from ScheduledJob at Spawn
```python
# Source: puppeteer/agent_service/services/scheduler_service.py — execute_scheduled_job()
# Extend Job creation to inherit retry policy from ScheduledJob
new_job = Job(
    guid=execution_guid,
    task_type="python_script",
    payload=payload_json,
    status="PENDING",
    node_id=s_job.target_node_id,
    target_tags=s_job.target_tags,
    scheduled_job_id=s_job.id,
    max_retries=s_job.max_retries,                   # inherited
    backoff_multiplier=s_job.backoff_multiplier,      # inherited
    timeout_minutes=s_job.timeout_minutes,            # inherited
    # retry_count starts at 0 (default)
    # retry_after starts as None (default)
)
```

### Node.py report_result — Adding retriable parameter
```python
# Source: puppets/environment_service/node.py — report_result()
# No node-side retry logic — just add retriable to the payload when success=False
# Nodes that fail due to a transient error (e.g. runtime crash) pass retriable=True
async def report_result(self, guid: str, success: bool, result: Dict,
                        output_log=None, exit_code=None, security_rejected=False,
                        retriable: bool = None):
    # ...
    json={
        "success": success,
        "result": result,
        "output_log": output_log,
        "exit_code": exit_code,
        "security_rejected": security_rejected,
        "retriable": retriable,  # None by default = non-retriable
    },
```

### JobDefinitionCreate and JobDefinitionUpdate — retry fields
```python
# Source: puppeteer/agent_service/models.py
class JobDefinitionCreate(BaseModel):
    name: str
    script_content: str
    signature: str
    signature_id: str
    schedule_cron: Optional[str] = None
    target_node_id: Optional[str] = None
    target_tags: Optional[List[str]] = None
    capability_requirements: Optional[Dict[str, str]] = None
    max_retries: int = 0                        # new
    backoff_multiplier: float = 2.0             # new
    timeout_minutes: Optional[int] = None       # new

class JobDefinitionUpdate(BaseModel):
    # ... existing fields ...
    max_retries: Optional[int] = None           # new
    backoff_multiplier: Optional[float] = None  # new
    timeout_minutes: Optional[int] = None       # new
```

### JobDefinitionResponse — retry fields
```python
class JobDefinitionResponse(BaseModel):
    # ... existing fields ...
    max_retries: int = 0
    backoff_multiplier: float = 2.0
    timeout_minutes: Optional[int] = None
```

### get_job_stats() — extend status set
```python
# Source: puppeteer/agent_service/services/job_service.py — get_job_stats()
for status in ["PENDING", "ASSIGNED", "COMPLETED", "FAILED", "SECURITY_REJECTED", "RETRYING", "DEAD_LETTER"]:
    if status not in counts:
        counts[status] = 0

# Update success rate denominator — RETRYING is not terminal, DEAD_LETTER is terminal failure
total_finished = counts["COMPLETED"] + counts["FAILED"] + counts["DEAD_LETTER"]
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `status IN ('PENDING', 'ASSIGNED', 'COMPLETED', 'FAILED', 'SECURITY_REJECTED', 'CANCELLED')` | Add `RETRYING`, `DEAD_LETTER` | Phase 2 | All status switches/filters must be updated |
| No retry columns on Job | `max_retries`, `retry_count`, `retry_after`, `backoff_multiplier`, `timeout_minutes` | Phase 2 | migration_v15.sql required for existing deployments |
| `execute_scheduled_job` creates a new Job unconditionally | Overlap guard skips if active job exists | Phase 2 | Prevents pile-up during backoff cycles |
| Node sends no `retriable` flag | `retriable: Optional[bool]` on ResultReport | Phase 2 | Default absent=non-retriable; nodes must be redeployed for full benefit |

**Deprecated/outdated after this phase:**
- `status == "FAILED"` as the only non-success terminal: DEAD_LETTER is a second terminal failure state
- Job detail panel showing only one execution: it now shows a list (already works via ExecutionLogModal for multi-attempt)

## Open Questions

1. **Should manually-dispatched jobs (from the UI dispatch form) inherit a retry policy?**
   - What we know: `JobCreate` model currently has no retry fields. CONTEXT.md says "all jobs carry a retry policy regardless of origin" but the dispatch form doesn't expose retry settings.
   - What's unclear: Should the dispatch form gain retry inputs, or should manually dispatched jobs always have `max_retries=0` unless the API is called directly?
   - Recommendation: Default `max_retries=0` for UI-dispatched jobs (form unchanged). Advanced retry config available via direct API. This is the minimal-surprise approach.

2. **Backoff base: should retry_count=1 give exactly 30s or `multiplier^1 = 2.0s`?**
   - What we know: `backoff_multiplier=2.0`, `retry_count=1` gives `2^1 = 2 seconds`, which is very short. CONTEXT.md "suggests 30s" for the initial delay but defers to Claude.
   - Recommendation: Use an initial delay floor of 30 seconds. Formula: `max(30, backoff_multiplier ^ retry_count)` seconds before jitter. This means: attempt 1 waits 30s, attempt 2 waits 4s → clamped to 30s too, attempt 3 waits 8s → 30s, attempt 4 waits 16s → 30s, attempt 5 waits 32s, attempt 6 waits 64s, etc. Alternatively, use `30 * backoff_multiplier ^ (retry_count - 1)` as the base formula: attempt 1 = 30s, attempt 2 = 60s, attempt 3 = 120s, attempt 4 = 240s, attempt 5 = 480s, attempt 6 = 960s, capped at 3600s. This is the cleaner formula.
   - **Chosen approach:** `delay = min(30 * (backoff_multiplier ** (retry_count - 1)), 3600)` with ±20% jitter. Records reasonable human-scale backoff without the 2-second first retry.

3. **APScheduler misfire_grace_time — what value to use?**
   - What we know: STATE.md flags this as a Phase 2 concern. Default is 1 second which is too short.
   - Recommendation: Set `misfire_grace_time=60` (seconds) in `sync_scheduler()` when calling `scheduler.add_job()`. This allows up to 60 seconds of startup delay before a cron fire is considered missed.

## Sources

### Primary (HIGH confidence)
- Direct source code reading of `puppeteer/agent_service/services/job_service.py` — current `report_result()` and `pull_work()` implementation
- Direct source code reading of `puppeteer/agent_service/db.py` — all DB models, `Config` table, column patterns
- Direct source code reading of `puppeteer/agent_service/models.py` — `ResultReport`, `JobCreate`, `WorkResponse` current fields
- Direct source code reading of `puppeteer/agent_service/services/scheduler_service.py` — `execute_scheduled_job()` and APScheduler setup
- Direct source code reading of `puppeteer/dashboard/src/views/Jobs.tsx` — `getStatusVariant()`, status filter chips, Job interface
- Direct source code reading of `puppeteer/migration_v14.sql` — migration file pattern
- `.planning/phases/02-retry-policy/02-CONTEXT.md` — all user decisions verified against actual code

### Secondary (MEDIUM confidence)
- `puppeteer/tests/test_execution_record.py` — test patterns for mock DB session construction (used for test gap analysis)
- APScheduler `misfire_grace_time` documented in STATE.md blockers — known project concern

### Tertiary (LOW confidence)
- None — all claims in this document are verified against project source code or CONTEXT.md locked decisions.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — no new dependencies; all libraries already in use
- Architecture: HIGH — all integration points verified against actual source code
- Pitfalls: HIGH — derived from direct code inspection + STATE.md documented concerns
- DB migration pattern: HIGH — directly copied from migration_v14.sql structure
- Frontend patterns: HIGH — verified against Jobs.tsx source

**Research date:** 2026-03-05
**Valid until:** 2026-04-04 (stable project; no external dependency churn expected)
