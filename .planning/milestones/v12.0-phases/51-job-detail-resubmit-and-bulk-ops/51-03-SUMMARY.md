---
phase: 51-job-detail-resubmit-and-bulk-ops
plan: 03
subsystem: jobs-ui
tags: [jobs, resubmit, execution-output, node-health, drawer, frontend, backend]
dependency_graph:
  requires: [51-02]
  provides: [enriched-job-drawer, resubmit-flow, node-health-snapshot, executions-envelope]
  affects: [Jobs.tsx, ExecutionLogModal.tsx, main.py executions endpoint]
tech_stack:
  added: []
  patterns: [inline-confirm-transform, drawer-fetch-on-open, envelope-response]
key_files:
  created: []
  modified:
    - puppeteer/agent_service/main.py
    - puppeteer/dashboard/src/views/Jobs.tsx
    - puppeteer/dashboard/src/components/ExecutionLogModal.tsx
decisions:
  - "Executions endpoint changed from bare list to {records, node_health_at_execution} envelope; defensive array fallback in ExecutionLogModal ensures backward compat"
  - "GuidedFormState interface duplicated in Jobs.tsx (not imported) for decoupling — Plan 04 will consume it via the initialValues prop"
  - "Resubmit confirm pattern is inline transform (button -> Cancel/Confirm row), not a modal — lower friction for operator"
metrics:
  duration: 5min
  completed: "2026-03-23"
  tasks_completed: 2
  files_changed: 3
---

# Phase 51 Plan 03: Job Detail Enrichment and Resubmit Flow Summary

Enriched the job detail drawer with inline execution output, node health snapshot at execution time, and resubmit action buttons. Extended the executions endpoint to return a `{records, node_health_at_execution}` envelope. Updated ExecutionLogModal so the History view continues to work after the endpoint shape change.

## Tasks Completed

| # | Task | Commit | Files |
|---|------|--------|-------|
| 1 | Enrich executions endpoint and fix ExecutionLogModal fetch handler | fed2276 | main.py, ExecutionLogModal.tsx |
| 2 | Enrich JobDetailPanel — inline output, node health, resubmit buttons, edit-then-resubmit wiring | e801158 | Jobs.tsx |

## What Was Built

### Backend (main.py)
- `GET /jobs/{guid}/executions` now returns a dict envelope: `{"records": [...], "node_health_at_execution": {...} | null}`
- Fetches the job record at the start to obtain `node_id` and `started_at`
- Queries `NodeStats` for the most recent health record at or before job start time
- Node health contains `cpu`, `ram`, `recorded_at` fields

### Frontend — ExecutionLogModal.tsx
- `jobGuid` fetch branch now destructures `data.records` from the envelope with a defensive `Array.isArray` fallback for backward compat

### Frontend — Jobs.tsx
- `Job` interface extended: `originating_guid?: string`, `runtime?: string`
- `GuidedFormState` interface added locally (Plan 04 will consume it via initialValues prop)
- `JobDetailPanel` props: removed `onViewOutput` and `onRetry`; added `onResubmit` and `onEditResubmit`
- **Inline output section**: renders `output_log` lines with timestamp + stream tag + message; falls back to `stdout`/`stderr` plaintext; shows spinner while loading
- **SECURITY_REJECTED callout**: amber border/bg with plain-English message when `job.result.security_rejected === true` or status is `SECURITY_REJECTED`
- **Node health snapshot**: two-column CPU/RAM grid, shown only when `nodeHealth` is non-null
- **originating_guid row**: metadata section shows "Resubmitted from: [guid]" when present
- **Resubmit buttons**: replaces old "Re-queue Job" button; inline confirm transform (Resubmit -> Cancel/Confirm row); "Edit & Resubmit" button alongside
- Removed "View Output" button and "Re-queue Job" button from drawer
- `handleResubmit`: closes drawer, refreshes list, highlights new job with ring for 2.5s
- `handleEditResubmit`: closes drawer, populates `guidedInitialValues`, scrolls to GuidedDispatchCard
- Table rows: highlight ring applied via `highlightGuid` state (`ring-1 ring-primary/60 bg-primary/5`)
- `GuidedDispatchCard` wrapped in `ref={guidedCardRef}` div; `initialValues` prop with single `@ts-ignore` (Plan 04 will add the prop to GuidedDispatchCardProps)

## Verification

- `npm run build` — zero TypeScript errors
- `npm run test` — 8 test files, 39 tests passed (3 todo)
- `python3 -m py_compile agent_service/main.py` — syntax OK
- `grep -c "@ts-ignore" Jobs.tsx` — returns 1 (single scoped suppression for `initialValues`)
- No "View Output" or "Re-queue Job" buttons in drawer
- Executions endpoint returns `{records: [...], node_health_at_execution: {...}|null}`
- ExecutionLogModal.tsx uses `data.records` with defensive array fallback

## Deviations from Plan

None — plan executed exactly as written.

## Self-Check: PASSED

All key files found. All task commits verified (fed2276, e801158).
