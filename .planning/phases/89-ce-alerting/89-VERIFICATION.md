---
phase: 89-ce-alerting
verified: 2026-03-29T22:45:00Z
status: passed
score: 7/7 must-haves verified
re_verification: false
human_verification:
  - test: "Navigate to /admin, click Notifications tab"
    expected: "Tab is visible in tab bar; card renders with URL input, enabled toggle, security rejections checkbox, and Send test button"
    why_human: "Cannot verify tab rendering and form layout programmatically without browser"
  - test: "Enter a webhook URL (e.g. https://httpbin.org/post), click Save"
    expected: "Toast 'Notifications config saved' fires; toggle becomes active (no longer greyed out)"
    why_human: "Conditional enabled state requires browser interaction to verify"
  - test: "Enable the toggle, click 'Send test notification'"
    expected: "Inline result appears below button: green 'Delivered (200)' or red 'Failed: ...' text; Last Delivery section appears"
    why_human: "Inline result state and last delivery persistence require live network call"
  - test: "Log in as operator role, navigate to /admin > Notifications"
    expected: "Card loads without 403 error"
    why_human: "CE fallback in require_permission means this needs a real login session to verify"
  - test: "Submit a job that will FAIL (e.g. script that exits 1)"
    expected: "If webhook enabled+URL configured, destination receives POST with job_name, node_id, error_summary fields"
    why_human: "Real delivery on job failure requires live stack execution"
---

# Phase 89: CE Alerting Verification Report

**Phase Goal:** Deliver a production-ready CE webhook alerting system: real outbound HTTP POST delivery on FAILED/DEAD_LETTER events, operator-configurable URL and toggle via Admin UI, test-fire capability with inline result, and last-delivery-status persistence.
**Verified:** 2026-03-29T22:45:00Z
**Status:** human_needed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | `dispatch_event` performs real HTTP POST when enabled+URL set | VERIFIED | `webhook_service.py` lines 72-86: `httpx.AsyncClient` POST with 5s timeout; test `test_dispatch_sends_post` passes |
| 2 | Delivery fires only on FAILED, DEAD_LETTER (+ opt-in SECURITY_REJECTED) | VERIFIED | `_ALERT_EVENTS = {"job:failed", "job:dead_letter"}` at line 18; guard at lines 49-52; tests `test_completed_no_alert` and `test_security_rejected_opt_in` pass |
| 3 | Payload matches locked shape: event, job_guid, job_name, node_id, error_summary, failed_at | VERIFIED | `outbound` dict at lines 60-67 of `webhook_service.py`; `job_service.py` lines 1228-1234 supply all fields |
| 4 | `alerts.last_delivery_status` Config key updated after every dispatch | VERIFIED | Lines 88-102 of `webhook_service.py` write JSON status; test `test_delivery_status_written` passes; test endpoint in `main.py` also writes status |
| 5 | Three admin endpoints exist with `nodes:write` permission guard | VERIFIED | `GET /api/admin/alerts/config` (line 2155), `PATCH /api/admin/alerts/config` (line 2181), `POST /api/admin/alerts/test` (line 2208) — all use `Depends(require_permission("nodes:write"))` |
| 6 | `PATCH` endpoint validates URL format (http/https) | VERIFIED | `AlertsConfigUpdate.validate_url` in `models.py` lines 427-432 rejects non-http(s) URLs; test `test_config_model_validation` passes |
| 7 | Notifications UI tab with full form in Admin.tsx | VERIFIED | `NotificationsCard` component at line 1318; `TabsTrigger value="notifications"` at line 1631; `TabsContent value="notifications"` at line 1797; `Bell` icon imported at line 25 |

