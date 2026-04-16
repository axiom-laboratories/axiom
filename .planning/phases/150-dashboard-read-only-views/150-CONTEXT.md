# Phase 150: Dashboard Read-Only Views - Context

**Gathered:** 2026-04-16
**Status:** Ready for planning

<domain>
## Phase Boundary

Read-only dashboard UI for the v23.0 workflow engine: a DAG canvas showing workflow step graphs, live run status overlay on that canvas, run history list, and step-level log access. No editing or drag-and-drop (Phase 151). No new workflow CRUD API endpoints — Phase 150 consumes the API surface built in Phases 146–149.

</domain>

<decisions>
## Implementation Decisions

### DAG rendering library
- **Install ReactFlow now** — shared across Phase 150 (read-only) and Phase 151 (editor). Phase 150 uses `nodesConnectable={false}` and `nodesDraggable={false}`. Phase 151 re-enables those and adds editing controls on the same component. No architectural rework between phases.
- **Layout algorithm: dagre** — standard ReactFlow pairing, hierarchical Sugiyama layout, handles parallel fan-out well. Added to `package.json` alongside ReactFlow.
- **Layout direction: left-to-right** — horizontal flow for the DAG canvas.
- **Node shapes: distinct per type** — SCRIPT = rectangle, IF_GATE = diamond, AND_JOIN = hexagon/bar, OR_GATE = rounded diamond or circle, PARALLEL = fork-like shape, SIGNAL_WAIT = clock/hourglass shape. Immediately communicates node behaviour at a glance.
- **Status colors: match the Jobs screen pattern** — same `getStatusVariant` mapping: PENDING = muted/grey, RUNNING = blue (pulse animation), COMPLETED = green (`success` variant), FAILED = red (`destructive` variant), SKIPPED = muted strikethrough style, CANCELLED = grey strikethrough. Applied as node border/fill color on the DAG canvas.

