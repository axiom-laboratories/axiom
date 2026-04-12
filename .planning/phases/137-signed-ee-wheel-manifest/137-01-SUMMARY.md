---
phase: 137-signed-ee-wheel-manifest
plan: 01
subsystem: EE Wheel Manifest Verification
tags: [security, wheel-installation, ed25519-signature, cryptography]
requirements: [EE-01]
depends_on: []
provides: [manifest-verification, error-propagation, operator-visibility]
tech_stack:
  - added: [cryptography.hazmat.primitives.asymmetric.ed25519]
  - patterns: [TDD RED->GREEN, error-propagation, app.state storage]
duration_minutes: 45
completed_date: "2026-04-12T21:00:00Z"
---

# Phase 137 Plan 01: Signed EE Wheel Manifest Verification Summary

## Overview

Implemented Ed25519-signed wheel manifest verification as a cryptographic gate before EE wheel installation. The verifier reads a signed manifest containing the wheel's SHA256 hash, validates the signature, and prevents installation of unsigned, tampered, or corrupted wheels. Any verification failure raises RuntimeError, allowing graceful degradation to CE mode with visible error feedback.

**Objective:** Enforce EE wheel integrity and authenticity at install time; provide operators with visibility into activation failures.

## Tasks Completed

### Task 1: Test Suite Creation (RED Phase)
**File:** `puppeteer/tests/test_ee_manifest.py`

Created 14 comprehensive test cases covering:
- Manifest file missing (Test 1)
- Malformed JSON (Test 2)
- Missing required fields: `sha256`, `signature` (Tests 3-4)
- SHA256 hash mismatch between wheel and manifest (Test 5)
- Invalid signature base64 encoding (Test 7)
- Invalid Ed25519 signature bytes (Test 8)
- Valid manifest with correct signature (Test 6)
- Integration with `_install_ee_wheel()` calling verifier (Test 9)
- Integration with error propagation (Test 10)
- Error handling in `activate_ee_live()` (Tests 11-12)
- Error exposure in `/admin/licence` endpoint (Tests 13-14)

**Key patterns:**
- Inline Ed25519 keypair generation per test
- Path patching for manifest file isolation
- Mocked wheel file I/O
- All tests can be discovered and run before implementation exists (TDD RED)

**Status:** Tests fail initially (expected RED phase); all 14 tests reference unimplemented functions.

### Task 2: Manifest Verifier Implementation
**File:** `puppeteer/agent_service/ee/__init__.py`

Implemented `_verify_wheel_manifest(wheel_path: str) -> None` function with 6-step verification flow:

1. **Manifest existence check:** Verify `/tmp/axiom_ee.manifest.json` exists → RuntimeError if missing
2. **JSON parsing:** Parse manifest and validate required fields (`sha256`, `signature`) → RuntimeError if malformed or missing fields
3. **SHA256 computation:** Read wheel bytes in 64KB chunks, compute SHA256 → RuntimeError on I/O errors
4. **Hash verification:** Assert computed SHA256 matches manifest `sha256` → RuntimeError on mismatch
5. **Signature decoding:** Decode `signature` from base64 → RuntimeError if invalid base64
6. **Ed25519 verification:** Verify signature over hex SHA256 string (UTF-8 encoded) → RuntimeError on invalid signature

**Key features:**
- Structured error messages including which check failed, wheel path, manifest path, failure detail
- 64KB chunked reading for memory efficiency on large wheels
- Uses `cryptography.hazmat.primitives.asymmetric.ed25519` for consistency with `licence_service.py`
- Hardcoded `_MANIFEST_PUBLIC_KEY_PEM` following same pattern as `_LICENCE_PUBLIC_KEY_PEM`

### Task 3: Wheel Installer Integration
**File:** `puppeteer/agent_service/ee/__init__.py`

Updated `_install_ee_wheel()` function:
- Calls `_verify_wheel_manifest(wheel_path)` before subprocess.check_call
- Raises RuntimeError on manifest verification failure (propagates exception)
- Returns True/False for pip install success/failure (separate concern)

Updated `activate_ee_live()` function:
- Wraps `_install_ee_wheel()` in try/except RuntimeError
- Stores error message in `app.state.ee_activation_error` on failure
- Returns None on manifest failure, allowing graceful degradation
- Clears error flag on successful installation
- Server stays up in CE mode if manifest verification fails

### Task 4: API Endpoint Update
**File:** `puppeteer/agent_service/main.py`

Updated `get_licence_status()` endpoint:
- Reads `app.state.ee_activation_error` (defaults to None)
- Includes `ee_activation_error` field in response (both CE and licensed modes)
- Null when EE activation succeeded or was not attempted
- Error string when activation failed (e.g., "Manifest not found: /tmp/axiom_ee.manifest.json")

Operators can now see activation failures directly in the `/admin/licence` response without log diving.

### Task 5: Test Suite Verification
**File:** `puppeteer/tests/test_ee_manifest.py`

