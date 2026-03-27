# Phase 72: Security Fixes - Context

**Gathered:** 2026-03-26
**Status:** Ready for planning

<domain>
## Phase Boundary

Apply 6 targeted backend security patches closing all CodeQL error-severity and warning-severity alerts in the GitHub Security tab. Covers: reflected XSS in device-approval page, path traversal in vault and installer routes, ReDoS in PII masker, redundant API_KEY crash + node-route auth, and missing CSV content-type enforcement. No new features, no frontend changes.

</domain>

<decisions>
## Implementation Decisions

### API_KEY removal (SEC-05)
- Fully remove `API_KEY` env var, the `try/except` crash block, and the `verify_api_key` function from `security.py`
- Remove `verify_api_key` from all three node-facing routes: `/work/pull`, `/heartbeat`, `/jobs/{guid}/result`
- Researcher must verify service principals do not depend on the global `API_KEY` before planning full deletion
- If `API_KEY` is still present in an operator's env at startup, ignore it silently — no deprecation log

### Path traversal fix pattern (SEC-02 + SEC-03)
- Write a shared helper `validate_path_within(base: Path, candidate: Path) -> Path` in `security.py`
- Helper raises HTTP 400 if `candidate.resolve()` is not relative to `base.resolve()`
- Call the helper from `vault_service.py` (artifact store/delete) and all flagged locations in `main.py`
- Use GitHub Security tab to find the actual current line numbers for SEC-03 alerts (STATE.md notes they have drifted from the original todo)

### Regex safety review (SEC-04)
- Email regex in `mask_pii()` is the CodeQL-flagged pattern — rewrite to a linear bounded form (no catastrophic backtracking on pathological email-like strings)
- Also review the SSN regex (`\d{3}-\d{2}-\d{4}`) while in the function — confirm it is linear or fix if not
- Only change patterns, not the overall mask_pii() recursion logic

### Test coverage
- Claude's discretion on which fixes warrant automated tests
- Priority signals: fixes that are hard to visually verify (ReDoS timing, nosniff header) and fixes with a clear exploit scenario (XSS, path traversal) benefit most from tests

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `security.py`: existing module for auth/validation helpers — `validate_path_within()` belongs here alongside `verify_api_key`, `mask_pii`
- `vault_service.py`: `VAULT_DIR` constant already defined — use it as the base path in the path guard
- `mask_pii()` in `security.py` lines 86–102: current email and SSN regex patterns

### Established Patterns
- `HTTPException(status_code=400, ...)`: existing pattern for invalid input rejection — use for path traversal guard
- `StreamingResponse` with `headers={}` dict: already used in CSV export (line ~873) — add nosniff header to this dict
- Device-approve HTML is inline string in `main.py` (lines ~575–628): `html.escape()` from stdlib is sufficient — no template engine needed

### Integration Points
- Node-facing routes at `main.py` lines 1225, 1234, 1241: remove `api_key: str = Depends(verify_api_key)` parameter from each
- `security.py` import line in `main.py` (line 43–44): remove `verify_api_key` and `API_KEY` from the import tuple after deletion
- `vault_service.py` `store_artifact()` and `delete_artifact()`: add path guard before any file I/O

</code_context>

<specifics>
## Specific Ideas

- For XSS (SEC-01): `html.escape(user_code or "")` — wrap every occurrence of `{user_code}` in the inline HTML response, including the hidden form inputs
- For SEC-03: check GitHub Security tab first — alert locations are the authoritative source; do not guess from old line numbers
- Service principal auth path: `mop_` prefixed keys in the `UserApiKey` table, verified via their own middleware — completely separate from `API_KEY`; researcher should confirm

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 72-security-fixes*
*Context gathered: 2026-03-26*
