# Phase 154: Unified Schedule View - Context

**Gathered:** 2026-04-16
**Status:** Ready for planning

<domain>
## Phase Boundary

Implement UI-05: a new `/schedule` page showing ScheduledJob (JOB badge) and cron-scheduled Workflow (FLOW badge) entries in a single unified table, with next-run time and last-run status. Read-only observability view — no management actions. Closes UI-05 in REQUIREMENTS.md.

</domain>

<decisions>
## Implementation Decisions

### Page placement & navigation
- New top-level **Schedule** sidebar entry at route `/schedule`
- Existing **Workflows** sidebar entry stays (workflow definition management)
- Existing **Scheduled Jobs** sidebar entry renamed to **Job Definitions** — clarifies its CRUD management purpose vs. the new Schedule overview page
- Three entries coexist: Schedule (unified overview), Job Definitions (ScheduledJob CRUD), Workflows (Workflow CRUD + DAG)

### Table structure
- Single unified flat table — one row per scheduled item, JOB and FLOW mixed together
- Default sort: next_run_time ascending (soonest-firing at top)
- Items with no cron and paused items are excluded — this is a "what will run" view, not an inventory
- Columns: **Type** (JOB/FLOW badge) | **Name** (clickable) | **Next Run** | **Last Run Status**
- Next Run displayed human-readable (e.g. "in 5m", "in 2h 14m") — not raw ISO datetime

### Backend API
- New `GET /api/schedule` endpoint — single call returns unified list
- Backend merges ScheduledJobs + cron-scheduled Workflows server-side
- `next_run_time` computed via APScheduler `get_next_fire_time()` in Python — stays server-side where APScheduler lives
- Response shape per entry: `{ id, type: "JOB"|"FLOW", name, next_run_time, last_run_status }`
- Sorted by `next_run_time` ascending in the response
- Auth: `jobs:read` permission (consistent with `/api/jobs/definitions`)
- Only includes entries with an active cron (ScheduledJob.is_active=true + cron set; Workflow.is_paused=false + schedule_cron set)

### Row interactions
- Clicking a row navigates to the item's detail page:
  - JOB → `/job-definitions` (opens edit modal for that definition)
  - FLOW → `/workflows/:id`
- Read-only view — no inline actions (no pause/enable toggle, no run-now button)
- Management actions remain on the dedicated Job Definitions and Workflows pages

### Claude's Discretion
- Exact sidebar icon for the Schedule entry
- Human-readable relative time format implementation (e.g. `date-fns formatDistanceToNow` or custom)
- Empty state copy when no active schedules exist
- Polling interval for auto-refresh (30s is the established pattern from Workflows.tsx)
- Last run status badge colors — reuse `getStatusVariant()` from existing views

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `getStatusVariant()` — status badge color mapping, used across Jobs, History, Queue views; reuse for last_run_status
- `authenticatedFetch` (`src/auth.ts`) — JWT injection for all API calls
- `useQuery` / `@tanstack/react-query` — data fetching; use with `refetchInterval: 30000` (established pattern in Workflows.tsx)
- shadcn `Badge`, `Table`, `TableRow` etc. — all available in `src/components/ui/`
- `Workflows.tsx` table pattern — columns, row click handler, pagination setup to reference
- APScheduler `trigger.get_next_fire_time(None, datetime.now(timezone.utc))` — already called in scheduler_service.py; reuse for the unified endpoint

### Established Patterns
- `AppRoutes.tsx` — add `/schedule` route with the new `Schedule` component
- Sidebar navigation: add Schedule entry, rename Scheduled Jobs → Job Definitions
- Status badge: `<Badge variant={getStatusVariant(status)}>{status}</Badge>`
- `refetchInterval: 30000` for operational views that need near-real-time freshness
- `SchedulerService` in `scheduler_service.py` — has `get_jobs()` and fire time helpers; the new endpoint is a thin service method here

### Integration Points
- `main.py` — add `GET /api/schedule` route, gated on `jobs:read`
- `scheduler_service.py` — add `get_unified_schedule()` method (or similar) that queries ScheduledJobs + Workflows, computes next_run_time for each, returns unified sorted list
- `models.py` — add `ScheduleEntryResponse` Pydantic model for the unified shape
- `AppRoutes.tsx` — add `/schedule` route
- Sidebar component (`MainLayout.tsx` or `Sidebar.tsx`) — add Schedule entry, rename existing Scheduled Jobs entry

</code_context>

<specifics>
## Specific Ideas

- The Schedule page is the operator's "at-a-glance" view: "what fires next and did the last run succeed?" — not a management interface
- JOB vs FLOW badge distinguishes item type at a glance, consistent with ROADMAP spec language
- Renaming "Scheduled Jobs" → "Job Definitions" in the sidebar aligns with the existing filename `JobDefinitions.tsx` and clarifies that the page is for managing definitions, not for viewing scheduled runs

</specifics>

<deferred>
## Deferred Ideas

- Paused/inactive items shown greyed-out with a toggle to include them — useful UX enhancement for a later pass
- Cron expression column — power user addition deferred to keep table clean
- Inline pause/enable row action — management action; belongs on dedicated pages
- Run-now button from schedule view — scope creep; Phase 154 is read-only

</deferred>

---

*Phase: 154-unified-schedule-view*
*Context gathered: 2026-04-16*
