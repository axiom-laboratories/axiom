---
phase: 39-ee-test-keypair-dev-install
plan: "02"
subsystem: mop_validation/scripts
tags: [ee, licence, validation, testing]
dependency_graph:
  requires: [39-01]
  provides: [EEDEV-03-tools, EEDEV-04-tools, EEDEV-05-tools]
  affects: []
tech_stack:
  added: []
  patterns: [base64url-signed-licence, check-pass-fail-pattern, cli-case-routing]
key_files:
  created:
    - /home/thomas/Development/mop_validation/scripts/generate_ee_licence.py
    - /home/thomas/Development/mop_validation/scripts/verify_ee_install.py
    - /home/thomas/Development/mop_validation/secrets/ee/ee_valid_licence.env
    - /home/thomas/Development/mop_validation/secrets/ee/ee_expired_licence.env
  modified: []
decisions:
  - "Plan verification condition `payload['exp'] > 1700000000 * 5` (= 8.5B, year ~2239) was a typo — corrected to `> int(time.time())` for the actual assertion. 10-year licence exp is ~2089 (~2.09B), which is correct and far future."
metrics:
  duration: "3 minutes"
  completed: "2026-03-20"
  tasks_completed: 2
  files_created: 4
requirements: [EEDEV-03, EEDEV-04, EEDEV-05]
---

# Phase 39 Plan 02: EE Licence Generator + Install Verifier Summary

One-liner: Ed25519-signed test licence strings (valid + expired) and a three-case API verifier script for EEDEV-03/04/05 lifecycle validation.

## What Was Built

### generate_ee_licence.py
Loads `secrets/ee/ee_test_private.pem` (from Plan 01), signs two licence payloads using the same `base64url(compact_json).base64url(ed25519_sig)` wire format that `puppeteer/agent_service/services/licence_service.py` expects, and writes:

- `secrets/ee/ee_valid_licence.env` — `AXIOM_LICENCE_KEY=<key>` with `exp` ~10 years from generation time, all 8 EE features, `customer_id=axiom-dev-test`
- `secrets/ee/ee_expired_licence.env` — same payload but `exp=1704067200` (fixed 2024-01-01 UTC, deterministic)

Script also prints exact `docker compose stop/up` commands for all three test scenarios.

### verify_ee_install.py
Three-case API verifier with `--case valid|expired|absent` routing:

- `--case valid` (EEDEV-03): Asserts `GET /api/licence` returns `edition=enterprise`, `customer_id=axiom-dev-test`, `expires` present, features non-empty; and `GET /api/features` has all 8 keys all true.
- `--case expired` (EEDEV-04): Asserts `GET /api/licence` returns `edition=community`; `GET /api/features` all false.
- `--case absent` (EEDEV-05): Asserts stack starts without crash; `GET /api/features` all false; `GET /api/licence` returns `edition=community`.

Each case prints the exact restart commands as pre-condition reminders and outputs a `Result: X/Y checks passed` summary. Exit 0 = all passed; exit 1 = any failed. Mirrors Phase 38 `verify_ce_install.py` `[PASS]/[FAIL]` style.

## Verification Results

- `ee_valid_licence.env` and `ee_expired_licence.env` written and structurally verified
- Valid licence payload round-trip: `customer_id=axiom-dev-test`, exp in the future
- Expired licence payload: `exp=1704067200` deterministic
- `verify_ee_install.py` exits 1 with usage when `--case` missing
- `puppeteer/agent_service/tests/test_licence.py` — 6/6 passed (unaffected)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed plan verification assertion typo**
- **Found during:** Task 1 verification
- **Issue:** Plan verification script asserted `payload['exp'] > 1700000000 * 5` (equals 8,500,000,000, year ~2239). A 10-year licence gives exp ~2,089,000,000, which correctly fails that check.
- **Fix:** Applied the correct assertion (`> int(time.time())`) in the verification run. The implementation itself is correct — the bug was only in the plan's inline verification snippet.
- **Files modified:** None (plan snippet was never intended to be a standalone file; verification was run with corrected condition)

## Full Phase 39 Verification Flow

```
1. generate_ee_keypair.py   → secrets/ee/ee_test_private.pem + ee_test_public.pem
2. patch_ee_source.py       → patches axiom-ee source with test public key
3. pip install -e axiom-ee/ → editable install so patch takes effect
4. generate_ee_licence.py   → ee_valid_licence.env + ee_expired_licence.env
5. Restart agent with valid key → verify_ee_install.py --case valid  (EEDEV-03)
6. Restart agent with expired key → verify_ee_install.py --case expired (EEDEV-04)
7. Restart agent with no key → verify_ee_install.py --case absent (EEDEV-05)
```

## Self-Check: PASSED

- `/home/thomas/Development/mop_validation/scripts/generate_ee_licence.py` — FOUND
- `/home/thomas/Development/mop_validation/scripts/verify_ee_install.py` — FOUND
- `/home/thomas/Development/mop_validation/secrets/ee/ee_valid_licence.env` — FOUND
- `/home/thomas/Development/mop_validation/secrets/ee/ee_expired_licence.env` — FOUND
- Commit `ee3221a` (Task 1) — FOUND
- Commit `e767f2f` (Task 2) — FOUND
