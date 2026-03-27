---
phase: 74-fix-ee-licence-display
plan: "01"
subsystem: frontend
tags: [tdd, licence, ee, react, typescript]
dependency_graph:
  requires: []
  provides: [corrected-useLicence-hook, ee-badge-colour-states, grace-expired-banner, admin-licence-section]
  affects: [puppeteer/dashboard/src/hooks/useLicence.ts, puppeteer/dashboard/src/views/Admin.tsx, puppeteer/dashboard/src/layouts/MainLayout.tsx]
tech_stack:
  added: []
  patterns: [tdd-red-green, vi-mock-hook, react-query-renderHook]
key_files:
  created:
    - puppeteer/dashboard/src/hooks/__tests__/useLicence.test.ts
    - puppeteer/dashboard/src/views/__tests__/Admin.test.tsx
    - puppeteer/dashboard/src/layouts/__tests__/MainLayout.test.tsx
  modified:
    - puppeteer/dashboard/src/hooks/useLicence.ts
    - puppeteer/dashboard/src/views/Admin.tsx
    - puppeteer/dashboard/src/layouts/MainLayout.tsx
decisions:
  - isEnterprise computed as status !== 'ce' — valid/grace/expired all count as EE-licenced
  - formatExpiryDate helper uses days_until_expiry to compute a display date
  - STATUS_BADGE and STATUS_LABEL lookup maps for clean status badge rendering
  - Banner placed between <header> and <main> inside the flex column
  - Test 6 uses getAllByText for Community because both Edition and Status rows render it for CE
metrics:
  duration: "3m 8s"
  completed: "2026-03-27T11:54:58Z"
  tasks_completed: 2
  files_modified: 6
---

# Phase 74 Plan 01: Fix EE Licence Display Summary

Fixed the EE licence frontend by rewriting `useLicence.ts` to match the actual `/api/licence` backend response, then updating both callers (Admin.tsx, MainLayout.tsx) with new UI elements.

## What Was Built

The `useLicence` hook was written against a fabricated interface (`edition`, `expires`, `features`) that never matched the backend. All three fields were absent from the real response, causing `licence.edition === 'enterprise'` to always be false — the EE badge always showed "CE", Admin never showed expiry or tier correctly.

### Changes

**`useLicence.ts` — full rewrite:**
- New `LicenceInfo` interface with six backend fields: `status`, `tier`, `days_until_expiry`, `node_limit`, `customer_id`, `grace_days`
- Computed `isEnterprise` field: `status !== 'ce'` (valid/grace/expired are all EE-licenced)
- CE_DEFAULTS fallback uses correct zero-value shape

**`Admin.tsx` LicenceSection — rewrite:**
- `STATUS_BADGE` and `STATUS_LABEL` lookup maps for four status states
- `formatExpiryDate(days)` helper computes human-readable date from days_until_expiry
- Expiry row: shows 'Expired' when status is 'expired', date string otherwise
- Node limit row: visible only when `isEnterprise && node_limit > 0`
- Features chip list: removed entirely
- CE upgrade hint: preserved for `!isEnterprise`

**`MainLayout.tsx` — badge + banner:**
- Sidebar badge: `expired` → red, `grace` → amber, `isEnterprise` → indigo, else zinc
- `AlertTriangle` added to lucide-react imports
- Grace/expired banner rendered before `<main>` with status-appropriate message and colour

## Test Coverage

15 new tests across 3 files (all pass):

| File | Tests | Coverage |
|------|-------|----------|
| `useLicence.test.ts` | 4 | Field mapping, isEnterprise for all 4 status values |
| `Admin.test.tsx` | 6 | Status badges, expiry text, node_limit row, CE hint, no features list |
| `MainLayout.test.tsx` | 5 | Badge colour per status, grace/expired banner presence/absence |

Full suite: 56 tests passing (12 test files).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Test 6 used getByText for 'Community' which matched two elements**
- **Found during:** Task 2 (GREEN phase)
- **Issue:** STATUS_LABEL maps `ce` to `'Community'`, so both the Edition badge and the Status badge render 'Community' for CE status — `getByText` throws on multiple matches
- **Fix:** Changed to `getAllByText('Community')` with `length >= 1` assertion in Admin.test.tsx
- **Files modified:** `puppeteer/dashboard/src/views/__tests__/Admin.test.tsx`
- **Commit:** 5b75160

## Self-Check: PASSED

All created/modified files exist and both commits are present:
- `370e86c` — RED tests committed
- `5b75160` — GREEN implementation committed
