# Phase 172 Context: PR Review Fix — Critical CE/EE Table Isolation, Permission Cache Cleanup, and SIEM/Vault Hardening

**Source:** PR #24 code review (`/home/thomas/Development/mop_validation/reports/pr24_review.md`)
**Branch:** `phase-168-siem-audit-streaming-ee`
**Goal:** Fix all CRITICAL, HIGH, and MEDIUM findings before merging PR #24 to main.

---

## Phase Goal

Close the remaining CRITICAL/HIGH/MEDIUM findings from the PR #24 review. This phase is the gate before merging the SIEM/Vault work to main.

**Success criteria:**
1. `pytest puppeteer/` passes with zero failures (including `test_ce_smoke.py::test_ce_table_count`)
2. Ghost import removed from `main.py`
3. CE and EE SQLAlchemy models split onto separate `Base` / `EE_Base` declarative bases
4. Vault reauth loop capped at max attempts with escalation
5. SIEM `SENSITIVE_KEYS` expanded to cover `jwt`, `connection_string`, `tls_cert`, `webhook_secret`, and variants
6. SIEM hot-reload rolls back to old service if new startup fails
7. SIEM queue overflow increments `dropped_events` counter and surfaces admin alert

---

## Locked Decisions (from PR review)

All findings below are **confirmed bugs** — no ambiguity, no design choices. Execute directly.

### CRITICAL-01: Ghost Permission Cache Import (main.py:250-261)

**File:** `puppeteer/agent_service/main.py`, lines 250–261

**Problem:** Phase 171-04 removed `_perm_cache` from `deps.py` but `main.py` still has startup code that imports it. The code is wrapped in `try/except Exception` so it doesn't crash — but it's dead code and misleading.

```python
# This entire block is dead code — DELETE IT
try:
    async with AsyncSessionLocal() as _db:
        from sqlalchemy import text as _text
        _result = await _db.execute(_text("SELECT role, permission FROM role_permissions"))
        from .deps import _perm_cache  # ImportError caught silently
        for _role, _perm in _result.all():
            _perm_cache.setdefault(_role, set()).add(_perm)
        logger.info(f"Permission cache pre-warmed: {len(_perm_cache)} roles")
except Exception as _e:
    logger.debug(f"CE mode or no role_permissions table — cache pre-warm skipped: {_e}")
```

**Fix:** Delete the entire try/except block (12 lines). No replacement needed — `require_permission()` in `deps.py` already does per-request DB queries correctly.

---

### CRITICAL-02: CE/EE Table Isolation (db.py — all models on single Base)

**File:** `puppeteer/agent_service/db.py`

**Problem:** ALL SQLAlchemy models (CE and EE) extend the same `Base = DeclarativeBase()`. This causes `Base.metadata` to include EE table names, which breaks `test_ce_smoke.py::test_ce_table_count`.

**Failing test:**
```python
# puppeteer/agent_service/tests/test_ce_smoke.py
def test_ce_table_count():
    from agent_service.db import Base
    ce_tables = set(Base.metadata.tables.keys())
    ee_tables = {
        "blueprints", "puppet_templates", "capability_matrix", "image_boms",
        "package_index", "approved_os", "artifacts", "approved_ingredients",
        "audit_log", "user_signing_keys", "user_api_keys", "service_principals",
        "role_permissions", "webhooks", "triggers"
    }
    found_ee = ce_tables & ee_tables
    assert not found_ee, f"EE tables found in CE Base.metadata: {found_ee}"
    assert len(ce_tables) == 15, f"Expected 15 CE tables, got {len(ce_tables)}: {sorted(ce_tables)}"
```

**CE tables (15):** jobs, users, nodes, signatures, scheduled_jobs, node_stats, revoked_certs, alerts, configs, workflows, workflow_steps, workflow_runs, workflow_step_runs, workflow_triggers, siem_configs

Wait — `vault_configs` and `siem_configs` need to be checked: they are EE-only features but their DB models are currently in the CE `db.py`. The test lists `siem_configs` as NOT in ee_tables, which means it's expected to be in CE Base. Similarly `vault_configs` is not in ee_tables.

