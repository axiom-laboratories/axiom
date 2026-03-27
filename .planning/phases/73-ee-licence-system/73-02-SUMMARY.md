---
phase: 73-ee-licence-system
plan: 02
subsystem: auth
tags: [jwt, eddsa, ed25519, licence, ee, pyjwt, clock-rollback]

# Dependency graph
requires:
  - phase: 73-01
    provides: "7 failing RED tests for all LIC requirements"
provides:
  - "LicenceState dataclass + LicenceStatus enum (VALID, GRACE, EXPIRED, CE)"
  - "load_licence() — reads env/file, verifies EdDSA JWT, computes state, CE fallback"
  - "_compute_state() — grace period arithmetic from exp + grace_days"
  - "check_and_record_boot() — hash-chained boot.log clock rollback detection"
  - "tools/generate_licence.py — offline CLI to produce EdDSA-signed JWT licence keys"
affects: [73-03]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "PyJWT (import jwt) for EdDSA JWT encode/decode — NOT python-jose which lacks OKP support in 3.5.0"
    - "LicenceState as dataclass stored on app.state — not module-level mutable global, for test isolation"
    - "verify_exp=False in jwt.decode() — expiry handled manually via grace_days arithmetic"
    - "Hardcoded _LICENCE_PUBLIC_KEY_PEM bytes constant — operators cannot replace verification key"
    - "tools/ directory: standalone offline CLI with no agent_service imports"

key-files:
  created:
    - puppeteer/agent_service/services/licence_service.py
    - tools/generate_licence.py
    - tools/__init__.py
  modified: []

key-decisions:
  - "Placed licence_service.py in services/ (not ee/) — licence validation must live in CE code per STATE.md to prevent partial EE route registration"
  - "Boot log path BOOT_LOG_PATH = Path('secrets/boot.log') as module-level constant, patchable in tests"
  - "tools/licence_signing.key gitignored — private key must not be committed; document as manual bootstrap"
  - "pytest run from repo root (not puppeteer/) — test_licence_service.py uses puppeteer.agent_service.* import path"

patterns-established:
  - "Pattern: licence key fallback chain — AXIOM_LICENCE_KEY env var first, then secrets/licence.key file"
  - "Pattern: CE fallback on any JWT error — no crash, log WARNING, return _ce_state()"
  - "Pattern: clock rollback via ISO8601 lexicographic comparison with UTC timestamps"

requirements-completed: [LIC-01, LIC-02, LIC-03, LIC-04, LIC-05]

# Metrics
duration: 4min
completed: 2026-03-27
---

# Phase 73 Plan 02: Licence Service Implementation Summary

**EdDSA JWT licence validation service (LicenceState + load_licence) and offline key generator CLI, turning LIC-01 through LIC-05 GREEN**

## Performance

- **Duration:** ~4 min
- **Started:** 2026-03-27T08:18:24Z
- **Completed:** 2026-03-27T08:22:00Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments

- Created `puppeteer/agent_service/services/licence_service.py` with full LicenceState dataclass, load_licence(), _compute_state(), check_and_record_boot()
- Created `tools/generate_licence.py` as a standalone offline CLI — no agent_service imports, pure stdlib + PyJWT + cryptography
- 5 of 7 LIC tests GREEN (LIC-01 through LIC-05); LIC-06 and LIC-07 remain RED as expected (plan 03 integration)

## Task Commits

1. **Task 1: Implement licence_service.py** - `d6c3f19` (feat)
2. **Task 2: Implement tools/generate_licence.py** - `9df7b91` (feat)

## Files Created/Modified

- `puppeteer/agent_service/services/licence_service.py` — LicenceState, LicenceStatus, load_licence(), _compute_state(), check_and_record_boot(), _decode_licence_jwt(), _ce_state(), _read_licence_raw()
- `tools/generate_licence.py` — offline EdDSA JWT licence key generator CLI
- `tools/__init__.py` — empty package init

## Decisions Made

- `tools/licence_signing.key` is gitignored (correct for private keys) — the file exists locally but is not committed. Operators must run `python tools/generate_licence.py --generate-keypair` during bootstrap.
- pytest must be run from the repo root (`python3 -m pytest puppeteer/tests/...`), not `cd puppeteer && pytest`, because the test file imports `puppeteer.agent_service.*` which requires the parent of `puppeteer/` to be in sys.path.
- The hardcoded `_LICENCE_PUBLIC_KEY_PEM` in `licence_service.py` uses the Ed25519 public key generated during task 1 execution. Plan 03 does not need to regenerate the keypair.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

- **pytest run path:** Running `cd puppeteer && pytest tests/test_licence_service.py` fails with `ModuleNotFoundError: No module named 'puppeteer.agent_service'` because the test file imports via the `puppeteer.` prefix. Fixed by running from repo root: `python3 -m pytest puppeteer/tests/test_licence_service.py`. Not a code bug — the test was written this way intentionally in plan 01.
- **tools/licence_signing.key gitignored:** The `tools/*.key` pattern matches in `.gitignore`. The private key file exists on disk but cannot be committed. Documented as expected — private keys should never be in version control.

## User Setup Required

To use the licence system, operators must:
1. The private key `tools/licence_signing.key` is already generated locally (re-run `python tools/generate_licence.py --generate-keypair` if lost)
2. Issue licence: `python tools/generate_licence.py --key tools/licence_signing.key --customer-id ACME --tier ee --node-limit 10 --expiry 2027-01-01 --issued-to "ACME Corp"`
3. Set `AXIOM_LICENCE_KEY=<token>` env var or write token to `secrets/licence.key`

## Next Phase Readiness

- Plan 03 can integrate `load_licence()` into `main.py` lifespan, wire `GET /api/licence` endpoint, and add node limit guard to `enroll_node()` — all 5 integration points are ready
- LIC-06 (`/api/licence` route) and LIC-07 (`enroll_node` 402) will be turned GREEN by plan 03
- The `_pub_key` constant in `licence_service.py` is testable via `unittest.mock.patch("puppeteer.agent_service.services.licence_service._pub_key", test_pub_key)` as demonstrated in `test_invalid_signature_falls_to_ce`

## Self-Check: PASSED

- `puppeteer/agent_service/services/licence_service.py` — FOUND
- `tools/generate_licence.py` — FOUND
- `tools/__init__.py` — FOUND
- commit `d6c3f19` — FOUND
- commit `9df7b91` — FOUND

---
*Phase: 73-ee-licence-system*
*Completed: 2026-03-27*
