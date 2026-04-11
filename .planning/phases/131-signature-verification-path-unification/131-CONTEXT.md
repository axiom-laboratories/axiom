# Phase 131: Signature Verification Path Unification - Context

**Gathered:** 2026-04-11
**Status:** Ready for planning

<domain>
## Phase Boundary

Fix the countersigning gap between on-demand jobs and scheduled jobs so both paths deliver a server-signed payload that nodes can verify with `verification.key`. Unify the countersigning logic into a single service method. Fix the missing HMAC stamping for scheduled job fires. Backend-only — no frontend or API contract changes.

</domain>

<decisions>
## Implementation Decisions

### Fix scope — unified service method
- Extract countersigning into `SignatureService.countersign_for_node(script_content: str) -> str` — returns the server-signed base64 signature
- Both `main.py` `create_job()` route handler and `scheduler_service._fire_job()` call this single method
- `main.py` existing inline block (nested imports, dual-path key resolution, fallback logging) is replaced with a clean `SignatureService.countersign_for_node()` call
- Signature logic lives in one place: `signature_service.py`

### Missing signing key behavior — hard fail everywhere
- `SignatureService.countersign_for_node()` raises an exception if `signing.key` is absent or unreadable
- **On-demand jobs**: catch the exception in `create_job()` route, return HTTP 500 with a clear message ("Server signing key unavailable — contact admin")
- **Scheduled jobs**: catch in `_fire_job()`, mark `fire_log.status = 'signing_error'`, write an audit log entry, and return without creating a `Job` — do NOT silently dispatch an unsigned payload
- This is a security boundary: dispatching without countersigning means nodes will always reject the job anyway, so silent continuation is strictly worse than failing loudly

### HMAC integrity for scheduled job fires — fix in this phase
- `scheduler_service._fire_job()` currently creates `Job` ORM objects directly and never stamps `signature_hmac`
- Fix: after countersigning, compute and set `new_job.signature_hmac` using `compute_signature_hmac(ENCRYPTION_KEY, signature_payload, signature_id, guid)` — same pattern as `job_service.create_job()`
- This ensures the SEC-02 dispatch-time HMAC check covers scheduled jobs, not just on-demand jobs

### Claude's Discretion
- Exact signing key path resolution logic inside `SignatureService.countersign_for_node()` (whether to keep the `/app/secrets/` + `secrets/` two-path fallback or canonicalize via an env var)
- Whether to add a startup health check warning when `signing.key` is absent
- Exact wording of HTTP 500 error message for missing key

</decisions>

<specifics>
## Specific Ideas

- The `fire_log.status = 'signing_error'` approach keeps the existing fire log pattern and makes failures queryable through the scheduler health endpoint
- The audit log entry should use `action="job:signing_error"` and include `scheduled_job_id` and `error` in the detail dict so operators can diagnose

</specifics>

<code_context>
## Existing Code Insights

### Reusable Assets
- `SignatureService.verify_payload_signature()` in `signature_service.py` — the pattern to follow for `countersign_for_node()`
- `compute_signature_hmac()` in `security.py` — already imported in `job_service.py`; `scheduler_service.py` will need to import it too
- Fire log pattern in `scheduler_service._fire_job()` — `fire_log.status = 'skipped_overlap'` is the existing model for non-fatal skips; `'signing_error'` follows the same pattern
- `AuditLog` import pattern in `scheduler_service.py` uses try/except for CE mode where `AuditLog` may be absent — same pattern needed for the signing error audit entry

### Established Patterns
- Inline imports in service files (`from ..security import ...`) are already used in `scheduler_service.py`
- `job_service.create_job()` stamps `signature_hmac` at lines 563–572 — exact logic to replicate in `_fire_job()`
- Route handler error handling: `raise HTTPException(status_code=500, detail=...)` is the standard pattern for unrecoverable errors in `main.py`

### Integration Points
- `signature_service.py`: new `countersign_for_node(script_content: str) -> str` static method
- `main.py` `create_job()`: replace inline countersign block (lines ~1481–1501) with `SignatureService.countersign_for_node()` call
- `scheduler_service.py` `_fire_job()`: add countersign call + HMAC stamp before `session.add(new_job)`
- Signing key location: `/app/secrets/signing.key` (production) or `secrets/signing.key` (local dev) — same fallback already in `main.py`

</code_context>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 131-signature-verification-path-unification*
*Context gathered: 2026-04-11*
