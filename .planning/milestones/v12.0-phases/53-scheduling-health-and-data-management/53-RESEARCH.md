# Phase 53: Scheduling Health and Data Management - Research

**Researched:** 2026-03-23
**Domain:** APScheduler cron analysis, execution record lifecycle, job templates, React health panel
**Confidence:** HIGH

## Summary

Phase 53 adds four orthogonal capabilities to the scheduling subsystem: a health visibility panel with missed-fire detection (VIS-05, VIS-06), reusable job templates (SRCH-06, SRCH-07), configurable execution record retention with pinning (SRCH-08, SRCH-09), and per-job CSV export (SRCH-10). All four capabilities build on stable, well-established patterns already in this codebase.

The missed-fire detection approach is the most architecturally novel piece. The CONTEXT.md decision uses APScheduler's `CronTrigger.get_next_fire_time()` to backfill expected fire windows. This is verified to work: the method returns timezone-aware datetimes given a reference point (see Code Examples). The strategy is to log each fire attempt in a `scheduled_fire_log` table and compare against `ExecutionRecord` rows by `scheduled_job_id + started_at` proximity, with a 5-minute grace period for LATE classification.

The remaining work follows established project patterns exactly: Config key/value for retention settings, StreamingResponse for CSV export, recharts AreaChart for sparklines, Sheet for the health detail drawer, tabs.tsx for the third tab, and the `audit()` helper for pin/unpin audit logging.

**Primary recommendation:** Deliver in five plans — (1) DB schema + migrations, (2) backend health/fire-log API, (3) backend retention/templates/pin API, (4) JobDefinitions Health + Templates tabs, (5) Admin retention panel + guided form template saving.

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- Health tab placed on JobDefinitions page alongside Definitions tab (three tabs: Definitions, Health, Templates)
- Time window switcher: 24h / 7d / 30d — default 24h
- Aggregate row at top: total fired / skipped / failed counts for window
- Per-definition rows: status icon + name + fire counts + recharts sparkline showing fire density timeline
- Clicking a red/failed definition row opens a right-side Sheet detail drawer (Phase 52 node drawer pattern)
- Backend uses stored expected-fires log (`scheduled_fire_log` table) populated by APScheduler hooks
- LATE = expected fire time passed + no execution started within 5-minute grace period
- MISSED = LATE fire with no execution record before the next scheduled fire time
- Fires during DRAFT or REVOKED state are excluded (not flagged as missed)
- Skipped-overlap fires classified as SKIPPED (not missed)
- `allow_overlap` boolean on `ScheduledJob` — default false
- Overlap skips logged with reason "Skipped: previous run still in progress"
- `allow_overlap` configurable in JobDefinition create/edit modal
- `dispatch_timeout_minutes` optional field on all jobs (scheduled and ad-hoc)
- No default for dispatch_timeout_minutes (blank = never auto-fail)
- Background sweeper transitions PENDING jobs to FAILED when dispatch_timeout exceeded
- Dispatch timeout failure counts as FAILED in health panel
- "Save as Template" button at bottom of guided job form alongside Submit button
- JobTemplate table: id, name, creator_id, visibility (private/shared), created_at, payload (JSON)
- Private templates visible only to creator; shared templates visible to all operators
- Visibility toggle: creator or admin can promote/demote
- Template management on third tab (Templates) on JobDefinitions page
- Actions: Load, Rename, Delete (delete restricted to creator or admin)
- Loading a template pre-populates guided job form with all fields editable
- Admin configures retention period in days (default 14) in Admin.tsx "Data Retention" subsection
- Admin config panel shows live count of eligible and pinned records
- Nightly background task hard-deletes where completed_at < now - retention_days AND pinned = false
- Pin/unpin via PATCH /executions/{id}/pin and PATCH /executions/{id}/unpin (admin or operator with jobs:write)
- Pin toggle in job detail drawer; pinned rows: filled pin icon + amber left border
- CSV export follows Phase 49 established pattern
- Download button in job detail drawer exports all execution records for that job as CSV
- CSV columns: job_guid, node_id, status, exit_code, started_at, completed_at, duration_s, attempt_number, pinned

### Claude's Discretion

- Exact `scheduled_fire_log` table schema details (columns, indexes)
- Background task polling interval for dispatch timeout sweeper
- Exact sparkline colour mapping (green / amber / red per fire state)
- `JobTemplate` table migration numbering

