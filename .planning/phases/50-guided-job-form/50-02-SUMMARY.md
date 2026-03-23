---
phase: 50-guided-job-form
plan: "02"
subsystem: frontend
tags: [react, typescript, dispatch, forms, job-submission]
dependency_graph:
  requires: [50-01]
  provides: [guided-dispatch-ui]
  affects: [Jobs.tsx, GuidedDispatchCard.tsx]
tech_stack:
  added: []
  patterns: [useMemo-payload, stale-signature-detection, chip-input-pattern, radix-select]
key_files:
  created:
    - puppeteer/dashboard/src/components/GuidedDispatchCard.tsx
  modified:
    - puppeteer/dashboard/src/views/Jobs.tsx
    - puppeteer/dashboard/src/views/__tests__/Jobs.test.tsx
decisions:
  - Stale signature detection uses prevScriptRef + useEffect watching scriptContent — triggers clear only when signature is non-empty at the time of script change
  - targetNodeId prepended to target_tags list in generatedPayload (not a separate field) — mirrors JobCreate model contract
  - Key ID dropdown fetches GET /signatures on mount with graceful degradation if empty
  - Old dispatch state and createJob function fully removed from Jobs.tsx
  - JOB-03 test stubs (ADV mode) remain as throw-not-implemented for Plan 03
metrics:
  duration: 6min
  completed: "2026-03-23"
  tasks_completed: 2
  files_modified: 3
---

# Phase 50 Plan 02: GuidedDispatchCard + Jobs.tsx Wire-Up Summary

Guided job dispatch form with structured inputs replacing raw-JSON card. Operators submit jobs through Name/Runtime/Script/Targeting/Sign form with live JSON preview.

## What Was Built

### GuidedDispatchCard component (`GuidedDispatchCard.tsx`)

Self-contained form with:
- Name input, Runtime selector (python/bash/powershell), Script textarea
- Targeting section: Node dropdown (from `nodes` prop), target tag chips (Enter/comma-to-add), capability requirement chips (key:value format)
- Sign section: Key ID dropdown (fetched from GET /signatures on mount), Signature textarea, amber stale-signature warning
- JSON preview accordion (collapsed by default, live updates via useMemo)
- Dispatch button disabled until targeting + signatureId + signature all set
- ADV placeholder button (for Plan 03)

Dispatch logic: POST /jobs with generatedPayload; calls `onJobCreated()` on success; resets form.

### Jobs.tsx updates

- `NodeItem` extended with `tags?: string[]`
- `fetchNodes` now maps `n.tags ?? []` into NodeItem
- Old dispatch state (7 vars) and `createJob` function removed
- Old raw-JSON dispatch Card JSX replaced with `<GuidedDispatchCard nodes={nodes} onJobCreated={() => fetchJobs({ reset: true })} />`
- Unused imports cleaned up (Plus, Play, Tag, Cpu, ChevronDown, ChevronUp, CardContent, Dialog imports)

### Test updates (`Jobs.test.tsx`)

JOB-01 and JOB-02 tests implemented and passing (7/11):
- Renders all form sections
- Dispatch button disabled with no targeting
- Dispatch button still disabled without signatureId (guards verified)
- POST /jobs payload structure verification
- Amber warning + signature clear on script change
- JSON preview collapsed by default
- JSON preview updates live on field change

JOB-03 stubs (ADV mode) remain as `throw new Error('not implemented')` for Plan 03.

## Commits

| Task | Commit | Description |
|------|--------|-------------|
| Task 1 | 90630e1 | feat(50-02): create GuidedDispatchCard component |
| Task 2 | d64afe6 | feat(50-02): wire GuidedDispatchCard into Jobs.tsx, remove old dispatch state |

## Deviations from Plan

None - plan executed exactly as written.

## Verification Results

- `npx vitest run src/views/__tests__/Jobs.test.tsx`: 7 pass, 4 stub-fail (JOB-03, expected)
- `npm run lint`: ok (no errors)
- `npx tsc --noEmit`: no errors for GuidedDispatchCard.tsx or Jobs.tsx

## Self-Check: PASSED

- GuidedDispatchCard.tsx: FOUND
- commit 90630e1: FOUND
- commit d64afe6: FOUND