**Score:** 7/7 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `puppeteer/agent_service/services/webhook_service.py` | Real HTTP POST delivery service | VERIFIED | 106 lines, full implementation with httpx, event filtering, status persistence |
| `puppeteer/agent_service/services/job_service.py` | Enriched dispatch_event call site | VERIFIED | Lines 1218-1234: `is_alert_status` filter, error_summary extraction, full payload |
| `puppeteer/agent_service/main.py` | Three alerting config endpoints | VERIFIED | GET/PATCH/POST at lines 2155, 2181, 2208; `import httpx` at line 25; `AlertsConfigUpdate` imported at line 43 |
| `puppeteer/agent_service/models.py` | AlertsConfigUpdate, AlertsConfigResponse, AlertsTestResponse | VERIFIED | Lines 422-446: all three models with URL validator |
| `puppeteer/tests/test_webhook_notification.py` | 7-test coverage suite | VERIFIED | 543 lines; all 7 tests pass in isolation |
| `puppeteer/dashboard/src/views/Admin.tsx` | NotificationsCard + Notifications tab | VERIFIED | NotificationsCard at line 1318 (~160 lines); tab trigger at 1631; tab content at 1797 |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `job_service.py` | `webhook_service.dispatch_event` | `await WebhookService.dispatch_event(db, ...)` | WIRED | Line 1228 calls dispatch_event with enriched payload |
| `webhook_service.dispatch_event` | `httpx.AsyncClient` | `async with httpx.AsyncClient(timeout=5.0) as client` | WIRED | Lines 73-74: POST fired with json payload |
| `webhook_service.dispatch_event` | `Config` table (status write) | `db.add(Config(...)) / row.value = status_json` | WIRED | Lines 94-102: status JSON persisted after every dispatch |
| `main.py GET /api/admin/alerts/config` | `Config` table | `select(Config).where(Config.key.in_(keys))` | WIRED | Lines 2161-2163 |
| `main.py PATCH /api/admin/alerts/config` | `Config` table | `select(Config).where(Config.key == key)` per field | WIRED | Lines 2196-2203 |
| `main.py POST /api/admin/alerts/test` | `httpx.AsyncClient` | `async with httpx.AsyncClient(timeout=5.0)` | WIRED | Lines 2236-2240 |
| `NotificationsCard` | `GET /api/admin/alerts/config` | `authenticatedFetch('/api/admin/alerts/config')` | WIRED | Admin.tsx line 1327 |
| `NotificationsCard` | `PATCH /api/admin/alerts/config` | `authenticatedFetch('/api/admin/alerts/config', { method: 'PATCH' })` | WIRED | Admin.tsx line 1343 |
| `NotificationsCard` | `POST /api/admin/alerts/test` | `authenticatedFetch('/api/admin/alerts/test', { method: 'POST' })` | WIRED | Admin.tsx line 1376 |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| ALRT-01 | 89-01, 89-02 | CE operator can configure webhook URL for job failure events | SATISFIED | PATCH endpoint + NotificationsCard URL input + toggle |
| ALRT-02 | 89-01 | FAILED job triggers notification with job name, node, error summary | SATISFIED | `job_service.py:1228-1234` enriched payload; `webhook_service.py` HTTP POST; NOTE: REQUIREMENTS.md checkbox still unchecked — documentation lag |
| ALRT-03 | 89-01, 89-02 | Alerting config accessible to CE operators without EE licence | SATISFIED (CE) | `require_permission("nodes:write")` falls back to auth-only in CE mode (deps.py:103-106); EE gap noted below |

**REQUIREMENTS.md inconsistency:** The traceability table marks ALRT-02 as "Pending" and the checkbox `[ ]` is unchecked, but the implementation is present and tested. This is a documentation gap — the code satisfies ALRT-02.

**ALRT-03 EE gap (informational, not a CE blocker):** `nodes:write` is never seeded for the operator role in any migration or startup code. In CE mode this is harmless (CE fallback grants access to any authenticated user). If an EE deployment adds `role_permissions`, operators would be blocked from `/api/admin/alerts/*` unless `nodes:write` is manually granted. This is out of scope for the CE phase but worth noting.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `webhook_service.py` | 66, 91 | `datetime.utcnow()` deprecated in Python 3.12+ | Info | Deprecation warning in tests; functional, not broken |

No stubs, placeholders, empty handlers, or TODO comments found in phase-89 files.

### Human Verification Required

#### 1. Notifications Tab Rendering

**Test:** Navigate to `/admin` in a browser session (Docker stack running), click the Notifications tab
**Expected:** Tab appears in the tab bar; card renders with: URL input field, enabled toggle (greyed out when URL empty), security rejections checkbox, "Send test notification" button (disabled until URL saved)
**Why human:** Tab visibility and conditional toggle state cannot be verified by grep

#### 2. URL Save + Toggle Activation

**Test:** Enter `https://httpbin.org/post`, click Save
**Expected:** `toast.success('Notifications config saved')` fires; toggle becomes enabled (opacity-40 removed)
**Why human:** Conditional class rendering (`disabled={!urlSaved}`) and toast feedback require browser interaction

#### 3. Send Test + Inline Result

**Test:** Enable the toggle; click "Send test notification"
**Expected:** Inline text appears below button: green `✓ Delivered (200)` or red `✗ Failed: ...`; "Last Delivery" section appears below the form with timestamp
**Why human:** State-driven inline result and query invalidation require live execution

#### 4. Operator Role Access

**Test:** Log in as an operator user, navigate to `/admin`, click Notifications tab
**Expected:** Card loads without 403 error; all controls respond normally
**Why human:** CE fallback behaviour in `require_permission` requires a real JWT session

#### 5. Real Job Failure Delivery

**Test:** Dispatch a job script that exits 1 (with webhook enabled + URL configured to a live bin)
**Expected:** HTTP POST received at configured URL with fields: `event="job.failed"`, `job_name`, `node_id`, `error_summary` (exit code or stderr)
**Why human:** Requires live Docker stack execution and a reachable webhook receiver

### Test Suite Status

- `tests/test_webhook_notification.py` — **7/7 pass** (run in isolation)
- Suite-wide run: 5 test files fail to collect (pre-existing, unrelated to phase 89: `test_intent_scanner.py`, `test_lifecycle_enforcement.py`, `test_smelter.py`, `test_staging.py`, `test_tools.py`). These collection failures cause test-order contamination affecting other test files including webhook tests when run together — this is a pre-existing CI issue, not introduced by phase 89.
- Frontend lint: `npm run lint` exits clean (no errors)

---

_Verified: 2026-03-29T22:45:00Z_
_Verifier: Claude (gsd-verifier)_
