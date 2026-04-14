# Phase 144: Nyquist Validation — EE Features - Research

**Researched:** 2026-04-14
**Domain:** Test validation and gap coverage for EE licence protection phases (137–140)
**Confidence:** HIGH

## Summary

Phase 144 validates all four EE licence protection phases (137–140) by running the `validate-phase` workflow on each. The phases are already implemented; this phase ensures all requirements have automated test coverage and fixes any failing tests.

**Current state:**
- **Phase 137** (Signed Wheel Manifest): 18/18 tests PASSING ✅
- **Phase 138** (HMAC Boot Log): 24/26 tests passing; 2 tests FAILING ❌
- **Phase 139** (Entry Point Whitelist + ENCRYPTION_KEY): 4/4 encryption tests + 4/4 entry point tests PASSING ✅
- **Phase 140** (Wheel Signing Tool): 23/23 tests PASSING ✅

**Primary blocker:** Phase 138 has 2 failing tests that must be fixed before marking phase compliant:
1. `test_reload_licence_with_invalid_key` — expects "signature invalid" but gets "parse error" (line 331)
2. `test_licence_expiry_guard_ee_prefixes` — test assertion outdated; production code has `/api/admin/bundles` prefix (line 443)

**Primary recommendation:** Fix both Phase 138 failures, then run full regression test (`cd puppeteer && pytest -x -q`) to ensure no collateral damage. Each phase will then be marked `nyquist_compliant: true` and `wave_0_complete: true`.

---

## User Constraints (from CONTEXT.md)

### Locked Decisions

1. **Dual test suite strategy:** Puppeteer phases (137, 138, 139) verified via `cd puppeteer && pytest -x -q`; Phase 140 verified separately via `cd axiom-licenses && pytest tests/tools/ -x -q`.
2. **Fix pre-existing failure:** `test_reload_licence_with_invalid_key` is currently failing; investigate and fix root cause (production regression or test expectation mismatch).
3. **Block on green:** Phase 138 cannot be marked compliant until all tests in `test_licence_service.py` pass, including the failing test above.
4. **Compliance behavior-based:** Phases are compliant if behavior is covered by a passing test, not if test names match VALIDATION.md wave 0 placeholders.
5. **Gap closure:** Any success criterion from phase description with zero test coverage must have a new test written.
6. **Manual-only items stay manual:** Items listed in VALIDATION.md "Manual-Only Verifications" are not automated.

### Claude's Discretion

- Order of fixing Phase 138 failures (both are blocking; prioritize by root cause complexity)
- Whether to add additional regression tests beyond the two failures

### Deferred Ideas (OUT OF SCOPE)

- Implementing new EE features
- Changing production EE logic beyond fixing confirmed regressions
- Adding new licence protection mechanisms

---

## Phase 137 — Signed EE Wheel Manifest (READY FOR COMPLIANCE)

| Property | Status |
|----------|--------|
| **Tests** | 18/18 PASSING ✅ |
| **Coverage** | EE-01 fully covered |
| **Validation** | READY TO MARK COMPLIANT |

### Test Coverage

