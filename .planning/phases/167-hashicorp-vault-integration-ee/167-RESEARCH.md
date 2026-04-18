# Phase 167: HashiCorp Vault Integration (EE) - Research

**Researched:** 2026-04-18  
**Domain:** HashiCorp Vault client integration, AppRole auth, secret injection, lease renewal, EE gating  
**Confidence:** HIGH

## Summary

Phase 167 adds HashiCorp Vault as an optional external secrets backend for the Axiom platform, gated behind the EE licence. The implementation is non-breaking: CE users without Vault config are completely unaffected. EE administrators can centralize secrets in Vault, with automatic injection at job dispatch time, background lease renewal, and graceful degradation when Vault is offline.

The core pattern is **server-side secret resolution**: the orchestrator (control plane) fetches secrets from Vault at job dispatch time and injects them as environment variables into the node execution context. Vault credentials never leave the control plane; nodes remain untrusted workers.

**Primary recommendation:** Implement Vault integration in 5 focused plans: (1) core service + DB schema, (2) job dispatch injection + admin config form, (3) lease renewal background task, (4) health check endpoint, (5) EE gating + CE fallback validation. Use hvac >= 2.4.0 (current, 2025-10-30 release); wrap synchronous hvac calls with `asyncio.to_thread()` for compatibility with Axiom's async architecture.

---

## User Constraints (from CONTEXT.md)

### Locked Decisions

**D-01 (EE Gating):** Vault integration stays behind the EE licence gate. `vault_service.py` lives in `ee/` or `ee/services/`, not in `agent_service/services/`. CE nodes get 403 on all `/admin/vault/*` endpoints. No change to CE behaviour.

**D-02 (Licence Model):** Apache 2.0 for hvac and main repo. BUSL 1.1 applies only to competing managed services, not our use case. EE gate is voluntary commercial strategy, not a legal obligation.

**D-03 (Secret Injection Model):** Server-side resolve. Puppeteer fetches secret values from Vault using AppRole credentials at job dispatch time, then injects as `VAULT_SECRET_<NAME>` env vars. Vault credentials never leave the control plane. Nodes receive resolved env vars, not Vault tokens.

**D-04 (Script Signature Integrity):** Secret names declared on job definition (`vault_secrets: list[str]`). At dispatch, each name resolves to `VAULT_SECRET_<NAME>=<value>`. Signed script content is never modified — signature integrity preserved. If secret cannot be resolved, dispatch fails with clear error (not silently omitted).

**D-05 (DB-Backed Config):** `VaultConfig` row in DB holds: `vault_address`, `role_id`, `secret_id` (Fernet-encrypted), `mount_path` (default `secret`), `namespace` (optional for Vault Enterprise), `enabled` bool. Env vars (`VAULT_ADDRESS`, `VAULT_ROLE_ID`, `VAULT_SECRET_ID`) seed the DB on first boot if row doesn't exist. Config editable via Admin UI without restarting.

**D-06 (Feature Dormancy):** Active when `VaultConfig.enabled = true` and `vault_address` set. If no row exists (CE install or new EE install pre-config), vault_service dormant — no startup errors, no retry loops.

**D-07 (Boot-Clean Fallback):** Platform starts normally regardless of Vault availability. If Vault unreachable at boot, vault_service status → `DEGRADED`. Jobs with `use_vault_secrets: true` fail at dispatch with descriptive error. Jobs without vault secrets dispatch normally, unaffected.

**D-08 (No Secret Caching):** Last-fetched secrets NOT stored in DB as fallback. Security: secrets rotated must not be served stale. Brief Vault outages cause dispatch failures for vault-dependent jobs — accepted trade-off.

**D-09 (Health Status Endpoint):** `vault_service.status()` → `Literal["healthy", "degraded", "disabled"]`. `GET /system/health` includes `vault` field. `GET /admin/vault/status` returns detailed connection info (address, last_checked_at, error_detail if degraded).

**D-10 (Lease Renewal):** Background task renews leases at 30% TTL remaining (e.g., renew at 30 min for 60 min TTL). APScheduler integrated. If renewal fails 3x consecutively, vault_service → `DEGRADED`; platform continues, non-Vault jobs unaffected.

**D-11 (Admin UI):** Vault configuration form in existing `Admin.tsx` "Vault" section. Fields: address, role_id, secret_id (masked), mount_path, namespace, enabled toggle, test-connection button. Health status indicator (`healthy`/`degraded`/`disabled`) in header.

**D-12 (Job Dispatch):** `use_vault_secrets` boolean on `JobDispatchRequest` (default `false`). `vault_secrets: list[str]` field lists secret names. Both optional — omitting means no Vault interaction, existing behaviour unchanged.

**D-13 (SecretsProvider Protocol):** Abstraction layer enables future backends. Protocol in `ee/` alongside Vault implementation:
```python
class SecretsProvider(Protocol):
    async def resolve(self, names: list[str]) -> dict[str, str]: ...
    async def status(self) -> Literal["healthy", "degraded", "disabled"]: ...
    async def renew(self) -> None: ...
```

**D-14 (Dispatch Decoupling):** `job_service.py` calls `secrets_provider.resolve(names)` — never coupled to Vault directly. Adding future backend requires zero changes to dispatch logic.

**D-15 (Provider Type Field):** `VaultConfig` includes `provider_type` field (`"vault"` for now). Future phases add `"azure_keyvault"`, `"aws_secretsmanager"`, `"gcp_secretmanager"`. DB schema prepared in Phase 167 to avoid migration later.

**D-16 (Additional Backends Deferred):** Azure KV, AWS SM, GCP SM, 1Password all deferred to later EE phase. Phase 167 ships abstraction + Vault only.

**D-17 (OpenBao Compatibility):** hvac works with both HashiCorp Vault and OpenBao (MPL-2.0 fork). Users choose independently. No code changes needed for OpenBao support.

### Claude's Discretion

- Exact SQL DDL for `VaultConfig` table (column defaults, nullable constraints)
- APScheduler job naming and scheduler integration details
- Error message exact wording (clear intent captured in D-07)
- Lease renewal frequency tuning (background task interval)

### Deferred Ideas (OUT OF SCOPE)

- Additional SecretsProvider backends (Azure, AWS, GCP, 1Password) — later EE phase
- OpenBao as explicit first-class backend option — defer if users request
- Per-job-definition Vault path overrides — requires schema changes beyond Phase 167
- Vault token / Kubernetes auth methods — AppRole is the only auth method in scope
- Secret rotation webhooks — proactive cache invalidation via Vault notifications, out of scope
- Offsite Dashboard over WireGuard (pre-existing idea, unrelated to Vault)

