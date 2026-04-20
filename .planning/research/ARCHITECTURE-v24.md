# Architecture Integration: v24.0 Security Infrastructure & Extensibility

**Project:** Axiom (Master of Puppets)
**Researched:** 2026-04-18
**Milestone:** v24.0 (in progress)
**Confidence:** MEDIUM (patterns established, Axiom-specific integration points require phase-level design)

## Executive Summary

The v24.0 feature set spans four distinct architectural layers: **secrets management** (Vault integration for dynamic credential injection), **node identity** (TPM-based attestation augmenting existing mTLS), **extensibility** (public Plugin SDK v2 building on existing entry_points pattern), and **observability** (async SIEM audit streaming with delivery guarantees). Router modularization refactors the 89-route monolith into domain-specific APIRouter modules while preserving the existing CE/EE plugin boundary and all security gates.

These features are **additive and non-breaking** — they extend existing patterns rather than replace them. The critical ordering constraint is: **router modularization must precede Vault and SIEM streaming** because both features require injectable middleware and distributed configuration discovery, which the modular structure enables. TPM identity and Plugin SDK v2 can proceed in parallel with router refactoring.

## Feature Integration Points

### 1. Vault Integration (External Secrets Provider)

**Where it fits:** Vault replaces/augments the existing **Fernet-at-rest** secrets model for long-lived secrets (database passwords, API keys, signing private keys); short-lived job secrets are generated per-request.

**New Components:**
- `vault_service.py` — wraps HashiCorp Vault API client (python-hvac library)
- `VaultConfig` in models/settings — Vault address, auth token/role, secret path prefix
- Middleware for dynamic credential injection in job execution context
- New DB table `VaultSecret` for audit trails (secret path, access log, lease duration)

**Integration with Existing Architecture:**

| Component | Integration Point | Change |
|-----------|------------------|--------|
| `main.py` lifespan | Vault health check at startup (before EE plugin load) | NEW: `await vault_service.health_check()` |
| `job_service.py` | Job creation accepts `vault_secrets: Dict[str, str]` (vault paths) | NEW: service method `resolve_vault_secrets()` |
| Node agent (`node.py`) | Job payload includes `VAULT_SECRETS_PATHS` env var JSON blob | NEW: agent resolves paths via Vault client at container startup |
| `security.py` | Vault auth token validation and TLS cert pinning | NEW: `verify_vault_cert()` |
| `models.py` | `JobCreate` expands: `vault_secrets` field (dict of secret-name → vault-path) | NEW: field + validator |
| AuditLog | Vault secret access logged with lease duration and resolution method | NEW: audit event type |

**Interaction with Fernet Secrets:**
- Fernet secrets remain in DB for **bootstrap/dev secrets** (database connection string, encryption key itself)
- Vault is **optional at runtime** — if `VAULT_ADDRESS` env var absent, job dispatch falls back to Fernet-only mode
- New boolean flag in `JobDispatchRequest`: `use_vault_secrets` (default False for backward compat)
- Vault **never stores** the Fernet key or root passwords — only application-level job secrets

**Per-Job Secret Injection:**
```python
# Job creation in dispatcher
job = Job(
    script_content=...,
    vault_secrets={
        "database_url": "secret/data/prod/db",
        "api_token": "secret/data/prod/slack"
    }
)

# At node execution time
# vault_service.resolve_vault_secrets() called server-side
# Returns fresh TTL-limited tokens
# Injected as VAULT_SECRET_<NAME> env vars into container
# Container lifetime = secret TTL; job cleanup auto-revokes lease
```

**Confidence: MEDIUM** — Pattern is established (hvac + AsyncHTTPClient + lifespan injection), but Axiom-specific token rotation SLAs and CE/EE gating need phase-level design.

---

### 2. TPM-Based Node Identity (Hardware-Backed Attestation)

**Where it fits:** TPM augments (not replaces) the existing **mTLS enrollment flow**. New optional hardware attestation layer for nodes in "hostile environment" mode.

**New Components:**
- `tpm_service.py` — wraps tpm2-tools Python bindings (python-tpm2-lib)
- `NodeAttestation` DB table (node_id, tpm_pcr_quote, quote_timestamp, attestation_status)
- `POST /api/enroll-tpm` endpoint (supplements existing `/api/enroll`)
- Dashboard "Node Attestation" admin panel