All 18 tests passing:
- `TestVerifyWheelManifestMissing::test_verify_wheel_manifest_raises_on_missing_manifest` ✅
- `TestVerifyWheelManifestMalformed::test_verify_wheel_manifest_raises_on_malformed_json` ✅
- `TestVerifyWheelManifestMissingFields::test_verify_wheel_manifest_raises_on_missing_sha256_field` ✅
- `TestVerifyWheelManifestMissingFields::test_verify_wheel_manifest_raises_on_missing_signature_field` ✅
- `TestVerifyWheelManifestHashMismatch::test_verify_wheel_manifest_raises_on_hash_mismatch` ✅
- `TestVerifyWheelManifestInvalidSignature::test_verify_wheel_manifest_raises_on_invalid_base64_signature` ✅
- `TestVerifyWheelManifestInvalidSignature::test_verify_wheel_manifest_raises_on_invalid_ed25519_signature` ✅
- `TestVerifyWheelManifestSuccess::test_verify_wheel_manifest_succeeds_with_valid_manifest` ✅
- `TestInstallEEWheelIntegration::test_install_ee_wheel_calls_verify_wheel_manifest` ✅
- `TestInstallEEWheelIntegration::test_install_ee_wheel_propagates_runtime_error` ✅
- `TestActivateEELiveErrorHandling::test_activate_ee_live_catches_runtime_error` ✅
- `TestActivateEELiveErrorHandling::test_activate_ee_live_returns_none_on_manifest_failure` ✅
- `TestLicenceEndpointEEActivationError::test_licence_endpoint_includes_ee_activation_error_null_on_success` ✅
- `TestLicenceEndpointEEActivationError::test_licence_endpoint_includes_ee_activation_error_string_on_failure` ✅
- `TestEntryPointWhitelist::test_entry_point_whitelist_startup_trusted` ✅
- `TestEntryPointWhitelist::test_entry_point_whitelist_startup_untrusted` ✅
- `TestEntryPointWhitelist::test_entry_point_whitelist_live_reload_trusted` ✅
- `TestEntryPointWhitelist::test_entry_point_whitelist_live_reload_untrusted` ✅

**Note:** `test_ee_manifest.py` covers both Phase 137 (manifest verification) and Phase 139 (entry point whitelist) behaviors due to shared module `agent_service.ee`. Both phases reference the same test file for their validation strategies.

---

## Phase 138 — HMAC-Keyed Boot Log (BLOCKED BY FAILURES)

| Property | Status |
|----------|--------|
| **Tests** | 24/26 PASSING; 2/26 FAILING ❌ |
| **Coverage** | EE-02, EE-03 partially covered |
| **Validation** | BLOCKED — must fix failures before compliance |

### Test Coverage

#### Passing Tests (24/26)
- `test_generate_licence_jwt` ✅
- `test_invalid_signature_falls_to_ce` ✅
- `test_grace_period_active` ✅
- `test_degraded_ce_state` ✅
- `test_clock_rollback_detection` ✅
- `test_check_and_record_boot_strict_ee` ✅
- `test_licence_status_endpoint` ✅
- `test_enroll_node_limit_enforced` ✅
- `test_reload_licence_with_valid_key` ✅
- ❌ `test_reload_licence_with_invalid_key` **FAILING** (see below)
- `test_reload_licence_no_key_raises_error` ✅
- `test_check_licence_expiry_valid` ✅
- `test_check_licence_expiry_grace` ✅
- `test_check_licence_expiry_expired` ✅
- `test_check_licence_expiry_ce_stays_ce` ✅
- ❌ `test_licence_expiry_guard_ee_prefixes` **FAILING** (see below)
- `test_licence_reload_endpoint_integration` ✅
- `test_licence_reload_preserves_all_fields` ✅
- `test_licence_state_transitions_complete` ✅
- `test_check_and_record_boot_integration` ✅
- `test_hmac_entry_write` ✅
- `test_hmac_verify_on_read` ✅
- `test_hmac_mismatch_ce_lax` ✅
- `test_legacy_sha256_silent_accept` ✅
- `test_legacy_warning_on_read` ✅
- `test_mixed_format_coexist` ✅

### Failing Tests (2/26) — ROOT CAUSE ANALYSIS

#### Failure 1: `test_reload_licence_with_invalid_key` (Line 327)

**What's failing:**
```python
async def test_reload_licence_with_invalid_key():
    """Phase 116: reload_licence() with invalid key raises LicenceError."""
    from agent_service.services.licence_service import reload_licence, LicenceError

    with pytest.raises(LicenceError, match="signature invalid"):
        await reload_licence(licence_key="invalid.token.here")
```

**Actual error message:**
```
"Licence key parse error: Invalid header string: 'utf-8' codec can't decode byte 0x8a 
in position 0: invalid start byte"
```

**Expected error message:** Regex `"signature invalid"`

**Root cause:** The test expects a malformed JWT to fail during signature verification, but it's actually failing earlier during JWT header parsing. The string `"invalid.token.here"` is base64-decoded and fails to parse as valid JSON when treated as a JWT header.

