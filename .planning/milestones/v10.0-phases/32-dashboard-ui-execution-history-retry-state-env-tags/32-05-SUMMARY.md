---
phase: 32-dashboard-ui-execution-history-retry-state-env-tags
plan: "05"
subsystem: dashboard-frontend
tags: [env-tag, nodes-view, filter, badge, react, typescript]
dependency_graph:
  requires: [32-01, 32-02]
  provides: [ENVTAG-03]
  affects: [puppeteer/dashboard/src/views/Nodes.tsx]
tech_stack:
  added: []
  patterns: [radix-select-filter, conditional-badge, useMemo-derived-list]
key_files:
  created: []
  modified:
    - puppeteer/dashboard/src/views/Nodes.tsx
    - puppeteer/dashboard/src/views/__tests__/Nodes.test.tsx
decisions:
  - "Filter dropdown only renders when uniqueEnvTags.length > 0 — no filter UI when no env tags in fleet"
  - "displayNodes derived by filter; empty state message adapts when envFilter is active"
  - "Radix Select scrollIntoView mock added to test file — jsdom does not implement it; crashes without guard"
  - "Test updated from RED placeholder (hardcoded not.toBeInTheDocument without trigger) to full fireEvent interaction test"
metrics:
  duration: 2m 27s
  completed: "2026-03-18"
  tasks_completed: 2
  files_changed: 2
---

# Phase 32 Plan 05: Env Tag Badges and Filter in Nodes View Summary

Nodes view extended with colour-coded `env_tag` badges per node card and a dynamic filter dropdown — operators can now see and filter by environment at a glance (ENVTAG-03).

## What Was Built

### Task 1 — env_tag interface field, badge helper, NodeCard badge

- `env_tag?: string` added as final field on the `Node` interface
- `getEnvTagBadgeClass(tag)` helper added after existing `getEnvBadgeColor()` — PROD → rose, TEST → amber, DEV → blue, custom → zinc
- NodeCard CardTitle renders an env_tag badge only when `node.env_tag` is truthy; badge is uppercase tag text with the colour-coded border/background
- Existing `getEnvBadgeColor()` and `node.tags` rendering untouched
- `useMemo` added to React import; Radix Select imported for Task 2 prep

### Task 2 — env filter dropdown

- `envFilter` state (default `'ALL'`) and `uniqueEnvTags` useMemo (sorted, null-safe) added to Nodes component
- `displayNodes` array filters `nodes ?? []` by `envFilter`
- Filter dropdown renders between the header row and node grid, only when `uniqueEnvTags.length > 0`
- Grid uses `displayNodes`; empty state message differentiates between "no nodes enrolled" and "no nodes match filter"
- All 5 Nodes.test.tsx tests GREEN — badge tests (3) and filter tests (2), including full Radix Select interaction test

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Nodes.test.tsx RED placeholder test updated to exercise real filter**

- **Found during:** Task 2 verification
- **Issue:** The stub test had `expect(screen.queryByText('dev-host')).not.toBeInTheDocument()` with comment "Assert failure to keep the test RED" — no actual filter interaction was triggered, so after implementation dev-host remained visible and the assertion still failed
- **Fix:** Updated test to use `fireEvent.click(trigger)` → `fireEvent.click(option)` Radix Select interaction pattern; added `window.HTMLElement.prototype.scrollIntoView = vi.fn()` mock (jsdom does not implement scrollIntoView; Radix crashes without it)
- **Files modified:** `puppeteer/dashboard/src/views/__tests__/Nodes.test.tsx`
- **Commit:** 0dfdb17

## Self-Check: PASSED

- `puppeteer/dashboard/src/views/Nodes.tsx` — FOUND (env_tag, getEnvTagBadgeClass, badge, filter dropdown all present)
- `puppeteer/dashboard/src/views/__tests__/Nodes.test.tsx` — FOUND (5/5 tests GREEN)
- Commit 3505bf4 — FOUND (Task 1)
- Commit 0dfdb17 — FOUND (Task 2 + tests)
