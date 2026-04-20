# Phase 169: PR Review Fix — EE Licence Guard and Import Correctness - Context

**Gathered:** 2026-04-18
**Status:** Ready for planning

<domain>
## Phase Boundary

Fix three MEDIUM-severity issues from PR #24 code review:
1. Add `/api/admin/vault` and `/api/admin/siem` to `LicenceExpiryGuard.EE_PREFIXES`
2. Replace absolute package imports with relative imports in `siem_router.py`
3. Add `test_service.shutdown()` inside a `try/finally` in the SIEM test-connection endpoint to prevent APScheduler job leaks

No new features. No UI changes. No schema changes. Pure correctness fixes in existing code.

</domain>

<decisions>
## Implementation Decisions

### No Discussion Needed
This phase has zero meaningful gray areas — all three fixes are mechanically precise with only one correct answer each. Decisions are fully determined by the codebase and the PR review findings.

### Fix 1 — EE_PREFIXES in LicenceExpiryGuard
- **D-01:** Add `"/api/admin/vault"` and `"/api/admin/siem"` to the `EE_PREFIXES` tuple in `LicenceExpiryGuard` class in `main.py` (lines 576-585).
- Both the Vault EE router (`vault_router.py`) and SIEM EE router (`siem_router.py`) mount at `/api/admin/vault` and `/api/admin/siem` respectively; without these prefixes the guard lets expired-licence users hit those EE endpoints.
- No other EE prefixes are missing — `foundry`, `audit`, `webhooks`, `triggers`, `auth-ext`, `smelter`, `executions`, `admin/bundles` are already present.

### Fix 2 — Relative Imports in siem_router.py
- **D-02:** Replace all absolute imports in `siem_router.py` with package-relative equivalents. File is at `agent_service/ee/routers/siem_router.py`.

  | Location | Absolute (wrong) | Relative (correct) |
  |----------|------------------|--------------------|
  | Line 85 (`update_config`) | `from ee.services.siem_service import SIEMService, set_active, get_siem_service` | `from ..services.siem_service import SIEMService, set_active, get_siem_service` |
  | Line 86 (`update_config`) | `from agent_service.services.scheduler_service import scheduler_service` | `from ...services.scheduler_service import scheduler_service` |
  | Line 112 (`test_connection`) | `from ee.services.siem_service import SIEMService, get_siem_service` | `from ..services.siem_service import SIEMService, get_siem_service` |
  | Line 113 (`test_connection`) | `from agent_service.db import AsyncSessionLocal` | `from ...db import AsyncSessionLocal` |
  | Line 114 (`test_connection`) | `from agent_service.services.scheduler_service import scheduler_service` | `from ...services.scheduler_service import scheduler_service` |
  | Line 182 (`get_status`) | `from ee.services.siem_service import get_siem_service` | `from ..services.siem_service import get_siem_service` |

- These are lazy inline imports (inside function bodies) used to break circular import chains — keep them inline, just fix the path style.

### Fix 3 — test_service.shutdown() in try/finally
- **D-03:** In the `test_connection` endpoint in `siem_router.py` (around line 104), wrap `startup()` and `status()` in a `try/finally` block that calls `await test_service.shutdown()` unconditionally.
- The shutdown must cover both `startup()` and `status()` — if startup partially registers APScheduler jobs and then status() raises, those jobs would leak without the finally clause.
- Pattern:
  ```python
  test_service = SIEMService(test_config, test_db, scheduler_service.scheduler)
  try:
      await test_service.startup()
      status = await test_service.status()
  finally:
      await test_service.shutdown()
  ```
- The vault test-connection endpoint (`vault_router.py`) does NOT have this issue — `VaultService` does not register APScheduler jobs on startup, so no equivalent fix is needed there.

### Claude's Discretion
- Exact line numbers may shift slightly during the fix; planner/executor should read the live file rather than relying on these line numbers.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Files to Modify
- `puppeteer/agent_service/main.py` — `LicenceExpiryGuard.EE_PREFIXES` (around line 576)
- `puppeteer/agent_service/ee/routers/siem_router.py` — absolute imports + missing try/finally

### Files for Reference Only (no changes needed)
- `puppeteer/agent_service/ee/routers/vault_router.py` — confirm vault test-connection does NOT need shutdown fix; confirm it already uses relative imports

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `LicenceExpiryGuard` at `main.py:566` — middleware class with `EE_PREFIXES` tuple (lowercase string matching); simply extend the tuple
- `SIEMService.shutdown()` already exists in `ee/services/siem_service.py` — no new method needed
- All other imports at the top of `siem_router.py` are already relative (`from ...db import ...`, `from ...deps import ...`) — the inline imports just need to match this existing style

### Established Patterns
- All other EE routers (`vault_router.py`, `siem_router.py` top-level) already use `...` relative import style for `agent_service` packages and `..` for sibling `ee/` packages
- Inline lazy imports are an established pattern in EE routers to avoid circular imports at module load time — maintain this pattern, just fix the paths

### Integration Points
- No new route registrations, no new DB columns, no new tests needed beyond confirming existing test suite still passes

</code_context>

<specifics>
## Specific Ideas

No specific implementation references beyond the PR #24 review findings captured above.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 169-pr-review-fix-ee-licence-guard-and-import-correctness*
*Context gathered: 2026-04-18*
