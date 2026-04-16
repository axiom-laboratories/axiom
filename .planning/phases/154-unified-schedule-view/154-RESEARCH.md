# Phase 154: Unified Schedule View - Research

**Researched:** 2026-04-16  
**Domain:** React Dashboard + FastAPI Backend (Scheduling & Time Handling)  
**Confidence:** HIGH  

## Summary

Phase 154 implements UI-05: a new `/schedule` unified page showing both ScheduledJob (JOB badge) and cron-scheduled Workflow (FLOW badge) entries in a single read-only observability table, sorted by next-run time ascending. This phase bridges workflow and job scheduling under a single operator view — a natural next-run-time dashboard for at-a-glance scheduling clarity.

The implementation is low-risk: the backend scheduling infrastructure (APScheduler, cron trigger evaluation) already exists in `scheduler_service.py`, and the frontend table pattern is standard across the codebase (Workflows.tsx, JobDefinitions.tsx). Key work: backend service method to merge and sort unified schedule entries, new API endpoint, frontend table view, and sidebar navigation changes.

**Primary recommendation:** Implement backend service method `get_unified_schedule()` that queries both ScheduledJob and Workflow tables, computes next-run times server-side using APScheduler, and returns merged sorted response. Frontend then renders a simple table with existing badge + navigation patterns.

## User Constraints (from CONTEXT.md)

### Locked Decisions
- **Page placement & navigation:** New top-level `/schedule` route with sidebar entry. Existing "Scheduled Jobs" sidebar renamed to "Job Definitions" to clarify CRUD vs. unified view distinction. Three entries coexist: Schedule (overview), Job Definitions (ScheduledJob CRUD), Workflows (Workflow CRUD).
- **Table structure:** Flat single-table design (JOB and FLOW rows mixed), default sort by `next_run_time` ascending. Columns: Type (badge) | Name (clickable) | Next Run | Last Run Status.
- **Filtering:** Only include active items with cron (ScheduledJob.is_active=true + schedule_cron set; Workflow.is_paused=false + schedule_cron set).
- **Next-run calculation:** Server-side via APScheduler `get_next_fire_time()` — not client-side date math.
- **Row interactions:** Click to navigate: JOB → `/job-definitions` (opens edit modal); FLOW → `/workflows/:id`. Read-only view — no inline management actions.
- **Auth:** `jobs:read` permission (consistent with `/api/jobs/definitions`).

### Claude's Discretion
- Exact sidebar icon for Schedule entry
- Human-readable relative time format implementation (e.g., `date-fns formatDistanceToNow`)
- Empty state copy when no active schedules exist
- Polling interval for auto-refresh (default: 30s, established in Workflows.tsx)
- Last run status badge colors (reuse existing `getStatusVariant()`)

### Deferred Ideas (OUT OF SCOPE)
- Paused/inactive items shown greyed-out with toggle (Phase 155+)
- Cron expression column (power user feature, later pass)
- Inline pause/enable row actions (management; belongs on dedicated pages)
- Run-now button from schedule view (scope creep; read-only phase)

---

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| **APScheduler** | 3.10+ | Cron trigger parsing + next-fire-time calculation | Already embedded in scheduler_service.py; `get_next_fire_time()` API proven in Phase 149+ |
| **Pydantic** | 2.x | Request/response model validation | Existing pattern across all API endpoints (JobDefinitionResponse, etc.) |
| **FastAPI** | Latest (0.100+) | HTTP endpoint routing + dependency injection | Same as all agent_service routes |
| **React** | 18.x | Frontend component library | Dashboard standard |
| **@tanstack/react-query** | 5.x | Data fetching + auto-refetch | Established across views (useQuery + refetchInterval pattern) |
| **date-fns** | 2.30+ | Human-readable date formatting | Already used in History.tsx, JobDefinitions.tsx for formatDistanceToNow |
| **shadcn/ui** | Latest | Table, Badge, Button, Card components | All used in existing views |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| **lucide-react** | Latest | Sidebar icon for Schedule entry | Icon selection in MainLayout navigation |
| **SQLAlchemy** | 2.0+ | ORM query interface | Existing; fetch ScheduledJob + Workflow in service method |

