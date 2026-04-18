# Feature Landscape — Axiom v24.0

**Scope:** Five major features for v24.0: HashiCorp Vault external secrets, TPM-based node identity, Plugin System v2 SDK, SIEM audit streaming, main.py router refactoring

**Researched:** 2026-04-18

**Overall Confidence:** MEDIUM (production patterns clear; implementation complexity higher for features 2–3, lower for features 4–5)

---

## Executive Summary

The v24.0 feature set addresses infrastructure hardening and extensibility gaps in Axiom. Three observations emerge from production research:

1. **External Secrets (Vault)** is table stakes for enterprise deployments and a low-risk addition that Axiom can support without architectural change. AppRole is the recommended authentication path with KV v2 for versioning.

2. **TPM-based Identity** is a differentiator that segments Axiom's market: enterprise deployments with hardware-backed infrastructure benefit significantly; homelab users gain minimal value and face substantial operational complexity. Attestation can be deferred to v25.0 if focusing on identity enrollment only.

3. **Plugin System v2** is a strategic differentiator: it enables third-party extensibility that competitors do not offer, but the implementation is complex because Python plugins can never be truly sandboxed. Axiom's pull architecture and container isolation model position the plugin system well if plugins are treated as trusted-by-default (like Docker daemon plugins, not untrusted third-party code).

4. **SIEM Streaming** is table stakes for enterprise and reduces operational overhead significantly. CEF/syslog patterns are well-established; webhook push is simpler than log-file tail approaches and avoids agent requirements on the Axiom orchestrator.

5. **Router Refactoring** is a housekeeping task that improves maintainability and testability but carries risk of regression if not carefully staged. Safe migration path exists: domain routers in parallel, gradual cutover, legacy routes deprecated per-version.

**Key Risk:** Attempting all five features in v24.0 is scope-heavy. Prioritize (1) Vault + SIEM streaming + router refactoring as Phase 1, deferring (2) TPM identity and (3) Plugin System to Phase 2 (v24.1 or v25.0) unless TPM is a critical enterprise blocker.

---

## Feature 1: External Secrets Provider (HashiCorp Vault)

### Estimated Complexity
**Table Stakes / Low Risk**

### What It Does

Axiom externalizes secrets (API keys, encryption keys, signing credentials, database passwords) to HashiCorp Vault instead of reading them from environment variables or disk files. The orchestrator and optionally nodes can authenticate to Vault and fetch secrets at startup or periodically.

### Table Stakes

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| AppRole authentication (Role ID + Secret ID) | Enterprise requirement: avoids long-lived tokens in CI/CD, dual-channel delivery splits credentials | Low–Med | Role ID is non-secret username; Secret ID is password. Standard in 90% of enterprise Vault deployments. |
| KV v2 secret engine support | Standard Vault API; enables secret versioning and soft delete | Low | Axiom need not implement versioning explicitly — read latest version and log audit trail. |
| Startup-time secret fetch | Orchestrator bootstraps encryption/JWT keys from Vault before serving | Low | No live reload needed for v24.0 — static at startup. |
| Secure credential delivery via Response Wrapping | Prevent Secret ID capture by intermediate systems | Med | HashiCorp best practice; reduces blast radius of single-point compromise. |
| Basic auth fallback | SQLite deployments or non-Vault environments continue to use env vars | Low | Feature flag in startup logic. |

### Differentiators

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Dynamic credential rotation on operator command | Operator can rotate secrets without redeploying orchestrator | Med | `POST /api/admin/rotate-secrets` endpoint; requires Vault client library. |
| Automated secret TTL refresh (APScheduler) | Secrets rotated on a schedule; operator does not need to manual-trigger | Med | Background job polls Vault, refreshes in-memory cache. Risk: rotation failure cascades to all dependent services. |
| Multi-region Vault HA failover | Orchestrator can reach standby Vault instances on primary failure | High | Requires Vault HA cluster; Axiom code simple (retry logic) but operational complexity high. |
| Logging of all secret access (audit trail) | Every Vault read audited in Vault logs and Axiom audit_log table | Low | Log Vault secret access policy in Vault config; hook in Axiom fetch layer. |

### Anti-Features