**Fix approach:**
1. Create `EE_Base = DeclarativeBase()` in `db.py` (or a new `puppeteer/agent_service/ee/db.py`)
2. Move these model classes from `Base` to `EE_Base`:
   - `Blueprint`, `PuppetTemplate`, `CapabilityMatrix`, `ApprovedOS`, `ApprovedIngredient`, `ImageBOM`, `PackageIndex`
   - `AuditLog`, `UserSigningKey`, `UserApiKey`, `ServicePrincipal`
   - `RolePermission`, `Webhook`, `Trigger`
   - `Artifact`
3. Update `init_db()` to call `EE_Base.metadata.create_all(engine)` only when EE is active
4. Update all imports of EE models throughout the codebase to use `EE_Base` (or just import the model classes directly — the base assignment change is transparent to importers of model classes)
5. Update Alembic env.py to include `EE_Base.metadata` in `target_metadata`

**Key constraint:** The 15 CE tables listed in the test must be EXACTLY the tables on `Base`. Do not add or remove from that set — the test is the spec.

**CE tables that stay on Base (15):**
`jobs`, `users`, `nodes`, `signatures`, `scheduled_jobs`, `node_stats`, `revoked_certs`, `alerts`, `configs`, `workflows`, `workflow_steps`, `workflow_runs`, `workflow_step_runs`, `workflow_triggers`, `siem_configs`

