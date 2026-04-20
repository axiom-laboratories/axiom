# Phase 171 Context — Security Hardening: Authorization, Credential Safety, and Vault Recovery

## Source
Deferred findings from Gemini peer review of PR #24. All items were known issues at the time of merge, deferred to this phase.

---

## Clear Fixes (no discussion required)

These are unambiguous — planners can implement without further input.

### Credential logging
- **File:** `puppeteer/agent_service/main.py:281`
- **Fix:** Remove the plaintext password argument from the log call.
  ```python
  # Before
  logger.warning("Admin bootstrapped with auto-generated password: %s", admin_password)
  # After
  logger.warning("Admin bootstrapped with auto-generated password (see secrets.env)")
  ```

### WebSocket resource leak
- **File:** `puppeteer/agent_service/routers/system_router.py:358-365`
- **Fix:** Wrap the event loop in try/finally so `ws_manager.disconnect(ws)` always runs, even on non-`WebSocketDisconnect` exceptions.
  ```python
  ws_manager._connections.append(ws)
  try:
      while True:
          data = await ws.receive_text()
          if data == "ping":
              await ws.send_text("pong")
  except WebSocketDisconnect:
      pass
  finally:
      ws_manager.disconnect(ws)
  ```

### Exception narrowing in vault_service.resolve()
- **File:** `puppeteer/ee/services/vault_service.py:154`
- **Current:** `except Exception as e:` catches everything including programming errors and re-raised VaultErrors.
- **Fix:** Catch `hvac.exceptions.VaultError` and `Exception` from the hvac network layer only. Avoid setting status=degraded for programming errors (e.g., KeyError on malformed response). Structure as:
  ```python
  except (hvac.exceptions.VaultError, hvac.exceptions.InvalidRequest,
          hvac.exceptions.Forbidden, hvac.exceptions.InternalServerError,
          ConnectionError, TimeoutError, OSError) as e:
      self._status = "degraded"
      self._last_error = str(e)
      raise VaultError(f"Secret resolution failed: {e}")
  ```

### YAML injection in compose generator
- **File:** `puppeteer/agent_service/main.py:669-700`
- **Parameters at risk:** `tags`, `mounts`, `token`, `execution_mode` — all interpolated directly into an f-string YAML block.
- **Fix:** Strip/reject newlines and control characters from all query params before interpolation. A newline in `tags` injects arbitrary YAML nodes. Either:
  1. Validate: reject any param containing `\n`, `\r`, `"`, or YAML structural chars (preferred for this endpoint — params have known shape)
  2. Or switch to `yaml.safe_dump` for the services block (more robust but changes output formatting)
- **Decision:** Use validation approach (option 1) — simpler, preserves exact output format the docs reference.

---

## Gray Area Decisions

### 1. Permission cache — remove cache entirely

**Decision:** Remove `_perm_cache` in `deps.py`. Always query `role_permissions` from DB on every request for non-admin users.

**Rationale:** Cache is correctly invalidated within a single process (`_invalidate_perm_cache` is called in `users_router.py:80,93`), but breaks silently in multi-worker deployments (each worker process has its own copy). The stack currently runs single-worker (`main.py:1035` — no `workers=N`), but this is fragile. Per-request DB query is one extra `SELECT` per request — negligible at current scale.

**Implementation:**
- Delete `_perm_cache: dict[str, set[str]] = {}`
- Delete `_invalidate_perm_cache()` function
- Remove the `if role not in _perm_cache` branch in `require_permission()`; always execute the DB query
- Remove all `_invalidate_perm_cache()` call sites (`users_router.py:80,93`)
- Update tests in `test_perm_cache.py` that test cache behavior

---

### 2. Vault stuck-degraded recovery — auto background retry

**Decision:** When Vault status is `degraded` and a client exists (i.e., we were previously healthy), attempt re-authentication on the existing renewal timer tick.

**Rationale:** A transient network error or token expiry sets `_status = "degraded"` permanently. The only current recovery is a config update (which calls `startup()` again). Auto retry on the renewal tick is lower friction and doesn't require a new API surface.

**Implementation in `vault_service.py`:**
- In `renew()`: if `self._status == "degraded"` and `self.config` is set (not disabled), attempt `await self._connect()` before the normal renew flow.
- If re-auth succeeds: set `_status = "healthy"`, reset `_consecutive_renewal_failures = 0`, log info.
- If re-auth fails: increment failure counter as normal, keep `_status = "degraded"`.
- This means the renewal background task (Phase 164/165 — called from lifespan) becomes the recovery mechanism with no new code needed in the router.

---

### 3. vault_router multi-provider management

**Decision:** Lean into the multi-provider design (D-15). One active provider at a time. Add CRUD to manage multiple configs.

**Rationale:** The `VaultConfig` table has a `provider_type` column and `enabled` flag designed for multiple providers. Currently only PATCH exists (targets the enabled row), so disabling a config makes it permanently unreachable. The schema supports the intent — the API just needs to catch up.

