# Phase 168: SIEM Audit Streaming (EE) - Context

**Gathered:** 2026-04-18
**Status:** Ready for planning

<domain>
## Phase Boundary

Build a real-time audit log streaming service, EE-gated, that batches audit events from the existing `audit()` function, formats them as CEF, masks sensitive fields, and delivers to a configurable SIEM destination (HTTP webhook and/or syslog). Covers: SIEM service layer, admin UI config, field masking, retry + backoff, admin status surface, and EE gating. The local `audit_log` DB table is unaffected in all SIEM states (disabled, healthy, degraded).

</domain>

<decisions>
## Implementation Decisions

### EE Gating (carried from Phase 167 pattern)
- **D-01:** SIEM service lives in `puppeteer/ee/services/siem_service.py`. CE users get 402 on all `/admin/siem/*` endpoints via a stub router in `agent_service/ee/interfaces/siem.py`. CE audit log write path (`deps.py:audit()`) is completely unaffected.
- **D-02:** `app.state.siem_service` is initialized in main.py lifespan, following the VaultService pattern. If no `SIEMConfig` row exists or `enabled=false`, service is dormant — silent, no errors.

### Event Capture
- **D-03:** Hook directly into `deps.py:audit()`. After scheduling the DB insert task, `audit()` also calls `get_siem_service().enqueue(event)` — a non-blocking call that pushes to the in-memory queue. No change to the external signature of `audit()`.
- **D-04:** `siem_service.py` exposes a module-level singleton via `get_siem_service() -> Optional[SIEMService]`. Set by main.py on startup: `siem_service.set_active(instance)`. Returns `None` in CE/dormant mode — `audit()` checks for None before calling enqueue. Mirrors the VaultService singleton pattern used for secrets injection.

### Transport Backends
- **D-05:** Phase 168 implements two backends: **webhook** (HTTP POST with CEF body) and **syslog** (UDP/TCP, RFC 5424, CEF payload). The `SIEMConfig` row has a `backend` field: `"webhook"` or `"syslog"`. Exactly one backend is active per config.
- **D-06:** Syslog protocol is configurable: `UDP` (default, fire-and-forget) or `TCP` (connection-oriented). Uses Python's `logging.handlers.SysLogHandler` — no additional dependencies. Protocol selector in the admin UI.
- **D-07:** CEF format is used for both backends. Webhook: CEF in the HTTP body (`Content-Type: application/cef`). Syslog: CEF as the syslog message body (standard enterprise SIEM convention).

### Batch Queue
- **D-08:** In-memory `asyncio.Queue` with a hard cap of 10,000 events. Fast, zero DB overhead. Events in the buffer are lost on crash — accepted trade-off since the local `audit_log` table is always the canonical record (SIEM-06 compliant).
- **D-09:** Flush triggers: (1) queue reaches 100 events, OR (2) APScheduler fires every 5 seconds — whichever comes first. Exactly as specified in SIEM-02.
- **D-10:** Queue full policy: drop oldest events. Log a structured warning when dropping. SIEM streaming is best-effort; the local audit_log is unaffected.

### Sensitive Field Masking
- **D-11:** Before transmission, the SIEM formatter scrubs the `detail` JSON for keys matching a keyword list: `password`, `secret`, `token`, `api_key`, `secret_id`, `role_id`, `encryption_key`, and any key ending in `_key` or `_secret`. Matched values are replaced with `"***"`. Keyword matching is case-insensitive.
- **D-12:** Masking is applied at format time (just before transmission) — the `audit_log` DB rows are never modified. The raw event data in the DB remains unredacted for local query/export.

### Retry Logic
- **D-13:** Failed batch deliveries are retried with exponential backoff: 5s → 10s → 20s (max 3 attempts total). If all 3 attempts fail, the batch is dropped and the failure is counted. APScheduler manages the retry schedule.
- **D-14:** After 3 consecutive batch failures (across different flush intervals), `SIEMService` transitions to `DEGRADED` status and logs a structured warning. Service continues accepting new events and attempting future flushes — it does not stop. Non-SIEM operations are unaffected.

### Admin Status Surface
- **D-15:** No new DB table for alerts. Status is in-memory on `SIEMService`: `status: Literal["disabled", "healthy", "degraded"]`, `last_failure: Optional[str]`, `consecutive_failures: int`, `last_checked_at: Optional[datetime]`. Resets to `healthy` on first successful flush after a degraded period.
- **D-16:** Two endpoints: `GET /admin/siem/status` (full detail: address/host, backend type, last_checked_at, error_detail if degraded). `GET /system/health` gains a `siem` field alongside the existing `vault` field.
- **D-17:** Admin UI: SIEM configuration form in `Admin.tsx` (new "SIEM" tab, following the "Vault" tab pattern from Phase 167 / D-11). Fields: backend selector (webhook/syslog), address (URL or host:port), protocol (UDP/TCP, shown only when syslog), CEF device vendor/product (optional branding), enabled toggle, test-connection button. Status indicator (`healthy / degraded / disabled`) in the section header.