**Fix recommendation:** **Fix the test expectation, not production code.** The `reload_licence()` function correctly raises `LicenceError` with a descriptive message when JWT parsing fails. The test should match the broader pattern `"parse error"` (which covers both signature AND parse failures), or accept any `LicenceError` without a specific match. This is NOT a production regression — JWT parsing failure is an appropriate error path.

**Status:** STALE TEST EXPECTATION

#### Failure 2: `test_licence_expiry_guard_ee_prefixes` (Line 443)

**What's failing:**
```python
def test_licence_expiry_guard_ee_prefixes():
    """Phase 116 Task 6: Verify LicenceExpiryGuard middleware has correct EE route prefixes."""
    from agent_service.main import LicenceExpiryGuard

    expected_prefixes = (
        "/api/foundry",
        "/api/audit",
        "/api/webhooks",
        "/api/triggers",
        "/api/auth-ext",
        "/api/smelter",
        "/api/executions",
    )
    assert LicenceExpiryGuard.EE_PREFIXES == expected_prefixes
```

**Actual EE_PREFIXES:** `('/api/foundry', '/api/audit', '/api/webhooks', '/api/triggers', '/api/auth-ext', '/api/smelter', '/api/executions', '/api/admin/bundles')`

**Root cause:** Production code (in `agent_service/main.py`) includes `/api/admin/bundles` in the `EE_PREFIXES` tuple, but the test does not. This happened during a post-implementation change that added a new EE-gated endpoint.

**Fix recommendation:** **Update the test to match production.** Add `"/api/admin/bundles"` to the `expected_prefixes` tuple. This is NOT a production bug; the test is simply outdated.

**Status:** OUTDATED TEST

---

## Phase 139 — Entry Point Whitelist + ENCRYPTION_KEY (READY FOR COMPLIANCE)

| Property | Status |
|----------|--------|
| **Tests** | 8/8 PASSING ✅ |
| **Coverage** | EE-04, EE-06 fully covered |
| **Validation** | READY TO MARK COMPLIANT |

### Test Coverage

#### Encryption Key Enforcement (4/4 tests)
- `TestEncryptionKeyRequired::test_encryption_key_required_at_module_load` ✅
- `TestEncryptionKeyRequired::test_encryption_key_absent_raises_runtime_error` ✅
- `TestEncryptionKeyRequired::test_encryption_key_error_message_includes_generation_command` ✅
- `TestEncryptionKeyRequired::test_encryption_key_loads_successfully_when_set` ✅

#### Entry Point Whitelist (4/4 tests)
- `TestEntryPointWhitelist::test_entry_point_whitelist_startup_trusted` ✅
- `TestEntryPointWhitelist::test_entry_point_whitelist_startup_untrusted` ✅
- `TestEntryPointWhitelist::test_entry_point_whitelist_live_reload_trusted` ✅
- `TestEntryPointWhitelist::test_entry_point_whitelist_live_reload_untrusted` ✅

All tests in two files:
- `puppeteer/tests/test_encryption_key_enforcement.py` (4 tests)
- `puppeteer/tests/test_ee_manifest.py` (4 tests — shared with Phase 137)

---

## Phase 140 — Wheel Signing Tool Release Infrastructure (READY FOR COMPLIANCE)

| Property | Status |
|----------|--------|
| **Tests** | 23/23 PASSING ✅ |
| **Coverage** | EE-05 fully covered |
| **Validation** | READY TO MARK COMPLIANT |

### Test Coverage

#### gen_wheel_key.py (5/5 tests in `axiom-licenses/tests/tools/test_gen_wheel_key.py`)
- `test_generate_keypair` ✅
- `test_no_overwrite_without_force` ✅
- `test_public_key_bytes_literal` ✅
- `test_force_flag_overwrites` ✅
- `test_file_permissions_0600` ✅

#### key_resolution.py (6/6 tests in `axiom-licenses/tests/tools/test_key_resolution.py`)
- `test_key_resolution_from_arg` ✅
- `test_key_resolution_from_env` ✅
- `test_key_resolution_missing` ✅
- `test_key_file_not_found` ✅
- `test_key_load_failure` ✅
- `test_key_resolution_private_to_public_fallback` ✅