| Anti-Feature | Why Avoid | What to Do Instead |
|--------------|-----------|-------------------|
| Vault agent sidecar in compose | Adds complexity: separate TLS, separate auth, separate leasing logic | Let Axiom fetch directly; if load is high, implement read caching in Axiom (in-memory, TTL-bound). |
| Encrypted field-level secrets in DB (DB-backed Vault) | Axiom already has Fernet encryption at rest; building a mini-Vault in code is unmaintainable | Use external Vault for secret store; use Axiom's Fernet only for at-rest encryption of non-secret config. |
| Interactive secret CLI commands | Operator should not have CLI tools for secret management; use Vault CLI directly | Doc the pattern: `vault kv get -format=json secret/axiom/api-key` and hand to Axiom. |

### Dependencies on Existing Features

- **Encryption Key Derivation**: Axiom currently uses `ENCRYPTION_KEY` env var (Fernet). With Vault, this becomes `ENCRYPTION_KEY = vault.read('secret/data/axiom/encryption-key')['data']['data']['key']`. Migration path: soft launch with optional Vault, keep env var fallback.
- **Database Connection String**: `DATABASE_URL` env var can be replaced with Vault read of `secret/data/axiom/database-url`. Same pattern.
- **Service Principals & API Keys**: Axiom stores these in the `UserApiKey` DB table. No conflict with Vault — Vault is for *operator* secrets, not user-issued API keys.

### Feasibility for Homelab vs Enterprise

| Context | Feasibility | Rationale |
|---------|-------------|-----------|
| **Homelab (SQLite, single node)** | Low–Medium; Optional | Vault setup is overkill for 1–5 nodes; Axiom env vars sufficient. If interested, `compose.server.yaml` can include Vault sidecar, but it's not a recommended path. |
| **Enterprise (Postgres, multi-region)** | High; Table Stakes | Vault is standard; Axiom must support it for operator comfort. AppRole auth is enterprise default. |

### Implementation Notes

**Safe API Contract:**
```python
# Vault client initialized at startup
@app.on_event("startup")
async def bootstrap_vault():
    if VAULT_ADDR:
        vault_client = hvac.Client(url=VAULT_ADDR, auth=AppRoleAuth(...))
        # Cache secrets in memory with TTL
        app.state.secrets = {
            'encryption_key': vault_client.read('secret/data/axiom/encryption-key'),
            'jwt_secret': vault_client.read('secret/data/axiom/jwt-secret'),
        }
    else:
        # Fallback to env vars
        app.state.secrets = {
            'encryption_key': os.getenv('ENCRYPTION_KEY'),
            'jwt_secret': os.getenv('SECRET_KEY'),
        }
```

**No breaking changes:** Axiom continues to start with env vars. Vault is opt-in via `VAULT_ADDR` + `VAULT_ROLE_ID` + `VAULT_SECRET_ID` (or response-wrapped token path).

---

## Feature 2: TPM-Based Node Identity

### Estimated Complexity
**Differentiator / Medium–High Risk**

### What It Does

Nodes prove their identity to the orchestrator using a Trusted Platform Module (hardware security chip). Instead of a certificate issued by the orchestrator's Root CA, nodes present a TPM-attested endorsement key and platform attestation quote. The orchestrator verifies the quote against a trusted PCR (Platform Configuration Register) baseline, proving the node's hardware and firmware configuration.

### Table Stakes

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| TPM 2.0 endpoint availability on node hardware | Cannot proceed without TPM present | Low | Most modern servers (2018+) have TPM 2.0. Homelabs may lack it. |
| Endorsement Key (EK) certificate extraction from TPM | Proves TPM is genuine (certified by manufacturer CA) | Low–Med | Standard TPM 2.0 operation; Python `tpm2_tools` or similar can extract EK cert and verify against Manufacturer CA. |
| Attestation Key (AK) generation and quote signing | Node signs a platform attestation quote with AK; orchestrator verifies signature | Med | TPM 2.0 quote format is standardized; orchestrator must validate AK signature and PCR values. |
| PCR (Platform Configuration Register) baseline definition | Orchestrator knows what "good" looks like for a given OS/firmware/boot config | High | PCR values change with firmware updates, kernel patches, initramfs content. Baseline management is operationally complex. |

