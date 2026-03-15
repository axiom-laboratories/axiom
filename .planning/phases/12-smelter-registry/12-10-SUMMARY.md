---
phase: 12-smelter-registry
plan: 10
subsystem: foundry/smelter
tags: [smelter, enforcement, mirror-status, SMLT-04, gap-closure]
dependency_graph:
  requires: [12-08, 12-09]
  provides: [SMLT-04 gap closed]
  affects: [foundry_service, test_smelter]
tech_stack:
  added: []
  patterns: [enforcement_mode gate, call-order mock routing]
key_files:
  modified:
    - puppeteer/agent_service/services/foundry_service.py
    - puppeteer/tests/test_smelter.py
decisions:
  - "Mirror-status 403 gated by enforcement_mode == STRICT; WARNING mode logs warning and sets is_compliant=False (consistent with unapproved-package WARNING path)"
  - "Test mock routing uses call-order counter (blueprint_call_count) instead of literal value search in SQLAlchemy stmt string — bound parameters make literal search unreliable"
metrics:
  duration: 6 minutes
  completed: 2026-03-15T18:25:45Z
  tasks_completed: 2
  files_modified: 2
---

# Phase 12 Plan 10: SMLT-04 Mirror-Status Enforcement Gate Summary

Gate the mirror-status 403 check behind `enforcement_mode == 'STRICT'` and replace the bare `pass` stub with async assertions covering both WARNING and STRICT mirror-status paths.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Gate mirror-status 403 behind STRICT mode | f11c4fd | foundry_service.py |
| 2 | Replace bare pass stub with SMLT-04 assertions | 470ed23 | test_smelter.py |

## What Was Built

**foundry_service.py** (lines 79-85): The unconditional `raise HTTPException(403)` for non-MIRRORED ingredients was wrapped with an `enforcement_mode == "STRICT"` guard. In WARNING mode, a warning is logged and `tmpl.is_compliant` is set to False — mirroring the existing unapproved-package WARNING path directly above it.

**test_smelter.py**: `test_smelter_enforcement_config_stub` replaced from a bare `pass` stub with a full async test that:
1. Sets up a blueprint with `python=["requests"]` and an `ApprovedIngredient` with `mirror_status="PENDING"`
2. Mocks `SmelterService.validate_blueprint` to return `[]` (all packages approved — isolates mirror-status path)
3. Asserts WARNING mode does NOT raise HTTPException and sets `tmpl.is_compliant = False`
4. Asserts STRICT mode raises `HTTPException(403)` with "mirror" in the detail message

## Verification

All 7 tests in `puppeteer/tests/test_smelter.py` pass:
- test_smelter_service_exists_stub PASSED
- test_vulnerability_scan_integration_stub PASSED
- test_validate_blueprint_logic PASSED
- test_foundry_enforcement_functional PASSED
- test_foundry_enforcement_strict_stub PASSED
- test_smelter_enforcement_config_stub PASSED  ← was bare `pass`, now has real assertions
- test_template_compliance_badging_stub PASSED

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed SQLAlchemy bound-parameter mock routing in test**
- **Found during:** Task 2 (test execution)
- **Issue:** The plan spec used `"rt2" in str(stmt)` to distinguish runtime vs network blueprint queries. SQLAlchemy compiles WHERE clauses with bound parameters (e.g. `WHERE blueprints.id = :id_1`) — literal values like "rt2" do not appear in the compiled SQL string. Both blueprint calls returned `nw_bp`, making `rt_def = {}` and skipping the mirror-status loop entirely.
- **Fix:** Replaced literal-search routing with a `blueprint_call_count` counter: first blueprint call returns `rt_bp`, second returns `nw_bp`. This correctly routes calls to the order `build_template` makes them.
- **Files modified:** `puppeteer/tests/test_smelter.py`
- **Commit:** 470ed23

## SMLT-04 Gap Status

Closed. Both conditions from `VERIFICATION.md` are now satisfied:
1. `foundry_service.py` no longer raises 403 unconditionally for non-MIRRORED ingredients — the check is gated by `enforcement_mode == "STRICT"`
2. `test_smelter_enforcement_config_stub` has real assertions that pass, covering both WARNING (proceeds, sets is_compliant=False) and STRICT (raises 403) modes

## Self-Check: PASSED

- [x] `puppeteer/agent_service/services/foundry_service.py` modified and contains `if enforcement_mode == "STRICT":` guard at mirror-status raise
- [x] `puppeteer/tests/test_smelter.py` contains `test_smelter_enforcement_config_stub` with `assert tmpl.is_compliant is False` and `assert excinfo.value.status_code == 403`
- [x] Commit f11c4fd exists (Task 1)
- [x] Commit 470ed23 exists (Task 2)
- [x] All 7 smelter tests pass