**Integration with Existing Architecture:**

| Component | Integration Point | Change |
|-----------|------------------|--------|
| Node enrollment flow (`node.py`) | New optional `--tpm-mode` CLI flag at node startup | NEW: env var `TPM_MODE=true` |
| `/api/enroll` route | Detects `tpm_pcr_quote` in request body; if present, validates via TPM service | MODIFIED: conditional attestation path |
| Root CA cert signing | TPM attestation is **additional validation**, not replacement | N/A — existing mTLS unaffected |
| `Heartbeat` payload | Optional `tpm_pcr_quote` field for periodic re-attestation | NEW: field + optional endpoint |
| `Node` DB model | New columns: `tpm_enabled`, `tpm_pcr_values`, `last_attestation_at` | NEW: columns |
| Job execution (`work/pull`) | TPM attestation checked at pull time (soft fail = warning, not blockage) | MODIFIED: attestation validation gate |
| CRL revocation | Revoked nodes may have TPM disabled (field on RevokedCert) | N/A — no new revocation flow |

**Attestation Flow:**
```
Node startup (TPM_MODE=true):
1. Read TPM PCR[0,1,2,7] values (boot measurement)
2. Generate attestation key (AIK) if absent
3. On enrollment: include PCR quote in /api/enroll body
   Server validates PCR quote signature via TPM public key
4. Server stores PCR baseline in NodeAttestation table
5. On job pull: PCR quote sent with heartbeat
   Server compares PCR against baseline (soft alarm if mismatch = code tampering)
```

**Confidence: LOW** — TPM 2.0 library maturity varies by platform (mature on Linux, emerging on Windows). Axis for phase-specific research: Linux vs Windows TPM availability, PCR value interpretation.

---

### 3. Plugin System v2 (Public SDK Architecture)

**Where it fits:** Extends existing **EE plugin (entry_points) model** into a public-facing SDK with versioned contracts, plugin registry, and lifecycle hooks.

**Existing EE Plugin Structure (v23.0):**
```python
# axiom-ee/ee/plugin.py
class EEPlugin:
    def __init__(self, app: FastAPI, db: AsyncSession): ...
    async def load(self) -> Dict[str, APIRouter]: ...
```

**v24.0 Plugin SDK v2 (Public API):**

**New Components:**
- `axiom-sdk` package: new public `plugin_sdk` submodule
- `PluginBase` abstract class with versioned contract (Protocol[PluginV2])
- `PluginRegistry` in-memory discovery + lifecycle management
- `plugin_hooks.py` — defined hook points (lifecycle, middleware injection, schema extensions)
- Optional DB table `InstalledPlugin` (plugin_id, version, config_hash, load_status)

**New Entry Points** (alongside EE):
```toml
# pyproject.toml
[project.entry-points."axiom.plugins"]
my_siem_exporter = "my_plugin.siem_exporter:SIEMExportPlugin"
my_cache_layer = "my_plugin.cache:CachePlugin"

# Plugin authors implement PluginBase with these hook points:
# - on_app_ready(app) → runs after FastAPI init, before lifespan
# - on_job_dispatched(job) → middleware hook, audit enrichment
# - on_audit_logged(event) → hook for SIEM streaming
# - get_api_routes() → returns APIRouter[] for plugin's own endpoints
# - get_db_models() → returns SQLAlchemy model classes
```

**Integration with Existing Architecture:**

| Component | Integration Point | Change |
|-----------|------------------|--------|
| `main.py` lifespan | Load both EE (old) and SDK v2 (new) plugins sequentially | MODIFIED: expand `load_ee_plugins()` to `load_plugins(mode='all')` |
| CE/EE boundary | SDK v2 plugins are **CE-loadable** (unlike EE which is EE-only) | NEW: allow third-party plugins in CE |
| Plugin entrypoint discovery | Use `importlib.metadata.entry_points()` for group `"axiom.plugins"` | MODIFIED: parallel group discovery |
| Plugin versioning | Plugins declare `__version__` + `SDK_MINIMUM_VERSION` | NEW: semver contract validation |
| Plugin sandbox | Plugins get read-only references; modifications via Depends() | NEW: dependency-injection model for plugins |
| Plugin failure mode | Plugin load error logs warning; app continues (non-blocking) | MODIFIED: graceful degradation (unlike EE which is hard-fail) |

