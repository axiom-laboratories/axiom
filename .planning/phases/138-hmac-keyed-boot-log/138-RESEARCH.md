# Phase 138: HMAC-Keyed Boot Log - Research

**Researched:** 2026-04-12
**Domain:** Licence service boot log cryptography
**Confidence:** HIGH

## Summary

Phase 138 upgrades the boot log in `licence_service.py` from a plain SHA256 hash chain to HMAC-SHA256 keyed on `ENCRYPTION_KEY`. The change maintains backward compatibility: new entries use HMAC with a `hmac:` prefix; legacy SHA256 entries (no prefix) continue to be accepted on read. The hash chain mechanism persists for continuity, but new entries store only the HMAC digest (not chained to the previous entry). No forced migration is required — both entry types coexist indefinitely.

**Primary recommendation:** Implement `compute_boot_hmac(key_bytes, iso_ts)` as a sibling to `_compute_hash()` in licence_service.py; modify `_compute_hash()` to continue for chain continuity, and refactor `check_and_record_boot()` to detect entry type by `hmac:` prefix and verify HMAC-tagged entries using constant-time comparison (existing pattern from `security.py`).

<user_constraints>

## User Constraints (from CONTEXT.md)

### Locked Decisions

**Entry format:**
- New HMAC entries: `hmac:<64-char-hex> <ISO8601-timestamp>`
- Legacy SHA256 entries: `<64-char-hex> <ISO8601-timestamp>` (no prefix)
- Reader distinguishes by presence/absence of `hmac:` prefix

**HMAC construction:**
- HMAC is self-contained: `HMAC(ENCRYPTION_KEY, iso_ts)` — no prior entry dependency
- Stored value is the HMAC digest (tagged `hmac:`)
- SHA256 chain (`SHA256(prev_hash + iso_ts)`) continues to run for chain continuity
- Previous line's hex (whether SHA256 or HMAC) read as `prev_hash` for chaining

**Verify on read:**
- When last entry has `hmac:` prefix: recompute `HMAC(ENCRYPTION_KEY, iso_ts)` and compare to stored digest
- Mismatch → `RuntimeError` for EE licences (VALID, GRACE, EXPIRED); `logger.warning()` for CE mode

**Chain continuity on upgrade:**
- On first boot after upgrade, last line is legacy SHA256 entry
- Read its hex value as `prev_hash` for chaining (no special handling needed)
- No chain reset at transition boundary

**Legacy entry read policy:**
- Legacy SHA256 entries (no `hmac:` prefix) accepted silently for chaining
- Emit `logger.warning()` once when last entry read is a legacy SHA256 line
- Warning logged inside `check_and_record_boot()`, not in separate startup path

### Claude's Discretion

- Exact bytes fed to `hmac.new()` as message (e.g., iso_ts only, or iso_ts + salt)
- Whether to preserve `_compute_hash()` as separate private function or inline
- Test fixture structure for new verify-on-read path

### Deferred Ideas (OUT OF SCOPE)

None — discussion stayed within phase scope.

</user_constraints>

<phase_requirements>

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| EE-02 | Boot log uses HMAC-SHA256 keyed on ENCRYPTION_KEY (replacing plain SHA256 hash chain) | HMAC construction via `hmac.new(ENCRYPTION_KEY, iso_ts_bytes, hashlib.sha256)` consistent with existing `security.py` pattern; constant-time comparison via `hmac.compare_digest()` |
| EE-03 | Boot log backward-compatible — legacy SHA256 chain entries accepted on read (no forced migration on upgrade) | Entry prefix detection and silent acceptance of non-`hmac:` entries; warning only when last line is legacy SHA256 |

</phase_requirements>

## Standard Stack

### Core Libraries
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `hmac` | stdlib | HMAC computation (SHA256) | Part of Python stdlib; existing `security.py` already uses `hmac.new()` and `hmac.compare_digest()` for SEC-02 signature HMAC stamping |
| `hashlib` | stdlib | SHA256 hash function | Already imported in licence_service.py; used for existing SHA256 chain; reuses hash for HMAC |
| `datetime`/`timezone` | stdlib | UTC timestamp generation | Already used in `check_and_record_boot()` for ISO8601 timestamps |