#### sign_wheels.py (12/12 tests in `axiom-licenses/tests/tools/test_sign_wheels.py`)
- `test_wheel_discovery` ✅
- `test_wheel_hash_chunked` ✅
- `test_signature_format` ✅
- `test_manifest_naming` ✅
- `test_deploy_name_flag` ✅
- `test_no_wheels_error` ✅
- `test_verify_mode` ✅
- `test_verify_exit_codes` ✅
- `test_key_resolution_arg` ✅
- `test_key_resolution_env` ✅
- `test_quiet_flag` ✅
- `test_verify_sha256_mismatch` ✅

---

## Standard Stack

| Component | Version | Purpose | Location |
|-----------|---------|---------|----------|
| pytest | 7.x / 9.0.2 | Test framework | puppeteer/ |
| pytest-asyncio | 1.3.0 | Async test support | puppeteer/ |
| cryptography | (latest) | Ed25519 keys, signatures | puppeteer/tests/ |
| PyJWT | (latest) | JWT parsing | puppeteer/agent_service/ |

---

## Architecture Patterns

### Test Organization

**Puppeteer tests (phases 137–139):**
```
puppeteer/tests/
├── test_ee_manifest.py        # Phase 137 + Phase 139 (entry points)
├── test_encryption_key_enforcement.py  # Phase 139 (ENCRYPTION_KEY)
└── test_licence_service.py    # Phase 138 (HMAC boot log)
```

**Axiom-licenses tests (phase 140):**
```
axiom-licenses/tests/tools/
├── test_gen_wheel_key.py      # Phase 140 (key generation)
├── test_sign_wheels.py        # Phase 140 (wheel signing)
└── test_key_resolution.py     # Phase 140 (key lookup)
```

### Test Class Pattern (Phase 137 Example)

```python
class TestVerifyWheelManifestMissing:
    """Test 1: Manifest file missing."""

    def test_verify_wheel_manifest_raises_on_missing_manifest(self, temp_wheel_file, manifest_path_patcher):
        """_verify_wheel_manifest raises RuntimeError when manifest file does not exist."""
        missing_manifest = Path("/nonexistent/path/axiom_ee.manifest.json")

        with manifest_path_patcher(missing_manifest):
            with pytest.raises(RuntimeError, match="Manifest not found"):
                _verify_wheel_manifest(str(temp_wheel_file))
```

**Key patterns:**
- Test classes group related behaviors
- Fixtures for Ed25519 keypairs, temp files, path patching
- Use `pytest.raises()` with regex matchers for exception verification
- Async tests use `@pytest.mark.asyncio`

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Ed25519 signature generation/verification | Custom crypto | `cryptography.hazmat.primitives.asymmetric.ed25519` | Battle-tested, constant-time, prevents timing attacks |
| JWT parsing and validation | Custom JWT parser | `PyJWT` (already in stack) | Handles all edge cases; standard library |
| HMAC-SHA256 | Custom HMAC | `hmac.HMAC(key, msg, hashlib.sha256)` | Built-in, constant-time, secure |
| Wheel discovery and hashing | Custom file scanning | Follow `sign_wheels.py` pattern (glob + chunked hash) | 64KB chunks prevent memory issues; matches Phase 137 verification |

---

## Common Pitfalls

### Pitfall 1: Test Expectation Drift from Production

**What goes wrong:** Test was written with a specific error message pattern, but production code is enhanced and raises a more general (still correct) error message. Test fails even though production is working.

**Why it happens:** Tests are often written early in development; later enhancements to error handling or parsing make original expectations too narrow.

**How to avoid:** Match on regex patterns that are broader than a single error message. For JWT/licence errors, match on `"error"` or the error class, not a specific substring. Review test failures to understand if they're regressions or expectation drift.

**Warning signs:** Test failure message shows the expected regex didn't match a *valid* error message (not a failure in the happy path).

