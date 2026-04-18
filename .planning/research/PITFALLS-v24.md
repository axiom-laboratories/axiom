# Domain Pitfalls — Axiom v24.0

**Scope:** Five major v24.0 features: HashiCorp Vault, TPM-based identity, Plugin System v2, SIEM audit streaming, main.py router refactoring

**Researched:** 2026-04-18

**Overall Confidence:** MEDIUM-HIGH (production patterns clear; feature-specific pitfalls well-documented in operator and security communities)

---

## Critical Pitfalls

### Pitfall 1: Vault Secret Fetch Timeout Cascading to All Services

**What goes wrong:**
Orchestrator calls `vault.read('secret/data/encryption-key')` at startup, Vault is slow/down/unreachable. Orchestrator hangs for 30–60s waiting for response, blocking all service initialization. If Vault timeout is misconfigured (too low), random failures on startup.

**Why it happens:**
Vault network latency is not zero. If Vault is in a different region or behind a load balancer, TTL can exceed default HTTP timeout. No fallback logic in initial implementation.

**Consequences:**
- Orchestrator fails to start during Vault transient issues (network hiccup, Vault leader election)
- Rolling deploys hang (each replica waits for Vault)
- No graceful degradation: either Vault succeeds or startup fails hard

**Prevention:**
1. **Implement retry + backoff** in Vault client initialization:
   ```python
   max_retries = 3
   backoff = [1, 2, 5]  # seconds
   for attempt, delay in enumerate(backoff):
       try:
           vault_token = vault_client.auth.approle.login(...)
           break
       except VaultConnectionError as e:
           if attempt == len(backoff) - 1:
               raise  # Give up after 3 attempts
           time.sleep(delay)
   ```

2. **Set explicit timeout per Vault call** (not relying on system defaults):
   ```python
   vault_client = hvac.Client(url=VAULT_ADDR, timeout=5)  # 5s per call
   ```

3. **Document fallback semantics** clearly:
   - If Vault read fails after retries, log clearly and EITHER:
     - **Option A (recommended):** Fall back to env vars (require ENCRYPTION_KEY also in env as safety net)
     - **Option B:** Fail-fast on startup (require operator to provision Vault first)
   - Choose once, document in runbook

4. **Test startup sequence** with Vault unavailable:
   ```bash
   # Unit test: mock Vault client to timeout
   # Integration test: start orchestrator, kill Vault sidecar mid-startup, verify graceful fallback
   ```

**Detection:**
- Startup logs show "Vault connection timeout" recurring across restarts
- Orchestrator stuck in "Initializing..." state for >10s
- Vault server logs show no record of the failed read attempt (network-level timeout)

---

### Pitfall 2: TPM Measured Boot Baseline Drift on OS Patches

**What goes wrong:**
PCR (Platform Configuration Register) values are tight fingerprints of the boot chain: firmware version, bootloader, kernel, initramfs. An OS security patch (e.g., kernel update) changes initramfs content, which changes PCR value. Node previously attested successfully suddenly fails attestation with "PCR mismatch." Operator does not know why.

**Why it happens:**
Linux kernel patches (or security hotfixes) regenerate initramfs automatically. Firmware updates change firmware binary. Neither is visible to the operator in the runbook, but both invalidate PCR baselines.

**Consequences:**
- Node attestation fails after routine security updates
- Operator must manually re-baseline PCR values
- If auto-remediation is enabled (drain/revoke on attestation fail), nodes auto-drain unexpectedly
- Operational friction: "Do I trust this PCR change or is it a compromise?"

**Prevention:**
1. **Implement PCR baseline versioning** — allow multiple baselines per OS:
   ```python
   # Store baseline mapping
   {
       "ubuntu-24.04-kernel-6.8.0-45": {"pcr_0": "...", "pcr_1": "..."},
       "ubuntu-24.04-kernel-6.8.0-46": {"pcr_0": "...", "pcr_1": "..."},  # After patch
   }
   ```

2. **Soft-fail attestation on known-good baselines**:
   - If PCR matches ANY baseline version for this OS, pass
   - If PCR is new and unrecognized, log as WARNING (not FAILURE) and accept node
   - Operator reviews new baselines asynchronously via audit log