### Integration Points
| Component | Location | Pattern |
|-----------|----------|---------|
| ENCRYPTION_KEY | `security.py` (lines 17–28) | `_load_or_generate_encryption_key()` returns bytes; already imported in main.py and exposed |
| HMAC verification pattern | `security.py` (lines 36–45) | `compute_signature_hmac()` and `verify_signature_hmac()` — constant-time comparison via `_hmac.compare_digest()` |
| Boot log path | `licence_service.py` (line 33) | `BOOT_LOG_PATH = Path("secrets/boot.log")` — testable via mock.patch |
| Licence status enum | `licence_service.py` (lines 51–55) | `LicenceStatus.VALID`, `.GRACE`, `.EXPIRED`, `.CE` — used for strict vs. lax error handling |

**ENCRYPTION_KEY availability:** Already imported in `main.py` line 52 as `from .security import ENCRYPTION_KEY`. Direct import into `licence_service.py` (or use as parameter) is straightforward.

## Architecture Patterns

### Recommended Implementation Structure

```python
# In licence_service.py — new HMAC helper (sibling to _compute_hash)

def _compute_boot_hmac(key_bytes: bytes, iso_ts: str) -> str:
    """HMAC-SHA256 of ISO8601 timestamp, keyed on ENCRYPTION_KEY.
    Returns 64-char hex string."""
    message = iso_ts.encode("utf-8")
    return _hmac.new(key_bytes, message, hashlib.sha256).hexdigest()


def _verify_boot_hmac(key_bytes: bytes, stored_hmac: str, iso_ts: str) -> bool:
    """Constant-time HMAC verification for boot log entry.
    Returns True if stored HMAC matches computed HMAC."""
    expected = _compute_boot_hmac(key_bytes, iso_ts)
    return _hmac.compare_digest(stored_hmac, expected)
```

### Entry Format Detection and Parsing

```python
def _parse_boot_log_entry(line: str) -> tuple[str, str, str]:
    """
    Parse a boot log line and detect entry type.
    
    Returns: (entry_type, hex_or_hmac, iso_ts)
    - entry_type: "hmac" or "sha256"
    - hex_or_hmac: the digest/HMAC value
    - iso_ts: the ISO8601 timestamp
    
    Line formats:
    - "hmac:<64-hex> <ISO8601>" → ("hmac", "<64-hex>", "<ISO8601>")
    - "<64-hex> <ISO8601>" → ("sha256", "<64-hex>", "<ISO8601>")
    """
    if line.startswith("hmac:"):
        # New format: "hmac:<hex> <iso_ts>"
        parts = line.split(" ", 1)
        hmac_part = parts[0][5:]  # strip "hmac:" prefix
        iso_ts = parts[1] if len(parts) > 1 else ""
        return ("hmac", hmac_part, iso_ts)
    else:
        # Legacy format: "<hex> <iso_ts>"
        parts = line.split(" ", 1)
        hex_val = parts[0]
        iso_ts = parts[1] if len(parts) > 1 else ""
        return ("sha256", hex_val, iso_ts)
```

### Modified `check_and_record_boot()` Flow

**Current flow (SHA256-only):**
1. Read last line, extract `prev_hash` and `last_ts`
2. Detect rollback if `last_ts > now_ts`
3. Compute new hash: `SHA256(prev_hash + now_ts)`
4. Write new line: `<new_hash> <now_ts>`

**New flow (mixed format with HMAC-on-write):**
1. Read last line, detect entry type via prefix
2. Extract hash/HMAC and timestamp
3. **If last entry is HMAC:** verify HMAC matches expected value (raise or warn on mismatch)
4. **If last entry is SHA256:** log warning once ("legacy SHA256 detected — migration in progress")
5. Detect rollback if `last_ts > now_ts` (unchanged)
6. Compute new hash for chain: `SHA256(prev_hash + now_ts)` (unchanged)
7. **Write new line as HMAC:** compute `HMAC(ENCRYPTION_KEY, now_ts)`, write `hmac:<hmac_hex> <now_ts>`

### Error Handling: Strict vs. Lax

Same pattern as existing rollback handling (licence_service.py lines 182, 214–216):

