---
phase: 78-cli-signing-ux
plan: 01
subsystem: cli
tags: [cli, ed25519, signing, axiom-push, cryptography, credentials]

# Dependency graph
requires: []
provides:
  - "axiom-push reads AXIOM_URL (not MOP_URL) for server address"
  - "axiom-push key generate subcommand: creates Ed25519 keypair in ~/.axiom/ without openssl"
  - "axiom-push init subcommand: idempotent login + key generation + server registration"
  - "CredentialStore migrated from ~/.mop/ to ~/.axiom/ with backward-compat migration"
  - "MOPClient.list_signatures(), register_signature(), get_me() methods"
affects: [phase-79-install-docs, phase-80-homepage]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "MOPClient imported at module level in cli.py for test-patchability"
    - "Idempotent init flow: preflight GET /signatures before POST to avoid duplicate registration"
    - "Ed25519 keypair via cryptography lib (no openssl subprocess)"

key-files:
  created: []
  modified:
    - mop_sdk/cli.py
    - mop_sdk/auth.py
    - mop_sdk/client.py
    - mop_sdk/tests/test_cli.py
    - mop_sdk/tests/test_client.py

key-decisions:
  - "MOPClient imported at module level in cli.py so tests can patch mop_sdk.cli.MOPClient"
  - "do_init() also implemented in Task 2 GREEN (not a separate commit) since all init tests passed together"
  - "AXIOM_URL replaces MOP_URL — MOP_URL removed entirely from cli.py (not kept as fallback)"

patterns-established:
  - "CLI subcommand pattern: subparsers.add_parser + do_<command>() function + dispatch in main()"
  - "Idempotent registration: list first, register only if name not found"

requirements-completed: [CLI-01, CLI-02, CLI-03]

# Metrics
duration: 35min
completed: 2026-03-27
---

# Phase 78 Plan 01: CLI Signing UX Summary

**axiom-push CLI gains AXIOM_URL env var support, Ed25519 key generate subcommand, and idempotent init flow — eliminating the openssl ceremony for new users**

## Performance

- **Duration:** ~35 min
- **Started:** 2026-03-27T17:25:00Z
- **Completed:** 2026-03-27T18:03:00Z
- **Tasks:** 3 (TDD: RED → GREEN for all three)
- **Files modified:** 5

## Accomplishments
- Fixed silent AXIOM_URL mismatch: CLI now reads `AXIOM_URL` (not `MOP_URL`), so documentation examples work
- Added `axiom-push key generate` subcommand: creates `~/.axiom/signing.key` (0o600) and `~/.axiom/verification.key` using the `cryptography` library — no openssl required
- Added `axiom-push init` subcommand: idempotent flow (login check → key check → preflight GET /signatures → register if missing → print copy-paste job push command)
- Migrated `CredentialStore` default path from `~/.mop/` to `~/.axiom/` with one-time shutil migration on first use
- Added `MOPClient.list_signatures()`, `register_signature()`, and `get_me()` methods

## Task Commits

Each task was committed atomically:

1. **Task 1: Tests for AXIOM_URL fix, key generate, and client.register_signature** - `cf6e3a1` (test)
2. **Task 2+3: Implement AXIOM_URL fix, key generate, auth migration, init flow** - `f6ad4fc` (feat)

## Files Created/Modified
- `mop_sdk/cli.py` - AXIOM_URL fix, key generate + init subcommands, MOPClient module-level import
- `mop_sdk/auth.py` - CredentialStore default path ~/.axiom/ with backward-compat migration from ~/.mop/
- `mop_sdk/client.py` - Added list_signatures(), register_signature(), get_me() methods
- `mop_sdk/tests/test_cli.py` - 8 new tests: AXIOM_URL, MOP_URL ignored, key generate (3), init flow (3)
- `mop_sdk/tests/test_client.py` - 2 new tests: register_signature, list_signatures

## Decisions Made
- `MOPClient` imported at module level in cli.py (not inside `do_job`/`do_init` functions) so tests can patch it at `mop_sdk.cli.MOPClient` without complex import patching
- `do_init()` implemented in the same GREEN commit as Task 2 since the init tests written in Task 1 all passed in the same pass
- AXIOM_URL replaces MOP_URL entirely — no fallback kept to avoid confusion

## Deviations from Plan

None — plan executed exactly as written. The only minor implementation detail was moving `from .client import MOPClient` to module level in cli.py (rather than inside function bodies as the existing pattern showed for `do_job`) to ensure the mock patch target `mop_sdk.cli.MOPClient` works. This is consistent with Python testing best practices and required no structural change.

## Issues Encountered
- First test run for `test_init_skip_login` failed with `AttributeError: <module 'mop_sdk.cli'> does not have attribute 'MOPClient'` because `do_job` had a local import. Fixed by moving `MOPClient` import to module level in cli.py.

## Next Phase Readiness
- CLI is ready. Phase 79 (Install Docs Cleanup) can now document `axiom-push key generate` and `axiom-push init` as the canonical onboarding path.
- Phase 80 homepage "30-minute setup" claim is now honest — users don't need openssl.

---
*Phase: 78-cli-signing-ux*
*Completed: 2026-03-27*

## Self-Check: PASSED

- FOUND: mop_sdk/cli.py
- FOUND: mop_sdk/auth.py
- FOUND: mop_sdk/client.py
- FOUND: .planning/phases/78-cli-signing-ux/78-01-SUMMARY.md
- FOUND commit: cf6e3a1 (test RED)
- FOUND commit: f6ad4fc (feat GREEN)