**Plugin Registry Responsibilities:**
```python
class PluginRegistry:
    async def discover_plugins(self) -> Dict[str, PluginBase]
    async def validate_version(plugin_id: str, version: str) -> bool
    async def load_plugin(plugin_id: str, config: Dict) -> None
    async def unload_plugin(plugin_id: str) -> None
    def get_hooks(hook_name: str) -> List[Callable]
    async def execute_hook(hook_name: str, *args, **kwargs) -> None
```

**Confidence: MEDIUM** — Entry points pattern is proven in axiom-ee; SDK v2 is a public-facing API wrapper requiring careful contract design. Phase-level decisions: versioning semantics, schema extension API, Depends() plugin access patterns.

---

### 4. SIEM Audit Log Streaming (Real-Time Event Export)

**Where it fits:** New **async streaming layer** above existing `AuditLog` table. Does not replace AuditLog; sends events to external SIEM in real-time.

**New Components:**
- `siem_service.py` — async webhook/syslog transport (batching, retry, delivery tracking)
- `SIEMConfig` in models/settings — target URL(s), protocol (webhook/syslog), auth headers, batch size
- `AuditLogDelivery` DB table (audit_id, siem_target, delivery_status, retry_count, last_error)
- Middleware that queues audit events to async channel (non-blocking on audit path)

**Integration with Existing Architecture:**

| Component | Integration Point | Change |
|-----------|------------------|--------|
| `audit()` helper (in `main.py`) | Existing sync function calls `_queue_siem_event()` (fire-and-forget) | MODIFIED: add async queue enqueue call |
| AuditLog table | No schema change; streaming is purely transport layer | N/A — backward compat |
| lifespan startup | Start background SIEM batch-sender task (asyncio.create_task) | NEW: `_start_siem_streaming_task()` |
| lifespan shutdown | Flush pending SIEM events before shutdown (5s timeout) | NEW: `_flush_siem_queue()` in shutdown |
| `admin_service.py` | New CRUD endpoints: `GET /api/admin/siem-config`, `PATCH /api/admin/siem-config` | NEW: routes |
| Dashboard Admin page | New "SIEM Integration" section with target URL, protocol, delivery status | NEW: UI component |
| Health endpoint | `GET /health/siem` returns queue depth, last delivery status, backpressure alerts | NEW: endpoint |

**Streaming Architecture:**
```
audit() call (synchronous)
  ↓
_queue_siem_event(event) [async enqueue, non-blocking]
  ↓
Background task: siem_streaming_worker
  Batches events (configurable: 10 events or 5s timeout)
  ↓
siem_service.send_batch(events)
  Webhook: POST /webhook with HMAC-SHA256 signature + nonce
  Syslog: send via UDP/TLS to syslog endpoint
  ↓
AuditLogDelivery table: record success/retry/failure
  Exponential backoff: 1s, 2s, 4s, 8s, final via dead-letter queue
```

**Delivery Guarantees:**
- **At-least-once:** Events queued in-memory until delivered; on process crash, in-flight events lost (acceptable for security events; full history in AuditLog)
- **Idempotency:** Each event includes `audit_id` + nonce (SIEM deduplicates via nonce on retry)
- **Ordering:** Events delivered in AuditLog insertion order (single background task)
- **Backpressure:** If SIEM target is down, queue grows; `/health/siem` warns when queue depth > 1000

**Confidence: HIGH** — Webhook pattern is established in v23.0 (workflow webhooks); SIEM streaming follows same batching/retry model. Axiom-specific: audit event schema mapping to SIEM CEF/Splunk formats requires phase-level design.

---

### 5. Router Modularization (main.py → Domain Routers)

**Where it fits:** **Prerequisite for Vault and SIEM** because both require injectable configuration and middleware that work cleanly in modular structure.

**Current State (v23.0):**
- `main.py`: 89 routes, ~3,500 LOC monolith
- All routes in single file → difficult to navigate, test, and extend
- CE/EE plugin boundary is external (ee/plugin.py); CE routes live in main.py