### Why This Stack

- **APScheduler** is already running in-process at server startup (scheduler_service.start()). No external dependency; `CronTrigger.get_next_fire_time(None, now)` is the proven API.
- **date-fns formatDistanceToNow()** is already imported and used in JobDefinitions.tsx for "When" column (relative time like "5 minutes ago"). Consistency across dashboard.
- **React Query** with `refetchInterval: 30000` matches the established pattern in Workflows.tsx — near-real-time without polling spam.
- **Pydantic models** enforce API contract; new `ScheduleEntryResponse` model prevents data shape surprises.

---

## Architecture Patterns

### Recommended Project Structure

Backend service method location: `puppeteer/agent_service/services/scheduler_service.py`  
Backend endpoint location: `puppeteer/agent_service/main.py` → new route `GET /api/schedule`  
Frontend view location: `puppeteer/dashboard/src/views/Schedule.tsx` (new)  
Route registration: `puppeteer/dashboard/src/AppRoutes.tsx`  
Sidebar navigation: `puppeteer/dashboard/src/components/MainLayout.tsx` (or dedicated Sidebar component)

```
Backend:
├── scheduler_service.py
│   ├── SchedulerService.get_unified_schedule() [NEW]
│   │   ├── query ScheduledJob where is_active=true + schedule_cron is not null
│   │   ├── query Workflow where is_paused=false + schedule_cron is not null
│   │   ├── for each: compute next_run_time via APScheduler.trigger.get_next_fire_time()
│   │   └── return unified sorted list (type, id, name, next_run_time, last_run_status)
│   └── [existing methods unchanged]
├── main.py
│   └── @app.get("/api/schedule") [NEW route]
│       ├── auth: jobs:read
│       ├── calls: scheduler_service.get_unified_schedule()
│       └── response: ScheduleListResponse (list of ScheduleEntryResponse)
└── models.py
    └── ScheduleEntryResponse [NEW Pydantic model]
        ├── id: str
        ├── type: Literal["JOB", "FLOW"]
        ├── name: str
        ├── next_run_time: datetime
        └── last_run_status: Optional[str]

Frontend:
├── views/Schedule.tsx [NEW]
│   ├── useQuery hook: fetch /api/schedule with refetchInterval: 30000
│   ├── table: Type | Name | Next Run | Last Run Status
│   ├── row click: navigate to detail page
│   └── empty state: "No active schedules"
├── AppRoutes.tsx
│   └── <Route path="/schedule" element={<Schedule />} /> [NEW]
└── components/MainLayout.tsx (or Sidebar component)
    └── add Schedule nav entry (icon + link to /schedule)
    └── rename "Scheduled Jobs" → "Job Definitions"
```

### Pattern 1: Backend Service Method for Unified Data Fetch

**What:** Consolidate ScheduledJob + Workflow scheduling data at the service layer, not in the route handler. Compute next-run times server-side using APScheduler's proven trigger API.

**When to use:** Multi-source queries where business logic (filtering, merging, sorting) is complex or requires domain knowledge (e.g., APScheduler API calls).

**Example:**