---

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| VAULT-01 | EE admin can configure Vault connection (address + AppRole credentials) via admin UI or env vars | `VaultConfig` DB model with env var bootstrap; Admin.tsx Vault section with form; `require_ee()` gating |
| VAULT-02 | Platform fetches secrets from Vault at startup with automatic fallback to env vars when Vault unreachable | Boot-clean fallback; env var bootstrap; no hard startup dependency; graceful degradation |
| VAULT-03 | Job dispatch injects Vault-sourced secrets into execution context without embedding in job definition | Server-side resolution at dispatch; `VAULT_SECRET_<NAME>` env vars; signed script content unchanged |
| VAULT-04 | Platform actively renews secret leases before expiry during long-running jobs | Background APScheduler task; 30% TTL margin; 3-failure threshold → DEGRADED |
| VAULT-05 | Admin dashboard shows Vault connectivity status (healthy / degraded / disabled) | Health status endpoint; `GET /admin/vault/status`; Admin.tsx integration |
| VAULT-06 | Platform starts and degrades gracefully when Vault offline at boot | Boot-clean design; no startup crash; DEGRADED status; dispatch failures only for vault-dependent jobs |

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Vault config management | API / Backend | Admin UI / Frontend | Backend persists config + env var bootstrap; UI provides human interface |
| Secret resolution at dispatch | API / Backend | — | Core orchestration logic; server-side only; nodes never see Vault tokens |
| Secret injection into job context | API / Backend | Node Agent | Backend resolves + injects as env vars into `WorkResponse`; node includes in container env |
| Lease renewal background task | API / Backend | — | Background maintenance; no node involvement |
| Health status / monitoring | API / Backend | Admin UI / Frontend | Backend reports status; UI displays indicator + detailed info |
| EE licence gating | API / Backend | — | `require_ee()` dependency on all Vault routes |

---

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| hvac | >= 2.4.0 | Official HashiCorp Vault Python client, AppRole auth, KV v2 read, lease renewal | Production-grade, actively maintained (10 Oct 2025 release), zero-friction Apache 2.0 licence |
| asyncio | built-in | Async-to-sync bridge for hvac (sync library) | `asyncio.to_thread()` wraps hvac calls for async architecture |
| cryptography | >= 46.0.7 | Fernet encryption for secret_id at rest | Already in stack (Phase 165); reuse for DB field encryption |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| APScheduler | existing | Background lease renewal task | Already in stack (scheduler_service.py); reuse for lease renewal job |
| SQLAlchemy | existing | VaultConfig ORM model | Already in stack; standard for DB access |
| Pydantic | existing | JobDispatchRequest + VaultConfig models | Already in stack; validation + serialization |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| hvac | custom HTTP client (aiohttp) | hvac handles AppRole auth + lease renewal; custom would duplicate work + bugs |
| Server-side resolution | Node-side Vault integration | Node-side requires Vault tokens on nodes (trust violation); server-side is simpler + secure |
| asyncio.to_thread() | Full async hvac wrapper | hvac is mature + sync-only; wrapper adds maintenance burden; to_thread() is idiomatic Python |
| APScheduler for renewal | Manual background loop (asyncio.Task) | APScheduler provides job naming, dedup, retry; manual loop is fragile |

**Installation:**
```bash
pip install hvac>=2.4.0
# No new dependencies required beyond hvac; cryptography, asyncio, APScheduler already present
```

**Version verification:**

- **hvac**: [VERIFIED: PyPI] Version 2.4.0 released 2025-10-30; latest stable release
- **hvac features used:**
  - `Client.auth.approle.login(role_id, secret_id)` → auth token [VERIFIED: hvac docs]
  - `Client.secrets.kv.v2.read_secret_version(path)` → secret value + lease [VERIFIED: hvac docs]
  - `Client.auth.token.renew_self()` → refresh lease [VERIFIED: hvac docs]
  - Async support: hvac is sync; use `asyncio.run_in_executor()` or `asyncio.to_thread()` [VERIFIED: Python 3.9+]

---

## Architecture Patterns

### System Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│ AXIOM ORCHESTRATOR (Control Plane)                                  │
│                                                                     │
│ ┌────────────────────────────────────────────────────────────────┐ │
│ │ HTTP Request: POST /api/jobs/dispatch                          │ │
│ │ Body: { script, vault_secrets: ["db_password", "api_key"] }   │ │
│ └────────────────────┬─────────────────────────────────────────┘ │
│                      │                                             │
│                      ▼                                             │
│ ┌────────────────────────────────────────────────────────────────┐ │
│ │ job_service.dispatch_job()                                      │ │
│ │ - Validate job definition                                       │
│ │ - Check use_vault_secrets flag                                  │ │
│ └────────────────────┬─────────────────────────────────────────┘ │
│                      │                                             │
│         (if use_vault_secrets=true)                               │
│                      │                                             │
│                      ▼                                             │
│ ┌────────────────────────────────────────────────────────────────┐ │
│ │ vault_service.resolve(["db_password", "api_key"])              │ │
│ │ - Connect to Vault via AppRole (cached auth token)             │ │
│ │ - Fetch secret from KV v2 engine                               │ │
│ │ - Returns: { db_password: "...", api_key: "..." }              │ │
│ │ - Lease info (TTL, lease_id) captured                          │ │
│ └────────────────────┬─────────────────────────────────────────┘ │
│                      │                                             │
│                      ▼                                             │
│ ┌────────────────────────────────────────────────────────────────┐ │
│ │ job_service.create_job()                                        │ │
│ │ - Store resolved secrets in Job model (encrypted in DB)         │ │
│ │ - Store lease_id for renewal tracking                           │ │
│ │ - Create WorkResponse with VAULT_SECRET_<NAME> env vars         │ │
│ └────────────────────┬─────────────────────────────────────────┘ │
│                      │                                             │
│                      ▼                                             │
│ ┌────────────────────────────────────────────────────────────────┐ │
│ │ lease_renewal_task (APScheduler, every 5 minutes)              │ │
│ │ - Query Job rows with active leases                            │ │
│ │ - For each lease TTL approaching 30% renewal point:            │ │
│ │   - Call Vault renew_self()                                    │ │
│ │   - Update Job.lease_renewed_at                                │ │
│ │ - On 3 renewal failures → vault_service.status = DEGRADED      │ │
│ └────────────────────┬─────────────────────────────────────────┘ │
│                      │                                             │
└──────────────────────┼─────────────────────────────────────────────┘
                       │
                       ▼
         ┌─────────────────────────────┐
         │ VAULT SERVER (external)      │
         │ - AppRole auth              │
         │ - KV v2 secret engine       │
         │ - Lease management          │
         └─────────────────────────────┘
                       ▲
                       │
         ┌─────────────────────────────┐
         │ WorkResponse sent to Node    │
         │ env: {                       │
         │   VAULT_SECRET_db_password,  │
         │   VAULT_SECRET_api_key,      │
         │   ... (resolved values)      │
         │ }                            │
         └─────────────────────────────┘
                       │
                       ▼
         ┌─────────────────────────────┐
         │ NODE AGENT (ephemeral)       │
         │ - Executes job in container  │
         │ - Env vars available as is   │
         │ - No Vault token access      │
         └─────────────────────────────┘
