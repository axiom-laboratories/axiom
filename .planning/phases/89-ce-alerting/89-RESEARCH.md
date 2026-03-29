# Phase 89: CE Alerting — Research

**Phase:** 89
**Researched:** 2026-03-29
**Status:** RESEARCH COMPLETE

---

## What We Know Before Planning

### Existing Stub — Ready to Fill

`puppeteer/agent_service/services/webhook_service.py` is a 15-line CE stub. The entire class body is:

```python
@staticmethod
async def dispatch_event(db: AsyncSession, event_type: str, payload: Any):
    """No-op in CE. EE plugin provides real webhook dispatch."""
    pass
```

Phase 89 replaces this `pass` body with real logic. The file stays in place — no new service file needed.

### Call Site in job_service.py

Lines 1217–1225 of `job_service.py`:

```python
# 4. Final Terminal Status Webhook
is_terminal = job.status in ["COMPLETED", "FAILED", "DEAD_LETTER", "SECURITY_REJECTED"]
if is_terminal:
    await WebhookService.dispatch_event(db, f"job:{job.status.lower()}", {
        "guid": job.guid,
        "node_id": job.node_id,
        "status": job.status,
        "exit_code": report.exit_code
    })
```

The CONTEXT.md specifies:
- Alert fires on FAILED and DEAD_LETTER only
- SECURITY_REJECTED: opt-in via `alerts.webhook_security_rejections` config key
- Payload shape in CONTEXT.md (locked from Phase 87) differs slightly from the current call site — plan must reconcile

**Current payload vs. locked payload:**
- Current: `guid`, `node_id`, `status`, `exit_code`
- Locked: `event`, `job_guid`, `job_name`, `node_id`, `error_summary`, `failed_at`

The `job_service.py` call passes `event_type` as first arg — but the locked payload has `event` inside the payload dict. The implementation needs to enrich the payload using the `Job` object fields (`job.name`, `job.result` for error_summary).

### Config Table Pattern

`db.py` shows `Config` is a simple key/value table (PK = key, value = Text). Pattern in `main.py`:
```python
result = await db.execute(select(Config).where(Config.key == "some_key"))
row = result.scalar_one_or_none()
if row:
    row.value = new_value
else:
    db.add(Config(key="some_key", value=new_value))
await db.commit()
```

This is the exact pattern for the four new config keys:
- `alerts.webhook_url`
- `alerts.webhook_enabled`
- `alerts.webhook_security_rejections`
- `alerts.last_delivery_status` (JSON string)

### httpx Is Already in requirements.txt

`puppeteer/requirements.txt` already includes `httpx`. No dependency changes needed. Use `httpx.AsyncClient` for async outbound POST.

### Backend API Pattern (for Admin endpoints)

The retention config endpoints (`GET /api/admin/retention`, `PATCH /api/admin/retention`) show the established pattern for Admin config APIs. They use `require_permission("users:write")`. The alerting endpoints should use `require_permission("nodes:write")` or a similar permission available to operators. Looking at the permissions seeded, `nodes:write` is the best fit for system config that operators need.

### Admin.tsx Frontend Pattern

Admin.tsx (1592 lines) uses a tab layout. The Data tab contains the retention config as a `bg-zinc-800/50 rounded-lg p-6 border border-zinc-700` card — a simpler pattern than the Card component-based Onboarding tab. The Notifications card should follow the newer Card component pattern (like Onboarding uses `bg-zinc-925 border-zinc-800/50`) since it's a first-class feature.

Existing tab list in Admin.tsx:
`Onboarding | Smelter Registry | BOM Explorer | Tools | Artifact Vault | Rollouts | Automation | Data`

A "Notifications" tab should be added OR the Notifications card goes inside an existing tab. Given the context decision "New Notifications card section in the Admin page" (not specifying a tab), and that this is a distinct operational area, adding a `Notifications` TabTrigger + TabContent is the cleanest approach.

### Test Infrastructure Observation

`test_alert_system.py` already exists and tests the `Alert` DB model and `AlertService`. There is a `@pytest.mark.skip(reason="Webhook dispatch is EE-only")` test for `test_webhook_dispatch_on_alert`. Phase 89 needs a NEW test file `test_webhook_notification.py` testing the CE webhook delivery logic specifically (config read → HTTP POST → status write-back).

### Validation Architecture

The CONTEXT.md `code_context` section describes:

1. **webhook_service.py** — reads config keys, POSTs to URL, writes `alerts.last_delivery_status`
2. **job_service.py:1218** — filter condition (FAILED + DEAD_LETTER + optional SECURITY_REJECTED)
3. **main.py** — 3 new endpoints: `GET /api/admin/alerts/config`, `PATCH /api/admin/alerts/config`, `POST /api/admin/alerts/test`
4. **Admin.tsx** — Notifications card with URL field, toggle, checkbox, "Send test" button, inline result

---

## Validation Architecture

### Test Surfaces

| Area | Method | Description |
|------|--------|-------------|
| Config read/write | pytest unit | Mock DB, verify config keys read/written correctly |
| Webhook dispatch | pytest unit + `respx` mock | Mock httpx, verify POST body matches locked payload shape |
| Filter logic | pytest unit | Only FAILED/DEAD_LETTER trigger when security_rejections=false |
| Test endpoint | pytest unit | Fires synthetic payload, returns status_code |
| Frontend form | Playwright smoke | URL field saves, toggle enables, "Send test" shows inline result |

### Key Risk: Payload Enrichment

The current `dispatch_event` call site only passes `guid`, `node_id`, `status`, `exit_code`. The locked Phase 87 payload requires `job_name`, `error_summary`, `failed_at`. The `webhook_service.dispatch_event` must either:
- **Option A**: Accept an enriched payload directly (caller enriches) — minimal changes to job_service call site
- **Option B**: Accept a `Job` object and enrich internally — job_service just passes `job`

**Recommendation**: Option A. The call site in `job_service.py` already has access to `job.name`, `job.result` (JSON with error), and `datetime.utcnow()`. Enriching at the call site keeps webhook_service.py simple and testable.

### Key Risk: Permission for alerts config

The alerting config should be accessible to `operator` role (ALRT-03). Currently the only system-config-adjacent permission used is `nodes:write`. If the operator role has `nodes:write`, this naturally includes alerting config. Need to confirm this in the seed or ensure `alerts:write` is added as a new permission. Given the CONTEXT decision "accessible to a user with the operator role", using an existing operator permission is simplest — use `nodes:write` for both GET and PATCH of alerting config.

---

## Summary

**What to build:**
1. `webhook_service.py` — replace no-op with real httpx POST + config read/write
2. `job_service.py` — update dispatch_event call site to filter statuses and enrich payload
3. `main.py` — 3 new endpoints (GET/PATCH `/api/admin/alerts/config`, POST `/api/admin/alerts/test`)
4. `Admin.tsx` — new Notifications tab with form (URL, toggle, checkbox, "Send test" with inline result)
5. `test_webhook_notification.py` — pytest unit tests for the new service

**No migration SQL needed** — Config table already exists, uses `create_all`-compatible key/value pattern.

**No new dependencies** — httpx already in requirements.txt.

**Wave structure**: Wave 1 (backend service + API), Wave 2 (frontend UI) — can execute sequentially, frontend depends on API being defined.
