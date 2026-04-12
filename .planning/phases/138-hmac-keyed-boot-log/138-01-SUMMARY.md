---
phase: 138-hmac-keyed-boot-log
plan: 01
subsystem: licence-service
tags: [hmac, boot-log, cryptography, backward-compatibility, ee-02, ee-03]
dependency_graph:
  requires: [ee-01-security-foundation]
  provides: [hmac-boot-log-verification, backward-compatible-boot-log]
  affects: [licence-service, licence-state-detection]
tech_stack:
  added: [hmac-sha256, constant-time-comparison, entry-type-detection]
  patterns: [mixed-format-coexistence, strict-vs-lax-error-handling, entry-versioning]
key_files:
  created: []
  modified:
    - puppeteer/agent_service/services/licence_service.py
    - puppeteer/tests/test_licence_service.py
decisions:
  - decision: Entry format versioning via prefix
    rationale: "New HMAC entries use 'hmac:' prefix, legacy SHA256 entries have no prefix. Allows indefinite coexistence without forced migration."
    impact: "Boot log can contain both formats simultaneously; parser detects type and handles accordingly."
  - decision: Strict vs lax error handling based on licence status
    rationale: "EE licences (VALID, GRACE, EXPIRED) require verified boot log integrity; CE mode prioritizes availability over strict validation."
    impact: "HMAC verification failures raise RuntimeError in EE mode, log warning in CE mode (non-blocking)."
metrics:
  duration_minutes: 45
  completed_date: 2026-04-12
  tests_added: 6
  helper_functions: 3
  test_pass_rate: "100% (8/8 tests: 6 new HMAC + 2 existing boot log tests)"
---

# Phase 138 Plan 01: HMAC-Keyed Boot Log — Summary

**HMAC-SHA256 boot log upgrade with full backward compatibility for legacy SHA256 entries.**

## Objective
Upgrade the boot log in `licence_service.py` from plain SHA256 hash chain to HMAC-SHA256 keyed on `ENCRYPTION_KEY`, strengthening EE licence protection by making the boot log cryptographically bound to the encryption key. Legacy SHA256 entries coexist indefinitely with no forced migration.

## Implementation Details

### Helper Functions Added (3)

**1. `_compute_boot_hmac(key_bytes: bytes, iso_ts: str) -> str`**
- HMAC-SHA256 computation of ISO8601 timestamp keyed on ENCRYPTION_KEY
- Returns 64-character hex string
- Implementation: `hmac.new(key_bytes, iso_ts.encode("utf-8"), hashlib.sha256).hexdigest()`

**2. `_verify_boot_hmac(key_bytes: bytes, stored_hmac: str, iso_ts: str) -> bool`**
- Constant-time HMAC verification using `hmac.compare_digest()`
- Compares stored HMAC against freshly computed HMAC for the timestamp
- Prevents timing attacks on verification

**3. `_parse_boot_log_entry(line: str) -> tuple[str, str, str]`**
- Parses boot log line and detects entry type
- Returns: `(entry_type, digest_or_hmac, iso_ts)`
- Handles both formats:
  - New: `hmac:<64-hex> <ISO8601>` → `("hmac", "<64-hex>", "<ISO8601>")`
  - Legacy: `<64-hex> <ISO8601>` → `("sha256", "<64-hex>", "<ISO8601>")`

### Core Function Refactored

**`check_and_record_boot(licence_status: LicenceStatus) -> bool`**

**Entry Type Detection:** After reading last boot log line, calls `_parse_boot_log_entry()` to detect if entry is HMAC or legacy SHA256.

**HMAC Verification Path:** When last entry is "hmac":
- Calls `_verify_boot_hmac(ENCRYPTION_KEY, stored_digest, iso_ts)`
- If verification fails:
  - **EE mode (VALID, GRACE, EXPIRED):** raises `RuntimeError("Boot log HMAC verification failed — possible tampering")`
  - **CE mode:** logs warning via `logger.warning()` and continues (non-blocking)

**Legacy Entry Read Path:** When last entry is "sha256":
- Logs warning once: "Legacy SHA256 boot log entry detected — migration to HMAC in progress, consider rebuilding the boot log"
- Continues without verification (silent acceptance, no block)

**Write Path:** 
- Computes new SHA256 chain hash for continuity: `SHA256(prev_hash + now_ts)` (using existing `_compute_hash()`)
- Computes new HMAC: `_compute_boot_hmac(ENCRYPTION_KEY, now_ts)`
- Writes line as: `f"hmac:{hmac_hex} {now_ts}"`
- New entries are self-contained HMACs; chain is computed separately for legacy continuity

**Rollback Detection:** Unchanged — if `last_ts > now_ts`, raises `RuntimeError` in strict mode or logs warning in CE mode.

### Entry Format

- **New:** `hmac:<64-hex-hmac> <ISO8601-timestamp>`
  - Example: `hmac:25bf03ccced81e0fc397b522f3f6bccae4483eae4ea63c4722b90993c7a22c24 2026-04-12T20:46:11.314862+00:00`

- **Legacy:** `<64-hex-sha256> <ISO8601-timestamp>` (no prefix)
  - Example: `5a1f2e3d4c5b6a7f8e9d0a1b2c3d4e5f6a7b8c9d0a1b2c3d4e5f6a7b8c9d0a 2026-04-11T15:30:00+00:00`

