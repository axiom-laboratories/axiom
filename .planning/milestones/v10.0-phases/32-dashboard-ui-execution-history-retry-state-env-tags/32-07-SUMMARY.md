---
phase: 32-dashboard-ui-execution-history-retry-state-env-tags
plan: "07"
subsystem: dashboard-frontend
tags: [attestation, badge, null-guard, tdd, container-rebuild]
dependency_graph:
  requires: [32-03]
  provides: [OUTPUT-04]
  affects: [ExecutionLogModal.tsx]
tech_stack:
  added: []
  patterns: [null-coalescing-fallback, tdd-red-green]
key_files:
  created: []
  modified:
    - puppeteer/dashboard/src/components/ExecutionLogModal.tsx
    - puppeteer/dashboard/src/components/__tests__/ExecutionLogModal.test.tsx
decisions:
  - "verified == null guard used instead of !verified so the string 'missing' passes through to map lookup while null/undefined still bail out"
  - "?? 'missing' applied at call site so DB NULL rows always render NO ATTESTATION badge without server changes"
metrics:
  duration_seconds: 162
  completed_date: "2026-03-19"
  tasks_completed: 2
  files_modified: 3
---

# Phase 32 Plan 07: Attestation Badge Null Guard Summary

**One-liner:** Hardened getAttestationBadge so DB-NULL attestation_verified always renders NO ATTESTATION badge via `verified == null` guard + `?? 'missing'` call-site fallback.

## What Was Built

Closed the UAT test 2 gap where ExecutionLogModal displayed no attestation badge for pre-Phase-30 job runs (where `attestation_verified` is NULL in the DB).

**Root cause:** `getAttestationBadge` used `if (!verified) return null` — null is falsy, so null short-circuited to return null (no badge rendered). Fix required two parts:

1. Guard changed to `verified == null` — null/undefined still bail out, but the string `"missing"` now passes through to the map
2. Call site updated to `getAttestationBadge(selected.attestation_verified ?? 'missing')` — DB NULL values become `"missing"` before reaching the function, producing the NO ATTESTATION badge

**Test update:** OUTPUT-03 test at line 72 updated from asserting NO ATTESTATION is absent to asserting it is present when `attestation_verified` is null.

**Container rebuild:** puppeteer-agent container rebuilt and restarted from Phase-30+ image so future jobs write `attestation_verified` to DB. Node containers rebuilt from latest `environment_service/` code so real attestation bundles are produced.

## Tasks Completed

| # | Name | Commit | Files |
|---|------|--------|-------|
| 1 | Harden getAttestationBadge null guard + test | ea1b3b2 | ExecutionLogModal.tsx, ExecutionLogModal.test.tsx |
| 2 | Rebuild puppeteer-agent and node containers | 931f1bf | puppets/node-compose.yaml (JOIN_TOKEN updated) |

## Decisions Made

- `verified == null` guard preferred over `!verified` — preserves the `"missing"` string path through the map while still bailing for null/undefined
- `?? 'missing'` applied at call site (not inside function) — keeps function signature clean and makes the fallback explicit at the point of use
- TDD RED-GREEN applied: test updated first to assert correct behavior, then code fixed

## Deviations from Plan

None — plan executed exactly as written. The `?? 'missing'` call-site change was explicitly described in the plan's action section.

## Success Criteria

- [x] `verified == null` guard present in ExecutionLogModal.tsx (replacing `!verified`)
- [x] All six getAttestationBadge unit tests pass (5 total in test file, all green)
- [x] OUTPUT-03 test updated: null now asserts NO ATTESTATION is visible
- [x] puppeteer-agent container running on rebuilt Phase-30+ image
- [x] Node containers running on rebuilt image

## Self-Check: PASSED

- ExecutionLogModal.tsx: FOUND
- ExecutionLogModal.test.tsx: FOUND
- Commit ea1b3b2: FOUND
- Commit 931f1bf: FOUND