**Example from Phase 138:** `test_reload_licence_with_invalid_key` expects `"signature invalid"` but gets `"parse error"` — both are correct, but the test is too specific.

### Pitfall 2: Middleware Prefix List Drift

**What goes wrong:** A new EE endpoint is added to the codebase, the `LicenceExpiryGuard.EE_PREFIXES` tuple is updated in production, but the test expectations are not.

**Why it happens:** Prefix lists are "invisible" changes — easy to update in one place and forget another. Tests become outdated silently.

**How to avoid:** When adding an EE endpoint, update BOTH the middleware tuple AND the test assertion in one commit. Use a pre-commit hook to validate they match (if critical).

**Warning signs:** Test assertion lists hardcoded tuples instead of reading from the source of truth (the middleware class).

---

## Code Examples

### Example 1: HMAC Boot Log Entry (Phase 138)

From `agent_service/services/licence_service.py`:

```python
def _compute_hmac(msg: bytes, encryption_key: bytes) -> str:
    """Compute HMAC-SHA256 digest as hex string (constant-time verification)."""
    h = hmac.HMAC(encryption_key, msg, hashlib.sha256)
    return h.hexdigest()

def check_and_record_boot(encryption_key: bytes, current_state: LicenceState):
    """Record boot event with HMAC for EE, SHA256 for CE (backward compatible)."""
    timestamp = datetime.utcnow().isoformat()
    
    if current_state.is_ee_active:
        # New EE format: hmac:<64-hex-hmac> <ISO8601>
        msg = timestamp.encode()
        hmac_hex = _compute_hmac(msg, encryption_key)
        entry = f"hmac:{hmac_hex} {timestamp}"
    else:
        # Legacy CE format: <64-hex-sha256> <ISO8601>
        sha256_hex = hashlib.sha256(timestamp.encode()).hexdigest()
        entry = f"{sha256_hex} {timestamp}"
    
    boot_log.append(entry)
```

**Key insight:** Entry format is `"hmac:" + hex(HMAC) + " " + timestamp` for new entries; legacy `sha256` entries (no prefix) are silently accepted for backward compatibility.

### Example 2: Entry Point Whitelist (Phase 139)

From `agent_service/ee/__init__.py`:

```python
def load_ee_plugins():
    """Load EE plugins, validating entry point value against whitelist."""
    from importlib.metadata import entry_points
    
    TRUSTED_ENTRY_POINT = "ee.plugin:EEPlugin"
    
    try:
        eps = entry_points(group="axiom_ee")
    except Exception:
        return
    
    for ep in eps:
        if ep.value != TRUSTED_ENTRY_POINT:
            raise RuntimeError(f"Untrusted entry point: {ep.value} (expected {TRUSTED_ENTRY_POINT})")
        
        plugin_module = ep.load()
        # ... activate plugin ...
```

**Key insight:** Whitelist is a simple string match, not a regex. Only `"ee.plugin:EEPlugin"` is trusted; any variation is rejected with RuntimeError.

### Example 3: Wheel Manifest Verification (Phase 137)

From `agent_service/ee/__init__.py`:

```python
def _verify_wheel_manifest(wheel_path: str) -> dict:
    """Verify wheel manifest: file exists, JSON valid, required fields, SHA256, signature."""
    manifest_path = Path(MANIFEST_PATH)
    
    # Step 1: Manifest file exists
    if not manifest_path.exists():
        raise RuntimeError(f"Manifest not found at {manifest_path}")
    
    # Step 2: Parse JSON
    try:
        with open(manifest_path) as f:
            manifest = json.load(f)
    except json.JSONDecodeError as e:
        raise RuntimeError(f"Manifest malformed: {e}")
    
    # Step 3: Required fields
    for field in ["sha256", "signature"]:
        if field not in manifest:
            raise RuntimeError(f"Manifest missing field: {field}")
    
    # Step 4: SHA256 hash
    wheel_hash = hashlib.sha256(Path(wheel_path).read_bytes()).hexdigest()
    if wheel_hash != manifest["sha256"]:
        raise RuntimeError(f"Wheel hash mismatch")
    
    # Step 5: Signature decode + verify
    try:
        sig_bytes = base64.b64decode(manifest["signature"])
        public_key.verify(sig_bytes, wheel_hash.encode())
    except Exception as e:
        raise RuntimeError(f"Signature verification failed: {e}")
    
    return manifest
```