```python
# scheduler_service.py — ADD THIS METHOD
async def get_unified_schedule(self, db: AsyncSession) -> List[dict]:
    """
    Returns merged list of ScheduledJob + Workflow entries with next-run times.
    Filters: only items with active cron (ScheduledJob.is_active=true + cron set;
             Workflow.is_paused=false + cron set).
    Sorted by next_run_time ascending.
    """
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc)
    
    # Fetch active ScheduledJobs with cron
    result = await db.execute(
        select(ScheduledJob).where(
            ScheduledJob.is_active == True,
            ScheduledJob.schedule_cron.isnot(None)
        )
    )
    jobs = result.scalars().all()
    
    # Fetch active Workflows with cron
    result = await db.execute(
        select(Workflow).where(
            Workflow.is_paused == False,
            Workflow.schedule_cron.isnot(None)
        )
    )
    workflows = result.scalars().all()
    
    entries = []
    
    # Process ScheduledJobs
    for job in jobs:
        parts = job.schedule_cron.strip().split()
        if len(parts) != 5:
            continue  # Skip invalid cron
        
        trigger = CronTrigger(
            minute=parts[0], hour=parts[1], day=parts[2],
            month=parts[3], day_of_week=parts[4]
        )
        next_fire = trigger.get_next_fire_time(None, now)
        
        # Get last run status from most recent Job or ScheduledFireLog
        last_status = None
        result = await db.execute(
            select(Job.status)
            .where(Job.scheduled_job_id == job.id)
            .order_by(Job.created_at.desc())
            .limit(1)
        )
        last_job = result.scalar_one_or_none()
        if last_job:
            last_status = last_job
        
        entries.append({
            "id": job.id,
            "type": "JOB",
            "name": job.name,
            "next_run_time": next_fire,
            "last_run_status": last_status,
        })
    
    # Process Workflows
    for workflow in workflows:
        parts = workflow.schedule_cron.strip().split()
        if len(parts) != 5:
            continue
        
        trigger = CronTrigger(
            minute=parts[0], hour=parts[1], day=parts[2],
            month=parts[3], day_of_week=parts[4]
        )
        next_fire = trigger.get_next_fire_time(None, now)
        
        # Get last run status from most recent WorkflowRun
        last_status = None
        result = await db.execute(
            select(WorkflowRun.status)
            .where(WorkflowRun.workflow_id == workflow.id)
            .order_by(WorkflowRun.created_at.desc())
            .limit(1)
        )
        last_run = result.scalar_one_or_none()
        if last_run:
            last_status = last_run
        
        entries.append({
            "id": workflow.id,
            "type": "FLOW",
            "name": workflow.name,
            "next_run_time": next_fire,
            "last_run_status": last_status,
        })
    
    # Sort by next_run_time ascending
    entries.sort(key=lambda e: e["next_run_time"] or datetime.max)
    return entries
```

### Pattern 2: Pydantic Response Model for Type Safety

**What:** Define `ScheduleEntryResponse` Pydantic model to enforce API contract and enable IDE autocomplete on frontend.

**Example:**

```python
# models.py — ADD THIS MODEL
class ScheduleEntryResponse(BaseModel):
    """Single entry in unified schedule (ScheduledJob or Workflow)."""
    id: str
    type: Literal["JOB", "FLOW"]
    name: str
    next_run_time: Optional[datetime] = None
    last_run_status: Optional[str] = None
    
    model_config = ConfigDict(from_attributes=True)

class ScheduleListResponse(BaseModel):
    """Response for GET /api/schedule."""
    entries: List[ScheduleEntryResponse]
    total: int
```

### Pattern 3: Frontend useQuery Hook with Polling

**What:** Fetch schedule data with automatic refetch interval (30s) to keep next-run times fresh without manual refresh.

**Example (Schedule.tsx):**

```typescript
const { data, isLoading, error } = useQuery({
  queryKey: ['schedule'],
  queryFn: async () => {
    const res = await authenticatedFetch('/api/schedule');
    if (!res.ok) throw new Error('Failed to fetch schedule');
    return res.json() as Promise<ScheduleListResponse>;
  },
  refetchInterval: 30000, // Auto-refresh every 30s
});
```

### Pattern 4: Table with Type Badge + Navigation

**What:** Row click navigates to detail page; type badge (JOB/FLOW) visually distinguishes items.

**Example:**

```typescript
const handleRowClick = (entry: ScheduleEntryResponse) => {
  if (entry.type === 'JOB') {
    navigate(`/job-definitions?edit=${entry.id}`); // Or open modal directly
  } else {
    navigate(`/workflows/${entry.id}`);
  }
};

// In Table:
<TableBody>
  {data.entries.map((entry) => (
    <TableRow
      key={`${entry.type}-${entry.id}`}
      onClick={() => handleRowClick(entry)}
      className="cursor-pointer hover:bg-muted/50"
    >
      <TableCell>
        <Badge variant={entry.type === 'JOB' ? 'secondary' : 'default'}>
          {entry.type}
        </Badge>
      </TableCell>
      <TableCell className="font-medium">{entry.name}</TableCell>
      <TableCell>
        {entry.next_run_time
          ? formatDistanceToNow(new Date(entry.next_run_time), { addSuffix: true })
          : '—'}
      </TableCell>
      <TableCell>
        {entry.last_run_status ? (
          <Badge variant={getStatusVariant(entry.last_run_status)}>
            {entry.last_run_status}
          </Badge>
        ) : (
          <span className="text-muted-foreground text-sm">Never</span>
        )}
      </TableCell>
    </TableRow>
  ))}
</TableBody>
```

