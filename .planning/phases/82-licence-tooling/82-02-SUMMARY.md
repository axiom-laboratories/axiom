---
phase: 82-licence-tooling
plan: "02"
subsystem: security
tags: [ed25519, jwt, gitleaks, ci, licence]

requires:
  - phase: 82-01
    provides: Ed25519 keypair in axiom-licenses/keys/licence.key

provides:
  - Updated _LICENCE_PUBLIC_KEY_PEM in licence_service.py matching the new keypair
  - .gitleaks.toml at repo root with allowlists for known CI dummy values
  - secret-scan CI job using gitleaks/gitleaks-action@v2 with full history scan

affects:
  - Phase 83 (job corpus signing — depends on licence verification being correct)
  - Future CI: all PRs now have secret scanning enabled

tech-stack:
  added: [gitleaks/gitleaks-action@v2]
  patterns: [Ed25519 public key hardcoded in service module, gitleaks toml allowlist for CI dummy values]

key-files:
  created:
    - .gitleaks.toml
  modified:
    - puppeteer/agent_service/services/licence_service.py
    - .github/workflows/ci.yml
    - puppeteer/tests/test_licence_service.py

key-decisions:
  - "New Ed25519 public key MCowBQYDK2VwAyEA4ceile+Eh85kcTaQuI+CZS3qlHX8f+kYYReW7x3heVk= embedded in licence_service.py; old key (VnaDTBFZ4C+X1Fk7F3FzqMbncsZ3oLvYCHVFBaGeHpA=) retired"
  - "tools/generate_licence.py removed from public repo — key generation tooling lives only in private axiom-licenses repo"
  - "gitleaks [[allowlists]] double-bracket syntax required for v8.25.0+; single [allowlist] is silently ignored"

patterns-established:
  - "Licence public key comment must reference the private axiom-licenses repo, not a local path"
  - "CI dummy values in .env sections must have corresponding .gitleaks.toml allowlist entries"

requirements-completed: [LIC-01, LIC-02]

duration: 12min
completed: 2026-03-28
---

# Phase 82 Plan 02: Licence Key Rotation and Secret Scan Summary

**New Ed25519 public key live in licence_service.py, generate_licence.py removed from public repo, gitleaks CI guard added covering full git history**

## Performance

- **Duration:** ~12 min
- **Started:** 2026-03-28T20:30:00Z
- **Completed:** 2026-03-28T20:42:00Z
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments

- Rotated `_LICENCE_PUBLIC_KEY_PEM` in `licence_service.py` from the placeholder key generated in plan 01 to the confirmed key derived from `axiom-licenses/keys/licence.key`
- Deleted `tools/generate_licence.py` from the public repo (git rm) and removed `tools/licence_signing.key` from disk
- Created `.gitleaks.toml` with `[[allowlists]]` syntax covering `ci-dummy-key` and `AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=`
- Added `secret-scan` job to `.github/workflows/ci.yml` using `gitleaks/gitleaks-action@v2` with `fetch-depth: 0`

## New Public Key

```
-----BEGIN PUBLIC KEY-----
MCowBQYDK2VwAyEA4ceile+Eh85kcTaQuI+CZS3qlHX8f+kYYReW7x3heVk=
-----END PUBLIC KEY-----
```

Round-trip verified: JWT signed with `axiom-licenses/keys/licence.key` decodes successfully against the embedded public key.

## Test Results

```
tests/test_licence_service.py — 8 passed in 0.95s
```

All 8 LIC tests pass: JWT round-trip, invalid signature CE fallback, grace period, degraded CE, clock rollback detection (CE and EE strict modes), licence status endpoint, node limit enforcement.

## Task Commits

Each task was committed atomically:

1. **Task 1: Replace public key and delete generate_licence.py** - `aa1ce29` (feat)
2. **Task 2: Add gitleaks CI guard and .gitleaks.toml** - `8097311` (feat)

## Files Created/Modified

- `puppeteer/agent_service/services/licence_service.py` — Updated `_LICENCE_PUBLIC_KEY_PEM` with new Ed25519 public key; updated comment to reference private axiom-licenses repo
- `puppeteer/tests/test_licence_service.py` — Fixed import paths from `puppeteer.agent_service...` to `agent_service...` to match project pythonpath convention
- `.gitleaks.toml` — New file: gitleaks config with `[[allowlists]]` covering both known CI dummy values
- `.github/workflows/ci.yml` — Added `secret-scan` job with `gitleaks/gitleaks-action@v2` and `fetch-depth: 0`

## Decisions Made

- New public key confirmed by deriving it from the private key file at `axiom-licenses/keys/licence.key` — matches the PEM provided in the plan execution context
- `tools/generate_licence.py` removed with `git rm` (not just `rm`) to ensure it leaves git history
- Old `tools/licence_signing.key` removed from disk (was gitignored, no history to purge)
- `[[allowlists]]` double-bracket syntax mandated in `.gitleaks.toml` — single `[allowlist]` is silently ignored in gitleaks v8.25.0+

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed incorrect import paths in test_licence_service.py**
- **Found during:** Task 1 (running `pytest tests/test_licence_service.py`)
- **Issue:** Test file created in plan 82-01 imported `from puppeteer.agent_service.services.licence_service import ...` but project's `pythonpath = ["puppeteer"]` makes `agent_service` the root package. All other tests use `from agent_service...`. Also used `patch("puppeteer.agent_service.services.licence_service.BOOT_LOG_PATH", ...)` which would fail to patch the correct module.
- **Fix:** Replaced all `from puppeteer.agent_service.` with `from agent_service.` and `patch("puppeteer.agent_service.` with `patch("agent_service.` throughout the test file.
- **Files modified:** `puppeteer/tests/test_licence_service.py`
- **Verification:** All 8 tests pass after fix
- **Committed in:** aa1ce29 (Task 1 commit)

---

**Total deviations:** 1 auto-fixed (1 bug in test import paths)
**Impact on plan:** Necessary for correctness — tests would have silently patched wrong module targets. No scope creep.

## Issues Encountered

Pre-existing collection errors in `puppeteer/tests/` (test_tools.py missing `admin_signer`, test_staging.py module name collision with agent_service/tests) are out of scope for this plan and pre-date these changes. Logged to deferred items.

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

- Phase 82 key rotation is complete: new keypair in use, old tooling removed from public repo, CI guards active
- Phase 83 (Node Validation Job Library) can proceed — signing infrastructure is settled
- Any licence JWT signed after 2026-03-28 must use `axiom-licenses/keys/licence.key`; licences signed with the old key (MCowBQYDK2VwAyEAVnaDTBFZ4C+X1Fk7F3FzqMbncsZ3oLvYCHVFBaGeHpA=) will be rejected

---
*Phase: 82-licence-tooling*
*Completed: 2026-03-28*