```python
strict_clock = licence_status != LicenceStatus.CE

# On HMAC mismatch:
if hmac_mismatch_detected:
    msg = f"Boot log HMAC verification failed — possible tampering"
    if strict_clock:  # EE: VALID, GRACE, EXPIRED
        raise RuntimeError(msg)
    else:  # CE mode
        logger.warning(msg)
```

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| HMAC computation | Custom SHA256 concatenation | `hmac.new(key, msg, hashlib.sha256)` | Constant-time implementation; avoids padding oracle attacks; standard library |
| HMAC constant-time comparison | `stored == computed` | `hmac.compare_digest(a, b)` | Prevents timing-based forgery; already used in SEC-02 (security.py line 45) |
| Timestamp encoding | Ad-hoc string→bytes | `iso_ts.encode("utf-8")` | Consistent encoding; RFC 3339 UTF-8 is standard for JSON timestamps |
| Boot log parsing | Regex | `line.split(" ", 1)` + prefix check | Simple, readable; entry format is strict (one space separator, one timestamp per line) |
| Key management | Pass raw bytes around | Import `ENCRYPTION_KEY` from `security.py` | Single source of truth; consistent with existing pattern (main.py line 52) |

**Key insight:** The HMAC is self-contained (verifiable without prior entries) — resist the temptation to build custom "chained verification" logic. Each HMAC entry stands alone; the chain continues separately for continuity.

## Common Pitfalls

### Pitfall 1: Confusing Chain Continuity with HMAC Verification
**What goes wrong:** Developer assumes HMAC entries must be chained to the previous entry (i.e., `HMAC(key, prev_hash + iso_ts)`) to verify.

**Why it happens:** The SHA256 chain mechanism is still present. It's easy to conflate "the line contains a hash/HMAC" with "the entry must be cryptographically linked to the previous entry."

**How to avoid:** HMAC entries are **self-contained** — `HMAC(key, iso_ts)` is verifiable with just the key and the timestamp. The SHA256 chain (`SHA256(prev_hash + iso_ts)`) continues to run in the background for continuity and fork detection, but it's separate from HMAC verification. Verify HMAC on read; maintain SHA256 chain on write.

**Warning signs:** Code that tries to re-verify the entire chain by checking each HMAC against the previous entry; HMAC verification logic that expects a `prev_hash` parameter.

### Pitfall 2: Forgetting to Distinguish Entry Type on Read
**What goes wrong:** Code assumes all entries are HMAC, tries to parse a legacy SHA256 entry as `hmac:<hex>`, and crashes or misinterprets the data.

**Why it happens:** Tempting to just refactor `_compute_hash()` without updating the read path; assumes all existing files have been migrated.

**How to avoid:** Always check for `hmac:` prefix before attempting HMAC verification. Legacy entries (no prefix) are valid and will coexist indefinitely — handle both types explicitly. Use the `_parse_boot_log_entry()` helper (above) to centralize format detection.

**Warning signs:** HMAC verification failure on the first line after upgrade; KeyError or IndexError when accessing hex fields.

### Pitfall 3: Timing-Based Forgery via String Comparison
**What goes wrong:** Code compares stored HMAC to computed HMAC using `==`, allowing an attacker to guess one byte at a time (timing side-channel).

**Why it happens:** Easy to overlook; equality works for casual testing. Only reveals itself under timing analysis or fuzzing.

**How to avoid:** **Always use `hmac.compare_digest()`** for HMAC comparison. This is already the pattern in `security.py` (line 45). No exceptions.

**Warning signs:** HMAC comparison using `if stored_hmac == expected_hmac:` or `.equals()` methods; absence of `hmac.compare_digest()` in the codebase.

### Pitfall 4: Encoding Mismatch Between Write and Verify
**What goes wrong:** HMAC computed during write uses `iso_ts.encode("utf-8")`, but verification encodes differently (e.g., `iso_ts.encode("ascii")` or `iso_ts.encode("latin-1")`), leading to mismatch.

**Why it happens:** ISO8601 timestamps are ASCII-compatible, so both encodings produce the same bytes in the common case. Testing with ASCII-only timestamps hides the bug. Unicode timestamps (if ever supported) would fail.

**How to avoid:** Use **`utf-8` consistently** in both compute and verify. Document the encoding in the function docstring. The timestamp string is ISO8601 (RFC 3339), which is ASCII; UTF-8 is the safe, future-proof choice.