### Differentiators

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Continuous attestation (periodic re-quote) | Node proves it is still in a trusted state on every heartbeat | High | Requires TPM quote generation every 10–30s; TPM performance bottleneck risk. Keylime's push model is reference architecture. |
| Hardware supply-chain attestation | Verify EK was issued by genuine manufacturer (not counterfeit TPM) | Med | Compare EK cert against manufacturer root CA cert store; requires maintaining cert database. |
| Measured Boot validation | Verify boot sequence matches baseline (firmware → bootloader → kernel) | High | PCR 0–7 encode boot chain; operator must define "good" baseline. Any OS patch breaks PCR values. |
| Remediation actions on attestation failure | Auto-drain/revoke node if attestation fails | Med | Depends on continuous attestation (above). Safe to implement if attestation runs async (not blocking heartbeat). |

### Anti-Features

| Anti-Feature | Why Avoid | What to Do Instead |
|--------------|-----------|-------------------|
| Per-job attestation on every dispatch | TPM quote generation is slow (100–500ms per quote); blocking job dispatch is unacceptable | Only quote at enrollment + periodic heartbeat. Job execution does not need fresh attestation if heartbeat is frequent (10s). |
| Full supply-chain traceability (tracking EK cert origin through manufacturer) | Requires maintaining curated list of manufacturer CAs; licensing/export restrictions on some CAs | Verify EK cert signature against public manufacturer CA certs; treat missing cert as untrusted but recoverable. |
| Nested attestation (Node→TPM→PCR→EK→Manufacturer) in tight loop | Creates circular dependency: PCR includes kernel code, kernel has TPM driver, TPM measures kernel — complex to audit | Measure at enrollment only; treat as static identity binding. Continuous re-measurement is bonus feature. |

### Complexity Differential: Enterprise vs. Homelab

| Context | Implementation | Operational Load | Feasibility |
|---------|---|---|---|
| **Enterprise** | Full measured boot + continuous attestation + firmware attestation | High: baseline management, PCR change tracking, supply-chain verification | High; justified ROI if compliance requires hardware-backed identity. |
| **Homelab** | TPM 2.0 EK certificate enrollment only (no continuous re-quote) | Low: one-time setup per node | Medium; adds hardening but no immediate operational benefit. |

### Dependencies on Existing Features

- **mTLS Fallback**: Axiom's current mTLS flow (Root CA → client cert) must remain functional for non-TPM nodes. TPM is opt-in per-node capability.
- **Node Heartbeat**: TPM quote can be embedded in heartbeat payload, avoiding a new round trip.
- **Capability Flags**: Add `tpm_capable` and `attestation_verified` to node capabilities and status responses.

### Research Findings: Keylime Reference Architecture

Keylime (Red Hat supported) is the de facto standard:
- **Push model** (not pull): Node sends attestation to verifier when ready; verifier processes async. Avoids firewall complexity.
- **Registrar + Verifier** roles: Registrar stores EK public keys; Verifier handles quote validation. Axiom can implement both roles in a single backend service.
- **PCR Whitelist**: Operator defines baseline PCRs per OS/config; any mismatch triggers audit log and optional alert.

**Key insight:** TPM attestation is powerful for *hostile environments* (where node hardware is untrusted). For homelab/internal deployments, mTLS is sufficient and TPM adds operational burden without corresponding security gain.

---

## Feature 3: Plugin System v2 (SDK)

### Estimated Complexity
**Strategic Differentiator / High Risk**

### What It Does

Third-party developers can extend Axiom with custom plugins for:
- Custom job dispatchers (send jobs to external orchestrators)
- Custom auditors (stream audit logs to external SIEM)
- Custom secret providers (call custom KMS instead of Vault)
- Custom authenticators (OIDC, SAML, custom LDAP)

Plugins are Python packages installed via PyPI or private wheel repos. Axiom loads them via `importlib.metadata` entry points. Plugins expose a versioned API contract.

### Table Stakes

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Plugin discovery via entry points | Axiom auto-loads plugins without hardcoded imports | Low | Use `importlib.metadata.entry_points()` same pattern as EE plugin (already implemented). |
| Versioned plugin API contract | Plugin SDK version pinned to Axiom version; plugins declare compatibility | Low–Med | Plugin must declare `api_version='1'` in metadata. Axiom loads only plugins matching its API version. |
| Plugin lifecycle hooks | Initialize on startup, shutdown gracefully, handle config reloads | Med | Async context manager pattern: `async with plugin.init(config):` wraps plugin lifetime. |
| Plugin dependency isolation | Plugin can declare its own `install_requires` without conflicting with Axiom deps | Low | `pip install axiom-plugin-foo` installs plugin + deps in same environment; no isolation. |
| Documentation of plugin API | SDK docs explain what hooks exist, what contracts to implement | Med | MkDocs guide + inline docstrings + example plugin in repo. |