3. **Operator controls baseline update trigger**:
   - POST `/api/admin/register-attestation-baseline` — operator explicitly blesses a new baseline
   - Gated by `admin:write` permission
   - Audit log records who approved baseline change and timestamp
   - Do NOT auto-accept PCR changes

4. **Test baseline change scenarios**:
   ```bash
   # Test: node with kernel 6.8.0-45 -> reboot with 6.8.0-46
   # Expected: attestation warning, operator approves new baseline, node re-attests successfully
   ```

**Detection:**
- Audit log shows repeated "PCR mismatch" events after OS patch deployment
- Multiple nodes fail attestation simultaneously (indicates OS-level change, not node compromise)
- Operator runbooks for attestation troubleshooting mention "check for recent kernel updates"

---

### Pitfall 3: Plugin Import Cycles and Module Reload Chaos

**What goes wrong:**
Plugin A imports Plugin B. Plugin B imports a utility from the main Axiom namespace. Axiom upgrades and reloads that utility. Existing instances of Plugin B have stale references. Plugin A crashes because Plugin B is broken. Operator has no visibility into the transitive dependencies.

**Why it happens:**
Python `importlib.metadata` entry points load plugins at runtime. If plugins have circular or cross-plugin imports, module reloads (common in development) cause "module already imported" errors or stale reference bugs. No mechanism to validate plugin dependency chains before loading.

