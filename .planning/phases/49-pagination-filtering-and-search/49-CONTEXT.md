# Phase 49: Pagination, Filtering and Search - Context

**Gathered:** 2026-03-22
**Status:** Ready for planning

<domain>
## Phase Boundary

Server-side pagination on Jobs (cursor-based, "load more") and Nodes (page-based); 9-axis job filtering with dismissible chips; free-text search by name or GUID; CSV export of the current filtered view. No new job capabilities — this is a navigation and discoverability layer over existing job/node data.

</domain>

<decisions>
## Implementation Decisions

### Job naming (SRCH-04)
- **Backend column only in Phase 49** — add nullable `name` column to the `Job` DB model; no name field added to the existing raw-JSON dispatch form (guided form in Phase 50 is the canonical submission UX for naming)
- Names are **non-unique free labels** — duplicate names are allowed; search returns all matching jobs
- When the scheduler fires a `ScheduledJob`, the resulting `Job.name` is **auto-populated** from the `ScheduledJob` name so operators can search "nightly-backup" and find all its execution records
- `name` included in `JobResponse` from `GET /jobs`
- In the Jobs table: show name if present, otherwise show truncated GUID as now — **no permanent empty "Name" column**

### Job search (SRCH-04)
- Free-text search box matches against both `Job.name` (if set) and `Job.guid` server-side
- Search is one of the compact filter bar controls (always visible, not behind "More filters")

### Cursor-based pagination — Jobs (SRCH-01)
- Cursor is a **base64-encoded {created_at, guid} pair** — stable across new job arrivals between pages (no duplicate/skipped rows)
- Backend WHERE clause: `created_at < cursor_ts OR (created_at = cursor_ts AND guid < cursor_guid)`
- "Load more" button appends next page to the existing list; counter shows "Showing N of M total"
- Page size: 50 rows

### Page-based pagination — Nodes (SRCH-02)
- Standard prev/next page controls with current page number and total count
- Node list is small enough that offset pagination is appropriate

### Live updates with cursor pagination
- **job:created** while operator is mid-scroll: show a sticky **"N new jobs — click to refresh"** banner at the top of the Jobs list. Clicking resets to page 1 (same pattern as Twitter/X new tweet banner)
- **job:updated** (status change on a job already in the list): **in-place row update** by GUID — find the job in the current loaded list and update status/duration without disrupting scroll position or losing "load more" state. No full list refetch.

### Filter UX — layout (SRCH-03)
- **Compact filter bar** above the Jobs table:
  - Always visible: Search box | Status dropdown | Runtime dropdown | [More filters →] button
  - "More filters" panel expands to show: date range, target node combobox, target tags chip input, created-by text input
- **Active filter chips** always displayed below the filter bar regardless of which control set them — each chip is individually dismissible

### Filter UX — individual axes
- **Date range** (created_at): relative presets (Last 1h / Last 24h / Last 7d / Last 30d) + Custom (two date-time pickers). Presets are primary; Custom is secondary.
- **Target node**: searchable combobox — dropdown populated from `/nodes` API (hostname + node_id), with a text input to filter the list as the operator types
- **Target tags**: chip-style multi-tag input — type a tag, hit Enter to add as a chip; filter returns jobs that have **ANY** of the entered tags (OR logic within the tags axis)
- **Created-by**: plain text input matching against `created_by` / submitter field
- **All axes compose with AND** — each additional active filter narrows the result set

### CSV export (SRCH-05)
- **Metadata-only export**: guid, name, status, task_type, display_type, runtime, node_id, created_at, started_at, completed_at, duration_seconds, target_tags. No payload JSON, no result/stdout.
- **Respects current filter state** — export applies all active filters (status, date range, runtime, node, tags, search text, etc.)
- **Backend streaming endpoint**: `GET /jobs/export` accepts same query params as `GET /jobs`; returns `Content-Disposition: attachment; filename=jobs-export.csv`
- **Max 10,000 rows** enforced server-side to prevent memory issues
- Export button lives near the filter chips (visually connected to the current filter state)

### Claude's Discretion
- Exact migration file numbering for `Job.name` column
- Whether "N new jobs" banner is a fixed sticky header element or a floating toast-style banner
- Combobox component choice (Radix or existing select pattern in the codebase)
- Exact relative preset labels (can adjust 1h/24h/7d/30d based on what makes sense)
- `created_by` field — if not currently on the Job model, Claude decides whether to add it or search by `node_id` as a proxy

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `list_jobs` in `job_service.py:42`: Already has skip/limit/status. Needs cursor logic, plus runtime, node, tags, date, name/guid search params added. The "two-call" pattern (`/jobs` + `/jobs/count`) in Jobs.tsx can be replaced by a single cursor-aware response that includes `total` and `next_cursor`.
- `list_nodes` in `main.py:1181`: Currently returns all nodes with no pagination. Needs page/page_size params and total count added.
- `Jobs.tsx`: Already has `page`, `filterStatus`, `filterText` state. `filterText` does client-side GUID filtering — this moves server-side. The `fetchJobs` function and `useWebSocket` handler will be refactored.
- `Badge` component: established amber/coloured chip pattern (Phases 46, 48) — reuse for active filter chips
- `Sheet`/`Dialog` components: already imported in Jobs.tsx — usable for "More filters" panel
- Existing `NodeResponse` model and `/nodes` endpoint can be reused to populate the target-node combobox

### Established Patterns
- Two-step data fetch in Jobs.tsx (`/jobs` + `/jobs/count`) — candidate for consolidation into a single paginated response with `{items, total, next_cursor}`
- WebSocket `job:created` / `job:updated` events already fired from backend; `useWebSocket` hook in Jobs.tsx receives them
- `authenticatedFetch` handles all auth headers and 401 redirect

### Integration Points
- `GET /jobs`: new query params — `cursor`, `runtime`, `node_id`, `tags`, `created_by`, `date_from`, `date_to`, `search` (name+guid); response shape changes to include `next_cursor` and `total`
- `GET /jobs/export`: new endpoint, same filter params, CSV response
- `GET /jobs/count`: likely consolidated into the main list response (or kept as fallback)
- `Job` DB model: new `name` column (nullable String)
- `ScheduledJob` → `Job` creation path in `scheduler_service.py`: auto-populate `name` from `ScheduledJob` name
- `list_nodes` in `main.py`: add `page` + `page_size` query params, return `{items: [...], total: N, page: N, pages: N}`

</code_context>

<specifics>
## Specific Ideas

- Target node filter uses a **searchable combobox** — dropdown list of known nodes (hostname + node_id) with a text input to filter the list as the operator types. Not a plain dropdown, not a free-text field alone — both combined.
- "N new jobs — click to refresh" banner: same UX pattern as Twitter/X new tweet indicator. Operator stays at current scroll position until they explicitly choose to refresh.
- In-place row update for job:updated — find by GUID in the loaded list and patch the row, no scroll disruption.

</specifics>

<deferred>
## Deferred Ideas

- None — discussion stayed within phase scope

</deferred>

---

*Phase: 49-pagination-filtering-and-search*
*Context gathered: 2026-03-22*