### Differentiators

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Plugin hot-reload (no restart) | Operator updates plugin code; APScheduler task reloads plugin without full restart | High | Requires plugin state cleanup + reimport + re-registration. High risk of dangling references and memory leaks. |
| Custom job task types (plugins define new task_type values) | Plugin adds `task_type='custom_ml_train'` that Axiom routes to plugin handler | Med–High | Axiom dispatch pipeline must delegate unknown task types to plugins; plugin must implement validation + execution. |
| Plugin-to-plugin messaging | Plugin A publishes events that Plugin B consumes | High | Requires event bus; plugins must be loosely coupled. Complex state management across restarts. |
| Plugin marketplace (package discovery) | Web UI shows available plugins, one-click install from PyPI | High | Registry service separate from Axiom core; requires trust/vetting model. Out of scope for v24.0. |

### Anti-Features

| Anti-Feature | Why Avoid | What to Do Instead |
|--------------|-----------|-------------------|
| Plugin sandboxing via separate process / container | "Untrusted plugins must be isolated." Reality: Python cannot be sandboxed; gVisor/Firecracker overhead is not justified for trusted plugins. | Treat plugins as trusted-by-default (like Docker daemon plugins, Kubernetes operators). Require code review for plugin approval, same as internal code. |
| Plugin A calling arbitrary Python code in Plugin B's namespace | Plugins should not import each other directly. | Use entry points only for Axiom to call plugins; plugins call Axiom APIs (HTTP/RPC) not each other. |
| Plugin defining custom DB schema | "Plugin needs custom table for state." Reality: Axiom schema becomes unmaintainable with arbitrary plugin tables. | Provide plugin a structured key-value store on Axiom tables (like Config table). Plugin uses `axiom_client.kv_set('plugin_name:key', value)`. |
| Dynamic plugin loading from untrusted sources (PyPI hotlinks in deploy) | No validation that plugin is from trusted author. | Manual approval workflow: operator runs `axiom-verify-plugin [package-name]` which checks author signature (Ed25519 key), then installs. |

### Feasibility: Enterprise vs. Homelab

| Context | Use Cases | Feasibility |
|---------|-----------|-------------|
| **Enterprise** | Custom auditors (to internal SIEM), custom dispatchers (to legacy schedulers), custom authenticators (OIDC bridge) | High; plugins reduce need for Axiom forks. Trusted environment (internal devops team writes plugins). |
| **Homelab** | Rarely needed; operators don't extend Axiom. | Low; overhead of plugin framework not justified. |

### Design Principle: Trust Model

**Axiom Plugin Trust Model (v24.0):**

Plugins are treated as **trusted code** at the same trust level as Axiom core. Installation workflow:

1. Operator runs `pip install axiom-plugin-foo` (or `pip install -e /local/plugin-foo`)
2. Axiom startup discovers plugin via entry points
3. Plugin hooks fire (init, register handlers, etc.)
4. Operator verifies plugin functionality via audit log / API tests
5. No runtime sandboxing; full OS access (like all Python code in the container)

**Why this works for Axiom:**

- Axiom nodes already execute arbitrary operator-authored code (job scripts), so trusting plugins is not a new risk category.
- Plugins run in the same container as Axiom, not on untrusted third-party hardware.
- Internal devops teams write plugins for their own infrastructure; external marketplace is a v25.0+ feature (if ever).

**What this prevents:**

- Axiom cannot safely run untrusted third-party plugins (like a plugin marketplace). If third-party extensibility is required, use microservice architecture (plugin as sidecar service, Axiom calls via HTTP).

### Implementation Notes

**Plugin Registry (Simple Pattern):**
```python
# axiom/plugin_api.py
class AxiomPlugin(ABC):
    name: str = "my-plugin"
    version: str = "1.0.0"
    api_version: str = "1"  # Must match Axiom.api_version
    
    async def init(self, config: Dict[str, Any]) -> None:
        """Initialize plugin. Called once at startup."""
        pass
    
    async def shutdown(self) -> None:
        """Cleanup. Called on SIGTERM."""
        pass
    
    # Plugin-specific hooks (examples):
    async def on_job_created(self, job: Job) -> None:
        """Hook: new job dispatched."""
        pass
    
    async def on_audit_event(self, event: AuditLogEntry) -> None:
        """Hook: audit event recorded."""
        pass
```