### SIEM Config Storage (following VaultConfig pattern)
- **D-18:** `SIEMConfig` table in DB: `backend` (webhook/syslog), `destination` (URL or host), `syslog_port` (int), `syslog_protocol` (UDP/TCP), `cef_device_vendor` (str, default "Axiom"), `cef_device_product` (str, default "MasterOfPuppets"), `enabled` (bool). Env-var bootstrap: `SIEM_BACKEND`, `SIEM_DESTINATION`, `SIEM_ENABLED`. Config editable at runtime via admin UI without restart.

### Claude's Discretion
- Exact CEF header field mapping (device severity, signatureId naming for each action type)
- APScheduler job naming for flush/retry tasks
- Error message exact wording (intent captured in D-14, D-10)
- SIEMConfig table column defaults and nullable constraints
- Whether `cef_device_vendor`/`cef_device_product` are exposed in admin UI or just env-var configurable

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Requirements
- `.planning/REQUIREMENTS.md` §SIEM-01–SIEM-06 — Six requirements covering config, batching, CEF format, masking, retry, and disable-without-affecting-local-log

### Prior Phase Context
- `.planning/phases/167-hashicorp-vault-integration-ee/167-CONTEXT.md` — EE service pattern (singleton, module-level accessor, app.state, CE stub router structure, VaultService lifecycle as template)

### Architecture
- `puppeteer/agent_service/deps.py` — `audit()` function (integration point at line ~148); module-level singleton pattern
- `puppeteer/agent_service/db.py` — `AuditLog` table schema (id, username, action, resource_id, detail, timestamp)
- `puppeteer/ee/services/vault_service.py` — Template for EE service structure (status model, startup/shutdown, singleton accessor)
- `puppeteer/agent_service/ee/interfaces/audit.py` — CE stub router pattern (402 responses)
- `puppeteer/agent_service/ee/routers/audit_router.py` — EE audit router (existing, may need SIEM status endpoint added)
- `puppeteer/agent_service/main.py` — Lifespan startup pattern for app.state.vault_service (SIEM follows same)

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `deps.py:audit()`: integration point — add `get_siem_service().enqueue(event)` call inside existing `_insert()` coroutine or alongside it
- `APScheduler`: already configured in scheduler_service.py — reuse for 5s flush interval and retry scheduling
- `security.py:cipher_suite`: Fernet encryption for sensitive config fields (e.g., no secrets in SIEMConfig, but pattern available if needed)
- `logging.handlers.SysLogHandler`: stdlib, no new dependencies for syslog transport
- `VaultService` lifecycle (startup/shutdown/status): direct template for SIEMService

### Established Patterns
- Module-level singleton with `get_X()` / `set_active(instance)` for EE services accessible from `deps.py`
- `app.state.X_service = XService(config, db)` in main.py lifespan
- CE stubs in `agent_service/ee/interfaces/` return `JSONResponse(status_code=402, ...)`
- EE routers in `agent_service/ee/routers/` imported conditionally based on EE licence check
- Status trinity: `"disabled" / "healthy" / "degraded"` with `last_error` and `last_checked_at` fields

### Integration Points
- `deps.py:audit()` — insert SIEM enqueue call here (no caller changes needed)
- `GET /system/health` — add `siem` field alongside `vault`
- `Admin.tsx` — new "SIEM" tab in existing admin tabbed layout (follows "Vault" tab)
- `agent_service/ee/routers/__init__.py` — register siem_router conditionally

</code_context>

<specifics>
## Specific Ideas

- Local `audit_log` table is always the canonical record — SIEM streaming is explicitly best-effort. Lost-in-buffer events on crash are acceptable because the local DB has them. This framing should be reflected in code comments and admin UI copy.
- The existing `audit()` function must never fail or block due to SIEM issues — `get_siem_service()` returns None gracefully in CE/dormant mode, and `enqueue()` must be fire-and-forget (no await, no exception propagation).
- Masking at format time (not storage time) preserves the raw audit trail for local forensics while protecting SIEM transmissions.

</specifics>

<deferred>
## Deferred Ideas

- Syslog TLS (RFC 5425) — current phase uses plain UDP/TCP. TLS syslog adds cert management complexity; deferred to a later EE hardening phase.
- Splunk HEC native format — CEF covers Splunk via HTTP Event Collector adapter. Native HEC format explicitly out of scope per REQUIREMENTS.md.
- Azure Monitor / AWS CloudWatch / GCP Cloud Logging backends — future EE extensibility phase.
- Configurable failure threshold (user-settable, not hardcoded to 3) — deferred; rarely-tuned parameter not worth the UI complexity now.
- Persisted `SIEMAlert` DB records — in-memory status is sufficient for Phase 168; persistent alert history deferred.

</deferred>

---

*Phase: 168-siem-audit-streaming-ee*
*Context gathered: 2026-04-18*
