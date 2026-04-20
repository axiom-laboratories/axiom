---
phase: 168
plan: 03
subsystem: SIEM Audit Streaming (EE)
tags: [audit, siem, integration, env-bootstrap]
dependencies:
  requires: ["168-01", "168-02"]
  provides: ["audit stream to SIEM", "env var configuration bootstrap"]
  affects: ["audit()", "main.py lifespan", "SIEMService"]
tech_stack:
  added: []
  patterns: ["fire-and-forget async enqueue", "try/except error suppression", "env var bootstrap"]
key_files:
  created: []
  modified:
    - puppeteer/agent_service/deps.py
    - puppeteer/agent_service/main.py
decisions:
  - Fire-and-forget enqueue in audit() never awaits to preserve non-blocking semantics
  - SIEM bootstrap only runs on first startup if no config exists (idempotent)
  - Bootstrap requires BOTH SIEM_BACKEND and SIEM_DESTINATION to be set (fail-safe)
metrics:
  duration: "15m"
  files_modified: 2
  tasks_completed: 3
  commits: 2
---

# Phase 168 Plan 03 — Audit Integration Summary

Completed integration of SIEMService into the existing audit stream and implemented environment variable bootstrap for SIEM configuration on startup.

## Task 1: SIEM Enqueue Hook in deps.py:audit()

**Status:** COMPLETE

**Implementation:**
- Added fire-and-forget SIEM enqueue call after `loop.create_task(_insert(...))` in audit()
- Event payload structure:
  ```python
  {
    "username": user.username,
    "action": action,
    "resource_id": resource_id,
    "detail": detail,
    "timestamp": datetime.utcnow().isoformat(),
  }
  ```
- All fields match SIEMService event format expectations
- Wrapped in try/except block to suppress any SIEM errors and prevent audit blocking
- Synchronous call to `siem.enqueue()` (no await — maintains non-blocking behavior)

**Error Handling:**
- SIEM initialization errors: silently caught (`except Exception`)
- SIEM service None checks: guarded with `if siem:` before enqueue
- CE mode compatibility: `get_siem_service()` returns None in CE → no enqueue attempts

**Verification:**
```
✓ audit() includes SIEM enqueue hook with error suppression
✓ audit() event payload has all required fields (username, action, resource_id, detail, timestamp)
✓ All modules import successfully
```

**Files Modified:**
- `puppeteer/agent_service/deps.py` — lines 177-193 added

**Commit:** `03653d17` — `feat(168-03): add SIEM enqueue hook to audit()`

---

## Task 2: SIEMConfig Bootstrap from Environment Variables

**Status:** COMPLETE

**Implementation:**
- Added bootstrap block in main.py lifespan, executed before SIEM service initialization
- Bootstrap sequence:
  1. Check if SIEMConfig exists in DB (idempotent — only runs once)
  2. Read env vars: `SIEM_BACKEND`, `SIEM_DESTINATION`, and optional fields
  3. If both backend AND destination are set, create SIEMConfig
  4. Add to session and commit (creates table entry)
  5. Log success with backend name

**Environment Variables Reference:**

| Variable | Required | Default | Purpose |
|----------|----------|---------|---------|
| SIEM_BACKEND | Yes (if dest) | None | "webhook" or "syslog" |
| SIEM_DESTINATION | Yes (if backend) | None | webhook URL or syslog host |
| SIEM_ENABLED | No | false | "true"/"1" to enable immediately |
| SIEM_SYSLOG_PORT | No | 514 | Syslog port (if backend=syslog) |
| SIEM_SYSLOG_PROTOCOL | No | UDP | "UDP" or "TCP" |
| SIEM_CEF_DEVICE_VENDOR | No | Axiom | CEF header vendor field |
| SIEM_CEF_DEVICE_PRODUCT | No | MasterOfPuppets | CEF header product field |

**Error Handling:**
- ImportError (EE not available): logs debug, continues
- Any exception during bootstrap: logs warning, continues (startup not blocked)
- Existing config check handles both none and enabled cases

**Verification:**
```
✓ SIEM env var parsing works correctly
✓ All modules import successfully
```

**Files Modified:**
- `puppeteer/agent_service/main.py` — lines 170-200 added (before SIEM service init)

**Commit:** `82481744` — `feat(168-03): bootstrap SIEMConfig from env vars on startup`

---

## Task 3: End-to-End Integration Verification

**Status:** COMPLETE

**Verified Behavior:**
1. audit() function successfully calls get_siem_service() without blocking
2. Event payload has correct structure with all required fields
3. SIEM enqueue never raises exceptions that escape audit()
4. CE mode (get_siem_service()=None) does not break audit()
5. SIEM bootstrap parses env vars correctly (case-insensitive booleans)
6. Bootstrap runs exactly once (idempotent on first startup)
7. Bootstrap respects both SIEM_BACKEND and SIEM_DESTINATION requirement

**Test Results:**
```
✓ audit() includes SIEM enqueue hook with error suppression
✓ SIEM env var parsing works correctly
✓ audit() event payload has all required fields
✓ All SIEM integration checks passed
✓ All modules import successfully
```

---

## CE Mode Compatibility

- `get_siem_service()` returns None in CE mode (SIEM service not initialized)
- audit() checks `if siem:` before enqueue — no errors in CE
- Bootstrap checks for SIEMConfig availability (EE table) — skipped if missing
- Zero impact on existing CE deployments

---

## Requirements Addressed

- **SIEM-02:** ✓ Event enqueueing happens at audit time via fire-and-forget pattern (D-03, D-09)
- **SIEM-06:** ✓ Audit log table unmodified; SIEM writes are best-effort, never block audit_log path (D-12)

---

## Success Criteria

- [x] audit() function includes get_siem_service() call with try/except wrapper
- [x] Event payload has username, action, resource_id, detail, timestamp fields
- [x] SIEM.enqueue() is synchronous and non-blocking
- [x] CE mode (get_siem_service()=None) does not break audit()
- [x] SIEM errors never propagate or block audit() (caught and suppressed)
- [x] SIEMConfig bootstrap from env vars (SIEM_BACKEND, SIEM_DESTINATION, etc.) works on startup
- [x] Env var bootstrap only creates config if none exists (doesn't overwrite)
- [x] All imports and error handling work correctly

---

## Known Issues

None. Plan executed exactly as specified.

---

## Next Steps

Phase 168 Plan 04 will connect the queued SIEM events to actual transmission (webhook POST / syslog transmit).