**Axiom Startup (Discovery):**
```python
# main.py
from importlib.metadata import entry_points

async def load_plugins():
    eps = entry_points()
    axiom_plugins = eps.select(group='axiom.plugins')
    
    for ep in axiom_plugins:
        try:
            plugin_class = ep.load()
            if plugin_class.api_version != "1":
                logger.warning(f"Skipping {ep.name}: incompatible API version {plugin_class.api_version}")
                continue
            
            plugin = plugin_class()
            await plugin.init(app.state.config)
            app.state.plugins.append(plugin)
            logger.info(f"Loaded plugin: {plugin.name} v{plugin.version}")
        except Exception as e:
            logger.error(f"Failed to load plugin {ep.name}: {e}")
            # Hard fail if plugin load fails (no silent skip)
            raise
```

---

## Feature 4: SIEM Audit Log Streaming

### Estimated Complexity
**Table Stakes / Low–Medium Risk**

### What It Does

Axiom streams audit log events to external SIEM platforms in real-time via webhook (HTTP POST), syslog (TCP/UDP), or CEF (Common Event Format). Integration is bidirectional: SIEM can correlate Axiom audit events with other infrastructure logs (network, OS, auth) and create cross-system alerts.

### Table Stakes

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| CEF (Common Event Format) export | Standard format recognized by 90% of SIEMs (Splunk, Elastic, QRadar, etc.) | Low | Axiom audit_log events → CEF header + extension fields. RFC 3164 compliant. |
| Syslog transport (TCP/UDP port 514) | Operator points Axiom to syslog collector; events flow continuously | Low–Med | Python `logging.handlers.SysLogHandler` built-in; UDP lossy but standard; TCP reliable. |
| Webhook push (HTTP POST with HMAC signature) | Alternative to syslog for operators without dedicated syslog infrastructure | Low | Simple: `POST https://siem.example.com/events` with JSON body + X-Axiom-Signature header (HMAC-SHA256). |
| Selective audit log streaming (not all events) | Operator chooses which event types to stream (e.g., only user actions, not heartbeats) | Low–Med | Config table: `audit_stream_filters = '{"event_type": ["USER_LOGIN", "JOB_DISPATCH"]}'`. |
| Startup-time configuration | Operator sets `AUDIT_SYSLOG_HOST=siem.internal:514` and streaming begins | Low | Syslog handler initialized in lifespan startup; errors logged but don't block startup. |

### Differentiators

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Real-time alerting on suspicious events (SIEM native) | SIEM rules trigger on Axiom events (e.g., alert if 3+ failed logins in 5 min) | Med | Depends on SIEM capabilities, not Axiom code. Axiom just streams clean events. |
| Splunk HEC (HTTP Event Collector) native support | Axiom → Splunk HEC endpoint with authentication token | Low–Med | HEC is HTTP; Axiom sends JSON; Splunk parses and indexes. No special Axiom code needed beyond webhook pattern. |
| Audit log retention in SIEM (long-term cold storage) | SIEM indexes all Axiom audit logs indefinitely; Axiom DB can prune old records | Med | Axiom continues to prune local audit_log table per retention policy; SIEM is authoritative archive. |
| Custom audit event mapping (Axiom field → SIEM field) | Operator maps `job_status=FAILED` → CEF `outcome=failure`, `error_reason` → CEF `reason` | Low | Configurable mapping in Admin UI or YAML; transforms audit events to match SIEM schema. |
| Delivery guarantee (at-least-once semantics) | If SIEM is unreachable, Axiom retries and logs failure | Med | Local queue (in-memory list, flushed periodically); on SIEM timeout, retry with exponential backoff. Risk: queue overflow on sustained SIEM outage. |

### Anti-Features

| Anti-Feature | Why Avoid | What to Do Instead |
|--------------|-----------|-------------------|
| Log file tailing from Axiom stdout/stderr | "SIEM will tail /var/log/axiom.log directly." | Don't log audit events to file; use structured events to SIEM. File logging is for operational logs (startup, errors), not audit trail. |
| Custom SIEM event format (Axiom-specific schema) | Forces SIEM operator to build custom parsers. | Use CEF (industry standard); CEF is understood by all SIEMs out of the box. |
| Batching events into single payload | Axiom buffers 100 events and sends once per minute. | Send each event immediately (fire-and-forget on separate thread); SIEM handles bursts. Single-event-per-POST is simpler and lower latency. |
| Two-way SIEM integration (SIEM tells Axiom to take action) | "SIEM detects attack and tells Axiom to revoke node." | Axiom is unaware of SIEM; SIEM is read-only consumer. If action needed, operator creates separate alert rule → triggers manual or external automation. |