### Deferred Ideas (OUT OF SCOPE)

- None raised during discussion — scope stayed within phase boundaries.
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| VIS-05 | Dashboard shows Scheduling Health panel with aggregate fired/skipped/failed counts and per-definition health indicators with configurable time window (24h / 7d / 30d) | APScheduler CronTrigger computes expected fires; `scheduled_fire_log` table records actuals; new `GET /health/scheduling` endpoint aggregates per window |
| VIS-06 | Scheduling Health panel detects missed fires; affected definitions show red health indicator | LATE/MISSED classification via 5-min grace + next-fire comparison; `scheduled_fire_log` status enum covers fired/skipped_overlap/skipped_draft/late/missed |
| SRCH-06 | Operator can save a job configuration as a reusable named template (signing state excluded) | New `JobTemplate` DB table + CRUD API; Save button on GuidedDispatchCard |
| SRCH-07 | Operator can load a saved template into the guided job form; all fields editable | Template load passes payload to GuidedDispatchCard via callback; existing `onLoadTemplate` prop pattern |
| SRCH-08 | Admin can configure global execution record retention period (default 14 days); nightly pruning skips pinned records | Config key `execution_retention_days`; updated `prune_execution_history()` checks `pinned=false`; existing APScheduler daily job |
| SRCH-09 | Admin can pin individual execution records; pin/unpin audit-logged | `pinned` boolean column on `ExecutionRecord`; PATCH endpoints; `audit()` helper |
| SRCH-10 | Operator can download execution records for a job as CSV from the job detail drawer | `GET /jobs/{guid}/executions/export` using StreamingResponse pattern from Phase 49 |
</phase_requirements>

---

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| APScheduler | 3.11.2 (confirmed in container) | CronTrigger.get_next_fire_time() for expected-fire computation | Already installed, powers all scheduling |
| SQLAlchemy async | existing | New tables: scheduled_fire_log, JobTemplate; column additions | All DB access uses this ORM |
| recharts | existing | AreaChart sparklines for fire density timeline | Already used in Nodes.tsx StatsSparkline |
| @radix-ui/react-sheet (sheet.tsx) | existing | Health detail drawer | Phase 52 node drawer — established pattern |
| tabs.tsx | existing | Three-tab layout on JobDefinitions page | Already used in Admin.tsx |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| StreamingResponse + csv | existing Python stdlib | Per-job execution CSV export | Exactly as in GET /jobs/export |
| date-fns | existing | Time window calculations in frontend | Already in project |
| lucide-react Pin icon | existing package | Pin/unpin toggle icon | Check `Pin` is exported from lucide-react |

**Installation:**
No new packages required. All dependencies are already installed.

**Verify Pin icon availability:**
```bash
grep -r "from 'lucide-react'" puppeteer/dashboard/src/ | grep "Pin" | head -3
# If absent, use: import { Pin } from 'lucide-react' — lucide-react ships Pin
```

**croniter NOT installed** — do not use croniter for cron parsing. Use APScheduler's `CronTrigger` which is already present.

---

## Architecture Patterns

### Recommended New File Structure
```
puppeteer/
├── agent_service/
│   ├── db.py                          # Add: ScheduledFireLog, JobTemplate; alter: ExecutionRecord.pinned, ScheduledJob.allow_overlap + dispatch_timeout_minutes, Job.dispatch_timeout_minutes
│   ├── models.py                      # Add: SchedulingHealthResponse, JobTemplateCreate/Response, etc.
│   ├── services/
│   │   └── scheduler_service.py       # Extend: fire log hooks, dispatch sweeper, health query method
│   └── main.py                        # Add: /health/scheduling, /job-templates/*, /executions/{id}/pin|unpin, /jobs/{guid}/executions/export
├── migration_v43.sql                  # All Phase 53 schema changes
puppeteer/dashboard/src/
├── views/
│   └── JobDefinitions.tsx             # Extend: three tabs (Definitions, Health, Templates)
├── components/
│   ├── GuidedDispatchCard.tsx         # Extend: Save as Template button + onSaveTemplate prop
│   ├── job-definitions/
│   │   ├── JobDefinitionModal.tsx     # Extend: allow_overlap toggle + dispatch_timeout_minutes field
│   │   └── HealthTab.tsx             # NEW: health panel component
│   └── TemplatesTab.tsx              # NEW: template list component
```

