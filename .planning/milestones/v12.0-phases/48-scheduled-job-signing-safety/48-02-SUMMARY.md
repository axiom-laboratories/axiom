---
phase: 48-scheduled-job-signing-safety
plan: 02
subsystem: frontend
tags: [job-definitions, draft-safety, re-sign, ux, signing]
dependency_graph:
  requires: [48-01]
  provides: [SCHED-03, SCHED-04]
  affects: [puppeteer/dashboard/src/views/JobDefinitions.tsx, puppeteer/dashboard/src/components/job-definitions/JobDefinitionList.tsx]
tech_stack:
  added: []
  patterns: [React Dialog intercept, conditional render, component composition, React Fragment]
key_files:
  created: []
  modified:
    - puppeteer/dashboard/src/views/JobDefinitions.tsx
    - puppeteer/dashboard/src/components/job-definitions/JobDefinitionList.tsx
decisions:
  - DRAFT warning modal placed as Dialog sibling in JobDefinitions.tsx rather than inside JobDefinitionModal to keep it decoupled from the full edit form lifecycle
  - Re-sign dialog implemented as a standalone component (ReSignDialog) inside JobDefinitionList.tsx so it is self-contained and co-located with the list rows that trigger it
  - React Fragment used to wrap Card + ReSignDialog in JobDefinitionList return — avoids adding a DOM wrapper div to the layout
metrics:
  duration: 3min
  completed_date: "2026-03-22"
  tasks_completed: 2
  files_modified: 2
---

# Phase 48 Plan 02: Frontend DRAFT Safety Layer Summary

Frontend safety layer for scheduled job signing — DRAFT warning modal intercepts script saves without a new signature, and an inline Re-sign dialog on DRAFT rows enables one-click reactivation.

## What Was Built

### Task 1: DRAFT Warning Modal Intercept (JobDefinitions.tsx)

- Added `showDraftWarning` and `pendingDraftSave` state variables
- Intercepted `handleSubmit` before `handleUpdate`: if script changed AND signature unchanged, captures the pending save and shows a confirmation dialog instead of saving immediately
- Clicking Cancel closes the dialog with all form edits preserved (not saved)
- Clicking "Save & Go to DRAFT" fires the captured `handleUpdate` call, transitioning the job to DRAFT
- Added `handleResign` function: sends only `signature_id` + `signature` via PATCH to avoid triggering another DRAFT transition
- Added `Dialog` (with shadcn components) to JSX as a sibling element after `ExecutionLogModal`
- Updated `JobDefinitionList` render to pass `onResign={handleResign}` and `signatures={signatures}` props

### Task 2: Re-sign Button and Dialog (JobDefinitionList.tsx)

- Added `KeyRound` to lucide-react imports
- Added shadcn Dialog, Textarea, Label, Select imports
- Extended `JobDefinition` interface with `signature_payload?: string`
- Added `Signature` interface and `signatures`/`onResign` props to `JobDefinitionListProps`
- Implemented `ReSignDialog` standalone component: shows read-only script content in a `<pre>` block, signing key Select dropdown, and base64 signature Textarea; "Re-sign & Reactivate" button is disabled until both fields are filled
- Added `resigningJob` state to control dialog open/close
- Added amber Re-sign button (`KeyRound` icon, `text-amber-500`) to DRAFT rows in the Actions cell, placed before the existing Publish button
- Wrapped `Card` and `ReSignDialog` in a React Fragment for valid JSX return

## Verification

- TypeScript build passes with no errors (`npm run build`)
- All 9 pytest scheduler service tests pass (from Phase 48 Plan 01)
- Frontend bundle size for JobDefinitions chunk: 26.31 kB (up from 23.81 kB, expected given new Dialog + component)

## Deviations from Plan

None — plan executed exactly as written.

## Self-Check

- [x] `puppeteer/dashboard/src/views/JobDefinitions.tsx` modified (showDraftWarning, handleResign, Dialog present)
- [x] `puppeteer/dashboard/src/components/job-definitions/JobDefinitionList.tsx` modified (ReSignDialog, KeyRound button, signatures/onResign props)
- [x] Commits e621bc8 and fcf2f97 exist

## Self-Check: PASSED