## Tests Added (6)

### 1. `test_hmac_entry_write()`
**Verifies:** New boot entries are written with `hmac:` prefix and HMAC-SHA256 digest
- Genesis boot: creates first entry with HMAC
- Verifies format: `hmac:<64-hex> <ISO8601>`
- Verifies HMAC is 64 hex characters

### 2. `test_hmac_verify_on_read()`
**Verifies:** HMAC entry on last line is verified on read; mismatch raises in EE mode
- Writes valid HMAC entry
- Corrupts HMAC in boot log
- Verifies `RuntimeError` raised when reading with EE licence status (VALID)
- Message: "Boot log HMAC verification failed — possible tampering"

### 3. `test_hmac_mismatch_ce_lax()`
**Verifies:** HMAC mismatch logs warning in CE mode (non-blocking)
- Writes valid HMAC entry
- Corrupts HMAC
- Verifies no exception raised with CE licence status
- Verifies warning logged: "Boot log HMAC verification failed — possible tampering"

### 4. `test_legacy_sha256_silent_accept()`
**Verifies:** Legacy SHA256 entries (no `hmac:` prefix) are read silently without verification
- Writes legacy SHA256 entry (no prefix)
- Reads and records boot with both CE and VALID licence status
- Verifies success (no raise, no warning about mismatch)

### 5. `test_legacy_warning_on_read()`
**Verifies:** Warning is logged once when last entry is legacy SHA256
- Writes legacy SHA256 entry
- Reads and records boot
- Verifies warning logged: "Legacy SHA256 boot log entry detected — migration to HMAC in progress, consider rebuilding the boot log"

### 6. `test_mixed_format_coexist()`
**Verifies:** Boot log with both legacy SHA256 and new HMAC entries reads correctly; chain maintained
- Writes legacy SHA256 entry (genesis)
- Records boot (creates new HMAC entry)
- Verifies both entries coexist in log
- Verifies second entry has HMAC format
- Verifies HMAC verification passes for second entry
- Verifies legacy entry doesn't block new HMAC entries

## Test Results

All 8 tests pass (6 new HMAC + 2 existing boot log integration tests):

```
tests/test_licence_service.py::test_hmac_entry_write PASSED              [ 12%]
tests/test_licence_service.py::test_hmac_verify_on_read PASSED           [ 25%]
tests/test_licence_service.py::test_hmac_mismatch_ce_lax PASSED          [ 37%]
tests/test_licence_service.py::test_legacy_sha256_silent_accept PASSED   [ 50%]
tests/test_licence_service.py::test_legacy_warning_on_read PASSED        [ 62%]
tests/test_licence_service.py::test_mixed_format_coexist PASSED          [ 75%]
tests/test_licence_service.py::test_check_and_record_boot_integration PASSED [ 87%]
tests/test_licence_service.py::test_clock_rollback_detection PASSED      [100%]

======================== 8 passed in 0.06s =========================
```

## Backward Compatibility

**Legacy entry handling:**
- All existing boot logs with plain SHA256 entries continue to work without modification
- New entries added after upgrade use HMAC format
- Mixed-format logs (legacy + HMAC) are fully supported
- No forced migration or log truncation required

**Import changes:**
- Added: `import hmac as _hmac` (same pattern as security.py)
- Added: `from agent_service.security import ENCRYPTION_KEY`

## Requirements Satisfied

- **EE-02:** HMAC-SHA256 boot log keyed on ENCRYPTION_KEY with constant-time verification
- **EE-03:** Full backward compatibility with legacy SHA256 entries; indefinite coexistence without forced migration

## Key Links

From `licence_service.py`:
- `_compute_boot_hmac()` — used by `check_and_record_boot()` to write new entries
- `_verify_boot_hmac()` — used by `check_and_record_boot()` to verify HMAC entries on read
- `_parse_boot_log_entry()` — used by `check_and_record_boot()` to detect entry type
- `ENCRYPTION_KEY` import from `agent_service.security` — provides keying material for HMAC

From `test_licence_service.py`:
- All 6 tests mock `BOOT_LOG_PATH` via `patch()` and use `tempfile.TemporaryDirectory()`
- Tests use `caplog` fixture for warning assertions
- Tests verify both strict (EE) and lax (CE) error handling modes

## Deviations from Plan

None — plan executed exactly as written. All 4 tasks completed:
1. **Task 1:** 6 test stubs created (RED phase) ✓
2. **Task 2:** 3 helper functions implemented; HMAC write/verify/legacy tests pass (GREEN phase) ✓
3. **Task 3:** `check_and_record_boot()` refactored for mixed HMAC+legacy support (REFACTOR phase) ✓
4. **Task 4:** All existing tests pass; no regression; test_check_and_record_boot_integration updated for new format ✓

## Known Limitations

None identified. The implementation fully satisfies all must-haves and success criteria.

## Related Work

**Phase 137 (completed):** EE wheel manifest verification with Ed25519 signatures
**Future:** Boot log migration tooling (optional) to aid operators in migrating legacy entries to HMAC format (not in scope for this phase)