### Dependencies on Existing Features

- **Audit Log Table**: Axiom already has `AuditLogEntry` in DB. Streaming is additive; existing audit log functionality unchanged.
- **Admin Config**: Syslog/webhook settings stored in `Config` table (key-value). Same pattern as notification webhooks (v16.0).
- **Background Worker**: Async task in lifespan sends events to SIEM. Same pattern as scheduled jobs.

### Feasibility: Homelab vs. Enterprise

| Context | Feasibility | Rationale |
|---------|-------------|-----------|
| **Homelab** | Low; Optional | Homelabs don't run SIEMs. ELK stack is overhead. Axiom's audit_log table is sufficient. |
| **Enterprise** | High; Table Stakes | Enterprise SIEM (Splunk, QRadar, Elastic) is standard. Axiom must integrate for compliance/forensics. |

### Implementation Notes

**CEF Event Format (Simple Example):**
```
CEF:0|Axiom|Axiom|1.0|JOB_DISPATCH|Job Dispatch|5|src=192.168.1.100 user=alice@example.com job_id=12345 job_name=db-backup job_status=COMPLETED target_nodes=node1,node2 msg=Job completed successfully
```

**Webhook Delivery (Async Background Task):**
```python
# In lifespan or APScheduler
async def stream_audit_events_to_siem():
    """Periodically fetch new audit events and POST to SIEM webhook."""
    webhook_url = config.get('AUDIT_WEBHOOK_URL')
    if not webhook_url:
        return
    
    last_sent_id = app.state.last_audit_event_id or 0
    new_events = db.query(AuditLogEntry).filter(AuditLogEntry.id > last_sent_id).all()
    
    for event in new_events:
        cef_payload = format_cef(event)
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.post(webhook_url, json=cef_payload, timeout=5.0)
                if resp.status_code == 200:
                    app.state.last_audit_event_id = event.id
        except Exception as e:
            logger.error(f"SIEM webhook failed: {e}")
            # Don't update last_audit_event_id; retry on next cycle
            break
```

---

## Feature 5: main.py Router Modularization

### Estimated Complexity
**Maintenance / Medium Risk (refactoring, not feature)**

### What It Does

Axiom's `main.py` currently contains all 89 FastAPI routes in a single 2500+ line file. Router modularization splits routes by domain:
- `routers/auth_router.py` — login, logout, token refresh
- `routers/jobs_router.py` — job dispatch, list, status
- `routers/nodes_router.py` — node list, detail, drain
- `routers/workflows_router.py` — workflow CRUD, execution
- `routers/admin_router.py` — users, roles, config
- `routers/system_router.py` — health, metrics, CRL
- `etc.`

Each router is an `APIRouter` registered in main.py via `app.include_router()`.

### Table Stakes

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Split routes into domain modules | Main file is >2500 lines; difficult to navigate | Low | No logic change; mechanical refactor. `APIRouter` handles registration. |
| Consistent import structure | All routers use same pattern for models, services, dependencies | Low | Establish conventions: `routers/{domain}_router.py` imports models from `models.py`, services from `services/`. |
| Preserve all existing API contracts | No route path changes; no request/response model changes | Low | Refactor is backward-compatible at API level. |
| Router-specific dependency injection | Each router can have its own Depends for auth, permissions, etc. | Low | FastAPI APIRouter supports route-level dependencies. |
| Test coverage preserved (no new test gaps) | Existing pytest suite continues to pass | Low–Med | Tests import routers directly or test via HTTP. No change to test patterns. |

### Differentiators

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Per-router version prefixes (/api/v1/jobs, /api/v2/jobs) | Allow parallel versions during migration. New clients use v2, old use v1. | High | Requires duplicating routes or wrapper logic. Complex if schemas differ. Defer to v25.0 if versioning is desired. |
| Per-router permission models (fine-grained RBAC) | Jobs router can enforce `jobs:read` + `jobs:write` separately; admin router can enforce `admin:*` | Med | Currently all permissions are flat (`users:write`, `jobs:write`). No change needed for v24.0; keep existing permission checks. |
| Auto-documented router groups in OpenAPI | Swagger UI groups routes by router (Jobs, Nodes, Admin tabs) | Low | FastAPI auto-groups by `tags` parameter. Routers already use tags; no extra work. |
| Router-specific rate limiting | Dispatch jobs limited to 10/min; node heartbeat unlimited | High | Requires per-router middleware; complex with async context. Defer to v25.0. |