**Warning signs:** HMAC verification fails sporadically; test passes for simple timestamps but fails for edge cases.

### Pitfall 5: Importing ENCRYPTION_KEY Too Late
**What goes wrong:** `licence_service.py` tries to import `ENCRYPTION_KEY` from `security.py` at the module level, but `security.py` hasn't finished initializing (circular import or key not loaded yet).

**Why it happens:** `ENCRYPTION_KEY` is generated lazily in `_load_or_generate_encryption_key()`. If `licence_service.py` imports it at module load, and `main.py` hasn't called `load_dotenv()` yet, the key might not be available.

**How to avoid:** Import `ENCRYPTION_KEY` from `security.py` (it's already exposed as a module-level variable). Main.py already does this (line 52). If there's a circular import, pass ENCRYPTION_KEY as a parameter to `check_and_record_boot()`, or import it inside the function that needs it. Test initialization order explicitly.

**Warning signs:** `AttributeError: 'NoneType' object has no attribute ...` during startup; ENCRYPTION_KEY is `None`; test fails on first boot but passes on second.

## Code Examples

Verified patterns from existing codebase:

### HMAC Computation (Pattern from security.py:36–39)
```python
import hmac as _hmac
import hashlib

def compute_signature_hmac(key_bytes: bytes, signature_payload: str, signature_id: str, job_id: str) -> str:
    """HMAC-SHA256 tag binding payload to its job and signature. key_bytes = ENCRYPTION_KEY."""
    message = f"{signature_payload}:{signature_id}:{job_id}".encode("utf-8")
    return _hmac.new(key_bytes, message, hashlib.sha256).hexdigest()
```

**For boot log HMAC, simplified to single input (iso_ts):**
```python
def _compute_boot_hmac(key_bytes: bytes, iso_ts: str) -> str:
    """HMAC-SHA256 of ISO8601 timestamp."""
    message = iso_ts.encode("utf-8")
    return _hmac.new(key_bytes, message, hashlib.sha256).hexdigest()
```

### Constant-Time Comparison (Pattern from security.py:42–45)
```python
def verify_signature_hmac(key_bytes: bytes, stored_hmac: str, signature_payload: str, signature_id: str, job_id: str) -> bool:
    """Constant-time HMAC verification. Returns True if tag matches."""
    expected = compute_signature_hmac(key_bytes, signature_payload, signature_id, job_id)
    return _hmac.compare_digest(stored_hmac, expected)
```

**For boot log HMAC verification:**
```python
def _verify_boot_hmac(key_bytes: bytes, stored_hmac: str, iso_ts: str) -> bool:
    """Constant-time HMAC verification for boot log entry."""
    expected = _compute_boot_hmac(key_bytes, iso_ts)
    return _hmac.compare_digest(stored_hmac, expected)
```

### Licence Status Conditional Logic (Pattern from licence_service.py:182, 214–216)
```python
strict_clock = licence_status != LicenceStatus.CE  # True for VALID, GRACE, EXPIRED; False for CE

# On error:
if error_condition:
    msg = "Error description"
    if strict_clock:
        raise RuntimeError(msg)
    logger.warning(msg)
    return False
```

**Applied to HMAC mismatch:**
```python
strict_hmac = licence_status != LicenceStatus.CE
if not _verify_boot_hmac(ENCRYPTION_KEY, stored_hmac, iso_ts):
    msg = "Boot log HMAC verification failed — possible tampering"
    if strict_hmac:
        raise RuntimeError(msg)
    logger.warning(msg)
```

### Test Fixtures Pattern (from test_licence_service.py:148–171)
Existing test structure for boot log:
```python
def test_clock_rollback_detection():
    from agent_service.services.licence_service import check_and_record_boot, LicenceStatus
    from datetime import datetime, timezone, timedelta
    import hashlib

    with tempfile.TemporaryDirectory() as tmpdir:
        boot_log = Path(tmpdir) / "boot.log"
        
        # Write a future timestamp to simulate rollback
        future_ts = (datetime.now(timezone.utc) + timedelta(hours=2)).isoformat()
        future_hash = hashlib.sha256(f"{future_ts}".encode()).hexdigest()
        boot_log.write_text(f"{future_hash} {future_ts}\n")

        with patch("agent_service.services.licence_service.BOOT_LOG_PATH", boot_log):
            result = check_and_record_boot(LicenceStatus.CE)
        
        assert result is False, "Expected rollback to be detected"
```

**New test structure for HMAC verification:**
```python
def test_hmac_verify_on_read():
    """HMAC entry on last line is verified on read; mismatch raises in EE mode."""
    from agent_service.services.licence_service import check_and_record_boot, _compute_boot_hmac, LicenceStatus
    from agent_service.security import ENCRYPTION_KEY
    from datetime import datetime, timezone
    import hmac as _hmac
    
    with tempfile.TemporaryDirectory() as tmpdir:
        boot_log = Path(tmpdir) / "boot.log"
        
        # Write a valid HMAC entry
        now_ts = datetime.now(timezone.utc).isoformat()
        correct_hmac = _compute_boot_hmac(ENCRYPTION_KEY, now_ts)
        boot_log.write_text(f"hmac:{correct_hmac} {now_ts}\n")
        
        # Read and verify — should succeed
        with patch("agent_service.services.licence_service.BOOT_LOG_PATH", boot_log):
            result = check_and_record_boot(LicenceStatus.CE)
        
        assert result is True
        
        # Write an invalid HMAC entry (tampering simulation)
        bad_hmac = "0" * 64  # Wrong digest
        boot_log.write_text(f"hmac:{bad_hmac} {now_ts}\n")
        
        # Read with invalid HMAC in EE mode — should raise
        with patch("agent_service.services.licence_service.BOOT_LOG_PATH", boot_log):
            with pytest.raises(RuntimeError, match="HMAC verification failed"):
                check_and_record_boot(LicenceStatus.VALID)
```

## State of the Art

| Aspect | Previous Approach | Current Approach | When Changed |
|--------|-------------------|------------------|--------------|
| Boot log chaining | Plain SHA256 hash chain (only) | SHA256 chain + HMAC entries | Phase 138 (2026-04-12) |
| HMAC vs. chain | (N/A — no HMAC before) | HMAC self-contained; chain separate | Phase 138 |
| Entry format | Single format: `<hex> <ts>` | Two formats: `<hex> <ts>` (legacy) and `hmac:<hex> <ts>` (new) | Phase 138 |
| Key material | (N/A) | ENCRYPTION_KEY from security.py | Phase 138 |

**Deprecated/outdated:**
- **Plain SHA256-only boot log:** Replaced by HMAC in Phase 138. SHA256 chain persists for continuity, but new writes use HMAC.

## Open Questions

1. **ENCRYPTION_KEY initialization timing**
   - What we know: `ENCRYPTION_KEY` is initialized in `security.py` via `_load_or_generate_encryption_key()` at module load; `main.py` imports it (line 52)
   - What's unclear: Will licence_service.py's import of ENCRYPTION_KEY succeed if called before main.py's lifespan startup? Is there a risk of circular import?
   - Recommendation: Test import order explicitly; if there's a timing issue, pass ENCRYPTION_KEY as parameter to `check_and_record_boot()` rather than module-level import

2. **Exact message format for HMAC**
   - What we know: CONTEXT.md specifies `HMAC(ENCRYPTION_KEY, iso_ts)` — timestamp only, no salt or prefix
   - What's unclear: Should we include a domain separator or version tag (e.g., `"boot:" + iso_ts`)? Decision locked in CONTEXT.md to use iso_ts only.
   - Recommendation: Follow CONTEXT.md lock: iso_ts only. If future phases need domain separation, add a version number to entry format (e.g., `hmacv2:...`)

3. **Preserve `_compute_hash()` or inline?**
   - What we know: CONTEXT.md marks this as Claude's discretion
   - What's unclear: Is `_compute_hash()` used elsewhere? (Answer: only in `check_and_record_boot()`.) Should it be kept for readability or inlined?
   - Recommendation: Keep `_compute_hash()` as a separate private function. It remains the mechanism for chain continuity; keeping it explicit clarifies the two-layer architecture (SHA256 chain + HMAC verification). Inlining would obscure the design.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (with asyncio support) |
| Config file | `puppeteer/pytest.ini` (or pytest.cfg if present; defaults to setup.cfg) |
| Quick run command | `cd puppeteer && pytest tests/test_licence_service.py -x` |
| Full suite command | `cd puppeteer && pytest tests/test_licence_service.py` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| EE-02 | HMAC entries written to boot log with `hmac:` prefix and verified against ENCRYPTION_KEY | unit | `pytest tests/test_licence_service.py::test_hmac_entry_write -x` | ❌ Wave 0 |
| EE-02 | HMAC computation matches existing `security.py` pattern (HMAC-SHA256 constant-time) | unit | `pytest tests/test_licence_service.py::test_hmac_constant_time_verify -x` | ❌ Wave 0 |
| EE-03 | Legacy SHA256 entries (no prefix) accepted silently on read; warning logged once | unit | `pytest tests/test_licence_service.py::test_legacy_sha256_silent_accept -x` | ❌ Wave 0 |
| EE-03 | Mixed-format boot log (legacy + HMAC entries) reads correctly; chain maintained | integration | `pytest tests/test_licence_service.py::test_mixed_format_coexist -x` | ❌ Wave 0 |
| EE-02 | HMAC mismatch raises RuntimeError in EE mode (VALID, GRACE, EXPIRED) | unit | `pytest tests/test_licence_service.py::test_hmac_mismatch_strict_ee -x` | ❌ Wave 0 |
| EE-02 | HMAC mismatch logs warning in CE mode (no raise) | unit | `pytest tests/test_licence_service.py::test_hmac_mismatch_ce_lax -x` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `cd puppeteer && pytest tests/test_licence_service.py -x` (quick feedback on HMAC-related tests)
- **Per wave merge:** `cd puppeteer && pytest tests/test_licence_service.py` (all licence_service tests pass)
- **Phase gate:** Full suite green before `/gsd:verify-work` — all HMAC + legacy coexistence tests pass

### Wave 0 Gaps
- [ ] `tests/test_licence_service.py::test_hmac_entry_write` — new test for HMAC entry format and writing
- [ ] `tests/test_licence_service.py::test_hmac_constant_time_verify` — verifies HMAC verification uses constant-time comparison
- [ ] `tests/test_licence_service.py::test_legacy_sha256_silent_accept` — legacy entries accepted silently; warning logged once
- [ ] `tests/test_licence_service.py::test_mixed_format_coexist` — mixed boot log (SHA256 + HMAC) integration test
- [ ] `tests/test_licence_service.py::test_hmac_mismatch_strict_ee` — HMAC mismatch raises RuntimeError in EE mode
- [ ] `tests/test_licence_service.py::test_hmac_mismatch_ce_lax` — HMAC mismatch logs warning in CE mode (no raise)

## Sources

### Primary (HIGH confidence)
- **CONTEXT.md (Phase 138)** — User decisions on entry format, HMAC construction, verification policy, legacy coexistence
- **REQUIREMENTS.md** — EE-02, EE-03 requirement definitions (HMAC-SHA256, backward compatibility)
- **licence_service.py (current implementation)** — SHA256 hash chain, boot log format, rollback detection, strict vs. lax error handling
- **security.py** — `compute_signature_hmac()` and `verify_signature_hmac()` patterns; ENCRYPTION_KEY initialization and exposure
- **test_licence_service.py** — existing test structure (fixtures, mocking, error handling patterns)

### Secondary (MEDIUM confidence)
- **Python stdlib HMAC docs** — `hmac.new()`, `hmac.compare_digest()` usage; constant-time comparison guarantees
- **Python stdlib hashlib docs** — `hashlib.sha256()` usage; integration with hmac module

### Tertiary (LOW confidence)
- (None — all critical information sourced from codebase and user context)

## Metadata

**Confidence breakdown:**
- Standard stack: **HIGH** — HMAC usage is stdlib; security.py already demonstrates the pattern; ENCRYPTION_KEY is an existing module-level export
- Architecture: **HIGH** — CONTEXT.md locks entry format, HMAC construction, and error handling; existing licence_service design is well-understood
- Pitfalls: **HIGH** — Based on common HMAC mistakes and existing codebase patterns (rollback handling, strict vs. lax, constant-time comparison)
- Validation: **HIGH** — Test structure follows existing patterns in test_licence_service.py; nyquist_validation enabled in config.json

**Research date:** 2026-04-12
**Valid until:** 2026-04-19 (7 days — stable domain with no upstream changes expected)
