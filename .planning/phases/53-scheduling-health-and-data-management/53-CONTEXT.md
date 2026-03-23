# Phase 53: Scheduling Health and Data Management - Context

**Gathered:** 2026-03-23
**Status:** Ready for planning

<domain>
## Phase Boundary

Scheduling Health panel with missed-fire detection and sparklines; overlap control and dispatch timeout per job; reusable job templates with private/shared visibility; execution record retention with nightly pruning; per-record pinning to exclude from pruning; CSV export of execution records per job. No new job capabilities beyond these.

</domain>

<decisions>
## Implementation Decisions

### Scheduling Health panel placement
- New **Health** tab on the JobDefinitions page alongside the existing Definitions tab
- Time window switcher: 24h / 7d / 30d — default loads at **24h**
- Aggregate row at top: total fired / skipped / failed counts for the window
- Per-definition rows: status icon (✓ green / ✗ red) + name + fire counts + **recharts sparkline** showing fire density timeline
- Clicking a RED/failed definition row opens a **detail drawer** (right-side Sheet, consistent with Phase 52 node drawer pattern) showing the timeline of expected vs actual fires for the window

### Missed-fire detection logic
- Backend uses **stored expected-fires log**: APScheduler hooks log each scheduled fire attempt to a new `scheduled_fire_log` table
- A fire log entry without a matching `ExecutionRecord` (by `scheduled_job_id` + `started_at`) is a candidate for LATE or MISSED
- **LATE**: expected fire time passed + no execution started within **5-minute grace period**
- **MISSED**: LATE fire with no execution record before the **next scheduled fire time**
- Fires expected during DRAFT or REVOKED state are **excluded** (not flagged as missed — intentional pause)
- Skipped-overlap fires (see below) are classified as **SKIPPED**, not missed

### Overlap control (per job definition)
- New `allow_overlap` boolean field on `ScheduledJob` (default: **false** — safe)
- If `allow_overlap=false` and the previous execution for this definition is still in progress, the new fire is **skipped** and logged with reason `"Skipped: previous run still in progress"`
- Configurable in the **JobDefinition create/edit modal**, in the scheduling section alongside the cron expression
- Skipped-overlap fires show as a distinct state in the health sparkline (not missed, not failed)

### Dispatch timeout (universal field)
- New `dispatch_timeout_minutes` optional field on **all jobs** (scheduled and ad-hoc)
- Available in: guided job submission form (Phase 50) and JobDefinition create/edit modal
- No default (blank = never auto-fail); operator sets it explicitly when needed
- Background task sweeps PENDING jobs: if `now > created_at + dispatch_timeout_minutes` and job is still PENDING → transition to FAILED with reason `"Dispatch timeout: no node picked up the job within N minutes"`
- In the health panel: a dispatch-timeout failure counts as **FAILED** (not missed)

### Job templates
- **Save as Template** button at the bottom of the guided job form, alongside the Submit button — saves current form state without submitting the job
- Templates stored in a new **`JobTemplate` DB table**: `id`, `name`, `creator_id`, `visibility` (`private` / `shared`), `created_at`, `payload` (JSON of all job fields excluding signing state)
- **Private** templates: visible only to the creator
- **Shared** templates: visible to all operators
- Visibility toggle: creator or any admin can promote private → shared or demote shared → private
- Template management: a **third tab** on the JobDefinitions page — `[Definitions] [Health] [Templates]`
  - Lists all templates visible to the current user (own private + all shared)
  - Actions per row: Load, Rename, Delete (delete restricted to creator or admin)
- Loading a template pre-populates the guided job form with all fields editable before submission

### Execution record retention
- Admin configures global **retention period in days** (default: 14) in Admin.tsx → new "Data Retention" subsection
- Admin config panel shows: `"Next pruning: ~N records eligible, M pinned (excluded)"` — live count computed from DB
- A nightly background task hard-deletes `ExecutionRecord` rows where `completed_at < now - retention_days` AND `pinned = false`
- Pin/unpin actions are **audit-logged**

### Pinning UX
- Pin toggle appears on each execution record row in the **job detail drawer** (Phase 51 established this drawer)
- Pinned records: filled pin icon + subtle **amber left border** tint on the row
- Pin/unpin via `PATCH /executions/{id}/pin` and `PATCH /executions/{id}/unpin` (admin or operator with jobs:write)

### CSV export
- Follows Phase 49's established CSV export pattern
- Download button in the job detail drawer exports all execution records for that job as CSV
- Columns: job_guid, node_id, status, exit_code, started_at, completed_at, duration_s, attempt_number, pinned

### Claude's Discretion
- Exact `scheduled_fire_log` table schema details (columns, indexes)
- Background task polling interval for dispatch timeout sweeper
- Exact sparkline colour mapping (green / amber / red per fire state)
- `JobTemplate` table migration numbering

</decisions>

<specifics>
## Specific Ideas

- Dispatch timeout is conceptually distinct from `timeout_minutes` (execution kill) — the UI should label them clearly: "Dispatch timeout" vs "Execution timeout" so operators don't confuse them
- The LATE → MISSED progression is intuitive: yellow dot (late, 5-min grace passed) → red dot (missed, next fire arrived with no execution) in the sparkline
- Overlap control default is OFF (safe) — this is important; concurrent runs on a long-running definition could cause cascading failures

</specifics>

<code_context>
## Existing Code Insights

### Reusable Assets
- `recharts` AreaChart: already used in `Nodes.tsx` for CPU/RAM sparklines — reuse for scheduling health sparklines
- `Sheet` / `SheetContent`: Phase 52 node detail drawer pattern — reuse for health detail drawer
- `JobDefinitionModal`: existing create/edit modal in `components/job-definitions/` — extend with `allow_overlap` toggle and `dispatch_timeout_minutes` input
- Phase 51 job detail drawer: execution record list already rendered there — pin toggle attaches here
- Phase 49 CSV export: established export pattern in Jobs view — reuse for per-job CSV download

### Established Patterns
- Tab switching: `JobDefinitions.tsx` already has a tabbed layout (Definitions + Create) — extend to three tabs
- Admin.tsx system config: existing section structure — add "Data Retention" subsection following same card pattern
- Audit logging: `audit()` helper in `main.py` — call for pin/unpin actions
- Background tasks: APScheduler already running via `scheduler_service.py` — add dispatch-timeout sweeper and nightly pruner as additional jobs

### Integration Points
- `ExecutionRecord` DB model: add `pinned` boolean column (migration required)
- `ScheduledJob` DB model: add `allow_overlap` boolean and `dispatch_timeout_minutes` integer columns (migration)
- `Job` DB model: add `dispatch_timeout_minutes` integer column (migration)
- New `scheduled_fire_log` table: `id`, `scheduled_job_id`, `expected_at`, `status` (fired/skipped_overlap/skipped_draft), `created_at`
- New `JobTemplate` table: full schema above
- Admin config: existing Config key/value store (already in DB) — add `execution_retention_days` key

</code_context>

<deferred>
## Deferred Ideas

- None raised during discussion — scope stayed within phase boundaries.

</deferred>

---

*Phase: 53-scheduling-health-and-data-management*
*Context gathered: 2026-03-23*