### Anti-Patterns to Avoid

- **Computing next-run time on the frontend:** Client-side date math can't interpret cron expressions. APScheduler is server-side; computation must stay there. ❌ Don't: `new Date(job.created_at) + job.interval`. ✅ Do: `trigger.get_next_fire_time(None, now)` in backend.
- **Polling /api/job-definitions + /api/workflows separately:** Creates two network calls and merges in JavaScript. ❌ Don't: `Promise.all([fetch(/api/job-definitions), fetch(/api/workflows)])`. ✅ Do: Single `/api/schedule` endpoint that merges server-side.
- **Stale next-run times:** If next-run time is fetched once and cached forever, the "Next Run" column becomes inaccurate after 30s. ✅ Do: Use `refetchInterval: 30000` to keep times fresh.
- **Hardcoded status badge colors:** Use `getStatusVariant()` from existing code (workflowStatusUtils.ts). ❌ Don't: Define new color logic. ✅ Do: Reuse proven utility.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Cron next-fire-time calculation | Custom regex/date math | APScheduler `CronTrigger.get_next_fire_time()` | Off-by-one errors on month/day logic; APScheduler handles DST, leap years, edge cases |
| Relative time formatting ("in 5m", "2h ago") | String concatenation of date parts | `date-fns formatDistanceToNow()` | Existing import in codebase; handles plurals, i18n, precision correctly |
| Merging + sorting schedule data | Custom JavaScript merge sort | Backend service method + single API endpoint | Single source of truth; avoids client-side inconsistency; reduces network calls |
| Status badge styling | New CSS classes | `getStatusVariant()` utility (Phase 150) | Consistent colors across dashboard; reuses proven color mapping |
| Table component | Custom HTML table | shadcn `Table` + `TableBody`/`Row`/`Cell` | Accessibility (ARIA), styling consistency, keyboard nav |

**Key insight:** Scheduling and time math are deceptively complex. APScheduler's cron evaluation has been battle-tested across hundreds of Python projects; client-side cron parsing is a source of subtle timezone/DST bugs. Server-side computation is non-negotiable for correctness.

---

## Common Pitfalls

### Pitfall 1: Timezone Ambiguity in next_run_time

**What goes wrong:** APScheduler's `get_next_fire_time()` returns timezone-aware datetimes. If cron was stored as UTC but the server is running in a different timezone, the next-fire-time calculation silently uses wrong reference.

**Why it happens:** APScheduler's CronTrigger constructor doesn't accept a timezone param; it uses the system default or local time. Cron expressions are inherently timezone-free.

**How to avoid:** 
- Explicitly pass `timezone.utc` when creating CronTrigger: `CronTrigger(..., timezone=timezone.utc)`.
- Ensure `now` argument to `get_next_fire_time(None, now)` is UTC: `now = datetime.now(timezone.utc)`.
- Document that all cron times are in UTC.

**Warning signs:** Next-run times drift after daylight saving time changes; "5 minute from now" fires unexpectedly 1 hour earlier.

### Pitfall 2: Invalid Cron Expression Crashes the Request

**What goes wrong:** If a ScheduledJob or Workflow has a malformed cron (e.g., "99 * * * *" or whitespace-only), `CronTrigger(...)` raises an error, crashing the entire `/api/schedule` endpoint instead of gracefully skipping bad entries.

**Why it happens:** No validation at ScheduledJob creation time (or pre-Phase 149 validation was loose). Bad crons silently exist in the DB.