**Proposed Structure (v24.0):**
```
puppeteer/agent_service/
  main.py                          # FastAPI app, lifespan, exception handlers
  routers/
    __init__.py
    auth_router.py                 # POST /auth/*, GET /auth/me (12 routes)
    jobs_router.py                 # POST /api/jobs/*, GET /api/jobs/* (18 routes)
    nodes_router.py                # GET /api/nodes/*, PATCH /api/nodes/* (14 routes)
    workflows_router.py            # POST/GET/PATCH /api/workflows/* (16 routes)
    foundry_router.py              # GET/POST /api/foundry/* (15 routes)
    admin_router.py                # GET/POST /api/admin/* (20 routes)
    system_router.py               # GET /health/*, /system/*, /docs (4 routes)
  services/                        # EXISTING — no change
    job_service.py
    foundry_service.py
    scheduler_service.py
    vault_service.py               # NEW in v24.0
    siem_service.py                # NEW in v24.0
```

**Integration Changes:**

| File | Current Approach | v24.0 Modular Approach |
|------|------------------|------------------------|
| `main.py` | All 89 routes defined inline | Instantiate APIRouter objects; include via `app.include_router(auth_router)` |
| Route definitions | `@app.post("/auth/login")` | `@router.post("/login")` in `auth_router.py` |
| Dependency injection | Routes use `Depends(require_permission(...))` | Routers use same Depends; no change to security gates |
| Middleware | Global middleware in FastAPI(middleware=...) | Middleware remains global; can apply per-router if needed |
| Exception handlers | Global exception handlers on `app` | Remains global; accessible to all routers |
| lifespan | Startup/shutdown in single lifespan context | Unchanged; lifespan remains in main.py |
| Imports | from db import Base; from models import * | Each router imports only what it needs |
| Tests | `test_main.py` tests all 89 routes | `test_auth.py`, `test_jobs.py`, etc. (modular test suite) |

**Router Prefix Strategy:**
```python
# In main.py
app.include_router(auth_router, prefix="")  # /auth/*
app.include_router(jobs_router, prefix="/api")  # /api/jobs/*
app.include_router(nodes_router, prefix="/api")  # /api/nodes/*
app.include_router(admin_router, prefix="/api/admin", tags=["admin"])
app.include_router(system_router, prefix="")  # /health/*, /system/*
```

**CE/EE Plugin Boundary (Preserved):**
```python
# In main.py lifespan
await load_ee_plugins(app)  # Still loads ee/plugin.py routes
app.include_router(auth_router)
app.include_router(jobs_router)
# ... CE routers
```

**Vault/SIEM Middleware Integration (Enabled by Modular Structure):**
```python
# vault_middleware.py (can wrap any router)
async def vault_credentials_middleware(request, call_next):
    if request.url.path.startswith("/api/jobs/dispatch"):
        # Resolve vault secrets for this request
        request.state.vault_secrets = await vault_service.resolve(...)
    return await call_next(request)

# In main.py: apply selectively
app.add_middleware(vault_credentials_middleware)

# Or per-router in v24.0 (cleaner approach for CE/EE isolation)
jobs_router.middleware('http')(vault_credentials_middleware)
```

**Build Order (Router Modularization as Phase 1):**
1. **Phase 1:** Split main.py → 6 domain routers; all tests pass; no logic changes
2. **Phase 2:** Vault integration (builds on modular structure)
3. **Phase 3:** SIEM streaming (builds on modular structure)
4. **Phases 4–5:** TPM identity + Plugin SDK v2 (can proceed in parallel)

**Confidence: HIGH** — APIRouter pattern is canonical FastAPI; projects like FastAPI-best-practices use this structure. Axiom-specific: preserving CE/EE boundary during refactor requires careful import ordering.

---

## New vs Modified Components Summary

### New Components (v24.0)

