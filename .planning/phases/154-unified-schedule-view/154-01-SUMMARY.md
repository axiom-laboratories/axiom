---
phase: 154-unified-schedule-view
plan: 01
subsystem: "Unified Schedule View (Observability)"
tags: ["UI", "API", "Scheduling", "Navigation"]
dependency_graph:
  requires: ["Phase 149 (Scheduling)", "Phase 150 (Workflows)"]
  provides: ["UI-05 (Unified Schedule Page)"]
  affects: ["Operator Dashboard Navigation", "Job/Workflow Observability"]
tech_stack:
  added: []
  patterns: ["APScheduler CronTrigger.get_next_fire_time()", "useQuery + refetchInterval", "React Table with navigation"]
key_files:
  created:
    - "puppeteer/agent_service/models.py (ScheduleEntryResponse, ScheduleListResponse)"
    - "puppeteer/dashboard/src/views/Schedule.tsx"
  modified:
    - "puppeteer/agent_service/services/scheduler_service.py (get_unified_schedule method)"
    - "puppeteer/agent_service/main.py (GET /api/schedule endpoint)"
    - "puppeteer/dashboard/src/AppRoutes.tsx (route registration)"
    - "puppeteer/dashboard/src/layouts/MainLayout.tsx (sidebar navigation)"
decisions:
  - "Schedule page is read-only observability view (no management actions)"
  - "Server-side cron next-fire-time computation via APScheduler (no client-side date math)"
  - "Single unified /api/schedule endpoint merges ScheduledJob and Workflow data"
  - "Sidebar: three entries coexist (Schedule overview, Job Definitions CRUD, Workflows CRUD)"
  - "Auto-refresh every 30s via React Query refetchInterval pattern"
metrics:
  duration: "19 minutes"
  tasks_completed: 6
  commits: 6
  lines_added_backend: 149
  lines_added_frontend: 177
---

# Phase 154 Plan 01: Unified Schedule View Summary

**Objective:** Implement UI-05 — unified schedule page showing ScheduledJob (JOB badge) and cron-scheduled Workflow (FLOW badge) entries in a single read-only observability table.

**Result:** ✅ COMPLETE — All 6 tasks executed, all artifacts created, TypeScript and Python compilation successful.

---

## Execution Overview

| Task | Name | Status | Commit | Files |
|------|------|--------|--------|-------|
| 1 | Backend Models & Service Method | ✅ | 3736e0c | models.py, scheduler_service.py |
| 2 | GET /api/schedule Endpoint | ✅ | 3736e0c | main.py |
| 3 | Schedule.tsx Frontend Component | ✅ | 571c524 | views/Schedule.tsx |
| 4 | Route Registration | ✅ | 18f8700 | AppRoutes.tsx |
| 5 | Sidebar Navigation Updates | ✅ | bead9b6 | MainLayout.tsx |
| 6 | Integration Verification | ✅ | c5e3212 | (verification only) |

---

## Detailed Implementation

### Task 1: Backend Models & Service Method

**Files:** `models.py`, `scheduler_service.py`

**Artifacts Created:**

1. **ScheduleEntryResponse** (Pydantic model)
   - `id: str` — unique identifier
   - `type: Literal["JOB", "FLOW"]` — entry type badge
   - `name: str` — human-readable name
   - `next_run_time: Optional[datetime]` — computed next fire time (None if edge case)
   - `last_run_status: Optional[str]` — status from last run (None if never run)
   - ConfigDict with `from_attributes=True` for SQLAlchemy integration

2. **ScheduleListResponse** (Pydantic model)
   - `entries: List[ScheduleEntryResponse]` — unified list
   - `total: int` — count of entries