**How to avoid:**
- Wrap CronTrigger construction in try/except; log warning + skip the entry.
- **Optional:** Add a DB migration to validate all existing crons; warn admins of any invalid ones.
- Frontend empty state should handle "0 entries" gracefully (no crash, clear message).

**Warning signs:** `/api/schedule` returns 500; logs show `CronTrigger invalid format` errors.

### Pitfall 3: Query Performance with Large Job/Workflow Counts

**What goes wrong:** `get_unified_schedule()` queries all active ScheduledJobs + all active Workflows without pagination or indexes. If 10,000 jobs exist, computing next-fire-time for each in a loop is slow (10K × CronTrigger operations).

**Why it happens:** No explicit pagination or lazy evaluation; every entry must be computed before returning.

**How to avoid:**
- For MVP: Assume <1000 active schedules; performance is acceptable.
- If needed later: Add DB index on (is_active, schedule_cron) for ScheduledJob; (is_paused, schedule_cron) for Workflow.
- Consider caching next-run times in the DB (precompute every 5 min) if count grows >5000.
- Frontend can add pagination later (skip/limit) if table grows unwieldy.

**Warning signs:** `/api/schedule` response time >2s; CPU spike when fetching schedule.

### Pitfall 4: Last-Run Status Lookup Inefficiency

**What goes wrong:** For each ScheduledJob, querying `SELECT Job WHERE scheduled_job_id = ? ORDER BY created_at DESC LIMIT 1` is an N+1 problem. If 1000 jobs exist, that's 1000 sequential queries.

**Why it happens:** No eager loading or batch query.

**How to avoid:**
- Use SQLAlchemy selectinload or a single batch query: `SELECT Job GROUP BY scheduled_job_id, rank by created_at DESC, take first per group`.
- Simpler approach: Load all Jobs once, group in Python (fast for <5000 rows).
- Alternatively: Defer last-run status to frontend (not required for Phase 154 spec, but simplifies backend).

**Warning signs:** `/api/schedule` response time increases linearly with job count.

### Pitfall 5: Assuming All Workflows Have a Last Run

**What goes wrong:** Code tries to access `workflow.last_run.status` without checking if last_run is None. New workflows have no runs yet.

**Why it happens:** Missing null checks; assumes database always has a related row.

**How to avoid:** Always wrap last_run_status in `Optional[str]`; frontend checks `if (entry.last_run_status) { ... } else { "Never" }`.

**Warning signs:** New workflow appears in schedule view with missing status column or crashes UI.

---

## Code Examples

Verified patterns from official sources:

### APScheduler Cron Next-Fire-Time Calculation

```python
# Source: Phase 149 scheduler_service.py + APScheduler documentation
from apscheduler.triggers.cron import CronTrigger
from datetime import datetime, timezone

cron_expr = "0 9 * * MON-FRI"  # 9 AM weekdays
parts = cron_expr.split()  # ['0', '9', '*', '*', 'MON-FRI']

trigger = CronTrigger(
    minute=parts[0],
    hour=parts[1],
    day=parts[2],
    month=parts[3],
    day_of_week=parts[4],
    timezone=timezone.utc  # CRITICAL: explicit UTC
)

now = datetime.now(timezone.utc)
next_fire = trigger.get_next_fire_time(None, now)  # Returns datetime or None
# next_fire: 2026-04-20 09:00:00+00:00 (Monday 9 AM UTC)
```

### Pydantic Model with Type Union

```python
# Source: Phase 149 models.py pattern (used in WorkflowResponse, JobResponse)
from pydantic import BaseModel, ConfigDict
from typing import Literal, Optional, List
from datetime import datetime

class ScheduleEntryResponse(BaseModel):
    id: str
    type: Literal["JOB", "FLOW"]
    name: str
    next_run_time: Optional[datetime] = None
    last_run_status: Optional[str] = None
    
    model_config = ConfigDict(from_attributes=True)

class ScheduleListResponse(BaseModel):
    entries: List[ScheduleEntryResponse]
    total: int
```

### React Query with Auto-Refetch