| Component | Type | Purpose | Location |
|-----------|------|---------|----------|
| `vault_service.py` | Service | Vault API client, secret resolution, lease tracking | `agent_service/services/` |
| `VaultConfig` | Model | Vault connection settings, auth method | `agent_service/models.py` |
| `siem_service.py` | Service | SIEM webhook/syslog transport, batching, retry | `agent_service/services/` |
| `SIEMConfig` | Model | SIEM target URL, protocol, auth, batch config | `agent_service/models.py` |
| `VaultSecret` | DB Table | Audit trail of vault secret access | `agent_service/db.py` |
| `AuditLogDelivery` | DB Table | SIEM delivery status, retry tracking | `agent_service/db.py` |
| `NodeAttestation` | DB Table | TPM attestation quotes, PCR baselines | `agent_service/db.py` |
| `tpm_service.py` | Service | TPM 2.0 tools wrapper, attestation validation | `agent_service/services/` |
| `tpm_router.py` | Router | Attestation admin endpoints | `agent_service/routers/` |
| `plugin_sdk/__init__.py` | Package | Public SDK exports (PluginBase, PluginRegistry, hooks) | `agent_service/plugin_sdk/` |
| `PluginRegistry` | Class | Plugin discovery, versioning, lifecycle | `agent_service/plugin_sdk/registry.py` |
| `PluginBase` | Abstract Class | Public plugin contract | `agent_service/plugin_sdk/base.py` |
| `plugin_hooks.py` | Module | Hook point definitions | `agent_service/plugin_sdk/hooks.py` |
| `auth_router.py` | Router | Auth routes extracted from main | `agent_service/routers/` |
| `jobs_router.py` | Router | Job routes extracted from main | `agent_service/routers/` |
| `nodes_router.py` | Router | Node routes extracted from main | `agent_service/routers/` |
| `workflows_router.py` | Router | Workflow routes extracted from main | `agent_service/routers/` |
| `foundry_router.py` | Router | Foundry routes extracted from main | `agent_service/routers/` |
| `admin_router.py` | Router | Admin routes extracted from main | `agent_service/routers/` |
| `system_router.py` | Router | System/health routes extracted from main | `agent_service/routers/` |

### Modified Components (v24.0)

| Component | Modification | Impact |
|-----------|--------------|--------|
| `main.py` | Remove all route definitions; instantiate and include routers; add Vault/SIEM lifespan hooks | ~500 LOC reduction; complexity moved to routers and services |
| `job_service.py` | `create_job()` calls `vault_service.resolve_vault_secrets()` if job has vault_secrets field | NEW: optional integration point |
| `node.py` (agent) | Accept `vault_secret_paths` in WorkResponse; resolve via Vault client at container startup | NEW: env var injection; optional feature |
| `audit()` helper | Call `_queue_siem_event()` asynchronously (non-blocking) | Imperceptible latency; backward compat |
| `models.py` | Add fields: `JobCreate.vault_secrets`, `Job.vault_secret_ids`, `Node.tpm_enabled`, `Node.tpm_pcr_values` | NEW: fields; existing fields unaffected |
| `db.py` | Add 3 new tables (VaultSecret, AuditLogDelivery, NodeAttestation) | DB migration required on first startup |
| `requirements.txt` | Add: hvac (Vault), python-tpm2-lib (TPM), pluggy (plugin hooks, optional) | 3 new dependencies; hvac required, others optional for CE |
| `lifespan()` context | Startup: health-check Vault, start SIEM background task; Shutdown: flush SIEM queue | NEW: async task lifecycle |
| `/api/admin/` routes | Add: GET/PATCH /api/admin/siem-config, GET/POST /api/admin/tpm-config | NEW: endpoints; gated on `users:write` |
| `/health/` routes | Add: GET /health/siem, GET /health/vault | NEW: endpoints; gated on `require_auth` |
| Dashboard Admin page | Add 3 new sections: Vault config, SIEM config, TPM attestation dashboard | NEW: UI; EE-only or CE-accessible TBD in phase |

---

## CE/EE Impact & Boundary Preservation

**Green (No Change):**
- mTLS enrollment flow
- Ed25519 job signing
- Container isolation enforcement
- RBAC permission gates
- Audit logging (existing table)

**Amber (Optional in Both CE/EE):**
- Vault integration: configuration optional; if `VAULT_ADDRESS` absent, falls back to Fernet-only
- SIEM streaming: configuration optional; if `SIEM_CONFIG` absent, events stay in AuditLog only
- TPM attestation: soft validation gate (warnings, not blockage); nodes run without TPM

**Red (EE-Only or Feature-Gated):**
- Plugin SDK v2: public API available in CE (third-party plugins), but certain hooks (EE-only observability) gated
- Advanced SIEM formats (CEF, Splunk HEC): EE feature; CE has basic webhook

