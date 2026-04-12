# Phase 138: HMAC-Keyed Boot Log - Context

**Gathered:** 2026-04-12
**Status:** Ready for planning

<domain>
## Phase Boundary

Replace the plain SHA256 hash chain in `licence_service.py` (`_compute_hash` / `check_and_record_boot`) with HMAC-SHA256 keyed on `ENCRYPTION_KEY`. New entries written after upgrade use HMAC. Legacy SHA256 entries already in the file are accepted on read without re-verification — no forced migration, mixed entries coexist indefinitely.

</domain>

<decisions>
## Implementation Decisions

### Entry format
- New HMAC entries have an `hmac:` prefix: `hmac:<64-char-hex> <ISO8601-timestamp>`
- Legacy SHA256 entries remain in the existing format: `<64-char-hex> <ISO8601-timestamp>` (no prefix)
- Reader distinguishes entry type by presence/absence of the `hmac:` prefix

### HMAC construction
- HMAC is self-contained: `HMAC(ENCRYPTION_KEY, iso_ts)` — verifiable with just the key and the timestamp stored in the line, without needing the previous entry
- The SHA256 chain computation (`SHA256(prev_hash + iso_ts)`) continues to run for chain continuity — the stored hex from the previous line (whether SHA256 or HMAC) is still read as `prev_hash`
- The stored hash value in the line for new entries is the HMAC digest (tagged `hmac:`)

### Verify on read
- When the last entry has the `hmac:` prefix: re-verify by recomputing `HMAC(ENCRYPTION_KEY, iso_ts)` and comparing to stored digest
- Mismatch → `RuntimeError` for EE licences (VALID, GRACE, EXPIRED); `logger.warning()` for CE mode (same pattern as clock rollback handling)

### Chain continuity on upgrade
- On first boot after upgrade, the last line is a legacy SHA256 entry — read its hex value as `prev_hash` for chaining (no special handling needed; it's an opaque hex string)
- No chain reset at the transition boundary

### Legacy entry read policy
- Legacy SHA256 entries (no `hmac:` prefix) are accepted silently for chaining
- Emit `logger.warning()` once when the last entry read is a legacy SHA256 line (operators know migration is in progress)
- Warning logged inside `check_and_record_boot()`, not in a separate startup path

### Claude's Discretion
- Exact bytes fed to `hmac.new()` as the message (e.g. iso_ts only, or iso_ts + salt)
- Whether to preserve `_compute_hash()` as a separate private function or inline
- Test fixture structure for the new verify-on-read path

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `security.py:compute_signature_hmac()` — already uses `hmac.new(key_bytes, message, hashlib.sha256).hexdigest()` with `_hmac.compare_digest` for constant-time comparison; the same pattern applies here
- `security.py:ENCRYPTION_KEY` — bytes, already loaded from env at module load; `licence_service.py` must import or re-use this value
- `security.py:verify_signature_hmac()` — same constant-time compare pattern to follow for boot log HMAC verification

### Established Patterns
- EE-strict vs CE-lax error handling: `strict_clock = licence_status != LicenceStatus.CE` → `raise RuntimeError` vs `logger.warning()` — apply same pattern for HMAC mismatch
- Boot log truncation to last 1000 lines is already in place — no change needed
- `BOOT_LOG_PATH = Path("secrets/boot.log")` defined at module level in `licence_service.py`

### Integration Points
- `_compute_hash(prev_hash_hex, iso_ts)` in `licence_service.py` — this is the function to modify/replace
- `check_and_record_boot(licence_status)` — the main function; reads last line, detects rollback, appends new entry
- `main.py` lifespan calls `check_and_record_boot()` at startup — no change needed there
- Existing tests in `puppeteer/tests/test_licence_service.py` (lines ~154–635) cover SHA256 chain; new tests needed for HMAC path and legacy coexistence

</code_context>

<specifics>
## Specific Ideas

- Entry format chosen specifically to be self-describing and future-proof (supports adding new algorithm prefixes later, e.g. `sha3:`)
- Verification is intentionally "self-contained" — each HMAC entry can be verified in isolation using just the ENCRYPTION_KEY and its own timestamp; this avoids needing to read N-1 entries to verify entry N
- The warning for legacy entries is informational only — no blocking, no forced migration

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 138-hmac-keyed-boot-log*
*Context gathered: 2026-04-12*