### Pattern 1: APScheduler Fire Log Hook
**What:** At the top of `execute_scheduled_job()`, before any status check, write a `ScheduledFireLog` row with `status='fired'`. Status checks that skip the job update the row status to `'skipped_draft'` or `'skipped_overlap'`.
**When to use:** Every APScheduler cron callback invocation.
**Example:**
```python
# Source: verified against APScheduler 3.11.2 in container
async def execute_scheduled_job(self, scheduled_job_id: str):
    fire_time = datetime.utcnow()
    async with db_module.AsyncSessionLocal() as session:
        fire_log = ScheduledFireLog(
            scheduled_job_id=scheduled_job_id,
            expected_at=fire_time,
            status='fired',
        )
        session.add(fire_log)
        await session.commit()
        fire_log_id = fire_log.id  # capture for status update if skip

        result = await session.execute(select(ScheduledJob).where(...))
        s_job = result.scalar_one_or_none()

        if s_job.status in SKIP_STATUSES:
            fire_log.status = 'skipped_draft'
            await session.commit()
            return

        if active_job:  # overlap guard
            fire_log.status = 'skipped_overlap'
            await session.commit()
            return
        # ... proceed to create Job
```

### Pattern 2: Expected-Fire Backfill via CronTrigger
**What:** For missed-fire detection, use `CronTrigger.get_next_fire_time(prev, window_start)` to generate the sequence of expected fires within a time window and compare against `scheduled_fire_log` rows.
**When to use:** In the health summary endpoint to classify fires as LATE or MISSED.
**Example:**
```python
# Source: verified in puppeteer-agent-1 container against APScheduler 3.11.2
from apscheduler.triggers.cron import CronTrigger
import datetime

def expected_fires_in_window(cron_expr: str, window_start: datetime, window_end: datetime):
    """Generate all expected fire times in [window_start, window_end)."""
    parts = cron_expr.split()
    trigger = CronTrigger(
        minute=parts[0], hour=parts[1],
        day=parts[2], month=parts[3], day_of_week=parts[4]
    )
    fires = []
    t = window_start
    while True:
        next_fire = trigger.get_next_fire_time(None, t)
        if next_fire is None or next_fire.replace(tzinfo=None) >= window_end:
            break
        fires.append(next_fire.replace(tzinfo=None))
        t = next_fire + datetime.timedelta(seconds=1)
    return fires
```

### Pattern 3: Config Key/Value for Retention Setting
**What:** Store `execution_retention_days` in the existing `Config` table (key/value store). Read/write via existing pattern.
**When to use:** Admin sets retention period; pruner reads it at runtime.
**Example:**
```python
# Source: existing Config usage in main.py (mounts config, signing key)
# Read:
res = await db.execute(select(Config).where(Config.key == 'execution_retention_days'))
row = res.scalar_one_or_none()
retention_days = int(row.value) if row else 14  # default 14

# Write (upsert):
existing = await db.execute(select(Config).where(Config.key == 'execution_retention_days'))
row = existing.scalar_one_or_none()
if row:
    row.value = str(new_value)
else:
    db.add(Config(key='execution_retention_days', value=str(new_value)))
await db.commit()
```

### Pattern 4: StreamingResponse CSV Export (execution records)
**What:** New endpoint `GET /jobs/{guid}/executions/export` streams execution records as CSV. Identical mechanics to `/jobs/export`.
**When to use:** SRCH-10 per-job CSV download.
**Example:**
```python
# Source: /jobs/export in main.py (lines 958-1007)
EXEC_CSV_HEADERS = ["job_guid", "node_id", "status", "exit_code",
                    "started_at", "completed_at", "duration_s", "attempt_number", "pinned"]

def generate():
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(EXEC_CSV_HEADERS)
    yield buf.getvalue()
    buf.seek(0); buf.truncate()
    for rec in records:
        duration = None
        if rec.started_at and rec.completed_at:
            duration = (rec.completed_at - rec.started_at).total_seconds()
        writer.writerow([rec.job_guid, rec.node_id, rec.status, rec.exit_code,
                         rec.started_at, rec.completed_at, duration,
                         rec.attempt_number, rec.pinned])
        yield buf.getvalue()
        buf.seek(0); buf.truncate()

return StreamingResponse(generate(), media_type="text/csv",
    headers={"Content-Disposition": f"attachment; filename=executions-{guid}.csv"})
```