```typescript
// Source: Phase 150 Workflows.tsx + React Query docs
import { useQuery } from '@tanstack/react-query';
import { authenticatedFetch } from '@/auth';

export function Schedule() {
  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ['schedule'],
    queryFn: async () => {
      const res = await authenticatedFetch('/api/schedule');
      if (!res.ok) throw new Error('Failed to fetch schedule');
      return res.json();
    },
    refetchInterval: 30000, // Auto-refetch every 30s (Phase 150 established pattern)
  });

  // ... rest of component
}
```

### Date Formatting with date-fns

```typescript
// Source: Phase 150 JobDefinitions.tsx, History.tsx
import { formatDistanceToNow } from 'date-fns';

function ScheduleTable({ entries }) {
  return (
    <TableBody>
      {entries.map((entry) => (
        <TableRow key={entry.id}>
          <TableCell>
            {entry.next_run_time
              ? formatDistanceToNow(new Date(entry.next_run_time), { addSuffix: true })
              : '—'}
          </TableCell>
        </TableRow>
      ))}
    </TableBody>
  );
}
```

### Status Badge Styling with getStatusVariant()

```typescript
// Source: Phase 150 workflowStatusUtils.ts + Workflows.tsx
import { Badge } from '@/components/ui/badge';
import { getStatusVariant } from '@/utils/workflowStatusUtils';

function ScheduleTable({ entries }) {
  return (
    <TableBody>
      {entries.map((entry) => (
        <TableRow key={entry.id}>
          <TableCell>
            {entry.last_run_status ? (
              <Badge variant={getStatusVariant(entry.last_run_status)}>
                {entry.last_run_status}
              </Badge>
            ) : (
              <span className="text-muted-foreground text-sm">Never</span>
            )}
          </TableCell>
        </TableRow>
      ))}
    </TableBody>
  );
}
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Separate `/api/job-definitions` and `/api/workflows` endpoints | Single `/api/schedule` endpoint (Phase 154) | Phase 154 (this phase) | One fetch call instead of two; server-side sorting guarantees consistency |
| Sidebar: "Scheduled Jobs" entry | Rename to "Job Definitions" + add "Schedule" entry | Phase 154 | Clearer UX: CRU**D** vs. **overview**; three entries coexist |
| Client-side cron next-fire-time math | Server-side APScheduler `get_next_fire_time()` | Phase 149+ (established) | Correct timezone/DST handling; no off-by-one bugs |
| Manual page refresh for updated next-run times | `refetchInterval: 30000` (React Query) | Phase 150+ (established) | Near-real-time UI without polling spam |
| Custom badge colors per status | `getStatusVariant()` utility function | Phase 150 | Consistent styling; single source of truth |

**Deprecated/outdated:**
- **Client-side cron parsing libraries** (e.g., cronstrue): Useful for display but not calculation. Next-fire-time must be server-side.
- **Manual `/api/job-definitions` + `/api/workflows` fetching separately:** Replaced by unified endpoint (reduces network calls and client-side merge logic).

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (backend) + vitest (frontend) |
| Config file | `puppeteer/pytest.ini` + `puppeteer/dashboard/vitest.config.ts` |
| Quick run command | `cd puppeteer && pytest tests/test_scheduler.py::test_get_unified_schedule -xvs` (backend) / `cd puppeteer/dashboard && npm run test -- src/__tests__/Schedule.test.tsx` (frontend) |
| Full suite command | `cd puppeteer && pytest && cd ../puppeteer/dashboard && npm run test` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| UI-05 | GET /api/schedule returns merged JOB + FLOW entries sorted by next_run_time | unit + integration | `pytest tests/test_scheduler.py::test_get_unified_schedule_merges_jobs_workflows -xvs` | ❌ Wave 0 |
| UI-05 | GET /api/schedule filters out inactive jobs (is_active=false) and paused workflows (is_paused=true) | unit | `pytest tests/test_scheduler.py::test_get_unified_schedule_filters_inactive -xvs` | ❌ Wave 0 |
| UI-05 | GET /api/schedule computes next_run_time via APScheduler, handles invalid cron gracefully | unit | `pytest tests/test_scheduler.py::test_get_unified_schedule_invalid_cron_skip -xvs` | ❌ Wave 0 |
| UI-05 | GET /api/schedule requires jobs:read permission | integration | `pytest tests/test_main.py::test_schedule_endpoint_requires_permission -xvs` | ❌ Wave 0 |
| UI-05 | Schedule.tsx renders table with Type/Name/Next Run/Last Run Status columns | component | `npm run test -- src/__tests__/Schedule.test.tsx` | ❌ Wave 0 |
| UI-05 | Schedule.tsx row click navigates to /job-definitions (JOB) or /workflows/:id (FLOW) | component + E2E | `npm run test -- src/__tests__/Schedule.test.tsx::test_row_navigation` | ❌ Wave 0 |
| UI-05 | Schedule.tsx uses refetchInterval: 30000 for auto-refresh | unit | `npm run test -- src/__tests__/Schedule.test.tsx::test_auto_refetch` | ❌ Wave 0 |
| UI-05 | Sidebar: Schedule entry visible; "Scheduled Jobs" renamed to "Job Definitions" | component + E2E | `npm run test -- src/__tests__/MainLayout.test.tsx` / Playwright smoke test | ❌ Wave 0 |
| UI-05 | Empty state: "No active schedules" shown when schedule is empty | component | `npm run test -- src/__tests__/Schedule.test.tsx::test_empty_state` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `pytest tests/test_scheduler.py::test_get_unified_schedule -xvs && npm run test -- src/__tests__/Schedule.test.tsx` (quick backend + frontend smoke tests)
- **Per wave merge:** `cd puppeteer && pytest && cd ../puppeteer/dashboard && npm run test` (full test suite)
- **Phase gate:** Full suite green + Playwright E2E check: Schedule page loads, table renders, navigation works

### Wave 0 Gaps
- [ ] `puppeteer/tests/test_scheduler.py::test_get_unified_schedule*` — backend service method tests (3 tests: merging, filtering, cron parsing)
- [ ] `puppeteer/agent_service/main.py` — GET /api/schedule route (scaffolding exists; needs integration)
- [ ] `puppeteer/dashboard/src/__tests__/Schedule.test.tsx` — frontend component tests (5 tests: render, navigation, refetch, empty state)
- [ ] `puppeteer/dashboard/src/components/MainLayout.tsx` — sidebar nav updates (rename, new entry)
- [ ] Framework install: None required (pytest + vitest already in place)

---

## Sources

### Primary (HIGH confidence)
- **APScheduler documentation** — `CronTrigger.get_next_fire_time()` API and timezone handling (verified in Phase 149)
- **Phase 149 scheduler_service.py** — `sync_workflow_crons()` method demonstrates workflow cron scheduling with APScheduler
- **Phase 150 Workflows.tsx** — established pattern for useQuery + refetchInterval: 30000
- **date-fns documentation** — formatDistanceToNow() with addSuffix option (imported in JobDefinitions.tsx)
- **shadcn Table + Badge components** — used consistently across all views

### Secondary (MEDIUM confidence)
- **CONTEXT.md locked decisions** — Phase 154 user constraints (verified by planner in discussion phase)
- **SQLAlchemy query patterns** — used throughout agent_service for ScheduledJob + Workflow queries
- **Pydantic model patterns** — Phase 149+ established response model structure

### Tertiary (LOW confidence)
- None for this phase — all patterns are proven in existing codebase

---

## Metadata

**Confidence breakdown:**
- **Standard stack:** HIGH — APScheduler, React Query, date-fns all proven in Phase 149–150; no new dependencies
- **Architecture:** HIGH — backend service method pattern established; frontend table pattern standard across codebase
- **Pitfalls:** MEDIUM — timezone/DST edge cases documented in APScheduler; cron parsing validated in Phase 149
- **Testing:** HIGH — test patterns match existing pytest + vitest infrastructure

**Research date:** 2026-04-16  
**Valid until:** 2026-05-14 (30 days; no fast-moving dependencies; APScheduler stable)

---

**Research Complete.** Planner can now create PLAN.md files based on patterns documented here.