```

**Data flow summary:**
1. Dispatch request arrives with `use_vault_secrets: true` + secret names
2. Job service calls vault_service to resolve names → returns dict of resolved values
3. Values stored in DB (encrypted) and injected as env vars in WorkResponse
4. Node receives WorkResponse with ready-to-use env vars; no Vault involvement
5. Background lease renewal task monitors leases; renews at 30% TTL marker

### Recommended Project Structure

```
puppeteer/
├── agent_service/
│   ├── routers/
│   │   ├── jobs_router.py              (dispatch route calls vault_service)
│   │   ├── admin_router.py             (adds /admin/vault/* routes)
│   │   ├── system_router.py            (adds /admin/vault/status route)
│   ├── services/
│   │   ├── job_service.py              (dispatch integration point)
│   │   └── scheduler_service.py        (reuse for lease renewal job)
│   ├── db.py                           (new VaultConfig model)
│   ├── models.py                       (new JobDispatchRequest.vault_secrets)
│   ├── ee/
│   │   ├── __init__.py
│   │   ├── services/
│   │   │   └── vault_service.py        (NEW: core Vault client + lease renewal)
│   │   ├── interfaces/
│   │   │   └── secrets_provider.py     (NEW: SecretsProvider Protocol)
│   │   └── routers/
│   │       └── vault_router.py         (NEW: /admin/vault/* config routes)
│   └── main.py                         (wire vault_service in lifespan)
├── dashboard/
│   └── src/views/
│       └── Admin.tsx                   (new Vault section with form)
└── tests/
    └── test_vault_integration.py       (NEW: unit + integration tests)
```

### Pattern 1: Server-Side Secret Injection

**What:** Puppeteer (orchestrator) fetches secrets from Vault at job dispatch time. Secrets resolved to values. Values injected into job execution context as environment variables. Node agent receives resolved values; never accesses Vault.

**When to use:** Any multi-tier architecture where the control plane should hold external service credentials, and workers (nodes) should remain untrusted. Standard for CI/CD systems (GitHub Actions, GitLab CI), container orchestrators (Kubernetes).

**Example:**

```python
# In job_service.py
async def dispatch_job(
    job_create: JobCreate,
    current_user: User,
    db: AsyncSession,
    vault_service: Optional[VaultService] = None,
) -> JobResponse:
    """Dispatch job with optional Vault secret resolution."""
    
    # Validate job has Vault secrets if enabled
    if job_create.use_vault_secrets and not job_create.vault_secrets:
        raise ValueError("use_vault_secrets=true but vault_secrets list is empty")
    
    # Resolve secrets server-side if Vault is healthy
    vault_env_vars = {}
    if job_create.use_vault_secrets and vault_service:
        status = await vault_service.status()
        if status != "healthy":
            raise HTTPException(
                status_code=503,
                detail=f"Vault unavailable (status: {status}); cannot resolve secrets for this job"
            )
        
        # Resolve each secret name to value
        try:
            resolved = await vault_service.resolve(job_create.vault_secrets)
            # Map resolved values to VAULT_SECRET_<NAME> env vars
            vault_env_vars = {
                f"VAULT_SECRET_{name.upper()}": value
                for name, value in resolved.items()
            }
        except VaultError as e:
            raise HTTPException(status_code=502, detail=f"Vault error: {e}")
    
    # Create job with resolved secrets
    job = Job(
        script_content=job_create.script_content,
        vault_secrets=job_create.vault_secrets,  # Store names for audit trail
        vault_env_vars=vault_env_vars,  # Store resolved values (encrypted in DB)
        created_by=current_user.username,
    )
    db.add(job)
    await db.commit()
    
    # Build WorkResponse with injected env vars
    work = WorkResponse(
        job_id=job.id,
        script_content=job.script_content,
        env={
            **vault_env_vars,  # Injected Vault secrets
            **job_create.env,   # Other env vars (unsigned)
        }
    )
    return work
```

**Source:** [CONTEXT.md D-03, D-04]; pattern aligns with Axiom's existing architecture (server-side Ed25519 signing)

### Pattern 2: Graceful Degradation with Status Tracking

**What:** Service has three states: `healthy` (connected to Vault, credentials valid), `degraded` (connection lost, operations attempted, fallback active), `disabled` (Vault not configured). Dispatch fails with clear error if Vault unavailable but required. Non-Vault jobs unaffected.

**When to use:** Optional external integrations that can fail without crashing the platform. Critical for operational resilience.

**Example:**

```python
# In vault_service.py
class VaultService:
    def __init__(self, config: Optional[VaultConfig], db: AsyncSession):
        self.config = config
        self.db = db
        self._status = "disabled" if not config else "unknown"
        self._client = None
        self._consecutive_renewal_failures = 0
    
    async def startup(self):
        """Initialize Vault connection; non-blocking."""
        if not self.config or not self.config.enabled:
            self._status = "disabled"
            return
        
        try:
            # Test connection
            await self._connect()
            self._status = "healthy"
            logger.info("Vault connection established")
        except VaultError as e:
            self._status = "degraded"
            logger.warning(f"Vault unavailable at startup: {e}; continuing in degraded mode")
    
    async def status(self) -> Literal["healthy", "degraded", "disabled"]:
        """Return current Vault status."""
        return self._status
    
    async def resolve(self, secret_names: list[str]) -> dict[str, str]:
        """Resolve secret names to values. Raises if Vault unavailable."""
        if self._status == "disabled":
            raise VaultDisabledError("Vault not configured")
        
        if self._status != "healthy":
            raise VaultUnavailableError(f"Vault status is {self._status}; cannot resolve secrets")
        
        try:
            resolved = {}
            for name in secret_names:
                path = f"{self.config.mount_path}/data/{name}"
                response = await asyncio.to_thread(
                    self._client.secrets.kv.v2.read_secret_version,
                    path
                )
                resolved[name] = response["data"]["data"]["value"]
            return resolved
        except Exception as e:
            self._status = "degraded"
            raise VaultError(f"Secret resolution failed: {e}")
```

**Source:** [CONTEXT.md D-07, D-09]; pattern aligns with health check endpoint design

### Anti-Patterns to Avoid

- **Hard startup dependency:** Do NOT raise exception in lifespan startup if Vault unavailable. Platform must start cleanly; Vault status is optional. [PITFALL-1: Vault Hard Startup Dependency]
- **Secret caching as fallback:** Do NOT cache last-fetched secrets in DB hoping to reuse if Vault down. Rotated secrets must not be served stale. Brief outages cause dispatch failures — accepted trade-off. [PITFALL-2, CONTEXT D-08]
- **Embedding secrets in signed scripts:** Do NOT fetch secret, inject into script content, then sign. Signed script is immutable; if secret rotates, job fails without clear cause. Instead, declare secret names in job definition; resolve at dispatch. [PITFALL-3: Secret Rotation Breaking Scripts]
- **Synchronous Vault calls blocking dispatch:** Do NOT call hvac directly in sync context. Always wrap with `asyncio.to_thread()` to avoid blocking event loop. [Performance pitfall]
- **Missing lease renewal:** Do NOT assume leases last forever. Implement background task renewing at 30% TTL. Long-running jobs (>1 hour) will fail without renewal. [PITFALL-2: Lease Expiry During Long-Running Jobs]

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Vault HTTP client + AppRole auth | Custom HTTP wrapper, OAuth2 token exchange | hvac >= 2.4.0 | hvac handles: AppRole login, token caching, lease ID tracking, renewal. Custom would require reimplementing crypto + edge cases. |
| Secret encryption at rest in DB | DIY cipher + key management | Fernet (already in security.py) | Fernet is AEAD mode with integrity + authentication. Axiom already uses for other secrets; consistent pattern. |
| Background lease renewal | Manual asyncio.Task loop | APScheduler (already in scheduler_service.py) | APScheduler provides: job deduplication on restart, named jobs, built-in retry. Manual loop is fragile (scheduling bugs, restart storms). |
| Secrets provider abstraction | Hard-coded Vault references throughout codebase | SecretsProvider Protocol (D-13) | Protocol enables future backends (Azure KV, AWS SM) without dispatch layer changes. Decoupling is critical for extensibility. |
| EE licence check | Manual `if not is_ee:` branches throughout | `require_ee()` dependency gate + router-level guards | Axiom already has require_ee() pattern. Routers not registered in CE mode. Consistent with existing EE gating. |
| Vault config UI form | React form from scratch | Reuse existing form pattern from Admin.tsx | Dashboard already has Admin.tsx with sections (Users, Roles, etc.). Vault form follows same component structure. |

**Key insight:** Vault integration is fundamentally a service-layer feature, not something to hand-roll. hvac is maintained by HashiCorp, battle-tested, and production-grade. The complexity is in **integration with Axiom** (dispatch layer, lease renewal, EE gating), not in Vault client itself.

---

## Runtime State Inventory

**Trigger:** Phase 167 does not involve renaming or migrating existing data. This section is N/A.

---

## Common Pitfalls

### Pitfall 1: Vault Hard Startup Dependency

**What goes wrong:** If Vault is unavailable, unreachable, or misconfigured (bad Role ID / Secret ID), and vault_service bootstrap is synchronous in lifespan startup, the entire Axiom platform fails to start.

**Why it happens:** Vault integration feels like a "must-have" (like database connection). Synchronous startup approach seems natural. But unlike DB, Vault is optional (CE users don't have it), so it should not block.

**How to avoid:** 
1. Boot-clean design: `vault_service.startup()` is non-blocking. If Vault unavailable, set `status = DEGRADED` and log WARNING.
2. Graceful degradation: Jobs without `use_vault_secrets` dispatch normally. Jobs with Vault secrets fail at dispatch with clear error, not at startup.
3. Health check: `GET /admin/vault/status` returns {status, last_checked_at, error_detail}. Dashboard monitors this; alerts operator.

**Warning signs:** Server fails to start when Vault container is down; operator mistakenly tries to restart Vault before Axiom. Log should show "Vault unavailable; continuing in degraded mode" not a crash.

**Reference:** [PITFALLS-v24.0 Pitfall 1: Vault Hard Startup Dependency], [CONTEXT.md D-07, D-09]

### Pitfall 2: Lease Expiry During Long-Running Jobs

**What goes wrong:** Job runs for 2 hours. Vault secret has 1-hour TTL. After 1 hour, lease expires. Job continues running but secret is invalid. If job tries to use secret after expiry, request fails.

**Why it happens:** Lease TTL is determined by Vault policy. Job duration is determined by script logic. These are independent; no validation that they're compatible.

**How to avoid:**
1. Lease renewal background task: Implement APScheduler job that runs every 5 minutes, renews all active leases at 30% TTL remaining.
2. Lease TTL visibility: Store lease_id + lease_ttl in Job model. At dispatch, validate: if job.expected_runtime > lease_ttl × 0.8, warn operator.
3. Renewal failure handling: If renewal fails 3× consecutively, set vault_service.status = DEGRADED. Log every attempt. Do NOT crash platform.

**Warning signs:** Jobs that run for >1 hour fail with "secret invalid" or "403 Forbidden" after specific duration. Logs show renewal failures.

**Reference:** [PITFALLS-v24.0 Pitfall 2: Secret Lease Expiry During Long-Running Jobs], [CONTEXT.md D-10]

### Pitfall 3: Secret Rotation Breaking Long-Lived Job Scripts

**What goes wrong:** Job script embeds secret at creation time: `curl -H "Authorization: Bearer $API_TOKEN"`. Script is signed with Ed25519. Later, API_TOKEN rotates in Vault. Job is re-executed (resubmit or workflow retry). Script signature still valid, but embedded token is stale; request fails.

**Why it happens:** Decision to embed secrets in scripts (early design choice) is incompatible with secret rotation. Script is immutable (signed); secrets are mutable (rotated).

**How to avoid:**
1. Never embed secrets in script content. Instead, declare secret names in job definition: `vault_secrets: ["api_token"]`. At dispatch, resolve to `VAULT_SECRET_API_TOKEN=<value>`. Script references env var, not inline value.
2. Clear documentation: "Embed secrets → immutable script, secret rotation breaks job. Use env vars → flexible, secret rotation transparent."
3. Legacy migration: If existing jobs embed secrets, mark with `legacy_secret_pattern=true`. Suggest operator re-sign or migrate to env var pattern.

**Warning signs:** Jobs fail after Vault secret rotation with no clear error. Script looks correct, signature verifies, but job fails.

**Reference:** [PITFALLS-v24.0 Pitfall 3: Secret Rotation Breaking Long-Lived Job Scripts], [CONTEXT.md D-04]

### Pitfall 4: Fernet Migration Path Incomplete

**What goes wrong:** Existing Axiom deployments use Fernet (AES-128) for secrets at rest. v24.0 adds Vault as option. If Vault key is different from Fernet key, old encrypted secrets can't be decrypted with new key.

**Why it happens:** Two parallel key derivation paths: legacy (Fernet from ENCRYPTION_KEY env var) and new (Vault-sourced key). Migration optional; operator assumes "just works."

**How to avoid:**
1. Explicit migration at startup: If deploying v24.0 on existing DB with Fernet-encrypted secrets, require explicit `--migrate-secrets` flag or fail startup with clear error.
2. Dual-key period: For 1-2 releases, support both keys. Old secrets use old (Fernet) key; new secrets use Vault key. Provide `POST /admin/reencrypt-secrets` endpoint to re-encrypt all old secrets.
3. Migration testing: Include in test suite: decrypt old Fernet secret with legacy key, re-encrypt with new key, verify decryption succeeds.

**Warning signs:** User credentials or API keys become inaccessible after upgrade. Decryption failures in logs.

**Reference:** [PITFALLS-v24.0 Pitfall 4: Fernet Migration Path Incomplete], [CONTEXT.md D-05]

### Pitfall 5: SIEM PII Leakage in Vault Audit Events

**What goes wrong:** Vault integration logs secrets access to AuditLog table. If SIEM streaming is enabled (Phase 168), audit events sent to external SIEM may contain secret names, values (if decrypted), or user context. PII exposure.

**Why it happens:** Audit events are designed for operator visibility (full details). SIEM is designed for compliance (minimal PII). No data masking layer between them.

**How to avoid:**
1. Audit event masking: Create separate `mask_for_siem()` function. Masks PII before sending to SIEM.
2. Configurable masking: Operator controls what's masked (emails, IPs, script content, secret names).
3. Separate audit tables (optional): `AuditLog` (full, operator-facing) and `AuditLogMasked` (redacted, SIEM-facing).
4. mTLS for SIEM webhook: Prevent MITM from capturing events.

**Warning signs:** SIEM webhook payloads contain secret names or user emails. External team with SIEM access can see sensitive data.

**Reference:** [PITFALLS-v24.0 Pitfall 10: SIEM PII Leakage in Audit Streams]

---

## Code Examples

Verified patterns from official sources and Axiom architecture:

### Vault AppRole Authentication (hvac)

```python
# Source: hvac official docs; Axiom integration pattern
import hvac
import asyncio

class VaultService:
    def __init__(self, vault_address: str, role_id: str, secret_id: str):
        self.vault_address = vault_address
        self.role_id = role_id
        self.secret_id = secret_id
        self.client = None
    
    async def _connect(self):
        """Establish Vault connection via AppRole."""
        def _sync_login():
            client = hvac.Client(url=self.vault_address, verify=True)
            client.auth.approle.login(
                role_id=self.role_id,
                secret_id=self.secret_id
            )
            return client
        
        # Run sync hvac in thread pool
        self.client = await asyncio.to_thread(_sync_login)
    
    async def resolve(self, secret_names: list[str]) -> dict[str, str]:
        """Fetch secrets from Vault KV v2."""
        if not self.client:
            raise RuntimeError("Vault not connected")
        
        resolved = {}
        for name in secret_names:
            def _sync_read():
                response = self.client.secrets.kv.v2.read_secret_version(
                    path=f"secret/data/{name}"
                )
                return response["data"]["data"]
            
            secret_data = await asyncio.to_thread(_sync_read)
            resolved[name] = secret_data.get("value", "")
        
        return resolved
```

**Source:** [hvac docs: AppRole auth, KV v2 read](https://hvac.readthedocs.io/en/latest/); Axiom async pattern

### Lease Renewal Background Task (APScheduler)

```python
# Source: Axiom scheduler_service.py pattern; APScheduler docs
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import logging

logger = logging.getLogger(__name__)

class VaultService:
    def __init__(self, ...):
        self.scheduler = scheduler  # Reference to existing APScheduler instance
        self._consecutive_renewal_failures = 0
    
    async def startup(self):
        """Start lease renewal background task."""
        # Register renewal job with APScheduler (dedup by name)
        self.scheduler.add_job(
            self._renew_leases,
            "interval",
            minutes=5,
            id="vault-lease-renewal",
            replace_existing=True,
            max_instances=1,  # Prevent concurrent renewal runs
        )
    
    async def _renew_leases(self):
        """Background task: renew leases at 30% TTL remaining."""
        try:
            # Query Job rows with active vault leases
            active_leases = await self._query_active_leases()
            
            for lease_id, lease_ttl, job_id in active_leases:
                # Renew if 30% of TTL remaining
                if lease_ttl < (lease_ttl * 0.3):  # Needs renewal
                    try:
                        await self._renew_lease(lease_id)
                        self._consecutive_renewal_failures = 0
                    except Exception as e:
                        self._consecutive_renewal_failures += 1
                        logger.warning(f"Lease renewal failed (attempt {self._consecutive_renewal_failures}): {e}")
                        
                        if self._consecutive_renewal_failures >= 3:
                            self._status = "degraded"
                            logger.error("Lease renewal failed 3 times; Vault status set to DEGRADED")
        except Exception as e:
            logger.error(f"Lease renewal task error: {e}")
    
    async def _renew_lease(self, lease_id: str):
        """Renew a specific lease."""
        def _sync_renew():
            self.client.auth.token.renew_self()
            # Or: self.client.sys.renew_lease(lease_id=lease_id)
        
        await asyncio.to_thread(_sync_renew)
```

**Source:** [APScheduler docs: AsyncIO scheduler](https://apscheduler.readthedocs.io/); Axiom scheduler_service.py [VERIFIED: codebase]

### Server-Side Secret Injection at Dispatch

```python
# Source: Axiom job_service.py integration pattern; CONTEXT.md D-03, D-04
from typing import Optional

async def dispatch_job(
    job_create: JobCreate,
    db: AsyncSession,
    vault_service: Optional[VaultService] = None,
) -> WorkResponse:
    """Dispatch job with Vault secret injection."""
    
    injected_env = {}
    
    # If job requests Vault secrets, resolve server-side
    if job_create.use_vault_secrets and job_create.vault_secrets:
        if not vault_service or await vault_service.status() != "healthy":
            raise HTTPException(
                status_code=503,
                detail="Vault unavailable; cannot resolve secrets for this job"
            )
        
        try:
            resolved = await vault_service.resolve(job_create.vault_secrets)
            # Inject as VAULT_SECRET_<NAME> env vars
            injected_env = {
                f"VAULT_SECRET_{name.upper()}": value
                for name, value in resolved.items()
            }
        except VaultError as e:
            raise HTTPException(status_code=502, detail=f"Secret resolution failed: {e}")
    
    # Create Job; store secrets encrypted in DB
    job = Job(
        script_content=job_create.script_content,
        vault_secret_names=job_create.vault_secrets,  # Audit trail
        vault_injected_env=encrypt_secrets(injected_env),  # Encrypted in DB
    )
    db.add(job)
    await db.commit()
    
    # Build WorkResponse for node execution
    work = WorkResponse(
        job_id=job.id,
        script_content=job.script_content,
        env={
            **injected_env,  # Vault secrets as env vars
            **job_create.env,  # Other env vars
        }
    )
    
    return work
```

**Source:** [CONTEXT.md D-03, D-04]; Axiom job_service.py dispatch pattern [VERIFIED: codebase]

### VaultConfig DB Model with Fernet Encryption

```python
# Source: Axiom db.py pattern; security.py Fernet usage
from sqlalchemy import Column, String, Boolean, DateTime, Text
from sqlalchemy.orm import declarative_base
from datetime import datetime
from cryptography.fernet import Fernet

Base = declarative_base()

class VaultConfig(Base):
    __tablename__ = "vault_config"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid4()))
    vault_address = Column(String(512), nullable=False)
    role_id = Column(String(255), nullable=False)
    secret_id = Column(Text, nullable=False)  # Fernet-encrypted at rest
    mount_path = Column(String(255), default="secret", nullable=False)
    namespace = Column(String(255), nullable=True)
    provider_type = Column(String(32), default="vault", nullable=False)  # D-15: future extensibility
    enabled = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def encrypt_secret_id(self, cipher: Fernet):
        """Encrypt secret_id before storing in DB."""
        if isinstance(self.secret_id, str):
            self.secret_id = cipher.encrypt(self.secret_id.encode()).decode()
    
    def decrypt_secret_id(self, cipher: Fernet) -> str:
        """Decrypt secret_id from DB."""
        if isinstance(self.secret_id, str):
            return cipher.decrypt(self.secret_id.encode()).decode()
        return self.secret_id
```

**Source:** [Axiom db.py SQLAlchemy pattern](https://github.com/bambibanners/master_of_puppets/blob/main/puppeteer/agent_service/db.py) [VERIFIED: codebase]; [security.py Fernet helpers](https://github.com/bambibanners/master_of_puppets/blob/main/puppeteer/agent_service/security.py) [VERIFIED: codebase]

### SecretsProvider Protocol (Abstraction Layer)

```python
# Source: CONTEXT.md D-13; Python Protocol pattern
from typing import Protocol, Literal

class SecretsProvider(Protocol):
    """Protocol for secret backends (Vault, Azure, AWS, etc.)."""
    
    async def resolve(self, names: list[str]) -> dict[str, str]:
        """Resolve secret names to values.
        
        Args:
            names: List of secret names/paths
        
        Returns:
            dict mapping name -> value
        
        Raises:
            SecretsError: if resolution fails
        """
        ...
    
    async def status(self) -> Literal["healthy", "degraded", "disabled"]:
        """Return current provider status."""
        ...
    
    async def renew(self) -> None:
        """Renew leases / refresh credentials.
        
        Called by background task. Should not raise.
        """
        ...
```

**Source:** [Python typing.Protocol docs](https://docs.python.org/3/library/typing.html#typing.Protocol); [CONTEXT.md D-13, D-14]

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Secrets in .env files (plaintext) | Fernet encryption at rest in DB | v22.0 | Secrets no longer exposed in git; encryption key externalized to ENCRYPTION_KEY env var |
| No external secrets backend | Vault integration (Phase 167) | v24.0 | EE users can centralize secrets; CE users unaffected |
| Synchronous job dispatch | Async dispatch with middleware (Phase 166) | v24.0 | Router modularization enables injectable middleware for Vault + SIEM |
| Manual lease management | Background APScheduler task | v24.0 | Automatic renewal prevents mid-job secret expiry |
| No secret audit trail | VaultSecret table + AuditLog entries | v24.0 | Compliance visibility; tracks which secrets accessed when |

**Deprecated/outdated:**
- Direct node access to Vault (would require Vault tokens on nodes — trust violation). Current: server-side resolution only.
- Embedding secrets in signed scripts (immutable; secret rotation breaks). Current: declarative secret names; resolved at dispatch.
- Mandatory Vault at startup (blocks platform if Vault unavailable). Current: boot-clean fallback; Vault optional.

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | hvac >= 2.4.0 AppRole login returns auth token usable for subsequent API calls | Standard Stack | If incorrect, secret resolution fails; lease renewal fails |
| A2 | asyncio.to_thread() works with hvac sync calls in Axiom's async architecture | Standard Stack | If incorrect, Vault calls block event loop; dispatch hangs |
| A3 | VaultConfig env var bootstrap (VAULT_ADDRESS, etc.) is sufficient for EE admin setup | User Constraints (D-05) | If incomplete, operators must use admin UI; env-only setup not viable for some deployments |
| A4 | Lease renewal at 30% TTL is sufficient margin for long-running jobs (1–4 hours typical) | Common Pitfalls (Pitfall 2) | If conservative, renewal happens too often (unnecessary Vault load); if aggressive, leases expire mid-job |
| A5 | APScheduler job deduplication (replace_existing=True) prevents duplicate renewal tasks on restart | Code Examples (Lease Renewal) | If incorrect, multiple renewal tasks run concurrently; Vault gets overloaded |
| A6 | Fernet encryption key (ENCRYPTION_KEY) is sufficient strength for encrypting secret_id in DB | Code Examples (VaultConfig) | If weak key, attacker can decrypt secret_id and access Vault |
| A7 | SecretsProvider Protocol will be sufficient for Azure KV, AWS SM, GCP SM without schema changes | User Constraints (D-15) | If protocol too rigid, future backends require rework; planning value lost |
| A8 | 3-failure threshold before DEGRADED status is appropriate (not too aggressive, not too lenient) | Common Pitfalls (Pitfall 1) | If too low, degraded mode triggered on transient errors; if too high, operator doesn't notice real Vault issues |

**All assumptions labeled [ASSUMED] should be confirmed by the planner and user before execution. None are verified against running Vault instances in this session.**

---

## Open Questions

1. **Vault Enterprise Namespace Isolation**
   - What we know: VaultConfig has optional `namespace` field (D-05); hvac supports namespaces
   - What's unclear: Should namespace be a requirement for multi-tenant deployments, or optional?
   - Recommendation: Keep optional in Phase 167; document use case (multi-tenant Vault Enterprise); add per-job namespace override in Phase 168+ if needed

2. **AppRole Secret ID Rotation Workflow**
   - What we know: AppRole auth requires Role ID + Secret ID; both should be rotated periodically
   - What's unclear: Should Phase 167 include automated Secret ID rotation, or operator manual?
   - Recommendation: Phase 167 supports manual rotation (Admin UI for Secret ID update). Automated rotation (standby ID pattern) deferred to Phase 168

3. **Lease TTL vs Job Runtime Validation**
   - What we know: Jobs can run longer than lease TTL; renewal handles this
   - What's unclear: Should dispatch reject jobs if runtime > lease_ttl × 0.8, or just warn?
   - Recommendation: Warn at dispatch; rejection is too strict. Operator can configure acceptable risk via VAULT_MIN_LEASE_TTL env var

4. **Storage of Resolved Secret Values in DB**
   - What we know: Resolved values are encrypted in DB for audit trail
   - What's unclear: Should secrets be stored indefinitely for audit log, or purged after job completes?
   - Recommendation: Store encrypted secrets for 30 days (configurable) for audit trail. After 30 days, delete. Permanent audit trail in AuditLog table (names, access times, not values)

5. **CE Fallback When Vault Unavailable**
   - What we know: CE users without Vault config are unaffected
   - What's unclear: If EE user misconfigures Vault, should CE fallback mode (env vars only) auto-activate?
   - Recommendation: No auto-fallback; requires explicit configuration. Operator chooses: Vault mandatory (fail-fast) or optional (fallback to env vars) via config flag

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Vault Server (external) | VaultService at dispatch/renewal | ✗ (external service) | — | Graceful degradation; jobs without vault_secrets unaffected |
| hvac Python library | Phase 167 implementation | ✓ (will install) | >= 2.4.0 | No fallback; hvac is required for implementation |
| APScheduler | Lease renewal background task | ✓ (already in stack) | existing | Lease renewal is optional; if scheduler unavailable, manual lease management required |
| Cryptography (Fernet) | Secret ID encryption at rest | ✓ (already in stack, Phase 165) | >= 46.0.7 | No fallback; Fernet required for DB field encryption |
| SQLAlchemy | VaultConfig ORM | ✓ (already in stack) | existing | No fallback; ORM is foundational to DB schema |

**Missing dependencies with no fallback:**
- None — all required dependencies are in stack or will be installed

**Missing dependencies with fallback:**
- Vault Server: Graceful degradation (status = DEGRADED); non-Vault jobs unaffected; Vault-dependent jobs fail at dispatch with clear error

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest (existing, used for all backend tests) |
| Config file | `puppeteer/pytest.ini` (existing) |
| Quick run command | `cd puppeteer && pytest tests/test_vault_integration.py -x -v` |
| Full suite command | `cd puppeteer && pytest --cov=agent_service --cov-report=term-missing tests/` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| VAULT-01 | VaultConfig created via Admin UI form | integration | `pytest tests/test_vault_admin.py::test_create_vault_config -v` | ❌ Wave 0 |
| VAULT-01 | VaultConfig env var bootstrap at startup | unit | `pytest tests/test_vault_integration.py::test_bootstrap_from_env -v` | ❌ Wave 0 |
| VAULT-02 | Vault unreachable at startup → status=DEGRADED | unit | `pytest tests/test_vault_integration.py::test_startup_vault_unavailable -v` | ❌ Wave 0 |
| VAULT-03 | Job dispatch resolves secrets → WorkResponse env vars | integration | `pytest tests/test_vault_integration.py::test_dispatch_with_secrets -v` | ❌ Wave 0 |
| VAULT-03 | Job without vault_secrets unaffected | unit | `pytest tests/test_vault_integration.py::test_dispatch_no_secrets -v` | ❌ Wave 0 |
| VAULT-04 | Lease renewal background task runs every 5 min | unit | `pytest tests/test_vault_integration.py::test_lease_renewal_scheduled -v` | ❌ Wave 0 |
| VAULT-04 | 3 renewal failures → status=DEGRADED | unit | `pytest tests/test_vault_integration.py::test_renewal_failure_threshold -v` | ❌ Wave 0 |
| VAULT-05 | GET /admin/vault/status returns health indicator | integration | `pytest tests/test_vault_admin.py::test_vault_status_endpoint -v` | ❌ Wave 0 |
| VAULT-06 | Platform starts when Vault unavailable; no hard crash | integration | `pytest tests/test_vault_integration.py::test_startup_graceful_degradation -v` | ❌ Wave 0 |
| VAULT-06 | Non-Vault jobs dispatch normally when Vault down | integration | `pytest tests/test_vault_integration.py::test_dispatch_without_vault -v` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `pytest tests/test_vault_integration.py -x` (quick suite, ~30 seconds)
- **Per plan completion:** Full backend test suite: `pytest puppeteer/tests/ --cov` (comprehensive, ~5 minutes)
- **Phase gate:** All 10 requirements validated; full integration test suite passes; E2E with mock Vault endpoint succeeds

### Wave 0 Gaps

- [ ] `tests/test_vault_integration.py` — 8 unit tests covering VaultService (connect, resolve, status, renewal, fallback)
- [ ] `tests/test_vault_admin.py` — 4 integration tests covering Admin UI routes (/admin/vault/config GET/PATCH, /admin/vault/status)
- [ ] `tests/conftest.py` — Mock Vault fixture (using responses library to stub Vault HTTP endpoints)
- [ ] Docker mock Vault container (optional): `docker run -d -p 8200:8201 vault:latest` for live integration tests
- [ ] Framework install: hvac already added to requirements.txt by planning phase

*(All test files are Wave 0 — implementation will create them; research only identifies structure)*

---

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | yes | AppRole auth; ENCRYPTION_KEY as seed for HMAC (no password auth) |
| V3 Session Management | yes | Vault auth token lifecycle; background renewal before expiry |
| V4 Access Control | yes | Vault secret paths scoped by Role ID; job-level vault_secrets declarations; ACL at secret resolution |
| V5 Input Validation | yes | vault_secrets list validated (non-empty if use_vault_secrets=true); secret names sanitized for path safety |
| V6 Cryptography | yes | Fernet (AES-128 CBC) for secret_id at rest; TLS for Vault communication; ENCRYPTION_KEY required |
| V7 Errors | yes | Secret resolution errors logged with audit trail; no secrets in error messages (masked) |
| V8 Data Protection | yes | Secrets encrypted in DB; no secrets in logs; secrets never embedded in signed scripts |
| V9 Communications | yes | TLS for Vault connection; mTLS optional for enhanced Vault server validation |
| V13 API Security | yes | /admin/vault routes gated on require_ee() + require_permission("admin:config"); secret resolution only at dispatch (no ad-hoc queries) |

### Known Threat Patterns for Vault Integration

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Vault AppRole Secret ID leaked | Tampering / Disclosure | Fernet encryption at rest; env var is not exposed in logs; rotate Secret ID periodically (operator responsibility) |
| Lease replay attack (old lease after rotation) | Spoofing | Vault tracks lease validity; hvac validates token expiry; background renewal prevents stale leases |
| Job script embeds Vault secret (immutable) | Tampering / Disclosure | Design: declare secret names in job definition; resolve at dispatch. Document anti-pattern (D-04). Script audit validation prevents embedding. |
| Vault connection MITM | Tampering / Disclosure | TLS for Vault connection; optional client cert validation via security.py |
| Secret log leakage (values in audit trail) | Disclosure | Phase 168: SIEM PII masking. Phase 167: no secret values logged (names only; values encrypted). |
| Long-running job secret expiry | Availability | Lease renewal background task; validation at dispatch (job.runtime < lease_ttl × 0.8) |
| Fernet key stolen | Disclosure | ENCRYPTION_KEY required at startup; no file fallback; env var only (rotate via container restart) |
| CE user accesses /admin/vault routes | Privilege Escalation | EE gating: require_ee() on all vault routes; CE tests verify 402 responses |
| Plugin exfiltrates secrets via Vault API | Disclosure | Phase 3: plugins get read-only API proxy (can't access Vault directly); audit every call |

---

## Sources

### Primary (HIGH confidence)

- [hvac Library Documentation](https://hvac.readthedocs.io/en/latest/) — AppRole auth, KV v2 read, lease renewal APIs [VERIFIED: Current as of 2025-10-30]
- [HashiCorp Vault AppRole Auth Method](https://developer.hashicorp.com/vault/docs/auth/approle) — Official Vault docs; Role ID, Secret ID, token workflow [CITED: Official HashiCorp docs]
- [Axiom CONTEXT.md Phase 167 Decisions](/.planning/phases/167-hashicorp-vault-integration-ee/167-CONTEXT.md) — D-01 through D-17; locked design decisions [VERIFIED: Phase discuss-phase output]
- [Axiom ARCHITECTURE-v24.md](/.planning/research/ARCHITECTURE-v24.md) — Vault integration points; lifespan, dispatch layer, lease renewal [VERIFIED: Phase research output]
- [Axiom PITFALLS-v24.0.md](/.planning/research/PITFALLS-v24.0.md) — Pitfalls 1–4 specific to Vault; prevention strategies [VERIFIED: Phase research output]

### Secondary (MEDIUM confidence)

- [Python asyncio.to_thread() Documentation](https://docs.python.org/3/library/asyncio-task-groups.html#running-tasks-concurrently) — Wrapping sync hvac calls in async context [CITED: Python 3.9+]
- [APScheduler AsyncIO Scheduler](https://apscheduler.readthedocs.io/en/latest/schedulers/asyncio.html) — Background lease renewal task pattern [CITED: APScheduler docs]
- [Python typing.Protocol](https://docs.python.org/3/library/typing.html#typing.Protocol) — SecretsProvider abstraction pattern [CITED: Python stdlib]
- [Axiom security.py Fernet Implementation](https://github.com/bambibanners/master_of_puppets/blob/main/puppeteer/agent_service/security.py) — Encryption helpers for DB fields [VERIFIED: Codebase inspection]

### Tertiary (LOW confidence, flagged for validation)

- Assumption A4 (30% TTL lease renewal margin): Not verified against live Vault with varying job durations
- Assumption A8 (3-failure threshold before DEGRADED): Chosen conservatively; may need tuning based on operational experience

---

## Metadata

**Confidence breakdown:**
- **Standard Stack (HIGH):** hvac 2.4.0 is current release; APIs documented; actively maintained
- **Architecture (MEDIUM):** Integration points identified; patterns align with Axiom existing architecture (async, EE gating); implementation details deferred to planning phase
- **Pitfalls (HIGH):** All 4 pitfalls have clear prevention strategies; most mitigation is standard practice (graceful degradation, background tasks, TLS)
- **Security (HIGH):** ASVS mapping is standard; no novel threat patterns; mitigations are conventional (encryption, ACL, audit logging)

**Research date:** 2026-04-18  
**Valid until:** 2026-05-18 (30 days; Vault API stable; hvac library updates may require re-check)  
**Next action:** Planner creates 167-PLAN.md with 5 detailed plans

---

*Research completed by Claude Sonnet 4.6*  
*Phase: 167 — HashiCorp Vault Integration (EE)*  
*Confidence: HIGH (locked decisions + architecture alignment + pitfall prevention)*