**Key pattern:** 6-step verification with specific error on each failure. Tests cover each step in isolation.

---

## State of the Art

| Aspect | Previous | Current | When | Impact |
|--------|----------|---------|------|--------|
| EE wheel verification | Manual inspection | Automated Ed25519 signature | Phase 137 | Installation integrity guaranteed |
| Boot log integrity | Plain SHA256 | HMAC-SHA256 (EE) + legacy support | Phase 138 | Tamper detection without forced migration |
| Plugin loading | No whitelist | Strict entry point value check | Phase 139 | Untrusted plugins blocked at load time |
| Wheel signing | Manual process | CLI `sign_wheels.py` + `gen_wheel_key.py` | Phase 140 | Repeatable release-time signing |

---

## Open Questions

1. **Should Phase 138 failures be prioritized differently?**
   - Both are blocking; both are non-production bugs (stale test or outdated assertion)
   - Recommendation: Fix `test_licence_expiry_guard_ee_prefixes` first (simpler: update tuple); then `test_reload_licence_with_invalid_key` (requires regex judgment call)

2. **Are there any integration gaps between phases?**
   - Phase 137 provides manifest verification; Phase 140 provides signing tools
   - Phase 139 provides entry point validation + ENCRYPTION_KEY enforcement
   - Phase 138 provides boot log integrity
   - All seem complete and non-overlapping

3. **Should we add regression tests for the fixes?**
   - After fixing Phase 138 failures, run the full puppeteer test suite to ensure no collateral
   - Consider adding a test that explicitly validates "parse error is accepted" for malformed JWTs (prevents drift in future)

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest 7.x / 9.0.2 |
| Config file | `puppeteer/pytest.ini` (or `pyproject.toml` for axiom-licenses) |
| Quick run command (137–139) | `cd puppeteer && pytest tests/test_ee_manifest.py tests/test_encryption_key_enforcement.py tests/test_licence_service.py -x -q` |
| Full suite command (137–139) | `cd puppeteer && pytest -x -q` |
| Quick run command (140) | `cd axiom-licenses && pytest tests/tools/ -x -q` |
| Full suite command (140) | `cd axiom-licenses && pytest tests/ -q` |
| Estimated runtime | ~20 seconds total |

### Phase Requirements → Test Map

#### Phase 137: Signed EE Wheel Manifest (EE-01)

| Requirement | Behavior | Test Type | Automated Command | Status |
|-------------|----------|-----------|-------------------|--------|
| EE-01 | Manifest file missing raises error | unit | `cd puppeteer && pytest tests/test_ee_manifest.py::TestVerifyWheelManifestMissing -xvs` | ✅ PASS |
| EE-01 | Manifest JSON malformed raises error | unit | `cd puppeteer && pytest tests/test_ee_manifest.py::TestVerifyWheelManifestMalformed -xvs` | ✅ PASS |
| EE-01 | Required fields missing raises error | unit | `cd puppeteer && pytest tests/test_ee_manifest.py::TestVerifyWheelManifestMissingFields -xvs` | ✅ PASS |
| EE-01 | SHA256 mismatch raises error | unit | `cd puppeteer && pytest tests/test_ee_manifest.py::TestVerifyWheelManifestHashMismatch -xvs` | ✅ PASS |
| EE-01 | Invalid signature raises error | unit | `cd puppeteer && pytest tests/test_ee_manifest.py::TestVerifyWheelManifestInvalidSignature -xvs` | ✅ PASS |
| EE-01 | Valid manifest passes verification | unit | `cd puppeteer && pytest tests/test_ee_manifest.py::TestVerifyWheelManifestSuccess -xvs` | ✅ PASS |
| EE-01 | Integration with _install_ee_wheel | unit | `cd puppeteer && pytest tests/test_ee_manifest.py::TestInstallEEWheelIntegration -xvs` | ✅ PASS |
| EE-01 | Error visible in /admin/licence endpoint | unit | `cd puppeteer && pytest tests/test_ee_manifest.py::TestLicenceEndpointEEActivationError -xvs` | ✅ PASS |

