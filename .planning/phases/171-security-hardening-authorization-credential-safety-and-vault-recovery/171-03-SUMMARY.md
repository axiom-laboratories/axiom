---
phase: 171-security-hardening-authorization-credential-safety-and-vault-recovery
plan: 03
subsystem: Vault Service
tags: [vault, exception-handling, auto-recovery, multi-provider, hardening]
dependencies:
  requires:
    - "171-CONTEXT.md (D-03, D-15 decisions)"
    - "Phase 170 Pattern Map (VaultConfigSnapshot pattern)"
  provides:
    - "Narrowed exception handling in Vault service"
    - "Auto re-authentication recovery mechanism"
    - "Multi-provider Vault config CRUD API"
  affects:
    - "puppeteer/ee/services/vault_service.py"
    - "puppeteer/agent_service/ee/routers/vault_router.py"
tech_stack:
  added:
    - "hvac.exceptions narrowed catch (hvac.exceptions.VaultError, InvalidRequest, Forbidden, InternalServerError + network errors)"
    - "VaultConfigSnapshot frozen dataclass (dataclasses.dataclass frozen=True)"
    - "Renewal timer auto re-auth logic in renew() method"
  patterns:
    - "EE-gated endpoints via Depends(require_ee())"
    - "Secret masking in API responses (****XXXX format)"
    - "Audit trail on all config mutations"
key_files:
  created:
    - "puppeteer/tests/test_vault_service_hardening.py (10 integration tests)"
  modified:
    - "puppeteer/ee/services/vault_service.py (exception narrowing, auto re-auth logic)"
    - "puppeteer/agent_service/ee/routers/vault_router.py (5 CRUD endpoints)"
    - "puppeteer/agent_service/models.py (VaultConfigCreateRequest model)"
metrics:
  duration_seconds: 182
  completed_date: "2026-04-19T16:01:52Z"
  tasks_completed: 5
  files_modified: 3
  files_created: 1
  tests_added: 10
---

# Phase 171 Plan 03: Vault Service Hardening — Exception Handling, Auto-Recovery, and Multi-Provider Management

## One-Liner
Vault service exception handling narrowed to hvac/network errors only; auto re-authentication recovery on timer tick when degraded; 5 new EE-gated CRUD endpoints for multi-provider config management with secret masking.

---

## Summary

**Plan 171-03** hardens the Vault service and completes the multi-provider API. Three critical gaps addressed:

1. **Broad exception catch masks programming errors** — Narrowed `resolve()` handler from `Exception` to specific `hvac.exceptions.*` + network errors (ConnectionError, TimeoutError, OSError). Programming errors like KeyError now propagate immediately for debugging instead of setting status=degraded.

2. **Transient failures stuck in degraded state** — Added auto re-authentication logic to `renew()` method. On renewal timer tick (60s), if status is degraded and config exists, attempt `_connect()`. Success restores status to healthy; failure increments counter. Transient network blips or token expiry now auto-recover without manual config update.

3. **Multi-provider API incomplete** — Implemented 5 new EE-gated endpoints:
   - `GET /admin/vault/configs` — list all configs (enabled/disabled)
   - `POST /admin/vault/config` — create new provider (starts disabled)
   - `PATCH /admin/vault/config/{id}` — update specific config by ID
   - `DELETE /admin/vault/config/{id}` — delete (prevents delete of enabled config with 409)
   - `POST /admin/vault/config/{id}/enable` — switch active provider (disables all others)

All endpoints mask secret_id in responses (****XXXX format), audit mutations, and reinitialize vault_service when needed.

---

## Tasks Completed

### Task 1: Narrow Exception Handler in resolve()
- Modified `puppeteer/ee/services/vault_service.py:resolve()` line 154
- Changed from broad `except Exception as e:` to:
  ```python
  except (hvac.exceptions.VaultError, hvac.exceptions.InvalidRequest,
          hvac.exceptions.Forbidden, hvac.exceptions.InternalServerError,
          ConnectionError, TimeoutError, OSError) as e:
  ```
- **Result:** Programming errors (KeyError, AttributeError, TypeError) now propagate immediately; only operational failures (network, Vault unreachable) set status=degraded.
- **Commit:** 3a3c11f6