**Consequences:**
- Plugin load fails silently or with cryptic "module already imported" error
- Axiom continues to run but with degraded functionality (expected plugin didn't load)
- Operator does not notice until a workflow triggers the broken plugin
- Debugging is hard: import cycle is implicit in plugin code, not in config

**Prevention:**
1. **Enforce plugin isolation**: plugins cannot import from each other:
   ```python
   # In load_ee_plugins():
   if ep.value.split(':')[0] in LOADED_PLUGINS:
       raise PluginConflictError(f"Plugin {ep.name} imports {ep.value}, cross-plugin imports forbidden")
   ```

2. **Validate dependency chain at load time**:
   ```python
   # Each plugin declares its dependencies in __axiom_metadata__
   class MyPlugin(AxiomPlugin):
       __axiom_metadata__ = {
           "api_version": "2.0",
           "depends_on": ["job-dispatcher"],  # APIs it expects from Axiom
           "requires_plugins": [],  # Other plugins it depends on
       }
   
   # Loader validates that depends_on APIs exist in current Axiom version
   # If missing, raise PluginCompatibilityError at load time
   ```

3. **Forbid relative imports in plugins**:
   - Document: plugins must use absolute imports or import only from `axiom.sdk`
   - Add linter check in CI/CD: `grep "from \. import\|from \.\." <plugin_src> && exit 1`

4. **Plugin versioning contract**:
   - Each Axiom version publishes API contract (e.g., `axiom.api_version = "2.0"`)
   - Plugins declare `api_version` and must match or plugin fails to load
   - Allows plugins to opt-out of load if they're incompatible with new Axiom version

**Detection:**
- Startup logs show plugin load failure with "ModuleNotFoundError" or "circular import"
- Audit log shows repeated attempts to re-load same plugin
- Operator notices workflows hanging when they reach a step that needs the broken plugin

---

### Pitfall 4: SIEM Event Loss During Network Partition

**What goes wrong:**
Axiom sends audit events to SIEM via syslog/webhook. Network partition occurs (Axiom network → SIEM unreachable). Events are dropped silently. When network heals, no backlog is resent. SIEM audit trail has gaps. Operator does not know events were lost until forensic review.

**Why it happens:**
Syslog and webhooks are fire-and-forget by default. No retry logic, no persistent queue on the Axiom side. If SIEM is unreachable, send fails silently (or with a log message that gets lost in noise).

**Consequences:**
- Compliance violations: audit trail is incomplete
- Forensic investigation is impossible: attacker activity may be missing from SIEM
- Operator cannot detect the gap until auditing the audit log itself

**Prevention:**
1. **Implement event queue with persistence**:
   ```python
   # Events written to local SQLite queue before sending to SIEM
   # Background task drains queue every 5s
   class SIEMQueue:
       def enqueue(self, event):
           # Write to db.SIEMEventQueue table
           session.add(SIEMEventQueue(event_id=..., payload=..., status='PENDING'))
           session.commit()
       
       def drain(self):
           # Poll SIEM; on success, mark as 'SENT' and delete
           # On failure, retry up to 3 times with backoff
   ```

2. **Distinguish between transient and permanent failures**:
   - Transient (SIEM timeout, 5xx): retry 3 times with exponential backoff (1s, 2s, 5s)
   - Permanent (SIEM rejects event, invalid format): log and move on (do not retry forever)

3. **Alert operator to SIEM connectivity issues**:
   - If 100+ events queued and SIEM unreachable for >5min, emit health check alert
   - Dashboard shows "SIEM Connection: HEALTHY | WARNING | FAILED"

4. **Expose queue metrics**:
   - `GET /admin/siem-status` returns `{"pending_events": 42, "last_sent_at": ..., "last_error": ...}`
   - Prometheus metrics: `axiom_siem_queue_size`, `axiom_siem_send_errors_total`

**Detection:**
- `SELECT COUNT(*) FROM siem_event_queue WHERE status='PENDING'` shows accumulation
- Audit log shows audit events present but SIEM query for same time range is empty
- Operator notices SIEM dashboard has time gaps

---

### Pitfall 5: Router Refactoring Breaks Route Ordering and Dependency Injection

**What goes wrong:**
`main.py` currently has 89 routes. Refactoring splits them into 6 domain routers. Routes are included with `app.include_router(auth_router, prefix="/api/auth")`. But the ordering matters:
- Rate limit middleware must wrap all routes
- RBAC dependency injection must wrap job routes but not public routes
- Some routes override others (e.g., `GET /ws` vs `GET /ws/{id}`)

If included in wrong order, middleware does not apply correctly. Route precedence changes. Tests pass, but runtime behavior is broken.

**Why it happens:**
FastAPI processes routers in order. If a specific route is added after a catchall route, the catchall takes precedence. No compile-time validation that middleware wraps correctly. Easy to miss during refactoring.

**Consequences:**
- RBAC checks get skipped for some routes (security issue)
- Rate limiting does not apply to all routes (DoS vulnerability)
- Route parameter matching breaks unexpectedly (e.g., `/ws/details` vs `/ws?token=...`)
- Tests pass because test order is different from runtime order

**Prevention:**
1. **Explicit middleware wrapping in router order**:
   ```python
   # Document in code: router inclusion order is critical
   # MUST include before RBAC wrap:
   app.include_router(public_router)  # /login, /health, /metrics
   
   # All subsequent routers are RBAC-protected:
   app.include_router(auth_router, prefix="/api/auth", dependencies=[Depends(require_auth)])
   app.include_router(jobs_router, prefix="/api/jobs", dependencies=[Depends(require_auth)])
   ```

2. **Use route grouping tags for OpenAPI + for test verification**:
   ```python
   # Each router marks its routes with a tag
   @auth_router.get("/login", tags=["auth"])
   @jobs_router.get("/list", tags=["jobs"])
   
   # Test: verify all routes except /health, /login, /metrics require auth
   protected_tags = {"jobs", "nodes", "admin", "workflows"}
   unprotected_tags = {"public"}  # Only these should lack auth dependency
   ```

3. **Test route registration in integration tests**:
   ```python
   # Not just unit tests of individual route handlers
   # Integration test: start app, verify all routes exist and dependencies apply
   def test_route_coverage():
       routes = [r.path for r in app.routes]
       assert "/api/jobs/list" in routes
       assert "/api/auth/login" in routes
       # Verify auth dependency is attached to job routes
       job_routes = [r for r in app.routes if r.path.startswith("/api/jobs")]
       for route in job_routes:
           assert any(isinstance(d, Depends) for d in (route.dependencies or []))
   ```

4. **Use per-router prefix + explicit migration path**:
   ```python
   # Phase 1: Add new routers in parallel, keep old routes
   # OLD: app.get("/api/jobs/list") in main.py
   # NEW: @jobs_router.get("/list", prefix="/api/jobs") in jobs_router.py
   # Both work for a release cycle
   
   # Phase 2: Remove old routes
   # Keep new routers only
   
   # Phase 3: Remove router includes from main.py, move to separate module
   ```

**Detection:**
- Smoke test shows 403 Forbidden on previously-accessible routes
- Test coverage report shows previously-tested paths now unreachable (404)
- Middleware logs show "auth check skipped for route /api/jobs/list" (unexpected)

---

## Moderate Pitfalls

### Pitfall 6: Vault Secret ID Leakage in Logs

**What goes wrong:**
Vault configuration requires `VAULT_ROLE_ID` and `VAULT_SECRET_ID` as env vars. Orchestrator logs show full command line at startup: `python main.py`. If Vault client library logs auth attempt details, logs show Secret ID in plaintext.

**Why it happens:**
Vault client libraries (hvac) may log auth details for debugging. If logging level is DEBUG, full payloads are captured. logs get shipped to SIEM/ELK. SIEM archive is less protected than live systems.

**Consequences:**
- Secret ID captured in logs
- Attacker with read access to logs can authenticate as Axiom and read all Vault secrets
- Log retention policies may keep logs for 90+ days (extended exposure)

**Prevention:**
1. **Never log Vault credentials**:
   ```python
   # Filter logs before shipping to SIEM
   import logging
   class SecretIDFilter(logging.Filter):
       def filter(self, record):
           record.msg = record.msg.replace(os.getenv('VAULT_SECRET_ID'), '***')
           return True
   logging.getLogger('hvac').addFilter(SecretIDFilter())
   ```

2. **Use response-wrapped AppRole tokens instead of direct Secret ID**:
   - Vault issues a short-lived wrapper token containing the Secret ID
   - Wrapper token is one-time-use and expires quickly (1 hour)
   - Even if logged, token is useless after expiry

3. **Run Axiom with minimal logging in production**:
   - Set `LOG_LEVEL=INFO` (not DEBUG)
   - Ensure hvac client logging is set to WARN level

**Detection:**
- Search logs for "VAULT_SECRET_ID"
- Check hvac library log output for credential patterns

---

### Pitfall 7: TPM Quote Stale-ness and Replay Attacks

**What goes wrong:**
Node sends TPM quote to orchestrator. Orchestrator verifies quote is recent (timestamp check). But TPM does not have a network clock. Node's system time is wrong (10 minutes behind). Quote timestamp is old. Orchestrator rejects it as stale. Node fails attestation and cannot enroll.

Alternatively, attacker captures a valid quote and replays it later. Without a nonce (one-time random value), orchestrator accepts the old quote.

**Why it happens:**
TPM quotes include a timestamp but timestamp depends on node's system time. If node clock drifts (common in VMs), quote appears stale. No nonce binding means replay protection depends only on timestamp freshness check.

**Consequences:**
- Legitimate nodes fail attestation due to clock drift
- Attacker can replay old quotes if nonce is missing
- Operator has no way to force re-quote (no nonce).

**Prevention:**
1. **Use nonce-bound quotes** (TPM 2.0 standard feature):
   ```python
   # Orchestrator sends nonce to node
   nonce = secrets.token_bytes(32)
   # Node includes nonce in quote request
   quote = tpm.Quote(pcr_mask=..., nonce=nonce)
   # Orchestrator verifies nonce is present in quote
   # (Each quote can be bound to exactly one nonce, preventing replay)
   ```

2. **Implement clock skew tolerance** (not strict timestamp validation):
   ```python
   quote_timestamp = quote.timestamp
   current_time = time.time()
   max_skew = 5 * 60  # 5 minutes
   
   if abs(current_time - quote_timestamp) > max_skew:
       raise AttestationError(f"Quote too old: {current_time - quote_timestamp}s")
   ```

3. **Require NTP sync on nodes**:
   - Document: nodes must run ntpd or systemd-timesyncd
   - Node heartbeat includes system time; orchestrator compares to server time
   - If drift > 5min, health check warns "Clock skew detected"

**Detection:**
- Attestation fails with "quote timestamp too old"
- Node heartbeat shows `sys_time` out of sync with server

---

### Pitfall 8: Plugin Versioning and API Stability

**What goes wrong:**
Plugin A is written for Axiom 2.0 API. Axiom upgrades to 2.1 and changes the API (e.g., `Job` class constructor changes). Plugin A loads but crashes at runtime because Job constructor signature changed.

**Why it happens:**
Axiom API is not stable across minor versions. No semantic versioning contract is enforced. Plugins are external code, so they cannot be updated in lockstep with Axiom.

**Consequences:**
- Plugin breaks on Axiom upgrade
- Workflow using that plugin fails silently
- Operator has no warning that plugin is incompatible

**Prevention:**
1. **Publish stable API contract** with semantic versioning:
   ```python
   # Axiom publishes api_version as part of __version__
   AXIOM_API_VERSION = "2.0"  # Bumped on breaking changes only
   AXIOM_VERSION = "24.0.1"   # Semantic versioning
   ```

2. **Plugins declare required API version**:
   ```python
   class CustomAudit(AxiomPlugin):
       required_api_version = "2.0"  # Fails to load if Axiom is 3.0
   ```

3. **Define stable plugin interfaces** (ABC base classes):
   ```python
   from axiom.sdk import AxiomPlugin, JobExecution
   
   # These class signatures are guaranteed stable for version 2.x
   class AxiomPlugin(ABC):
       @abstractmethod
       def on_job_complete(self, execution: JobExecution):
           pass
   ```

4. **Test plugin backward compatibility** in CI/CD:
   - Build Axiom v24.0
   - Load plugins written for v23.0
   - Verify old plugins still work (or fail gracefully with clear error)

**Detection:**
- Startup logs show "PluginCompatibilityError: requires API v2.0, Axiom is v3.0"
- Workflows hang when reaching plugin step with no error message

---

### Pitfall 9: SIEM Event Batch Truncation and Loss

**What goes wrong:**
Axiom batch-sends audit events to SIEM to reduce network traffic: "send 100 events at once." If one event in the middle of the batch is malformed (oversized JSON), SIEM rejects the entire batch. All 100 events are lost.

**Why it happens:**
Syslog and webhook protocols have size limits (1024 bytes for UDP syslog). If batch payload exceeds limit, entire batch fails. No validation per-event before batching.

**Consequences:**
- 100 legitimate events lost because 1 was oversized
- SIEM audit trail has gaps
- Operator has no visibility into the loss

**Prevention:**
1. **Validate event size before queueing**:
   ```python
   def enqueue_event(event: AuditEvent):
       payload = json.dumps(event)
       max_size = 900  # 1024 - 124 (syslog header)
       if len(payload.encode()) > max_size:
           # Truncate event fields or split into multiple events
           event.script_output = event.script_output[:500]  # Truncate
       queue.add(event)
   ```

2. **Send per-event, not batched**:
   - Simpler to implement
   - If one event fails, only that event is lost (not 100)
   - Slight network overhead but acceptable for audit logs

3. **Implement event deduplication** at send time:
   - If same event sent twice, SIEM deduplicates on event_id
   - Guarantees at-least-once delivery

**Detection:**
- SIEM query for time range shows fewer events than Axiom audit_log table
- Oversized event in audit_log but not in SIEM

---

## Minor Pitfalls

### Pitfall 10: Router Import Cycle in Dependency Injection

When splitting routers, each router may import from `db.py`, `models.py`, `services/`. If a service imports a router, import cycle occurs: `main.py` -> `auth_router.py` -> `auth_service.py` -> `main.py`. Python detects cycle but leaves modules partially initialized.

**Prevention:** Routes should never import from main.py. Services can import routes' dependencies (models, db) but never routers themselves.

### Pitfall 11: SIEM Webhook Certificate Validation

If SIEM endpoint is HTTPS, Axiom must validate TLS certificate. If cert validation is disabled for testing and left in production code, attacker can MITM webhook events.

**Prevention:** Always validate TLS certs in production. Only skip validation in tests with explicit `verify=False` flag and a TODO comment.

### Pitfall 12: TPM Endorsement Key Revocation List (EKRL)

Manufacturers may revoke EKs (e.g., if firmware vulnerability discovered). Axiom must check EKRL before accepting node. If EKRL check is skipped, compromised nodes are accepted.

**Prevention:** Implement EKRL check in EK verification pipeline. If EKRL is unavailable, log warning but do not fail (assume EKRL mirrors may be down). Re-check asynchronously.

---

## Phase-Specific Warnings

| Phase/Feature | Likely Pitfall | Mitigation |
|---|---|---|
| **Vault Integration (Week 2–3)** | Secret fetch timeout cascading to startup | Implement retry + backoff + env var fallback; test with Vault down |
| **Vault Integration** | Secret ID leakage in logs | Use response-wrapped tokens; disable DEBUG logging in production |
| **TPM Enrollment (Week 4)** | PCR baseline drift after OS patches | Version baselines; allow multiple baseline versions per OS |
| **TPM Attestation (Week 5)** | Quote staleness and replay attacks | Bind quotes to nonces; enforce NTP sync on nodes |
| **Plugin System v2 (Week 5–6)** | Plugin import cycles and module reload | Forbid cross-plugin imports; validate dependency chains at load time |
| **Plugin System v2** | Plugin API stability | Define stable API contract; plugins declare required version |
| **SIEM Streaming (Week 3)** | Event loss during network partition | Persistent event queue; retry with backoff; expose metrics |
| **SIEM Streaming** | Batch truncation and loss | Send per-event; validate event size before queueing |
| **Router Refactoring (Week 1–2)** | Route ordering and middleware precedence | Explicit router inclusion order; integration tests for dependency wrapping |
| **Router Refactoring** | Import cycles in dependency injection | Routes never import from main.py; services only import models/db |

---

## Sources

### Vault Security & Operations
- [HashiCorp Vault Best Practices - Response Wrapping](https://www.vaultproject.io/docs/concepts/response-wrapping)
- [HashiCorp Vault AppRole Auth Method](https://www.vaultproject.io/docs/auth/approle)
- [hvac Python Client Logging and Debug](https://hvac.readthedocs.io/en/stable/)
- [Vault Secret ID Management and Rotation](https://www.vaultproject.io/docs/auth/approle#secret-id-management)

### TPM 2.0 and Attestation
- [Keylime Attestation Concepts](https://keylime.dev/docs/overview/)
- [TPM 2.0 PCR and Measured Boot](https://trustedcomputinggroup.org/wp-content/uploads/TCG_TPM2_Understanding_PCRs_r2-0-0.pdf)
- [NIST TPM 2.0 Implementation Recommendations](https://nvlpubs.nist.gov/nistpubs/SpecialPublications/NIST.SP.800-155.pdf)

### Python Plugin Architecture
- [importlib.metadata Entry Points](https://docs.python.org/3/library/importlib.metadata.html)
- [Pluggy Plugin Framework (pytest ecosystem)](https://pluggy.readthedocs.io/)
- [importlib Resources and Module Reloading](https://docs.python.org/3/library/importlib.html#importlib.reload)

### SIEM Log Streaming and Reliability
- [Splunk HTTP Event Collector with Retry Logic](https://docs.splunk.com/Documentation/Splunk/9.0.0/Data/UsetheHTTPEventCollector)
- [Syslog Protocol (RFC 5424) — Size Limits](https://tools.ietf.org/html/rfc5424)
- [CEF Format and Event Truncation](https://www.kstorb.nl/cef-format-and-compliance/)

### FastAPI Router and Middleware
- [FastAPI APIRouter and Dependencies](https://fastapi.tiangolo.com/tutorial/bigger-applications/)
- [Middleware Execution Order in FastAPI](https://fastapi.tiangolo.com/tutorial/middleware/)
- [Route Parameter Matching and Precedence](https://fastapi.tiangolo.com/tutorial/path-params/)

---

**Research Complete:** 2026-04-18

**Confidence Assessment:** MEDIUM-HIGH

All pitfalls derived from documented production patterns: Vault timeout cascades documented in operator communities; TPM baseline drift confirmed in Keylime project discussions; plugin import cycles are standard Python gotchas; SIEM event loss is known failure mode in log streaming; router refactoring risks align with FastAPI best practices. Axiom's existing architecture (mTLS, container isolation, RBAC) provides some mitigation for plugin trust and router dependency injection, reducing likelihood of critical failures. Testing strategy and validation patterns recommended above are standard in production Python systems.