### Navigation & page structure
- **New top-level sidebar entry: Workflows** — alongside Jobs, Scheduled Jobs, History. Workflows are first-class citizens.
- **Route structure with deep links:**
  - `/workflows` — list page
  - `/workflows/:id` — workflow detail (DAG canvas + run history list)
  - `/workflows/:id/runs/:runId` — specific run detail (DAG with this run's status overlay + step list)
- **List page columns:** Name, step count, last run status (Badge), last run time, trigger type (MANUAL/CRON/WEBHOOK). Enough to triage without opening detail.
- **Workflow detail page:** DAG canvas on top half, run history list below. Clicking a run navigates to `/workflows/:id/runs/:runId`.
- **Run detail page:** Same DAG canvas with status overlay for that run's WorkflowStepRuns. Step status panel/list beside or below the canvas.

### Live run status updates
- **Extend WebSocket protocol** — add two new event types to the existing WS handler in `main.py`:
  - `workflow_run_updated` — emitted when WorkflowRun status changes (RUNNING → COMPLETED/PARTIAL/FAILED/CANCELLED)
  - `workflow_step_updated` — emitted when a WorkflowStepRun status changes (step moves to RUNNING/COMPLETED/FAILED/SKIPPED/CANCELLED)
- Frontend `useWebSocket` hook receives these events and updates React Query cache or local state to re-render DAG node colors and run header without a full re-fetch.
- Backend emits these events from `advance_workflow()` and the cancel handler in `workflow_service.py` — same place the status transitions happen.

### Step log access
- **Click DAG node → slide-out right drawer** — clicking any step node on the canvas opens a drawer. No navigation away from the DAG view.
- **Drawer content for run steps (RUNNING/COMPLETED/FAILED):** Step name, node type badge, status badge (matching Jobs screen style), started_at, completed_at (duration calculated). Full job stdout/stderr log output fetched via the existing `/api/executions/{job_guid}/logs` endpoint. Reuse `ExecutionLogModal` internals inside the drawer.
- **Drawer content for unrun steps (PENDING/SKIPPED/CANCELLED):** Status message only — "This step has not run yet" / "This step was skipped" / "This step was cancelled". Show the underlying ScheduledJob name and node_type for context. No log output.
- **Drawer is read-only** — no actions in Phase 150. Phase 151 may add edit/reconfigure actions.

### Claude's Discretion
- Exact drawer component implementation (shadcn Sheet or custom slide-out)
- Sidebar navigation item placement and icon choice
- ReactFlow custom node component internal CSS/Tailwind details
- Whether dagre layout is recomputed on every render or memoized
- Exact pulse animation implementation for RUNNING nodes
- Test structure and fixtures

</decisions>

<specifics>
## Specific Ideas

- "Keep it consistent with the Jobs screen" — status badges and colors must use the same `getStatusVariant` pattern already established across Jobs, History, and Queue views. No new color system for workflow status.
- ReactFlow installed now means Phase 151 (Visual DAG Editor) starts with a working read-only canvas and layers editing on top — avoids a full rewrite of the DAG component between phases.
- The `/workflows/:id/runs/:runId` URL pattern makes runs deep-linkable — operators can share a link to a specific failed run in incident reports.

</specifics>

<code_context>
## Existing Code Insights

### Reusable Assets
- `ExecutionLogModal` (`puppeteer/dashboard/src/components/ExecutionLogModal.tsx`) — fetches and renders job output logs. Reuse its log-fetching logic inside the step drawer.
- `useWebSocket` (`puppeteer/dashboard/src/hooks/useWebSocket.ts`) — existing WS hook with auto-reconnect and exponential backoff. Extend to handle `workflow_run_updated` and `workflow_step_updated` event types.
- `getStatusVariant()` helper pattern (defined in Jobs.tsx and History.tsx) — extract to a shared utility or replicate for WorkflowRun/WorkflowStepRun status mapping. Same color/variant mapping.
- `authenticatedFetch` (`src/auth.ts`) — all API calls go through this; inject JWT automatically.
- `useQuery` / `@tanstack/react-query` — already used throughout; use for workflow list, detail, and run history queries with `refetchInterval` fallback.
- shadcn/ui Sheet component — available in `src/components/ui/` for the slide-out step log drawer.

### Established Patterns
- Table + Badge + pagination: History.tsx pattern for run history list (skip/limit pagination, status filter)
- Route structure: `AppRoutes.tsx` — add `/workflows`, `/workflows/:id`, `/workflows/:id/runs/:runId` entries
- Sidebar navigation: MainLayout.tsx likely holds sidebar links — add Workflows entry there
- Status badge pattern: `<Badge variant={getStatusVariant(status)}>{status}</Badge>` — uniform across all views
- React Query cache invalidation: existing views use `queryClient.invalidateQueries` on WS events

### Integration Points
- `AppRoutes.tsx` — add three new routes for Workflows
- `MainLayout.tsx` (or sidebar component) — add Workflows sidebar link
- `main.py` WebSocket handler — emit `workflow_run_updated` and `workflow_step_updated` events from `workflow_service.py`
- `workflow_service.py` `advance_workflow()` + `cancel_run()` — the transition points where WS events get emitted
- `package.json` — add `reactflow` (or `@xyflow/react`) and `dagre` + `@dagrejs/dagre` dependencies

</code_context>

<deferred>
## Deferred Ideas

- Workflow parameter display on the run detail (show what params were injected for this run) — useful but not critical for read-only views; could be added in Phase 151
- Cron schedule display / next-fire-time on the workflow list — informational; Phase 151 handles cron editing so deferred there
- Run filtering/search on the workflow detail page (filter runs by status, date range) — Phase 150 shows a simple run list; filtering is a UX enhancement for a later phase
- Bulk run actions (cancel multiple runs) — out of scope for read-only views

</deferred>

---

*Phase: 150-dashboard-read-only-views*
*Context gathered: 2026-04-16*
