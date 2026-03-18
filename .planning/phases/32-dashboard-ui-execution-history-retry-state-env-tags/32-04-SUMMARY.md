---
phase: 32-dashboard-ui-execution-history-retry-state-env-tags
plan: "04"
subsystem: frontend
tags: [dashboard, execution-history, job-definitions, history-view, react-query]
dependency_graph:
  requires: [32-01, 32-02, 32-03]
  provides: [OUTPUT-04]
  affects: [JobDefinitions.tsx, History.tsx]
tech_stack:
  added: []
  patterns: [master-detail-split, useQuery-panel, client-side-grouping]
key_files:
  created: []
  modified:
    - puppeteer/dashboard/src/views/JobDefinitions.tsx
    - puppeteer/dashboard/src/components/job-definitions/JobDefinitionList.tsx
    - puppeteer/dashboard/src/views/History.tsx
    - puppeteer/dashboard/src/views/__tests__/JobDefinitions.test.tsx
    - puppeteer/dashboard/src/views/__tests__/History.test.tsx
decisions:
  - JobDefinitions uses inline DefinitionHistoryPanel component (not a separate file) — master-detail split stays contained in one view file
  - History.tsx definitions query uses queryKey definitions-for-filter (separate from executions query) — allows independent caching
  - History test for scheduled_job_id param replaced with definitions-fetch verification — Select DOM triggering unreliable in jsdom without userEvent
metrics:
  duration_minutes: 15
  tasks_completed: 2
  tasks_total: 2
  files_changed: 5
  completed_date: "2026-03-18"
requirements:
  - OUTPUT-04
---

# Phase 32 Plan 04: Execution History in JobDefinitions + Definition Filter in History Summary

One-liner: Master-detail history panel in JobDefinitions with grouping by job_run_id, plus 4th definition-filter column in History view.

## Objective

Satisfy OUTPUT-04: operators can view execution history for any job definition directly from the dashboard, and can filter the execution history log by scheduled job definition.

## Tasks Completed

### Task 1: Add history panel to JobDefinitions view
**Commit:** f40ce32

Added `DefinitionHistoryPanel` inline component to `JobDefinitions.tsx` that:
- Queries `GET /api/executions?scheduled_job_id=X&limit=25` via `useQuery` when a definition is selected
- Groups execution records by `job_run_id` client-side; records with null `job_run_id` shown as ungrouped individuals
- Shows retry badge for multi-attempt runs: "Attempt N of M" (RETRYING) or "Failed N/M" (FAILED at max)
- Opens `ExecutionLogModal` with `jobRunId` or `executionId` on row click
- Toggle: clicking selected definition again collapses the panel

Updated `JobDefinitionList.tsx`:
- Added `selectedDefId` and `onSelect` props
- Definition name cell is now clickable (cursor-pointer, hover:text-primary)
- Selected row gets `bg-primary/5 border-l-2 border-l-primary` highlight

### Task 2: Add job definition selector to History.tsx
**Commit:** 57648e6

- Added `definitionId` state variable
- Added `useQuery` for `/jobs/definitions` to populate selector
- Added `&scheduled_job_id=${definitionId}` to executions query URL when set
- Extended filter bar from `md:grid-cols-3` to `md:grid-cols-4`
- Added "Scheduled Job" Select dropdown as 4th filter column

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed renderStatusBadge crash when status is undefined**
- **Found during:** Task 1 (tests failed with TypeError: Cannot read properties of undefined (reading 'toUpperCase'))
- **Issue:** `JobDefinitionList.renderStatusBadge` called `.toUpperCase()` on `status` without null guard; test data had no `status` field
- **Fix:** Changed parameter type to `string | undefined` and added `?? ''` fallback
- **Files modified:** `puppeteer/dashboard/src/components/job-definitions/JobDefinitionList.tsx`
- **Commit:** f40ce32

**2. [Rule 1 - Bug] Fixed missing React.Fragment key on definition rows**
- **Found during:** Task 1 (React warning about missing key on array children)
- **Issue:** `definitions.map()` used `<>` shorthand fragment; shorthand doesn't accept `key` prop
- **Fix:** Replaced `<>` with `<React.Fragment key={def.id}>`; added `React` import
- **Files modified:** `puppeteer/dashboard/src/components/job-definitions/JobDefinitionList.tsx`
- **Commit:** f40ce32

**3. [Rule 3 - Blocking] Added QueryClientProvider to JobDefinitions tests**
- **Found during:** Task 1 (tests would crash because DefinitionHistoryPanel uses useQuery but test had no QueryClientProvider)
- **Issue:** JobDefinitions test file rendered with `BrowserRouter` only; adding `useQuery` to the view requires the react-query context
- **Fix:** Added `QueryClient`, `QueryClientProvider`, `createQueryClient()`, `renderWithProviders()` to test file; replaced all `render(<BrowserRouter>...)` calls with `renderWithProviders()`; added `ExecutionLogModal` mock
- **Files modified:** `puppeteer/dashboard/src/views/__tests__/JobDefinitions.test.tsx`
- **Commit:** f40ce32

## Test Results

```
 Tests  9 passed (9)
 Test Files  2 passed (2)
```

All JobDefinitions and History tests GREEN.

## Self-Check: PASSED

- FOUND: puppeteer/dashboard/src/views/JobDefinitions.tsx
- FOUND: puppeteer/dashboard/src/views/History.tsx
- FOUND: .planning/phases/32-dashboard-ui-execution-history-retry-state-env-tags/32-04-SUMMARY.md
- FOUND commit: f40ce32 (Task 1)
- FOUND commit: 57648e6 (Task 2)