### Pattern 5: Pin Toggle in React (execution drawer)
**What:** PATCH calls to `/api/executions/{id}/pin` or `/api/executions/{id}/unpin`. Pin state shown with lucide `Pin` icon + amber left border on row.
**When to use:** SRCH-09 pinning UX in job detail drawer.
**Example:**
```tsx
// Amber left-border pattern (consistent with project's status row patterns)
<tr className={`border-t border-zinc-900 ${rec.pinned ? 'border-l-2 border-l-amber-500' : ''}`}>
  <td>
    <button onClick={() => handlePin(rec.id, rec.pinned)}>
      <Pin className={`h-3 w-3 ${rec.pinned ? 'fill-amber-500 text-amber-500' : 'text-zinc-500'}`} />
    </button>
  </td>
  ...
</tr>
```

### Pattern 6: Three-Tab Layout on JobDefinitions
**What:** Convert existing two-button tab switcher to tabs.tsx Radix tabs (same component used in Admin.tsx).
**When to use:** JobDefinitions page restructure.
**Example:**
```tsx
// Source: Admin.tsx uses Tabs/TabsList/TabsTrigger/TabsContent from @/components/ui/tabs
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs';

<Tabs defaultValue="definitions">
  <TabsList>
    <TabsTrigger value="definitions">Definitions</TabsTrigger>
    <TabsTrigger value="health">Health</TabsTrigger>
    <TabsTrigger value="templates">Templates</TabsTrigger>
  </TabsList>
  <TabsContent value="definitions">...</TabsContent>
  <TabsContent value="health">...</TabsContent>
  <TabsContent value="templates">...</TabsContent>
</Tabs>
```

### Anti-Patterns to Avoid
- **Querying APScheduler job store for expected fires:** APScheduler's in-memory job store does not persist fire history. Use `CronTrigger.get_next_fire_time()` to compute expected fires from the cron expression + time window instead.
- **Using croniter library:** Not installed. Not needed — APScheduler's CronTrigger covers the use case.
- **Altering prune_execution_history() before adding pinned column:** The pruner update must land in the same migration wave as the `pinned` column addition.
- **Relying on `prune_execution_history()` existing Config key `history_retention_days`:** The existing pruner uses `history_retention_days` (30-day default for execution records). This phase introduces `execution_retention_days` with a 14-day default as a distinct key for the new operator-controlled retention. The existing `history_retention_days` key is separate and should remain unchanged.
- **No switch.tsx component:** The UI component library does not have a Switch component. Use a styled Checkbox or a custom toggle button for the `allow_overlap` boolean. Alternatively, install `@radix-ui/react-switch` and create `switch.tsx`.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Cron next-fire computation | Custom regex/parser | APScheduler CronTrigger.get_next_fire_time() | Already in container; handles all cron edge cases, DST, etc. |
| CSV streaming | Load all rows into memory | StreamingResponse generator | Exact pattern from /jobs/export; memory-safe for large datasets |
| Tab switching | Custom tab state management | tabs.tsx (Radix) | Already in project; accessible, consistent styling |
| Right-side drawer | Custom slide-in panel | sheet.tsx (Radix Sheet) | Phase 52 node drawer — identical pattern |
| Audit logging | Custom audit table inserts | `audit()` helper from deps.py | Handles CE/EE mode differences automatically |

---

## Common Pitfalls

### Pitfall 1: CronTrigger timezone-aware returns
**What goes wrong:** `get_next_fire_time()` returns a timezone-aware datetime (UTC+00:00). Comparing it directly to a naive `datetime.utcnow()` raises `TypeError: can't compare offset-naive and offset-aware datetimes`.
**Why it happens:** APScheduler always attaches timezone info to computed fire times.
**How to avoid:** Strip tzinfo with `.replace(tzinfo=None)` before storing in DB or comparing to naive datetimes. See Code Examples — verified in container.
**Warning signs:** `TypeError` in `execute_scheduled_job` or health computation code.

### Pitfall 2: Existing pruner Config key conflict
**What goes wrong:** The existing `prune_execution_history()` reads `history_retention_days` (default 30). The new SRCH-08 feature uses `execution_retention_days` (default 14). If the planner conflates these, pruning behavior changes silently on existing deployments.
**Why it happens:** Two Config keys for related-but-distinct retention settings.
**How to avoid:** The SRCH-08 retention feature should update `prune_execution_history()` to read `execution_retention_days` first, falling back to `history_retention_days` for backward compatibility, with an ultimate default of 14. Document this clearly in the migration.