Wait, this needs careful checking. Let me re-examine: `vault_configs` and `siem_configs` — are these CE or EE? They are EE features but their configs might need to persist in CE mode (e.g., upgrading). The test says `siem_configs` is NOT in `ee_tables` (it's not in the set of 15 EE tables). So `siem_configs` stays on CE `Base`. Same analysis applies to `vault_configs` — it's also not listed in the ee_tables set in the test.

**Actual EE tables to move (per test's ee_tables set):**
`blueprints`, `puppet_templates`, `capability_matrix`, `image_boms`, `package_index`, `approved_os`, `artifacts`, `approved_ingredients`, `audit_log`, `user_signing_keys`, `user_api_keys`, `service_principals`, `role_permissions`, `webhooks`, `triggers`

**Important:** `vault_config` and `siem_config` stay on `Base` (CE tables). The test expects exactly 15 CE tables.

**Table name discrepancies to resolve before planning:**
- Test says `image_boms` but `db.py` has `__tablename__ = "image_bom"` — the model or test needs aligning
- Test says `webhooks` but `db.py` has `WorkflowWebhook.__tablename__ = "workflow_webhooks"` — these may be different tables or the test has a different name in mind
- Test says `artifacts` — no `artifacts` table visible in `db.py` grep; check EE plugin files
- Tables in `db.py` not in the test's `ee_tables` list: `ingredient_dependencies`, `curated_bundles`, `curated_bundle_items`, `script_analysis_requests`, `tokens`, `pings`, `signals`, `job_templates`, `scheduled_fire_log`, `execution_records`, `workflow_edges`, `workflow_parameters`, `workflow_webhooks` — these need categorization (CE or EE, and if EE must also move to EE_Base even though the test doesn't explicitly check them)

**Planner guidance:** Read `db.py` in full and `tests/test_ce_smoke.py` to determine the canonical list of 15 CE tables. The test `assert len(ce_tables) == 15` is the hard constraint — the planner must determine which 15 tables remain on `Base` and move all others (EE or transitional) to `EE_Base`.

**Alembic:** `puppeteer/agent_service/migrations/env.py` uses `target_metadata = Base.metadata`. After the split, update to include both: `target_metadata = [Base.metadata, EE_Base.metadata]` (Alembic supports a list).

---

### HIGH-01: Vault Reauth Unbounded Retry (vault_service.py:168-177)

**File:** `puppeteer/ee/services/vault_service.py`, lines 168–177

**Problem:** The degraded-state reauth loop retries every 10s indefinitely with no upper bound. A permanently broken Vault credential will spam logs forever and never escalate.

```python
# Current — no cap
if self._status == "degraded" and self.config is not None:
    try:
        await self._connect()
        self._status = "healthy"
        self._consecutive_renewal_failures = 0
    except Exception as e:
        self._consecutive_renewal_failures += 1
        logger.warning("Vault re-authentication attempt failed: %s", e)
        return
```

**Fix:** Add a `MAX_REAUTH_ATTEMPTS = 10` constant. After 10 consecutive failures, log at ERROR level, fire an admin alert (using the existing `Alert` DB model / alert mechanism used elsewhere in the codebase), and stop retrying until the config is explicitly updated.

---

### MEDIUM-01: SIEM Sensitive Field Masking — Missing Keys

**File:** `puppeteer/ee/services/siem_service.py`, lines 43–53

**Problem:** `SENSITIVE_KEYS` is missing several sensitive field names.

**Current:**
```python
SENSITIVE_KEYS = {
    "password", "secret", "token", "api_key", "secret_id", "role_id",
    "encryption_key", "access_token", "refresh_token",
}
```

**Fix — add these missing keys:**
```python
SENSITIVE_KEYS = {
    "password", "secret", "token", "api_key", "secret_id", "role_id",
    "encryption_key", "access_token", "refresh_token",
    "jwt", "jwt_token", "connection_string", "tls_cert", "client_cert",
    "webhook_auth", "webhook_secret", "private_key", "signing_key",
}
```

---

### MEDIUM-02: SIEM Hot-Reload Rollback Gap (siem_router.py:84-102)

**File:** `puppeteer/agent_service/ee/routers/siem_router.py`, lines 84–102

**Problem:** When PATCH /admin/siem/config hot-reloads the service, the sequence is: shutdown old → start new. If new startup fails, the old APScheduler job is gone and the new one was never created — SIEM is silently dead until restart.

```python
# Current — no rollback
try:
    old = get_siem_service()
    if old:
        await old.shutdown()
    if config.enabled:
        new_siem = SIEMService(config, db, scheduler_service.scheduler)
        await new_siem.startup()
        set_active(new_siem)
    else:
        set_active(None)
except Exception as e:
    logger.warning(f"Failed to reinitialize SIEM service: {e}")
```

**Fix:** Capture reference to old service before shutdown. If new startup raises, restore old service and re-call `old.startup()` (or keep old running by not calling shutdown until new is confirmed healthy).

```python
# Pattern to implement:
old = get_siem_service()
if config.enabled:
    new_siem = SIEMService(config, db, scheduler_service.scheduler)
    try:
        await new_siem.startup()
    except Exception as e:
        logger.error("SIEM hot-reload failed, keeping existing service: %s", e)
        raise HTTPException(status_code=500, detail=f"SIEM reinit failed: {e}")
    # Only shut down old AFTER new is confirmed healthy
    if old:
        await old.shutdown()
    set_active(new_siem)
else:
    if old:
        await old.shutdown()
    set_active(None)
```

---

### MEDIUM-03: SIEM Queue Overflow — Silent Event Drop

**File:** `puppeteer/ee/services/siem_service.py` — `enqueue()` method

**Problem:** When the queue is full (`maxsize=10_000`), events are silently dropped. There's a `dropped_events` counter in `status_detail()` but it's not being incremented on overflow, and no admin alert is fired.

**Fix:**
1. Increment `self._dropped_events` counter on `asyncio.QueueFull`
2. Every N dropped events (e.g., every 100), fire an admin alert using the existing alert mechanism
3. Surface `dropped_events` in the SIEM status endpoint response (it may already be there — verify)

---

## Out of Scope for Phase 172

- LOW findings from PR #24 (documentation comments) — acceptable as-is
- Any new features
- Alembic migration for existing EE tables (they already exist in production; the EE_Base split only affects `create_all` behavior for new installs and Alembic metadata tracking)

---

## Plan Structure

### Plan 01: Critical Fixes
1. Remove ghost perm-cache import block from `main.py:250-261`
2. Create `EE_Base` in `db.py`; move 15 EE model classes to it
3. Update `init_db()` to conditionally call `EE_Base.metadata.create_all()`
4. Update Alembic `env.py` to include `EE_Base.metadata`
5. Run `pytest puppeteer/` — verify `test_ce_table_count` passes, zero regressions

### Plan 02: SIEM/Vault Hardening
1. Cap Vault reauth at `MAX_REAUTH_ATTEMPTS = 10`; fire admin alert on exhaustion
2. Expand `SIEM_SENSITIVE_KEYS` with missing field names
3. Implement SIEM hot-reload rollback (start-new-before-shutdown-old pattern)
4. Increment `dropped_events` counter on queue overflow; fire periodic admin alert
5. Run `pytest puppeteer/` — full regression check
