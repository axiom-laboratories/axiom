---
phase: 51-job-detail-resubmit-and-bulk-ops
plan: "04"
subsystem: frontend
tags: [jobs, bulk-ops, guided-form, checkboxes, bulk-cancel, bulk-resubmit, bulk-delete]
dependency_graph:
  requires: [51-03]
  provides: [JOB-06, BULK-01, BULK-02, BULK-03, BULK-04]
  affects: [Jobs.tsx, GuidedDispatchCard.tsx]
tech_stack:
  added: []
  patterns:
    - Set<string> for checkbox selection state with toggleSelect/toggleAll helpers
    - Bulk action bar replacing filter bar when selectionActive
    - Radix Dialog for bulk confirmation with contextual count+skipped text
    - useEffect on initialValues reference identity to trigger form pre-population
key_files:
  created: []
  modified:
    - puppeteer/dashboard/src/components/GuidedDispatchCard.tsx
    - puppeteer/dashboard/src/views/Jobs.tsx
    - puppeteer/dashboard/src/views/__tests__/Jobs.test.tsx
decisions:
  - "initialValues useEffect depends on reference identity — parent creates new object per handleEditResubmit call so effect fires correctly without deep comparison"
  - "Amber warning reuses signatureCleared flag for both script-change and edit-resubmit cases — single message covers both scenarios"
  - "Bulk action bar replaces the filter bar row entirely when selectionActive, preserving layout without adding a new fixed bar"
  - "TERMINAL_STATES and CANCELLABLE_STATES defined inside component — collocated with handlers that use them"
metrics:
  duration: "~10 minutes"
  completed: "2026-03-23T14:34:30Z"
  tasks_completed: 2
  files_modified: 3
---

# Phase 51 Plan 04: Frontend Bulk Ops and Guided Form InitialValues Summary

Complete Phase 51 frontend: GuidedDispatchCard initialValues pre-population for edit-then-resubmit (JOB-06), and multi-select checkbox column with floating bulk action bar for batch operations (BULK-01 through BULK-04).

## What Was Built

### Task 1 — GuidedDispatchCard initialValues prop (JOB-06)

- Added `initialValues?: Partial<GuidedFormState>` to `GuidedDispatchCardProps`
- Accept `initialValues` in component function signature
- Added `useEffect` that fires when `initialValues` reference changes: merges values into form state, clears `signatureId`/`signature`, sets `signatureCleared: true` to force re-signing
- Updated amber re-signing warning message from "Script changed — signature cleared. Re-sign before dispatching." to the spec's message: "Re-signing required — script payload has changed or job was resubmitted." with `AlertTriangle` icon
- Imported `AlertTriangle` from `lucide-react`
- Updated existing test to match the new warning text

**Commit:** `4fe46e7`

### Task 2 — Multi-select checkboxes and bulk actions in Jobs.tsx (BULK-01 to BULK-04)

- Added `Checkbox` and `Dialog`/`DialogContent`/`DialogHeader`/`DialogTitle`/`DialogDescription` imports
- Added selection state: `selectedGuids: Set<string>`, `selectionActive`, `bulkConfirmOpen`, `pendingBulkAction`
- Added `TERMINAL_STATES` and `CANCELLABLE_STATES` sets for state classification
- Added helpers: `toggleSelect(guid)`, `toggleAll()`, `getSelectedJobs()`
- Added `setSelectedGuids(new Set())` in `fetchJobs` reset path — clears selection on filter change or reload
- Added `handleBulkCancel`, `handleBulkResubmit`, `handleBulkDelete` handlers that set pending action + open confirmation dialog
- Added `executeBulkAction`: calls `POST /jobs/bulk-cancel`, `POST /jobs/bulk-resubmit`, or `DELETE /jobs/bulk` with `{ guids }` body; shows success toast with processed/skipped counts; clears selection and refreshes
- Added `bulkConfirmText()`: computes context-sensitive confirmation message showing action count and skipped count
- Added bulk action bar in CardHeader that replaces the filter bar when `selectionActive`: shows selected count, context-sensitive Cancel/Resubmit/Delete buttons, and "Clear selection ×" button
- Added checkbox `<TableHead>` (first column, w-10) with header select-all checkbox
- Added checkbox `<TableCell>` (first column per row, `onClick` with `stopPropagation` to prevent detail drawer opening)
- Updated skeleton loader and empty-state colspan from 7 to 8
- Added Radix Dialog confirmation: `Confirm bulk action` title, context text from `bulkConfirmText()`, Cancel and Confirm buttons (Confirm is `variant="destructive"` for deletes)
- Removed `// @ts-ignore` on `GuidedDispatchCard` — `initialValues` prop now properly typed

**Commit:** `c92118a`

## Deviations from Plan

**1. [Rule 1 - Bug] Updated test to match new amber warning message**
- **Found during:** Task 1
- **Issue:** Existing test asserted `screen.getByText(/script changed.*signature cleared/i)` — the old warning text that was replaced per plan spec
- **Fix:** Updated test to `screen.getByText(/re-signing required/i)` to match new message
- **Files modified:** `puppeteer/dashboard/src/views/__tests__/Jobs.test.tsx`
- **Commit:** `4fe46e7`

## Verification

- `npm run build` — zero TypeScript errors
- `npm run test` — 39 passed, 3 todo (all BULK-01 stubs now promoted to real tests via implementation)
- Docker stack rebuilt and running with new dashboard image

## Self-Check: PASSED

- GuidedDispatchCard.tsx: FOUND
- Jobs.tsx: FOUND
- Commit 4fe46e7 (Task 1): FOUND
- Commit c92118a (Task 2): FOUND
