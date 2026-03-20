---
phase: 37-licence-validation-docs-docker-hub
plan: 01
subsystem: auth
tags: [ed25519, licence, offline-validation, fastapi, pytest, tdd]

# Dependency graph
requires:
  - phase: 36-cython-so-build-pipeline
    provides: "Cython-compiled EE plugin (.so) that _parse_licence compiles into"
provides:
  - "Ed25519 offline licence key validation in ee/plugin.py (_parse_licence + _LICENCE_PUBLIC_KEY_BYTES)"
  - "Licence check block as first action in EEPlugin.register() — gates all EE features"
  - "GET /api/licence endpoint returning edition/customer_id/expires/features"
  - "6 passing unit + integration tests for licence validation"
affects:
  - phase: 37-licence-validation-docs-docker-hub
  - "axiom-ee compilation — _LICENCE_PUBLIC_KEY_BYTES must be replaced before release"

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Wire format for licence keys: base64url(json_payload).base64url(ed25519_sig) — sig verified BEFORE json.loads()"
    - "_LICENCE_PUBLIC_KEY_BYTES module-level constant — replaces placeholder 32-zero bytes before release"
    - "app.state.licence dict set ONLY after both sig verify AND expiry check pass"
    - "Dependency override pattern for require_auth in tests: use MagicMock not SQLAlchemy User()"

key-files:
  created:
    - ".worktrees/axiom-split/puppeteer/agent_service/tests/test_licence.py — 6-case licence test suite"
  modified:
    - "/home/thomas/Development/axiom-ee/ee/plugin.py — _LICENCE_PUBLIC_KEY_BYTES, _parse_licence(), licence check in register()"
    - ".worktrees/axiom-split/puppeteer/agent_service/main.py — GET /api/licence endpoint"

key-decisions:
  - "Sig is verified against raw payload bytes BEFORE json.loads() — prevents tampered payload reaching JSON parser"
  - "Expiry check is caller responsibility (register()), not _parse_licence() — _parse_licence returns dict even for expired keys (valid sig)"
  - "app.state.licence set only after BOTH signature and expiry checks pass — fail-secure design"
  - "MagicMock used in endpoint tests instead of SQLAlchemy User() — ORM rejects unknown kwargs in constructor"
  - "Separate commits in axiom-ee repo (1861f68) and worktree repo (6d6acc7) — different git repos"

patterns-established:
  - "TDD RED/GREEN: write failing tests first, commit, then implement, commit again"
  - "require_auth bypass in tests: app.dependency_overrides[require_auth] = async lambda: MagicMock()"

requirements-completed: [DIST-01]

# Metrics
duration: 22min
completed: 2026-03-20
---

# Phase 37 Plan 01: Licence Validation Summary

**Ed25519 offline licence key validation with `_parse_licence()` in EEPlugin, `_LICENCE_PUBLIC_KEY_BYTES` placeholder, licence check gating all EE startup, and `GET /api/licence` endpoint — 6 tests all green**

## Performance

- **Duration:** 22 min
- **Started:** 2026-03-20T15:56:41Z
- **Completed:** 2026-03-20T16:18:00Z
- **Tasks:** 2 (TDD RED + GREEN)
- **Files modified:** 3 (test_licence.py, ee/plugin.py, main.py)

## Accomplishments

- `_parse_licence(key_str)` implemented at module level in `ee/plugin.py`: verifies Ed25519 sig against raw payload bytes before JSON parsing; returns dict on success, None on any failure
- Licence check block added as very first code in `EEPlugin.register()`: no key → CE mode; invalid sig → disabled; expired → disabled; valid → `app.state.licence` set
- `GET /api/licence` endpoint added to `main.py`: returns `{edition: "community"}` or full enterprise metadata
- All 6 tests green: 4 unit tests for `_parse_licence`, 2 integration tests for the endpoint

## Task Commits

Each task was committed atomically (in worktree feature/axiom-oss-ee-split branch):

1. **Task 1: Write failing test stubs (RED)** - `64b6484` (test)
2. **Task 2: Implement licence validation (GREEN)** - `6d6acc7` (feat)

Additional: `ee/plugin.py` committed to axiom-ee repo: `1861f68`

**Plan metadata:** (see docs commit below)

_Note: TDD tasks have two commits per spec — test (RED) then implementation (GREEN)_

## Files Created/Modified

- `.worktrees/axiom-split/puppeteer/agent_service/tests/test_licence.py` — 6-case test suite using pytest.importorskip, session-scoped keypair fixture, monkeypatch for public key, dependency_overrides for auth
- `/home/thomas/Development/axiom-ee/ee/plugin.py` — `_LICENCE_PUBLIC_KEY_BYTES` (32-zero placeholder), `_parse_licence()`, licence check block at top of `register()`
- `.worktrees/axiom-split/puppeteer/agent_service/main.py` — `GET /api/licence` endpoint after `GET /api/features`

## Decisions Made

- Sig is verified against raw payload bytes BEFORE `json.loads()` — prevents any tampered payload reaching the JSON parser (fail-secure ordering)
- `_parse_licence()` returns a dict even for expired keys (valid sig); expiry check is `register()`'s responsibility — clean separation of concerns
- `app.state.licence` is set only after BOTH signature verification AND expiry check pass — fail-secure; any partial state would be a security bug
- `MagicMock` used in endpoint tests rather than `SQLAlchemy User()` — ORM constructors reject unknown kwargs; MagicMock is cleaner for auth bypass
- Two separate git repos: `axiom-ee` (plugin logic) and the worktree (main.py + tests)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed SQLAlchemy User() constructor in endpoint tests**
- **Found during:** Task 2 (implement — GREEN phase), running test_licence_endpoint_community
- **Issue:** Test created `User(username="test-admin", role="admin", hashed_password="x", token_version=0)` but SQLAlchemy ORM raises `TypeError: 'role' is an invalid keyword argument for User`
- **Fix:** Replaced with `MagicMock()` with attributes set manually — correct pattern for auth bypass tests
- **Files modified:** `puppeteer/agent_service/tests/test_licence.py`
- **Verification:** All 6 tests pass GREEN after fix
- **Committed in:** `6d6acc7` (Task 2 commit)

---

**Total deviations:** 1 auto-fixed (Rule 1 - Bug)
**Impact on plan:** Required for test correctness. No scope creep.

## Issues Encountered

- Pre-existing failure in `test_ee_plugin.py::test_ee_plugin_register_creates_tables` (all 15 EE tables missing with mock SQLite — unrelated to this plan's changes). Confirmed pre-existing before Task 1. Logged as out-of-scope per deviation rules.

## User Setup Required

None — no external service configuration required. Note: `_LICENCE_PUBLIC_KEY_BYTES` is a 32-zero placeholder; must be replaced with the real public key before release (documented in ee/plugin.py comment).

## Next Phase Readiness

- DIST-01 complete — EE features fully gated behind valid Ed25519 licence key
- `_LICENCE_PUBLIC_KEY_BYTES` placeholder must be replaced with real key before packaging
- Ready for Phase 37 Plans 02-03 (docs admonitions, Docker Hub CE image)

---
*Phase: 37-licence-validation-docs-docker-hub*
*Completed: 2026-03-20*
