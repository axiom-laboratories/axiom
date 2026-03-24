---
phase: 61-lxc-environment-and-cold-start-compose
plan: 03
subsystem: testing
tags: [ed25519, licence, signing, secrets, python, cryptography]

# Dependency graph
requires:
  - phase: 61-02
    provides: EE keypair at mop_validation/secrets/ee/ee_test_private.pem
provides:
  - mop_validation/scripts/generate_coldstart_licence.py — generates 1-year Ed25519-signed EE licence and upserts AXIOM_EE_LICENCE_KEY in secrets.env
affects: [phase-64-ee-cold-start-run]

# Tech tracking
tech-stack:
  added: []
  patterns: [upsert-env-file pattern using regex multiline substitution for idempotent KEY=value updates]

key-files:
  created:
    - mop_validation/scripts/generate_coldstart_licence.py
    - mop_validation/scripts/test_generate_coldstart_licence.py
  modified: []

key-decisions:
  - "1-year expiry (not 10) to ensure Phase 64 run uses a shorter-lived licence representative of real deployments"
  - "customer_id set to axiom-coldstart-test (not axiom-dev-test) to distinguish cold-start evaluation licences"
  - "Output written directly to secrets.env AXIOM_EE_LICENCE_KEY (not a separate .env file) so Phase 64 compose picks it up from the shared secrets store"

patterns-established:
  - "upsert_secrets_env: regex multiline replace existing KEY=value, append with newline guard if absent — reusable for any secrets.env key management"

requirements-completed: [ENV-04]

# Metrics
duration: 2min
completed: 2026-03-24
---

# Phase 61 Plan 03: EE Cold-Start Licence Generator Summary

**Ed25519-signed EE test licence generator with 1-year expiry that upserts `AXIOM_EE_LICENCE_KEY` into `mop_validation/secrets.env` via idempotent regex replace**

## Performance

- **Duration:** 2 min
- **Started:** 2026-03-24T22:13:09Z
- **Completed:** 2026-03-24T22:15:51Z
- **Tasks:** 1 (TDD: RED + GREEN)
- **Files modified:** 2

## Accomplishments

- `generate_coldstart_licence.py` creates a 1-year-expiry Ed25519-signed EE licence from `mop_validation/secrets/ee/ee_test_private.pem`
- `upsert_secrets_env()` updates or creates `AXIOM_EE_LICENCE_KEY` in `secrets.env` with regex multiline replacement — idempotent, no duplicates
- 13 pytest tests cover: licence format (dot separator, compact JSON, base64url), upsert logic (create/append/replace/idempotent/newline edge case), payload values (1-year expiry, correct customer_id), and integration (exit 0 with key, idempotency across two runs)
- Script exits 1 with clear error pointing to `generate_ee_keypair.py` when private key is absent

## Task Commits

Each task was committed atomically to `mop_validation` (sister repo):

1. **Task 1: Write generate_coldstart_licence.py** - `dcbeefb` (feat) — implementation + 13 tests

## Files Created/Modified

- `mop_validation/scripts/generate_coldstart_licence.py` - EE cold-start licence generator (80 lines)
- `mop_validation/scripts/test_generate_coldstart_licence.py` - 13-test pytest suite for all behaviours

## Decisions Made

- Used `customer_id: "axiom-coldstart-test"` (not `"axiom-dev-test"`) to distinguish cold-start validation licences from developer test licences
- 1-year expiry (`365 * 86400`) as specified — not the 10-year expiry used in `generate_ee_licence.py`
- Output goes to `AXIOM_EE_LICENCE_KEY` in `secrets.env` (not `AXIOM_LICENCE_KEY`) — Phase 64 compose reads this key name

## Deviations from Plan

None - plan executed exactly as written. The script structure and content were provided verbatim in the plan's `<action>` block; implementation matched it precisely.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- `AXIOM_EE_LICENCE_KEY` is now present in `mop_validation/secrets.env` with a 1-year expiry
- Phase 64 EE cold-start compose can inject this value as `AXIOM_LICENCE_KEY` env var
- Re-run `generate_coldstart_licence.py` at any time to refresh the licence without side effects

---
*Phase: 61-lxc-environment-and-cold-start-compose*
*Completed: 2026-03-24*