### Pitfall 3: ScheduledFireLog grows without pruning
**What goes wrong:** Every cron fire writes a row. A job firing every minute accumulates 1,440 rows/day. No pruning = unbounded growth.
**Why it happens:** New table, no pruning job added at creation time.
**How to avoid:** Add pruning of `ScheduledFireLog` rows older than `max(30d, retention_window)` to the nightly maintenance jobs. Alternatively, prune rows older than 31 days (covers the max 30d health window).

### Pitfall 4: dispatch_timeout sweeper race with node pickup
**What goes wrong:** A job transitions to FAILED for dispatch timeout at the same instant a node picks it up, resulting in a job that runs on the node but is already FAILED in the DB.
**Why it happens:** No atomic lock on the PENDING→FAILED transition.
**How to avoid:** In the dispatch timeout sweeper, use `WHERE status = 'PENDING'` with optimistic concurrency — only update if still PENDING. The node's pull_work checks job status before executing, so if it picks up a PENDING job just before the sweeper runs, the sweeper will find `status != PENDING` and skip it. This is safe.

### Pitfall 5: allow_overlap default changes existing behavior
**What goes wrong:** Adding `allow_overlap` column with `default=False` on `ScheduledJob` implicitly changes the overlap behavior for all EXISTING jobs. The current code in `execute_scheduled_job` already skips overlapping runs (the `active_job` guard on lines 138-159 of scheduler_service.py), so `default=False` is consistent with existing behavior — no behavioral regression.
**Why it happens:** Potential concern, but actually safe due to aligned behavior.
**How to avoid:** No action needed — explicitly document this alignment in the migration comment.

### Pitfall 6: GuidedDispatchCard Save as Template button needs onSaveTemplate prop
**What goes wrong:** GuidedDispatchCard is rendered in Jobs.tsx — adding the Template save button requires Jobs.tsx to handle the callback AND the Templates tab on JobDefinitions.tsx also needs to trigger "load template into form". These are two different views.
**Why it happens:** The guided dispatch form lives in Jobs.tsx; the Templates management tab lives in JobDefinitions.tsx.
**How to avoid:** The "Save as Template" capability only needs to live in Jobs.tsx (SRCH-06 says "from the guided job form"). The Templates tab in JobDefinitions.tsx provides Load/Rename/Delete management only. Loading a template from the Templates tab navigates to the Jobs view with template data in state (or uses a query param), OR the Templates tab has its own "Load to Dispatch" button that triggers navigation to Jobs view. Keep these concerns separate.

---

## Code Examples

### ScheduledFireLog DB Model
```python
# Source: pattern matches existing NodeStats/ExecutionRecord models in db.py
class ScheduledFireLog(Base):
    __tablename__ = "scheduled_fire_log"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    scheduled_job_id: Mapped[str] = mapped_column(String, nullable=False)
    expected_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False, default='fired')
    # status values: fired | skipped_draft | skipped_overlap
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index("ix_fire_log_job_expected", "scheduled_job_id", "expected_at"),
    )
```

### JobTemplate DB Model
```python
class JobTemplate(Base):
    __tablename__ = "job_templates"
    id: Mapped[str] = mapped_column(String, primary_key=True)  # UUID hex
    name: Mapped[str] = mapped_column(String, nullable=False)
    creator_id: Mapped[str] = mapped_column(String, nullable=False)  # username
    visibility: Mapped[str] = mapped_column(String, nullable=False, default='private')  # private | shared
    payload: Mapped[str] = mapped_column(Text, nullable=False)  # JSON: all job fields, no signature
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
```