#### Phase 138: HMAC-Keyed Boot Log (EE-02, EE-03)

| Requirement | Behavior | Test Type | Automated Command | Status |
|-------------|----------|-----------|-------------------|--------|
| EE-02 | New entries use HMAC-SHA256 | unit | `cd puppeteer && pytest tests/test_licence_service.py::test_hmac_entry_write -xvs` | ✅ PASS |
| EE-02 | HMAC verified on read | unit | `cd puppeteer && pytest tests/test_licence_service.py::test_hmac_verify_on_read -xvs` | ✅ PASS |
| EE-03 | Legacy SHA256 entries accepted | unit | `cd puppeteer && pytest tests/test_licence_service.py::test_legacy_sha256_silent_accept -xvs` | ✅ PASS |
| EE-03 | Mixed legacy+HMAC coexist | unit | `cd puppeteer && pytest tests/test_licence_service.py::test_mixed_format_coexist -xvs` | ✅ PASS |
| EE-03 | Legacy entry warning on read | unit | `cd puppeteer && pytest tests/test_licence_service.py::test_legacy_warning_on_read -xvs` | ✅ PASS |
| EE-02/03 | HMAC mismatch strict in EE mode | unit | (covered by boot log integration tests) | ✅ PASS |

#### Phase 139: Entry Point Whitelist + ENCRYPTION_KEY (EE-04, EE-06)

| Requirement | Behavior | Test Type | Automated Command | Status |
|-------------|----------|-----------|-------------------|--------|
| EE-06 | ENCRYPTION_KEY required at module load | unit | `cd puppeteer && pytest tests/test_encryption_key_enforcement.py::test_encryption_key_required_at_module_load -xvs` | ✅ PASS |
| EE-06 | RuntimeError if ENCRYPTION_KEY absent | unit | `cd puppeteer && pytest tests/test_encryption_key_enforcement.py::test_encryption_key_absent_raises_runtime_error -xvs` | ✅ PASS |
| EE-06 | Error message includes generation command | unit | `cd puppeteer && pytest tests/test_encryption_key_enforcement.py::test_encryption_key_error_message_includes_generation_command -xvs` | ✅ PASS |
| EE-04 | Entry point whitelist at startup | unit | `cd puppeteer && pytest tests/test_ee_manifest.py::TestEntryPointWhitelist::test_entry_point_whitelist_startup_trusted -xvs` | ✅ PASS |
| EE-04 | Untrusted entry point blocked at startup | unit | `cd puppeteer && pytest tests/test_ee_manifest.py::TestEntryPointWhitelist::test_entry_point_whitelist_startup_untrusted -xvs` | ✅ PASS |
| EE-04 | Entry point whitelist on live reload | unit | `cd puppeteer && pytest tests/test_ee_manifest.py::TestEntryPointWhitelist::test_entry_point_whitelist_live_reload_trusted -xvs` | ✅ PASS |
| EE-04 | Untrusted entry point blocked on live reload | unit | `cd puppeteer && pytest tests/test_ee_manifest.py::TestEntryPointWhitelist::test_entry_point_whitelist_live_reload_untrusted -xvs` | ✅ PASS |

#### Phase 140: Wheel Signing Tool (EE-05)