### Anti-Features

| Anti-Feature | Why Avoid | What to Do Instead |
|--------------|-----------|-------------------|
| Circular imports between routers | Router A imports from Router B. | Routers import only from `models.py`, `services/`, and `security.py`. No cross-router imports. Keep dependency graph acyclic. |
| Moving business logic into routers | Routers become bloated with service layer code. | Keep routers thin; move logic to service layer. Router = input validation + auth + service call + response transform. |
| Router subpackages (routers/jobs/dispatch.py, routers/jobs/status.py) | Over-modularization; 50 tiny files instead of 10 med files. | Keep to 1 file per domain (jobs_router.py, not jobs/{dispatch,status,list}.py). |

### Safe Migration Path

**Phase 1 (Create new routers in parallel):**
```
# No changes to main.py yet
puppeteer/
  agent_service/
    main.py (original, no changes)
    routers/
      __init__.py (empty)
      auth_router.py (new)
      jobs_router.py (new)
      nodes_router.py (new)
      workflows_router.py (new)
      admin_router.py (new)
      system_router.py (new)
```

Routes defined in routers, but not yet included in main.py. Routers are tested in isolation via import.

**Phase 2 (Cutover routes one by one):**
```python
# main.py
from agent_service.routers import auth_router, jobs_router

app = FastAPI()

# Old: @app.get("/api/auth/me") is REMOVED
# New: auth_router has @router.get("/me")
app.include_router(auth_router.router, prefix="/api/auth", tags=["Auth"])

# Other routes still inline in main.py until migrated
@app.get("/api/jobs/list")  # ← OLD CODE, not yet migrated
async def list_jobs_old(...):
    ...
```

**Phase 3 (Deprecate old routes):**
```python
# main.py after all routers created
app.include_router(auth_router.router, prefix="/api/auth", tags=["Auth"])
app.include_router(jobs_router.router, prefix="/api/jobs", tags=["Jobs"])
app.include_router(nodes_router.router, prefix="/api/nodes", tags=["Nodes"])
# ... all routers included; main.py is now 200 lines (startup, lifespan, root routes)
```

**Risk Mitigation:**

1. **Test Coverage First**: Ensure full pytest coverage before refactoring. Use `pytest --cov` to identify untested paths.
2. **One Router Per PR**: Don't refactor all routers in one PR. Auth → Jobs → Nodes → etc. Easier to review and rollback.
3. **Route Name Stability**: Keep route paths and names identical. No `/api/auth/me` → `/api/auth/whoami` renames.
4. **Backward Compatibility**: If old endpoint is removed and new one added, provide deprecation warning or alias for 1–2 releases.

### Feasibility: When to Do This

| Timing | Rationale |
|--------|-----------|
| **Now (v24.0)** | Good: improves maintainability before adding Vault/TPM/Plugin features. Parallel router development is clean. |
| **Later (v25.0)** | Also acceptable: if v24.0 is time-constrained, defer this refactoring. Not a blocker for other features. |

### Implementation Estimate

- **Time**: 3–4 days (1 day per 20–25 routes)
- **Files Created**: 7 new routers + 1 `__init__.py`
- **Files Modified**: `main.py` (registration logic), `requirements.txt` (no change)
- **Test Changes**: Minimal; tests continue to import and call routes the same way
- **Risk**: Low if done incrementally; high if attempted all-at-once

---

## Feature Dependencies & Implementation Sequencing

```
Feature 1: Vault (External Secrets)
├─ Dependency: Encryption Key + JWT Secret must be retrievable
├─ Risk: Low
└─ Blocker for: Nothing (foundational)

Feature 2: TPM (Hardware Identity)
├─ Dependency: mTLS endpoint (/api/enroll) must exist (already exists)
├─ Risk: Medium (PCR baseline management complexity)
└─ Blocker for: Continuous attestation (if implemented)

Feature 3: Plugin System v2
├─ Dependency: Plugin API contract must be stable (new in v24.0)
├─ Risk: High (Python plugin trust model is novel for Axiom)
└─ Blocker for: Custom dispatchers, custom auditors

Feature 4: SIEM Audit Streaming
├─ Dependency: Audit log table must exist (already exists)
├─ Risk: Low
└─ Blocker for: Compliance workflows (downstream)

Feature 5: Router Refactoring
├─ Dependency: None (purely internal)
├─ Risk: Medium (mechanical but high-touch)
└─ Blocker for: Easier onboarding for future contributors
```