### ExecutionRecord.pinned column addition (migration SQL)
```sql
-- migration_v43.sql — Phase 53 schema additions
-- Part 1: ExecutionRecord pinning
ALTER TABLE execution_records ADD COLUMN IF NOT EXISTS pinned BOOLEAN DEFAULT FALSE;
-- SQLite: ALTER TABLE execution_records ADD COLUMN pinned INTEGER DEFAULT 0;

-- Part 2: ScheduledJob.allow_overlap + dispatch_timeout_minutes
ALTER TABLE scheduled_jobs ADD COLUMN IF NOT EXISTS allow_overlap BOOLEAN DEFAULT FALSE;
ALTER TABLE scheduled_jobs ADD COLUMN IF NOT EXISTS dispatch_timeout_minutes INTEGER;
-- SQLite:
-- ALTER TABLE scheduled_jobs ADD COLUMN allow_overlap INTEGER DEFAULT 0;
-- ALTER TABLE scheduled_jobs ADD COLUMN dispatch_timeout_minutes INTEGER;

-- Part 3: Job.dispatch_timeout_minutes
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS dispatch_timeout_minutes INTEGER;
-- SQLite: ALTER TABLE jobs ADD COLUMN dispatch_timeout_minutes INTEGER;

-- Part 4: New tables (handled by create_all on fresh deployments; manual on existing)
-- scheduled_fire_log and job_templates tables — create_all covers fresh deployments
-- Existing deployments: see CREATE TABLE IF NOT EXISTS statements below
CREATE TABLE IF NOT EXISTS scheduled_fire_log (
    id SERIAL PRIMARY KEY,
    scheduled_job_id VARCHAR NOT NULL,
    expected_at TIMESTAMP NOT NULL,
    status VARCHAR NOT NULL DEFAULT 'fired',
    created_at TIMESTAMP DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_fire_log_job_expected ON scheduled_fire_log(scheduled_job_id, expected_at);

CREATE TABLE IF NOT EXISTS job_templates (
    id VARCHAR PRIMARY KEY,
    name VARCHAR NOT NULL,
    creator_id VARCHAR NOT NULL,
    visibility VARCHAR NOT NULL DEFAULT 'private',
    payload TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);
```

### Health Summary Endpoint Shape
```python
# Source: designed to match CONTEXT.md requirements
# GET /health/scheduling?window=24h|7d|30d
@app.get("/health/scheduling")
async def get_scheduling_health(
    window: Literal["24h", "7d", "30d"] = "24h",
    current_user: User = Depends(require_permission("jobs:read")),
    db: AsyncSession = Depends(get_db),
):
    window_hours = {"24h": 24, "7d": 168, "30d": 720}[window]
    window_start = datetime.utcnow() - timedelta(hours=window_hours)
    # ... aggregate query on scheduled_fire_log joined with scheduled_jobs
    # Returns: { aggregate: {fired, skipped, failed}, definitions: [{...per-def health}] }
```