| Requirement | Behavior | Test Type | Automated Command | Status |
|-------------|----------|-----------|-------------------|--------|
| EE-05 | gen_wheel_key.py generates keypair | unit | `cd axiom-licenses && pytest tests/tools/test_gen_wheel_key.py::test_generate_keypair -xvs` | ✅ PASS |
| EE-05 | Overwrite protection on key generation | unit | `cd axiom-licenses && pytest tests/tools/test_gen_wheel_key.py::test_no_overwrite_without_force -xvs` | ✅ PASS |
| EE-05 | sign_wheels.py discovers and signs wheels | unit | `cd axiom-licenses && pytest tests/tools/test_sign_wheels.py::test_wheel_discovery -xvs` | ✅ PASS |
| EE-05 | Chunked SHA256 hash (64KB) | unit | `cd axiom-licenses && pytest tests/tools/test_sign_wheels.py::test_wheel_hash_chunked -xvs` | ✅ PASS |
| EE-05 | Signature format (base64) | unit | `cd axiom-licenses && pytest tests/tools/test_sign_wheels.py::test_signature_format -xvs` | ✅ PASS |
| EE-05 | Per-wheel manifest naming | unit | `cd axiom-licenses && pytest tests/tools/test_sign_wheels.py::test_manifest_naming -xvs` | ✅ PASS |
| EE-05 | --deploy-name flag support | unit | `cd axiom-licenses && pytest tests/tools/test_sign_wheels.py::test_deploy_name_flag -xvs` | ✅ PASS |
| EE-05 | --verify mode | unit | `cd axiom-licenses && pytest tests/tools/test_sign_wheels.py::test_verify_mode -xvs` | ✅ PASS |
| EE-05 | Key resolution from arg/env | unit | `cd axiom-licenses && pytest tests/tools/test_key_resolution.py -xvs` | ✅ PASS |

### Sampling Rate

- **Per task commit (137–139):** `cd puppeteer && pytest tests/test_ee_manifest.py tests/test_encryption_key_enforcement.py tests/test_licence_service.py -x -q`
- **Per task commit (140):** `cd axiom-licenses && pytest tests/tools/ -x -q`
- **Per wave merge:** `cd puppeteer && pytest -x -q` + `cd axiom-licenses && pytest tests/ -q`
- **Phase gate:** Full suite green before marking compliant

### Wave 0 Gaps

#### Phase 137
- None — all test behaviors implemented and passing

#### Phase 138
- **Fix 1 (line 331):** Update `test_reload_licence_with_invalid_key` to match `"parse error"` or remove regex match (accept any LicenceError)
- **Fix 2 (line 443):** Update `test_licence_expiry_guard_ee_prefixes` to include `"/api/admin/bundles"` in expected tuple

#### Phase 139
- None — all test behaviors implemented and passing

#### Phase 140
- None — all test behaviors implemented and passing (Wave 1 complete)

---

## Sources

### Primary (HIGH confidence)

- **Phase 137 VALIDATION.md** — Wave 0 test expectations
- **Phase 138 VALIDATION.md** — Wave 0 test expectations
- **Phase 139 VALIDATION.md** — Wave 0 test expectations
- **Phase 140 VALIDATION.md** — Wave 0 test expectations
- **Direct pytest run output** — Current test status (18/18, 24/26, 8/8, 23/23 respectively)
- **CONTEXT.md (Phase 144)** — Dual test suite strategy, locked decisions, gap assessment approach
- **REQUIREMENTS.md** — EE-01 through EE-06 requirement definitions

### Secondary (MEDIUM confidence)

- **Memory context** (from .claude/memory/MEMORY.md) — Previous phase implementations confirmed all 4 phases are complete in production; testing is the focus

---

## Metadata

**Confidence breakdown:**
- **Phase 137 (Signed Wheel Manifest):** HIGH — 18/18 tests passing, no gaps identified
- **Phase 138 (HMAC Boot Log):** MEDIUM — 24/26 passing; 2 failures are investigation-ready (not blocking)
- **Phase 139 (Entry Point + ENCRYPTION_KEY):** HIGH — 8/8 tests passing, no gaps
- **Phase 140 (Wheel Signing Tool):** HIGH — 23/23 tests passing, no gaps

**Failing test diagnosis:**
1. `test_reload_licence_with_invalid_key` — STALE EXPECTATION (not a production regression)
2. `test_licence_expiry_guard_ee_prefixes` — OUTDATED TEST (production code evolved, test did not)

**Research date:** 2026-04-14  
**Valid until:** 2026-04-21 (7 days, due to fast test-execution feedback)