### Recommended Implementation Order (v24.0)

**Tier 1 (Primary, ship in v24.0):**
1. Router Refactoring (Week 1–2): Foundational cleanup that unblocks the rest
2. Vault Integration (Week 2–3): Enterprise requirement, low risk
3. SIEM Audit Streaming (Week 3): Builds on router structure, low risk

**Tier 2 (Secondary, defer to v24.1 or v25.0):**
4. TPM Identity (Week 4–5): High complexity, market-segment feature. Defer unless critical enterprise blocker.
5. Plugin System v2 (Week 5–6): Requires stable API contract. Defer to v25.0 to allow plugin ecosystem to mature.

**Rationale:**
- Tiers 1–3 are low-risk, high-value. Complete by v24.0 release.
- Tiers 4–5 are complex with operational overhead. Defer to allow separate research/design phases.

---

## MVP Recommendation

### v24.0 Scope (Focused Release)

**Build:**
1. Router refactoring (maintainability)
2. Vault integration (enterprise requirement)
3. SIEM audit streaming (compliance requirement)

**Defer:**
4. TPM identity (defer to v24.1; complex operational model)
5. Plugin System v2 (defer to v25.0; plugin ecosystem not ready)

**Rationale:**
- Tier 1–3 features deliver immediate value without architectural risk.
- Focus on hardening and operability (Vault + SIEM streaming) vs. new user-facing features.
- Defer complex infrastructure features (TPM) and extensibility (Plugins) to focused future releases.

---

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| **Vault Integration** | HIGH | AppRole is standard; KV v2 is well-documented. Low implementation risk. |
| **SIEM Streaming** | HIGH | CEF/syslog are industry standards. Webhook pattern is simple and proven. |
| **Router Refactoring** | MEDIUM | Mechanical refactoring is straightforward; risk is regression under high-touch changes. Mitigate with incremental PRs + full test coverage. |
| **TPM Identity** | MEDIUM | TPM 2.0 standards are stable; Keylime is reference. Complexity is in operational model (PCR baseline mgmt). Practical feasibility high for enrollment-only, complex for continuous attestation. |
| **Plugin System v2** | MEDIUM | Design pattern is clear (entry points, versioned API). Risk is in trust model (Python plugins can't be sandboxed). Feasible if plugins treated as trusted code. |

---

## Gaps to Address

- **TPM**: PCR baseline definition and management is not addressed in v24.0 scope. Requires operator runbook (Phase 25.0).
- **Plugins**: Plugin marketplace / third-party distribution model not addressed in v24.0. Requires vetting policy (Phase 25.0+).
- **Vault**: Dynamic secret rotation (automatic TTL refresh) deferred to v24.1. Startup-time fetch is v24.0 scope.
- **Router Refactoring**: API versioning (v1 vs v2 parallel routes) deferred to v25.0. Single version in v24.0.

---

## Sources

- [HashiCorp Vault AppRole Best Practices](https://developer.hashicorp.com/vault/docs/auth/approle/approle-pattern)
- [Vault KV v2 Secrets Engine](https://developer.hashicorp.com/vault/docs/secrets/kv/kv-v2)
- [Keylime TPM Agent-Driven Attestation](https://developers.redhat.com/articles/2026/04/08/agent-driven-attestation-how-keylimes-push-model-rethinks-remote-integrity)
- [Python Plugin Architecture Guide](https://mathieularose.com/plugin-architecture-in-python)
- [Common Event Format (CEF) — Splunk](https://www.splunk.com/en_us/blog/learn/common-event-format-cef.html)
- [Syslog Data Collection — Splunk](https://help.splunk.com/en/splunk-cloud-platform/get-started/splunk-validated-architectures/getting-data-in-forwarding-and-preprocessing/syslog-data-collection)
- [FastAPI Project Structuring with Routers](https://fastapi.tiangolo.com/tutorial/bigger-applications/)
- [Plugin Sandboxing with Firecracker/gVisor](https://northflank.com/blog/how-to-sandbox-ai-agents)
- [Azure SDK API Design Guidelines](https://azure.github.io/azure-sdk/python_design.html)
