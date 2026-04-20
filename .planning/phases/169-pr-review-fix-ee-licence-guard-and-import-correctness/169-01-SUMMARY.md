---
phase: 169
plan: 01
type: execute
date_completed: 2026-04-18
duration_minutes: 15
tasks_completed: 3
files_modified: 2
commits: 1
---

# Phase 169 Plan 01: PR #24 Review — EE Licence Guard and Import Correctness

**One-liner:** Fixed three MEDIUM-severity code review issues: expanded EE licence guard prefix coverage, replaced absolute imports with relative imports in SIEM router, and added APScheduler shutdown guarantee via try/finally.

## Completion Summary

All three tasks completed successfully without deviations. Changes are syntactically valid Python and ready for testing.

### Tasks Executed

| Task | Name | Status | Commit |
|------|------|--------|--------|
| 1 | Add /api/admin/vault and /api/admin/siem to LicenceExpiryGuard.EE_PREFIXES | Complete | 43556165 |
| 2 | Replace absolute imports with relative imports in siem_router.py | Complete | 43556165 |
| 3 | Add try/finally around test_service startup/status in test_connection endpoint | Complete | 43556165 |

## Changes

### Task 1: LicenceExpiryGuard.EE_PREFIXES Expansion (main.py)

**File:** `puppeteer/agent_service/main.py`

Added two new strings to the `EE_PREFIXES` tuple in the `LicenceExpiryGuard` middleware class (lines 576-587):

```python
EE_PREFIXES = (
    "/api/foundry",
    "/api/audit",
    "/api/webhooks",
    "/api/triggers",
    "/api/auth-ext",
    "/api/smelter",
    "/api/executions",
    "/api/admin/bundles",
    "/api/admin/vault",      # NEW
    "/api/admin/siem",       # NEW
)
```

**Rationale:** The vault and SIEM EE routers were missing from the licence expiry guard, allowing expired-licence users to access `/api/admin/vault` and `/api/admin/siem` endpoints. The guard checks `request.url.path.lower().startswith(prefix)` against this tuple; adding these prefixes ensures expired licence holders receive HTTP 402 Payment Required instead of accessing EE features.

### Task 2: Relative Import Fixes (siem_router.py)

**File:** `puppeteer/agent_service/ee/routers/siem_router.py`

Replaced 6 absolute imports with relative imports across three functions:

**In `update_config()` function (lines 85-86):**
- `from ee.services.siem_service import ...` → `from ..services.siem_service import ...`
- `from agent_service.services.scheduler_service import ...` → `from ...services.scheduler_service import ...`

**In `test_connection()` function (lines 112-114):**
- `from ee.services.siem_service import ...` → `from ..services.siem_service import ...`
- `from agent_service.db import AsyncSessionLocal` → `from ...db import AsyncSessionLocal`
- `from agent_service.services.scheduler_service import ...` → `from ...services.scheduler_service import ...`

**In `get_status()` function (line 182):**
- `from ee.services.siem_service import get_siem_service` → `from ..services.siem_service import get_siem_service`

**Rationale:** These are lazy imports inside function bodies (used to break circular import chains). The pattern `from ee.` and `from agent_service.` violates the project's import consistency. The vault router (`vault_router.py`) already uses relative imports; this aligns SIEM router with the established convention.

### Task 3: APScheduler Shutdown Guarantee (siem_router.py)

**File:** `puppeteer/agent_service/ee/routers/siem_router.py`

Added `try/finally` wrapper around `test_service.startup()` and `status()` calls in the `test_connection` endpoint (lines 130-135):

```python
async with AsyncSessionLocal() as test_db:
    test_service = SIEMService(test_config, test_db, scheduler_service.scheduler)
    try:
        await test_service.startup()
        status = await test_service.status()
    finally:
        await test_service.shutdown()
```

**Rationale:** `SIEMService.startup()` registers background APScheduler jobs. If `status()` raises an exception, those jobs leak (never cleaned up) without the `finally` clause. The unconditional shutdown ensures cleanup even if status() fails, preventing resource exhaustion on repeated test-connection failures.

## Verification

### Automated Checks

1. **EE_PREFIXES tuple verification:**
   ```bash
   grep -A 12 "EE_PREFIXES = (" puppeteer/agent_service/main.py
   ```
   Result: Both `/api/admin/vault` and `/api/admin/siem` present in tuple ✓

2. **Absolute imports scan:**
   ```bash
   grep "from ee.services\|from agent_service\." puppeteer/agent_service/ee/routers/siem_router.py | wc -l
   ```
   Result: 0 matches (all absolute imports replaced) ✓

3. **try/finally presence:**
   ```bash
   grep -A 8 "test_service = SIEMService" puppeteer/agent_service/ee/routers/siem_router.py | grep -c "finally:"
   ```
   Result: 1 match (try/finally block present) ✓

4. **Syntax validation:**
   ```bash
   python3 -m py_compile puppeteer/agent_service/ee/routers/siem_router.py puppeteer/agent_service/main.py
   ```
   Result: Both files compile without syntax errors ✓

### Line Count Verification

- `siem_router.py`: 197 lines → 199 lines (net +2 for try/finally structure) ✓

## Deviations from Plan

None. Plan executed exactly as written. All three fixes applied mechanically without interpretation.

## Integration Notes

- No database schema changes required
- No new environment variables needed
- No breaking API changes — all fixes are internal corrections
- Existing middleware pipeline unchanged; EE_PREFIXES tuple is evaluated at request dispatch time
- Import fixes maintain function-level scoping (lazy imports remain inside function bodies)

## Self-Check: PASSED

- [x] File `puppeteer/agent_service/main.py` exists and contains updated EE_PREFIXES
- [x] File `puppeteer/agent_service/ee/routers/siem_router.py` exists and all 6 imports converted to relative form
- [x] Commit 43556165 exists in git log
- [x] Both files are syntactically valid Python
- [x] All acceptance criteria from plan met
