---
phase: 78-cli-signing-ux
verified: 2026-03-27T19:00:00Z
status: passed
score: 10/10 must-haves verified
re_verification: false
---

# Phase 78: CLI Signing UX Verification Report

**Phase Goal:** A new user can generate a signing keypair and register it with the server using only the `axiom-push` CLI, with no openssl ceremony required
**Verified:** 2026-03-27T19:00:00Z
**Status:** passed
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Running axiom-push with AXIOM_URL set connects to the correct server | VERIFIED | `cli.py:65` reads `os.getenv("AXIOM_URL")`; MOP_URL entirely absent; `test_axiom_url_env_var` passes |
| 2 | axiom-push key generate produces signing.key and verification.key in ~/.axiom/ without openssl | VERIFIED | `do_key_generate()` in `cli.py:79-111` uses cryptography lib; `test_key_generate_creates_files` passes with 0o600 permission check |
| 3 | axiom-push key generate refuses to overwrite existing keys without --force | VERIFIED | `cli.py:85-87` guards on `priv_path.exists() and not force`; `test_key_generate_refuses_overwrite` passes with sys.exit(1) |
| 4 | axiom-push init completes login, key generation, and registration in one idempotent flow | VERIFIED | `do_init()` in `cli.py:114-174`; preflight GET /signatures before POST; `test_init_skip_login`, `test_init_full_flow`, `test_init_idempotent_existing_key` all pass |
| 5 | axiom-push init output shows the exact ready-to-copy job push command with real Key ID | VERIFIED | `cli.py:168` prints `axiom-push job push --script hello.py --key {priv_path} --key-id {key_id}`; `test_init_full_flow` asserts "axiom-push job push" in stdout |
| 6 | first-job.md presents axiom-push init as the primary getting-started path | VERIFIED | first-job.md line 23: `axiom-push init`; appears 2 times in Quick Start section as Step 1 |
| 7 | AXIOM_URL export appears as the first line in the Quick Start section | VERIFIED | first-job.md line 17: `export AXIOM_URL=https://your-orchestrator:8001` before any command |
| 8 | axiom-push key generate is documented as the standalone alternative to init | VERIFIED | first-job.md lines 43-56: collapsible `??? tip` block with `axiom-push key generate` |
| 9 | openssl ceremony is preserved but demoted to a collapsible fallback | VERIFIED | first-job.md has 4 openssl occurrences, all within the "Manual Setup" section (line 121+) |
| 10 | The ready-to-copy job push command example uses real flag names | VERIFIED | first-job.md line 38: `axiom-push job push --script hello.py --key ~/.axiom/signing.key --key-id <id>` |

**Score:** 10/10 truths verified

---

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `mop_sdk/cli.py` | AXIOM_URL fix, key generate subcommand, init subcommand | VERIFIED | `os.getenv("AXIOM_URL")` at line 65; `do_key_generate()` at line 79; `do_init()` at line 114; `key` and `init` subparsers at lines 44-51 |
| `mop_sdk/auth.py` | CredentialStore migrated to ~/.axiom/ with backward-compat migration from ~/.mop/ | VERIFIED | `new_path = Path.home() / ".axiom" / "credentials.json"` at line 18; migration via `shutil.move` at lines 21-24 |
| `mop_sdk/client.py` | register_signature(), list_signatures(), get_me() methods | VERIFIED | `list_signatures()` at line 181; `register_signature()` at line 187; `get_me()` at line 193 |
| `mop_sdk/tests/test_cli.py` | Tests for CLI-01, CLI-02, CLI-03 | VERIFIED | 8 new tests: `test_axiom_url_env_var`, `test_mop_url_not_read`, `test_key_generate_creates_files`, `test_key_generate_refuses_overwrite`, `test_key_generate_force_overwrites`, `test_init_skip_login`, `test_init_full_flow`, `test_init_idempotent_existing_key` |
| `mop_sdk/tests/test_client.py` | Tests for register_signature | VERIFIED | `test_register_signature` and `test_list_signatures` both pass |
| `docs/docs/getting-started/first-job.md` | Restructured first-job guide with axiom-push init as primary path | VERIFIED | `axiom-push init` is Step 1 in Quick Start; AXIOM_URL is first user-facing line; openssl demoted to Manual Setup |

---

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `cli.py do_init()` | `client.py register_signature()` | `MOPClient.from_store()` | VERIFIED | `cli.py:150` calls `MOPClient.from_store(verify_ssl=False)`; `cli.py:161` calls `client.register_signature(...)` |
| `cli.py do_init()` | `GET /signatures` | `client.list_signatures()` preflight before POST | VERIFIED | `cli.py:155` calls `client.list_signatures()` before any registration attempt |
| `auth.py CredentialStore.__init__` | `~/.axiom/credentials.json` | `Path.home() / ".axiom"` | VERIFIED | `auth.py:18-25` sets `new_path = Path.home() / ".axiom" / "credentials.json"` with migration from `.mop/` |
| `first-job.md Quick Start section` | `axiom-push init command` | Step 0 / primary path | VERIFIED | Quick Start section at line 9; `axiom-push init` at line 23 |

