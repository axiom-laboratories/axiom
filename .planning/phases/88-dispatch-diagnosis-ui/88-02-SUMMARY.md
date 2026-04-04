---
phase: 88-dispatch-diagnosis-ui
plan: 02
status: complete
completed_by: retroactive-summary
---

## What Was Done

Integrated dispatch diagnosis into the Jobs view (`Jobs.tsx`). PENDING and stuck-ASSIGNED jobs show inline diagnosis text beneath their status badge in the job drawer. Diagnosis auto-refreshes on `node:updated`, `node:heartbeat`, and `job:updated` WebSocket events while the drawer is open.

The implementation uses per-job `authenticatedFetch` to the single-job diagnosis endpoint rather than the bulk polling approach originally planned — functionally equivalent, triggered reactively via WebSocket events instead of interval polling.

## Artifacts

| File | Change |
|------|--------|
| `puppeteer/dashboard/src/views/Jobs.tsx` | Inline diagnosis display in job drawer, reactive refresh on WS events |

## Deviations

- Uses single-job `GET /jobs/{guid}/dispatch-diagnosis` on drawer open + WS events instead of bulk polling with `diagnosisCache`. The bulk endpoint exists but the UI opted for a simpler reactive pattern.
