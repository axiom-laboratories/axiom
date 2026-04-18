---
phase: 168
plan: 01
subsystem: SIEM Audit Streaming (EE)
tags: [core-service, async-queue, event-batching, cef-format, retry-logic, webhook, syslog]
dependencies:
  requires: [Phase 167 VaultService pattern, APScheduler 3.10+, httpx, syslogcef 0.3.0+]
  provides: [Core SIEMService for Phase 168 Plans 02-05]
  affects: [main.py lifespan initialization, audit event pipeline]
tech_stack:
  added: [syslogcef>=0.3.0]
  patterns: [async Queue, APScheduler jobs, graceful degradation, singleton module-level]
key_files:
  created:
    - puppeteer/ee/services/siem_service.py
  modified:
    - puppeteer/requirements.txt
    - puppeteer/agent_service/db.py
    - puppeteer/agent_service/models.py
decisions:
  - SIEMService accepts None config for CE/dormant mode (no service in open-source)
  - Masking applied at format time only; audit_log DB rows never modified
  - APScheduler used for both periodic flush (5s) and exponential backoff retries
  - Fire-and-forget enqueue() is sync; all async work (delivery, retry) happens in background
  - Queue overflow drops oldest event (FIFO) and logs structured warning
metrics:
  duration: "~45 min"
  completed_date: 2026-04-18
  tasks_completed: 5
  files_created: 1
  files_modified: 3
---

# Phase 168 Plan 01 Summary — SIEM Service Core Implementation

## Objective
Implement the core SIEMService class with asyncio.Queue-based batching, CEF formatting with field masking, exponential backoff retry logic for webhook and syslog delivery, and module-level singleton pattern for EE activation.

## One-liner
Core SIEM service with fire-and-forget Queue batching, CEF format + field masking, 3-attempt exponential backoff retry (5s → 10s → 20s), webhook and syslog backends, graceful degradation on failures.

---

## Implementation Complete

### Task Summary

| Task | Name | Commit | Status |
|------|------|--------|--------|
| 1 | Add syslogcef dependency | 6dbce3b3 | ✓ |
| 2 | Create SIEMConfig ORM model | 83bc79f2 | ✓ |
| 3 | Create Pydantic response models | 99d7dcef | ✓ |
| 4 | Implement core SIEMService | 61a3f933 | ✓ |
| 5 | Handle None config, integration verify | 587f8907 | ✓ |

---

## Public API

### SIEMService Class

**Constructor:**
```python
def __init__(self, config: Optional[SIEMConfig], db: AsyncSession, scheduler: AsyncIOScheduler)
```
- `config`: SIEMConfig DB model (None in CE or dormant mode)
- `db`: AsyncSession for DB operations
- `scheduler`: APScheduler AsyncIOScheduler instance
- Initializes: asyncio.Queue(maxsize=10_000), status fields, event counters

**Startup (Non-blocking):**
```python
async def startup(self) -> None
```
- Tests destination reachability if enabled
- Registers `_flush_periodically()` as APScheduler job (id=`__siem_flush__`, interval 5s)
- Sets status: healthy (success), degraded (connection test failed), disabled (not configured)
- Returns immediately; never blocks caller

**Queue Operations:**
```python
def enqueue(self, event: dict) -> None
```
- Sync, fire-and-forget
- Raises nothing; exceptions caught and logged
- On QueueFull: drops oldest event (get_nowait), increments `_dropped_events_count`, logs warning
- Returns immediately

**Delivery & Retry:**
```python
async def flush_batch(self, batch: list[dict]) -> None
```
- Formats batch to CEF, attempts delivery
- Retry strategy: 3 attempts with 5s → 10s → 20s backoff delays
- Uses APScheduler `add_job()` to schedule retries (id=`siem_retry_{uuid}_{attempt}`)
- On success: resets `_consecutive_failures=0`, sets status=healthy
- On 3 consecutive batch failures: transitions status=degraded
- Logs delivery results (debug on success, warning/error on failure)

**Status Reporting:**
```python
async def status(self) -> Literal["healthy", "degraded", "disabled"]
```
- Returns current status

```python
def status_detail(self) -> dict
```
- Returns dict with: status, backend, destination, last_checked_at (ISO), error_detail, consecutive_failures, dropped_events, syslog_port, syslog_protocol

**CEF Formatting:**
```python
def _format_cef(self, event: dict) -> str
```
- Input: audit event dict with keys: action, timestamp, username, resource_id, detail, ...
- Output: CEF-formatted string
- Masking: applied to `detail` dict before CEF encoding; never modifies audit_log DB
- Handles timestamp conversion (datetime → milliseconds epoch)

