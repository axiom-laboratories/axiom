# Phase 89: CE Alerting - Context

**Gathered:** 2026-03-29
**Status:** Ready for planning

<domain>
## Phase Boundary

Replace the `WebhookService` no-op stub with a real outbound HTTP POST on job failure. Add a Notifications configuration section to the Admin page where operators enter a webhook URL and toggle delivery on/off. No EE licence required, no SMTP infrastructure. Single-destination only (CE boundary).

</domain>

<decisions>
## Implementation Decisions

### Failure trigger scope
- Alert fires on **FAILED** and **DEAD_LETTER** only — not COMPLETED, not SECURITY_REJECTED by default
- RETRYING jobs: no alert during intermediate retries — alert fires only when the job reaches a terminal failure state
- SECURITY_REJECTED alerting: **opt-in**, controlled by a checkbox in the Admin Notifications form ("Also alert on security rejections")
  - Config key: `alerts.webhook_security_rejections` = 'true'/'false'
  - Default: false (off)

### Admin Notifications form (Admin page)
- New "Notifications" card section in the Admin page
- Fields:
  - Webhook URL input (http:// or https:// validated on save)
  - Enabled/disabled toggle (`alerts.webhook_enabled`) — shown but greyed out until a URL is saved; tooltip: "Enter a webhook URL to enable"
  - Checkbox: "Also alert on security rejections" (`alerts.webhook_security_rejections`)
  - "Send test" button — active only after a URL is saved; fires synthetic payload
- Config keys: `alerts.webhook_url` + `alerts.webhook_enabled` + `alerts.webhook_security_rejections`
- Clearing the URL does **not** automatically disable — the enabled toggle is separate

### Test notification
- "Send test" button fires a synthetic `job.failed` payload with clearly fake data:
  - `job_name: "test-alert"`, `node_id: "system"`, `error_summary: "This is a test notification"`
- Backend endpoint: `POST /api/admin/alerts/test` — fires against the currently saved URL, returns `{success, status_code, body_snippet}`
- Feedback shown **inline below the button**: green "✓ Delivered (200)" or red "✗ Failed: connection refused"
- No modal, no page reload

### Delivery failure handling
- **Log + continue, no retry** — delivery failure is logged server-side; job status is unaffected
- Admin Notifications section shows **last delivery status** (persisted as Config key `alerts.last_delivery_status`, JSON):
  - Fields: `{status_code, timestamp, body_snippet}` — first 200 chars of response body included
  - Example display: "✓ 200 OK — 2026-03-29 22:15" or "✗ Connection refused — 2026-03-29 22:15"
  - Updated after every real delivery and after test sends

### URL save behaviour
- Backend validates format on save (must be http:// or https://) — no outbound ping on save
- Toggle (`alerts.webhook_enabled`) is independent of the URL — URL persists when toggled off
- Toggle greyed out until URL is saved; tooltip communicates the dependency

### Webhook payload (from Phase 87 — locked)
```json
{
  "event": "job.failed",
  "job_guid": "...",
  "job_name": "nightly-backup",
  "node_id": "node-alpha",
  "error_summary": "exit code 1: permission denied",
  "failed_at": "2026-03-29T22:15:00Z"
}
```
- DEAD_LETTER fires with `"event": "job.failed"` (same event type — it is a terminal failure)
- SECURITY_REJECTED fires with `"event": "job.security_rejected"` (distinct event, only when checkbox enabled)

### Claude's Discretion
- Exact layout/styling of the Notifications card within Admin.tsx (consistent with existing config cards)
- Whether `alerts.last_delivery_status` is a single JSON Config key or split into multiple keys
- HTTP timeout for outbound webhook calls (recommend 5s)
- Whether the test endpoint validates the URL format before firing

</decisions>

<specifics>
## Specific Ideas

- Toggle shown-but-disabled (greyed with tooltip) rather than hidden — communicates to operators that alerting can be enabled, before they've entered a URL
- Inline test feedback (not toast) — operator is actively configuring; they're looking at the form when they click "Send test"
- `alerts.webhook_security_rejections` checkbox is the toggle pattern — same Admin form, one card, all alerting config in one place

</specifics>

<code_context>
## Existing Code Insights

### Reusable Assets
- `agent_service/services/webhook_service.py`: CE stub with `dispatch_event(db, event_type, payload)`. Phase 89 replaces the no-op body with real HTTP POST logic. Reads `alerts.webhook_url` + `alerts.webhook_enabled` from Config, updates `alerts.last_delivery_status` after dispatch.
- `job_service.py:1218–1225`: Existing hook — `dispatch_event()` called for all terminal statuses. Phase 89 filters the call to FAILED + DEAD_LETTER (+ SECURITY_REJECTED if config flag set). The `job.status.lower()` string already produces `"job.failed"`, `"job.dead_letter"`, `"job.security_rejected"`.
- `Config` table (key/value): Already used for `alerts.webhook_url` (Phase 87 design), `stale_base_updated`, retention config, etc. Same pattern for all new alerting config keys.
- `Admin.tsx`: Existing config cards (Smelter enforcement, Mirror config) show the pattern — `useQuery` to load, `useMutation` to save. Notifications card follows the same structure.

### Established Patterns
- Config key pattern: `select(Config).where(Config.key == "key")` / `db.add(Config(key=..., value=...))` — used throughout `main.py`.
- Admin card pattern: `<Card>` with `<CardTitle>` + `<CardDescription>` + form fields + save button (`useMutation`).
- Inline status feedback: `authenticatedFetch` result drives a state variable rendered below the button — used in other Admin mutations.

### Integration Points
- `job_service.py:1218`: Filter condition before `dispatch_event()` call — check `job.status in ["FAILED", "DEAD_LETTER"]` (+ SECURITY_REJECTED if config flag).
- `main.py`: Add `GET /api/admin/alerts/config` + `PATCH /api/admin/alerts/config` + `POST /api/admin/alerts/test` endpoints (gated on `admin:write` or `system:write` permission).
- `webhook_service.py`: Real implementation reads from Config, fires HTTP POST, writes delivery status back. `httpx` or `aiohttp` for async HTTP call.

</code_context>

<deferred>
## Deferred Ideas

- Multiple webhook destinations + per-job routing rules — EE territory
- Richer payload (stdout, stderr, script content) — EE
- Delivery retry with backoff + dead-letter log — EE
- SMTP/email alerting — future phase if webhook-only proves insufficient

</deferred>

---

*Phase: 89-ce-alerting*
*Context gathered: 2026-03-29*
