---
phase: 85-screenshot-capture
plan: 01
subsystem: tools
tags: [playwright, screenshots, ed25519, requests, python]

# Dependency graph
requires: []
provides:
  - tools/capture_screenshots.py — operator-invoked Playwright script that seeds demo data and captures 11 named PNGs at 1440x900
  - Pre-flight check (--check flag) verifying stack reachability, JWT auth, and node enrollment
  - Output to docs/docs/assets/screenshots/ and homepage/assets/screenshots/

affects: [86-docs-accuracy-validation, homepage-screenshots-integration]

# Tech tracking
tech-stack:
  added: [playwright (sync_api), cryptography (Ed25519), requests]
  patterns:
    - Ephemeral Ed25519 keypair generated inline — no key file dependency
    - JWT injected via localStorage before Playwright navigation
    - Chromium launched with --no-sandbox (Linux requirement per CLAUDE.md)
    - networkidle wait strategy preferred over sleep
    - try/except per screenshot — partial output preferred over crash

key-files:
  created:
    - tools/capture_screenshots.py
  modified: []

key-decisions:
  - "Ephemeral keypair regenerated on each run; existing 'screenshot-seed-key' handled by registering under a timestamped unique name to ensure correct public key pairing"
  - "node_detail screenshot reuses already-loaded nodes page via URL check to avoid redundant navigation"
  - "job_detail uses filter(has_text='COMPLETED') to guarantee an interactable row exists post-seeding"

patterns-established:
  - "Pre-flight check pattern: stack reachable → JWT login → node enrollment — call before any destructive/capture operation"
  - "load_secrets() line-by-line parser: skip blanks and # comments, partition on first = — reusable for other operator scripts"
  - "save_screenshot() writes bytes to all out_dirs at once — single screenshot() call, multiple path writes"

requirements-completed:
  - SCR-01

# Metrics
duration: 25min
completed: 2026-03-29
---

# Plan 85-01: Screenshot Capture Script Summary

**Playwright operator script with preflight check, ephemeral Ed25519 seeding, and 11-view PNG capture at 1440x900 writing to docs and homepage asset directories**

## Performance

- **Duration:** ~25 min
- **Started:** 2026-03-29T15:25:00Z
- **Completed:** 2026-03-29T15:50:00Z
- **Tasks:** 3
- **Files modified:** 1 (created)

## Accomplishments
- `tools/capture_screenshots.py` fully implemented with `--url` and `--check` flags
- Pre-flight check verifies stack reachability, JWT login, and node enrollment before proceeding
- `seed_demo_data()` generates ephemeral Ed25519 keypair, registers public key, dispatches 4 signed jobs (mix of hello, platform-info, intentional-failure, sleep), polls for 2 terminal states
- `capture_screenshots()` navigates 11 routes in headless Chromium at 1440x900 with per-capture try/except

## Task Commits

Each task was committed atomically:

1. **Task 1: Script skeleton with argument parsing and pre-flight check** - `aab0ada` (feat)
2. **Task 2: Data seeding — ephemeral keypair + job dispatch** - `0782207` (feat)
3. **Task 3: Screenshot capture — 11 views** - `c2684bd` (feat)

## Files Created/Modified
- `tools/capture_screenshots.py` — complete operator script: secrets loader, preflight check, demo data seeding, 11-view Playwright capture

## Decisions Made
- Existing "screenshot-seed-key" collision handled by registering a fresh timestamped key so the ephemeral private key matches the registered public key on each run
- URL-based navigation used throughout (not nav link clicks) — more reliable with Playwright per CLAUDE.md guidance
- `node_detail.png` reuses the nodes page if already loaded to avoid redundant navigation

## Deviations from Plan

None - plan executed exactly as written. The timestamped key fallback was a minor implementation detail to handle the collision case described in the plan notes.

## Issues Encountered
- Backend test suite has pre-existing collection errors in `test_intent_scanner.py` and `test_lifecycle_enforcement.py` (module path issues unrelated to this plan). Verified no regressions by confirming our changes touch zero backend files.

## User Setup Required

None - no external service configuration required beyond the stated prerequisites (stack running, node enrolled, `pip install playwright requests && playwright install chromium`).

## Next Phase Readiness
- Script is ready for operator use: `python tools/capture_screenshots.py --check` validates the stack, full run produces 11 PNGs
- Phase 86 (Docs Accuracy Validation) can reference the screenshots once captured
- Homepage and docs markdown integration (SCR-02, SCR-03) are not in this plan — deferred to the phase 85 follow-on plans if planned

---
*Phase: 85-screenshot-capture*
*Completed: 2026-03-29*