**Critical for Phase Design:**
1. **Vault integration licensing:** Is vault_secrets a paid feature or CE-native?
2. **SIEM streaming licensing:** Is SIEM config an EE feature or CE-native?
3. **TPM attestation licensing:** Is TPM a paid "hardening" feature?
4. **Plugin SDK licensing:** Are third-party CE plugins allowed or EE-only?

---

## Suggested Phase Build Order (v24.0)

### Phase 1: Dependabot Vulnerability Remediation (Days 1–2)
- Identify 2 high + 1 moderate vulnerabilities from GitHub Security tab
- Pin or patch in `requirements.txt`; add regression tests
- Verify all existing E2E tests pass

### Phase 2: Router Modularization (Days 3–5)
- Extract 89 routes into 6 domain routers
- Preserve all security gates (require_permission, mTLS validation)
- Refactor test suite: split `test_main.py` → modular test files
- Ensure zero behavior change (all 89 routes unchanged)

### Phase 3: Vault Integration (Days 6–8)
- Implement `vault_service.py` + `VaultConfig`
- Add `vault_secrets` field to JobCreate
- Wire into job dispatch + node execution
- Test with mock Vault (hvac testcontainer)

### Phase 4: SIEM Streaming (Days 9–11)
- Implement `siem_service.py` + background task
- Add Admin config panel + GET /health/siem
- Test webhook delivery + retry logic (mock SIEM endpoint)

### Phase 5: TPM Identity (Days 12–14, Parallel Option)
- Implement `tpm_service.py` + attestation flow
- Add optional `/api/enroll-tpm` endpoint
- Test on Linux nodes with TPM hardware (or simulator)

### Phase 6: Plugin SDK v2 (Days 15–17, Parallel Option)
- Define `PluginBase` contract + hook points
- Implement `PluginRegistry` + versioning
- Create example CE plugin (e.g., sample SIEM exporter)
- Document public SDK in MkDocs

---

## Risk Assessment & Validation Needs

| Area | Risk | Mitigation | Phase |
|------|------|-----------|-------|
| Router refactoring breaks CE/EE boundary | MEDIUM | Comprehensive route mapping; test CE/EE split on both editions | Phase 2 |
| Vault misconfiguration blocks job dispatch | MEDIUM | Fallback to Fernet if Vault unavailable; health checks in startup | Phase 3 |
| SIEM queue overflow on network outage | MEDIUM | Bounded in-memory queue (max 10K events); backpressure alerts | Phase 4 |
| TPM unavailable on Windows nodes | MEDIUM | Soft validation gate; attestation warnings not errors | Phase 5 |
| Plugin SDK security: untrusted plugins break app | MEDIUM | Entry point whitelist (exact match); plugins run with read-only refs | Phase 6 |
| Dependabot vulnerabilities in dependencies | HIGH | Fix immediately; add to CI gate; monthly audit | Phase 1 |

---

## Sources

- [FastAPI Router Best Practices](https://fastapi.tiangolo.com/tutorial/bigger-applications/)
- [Stop Writing Monolithic FastAPI Apps — Modular Setup](https://medium.com/@bhagyarana80/stop-writing-monolithic-fastapi-apps-this-modular-setup-changed-everything-44b9268f814c)
- [FastAPI Best Practices Repository](https://github.com/zhanymkanov/fastapi-best-practices)
- [HashiCorp Vault FastAPI Integration](https://hoop.dev/blog/how-to-configure-fastapi-hashicorp-vault-for-secure-repeatable-access/)
- [Device & Workload Authentication using TPM](https://www.infracloud.io/blogs/device-workload-authentication/)
- [SPIFFE & SPIRE: Workload Identity Standard](https://sameerbhanushali.substack.com/p/spiffe-and-spire-the-workload-identity)
- [Creating and Discovering Plugins — Python Packaging](https://packaging.python.org/guides/creating-and-discovering-plugins/)
- [SIEM Audit Log Streaming Best Practices](https://zitadel.com/docs/guides/integrate/external-audit-log)
- [Kubernetes Audit Sinks for Real-Time Event Streaming](https://oneuptime.com/blog/post/2026-02-09-audit-sink-real-time-event-streaming/view)
- [Python Plugin System Design](https://oneuptime.com/blog/post/2026-01-30-python-plugin-systems/view)
- [Octantis Plugin SDK Architecture](https://pypi.org/project/octantis-plugin-sdk/)
