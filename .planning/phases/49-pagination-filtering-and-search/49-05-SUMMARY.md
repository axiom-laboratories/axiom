---
phase: 49-pagination-filtering-and-search
plan: "05"
subsystem: dashboard-frontend
tags: [pagination, cursor, filtering, csv-export, websocket, jobs-view]
dependency_graph:
  requires: ["49-04"]
  provides: ["Jobs.tsx cursor pagination", "9-axis filter bar", "CSV export UI", "WebSocket banner pattern"]
  affects:
    - puppeteer/dashboard/src/views/Jobs.tsx
tech_stack:
  added: ["date-fns (subHours, subDays for date presets)"]
  patterns: ["cursor load-more pagination", "filter chip dismissal", "WebSocket in-place patch", "blob download for CSV"]
key_files:
  created: []
  modified:
    - puppeteer/dashboard/src/views/Jobs.tsx
decisions:
  - "Export CSV button rendered in two positions: in chips row when filters are active, as ghost button otherwise — always reachable without wasting layout space"
  - "More filters Sheet used for date/node/tags/createdBy — keeps always-visible bar compact (3 controls + button) and avoids layout shift on filter expansion"
  - "fetchJobs useCallback with filtersRef avoids double-fetch on mount — initial load via useEffect([]), re-fetch on filter change via separate useEffect([filters])"
  - "Nodes fetched at mount with page_size=200 for combobox population — non-critical, silent failure on error"
metrics:
  duration: "8 min"
  completed: "2026-03-22"
  tasks_completed: 1
  files_modified: 1
---

# Phase 49 Plan 05: Jobs.tsx Frontend Refactor Summary

**One-liner:** Refactored Jobs.tsx with cursor-based load-more pagination, compact 9-axis filter bar with dismissible chips, CSV export, WebSocket new-job banner, and in-place row updates.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Refactor Jobs.tsx — cursor pagination, filter bar, chips, WebSocket banner | 5a4da19 | Jobs.tsx |

## What Was Built

### State Changes
Removed `page`, `filterText`, `filterStatus`. Added:
- `filters: FilterState` — 9-axis filter object (search, status, runtime, taskType, nodeId, tags[], createdBy, dateFrom, dateTo, datePreset)
- `nextCursor: string | null` — cursor for load-more
- `pendingNewJobs: number` — counter for the new-jobs banner
- `showMoreFilters: boolean` — controls the More Filters Sheet
- `nodes: NodeItem[]` + `nodeSearch: string` — target-node combobox population
- `tagInput: string` — chip input for the tags filter
- `loadingMore: boolean` — separate from `loading` for load-more UX

### Fetch Pattern
Single `fetchJobs({reset?, cursor?})` replaces the old two-call pattern (`/jobs` + `/jobs/count`). On `reset: true`, the job list is replaced. On cursor load-more, items are appended. Filter query params are built by a shared `buildFilterParams()` utility used by both fetchJobs and handleExport.

### Filter Bar
Always-visible row: Search Input | Status Select | Runtime Select | More filters button (with active-count badge). Triggers server-side re-fetch via `useEffect([filters])`.

### More Filters Sheet (slide-in from right)
- Date range: Last 1h / 24h / 7d / 30d preset buttons (using `date-fns subHours/subDays`) + custom datetime-local inputs
- Target node: text search box filtering the `/nodes` list with clickable rows
- Target tags: chip input (Enter or Add button) with inline dismissible chips
- Created by: plain text input
- Clear All Filters button resets to EMPTY_FILTERS

### Active Filter Chips
Derived from `filters` state — each chip shows the filter value and has an X button that clears that axis and re-fetches. Export CSV button appears in the same row when chips are visible, or as a ghost button when no chips are active.

### WebSocket Handler
- `job:created` — increments `pendingNewJobs` counter (no refetch)
- `job:updated` — patches the matching row in-place by guid using `setJobs(prev => prev.map(...))`

### Banner
Sticky banner above the table when `pendingNewJobs > 0`. Clicking it calls `fetchJobs({reset: true})` and resets the counter.

### Table Changes
- Column renamed "GUID" → "Name / ID"
- Shows `job.name` in foreground font when present; truncated guid with Hash icon when absent
- Removed client-side `jobs.filter(j => j.guid.includes(filterText))` — all filtering is now server-side

### Footer
"Showing N of M" counter (jobs.length of total) + "Load more" button (shown only when `nextCursor` is non-null).

## Deviations from Plan

### Auto-fixed Issues

None significant. One minor layout deviation: the plan specified Export CSV in the chips row only. Instead, it is rendered in both positions (chips row when active, ghost button otherwise) to ensure it is always accessible without requiring the user to apply a filter first.

## Self-Check

- [x] `puppeteer/dashboard/src/views/Jobs.tsx` updated (599 insertions, 122 deletions)
- [x] `npm run build` — clean, no TypeScript errors
- [x] `npm run lint` — no lint errors
- [x] Commit 5a4da19 exists

## Self-Check: PASSED