---

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| CLI-01 | 78-01-PLAN.md | `axiom-push` reads `AXIOM_URL` env var for server address (fixes silent MOP_URL mismatch) | SATISFIED | `cli.py:65` uses `os.getenv("AXIOM_URL")`; MOP_URL removed entirely; 2 tests pass |
| CLI-02 | 78-01-PLAN.md | User can generate an Ed25519 keypair locally with `axiom-push key generate` | SATISFIED | `do_key_generate()` uses cryptography lib (no openssl); 3 tests pass; signing.key, verification.key created in ~/.axiom/ |
| CLI-03 | 78-01-PLAN.md | User can complete login, key generation, and public key registration with `axiom-push init` | SATISFIED | `do_init()` implements idempotent 3-step flow; 3 tests pass including idempotency check |
| CLI-04 | 78-02-PLAN.md | `first-job.md` documents the `axiom-push init` / `key generate` flow as the primary path | SATISFIED | first-job.md restructured: AXIOM_URL first, `axiom-push init` as Step 1, `key generate` in collapsible tip, openssl in Manual Setup |

No orphaned requirements — all 4 requirement IDs from REQUIREMENTS.md Phase 78 rows are accounted for in plan frontmatter and verified in codebase.

---

### Test Suite Results

All 17 tests pass (run: 2026-03-27):

```
mop_sdk/tests/test_cli.py::test_cli_help PASSED
mop_sdk/tests/test_cli.py::test_cli_no_args PASSED
mop_sdk/tests/test_cli.py::test_cli_login_flow PASSED
mop_sdk/tests/test_cli.py::test_axiom_url_env_var PASSED
mop_sdk/tests/test_cli.py::test_mop_url_not_read PASSED
mop_sdk/tests/test_cli.py::test_key_generate_creates_files PASSED
mop_sdk/tests/test_cli.py::test_key_generate_refuses_overwrite PASSED
mop_sdk/tests/test_cli.py::test_key_generate_force_overwrites PASSED
mop_sdk/tests/test_cli.py::test_init_skip_login PASSED
mop_sdk/tests/test_cli.py::test_init_full_flow PASSED
mop_sdk/tests/test_cli.py::test_init_idempotent_existing_key PASSED
mop_sdk/tests/test_client.py::test_push_job PASSED
mop_sdk/tests/test_client.py::test_create_job_definition PASSED
mop_sdk/tests/test_client.py::test_client_from_store PASSED
mop_sdk/tests/test_client.py::test_client_from_store_not_logged_in PASSED
mop_sdk/tests/test_client.py::test_register_signature PASSED
mop_sdk/tests/test_client.py::test_list_signatures PASSED
```

---

### Anti-Patterns Found

None. No TODOs, FIXMEs, placeholder returns, or stub implementations found in the modified files. The `save()` method in `auth.py` has a stale docstring mentioning `~/.mop/` (line 28), but this is cosmetic only and does not affect behavior.

---

### Commit Verification

All commits documented in SUMMARY files exist in git history:

| Hash | Message |
|------|---------|
| `cf6e3a1` | test(78-01): add failing tests for CLI-01 CLI-02 client.register_signature |
| `f6ad4fc` | feat(78-01): implement AXIOM_URL fix, key generate, auth migration |
| `a51b5ac` | docs(78-02): restructure first-job.md with axiom-push init as primary path |

---

### Human Verification Required

One item is not verifiable programmatically:

**Doc rendering in MkDocs**

- **Test:** Run `mkdocs serve` or `mkdocs build` against the docs directory and navigate to the first-job page
- **Expected:** The `??? tip` collapsible block renders as a collapsible admonition, the `=== "CLI"` tabs render as tabs, and the `!!! note` EE gate renders as an info box
- **Why human:** MkDocs admonition and tab syntax validity requires a browser render to confirm visual correctness; `mkdocs build --strict` was not confirmed in this environment

---

### Summary

Phase 78 achieves its goal. A new user following the documented flow can:

1. Set `AXIOM_URL` and run `axiom-push init` — the CLI performs login (OAuth device flow), generates an Ed25519 keypair in `~/.axiom/` using the cryptography library (no openssl), registers the public key with the server, and prints a copy-paste-ready `axiom-push job push` command containing the real Key ID.

All four requirement IDs (CLI-01 through CLI-04) are fully implemented, tested, and documented. The 17-test suite is green. The docs restructure places `axiom-push init` as the primary path with openssl preserved but demoted. No stubs, orphaned artifacts, or missing wiring were found.

---

_Verified: 2026-03-27T19:00:00Z_
_Verifier: Claude (gsd-verifier)_