**New API surface (all EE-gated via `require_ee()`):**

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/admin/vault/configs` | List all configs (any enabled state). Returns `id`, `provider_type`, `enabled`, `vault_address`, masked `secret_id`. |
| `POST` | `/admin/vault/config` | Create a new provider config. Does not auto-enable. |
| `PATCH` | `/admin/vault/config/{id}` | Update a specific config by ID (replaces current PATCH that targets enabled-only). |
| `DELETE` | `/admin/vault/config/{id}` | Delete a config. Cannot delete the currently-enabled one (return 409). |
| `POST` | `/admin/vault/config/{id}/enable` | Enable this config, disable all others. Triggers `vault_service.startup()` with new config. |

**Keep existing endpoints:**
- `GET /admin/vault/config` — returns the currently active config (WHERE enabled=True). Keep as-is for backwards compat.
- `GET /admin/vault/status` — unchanged.
- `POST /admin/vault/test-connection` — unchanged.

**Startup behavior:** `main.py` startup already queries `WHERE enabled=True LIMIT 1` — no change needed.

---

### 4. Authorization permission gaps

**Decision:** Fix all three categories. Create new permission names where the existing set doesn't fit. Admin always bypasses all checks — no change needed there.

**Existing permissions (already seeded):**
`jobs:read`, `jobs:write`, `nodes:write`, `users:write`, `system:write`, `foundry:write`, `signatures:write`

**New permissions to add:**
- `nodes:read` — read-only node data (compose generation is read-only infra, enrollment diagnosis)
- `system:read` — read-only system state (alerts, signals listing, dispatch status)

**Mapping — admin_router.py:**

| Endpoint | Current | → New |
|----------|---------|-------|
| `POST /signatures` | `require_auth` | `require_permission("signatures:write")` |
| `GET /signatures` | `require_auth` | `require_permission("signatures:write")` ← write-gate (managing keys is privileged) |
| `DELETE /signatures/{id}` | `require_auth` | `require_permission("signatures:write")` |
| `GET /api/alerts` | `require_auth` | `require_permission("system:read")` |
| `POST /api/alerts/{id}/acknowledge` | `require_auth` | `require_permission("system:write")` |
| `POST /admin/generate-token` | `require_auth` | `require_permission("nodes:write")` ← critical: creating enrollment tokens |
| `POST /admin/upload-key` | `require_auth` | `require_permission("signatures:write")` |
| `POST /config/mounts` | `require_auth` | `require_permission("system:write")` |
| `POST /api/signals/{name}` | `require_auth` | `require_permission("jobs:write")` ← signals unblock jobs |
| `GET /api/signals` | `require_auth` | `require_permission("system:read")` |
| `DELETE /api/signals/{name}` | `require_auth` | `require_permission("jobs:write")` |

**Mapping — jobs_router.py:**

| Endpoint | Current | → New |
|----------|---------|-------|
| `GET /jobs/count` | `require_auth` | `require_permission("jobs:read")` |
| `POST /jobs` | `require_auth` | `require_permission("jobs:write")` ← critical: any user can run jobs |
| `PATCH /jobs/{guid}/cancel` | `require_auth` | `require_permission("jobs:write")` |
| `GET /jobs/{guid}/dispatch-diagnosis` | `require_auth` | `require_permission("jobs:read")` |
| `POST /jobs/bulk-dispatch-diagnosis` | `require_auth` | `require_permission("jobs:read")` |
| `POST /jobs/{guid}/retry` | `require_auth` | `require_permission("jobs:write")` |
| `POST /api/dispatch` | `require_auth` | `require_permission("jobs:write")` |
| `GET /api/dispatch/{guid}/status` | `require_auth` | `require_permission("jobs:read")` |
| `POST /jobs/definitions` | `require_auth` | `require_permission("jobs:write")` |
| `GET /jobs/definitions` | `require_auth` | `require_permission("jobs:read")` |
| `GET /api/jobs/dashboard/definitions` | `require_auth` | `require_permission("jobs:read")` |
| `DELETE /jobs/definitions/{id}` | `require_auth` | `require_permission("jobs:write")` |
| `PATCH /jobs/definitions/{id}/toggle` | `require_auth` | `require_permission("jobs:write")` |
| `GET /jobs/definitions/{id}` | `require_auth` | `require_permission("jobs:read")` |
| `PATCH /jobs/definitions/{id}` | `require_auth` | `require_permission("jobs:write")` |

**New permission seeding:** Add `nodes:read` and `system:read` to the startup permission seeder. Assign to roles:
- `operator`: gets `nodes:read`, `system:read`, `system:write` (already has `jobs:write`, `nodes:write`, etc.)
- `viewer`: gets `nodes:read`, `system:read`, `jobs:read` (read-only access to monitoring data)

---

## Plan Structure

The planner should structure execution as 4 plans matching the ROADMAP:

| Plan | Scope |
|------|-------|
| 01 | Authorization hardening — all admin_router and jobs_router permission upgrades + new permissions seeded |
| 02 | Credential safety — scrub log, YAML injection sanitization |
| 03 | Vault service hardening — exception narrowing in resolve(), auto re-auth in renew(), multi-provider vault_router CRUD |
| 04 | Deps hardening — remove perm cache, WebSocket try/finally |

Plan 04 is the most test-breaking (cache removal changes test setup in `test_perm_cache.py` and regression tests). Run it last.