### Dispatch Timeout Sweeper
```python
# Add to scheduler_service.py — runs every N minutes (recommend: 5 minutes)
async def sweep_dispatch_timeouts(self):
    """Transition PENDING jobs to FAILED when dispatch_timeout_minutes exceeded."""
    async with db_module.AsyncSessionLocal() as session:
        now = datetime.utcnow()
        result = await session.execute(
            select(Job).where(
                Job.status == "PENDING",
                Job.dispatch_timeout_minutes.isnot(None),
            )
        )
        jobs = result.scalars().all()
        failed_count = 0
        for job in jobs:
            deadline = job.created_at + timedelta(minutes=job.dispatch_timeout_minutes)
            if now > deadline:
                job.status = "FAILED"
                job.result = json.dumps({
                    "error": f"Dispatch timeout: no node picked up the job within {job.dispatch_timeout_minutes} minutes"
                })
                failed_count += 1
        if failed_count:
            await session.commit()
            logger.info(f"Dispatch timeout sweeper: failed {failed_count} jobs")
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Manual cron fire tracking (none) | scheduled_fire_log table populated by APScheduler callback hooks | Phase 53 (new) | Enables missed-fire detection without external cron daemon |
| Execution records never pruned (or pruned via `history_retention_days`) | Pinning + configurable `execution_retention_days` (default 14d) | Phase 53 (new) | Operators control data growth; important records preserved |
| No job config reuse | JobTemplate table with private/shared visibility | Phase 53 (new) | Reduces repeat configuration effort |

**Existing behavior to preserve:**
- `history_retention_days` Config key and `prune_execution_history()` behavior: the new `execution_retention_days` key coexists; backward compat maintained by fallback.
- Current overlap guard in `execute_scheduled_job` (lines 138-159) already blocks concurrent runs. The `allow_overlap=False` default aligns with this existing behavior — no regression.

---

## Open Questions

1. **No switch.tsx UI component for allow_overlap toggle**
   - What we know: `switch.tsx` is absent from `src/components/ui/`. The `checkbox.tsx` exists.
   - What's unclear: Whether to install `@radix-ui/react-switch` and create `switch.tsx`, or use a styled checkbox/button.
   - Recommendation: Use a styled toggle button (two-state pill button) consistent with the existing ACTIVE/STAGING tab pattern, or use `checkbox.tsx` with a label. Either avoids adding a new dependency.

2. **"Load template" navigation: Jobs.tsx to Templates tab**
   - What we know: GuidedDispatchCard lives in Jobs.tsx view; template list lives in JobDefinitions.tsx.
   - What's unclear: Should "Load" in the Templates tab navigate to Jobs view, or should templates only be loadable from the Jobs view itself?
   - Recommendation: Keep it simple — "Load" in Templates tab navigates to `/jobs` with a `?template_id=<id>` query param; Jobs.tsx reads the param on mount and calls the template API to pre-populate the form.

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (backend) + vitest (frontend) |
| Config file | `puppeteer/pytest.ini` (or implicit) + `puppeteer/dashboard/vite.config.ts` |
| Quick run command | `cd puppeteer && pytest tests/test_scheduling_health.py -x` |
| Full suite command | `cd puppeteer && pytest` / `cd puppeteer/dashboard && npm run test` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| VIS-05 | Health endpoint returns aggregate fired/skipped/failed + per-def rows for 24h/7d/30d | unit | `pytest tests/test_scheduling_health.py::test_health_aggregate -x` | Wave 0 |
| VIS-06 | LATE/MISSED classification: 5-min grace, next-fire boundary | unit | `pytest tests/test_scheduling_health.py::test_missed_fire_detection -x` | Wave 0 |
| SRCH-06 | POST /job-templates creates template, returns id + payload sans signature | unit | `pytest tests/test_job_templates.py::test_create_template -x` | Wave 0 |
| SRCH-07 | GET /job-templates returns visible templates for user; private filtered correctly | unit | `pytest tests/test_job_templates.py::test_template_visibility -x` | Wave 0 |
| SRCH-08 | Pruner deletes records where completed_at < cutoff AND pinned=False | unit | `pytest tests/test_retention.py::test_pruner_respects_pinned -x` | Wave 0 |
| SRCH-09 | PATCH /executions/{id}/pin sets pinned=True + audit log entry | unit | `pytest tests/test_retention.py::test_pin_unpin -x` | Wave 0 |
| SRCH-10 | GET /jobs/{guid}/executions/export returns CSV with correct headers and pinned column | unit | `pytest tests/test_execution_export.py::test_csv_export -x` | Wave 0 |

### Sampling Rate
- **Per task commit:** `cd puppeteer && pytest tests/test_scheduling_health.py tests/test_job_templates.py tests/test_retention.py tests/test_execution_export.py -x`
- **Per wave merge:** `cd puppeteer && pytest`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `puppeteer/tests/test_scheduling_health.py` — covers VIS-05, VIS-06
- [ ] `puppeteer/tests/test_job_templates.py` — covers SRCH-06, SRCH-07
- [ ] `puppeteer/tests/test_retention.py` — covers SRCH-08, SRCH-09
- [ ] `puppeteer/tests/test_execution_export.py` — covers SRCH-10

---

## Sources

### Primary (HIGH confidence)
- APScheduler 3.11.2 (verified in `puppeteer-agent-1` container) — CronTrigger.get_next_fire_time() behavior confirmed via live execution
- Existing codebase: `db.py`, `scheduler_service.py`, `models.py`, `main.py`, `deps.py`, `Nodes.tsx`, `Admin.tsx`, `Jobs.tsx`, `JobDefinitions.tsx`, `GuidedDispatchCard.tsx` — patterns confirmed by direct read

### Secondary (MEDIUM confidence)
- APScheduler 3.x documentation patterns — CronTrigger, misfire_grace_time — consistent with observed container behavior

### Tertiary (LOW confidence)
- None — all findings verified against codebase or container execution

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all libraries verified in container and codebase
- Architecture: HIGH — all patterns replicate established project patterns exactly
- Pitfalls: HIGH — identified from direct codebase analysis (existing overlap guard, existing Config key, timezone issue confirmed)
- Missed-fire logic: HIGH — CronTrigger.get_next_fire_time() verified working in container

**Research date:** 2026-03-23
**Valid until:** 2026-04-23 (stable stack, no fast-moving dependencies)
