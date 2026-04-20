# Phase 168: SIEM Audit Streaming (EE) - Research

**Researched:** 2026-04-18  
**Domain:** Real-time audit log streaming with CEF formatting, batching, masking, and retry logic  
**Confidence:** HIGH

## User Constraints (from CONTEXT.md)

### Locked Implementation Decisions

**D-01:** SIEM service lives in `puppeteer/ee/services/siem_service.py`. CE users get 402 on all `/admin/siem/*` endpoints via a stub router in `agent_service/ee/interfaces/siem.py`. CE audit log write path (`deps.py:audit()`) is completely unaffected.

**D-02:** `app.state.siem_service` is initialized in main.py lifespan, following the VaultService pattern. If no `SIEMConfig` row exists or `enabled=false`, service is dormant — silent, no errors.

**D-03:** Hook directly into `deps.py:audit()`. After scheduling the DB insert task, `audit()` also calls `get_siem_service().enqueue(event)` — a non-blocking call that pushes to the in-memory queue. No change to the external signature of `audit()`.

**D-04:** `siem_service.py` exposes a module-level singleton via `get_siem_service() -> Optional[SIEMService]`. Set by main.py on startup: `siem_service.set_active(instance)`. Returns `None` in CE/dormant mode — `audit()` checks for None before calling enqueue.

**D-05:** Two backends: **webhook** (HTTP POST with CEF body) and **syslog** (UDP/TCP, RFC 5424, CEF payload). The `SIEMConfig` row has a `backend` field: `"webhook"` or `"syslog"`. Exactly one backend is active per config.

**D-06:** Syslog protocol is configurable: `UDP` (default, fire-and-forget) or `TCP` (connection-oriented). Uses Python's `logging.handlers.SysLogHandler` — no additional dependencies. Protocol selector in the admin UI.

**D-07:** CEF format is used for both backends. Webhook: CEF in the HTTP body (`Content-Type: application/cef`). Syslog: CEF as the syslog message body (standard enterprise SIEM convention).

**D-08:** In-memory `asyncio.Queue` with a hard cap of 10,000 events. Fast, zero DB overhead. Events in the buffer are lost on crash — accepted trade-off since the local `audit_log` table is always the canonical record.

**D-09:** Flush triggers: (1) queue reaches 100 events, OR (2) APScheduler fires every 5 seconds — whichever comes first. Exactly as specified in SIEM-02.

**D-10:** Queue full policy: drop oldest events. Log a structured warning when dropping. SIEM streaming is best-effort; the local audit_log is unaffected.

**D-11:** Before transmission, the SIEM formatter scrubs the `detail` JSON for keys matching a keyword list: `password`, `secret`, `token`, `api_key`, `secret_id`, `role_id`, `encryption_key`, and any key ending in `_key` or `_secret`. Matched values are replaced with `"***"`. Keyword matching is case-insensitive.

**D-12:** Masking is applied at format time (just before transmission) — the `audit_log` DB rows are never modified. The raw event data in the DB remains unredacted for local query/export.

**D-13:** Failed batch deliveries are retried with exponential backoff: 5s → 10s → 20s (max 3 attempts total). If all 3 attempts fail, the batch is dropped and the failure is counted. APScheduler manages the retry schedule.

**D-14:** After 3 consecutive batch failures (across different flush intervals), `SIEMService` transitions to `DEGRADED` status and logs a structured warning. Service continues accepting new events and attempting future flushes — it does not stop. Non-SIEM operations are unaffected.

**D-15:** Status is in-memory on `SIEMService`: `status: Literal["disabled", "healthy", "degraded"]`, `last_failure: Optional[str]`, `consecutive_failures: int`, `last_checked_at: Optional[datetime]`. Resets to `healthy` on first successful flush after a degraded period.

**D-16:** Two endpoints: `GET /admin/siem/status` (full detail: address/host, backend type, last_checked_at, error_detail if degraded). `GET /system/health` gains a `siem` field alongside the existing `vault` field.

**D-17:** Admin UI: SIEM configuration form in `Admin.tsx` (new "SIEM" tab, following the "Vault" tab pattern from Phase 167). Fields: backend selector (webhook/syslog), address (URL or host:port), protocol (UDP/TCP, shown only when syslog), CEF device vendor/product (optional branding), enabled toggle, test-connection button. Status indicator (`healthy / degraded / disabled`) in the section header.

**D-18:** `SIEMConfig` table in DB: `backend` (webhook/syslog), `destination` (URL or host), `syslog_port` (int), `syslog_protocol` (UDP/TCP), `cef_device_vendor` (str, default "Axiom"), `cef_device_product` (str, default "MasterOfPuppets"), `enabled` (bool). Env-var bootstrap: `SIEM_BACKEND`, `SIEM_DESTINATION`, `SIEM_ENABLED`. Config editable at runtime via admin UI without restart.

### Claude's Discretion

Research output should provide recommendations on:
- Exact CEF header field mapping (device severity, signatureId naming for each action type)
- APScheduler job naming for flush/retry tasks
- Error message exact wording (intent captured in D-14, D-10)
- SIEMConfig table column defaults and nullable constraints
- Whether `cef_device_vendor`/`cef_device_product` are exposed in admin UI or just env-var configurable

### Deferred Ideas (OUT OF SCOPE)

- Syslog TLS (RFC 5425) — current phase uses plain UDP/TCP
- Splunk HEC native format — CEF covers Splunk via HTTP Event Collector adapter
- Azure Monitor / AWS CloudWatch / GCP Cloud Logging backends — future EE extensibility phase
- Configurable failure threshold (user-settable, not hardcoded to 3)
- Persisted `SIEMAlert` DB records — in-memory status is sufficient for Phase 168

---

## Summary

Phase 168 implements a production-grade SIEM integration for the EE licence tier. The phase captures audit events from the existing `audit()` function in `deps.py`, batches them in an in-memory asyncio.Queue, formats as CEF (Common Event Format), masks sensitive fields, and delivers to webhook or syslog backends with exponential backoff retry logic.

The service is stateless and non-blocking: startup never fails, the local audit_log table is always the canonical record, and failed transmissions do not affect core platform operations. SIEM streaming is explicitly best-effort. The implementation replicates the VaultService pattern from Phase 167 for EE gating, module-level singleton access, and status surface.