### Task 2: Add Auto Re-Auth Recovery in renew()
- Modified `puppeteer/ee/services/vault_service.py:renew()` method
- Added auto re-authentication logic at method start:
  - Check if `_status == "degraded"` and `self.config is not None`
  - Attempt `await self._connect()`
  - On success: set `_status = "healthy"`, reset `_consecutive_renewal_failures = 0`
  - On failure: increment failure counter, return (don't attempt normal renewal)
- **Result:** Degraded status monitored on timer tick (APScheduler, every 60s); transient failures auto-recover without operator intervention.
- **Commit:** 3a3c11f6

### Task 3: Implement Multi-Provider CRUD Endpoints
- Modified `puppeteer/agent_service/ee/routers/vault_router.py`
- Added imports: `uuid`, `List[dict]`, `update` (from sqlalchemy)
- Implemented 5 endpoints (lines 211-413):
  1. **GET /admin/vault/configs** — returns list with id, provider_type, enabled, vault_address, masked secret_id
  2. **POST /admin/vault/config** — creates new config (disabled by default), encrypts secret_id via cipher_suite
  3. **PATCH /admin/vault/config/{id}** — updates specific config by ID (optional fields), reinitializes vault_service if enabled
  4. **DELETE /admin/vault/config/{id}** — deletes config (409 Conflict if enabled)
  5. **POST /admin/vault/config/{id}/enable** — enables this config, disables all others, reinitializes vault_service
- All endpoints use `Depends(require_ee())` for EE gating
- All audit mutations via `audit(db, current_user, ...)`
- **Commit:** a57ad34d

### Task 4: Add Request/Response Models
- Modified `puppeteer/agent_service/models.py`
- Added `VaultConfigCreateRequest` model (provider_type, vault_address, role_id, secret_id, namespace, mount_path)
- Updated imports in vault_router.py to include `VaultConfigCreateRequest`
- **Commit:** a57ad34d

### Task 5: Integration Tests for Vault Service Hardening
- Created `puppeteer/tests/test_vault_service_hardening.py` (233 lines, 10 tests)
- **Test Classes:**
  - `TestVaultConfigSnapshot` — verify immutability (FrozenInstanceError on field assignment), from_orm conversion
  - `TestVaultServiceRenewalFailures` — verify renewal_failures property exposes _consecutive_renewal_failures
  - `TestVaultServiceExceptionHandling` — verify narrowed handler catches hvac errors and ConnectionError, sets degraded status
  - `TestVaultAutoReauth` — verify auto re-auth on degraded, failure increment, success status restoration, disabled config no-op, normal renewal continues
- All tests pass (10/10 PASSED)
- **Commit:** 9e2969d5

---

## Deviations from Plan

None — plan executed exactly as specified.

---

## Architecture & Implementation Notes

### VaultConfigSnapshot Design
The frozen dataclass pattern prevents `DetachedInstanceError` when the ORM session that loaded the VaultConfig is closed or committed while the long-lived singleton vault_service still holds a reference. Snapshot captures values at construction time; all code uses snapshot fields instead of ORM properties.

### Exception Narrowing Rationale
Broad `except Exception` catch-all prevents debugging:
- **hvac.exceptions.***: Operational failures (Vault unreachable, auth failure) → set status=degraded
- **ConnectionError, TimeoutError, OSError**: Network-level issues → set status=degraded
- **Not caught**: KeyError (malformed response), AttributeError, TypeError → propagates immediately, visible during development

### Auto Re-Auth Recovery Flow
1. Renewal timer (APScheduler) calls `renew()` every 60 seconds (existing)
2. At method start, check degraded status
3. If degraded, attempt `_connect()` (full re-auth using encrypted secret_id)
4. Success: status→healthy, failure counter→0, continue to normal renewal
5. Failure: failure counter++, return early (don't attempt renewal)
6. Repeat on next timer tick (~60s later)

Transient token expiry (~1-2 min) auto-recovers without operator action.

### Multi-Provider Endpoint Design
- **One active provider at a time** — `enabled=True` on only one config
- **Enable endpoint atomicity** — disables all others in same transaction
- **Cannot delete enabled config** — returns 409 Conflict (prevents orphaning service)
- **Secret masking** — all responses show `****` + last 4 chars; plaintext never in logs
- **Audit trail** — all mutations logged via `audit()` for compliance

---

## Verification Checklist

- [x] VaultConfigSnapshot frozen dataclass exists
- [x] VaultService.__init__ creates snapshot from ORM object
- [x] renewal_failures property added (reads _consecutive_renewal_failures)
- [x] Exception handler narrowed: catches hvac.exceptions.* + network errors only
- [x] renew() checks degraded status and attempts _connect() on timer tick
- [x] Auto re-auth resets status to healthy and failure counter on success
- [x] 5 CRUD endpoints in vault_router.py (list, create, update, delete, enable)
- [x] All vault_router endpoints use Depends(require_ee())
- [x] Secret IDs masked in all API responses (****XXXX format)
- [x] Cannot delete enabled config (409 Conflict)
- [x] Enable endpoint disables all others and reinitializes vault_service
- [x] VaultConfigCreateRequest model added to models.py
- [x] Integration tests created and all passing (10/10)
- [x] Audit trail events logged for all config mutations
- [x] No new failures in existing test suite

---

## Known Stubs

None — all code paths implemented without placeholders or TODOs.

---

## Threat Surface Scan

No new security surface introduced outside the threat model. All changes within scope:
- **T-171-09**: Exception narrowing prevents debugging via catch-all → mitigated ✓
- **T-171-10**: Degraded state stuck without recovery → mitigated via auto re-auth ✓
- **T-171-11**: Secret exposure in responses → mitigated via masking ✓
- **T-171-12**: Disabled configs unreachable → mitigated via CRUD endpoints ✓

New endpoints are EE-gated (Depends(require_ee())); no public surface expansion.

---

## Self-Check

All created files exist and contain correct content:
- [x] `/home/thomas/Development/master_of_puppets/puppeteer/ee/services/vault_service.py` — narrowed exception handler, auto re-auth logic
- [x] `/home/thomas/Development/master_of_puppets/puppeteer/agent_service/ee/routers/vault_router.py` — 5 CRUD endpoints
- [x] `/home/thomas/Development/master_of_puppets/puppeteer/agent_service/models.py` — VaultConfigCreateRequest
- [x] `/home/thomas/Development/master_of_puppets/puppeteer/tests/test_vault_service_hardening.py` — 10 integration tests (all passing)

All commits exist and are reachable:
- [x] 3a3c11f6: feat(171-03): harden Vault exception handling and add auto re-auth recovery
- [x] a57ad34d: feat(171-03): implement multi-provider Vault CRUD endpoints
- [x] 9e2969d5: test(171-03): add integration tests for Vault service hardening