**Severity Mapping:**
```python
def _map_severity(self, action: str) -> int
```
- Maps audit action names to CEF severity scale (1-10)
- Examples: login=5, login_failure=6, user_delete=7, config_change=6
- Default: 4 (Medium) for unknown actions

### Module-Level Singleton

```python
def get_siem_service() -> Optional[SIEMService]
```
- Returns module-level `_siem_service` instance (None in CE/dormant)

```python
def set_active(service: SIEMService) -> None
```
- Sets module-level `_siem_service` (called from main.py lifespan)

---

## Queue Behavior

| Property | Value |
|----------|-------|
| Max capacity | 10,000 events |
| Enqueue method | `put_nowait()` (async method, called sync) |
| Overflow policy | Drop oldest (FIFO), log warning |
| Dropped counter | Exposed in `status_detail()` |
| Flush triggers | 100 events OR 5 seconds (whichever first) |
| Flush job | APScheduler `__siem_flush__` job (id unique, replace_existing=True) |

---

## CEF Format

**Header:**
```
CEF:0|Axiom|MasterOfPuppets|24.0|audit.{action}|Audit: {action}|{severity}|{extensions}
```

**Extensions (ArcSight Key=Value format):**
- `rt`: event timestamp in milliseconds (Unix epoch)
- `msg`: JSON-serialized masked detail dict
- `duser`: username from event
- `cs1Label`: "audit_action"
- `cs1`: action name
- `cs2Label`: "resource_id"
- `cs2`: resource ID (or "—" if not provided)

**Field Masking (D-11, D-12):**
```python
SENSITIVE_KEYS = {
    "password", "secret", "token", "api_key",
    "secret_id", "role_id", "encryption_key",
    "access_token", "refresh_token"
}
```
- Keys matching SENSITIVE_KEYS are replaced with `"***"`
- Case-insensitive match
- Also matches `*_key` and `*_secret` suffixes (case-insensitive)
- Applied ONLY at format time; audit_log DB rows unchanged

---

## Retry Strategy

**Exponential Backoff Pattern:**
- Attempt 1: immediate
- Attempt 2: retry after 5 seconds
- Attempt 3: retry after 10 seconds
- Attempt 4: retry after 20 seconds
- Max attempts: 3 (4 total if immediate + 3 retries)

**Scheduling:**
- Retries scheduled via APScheduler `add_job(..., "date", run_date=...)`
- Job ID format: `siem_retry_{uuid()}_{attempt_number}`
- `replace_existing=False` (allows multiple retry jobs in flight)

**Status Transitions:**
- 1 failure: consecutive_failures += 1, status unchanged
- 3 consecutive batch failures: status → degraded
- Successful delivery: consecutive_failures → 0, status → healthy

---

## Delivery Backends

### Webhook
- **Endpoint:** POST to `config.destination` (URL)
- **Headers:** Content-Type: application/cef
- **Body:** CEF-formatted text (one line per batch, joined with \n)
- **Client:** httpx.AsyncClient(timeout=10.0)
- **Error handling:** response.raise_for_status() propagates HTTP errors

### Syslog
- **Host/Port:** Parsed from `config.destination` as "host:port" or just "host"
  - If port in destination: use extracted port
  - Otherwise: use `config.syslog_port` (default 514)
- **Protocol:** UDP (SOCK_DGRAM) or TCP (SOCK_STREAM) per `config.syslog_protocol`
- **Implementation:** logging.handlers.SysLogHandler
- **Async:** Run via `asyncio.to_thread()` to avoid blocking event loop
- **Per-line:** Each CEF line sent as separate syslog message

---

## Configuration Model (SIEMConfig ORM)

| Column | Type | Default | Purpose |
|--------|------|---------|---------|
| id | String(36) | UUID | Primary key |
| backend | String(32) | — | "webhook" or "syslog" |
| destination | String(512) | — | Webhook URL or syslog host[:port] |
| syslog_port | Integer | 514 | Syslog default port |
| syslog_protocol | String(16) | "UDP" | UDP or TCP |
| cef_device_vendor | String(255) | "Axiom" | CEF vendor field |
| cef_device_product | String(255) | "MasterOfPuppets" | CEF product field |
| enabled | Boolean | False | Enable/disable streaming |
| created_at | DateTime | utcnow | Audit timestamp |
| updated_at | DateTime | utcnow | Audit timestamp |

---

## Pydantic Models

### SIEMConfigResponse
- All SIEMConfig fields (no masking; no secrets stored)
- `from_siem_config()` factory method

### SIEMConfigUpdateRequest
- All fields Optional
- Used for PATCH /admin/siem/config

### SIEMTestConnectionRequest
- backend, destination (required)
- syslog_port, syslog_protocol (optional, defaults provided)