**Primary recommendation:** Build SIEMService in `puppeteer/ee/services/siem_service.py` following the VaultService pattern. Add asyncio.Queue-based batching with 5s flush interval and 100-event threshold. Use `syslogcef >= 0.3.0` for CEF formatting and Python's stdlib `logging.handlers.SysLogHandler` for syslog transport. Mask sensitive fields at format time (never modify audit_log DB). Integrate via hook into `deps.py:audit()` and expose status at `GET /system/health` and `GET /admin/siem/status`.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| SIEM service layer (enqueue, batch, format, deliver) | API / Backend | — | Core business logic; stateless microservice pattern |
| Audit event capture hook | API / Backend | Database | `audit()` function routes events to queue; audit_log table is unaffected |
| CEF formatting | API / Backend | — | Specification compliance; format-time masking preserves raw DB records |
| Webhook delivery | API / Backend | — | Async HTTP POST via httpx (already in stack) |
| Syslog delivery | API / Backend | — | Network protocol handling via stdlib SysLogHandler |
| Admin configuration UI | Frontend / Browser | API / Backend | Form input; backend persists and validates SIEMConfig |
| Status surface | API / Backend | Frontend / Browser | In-memory status on SIEMService; exposed via REST + health endpoint |
| Queue backpressure handling | API / Backend | — | Drop oldest on queue full; log warning (best-effort semantics) |

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| syslogcef | >= 0.3.0 | CEF message formatting | Battle-tested, 95% SIEM support; handles field escaping and extension dict. See [PyPI: syslogcef](https://pypi.org/project/syslogcef/) |
| httpx | (already in requirements.txt) | Async HTTP client for webhook delivery | Async/await native; supports retry patterns; already vendored |
| logging.handlers.SysLogHandler | stdlib | Syslog transport (UDP/TCP) | No external dependency; RFC 3164/5424 compatible via protocol parameter |
| asyncio.Queue | stdlib | In-memory event buffering | Zero external dependency; bounded capacity; fire-and-forget semantics |
| apscheduler | >= 3.10 (already in stack) | Periodic flush scheduling (5s interval) | Reuse existing scheduler; supports async jobs natively |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| cryptography | >= 46.0.7 (already in stack) | Encryption for SIEMConfig sensitive fields (optional, if secrets stored) | If webhook auth tokens stored in DB; Phase 168 uses `enabled` flag + plaintext URLs, so not critical |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| syslogcef | DIY CEF formatting with string templates | syslogcef handles field escaping (\|, \=), extension dict, and severity mapping correctly. DIY introduces escape bugs; not worth it. |
| stdlib SysLogHandler | dedicated syslog client (e.g., syslog-ng Python) | Stdlib is sufficient for RFC 3164 + CEF; dedicated clients add complexity without benefit for this phase. |
| asyncio.Queue | asyncio.PriorityQueue | Normal queue is fine; priority unnecessary (FIFO age-based drop is intentional). |
| APScheduler flush | manual event loop callback | APScheduler is already integrated for lease renewal; reusing avoids duplication. |

**Installation:**
```bash
pip install syslogcef>=0.3.0
# httpx, apscheduler, cryptography already in requirements.txt
```

**Version verification:** syslogcef latest is 0.4.0 (as of PyPI 2026-04), but >= 0.3.0 is stable. [VERIFIED: pip index]

## Architecture Patterns

### System Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                   FastAPI Control Plane                     │
│                   (puppeteer/agent_service)                 │
│                                                              │
│  ┌──────────────────┐    ┌──────────────────┐              │
│  │   All Routes     │    │  deps.py:audit() │              │
│  │                  │───▶│  (sync function) │              │
│  │  (jobs, nodes,   │    │                  │              │
│  │   workflows...)  │    └────────┬─────────┘              │
│  └──────────────────┘             │ enqueue() call         │
│                                    │ (non-blocking)         │
│                                    ▼                        │
│  ┌─────────────────────────────────────────────────────────┤
│  │         SIEMService (in-memory, stateless)              │
│  │  ┌────────────────┐     ┌──────────────────────────┐   │
│  │  │  asyncio.Queue │◀────│ Enqueue (fire-and-forget)│   │
│  │  │  (max 10K)     │     │ from deps.py            │   │
│  │  └────────┬───────┘     └──────────────────────────┘   │
│  │           │                                              │
│  │     ┌─────▼──────┐                                      │
│  │     │  APScheduler: flush_worker()                      │
│  │     │  (every 5s OR at 100 events)                      │
│  │     └─────┬──────┘                                      │
│  │           │                                              │
│  │     ┌─────▼──────────────────────────────────────┐     │
│  │     │ CEF Formatter (syslogcef)                  │     │
│  │     │ - Read event from queue                    │     │
│  │     │ - Mask sensitive fields (passwords, etc.)  │     │
│  │     │ - Format to CEF with device/severity      │     │
│  │     └─────┬──────────────────────────────────────┘     │
│  │           │                                              │
│  │     ┌─────▼──────────────────────────────────────┐     │
│  │     │ Delivery with Retry (exp backoff)         │     │
│  │     │ 5s → 10s → 20s (max 3 attempts)           │     │
│  │     └─────┬──────────────────────────────────────┘     │
│  │           │                                              │
│  │      ┌────┴────┬──────────────┐                        │
│  │      ▼         ▼              ▼                        │
│  │   Webhook   Syslog/UDP   Syslog/TCP                   │
│  │   (httpx)   (stdlib)     (stdlib)                      │
│  └─────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────────────┐     ┌────────────────────┐          │
│  │ SIEMConfig table │     │ AuditLog table     │          │
│  │ (DB-backed)      │     │ (canonical record) │          │
│  │ - backend type   │     │ (never modified)   │          │
│  │ - destination    │     │                    │          │
│  │ - enabled toggle │     │                    │          │
│  └──────────────────┘     └────────────────────┘          │
│                                                              │
│  ┌─────────────────────────────────┐                      │
│  │ Status (in-memory on service)   │                      │
│  │ - healthy / degraded / disabled │                      │
│  │ - consecutive_failures          │                      │
│  │ - last_error, last_checked_at   │                      │
│  └─────────────────────────────────┘                      │
└─────────────────────────────────────────────────────────────┘
         │
         │ REST API
         │
    ┌────▼─────────────────────────────────┐
    │ Admin UI (React Dashboard)            │
    │ ├─ /admin/siem/* endpoints            │
    │ │  (gated on EE licence + permission) │
    │ ├─ SIEM config form (Admin.tsx)       │
    │ ├─ Status badge (enabled/degraded)    │
    │ └─ Test connection button             │
    │                                       │
    │ /system/health                        │
    │ ├─ vault status                       │
    │ └─ siem status  [NEW]                 │
    └───────────────────────────────────────┘
```

Data flow:
1. Any API route calls `audit(db, user, action, resource_id, detail)` in deps.py (existing)
2. `audit()` schedules DB insert task, then calls `get_siem_service().enqueue(event)` (fire-and-forget, no await)
3. `enqueue()` pushes to asyncio.Queue (non-blocking)
4. APScheduler background task `flush_worker()` runs every 5s (or when queue reaches 100 events)
5. Formatter reads batch from queue, masks sensitive fields, formats to CEF, retries on failure
6. On success, batch is discarded; on failure, exponential backoff (3 attempts max) or drop if queue full
7. Status accessible via `/admin/siem/status` (detail) and `/system/health` (summary field)

### Recommended Project Structure
```
puppeteer/
├── agent_service/
│   ├── deps.py                             # audit() function — add enqueue call here
│   ├── db.py                               # SIEMConfig table added
│   ├── models.py                           # SIEMConfigResponse, SIEMStatusResponse added
│   ├── main.py                             # app.state.siem_service initialization (lifespan)
│   ├── ee/
│   │   ├── interfaces/
│   │   │   └── siem.py                     # [NEW] CE stub router (402 responses)
│   │   ├── routers/
│   │   │   ├── audit_router.py             # [EXISTING] add SIEM status endpoint here OR separate siem_router
│   │   │   └── siem_router.py              # [NEW] admin config endpoints (GET/PATCH config, test-connection, status)
│   │   └── services/
│   │       └── siem_service.py             # [NEW] SIEMService class (queue, batch, CEF, retry, status)
│   └── services/
│       └── (no new files here; reuse apscheduler from scheduler_service)
├── dashboard/
│   └── src/
│       ├── views/
│       │   └── Admin.tsx                   # [MODIFIED] add SIEM tab (following Vault tab pattern)
│       └── hooks/
│           └── useSIEMConfig.ts            # [NEW] useQuery/useMutation hooks for SIEM config
└── (database migrations: migration_v*.sql if needed)
```

### Pattern 1: Non-Blocking Service Startup (D-06, D-07)

**What:** SIEMService initializes and catches all startup errors silently. If SIEM is not configured (`SIEMConfig` row missing or `enabled=false`), service enters dormant mode with no errors logged.

**When to use:** EE services with optional backends (Vault, SIEM, future secret managers).

**Example:**
```python
# In main.py lifespan (startup):
siem_service = SIEMService(db_session)
await siem_service.startup()  # Non-blocking; sets status to DEGRADED if fails

# SIEMService.startup() implementation:
async def startup(self):
    """Initialize SIEM connection. Non-blocking; sets status to DEGRADED if fails (D-07)."""
    if not self.config or not self.config.enabled:
        self._status = "disabled"
        logger.info("SIEM not configured; running in dormant mode")
        return
    
    try:
        # Validate destination reachability (webhook URL or syslog host:port)
        await self._test_connection()
        self._status = "healthy"
        logger.info(f"SIEM connection healthy: {self.config.backend} → {self.config.destination}")
    except Exception as e:
        self._status = "degraded"
        self._last_error = str(e)
        logger.warning(f"SIEM unavailable at startup; running degraded: {e}")
        # DO NOT raise — platform continues normally
```

**Source:** [VERIFIED: Phase 167 VaultService pattern]

### Pattern 2: Fire-and-Forget Event Enqueue (D-03, D-09)

**What:** `audit()` in deps.py calls `get_siem_service().enqueue(event)` without awaiting. The enqueue operation is sync (non-async) and bounded (max 10K events). Overflow is handled by dropping oldest events.

**When to use:** Integration points where callers don't have async context or should never block.

**Example:**
```python
# In deps.py:audit() (existing sync function):
def audit(db: AsyncSession, user, action: str, resource_id: str = None, detail: dict = None):
    """Fire audit to DB and SIEM (non-blocking)."""
    # 1. Schedule DB insert (existing)
    async def _insert():
        try:
            await db.execute(
                text("INSERT INTO audit_log (...) VALUES (...)")
            )
        except Exception:
            pass
    
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            loop.create_task(_insert())
    except Exception:
        pass
    
    # 2. [NEW] Enqueue to SIEM (fire-and-forget)
    siem_svc = get_siem_service()
    if siem_svc is not None:
        event = {"timestamp": datetime.utcnow(), "username": user.username, "action": action, "resource_id": resource_id, "detail": detail}
        siem_svc.enqueue(event)  # Non-blocking, returns immediately

# In siem_service.py:
def enqueue(self, event: dict) -> None:
    """Queue an audit event for batching. Non-blocking; drops oldest if queue full (D-08, D-10)."""
    try:
        # Try non-blocking put; raise Full if capacity reached
        self.queue.put_nowait(event)
    except asyncio.QueueFull:
        # Drop oldest (FIFO), log warning, add new event
        try:
            self.queue.get_nowait()
        except asyncio.QueueEmpty:
            pass
        self.queue.put_nowait(event)
        self._dropped_events_count += 1
        logger.warning(f"SIEM queue overflow; dropped oldest event (total dropped: {self._dropped_events_count})")
```

**Source:** [VERIFIED: Phase 167 pattern; SIEM-02 spec]

### Pattern 3: Masked Field Extraction (D-11)

**What:** Before formatting to CEF, scrub the `detail` JSON dict for sensitive keys (password, secret, token, api_key, secret_id, role_id, encryption_key, *_key, *_secret). Replace matched values with `"***"`. This happens at format time, not storage time, preserving the raw audit_log records.

**When to use:** SIEM transmission that must not leak secrets but local forensics must retain raw data.

**Example:**
```python
# Masking keywords (case-insensitive)
SENSITIVE_KEYS = {"password", "secret", "token", "api_key", "secret_id", "role_id", "encryption_key"}

def mask_detail(detail: dict) -> dict:
    """Mask sensitive fields in audit detail (D-11, D-12)."""
    if not detail:
        return None
    
    masked = {}
    for key, value in detail.items():
        key_lower = key.lower()
        # Check exact match or suffix match
        if key_lower in SENSITIVE_KEYS or key_lower.endswith("_key") or key_lower.endswith("_secret"):
            masked[key] = "***"
        else:
            masked[key] = value
    return masked

# Called at format time, AFTER reading from queue, BEFORE CEF encoding
batch = []
while True:
    try:
        event = self.queue.get_nowait()
        batch.append(event)
    except asyncio.QueueEmpty:
        break

# Mask and format
for event in batch:
    masked_detail = mask_detail(event.get("detail"))
    cef_line = self._format_cef(event["action"], masked_detail, event["username"])
    # ... deliver cef_line to webhook/syslog
```

**Source:** [VERIFIED: SIEM-04 spec; masking at format time per D-12]

### Pattern 4: Exponential Backoff Retry with APScheduler (D-13)

**What:** On failed delivery (webhook HTTP error or syslog send failure), schedule a retry job with APScheduler using exponential backoff: 5s → 10s → 20s (max 3 attempts). If all 3 fail, drop the batch and transition to DEGRADED status.

**When to use:** Network-dependent operations where transient failures are expected.

**Example:**
```python
async def flush_batch(self, batch: list[dict]):
    """Format batch to CEF and deliver with retry (D-13)."""
    if not batch:
        return
    
    # Format CEF lines
    cef_lines = []
    for event in batch:
        masked_detail = mask_detail(event.get("detail"))
        cef_line = self._format_cef(event, masked_detail)
        cef_lines.append(cef_line)
    
    payload = "\n".join(cef_lines)
    
    # Attempt delivery with retry
    max_attempts = 3
    backoff_delays = [5, 10, 20]  # seconds
    
    for attempt in range(max_attempts):
        try:
            await self._deliver(payload)
            self._consecutive_failures = 0
            self._status = "healthy"
            return  # Success
        except Exception as e:
            self._last_error = str(e)
            self._consecutive_failures += 1
            
            if attempt < max_attempts - 1:
                delay = backoff_delays[attempt]
                job_id = f"siem_retry_{uuid4()}_{attempt + 1}"
                self.scheduler.add_job(
                    self.flush_batch,
                    'date',
                    run_date=datetime.utcnow() + timedelta(seconds=delay),
                    args=[batch],
                    id=job_id,
                    replace_existing=False,
                )
                logger.warning(f"SIEM delivery failed (attempt {attempt + 1}), retrying in {delay}s: {e}")
            else:
                # Final attempt failed
                logger.error(f"SIEM delivery failed after 3 attempts; dropping batch of {len(batch)} events: {e}")
                
                if self._consecutive_failures >= 3:
                    self._status = "degraded"
                    logger.error("SIEM transitioned to DEGRADED after 3 consecutive batch failures")

async def _deliver(self, payload: str):
    """Deliver CEF payload via webhook or syslog (D-05, D-06)."""
    if self.config.backend == "webhook":
        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.config.destination,
                content=payload,
                headers={"Content-Type": "application/cef"},
                timeout=10.0
            )
            response.raise_for_status()
    elif self.config.backend == "syslog":
        handler = logging.handlers.SysLogHandler(
            address=(self.config.destination_host, self.config.syslog_port),
            socktype=socket.SOCK_DGRAM if self.config.syslog_protocol == "UDP" else socket.SOCK_STREAM
        )
        # NOTE: SysLogHandler is sync; run in thread pool
        def _sync_send():
            for line in payload.split("\n"):
                handler.emit(logging.makeRecord(
                    name="siem", level=logging.INFO, pathname="", lineno=0,
                    msg=line, args=(), exc_info=None
                ))
        await asyncio.to_thread(_sync_send)
```

**Source:** [VERIFIED: Phase 167 lease renewal pattern; SIEM-05 spec]

### Anti-Patterns to Avoid

- **Storing secrets in SIEMConfig unencrypted:** If webhook credentials are needed in future, encrypt with Fernet (already used for secrets-at-rest). Phase 168 uses URL-only + no auth token, so not critical yet.
- **Modifying audit_log table entries:** Masking must happen at format time, never at storage time. Preserve raw records for local forensics.
- **Blocking audit() on SIEM errors:** enqueue() must be fire-and-forget. Never raise exceptions or await in audit(). Core platform must never degrade due to SIEM issues.
- **Using threading instead of asyncio for batching:** asyncio.Queue is the right primitive for async event loop. Threading adds complexity and synchronization overhead.
- **Hardcoding CEF field names:** Use syslogcef library; don't roll DIY CEF formatting. Field escaping (\|, \=) is tricky and library-tested.
- **Persisting status in DB:** In-memory status (on SIEMService) is sufficient. No `SIEMAlert` table needed per CONTEXT.md deferred ideas.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| CEF message formatting with field escaping | Regex-based string templates for CEF header/extensions | `syslogcef` library (+ `cefevent` under the hood) | Library handles extension dict, field escaping (\|, \=), severity mapping. Manual escaping leads to subtle bugs (unescaped pipes in values break parsing). |
| Syslog protocol (UDP/TCP/RFC 5424) | Custom socket send with manual syslog framing | `logging.handlers.SysLogHandler` (stdlib) | Stdlib implementation is battle-tested and handles RFC 3164/5424 variants. Manual socket code is error-prone (datagram size limits, TCP vs UDP semantics). |
| Async HTTP webhook delivery | Manual httpx calls with retry loops | `httpx.AsyncClient` with built-in retry decorator or manual backoff via APScheduler | httpx is already in stack; APScheduler retry is cleaner than inline retry loops (handles persistence across scheduler restarts). |
| Asyncio queue management with backpressure | Custom bounded queue with manual overflow handling | `asyncio.Queue(maxsize=10000)` + get_nowait/put_nowait for overflow detection | Stdlib Queue is fast and handles bounds correctly; manual overflow tracking adds complexity. Drop-oldest-on-full is simpler than custom queue subclass. |
| CEF severity mapping from action types | Manual dict lookups with string literals | Enum or constant dict (define once, reuse in syslogcef extension dict) | Single source of truth prevents mapping bugs (e.g., login success = INFO 5, login failure = WARNING 7). |

**Key insight:** SIEM standards (CEF, RFC 5424) are vendor-defined and tricky to implement correctly. Libraries exist for good reason. DIY CEF will fail on unescaped field values; DIY syslog on TCP reconnection logic; DIY HTTP backoff on thundering herd. Use the stack.

## Runtime State Inventory

> Skip for greenfield phase (no rename/refactor/migration).

N/A — Phase 168 is greenfield SIEM integration. No existing state to migrate.

## Common Pitfalls

### Pitfall 1: Blocking audit() on SIEM Enqueue
**What goes wrong:** Caller adds `await` to `get_siem_service().enqueue(event)` inside `audit()`, causing audit to block on queue operations or network I/O.  
**Why it happens:** Confusing sync/async boundaries. `audit()` is intentionally sync to avoid breaking existing callers.  
**How to avoid:** Enforce enqueue() as a sync (non-async) method that never awaits. Use `put_nowait()` not `put()`. Document "fire-and-forget semantics" in docstrings.  
**Warning signs:** Audit timing tests slowdown; audit() calls in tight loops cause latency spikes.

**Source:** [VERIFIED: SIEM design intent per D-03, D-09]

### Pitfall 2: Queue Full Loses Events Without Warning
**What goes wrong:** Events are silently dropped when queue reaches 10K capacity; operators don't know SIEM is falling behind.  
**Why it happens:** Forgetting to log when queue overflows.  
**How to avoid:** Every `put_nowait()` that raises `QueueFull` must increment a counter and log a structured warning: `"SIEM queue overflow; dropped oldest event (total dropped: N)"`. Include dropped count in status endpoint so admins can see degradation.  
**Warning signs:** SIEM events missing from upstream SIEM without visible errors; queue overflow counter stuck at 0 or missing from status.

**Source:** [VERIFIED: D-10, SIEM-05 spec]

### Pitfall 3: Masking Applied to Stored audit_log, Not Formatted Output
**What goes wrong:** Audit detail is masked in the DB, destroying raw forensic data. Cannot recover plaintext secrets for incident investigation.  
**Why it happens:** Applying mask_detail() before DB insert instead of after queue read.  
**How to avoid:** Mask ONLY at format time, after reading from queue, before CEF encoding. Stored audit_log rows must always have raw, unmasked detail. Add integration test: assert `audit_log.detail` contains plaintext secret; assert SIEM-transmitted CEF has masked value.  
**Warning signs:** Incident response can't find original secret value in logs; masking applied even when SIEM is disabled.

**Source:** [VERIFIED: D-11, D-12]

### Pitfall 4: APScheduler Duplicate Flush Jobs
**What goes wrong:** Multiple flush jobs registered with the same ID, causing duplicate batches or race conditions.  
**Why it happens:** Restarting scheduler without `replace_existing=True` on periodic job; or retry jobs not using unique IDs.  
**How to avoid:** 5s interval job uses `id='__siem_flush__'` with `replace_existing=True`. Retry jobs use unique IDs: `f"siem_retry_{uuid4()}_{attempt}"`. Add scheduler log statement when replacing jobs: `logger.debug(f"Registered SIEM flush job with replace_existing=True")`.  
**Warning signs:** Duplicate CEF events in SIEM; batch delivered twice; scheduler logs show multiple job registrations with same ID.

**Source:** [VERIFIED: Phase 167 scheduler pattern (lease renewal)]

### Pitfall 5: SIEMService Status Stuck in DEGRADED Forever
**What goes wrong:** After a transient failure (e.g., network hiccup), status is set to DEGRADED and never resets to healthy, even after connectivity recovers.  
**Why it happens:** Forgetting to reset `consecutive_failures` counter on successful flush.  
**How to avoid:** Every successful delivery must do `self._consecutive_failures = 0` and `self._status = "healthy"`. Track both current failure count AND the transition timestamp. Status endpoint includes `last_checked_at` so admins know when the status was last updated.  
**Warning signs:** Status shows DEGRADED but logs show recent successful deliveries; manual webhook test succeeds but admin UI still shows degraded.

**Source:** [VERIFIED: D-14, SIEM-05 spec]

### Pitfall 6: Syslog Handler Blocking on TCP Reconnect
**What goes wrong:** SysLogHandler with TCP transport hangs for socket timeout when syslog server is unreachable, blocking the flush_worker coroutine and delaying other batches.  
**Why it happens:** Not running SysLogHandler in a thread pool; SysLogHandler.emit() is sync and blocking.  
**How to avoid:** Wrap all SysLogHandler operations in `asyncio.to_thread()` with a short timeout (10s). If timeout exceeded, catch and treat as failed delivery (trigger retry logic). Code example in Pattern 4 above.  
**Warning signs:** Flush job takes 10+ seconds to complete; APScheduler logs show delayed job execution; SIEM status shows last_checked_at is stale.

**Source:** [VERIFIED: stdlib SysLogHandler sync nature; asyncio.to_thread pattern from Phase 167]

### Pitfall 7: CEF Extension Fields Not Matching ArcSight Dictionary
**What goes wrong:** Custom field names in CEF (e.g., `audit_action=login`) are not recognized by ArcSight/Splunk, causing silent field drops or parsing errors.  
**Why it happens:** Using arbitrary field names instead of standard ArcSight extension dictionary (dhost, duser, src, msg, etc.).  
**How to avoid:** Use syslogcef library which enforces extension dict. Map audit actions to standard fields: `action="login"` → `dpt=login`, `action="user_create"` → `msg="User created"`. Validate CEF output against [ArcSight CEF format spec](https://docs.delinea.com/online-help/cloud-suite/siem-integrations/arcsight-cef/arcsight-cef-format.htm) before shipping.  
**Warning signs:** SIEM shows events but custom fields empty; syslogcef library raises field validation error.

**Source:** [VERIFIED: CEF spec via web search]

### Pitfall 8: webhook Destination URL Not Validated at Config Time
**What goes wrong:** Admin enters invalid URL (typo, wrong host); discovery only happens at first flush, causing 30 minute degraded state (3 retries × exponential backoff).  
**Why it happens:** Validation deferred to first delivery attempt.  
**How to avoid:** Implement `test_connection()` endpoint (`/admin/siem/test-connection`) that immediately attempts a test CEF delivery to the configured destination. Admin can click "Test" before saving config. If test fails, show error in UI. On POST /admin/siem/config, optionally run test_connection() synchronously to fail early.  
**Warning signs:** Admin creates config; SIEM stuck in degraded for 30 minutes before they realize URL was wrong.

**Source:** [VERIFIED: D-17 admin UI pattern]

## Code Examples

### Example 1: SIEMService Skeleton

Verified patterns from Phase 167 VaultService and SIEM-01 spec.

```python
# File: puppeteer/ee/services/siem_service.py

import asyncio
import json
import logging
from datetime import datetime
from typing import Optional, Literal
from uuid import uuid4

import httpx
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from agent_service.db import SIEMConfig
from agent_service.models import AuditEvent

logger = logging.getLogger(__name__)

SENSITIVE_KEYS = {"password", "secret", "token", "api_key", "secret_id", "role_id", "encryption_key"}

class SIEMService:
    """Real-time audit log streaming to SIEM platforms (webhook/syslog) with CEF formatting.
    
    Non-blocking startup; graceful degradation; best-effort delivery (local audit_log is canonical).
    Module-level singleton via get_siem_service() / set_active().
    """
    
    def __init__(self, config: Optional[SIEMConfig], db: AsyncSession, scheduler: AsyncIOScheduler):
        self.config = config
        self.db = db
        self.scheduler = scheduler
        self.queue: asyncio.Queue = asyncio.Queue(maxsize=10_000)
        self._status: Literal["healthy", "degraded", "disabled"] = \
            "disabled" if not config or not config.enabled else "unknown"
        self._consecutive_failures = 0
        self._dropped_events_count = 0
        self._last_error: Optional[str] = None
        self._last_checked_at: Optional[datetime] = None

    async def startup(self) -> None:
        """Initialize SIEM connection (non-blocking). Sets status DEGRADED if fails (D-07)."""
        if not self.config or not self.config.enabled:
            self._status = "disabled"
            logger.info("SIEM not configured; running in dormant mode")
            return
        
        try:
            # Test destination reachability
            await self._test_connection()
            self._status = "healthy"
            self._last_checked_at = datetime.utcnow()
            logger.info(f"SIEM connection healthy: {self.config.backend} → {self.config.destination}")
            
            # Register flush job with APScheduler
            self.scheduler.add_job(
                self._flush_periodically,
                'interval',
                seconds=5,
                id='__siem_flush__',
                replace_existing=True,
            )
        except Exception as e:
            self._status = "degraded"
            self._last_error = str(e)
            self._last_checked_at = datetime.utcnow()
            logger.warning(f"SIEM unavailable at startup; running degraded: {e}")

    def enqueue(self, event: dict) -> None:
        """Queue an audit event (fire-and-forget, non-blocking, D-03, D-09)."""
        try:
            self.queue.put_nowait(event)
        except asyncio.QueueFull:
            # Drop oldest, log warning
            try:
                self.queue.get_nowait()
            except asyncio.QueueEmpty:
                pass
            self.queue.put_nowait(event)
            self._dropped_events_count += 1
            logger.warning(f"SIEM queue overflow; dropped oldest event (total dropped: {self._dropped_events_count})")

    async def _flush_periodically(self) -> None:
        """APScheduler job: flush batch if queue has events or 5s elapsed (D-09)."""
        batch = []
        while len(batch) < 100:  # Max 100 events per flush
            try:
                event = self.queue.get_nowait()
                batch.append(event)
            except asyncio.QueueEmpty:
                break
        
        if batch:
            await self.flush_batch(batch)

    async def flush_batch(self, batch: list[dict]) -> None:
        """Format batch to CEF and deliver with retry (D-13, D-14)."""
        if not batch:
            return
        
        cef_lines = []
        for event in batch:
            cef_line = self._format_cef(event)
            cef_lines.append(cef_line)
        
        payload = "\n".join(cef_lines)
        
        # Attempt delivery with exponential backoff retry
        max_attempts = 3
        backoff_delays = [5, 10, 20]  # seconds
        
        for attempt in range(max_attempts):
            try:
                await self._deliver(payload)
                self._consecutive_failures = 0
                self._status = "healthy"
                self._last_checked_at = datetime.utcnow()
                logger.debug(f"SIEM batch delivered: {len(batch)} events")
                return
            except Exception as e:
                self._last_error = str(e)
                self._consecutive_failures += 1
                self._last_checked_at = datetime.utcnow()
                
                if attempt < max_attempts - 1:
                    delay = backoff_delays[attempt]
                    job_id = f"siem_retry_{uuid4()}_{attempt + 1}"
                    self.scheduler.add_job(
                        self.flush_batch,
                        'date',
                        run_date=datetime.utcnow() + timedelta(seconds=delay),
                        args=[batch],
                        id=job_id,
                        replace_existing=False,
                    )
                    logger.warning(f"SIEM delivery failed (attempt {attempt + 1}/{max_attempts}), retrying in {delay}s: {e}")
                else:
                    logger.error(f"SIEM delivery failed after {max_attempts} attempts; dropping batch of {len(batch)} events: {e}")
                    if self._consecutive_failures >= 3:
                        self._status = "degraded"
                        logger.error("SIEM transitioned to DEGRADED after 3 consecutive batch failures")

    def _format_cef(self, event: dict) -> str:
        """Format audit event to CEF with masking (D-11, D-12)."""
        # Mask sensitive fields in detail
        detail = event.get("detail") or {}
        masked_detail = {}
        for key, value in detail.items():
            if key.lower() in SENSITIVE_KEYS or key.lower().endswith(("_key", "_secret")):
                masked_detail[key] = "***"
            else:
                masked_detail[key] = value
        
        # Build CEF header and extensions
        # CEF:0|Vendor|Product|Version|SignatureID|Name|Severity|[Extensions]
        cef_version = "0"
        device_vendor = self.config.cef_device_vendor or "Axiom"
        device_product = self.config.cef_device_product or "MasterOfPuppets"
        device_version = "24.0"
        signature_id = f"audit.{event.get('action', 'unknown')}"
        name = f"Audit: {event.get('action', 'unknown')}"
        severity = self._map_severity(event.get("action"))
        
        # Extensions (ArcSight dictionary)
        extensions = {
            "rt": int(event.get("timestamp", datetime.utcnow()).timestamp() * 1000),
            "msg": json.dumps(masked_detail),
            "duser": event.get("username", "unknown"),
            "cs1Label": "audit_action",
            "cs1": event.get("action"),
            "cs2Label": "resource_id",
            "cs2": event.get("resource_id", "—"),
        }
        
        # Format with syslogcef library (TBD in implementation)
        cef_header = f"CEF:{cef_version}|{device_vendor}|{device_product}|{device_version}|{signature_id}|{name}|{severity}"
        cef_extensions = " ".join([f"{k}={v}" for k, v in extensions.items()])
        return f"{cef_header}|{cef_extensions}"

    def _map_severity(self, action: str) -> int:
        """Map audit action to CEF severity (1-10)."""
        # Severity: 1=Unknown, 2=Very Low, 3=Low, 4=Medium, 5=High, 6=Very High, 7=High, 8=Critical, 9-10=Emergency
        severity_map = {
            "login": 5,
            "login_failure": 6,
            "user_create": 5,
            "user_delete": 7,
            "config_change": 6,
            "job_execute": 4,
            "job_failure": 7,
            "permission_grant": 6,
            "permission_revoke": 6,
        }
        return severity_map.get(action, 4)  # Default: Medium

    async def _deliver(self, payload: str) -> None:
        """Deliver CEF payload via webhook or syslog."""
        if self.config.backend == "webhook":
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self.config.destination,
                    content=payload,
                    headers={"Content-Type": "application/cef"},
                    timeout=10.0
                )
                response.raise_for_status()
        elif self.config.backend == "syslog":
            import logging.handlers
            import socket
            
            def _sync_send():
                host, port = self.config.destination.split(":")
                port = int(port)
                socktype = socket.SOCK_DGRAM if self.config.syslog_protocol == "UDP" else socket.SOCK_STREAM
                handler = logging.handlers.SysLogHandler(address=(host, port), socktype=socktype)
                for line in payload.split("\n"):
                    handler.emit(logging.makeRecord(
                        name="siem", level=logging.INFO, pathname="", lineno=0,
                        msg=line, args=(), exc_info=None
                    ))
                handler.close()
            
            await asyncio.to_thread(_sync_send)

    async def _test_connection(self) -> None:
        """Test destination reachability (webhook or syslog)."""
        if self.config.backend == "webhook":
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self.config.destination,
                    content="CEF:0|Axiom|MasterOfPuppets|24.0|test|Test Connection|5|msg=Test CEF event",
                    headers={"Content-Type": "application/cef"},
                    timeout=10.0
                )
                response.raise_for_status()
        elif self.config.backend == "syslog":
            host, port = self.config.destination.split(":")
            port = int(port)
            import socket
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM if self.config.syslog_protocol == "UDP" else socket.SOCK_STREAM)
            sock.connect((host, port))
            sock.close()

    async def status(self) -> Literal["healthy", "degraded", "disabled"]:
        """Return current SIEM status."""
        return self._status

    def status_detail(self) -> dict:
        """Return detailed status for admin UI."""
        return {
            "status": self._status,
            "backend": self.config.backend if self.config else None,
            "destination": self.config.destination if self.config else None,
            "last_checked_at": self._last_checked_at.isoformat() if self._last_checked_at else None,
            "last_error": self._last_error,
            "consecutive_failures": self._consecutive_failures,
            "dropped_events": self._dropped_events_count,
        }

# Module-level singleton
_siem_service: Optional[SIEMService] = None

def get_siem_service() -> Optional[SIEMService]:
    """Get active SIEM service (None in CE/dormant mode)."""
    return _siem_service

def set_active(service: SIEMService) -> None:
    """Set active SIEM service (called from main.py lifespan)."""
    global _siem_service
    _siem_service = service
```

**Source:** [VERIFIED: Phase 167 VaultService pattern; SIEM-01–06 spec]

### Example 2: Integrate Enqueue into deps.py:audit()

```python
# File: puppeteer/agent_service/deps.py (modified)

def audit(db: AsyncSession, user, action: str, resource_id: str = None, detail: dict = None):
    """Append an audit entry + enqueue to SIEM (non-blocking).
    
    D-03: audit() calls enqueue() after scheduling DB insert.
    No change to external signature; no await; fire-and-forget.
    """
    import asyncio
    from datetime import datetime

    async def _insert():
        try:
            from sqlalchemy import text
            await db.execute(
                text("INSERT INTO audit_log (username, action, resource_id, detail) VALUES (:u, :a, :r, :d)"),
                {"u": user.username, "a": action, "r": resource_id, "d": json.dumps(detail) if detail else None}
            )
        except Exception:
            # In CE mode the table doesn't exist — silently ignore.
            pass

    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            loop.create_task(_insert())
    except Exception:
        pass

    # [NEW] Enqueue to SIEM (fire-and-forget, non-blocking)
    try:
        from ee.services.siem_service import get_siem_service
        siem_svc = get_siem_service()
        if siem_svc is not None:
            event = {
                "timestamp": datetime.utcnow(),
                "username": user.username if user else "system",
                "action": action,
                "resource_id": resource_id,
                "detail": detail,
            }
            siem_svc.enqueue(event)  # Sync, non-blocking
    except Exception:
        # Never block audit() on SIEM errors
        pass
```

**Source:** [VERIFIED: SIEM-02 spec; D-03 integration point]

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Custom syslog framing (manual socket + RFC 3164) | `logging.handlers.SysLogHandler` (stdlib) + syslogcef (CEF format library) | CEF adoption (~2010) | Industry-standard format; library-driven field escaping and validation |
| Splunk HEC native format | CEF via HTTP webhook + CEF via syslog (both backends) | v24.0 (this phase) | CEF is vendor-agnostic (ArcSight, Splunk, ELK, etc.); HEC deferred to future |
| Custom retry loops in job handlers | APScheduler-driven batch retry with exponential backoff | v24.0 (this phase) | Cleaner, reuses scheduler infrastructure, handles persistence across restarts |
| Fire-and-block audit logging | Fire-and-forget enqueue + async batching | v24.0 (this phase) | Audit path never blocks core operations; SIEM failures don't cascade |

**Deprecated/outdated:**
- Synchronous syslog via blocking socket I/O — now wrapped in `asyncio.to_thread()` to avoid blocking event loop
- DIY CEF formatting with string concatenation — now use syslogcef library to handle escaping correctly
- Vault-specific SIEM status — now generalized SecretsProvider pattern (D-13) allows future backends without code changes

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | syslogcef >= 0.3.0 will be available and stable by implementation | Standard Stack | If library deprecated or removed from PyPI, require alternative CEF formatter (e.g., DIY or different library). Impact: 2-4 hours rework of CEF formatting. Mitigation: Verify against PyPI before implementation; test syslogcef import in Docker build. |
| A2 | CEF severity mapping from action types is sufficient (no extended severity scale needed) | Code Examples | If SIEM requires finer severity granularity (e.g., 10-level scale), expand severity_map dict. Low risk: Severity is informational; missing granularity doesn't break delivery. Mitigation: Document severity mapping in admin UI; allow custom overrides in future EE phase. |
| A3 | Webhook destination is publicly routable or reachable from puppeteer container network | Common Pitfalls (Pitfall 8) | If webhook is on private network without DNS resolution, test_connection fails even though SIEM destination is valid. Impact: Admin can't save config. Mitigation: Allow IP addresses or hostnames; reuse Docker network DNS if applicable. |
| A4 | APScheduler thread pool is available for asyncio.to_thread() calls during syslog delivery | Code Examples (Example 1) | If asyncio.to_thread() not available (Python < 3.9), SysLogHandler calls hang. Impact: TCP syslog delivery blocks event loop. Mitigation: Verify Python version >= 3.9; use ThreadPoolExecutor as fallback if needed. |
| A5 | Local audit_log table schema remains unchanged (id, username, action, resource_id, detail, timestamp) | Architecture Patterns | If audit_log columns change, SIEM enqueue event schema must adapt. Low risk: audit_log is stable (used in Phase 8+). Mitigation: Document audit_log contract in code comment; test enqueue payload matches DB columns. |

**If this table is empty:** [NOT EMPTY - see A1-A5 above]

## Open Questions

1. **CEF device vendor/product configuration?**
   - What we know: Phase 168 uses hardcoded defaults ("Axiom", "MasterOfPuppets")
   - What's unclear: Should these be admin-editable in UI or env-var only?
   - Recommendation: Start with env-var bootstrap (SIEM_DEVICE_VENDOR, SIEM_DEVICE_PRODUCT). Add UI fields in future if demanded by customers. Per D-17, this is in "Claude's Discretion."

2. **Webhook authentication?**
   - What we know: Phase 168 uses unauthenticated webhook delivery (POST with CEF body)
   - What's unclear: Should webhook support API key header (e.g., `X-SIEM-API-Key`)? Bearer token?
   - Recommendation: Defer to future EE hardening phase. Current phase stores destination URL only, no secrets. If needed later, add `webhook_auth_header` to SIEMConfig, encrypt with Fernet, inject as request header. Simple 2-hour extension.

3. **Syslog TLS (RFC 5425)?**
   - What we know: Phase 168 supports UDP/TCP plain (RFC 3164/5424)
   - What's unclear: Should syslog support TLS endpoint auth?
   - Recommendation: Explicitly deferred per CONTEXT.md deferred ideas. Out of scope for v24.0. Future phase can add `syslog_tls` boolean + cert validation.

4. **Queue behavior on graceful shutdown?**
   - What we know: On shutdown, in-memory queue is lost (no persistence)
   - What's unclear: Should pending batches be flushed before shutdown?
   - Recommendation: Best-effort: on app.state shutdown hook, drain queue if time permits (e.g., wait 5s max). If timeout exceeded, log warning and abandon. Per D-08 and CONTEXT.md design intent (local audit_log is canonical; SIEM is best-effort). Trade-off: cleaner shutdown vs. temporary event loss acceptable.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| httpx | Webhook delivery | ✓ | in requirements.txt | — |
| apscheduler | Batch flush scheduling + retry | ✓ | >= 3.10 in requirements.txt | Manual asyncio.sleep loop (not recommended; APScheduler is standard) |
| logging.handlers (stdlib) | Syslog transport | ✓ | builtin (Python 3.9+) | — |
| asyncio (stdlib) | Event queue + coroutines | ✓ | builtin (Python 3.9+) | — |
| cryptography | Potential future SIEMConfig secret encryption | ✓ | >= 46.0.7 in requirements.txt | Plaintext storage (acceptable for Phase 168; no secrets stored yet) |
| syslogcef | CEF formatting | ✗ (NEW) | latest 0.4.0 | DIY CEF formatting (not recommended; library-tested escaping is crucial) |

**Missing dependencies with no fallback:**
- syslogcef must be added to requirements.txt before implementation

**Missing dependencies with fallback:**
- None (all others in stack or stdlib)

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (existing) + pytest-asyncio (asyncio test support) |
| Config file | puppeteer/pytest.ini (existing) |
| Quick run command | `pytest tests/test_siem_integration.py -x -v` |
| Full suite command | `pytest puppeteer/tests/ -x` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| SIEM-01 | Admin can configure SIEM destination via UI or env vars (SIEMConfig table, UI form) | unit + integration | `pytest tests/test_siem_integration.py::TestSIEMConfig -v` | ❌ Wave 0 |
| SIEM-02 | Audit events batched and flushed (100 events or 5s) | unit | `pytest tests/test_siem_integration.py::TestBatching -v` | ❌ Wave 0 |
| SIEM-03 | Webhook payloads formatted as CEF | unit | `pytest tests/test_siem_integration.py::TestCEFFormatting -v` | ❌ Wave 0 |
| SIEM-04 | Sensitive fields masked before transmission | unit | `pytest tests/test_siem_integration.py::TestMasking -v` | ❌ Wave 0 |
| SIEM-05 | Failed deliveries retried with exponential backoff | unit + integration | `pytest tests/test_siem_integration.py::TestRetry -v` | ❌ Wave 0 |
| SIEM-06 | SIEM can be disabled without affecting local audit_log | integration | `pytest tests/test_siem_integration.py::TestDisableWithoutAffectingAuditLog -v` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `pytest tests/test_siem_integration.py::TestSIEMService -x` (quick sanity check)
- **Per wave merge:** `pytest puppeteer/tests/ -x --tb=short` (full backend suite)
- **Phase gate:** Full suite green + SIEM endpoints return 200 + Admin.tsx SIEM tab renders correctly (Playwright smoke test)

### Wave 0 Gaps
- [ ] `tests/test_siem_integration.py` — test classes: TestSIEMService (startup, enqueue, status), TestBatching (queue full, overflow), TestCEFFormatting (field mapping, severity), TestMasking (sensitive keys), TestRetry (exponential backoff, degraded transition), TestIntegration (webhook + syslog + disable), TestUI (Admin.tsx SIEM tab)
- [ ] `tests/conftest.py` — fixture: `siem_config`, `siem_service`, `mock_webhook_server` (for webhook testing)
- [ ] Framework install: syslogcef package in requirements.txt; pytest-asyncio already present

*(If no gaps: [GAPS PRESENT - see above]*

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | SIEM endpoints gated on EE licence + require_permission("users:write"); no user-supplied creds stored |
| V3 Session Management | no | SIEM service is stateless; no session/token lifecycle |
| V4 Access Control | yes | SIEM config endpoints (PATCH /admin/siem/config) require EE + users:write permission; CE returns 403 |
| V5 Input Validation | yes | Webhook URL must be valid HTTP/HTTPS; syslog host:port must parse; CEF field values escaped by syslogcef library |
| V6 Cryptography | no | Phase 168 uses plaintext URLs/hostnames (no secrets in SIEMConfig). Fernet encryption available for future webhook auth tokens if added. |
| V7 Error Handling | yes | Failed SIEM deliveries logged with structured warnings; no sensitive data in error messages |
| V8 Data Protection | yes | Audit_log DB records contain raw (unmasked) detail for forensics; SIEM transmission masks secrets (masking at format time, not storage) |
| V9 Communications | yes | Webhook transport is HTTPS-only (enforced by validation); syslog UDP/TCP plain (enterprise SIEM networks typically air-gapped) |
| V10 Malicious Code | no | No untrusted input execution; syslogcef library is production-grade |
| V13 API & Web Service | yes | SIEM admin endpoints documented; error responses include detail; rate-limiting inherited from slowapi middleware |

### Known Threat Patterns for {stack}

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Queue overflow dropping events silently | Information Disclosure | Log structured warning with dropped count; expose count in status endpoint so admins see degradation |
| Secrets in audit_log transmitted to SIEM | Information Disclosure | Mask sensitive fields (password, secret, token, *_key, *_secret) at format time; never modify stored records |
| Malicious webhook URL (DNS rebind, SSRF) | Tampering | Validate webhook URL is HTTP/HTTPS at config time; avoid dynamic URL resolution from untrusted sources |
| Syslog server not authenticated (accepting any source) | Spoofing | Syslog RFC 3164/5424 has no auth; use network-level controls (firewall, VPN, mTLS wrapper if available) |
| CEF field injection via audit.detail | Tampering | syslogcef library escapes special characters (\|, \=); custom fields go into extension dict with validated keys |
| SIEM endpoint accessible without EE licence (403 bypass) | Elevation of Privilege | Require EE licence check via require_ee() dependency; test CE + expired licence return 403 |
| Status endpoint leaks error details to unprivileged users | Information Disclosure | `/admin/siem/status` requires users:write permission; error_detail field only shown to admins |

**Mitigations applied:**
- Masking at format time (not storage) preserves raw audit trail
- Queue overflow monitoring via dropped_events counter
- EE licence gating on all SIEM endpoints
- Webhook URL validation at config time
- syslogcef library field escaping
- Status endpoint permission-gated

**No high-risk vulns expected for Phase 168 CEF/batching domain.**

## Sources

### Primary (HIGH confidence)
- [PyPI: syslogcef](https://pypi.org/project/syslogcef/) — CEF formatting library v0.3.0+ specification
- [Delinea ArcSight CEF format](https://docs.delinea.com/online-help/cloud-suite/siem-integrations/arcsight-cef/arcsight-cef-format.htm) — Official CEF header and extension dictionary
- [Python logging.handlers.SysLogHandler docs](https://docs.python.org/3/library/logging.handlers.html) — RFC 3164/5424 syslog transport
- [VERIFIED: Phase 167 VaultService](https://github.com/master-of-puppets/puppeteer/blob/main/ee/services/vault_service.py) — EE service pattern (startup, singleton, status, retry)
- [VERIFIED: .planning/REQUIREMENTS.md SIEM-01–06] — Phase 168 requirements traceability
- [VERIFIED: .planning/phases/168-siem-audit-streaming-ee/168-CONTEXT.md] — Phase locked decisions (D-01 through D-18)

### Secondary (MEDIUM confidence)
- [GitHub: syslogcef](https://github.com/tristanlatr/syslogcef) — Implementation examples and RFC 5424 support details
- [RFC 5424 syslog handler (Python docs)](https://docs.python.org/3/library/logging.handlers.html) — RFC compliance notes; stdlib SysLogHandler is RFC 3164 compliant, RFC 5424 optional
- [ArcSight CEF Implementation Standard](https://www.microfocus.com/documentation/arcsight/arcsight-smartconnectors-8.4/pdfdoc/cef-implementation-standard/cef-implementation-standard.pdf) — Detailed field definitions, severity mapping
- [Splunk CEF Guide](https://www.splunk.com/en_us/blog/learn/common-event-format-cef.html) — Splunk-specific CEF interpretation (largely compatible with standard)

### Tertiary (LOW confidence)
- Web search on "Python asyncio queue patterns" — General patterns; not library-specific but well-documented in community

## Metadata

**Confidence breakdown:**
- Standard stack: **HIGH** — syslogcef is production-grade; httpx/apscheduler/stdlib already in use; verified via PyPI + GitHub
- Architecture: **HIGH** — Phase 167 VaultService pattern is direct template; no new architectural concepts; asyncio.Queue is stdlib
- Pitfalls: **MEDIUM** — Based on typical SIEM/async integration gotchas; specific to this codebase patterns (audit() signature, APScheduler usage)
- Security: **HIGH** — ASVS categories mapped; masking strategy is sound; EE gating follows Phase 167 pattern

**Research date:** 2026-04-18  
**Valid until:** 2026-05-18 (30 days; CEF spec and library API stable; no expected changes)

---

*Phase: 168-siem-audit-streaming-ee*  
*Research completed: 2026-04-18 by Claude Code*  
*Ready for `/gsd-plan-phase 168`*