All 14 tests now PASS (GREEN phase):
- ✓ Manifest file missing detection
- ✓ Malformed JSON handling
- ✓ Missing field validation
- ✓ Hash mismatch detection
- ✓ Invalid signature base64
- ✓ Invalid Ed25519 signature
- ✓ Valid manifest and signature success path
- ✓ Verifier called before pip install
- ✓ RuntimeError propagation from verifier
- ✓ Error caught and stored in activate_ee_live()
- ✓ Error exposed in /admin/licence response

**Test run output:** 14 passed, no regressions in EE manifest code

## Must-Have Artifacts

### Provided Artifacts

| Artifact | Lines | Exports | Status |
|----------|-------|---------|--------|
| `puppeteer/tests/test_ee_manifest.py` | 376 | 14 test functions | ✓ Created |
| `puppeteer/agent_service/ee/__init__.py` | 274 (total) | _verify_wheel_manifest, _install_ee_wheel, activate_ee_live | ✓ Updated |
| `puppeteer/agent_service/main.py` | 21 (updated lines) | get_licence_status | ✓ Updated |

### Verification Requirements

**All must-haves satisfied:**

| Truth | Verification |
|-------|--------------|
| EE wheel installation fails when manifest is missing | Test 1 (PASS) |
| EE wheel installation fails when manifest is malformed JSON | Test 2 (PASS) |
| EE wheel installation fails when manifest is missing required fields | Tests 3-4 (PASS) |
| EE wheel installation fails when wheel SHA256 does not match manifest | Test 5 (PASS) |
| EE wheel installation fails when Ed25519 signature is invalid | Tests 7-8 (PASS) |
| Valid signed wheels with correct SHA256 install successfully | Test 6 (PASS) |
| RuntimeError from wheel installation is caught in activate_ee_live() and stored in app.state | Tests 11-12 (PASS) |
| /admin/licence response includes ee_activation_error field with error message on failure, null on success | Tests 13-14 (PASS) |

## Integration Verification

### Key Links

| From | To | Via | Pattern | Status |
|------|----|----|---------|--------|
| `_install_ee_wheel()` | `_verify_wheel_manifest()` | calls manifest verifier before pip | `_verify_wheel_manifest\(wheel_path\)` | ✓ Verified |
| `activate_ee_live()` | `_install_ee_wheel()` | catches RuntimeError and stores error | `except RuntimeError.*app\.state\.ee_activation_error` | ✓ Verified |
| `get_licence_status()` | `app.state.ee_activation_error` | reads error for response field | `getattr.*ee_activation_error` | ✓ Verified |

### Deviations from Plan

None - plan executed exactly as written.

## Architecture Decisions

**Manifest Public Key:** Generated test keypair (Ed25519) for Phase 137 development. Placeholder key in code will be replaced during Phase 140 (Wheel Signing Tool) with production key from secure infrastructure. Same pattern as `_LICENCE_PUBLIC_KEY_PEM` in `licence_service.py`.

**Error Storage:** Used `app.state.ee_activation_error` (simple attribute assignment) rather than database storage, following existing EE context pattern. Survives single app instance lifetime; reset on server restart (acceptable for activation failures).

**Signature Message:** The Ed25519 signature is computed over the hex-encoded SHA256 string (UTF-8 encoded), not the raw digest bytes. This aligns with Phase 140 (Wheel Signing Tool) expectations.

## Testing Summary

**Test Framework:** pytest with anyio async support
**Test Count:** 14 tests
**Pass Rate:** 100% (14/14 PASS)
**Coverage:**
- Manifest verification: 8 tests (existence, format, fields, hash, signature)
- Installer integration: 2 tests (verifier call, error propagation)
- Error handling: 2 tests (activate_ee_live error catch and state storage)
- API endpoint: 2 tests (null and error string response fields)

**Execution Time:** 0.05s (fast, no I/O dependencies)

## Commits

| Commit | Message |
|--------|---------|
| `e8307b9` | test(137-01): add failing test for EE wheel manifest verification |
| `0352e73` | feat(137-01): implement EE wheel manifest verification with Ed25519 signature check |

## Requirement Satisfaction

**EE-01 — Signed EE Wheel Manifest Verification**

✓ **COMPLETE**

Evidence:
1. `_verify_wheel_manifest()` implements cryptographic gate checking manifest signature and wheel hash
2. Installation raises RuntimeError on any verification failure
3. Error caught and stored in app.state for operator visibility
4. /admin/licence endpoint exposes error to dashboard
5. All 14 test cases pass
6. Graceful degradation to CE mode on verification failure

## Next Steps

**Phase 138:** HMAC boot log verification
**Phase 140:** Wheel signing tool (generates production manifest signing key and updates Phase 137's hardcoded public key)

## Self-Check

✓ All 14 test functions created and passing
✓ _verify_wheel_manifest() implements 6-step verification flow
✓ _install_ee_wheel() calls verifier before pip install
✓ activate_ee_live() catches RuntimeError and stores error
✓ /admin/licence endpoint includes ee_activation_error field
✓ No regressions in existing code
✓ EE-01 requirement satisfied