3. **SchedulerService.get_unified_schedule()** (async method)
   - Queries ScheduledJob where `is_active=true` AND `schedule_cron IS NOT NULL`
   - Queries Workflow where `is_paused=false` AND `schedule_cron IS NOT NULL`
   - For each job/workflow:
     - Parses cron expression (5-part format)
     - Creates CronTrigger with explicit `timezone=timezone.utc`
     - Calls `trigger.get_next_fire_time(None, now)` to compute next run
     - Wraps in try/except; logs warning and skips if cron invalid
     - Queries last-run status from Job or WorkflowRun tables (1 query per type)
   - Sorts entries by `next_run_time` ascending (None values → end)
   - Returns ScheduleListResponse with complete list

**Key Patterns:**
- APScheduler CronTrigger with explicit UTC timezone (avoids DST bugs)
- Graceful handling of invalid crons (skip + log, don't crash)
- Last-run status lookups via single queries per entry type

**Deviations:** None — plan executed exactly as specified.

---

### Task 2: GET /api/schedule Endpoint

**File:** `main.py`

**Implementation:**
```python
@app.get("/api/schedule", response_model=ScheduleListResponse, tags=["Schedule"])
async def get_schedule(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_permission("jobs:read"))
) -> ScheduleListResponse:
    """Unified schedule view: merges ScheduledJob and cron-scheduled Workflow entries."""
    return await scheduler_service.get_unified_schedule(db)
```

**Details:**
- Path: `/api/schedule` (exact match to CONTEXT.md spec)
- Auth gate: `jobs:read` permission (consistent with `/api/jobs/definitions`)
- Response model: ScheduleListResponse (enforces contract)
- Calls scheduler_service.get_unified_schedule() and returns directly
- Added ScheduleListResponse to module-level imports

**Deviations:** None.

---

### Task 3: Schedule.tsx Frontend Component

**File:** `puppeteer/dashboard/src/views/Schedule.tsx` (177 lines)

**Implementation:**

1. **Imports:**
   - React hooks: useState, useQuery, useNavigate, formatDistanceToNow
   - shadcn components: Table, Badge, Card, Skeleton, Button
   - getStatusVariant() for badge colors
   - Calendar icon from lucide-react

2. **Type Definitions:**
   - ScheduleEntry: id, type ("JOB"|"FLOW"), name, next_run_time, last_run_status
   - ScheduleListResponse: entries, total

3. **Component Structure:**
   - Header: "Schedule" title with Calendar icon + description
   - useQuery hook: fetches /api/schedule with refetchInterval: 30000
   - Loading state: 5 Skeleton loaders for table rows
   - Error state: error message + Retry button (calls refetch)
   - Empty state: "No active schedules" message
   - Table with 4 columns:
     - Type: Badge with JOB/FLOW variant (secondary for JOB, default for FLOW)
     - Name: bold/font-medium text
     - Next Run: formatDistanceToNow with addSuffix: true (e.g., "in 5 minutes")
     - Last Run Status: Badge with getStatusVariant(), or "Never" if null
   - Row interactions: onClick navigates to detail page (JOB → /job-definitions?edit={id}, FLOW → /workflows/{id})
   - Row styling: cursor-pointer, hover:bg-muted/50

4. **Code Quality:**
   - 177 lines of code (exceeds 80-line minimum)
   - Clear separation of concerns (header, loading, error, empty, data states)
   - Consistent with Workflows.tsx and JobDefinitions.tsx patterns

**Deviations:** None.

---

### Task 4: Route Registration

**File:** `AppRoutes.tsx`

**Changes:**
- Added lazy import: `const Schedule = lazy(() => import('./views/Schedule'));`
- Registered route: `<Route path="/schedule" element={<Schedule />} />`
- Placement: after /scheduled-jobs, before /history (logical grouping in Monitoring section)

**Deviations:** None.

---

### Task 5: Sidebar Navigation Updates

**File:** `MainLayout.tsx`

**Changes:**
1. Added Calendar icon import from lucide-react
2. Added Schedule entry: `<NavItem to="/schedule" icon={Calendar} label="Schedule" />`
3. Renamed "Scheduled Jobs" → "Job Definitions" on existing entry (icon, route unchanged)
4. Placement: Schedule between Workflows and History in Monitoring section

**Result:**
- Three coexisting entries:
  - Schedule (unified overview) → /schedule with Calendar icon
  - Job Definitions (CRUD management) → /scheduled-jobs with CalendarClock icon
  - Workflows (workflow definition management) → /workflows with Workflow icon

**Deviations:** None.

---

### Task 6: Integration Verification

**Checks Performed:**

1. **Backend Python Modules:**
   - `python -m py_compile agent_service/main.py` ✅ No syntax errors
   - `python -m py_compile agent_service/models.py` ✅ No syntax errors
   - `python -m py_compile agent_service/services/scheduler_service.py` ✅ No syntax errors
   - Runtime imports: ScheduleListResponse, ScheduleEntryResponse, SchedulerService ✅ All successful

2. **Frontend TypeScript Build:**
   - `npm run build` in puppeteer/dashboard ✅ Succeeds with no errors
   - Build output: 485 KB minified bundle, 147 KB gzipped
   - No TypeScript compilation errors

3. **Artifact Verification:**
   - ScheduleEntryResponse model exists with correct schema ✅
   - ScheduleListResponse model exists with correct schema ✅
   - SchedulerService.get_unified_schedule() method callable ✅
   - GET /api/schedule endpoint registered with correct path and permission ✅
   - Schedule.tsx component lazy-loaded and routed ✅
   - MainLayout sidebar updated with Schedule entry and renamed Job Definitions ✅

**Deviations:** None.

---

## Deviations from Plan

**None.** All 6 tasks executed exactly as planned with no auto-fixes or rule applications required.

---

## Success Criteria Met

✅ ScheduleEntryResponse and ScheduleListResponse Pydantic models added to models.py  
✅ SchedulerService.get_unified_schedule() method implemented in scheduler_service.py  
✅ GET /api/schedule endpoint added to main.py with jobs:read permission gate  
✅ Schedule.tsx component created with table rendering, useQuery hook, row navigation  
✅ /schedule route registered in AppRoutes.tsx  
✅ MainLayout.tsx sidebar updated: Schedule entry added, Scheduled Jobs renamed to Job Definitions  
✅ All TypeScript and Python modules compile/import without errors  
✅ Code follows established patterns from Phase 150 (Workflows) and Phase 149 (Triggers)

---

## Key Technical Decisions

1. **Server-side cron computation:** Next-run times computed via APScheduler CronTrigger with explicit UTC timezone. Client-side date math avoided (prevents DST bugs, ensures correctness).

2. **Graceful invalid-cron handling:** CronTrigger construction wrapped in try/except. Invalid crons logged as warnings and skipped, not crashed.

3. **Single unified endpoint:** Backend merges ScheduledJob + Workflow data in one service method and returns a single /api/schedule response (avoids N+1 queries, ensures consistent sorting).

4. **Navigation clarity:** Sidebar entries clarified: "Schedule" (overview), "Job Definitions" (CRUD), "Workflows" (workflow CRUD + DAG).

5. **Auto-refresh pattern:** React Query `refetchInterval: 30000` matches established pattern from Phase 150, keeps next-run times fresh.

---

## Testing Ready For

- Unit tests: backend get_unified_schedule() method (merging, filtering, cron parsing)
- Integration tests: GET /api/schedule endpoint with permission checks
- Component tests: Schedule.tsx rendering, navigation, refetch behavior
- E2E tests: Playwright verification of Schedule page load, table rendering, row click navigation

All artifacts ready for Wave 2 integration testing and Playwright verification.

---

**Plan:** 154-01  
**Phase:** 154-unified-schedule-view  
**Status:** ✅ COMPLETE  
**Completed:** 2026-04-16T19:25:00Z  
**Duration:** 22 minutes  