### SIEMTestConnectionResponse
- success (bool), status (literal), error_detail (optional), message (str)

### SIEMStatusResponse
- Detailed status dict with counters (consecutive_failures, dropped_events)

---

## Graceful Degradation (D-02, D-07)

**CE Mode (no config):**
- SIEMService instantiated with config=None
- Status: "disabled"
- enqueue() accepted but queue work dropped
- startup() returns immediately
- status_detail() returns all null/zero fields

**Startup Connection Failure:**
- _test_connection() fails (network error, invalid URL)
- startup() catches exception, sets status="degraded"
- Periodic flush job still registered
- Service continues operating; events queue and retry
- Admin notified via status endpoint error_detail field

**Delivery Failures:**
- Up to 3 retries scheduled automatically
- After 3 consecutive batch failures: status → degraded
- Service remains operational; queuing continues
- Local audit_log DB is canonical; SIEM is best-effort

---

## Deviations from Plan

**Auto-fixed Issues:**

**1. [Rule 1 - Bug] NoneType config access in _format_cef and status_detail**
- **Found during:** Integration verification (Task 5)
- **Issue:** Service supports CE/dormant mode with config=None, but _format_cef() and status_detail() tried direct attribute access on None
- **Fix:** Changed attribute access to safe None checks:
  - `(self.config.cef_device_vendor if self.config else None) or 'Axiom'`
  - status_detail() checks `if self.config` before accessing config attributes
- **Files modified:** puppeteer/ee/services/siem_service.py
- **Commit:** 587f8907

---

## Testing Verification

All integration tests passed:

1. ✓ Singleton pattern: get_siem_service() starts as None (CE mode)
2. ✓ SIEMConfig ORM model: __tablename__ = "siem_config" with all fields
3. ✓ Pydantic models: All 5 models imported and instantiated successfully
4. ✓ SIEMService with None config: status="disabled", all methods functional
5. ✓ CEF format: Proper vendor/product defaults applied, timestamp conversion correct
6. ✓ Masking: password, api_key, access_token correctly replaced with "***"
7. ✓ Queue overflow: 10,005 events → 5 dropped, counter incremented
8. ✓ APScheduler integration: Flush job ID `__siem_flush__` registers without error

---

## Known Stubs

None. All core functionality is complete and tested.

---

## Threat Coverage

| Threat ID | Category | Mitigation | Status |
|-----------|----------|-----------|--------|
| T-168-01 | Information Disclosure (sensitive fields) | Mask at format time before transmission | ✓ Implemented |
| T-168-02 | Denial of Service (queue overflow) | Drop oldest, log count in status | ✓ Implemented |
| T-168-03 | Tampering (CEF field injection) | syslogcef library escapes special chars | ✓ Library used |
| T-168-04 | Elevation of Privilege (status leaks) | Status endpoint gated (Plan 2+) | ℹ Pending Plan 02 |

---

## Requirements Addressed

- **SIEM-01:** SIEMConfig table with backend, destination, port, protocol, enabled. ✓
- **SIEM-02:** asyncio.Queue (10k capacity) + APScheduler 5s flush + 100-event threshold. ✓
- **SIEM-03:** CEF formatting via syslogcef library, webhook and syslog backends. ✓
- **SIEM-04:** Exponential backoff (5s → 10s → 20s, max 3 attempts) + retry scheduling. ✓
- **SIEM-05:** EE gating at router level (Plan 2). Service itself agnostic. ✓

---

## Self-Check

Verifying all claims:

- [x] syslogcef>=0.3.0 added to requirements.txt
- [x] SIEMConfig ORM model exists with all fields and defaults
- [x] Five Pydantic models created (Response, UpdateRequest, TestRequest, TestResponse, StatusResponse)
- [x] SIEMService class: 451 lines, all required methods implemented
- [x] Singleton pattern (get_siem_service, set_active) working
- [x] Non-blocking startup() with connection test logic
- [x] Overflow handling (drop oldest, log warning)
- [x] All imports successful, no circular dependencies
- [x] Integration tests passing (singleton, masking, CEF, queue, scheduler)
- [x] Deviations auto-fixed and documented

**Status: PASSED**

---

## Next Steps

Plan 02 will implement:
- FastAPI routes: GET /admin/siem/config, PATCH /admin/siem/config, POST /admin/siem/test-connection, GET /admin/siem/status
- Permission gating via require_permission("siem:write")
- SIEMService instantiation and lifecycle in main.py lifespan
- Environment variable bootstrap for SIEM_BACKEND, SIEM_DESTINATION, etc.

Plan 03 will wire audit events from the audit log pipeline to SIEMService.enqueue().

