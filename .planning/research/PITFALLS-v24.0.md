# Domain Pitfalls: Axiom v24.0 Security Infrastructure & Extensibility

**Domain:** Adding HashiCorp Vault integration, TPM-based node identity, Plugin System v2 SDK, SIEM audit streaming, and main.py router modularization to a production job orchestration platform (64k+ LOC, mTLS+Ed25519-signed jobs, container-per-job isolation, CE/EE split via plugin mechanism)

**Researched:** 2026-04-18

**Confidence:** HIGH (production patterns established; implementation complexity higher for TPM/Plugin System, lower for Vault/SIEM/Router)

---

## Executive Summary

Axiom v24.0 introduces five architectural hardening features that collectively strengthen infrastructure foundation, extensibility, and observability. However, each feature introduces distinct pitfall categories:

1. **Vault integration** risks cascade failures on Vault unavailability, secret lease expiry during long-running jobs, and incomplete migration paths for legacy env-var secrets
2. **TPM-based identity** faces library availability challenges across OS variants, VM/container vTPM emulation limitations, and attestation token validation complexity
3. **Plugin System v2** introduces version conflict hazards, database access control risks, and supply-chain security gaps
4. **SIEM audit streaming** creates log flooding at scale, PII leakage in streaming, and delivery guarantee mismatches
5. **Router refactoring** risks circular import breakage, test fixture fragmentation, and CE/EE boundary drift during modularization

The recommended mitigation strategy is **phase gates with explicit validation**: Vault + SIEM + Router (Phase 1, low-risk foundation), followed by TPM (Phase 2, requires OS-specific validation), followed by Plugin SDK (Phase 3, requires security hardening). This ordering avoids five critical pitfalls identified in research: Vault hard startup dependency, TPM library availability across platforms, Plugin version conflicts, SIEM log flooding, and Router circular imports during CE/EE split.

---

## Critical Pitfalls

### Pitfall 1: Vault Hard Startup Dependency

**What goes wrong:**

Axiom configures critical secrets (ENCRYPTION_KEY, SECRET_KEY, DATABASE_URL) to be fetched from Vault at startup. If Vault is unavailable, unreachable, or returns authentication failure:

1. **Time 0:** `lifespan.on_startup()` calls `vault_service.bootstrap_secrets()`
2. **Time 1:** Vault connection fails (DNS timeout, 503, auth rejection)
3. **Time 2:** `bootstrap_secrets()` raises exception without fallback
4. **Time 3:** FastAPI lifespan fails; server never starts
5. **Time 4:** Orchestrator is offline; all nodes accumulate jobs in PENDING state

If operator misconfigures Role ID or Secret ID, or if the Vault token is revoked, the entire platform becomes inaccessible — even if env vars are still present on disk.

**Why it happens:**

- Vault integration is implemented as a **mandatory startup check**, not optional
- No fallback to environment variables if Vault is unavailable (either/or design)
- Lease renewal logic is asynchronous (background task) but bootstrap is synchronous (blocking startup)
- Operator assumes Vault availability is guaranteed; single points of failure are not documented

**Consequences:**

- Unplanned Vault maintenance (patching, reboot) cascades to Axiom downtime
- Certificate rotation in Vault (AppRole secret rotation) requires coordinated restart
- Air-gapped deployments forced to run local Vault instance (added operational complexity)
- Multi-region deployments with different Vault clusters face eventual-consistency issues
- Disaster recovery scenario: Vault lost; no way to bootstrap Axiom without restore

**Prevention:**

1. **Grace period fallback** — If Vault bootstrap fails, fall back to environment variables and log WARN. Set grace_period_seconds=300 config; if Vault unavailable for >300s, demote to degraded mode (read-only, warn banner).

2. **Startup fence** — Make Vault optional via `VAULT_ENABLED=false` env var. Operators explicitly enable it; bootstrap failure is a startup error not a crash.

3. **Health check endpoint** — Add `GET /health/vault` returning {status: "connected" | "degraded" | "offline", last_lease_renewal: timestamp, next_renewal: timestamp}. Dashboard alerts on OFFLINE.

4. **Lease renewal isolation** — Separate lease renewal (background task) from initial bootstrap (startup hook). Bootstrap fetches secrets, renewal maintains leases asynchronously. If renewal fails 3x consecutively, alert but do not crash.

5. **Secret caching with TTL** — Cache secrets locally for grace_period (e.g., 24h). If Vault unavailable, use cached secrets if within TTL, fall back to env vars if cache expired. Operator configures acceptable cache age.

6. **Explicit secret fallback order** — Document: Vault > environment variables > defaults (if applicable). Log which source was used for each secret.

**Detection:**

- Alert on Vault bootstrap failures in startup logs
- Monitor lease renewal success rate; if <95% over 10 minutes, escalate
- Track secret fetch latency; if bootstrap takes >10s, log slow dependency
- Audit trail: log each secret source (Vault vs env var vs cache)

**Phase to address:** Phase 1 (must be production-ready before shipping any Vault feature)

---

### Pitfall 2: Secret Lease Expiry During Long-Running Jobs

**What goes wrong:**

Vault KV v2 secrets have optional lease durations. If a job runs longer than the lease TTL, the secret becomes invalid mid-execution:

1. Job A starts at 10:00 AM, requests encrypted connection string from Vault (lease TTL 1 hour)
2. Job A is long-running: downloads 50GB of data, runs for 2 hours
3. At 11:00 AM, SECRET_KEY lease expires in Vault
4. At 11:15 AM, orchestrator tries to decrypt a log entry → AES-128 decryption fails → log lost
5. At 12:00 PM, job A completes, but encrypted audit trail is partially corrupted

Separately, if AppRole Secret ID rotates (a security best practice), and the orchestrator doesn't refresh it, subsequent lease renewals fail. Leases can't be renewed with expired Secret ID.

**Why it happens:**

- Lease management is orchestrator-level, not job-level
- Long-running jobs (data pipelines, backups) commonly exceed 1-hour TTLs
- Vault secret rotation is a periodic operation, not synchronized with job lifecycle
- AppRole Secret ID rotation (best practice) happens on a schedule independent of job duration
- Axiom doesn't validate lease TTL vs expected job duration at dispatch time

**Consequences:**

- Encrypted audit logs become partially unreadable after 1+ hour
- Compliance violations: audit trail integrity compromised
- Data pipeline failures mid-execution (hard to debug — "decryption failed" with no context)
- Orphaned long-running jobs (can't complete because secrets unavailable)
- Operational hazard: operator must restart orchestrator to renew AppRole Secret ID

**Prevention:**

1. **Lease TTL validation at dispatch** — When job is submitted, check expected runtime vs SECRET_KEY lease TTL. If runtime > TTL, warn in dispatch response; optionally reject if TTL < 2× expected runtime.

2. **Lease renewal before expiry** — Implement active lease renewal with 30% safety margin. If lease TTL is 1 hour, renew at 36-minute mark (before expiry). Background task runs every 5 minutes, renews any leases within 20% of expiry.

3. **AppRole Secret ID pre-rotation** — Store primary + standby Secret IDs in Vault. Rotate standby Secret ID weekly; every 2 weeks, make standby the primary. Orchestrator tries primary, falls back to standby if auth fails. No downtime during rotation.

4. **Per-job secret scope** — If supported by Vault, use per-job AppRole or short-lived tokens with job-specific permissions. Token expires when job completes; cannot be misused after job lifetime.

5. **Transparent credential refresh** — For long-running jobs, implement mid-execution secret refresh. Every N minutes (e.g., every 5 min), refresh ENCRYPTION_KEY from Vault. If refresh fails, log error but continue (use cached key for next window).

6. **Lease TTL visibility** — Add `lease_ttl_remaining_seconds` to health check endpoint. Dashboard shows time until next required action.

**Detection:**

- Log every lease renewal attempt with success/failure status
- Alert if lease renewal success rate drops below 95%
- Monitor job duration vs SECRET_KEY TTL; warn if job.expected_runtime > TTL × 0.8
- Audit trail: flag jobs that encountered mid-execution secret unavailability
- AES decryption failures should log secret source + remaining lease time

**Phase to address:** Phase 1 (Vault integration phase)

---

### Pitfall 3: Secret Rotation Breaking Long-Lived Job Scripts

**What goes wrong:**

A job script embeds a secret at creation time (e.g., an API token for an external service). The secret is fetched from Vault and embedded in the script for execution on a remote node:

1. Operator creates job "fetch-from-external-api" with embedded secret: `curl https://api.example.com -H "Authorization: Bearer ${API_TOKEN}"`
2. Job is signed with Ed25519 and saved in job library
3. Vault secret for API_TOKEN is rotated for security compliance
4. Job is later re-executed (resubmit, or as part of a workflow)
5. At runtime, node executes script with **old embedded secret** (script hasn't changed, so signature is still valid)
6. External API rejects the request (old token); job fails with cryptic "401 Unauthorized"

The operator is confused: script looks correct, signature verifies, but job fails. No clear indication that the embedded secret is stale.

**Why it happens:**

- Vault integration suggests "fetch secrets at runtime," but historical job scripts embed secrets at creation time
- Script signing (Ed25519) makes it immutable; rotation of underlying Vault secret does not invalidate the signature
- Job library (saved jobs, scheduled jobs) may contain hundreds of scripts; audit trail doesn't track which use which secrets
- No clear guidance on secret lifecycle vs script lifecycle

**Consequences:**

- Historical jobs fail unexpectedly after Vault secret rotation
- Operators must re-sign all dependent jobs after secret rotation (operational burden)
- Audit trail gaps: job failure lacks context ("which secret is missing?")
- Scheduled jobs silently fail after rotation (no visible cause)
- Long-term workflows or recurring tasks break without warning

**Prevention:**

1. **Don't embed secrets in scripts** — Instead, use Vault-backed environment variables. Script references `$SECRET_NAME`, node fetches from Vault at runtime (or from orchestrator-provided secrets in the Job payload).

2. **Secrets table in Job model** — Add Job.secret_references (list of {vault_key, env_var_name}). Script uses env var; orchestrator fetches secret from Vault and injects before node execution.

3. **Secret dependency audit** — Maintain a `JobSecretDependency` table (job_guid, vault_key, version_at_creation). When Vault secret rotates, query this table to identify affected jobs. Alert operator with list of jobs requiring re-sign.

4. **Job validation on secret rotation** — When Vault secret is rotated, validate all dependent jobs. If validation fails, mark job with `requires_resign=True` in audit trail.

5. **Runtime secret fetch** — Nodes fetch secrets from orchestrator's `/api/node/secret/{key}` endpoint (mTLS authenticated). Orchestrator proxies to Vault, logs fetch, validates ACL. Secrets never embedded in signed script.

6. **Clear documentation** — Document: "Embed secrets → immutable; secret rotation breaks job. Use env vars → flexible; secret rotation transparent to job."

**Detection:**

- Audit trail: log when a job is created with embedded secret; flag as "legacy pattern"
- Monitor job failures with "401 Unauthorized" or "403 Forbidden" errors; correlate with recent Vault rotations
- Script analyzer: detect `curl ... -H "Authorization: Bearer ${...}"` patterns; suggest migration to env var
- Alert on jobs marked with `requires_resign=True` persisting >7 days

**Phase to address:** Phase 1 (Vault feature) — document secret lifecycle clearly

---

### Pitfall 4: Fernet Migration Path Incomplete

**What goes wrong:**

Axiom currently encrypts secrets at rest using Fernet (AES-128 in CBC mode). When Vault integration is added, a migration is needed: existing secrets (in Config table, User model, etc.) must be re-encrypted with a Vault-backed key, or decrypted and migrated.

1. **Old deployment:** ENCRYPTION_KEY in `.env`, Fernet-encrypted secrets in DB
2. **Upgrade to v24.0:** Migration script should decrypt with old key, re-encrypt or store in Vault
3. **Missing migration:** Script not written; old encrypted secrets left in place
4. **At runtime:** Code tries to use Vault-fetched key to decrypt old Fernet ciphertexts → decryption fails
5. **Result:** User passwords, API keys, etc. become inaccessible

Alternatively, if migration decrypts old secrets and re-encrypts with new key, operator must coordinate rotating ENCRYPTION_KEY atomically. If ENCRYPTION_KEY changes mid-operation, partially-encrypted DB becomes corrupt.

**Why it happens:**

- Two separate key-derivation paths: legacy (Fernet from ENCRYPTION_KEY env var) and new (Vault-sourced key)
- Migration is optional / deferred in release notes; not mandatory at startup
- No validation that all secrets are decryptable with current key; silent failures possible
- Operator assumes old secrets "just work" with new Vault-backed encryption

**Consequences:**

- User credentials become inaccessible after upgrade (password resets required for all users)
- Service principal API keys lost (operators must regenerate)
- Encrypted audit logs unreadable (compliance violations)
- Rollback impossible: old key gone, new key in Vault, DB in inconsistent state

**Prevention:**

1. **Explicit migration at startup** — If deploying v24.0 for the first time on existing DB, add startup check: count secrets encrypted with old Fernet key. If count > 0, require explicit `--migrate-secrets` flag or fail startup with clear error message.

2. **Dual-key period** — For 1-2 releases, support both old (Fernet) and new (Vault) keys. At startup, old secrets use old key; new secrets use Vault. Provide `POST /admin/reencrypt-secrets` endpoint (async job) to re-encrypt all old secrets with new key. Must complete before Vault becomes mandatory.

3. **Migration testing** — Include in test suite: decrypt old Fernet secrets with legacy key, re-encrypt with new key, verify decryption with new key succeeds.

4. **Backup before migration** — Document: operator must backup `jobs.db` before upgrade. If migration fails, restore and retry with explicit rollback flag.

5. **Key derivation isolation** — Create separate encryption contexts: `FernetContext(legacy_key)` and `VaultContext(vault_key)`. DB schema includes encryption_context field; query layer routes to appropriate context.

6. **Audit logging** — Log every secret decryption/re-encryption with source key + destination key. If a secret fails migration, log explicitly with secret identifier.

**Detection:**

- Alert on decryption failures in logs (indicates key mismatch)
- Startup warning: "Found N secrets encrypted with legacy key; migration required"
- Audit trail: track re-encryption progress (X of Y secrets migrated)
- Health check: `GET /health/secrets` returns {migrated_count, remaining_count}

**Phase to address:** Phase 1 (must be completed before Vault becomes optional)

---

### Pitfall 5: TPM Library Availability Across OS Variants

**What goes wrong:**

TPM-based node identity requires accessing the TPM 2.0 device (`/dev/tpm0` on Linux, `//./TPM20:` on Windows) and using cryptographic libraries to parse TPM responses. The libraries (`pyasn1`, `pycryptodome`, `tpm2-tools`, `tpm2-abrmd`) are not in the base image and may not be available for all OS variants.

1. **Debian/Ubuntu:** `tpm2-tools` available in APT; `pyasn1` on PyPI; setup straightforward
2. **Alpine:** `tpm2-tools` available in APK; but `tpm2-abrmd` (daemon) not available; requires compilation from source or workaround
3. **ARM64 (Raspberry Pi):** `tpm2-tools` available; but hardware TPM drivers may not be compatible (driver depends on specific TPM vendor)
4. **vTPM in VM:** `tpm2-tools` available; but QEMU vTPM support is fragile (requires KVM + host TPM sharing or swtpm emulator)
5. **Containers:** `/dev/tpm0` not available in container unless volume-mounted from host; attestation quotas cannot be generated without hardware TPM

Result: Node fails to bootstrap if TPM libraries are missing or incompatible. If fallback to non-TPM identity is not available, node becomes unavailable.

**Why it happens:**

- TPM library availability is fragmented across distributions
- vTPM emulation (swtpm) is not widely available in standard container images
- Attestation logic assumes TPM access; no graceful degradation if TPM unavailable
- Multi-platform builds (Alpine, Debian, ARM64, amd64) need per-platform testing

**Consequences:**

- Node enrollment fails on Alpine (common in homelab/edge deployments)
- Raspberry Pi deployments fail (no ARM64 TPM driver support)
- VM deployments fail if vTPM not configured (requires host admin setup)
- Container deployments require `/dev/tpm0` volume mount (operational complexity)
- Disaster: operator provisions node on unsupported OS; 1 hour wasted troubleshooting "TPM not found"

**Prevention:**

1. **OS matrix + support tier** — Document supported OS/architecture combinations: {Debian 12 (amd64, ARM64), Alpine (amd64 only), Ubuntu 24.04 (amd64, ARM64), Windows Server 2022, vTPM (Linux KVM + swtpm)}. Mark unsupported combinations (Alpine ARM64) as "not recommended."

2. **Graceful degradation** — If TPM not available, fall back to non-TPM identity (e.g., Ed25519 public key issued by orchestrator). Log WARN and continue. If TPM availability is required, add `REQUIRE_TPM=true` env var; startup fails explicitly if TPM not found.

3. **TPM detection at build time** — Dockerfile includes TPM library setup:
   ```dockerfile
   RUN if [ "$OS_VARIANT" = "alpine" ]; then \
         apk add --no-cache tpm2-tools && \
         (which tpm2-getcap || echo "TPM unavailable on this Alpine build" > /tmp/tpm-warning.txt); \
       else \
         apt-get install -y tpm2-tools; \
       fi
   ```

4. **vTPM emulator support** — For VM deployments, provide optional `tpm2-abrmd` + `swtpm` sidecar in compose file. Document: `docker-compose -f compose.yaml -f compose.vtpm.yaml up`.

5. **Per-platform wheels** — Build Python wheels with pre-compiled TPM bindings for each OS/arch combo. Avoid compilation at runtime; fail fast if wheel not available.

6. **Attestation optional in v24** — Ship v24 with TPM enrollment only (persist public key, no attestation). Defer attestation verification to v25.0, after OS support matrix is validated.

**Detection:**

- Node startup logs: explicitly log "TPM not found; using fallback identity"
- Health check: `GET /health/node` returns {tpm_available: true/false, identity_method: "tpm" | "fallback"}
- Orchestrator audit log: track which nodes use TPM vs fallback identity
- Alert if >20% of nodes fall back to non-TPM (indicates OS/platform issue)

**Phase to address:** Phase 2 (TPM enrollment; defer attestation to v25)

---

### Pitfall 6: TPM Attestation Quote Validation Complexity

**What goes wrong:**

TPM attestation is complex: node generates an attestation quote (signed by TPM private key), orchestrator validates the quote signature, verifies PCR measurements (hardware state), and confirms quote was generated by trusted TPM. If validation is incomplete or incorrect:

1. Node requests attestation quote; TPM signs it with private key
2. Orchestrator receives quote + signature; validates quote was signed by that TPM
3. Validator checks PCR-0 (BIOS firmware), PCR-4 (bootloader), PCR-7 (secure boot state)
4. **Bug:** Validator doesn't check quote timestamp; accepts quotes from 2 days ago
5. Attacker compromises node 2 days ago, replays old attestation quote
6. Orchestrator approves node as "trustworthy"; attacker gets job access

Or: validator checks PCR values, but doesn't establish what PCR values should be for "known good" state. No audit trail of expected-vs-actual PCR values.

**Why it happens:**

- TPM attestation is cryptographically complex (ECC signatures, quote structures, PCR encoding)
- Validation logic has many independent checks; missing one invalidates the entire guarantee
- "Known good" PCR state is image-specific; reference values must be computed at build time and stored
- Testing requires physical TPM or vTPM emulator; easy to miss edge cases
- NIST/CIS guidance on TPM validation is dense; easy to misunderstand

**Consequences:**

- Attacker can replay old attestation quotes and impersonate trusted nodes
- Compromised firmware undetectable if PCR values not validated
- Audit trail lacks context for "why was node approved/rejected"
- Compliance violations: attestation not actually trusted (looks good on paper, ineffective in practice)

**Prevention:**

1. **Attestation deferral** — v24 ships TPM enrollment (identity) only; defer full attestation + PCR validation to v25. Build reference PCR values in v24, use in v25.

2. **Quote timestamp validation** — Every attestation quote includes a timestamp (TPMS_TIME_INFO). Validator rejects quotes older than 5 minutes. Prevents replay attacks.

3. **Reference PCR database** — At image build time, compute reference PCR values (BIOS + bootloader + secure boot + Axiom components). Store in DB with image version. At attestation, compare actual vs reference; alert on mismatch.

4. **Incremental validation** — Implement in phases:
   - Phase 1: Validate TPM signature on quote (cryptographic trust)
   - Phase 2: Validate quote timestamp (freshness)
   - Phase 3: Compare PCR-0, PCR-4, PCR-7 to reference values (firmware integrity)
   - Phase 4: Validate quote nonce (challenge-response to prevent pre-generation)

5. **Nonce in attestation requests** — Orchestrator sends random nonce; expects nonce echoed in attestation quote. Prevents attacker from pre-generating valid quotes.

6. **Detailed audit trail** — Log for each attestation request:
   ```
   {node_id, nonce, received_at, quote_timestamp, pcr_values, expected_pcr_values, validation_passed}
   ```
   Alert if validation fails; require operator review before node is trusted again.

**Detection:**

- Alert on attestation validation failures (quote timestamp too old, PCR mismatch, signature invalid)
- Monitor PCR value changes; if a node's PCR-0 (BIOS) changes unexpectedly, isolate node pending investigation
- Audit trail: flag nodes with repeated attestation failures
- Periodically (e.g., weekly) re-attest all nodes; alert if any fail

**Phase to address:** Phase 3 (v24 = enrollment only, v25 = full attestation)

---

### Pitfall 7: Plugin Version Conflicts and Dependency Hell

**What goes wrong:**

Axiom implements Plugin System v2 via `importlib.metadata.entry_points()`. Third-party plugins declare dependencies in their `setup.py` or `pyproject.toml`. If two plugins depend on different versions of the same library, Python's package manager cannot satisfy both:

1. Plugin A requires `requests==2.28.0` (security patch for Cookie bomb DoS)
2. Plugin B requires `requests==2.26.0` (last version it was tested against)
3. Operator runs `pip install axiom-plugin-a axiom-plugin-b`
4. pip cannot satisfy both constraints; fails with "Conflicting requirements"
5. Or: pip picks one version (e.g., 2.28.0); Plugin B breaks at runtime with "AttributeError: Response object has no attribute X"

Additionally, if Plugin A is updated to v2.0 with breaking changes, and a scheduled job still loads Plugin A v1.0 from cache, at runtime the plugin interface mismatches.

**Why it happens:**

- Plugins are loaded dynamically via entry points; dependency resolution happens at pip install time, not at Axiom startup
- No plugin API versioning; plugins declare dependencies but not minimum/maximum Axiom version
- Plugin ecosystem is decentralized; no central registry ensuring compatibility
- Tests run plugins individually; integration testing of multiple plugins + dependencies is skipped

**Consequences:**

- Operator cannot install two desired plugins simultaneously (version conflict)
- Silent plugin failures: wrong version loaded, plugin interface mismatches
- Scheduled jobs refer to plugin by name (e.g., `plugin_id="my-aggregator"`); if plugin version changes, behavior changes unexpectedly
- Dependency downgrades for plugin compatibility cascade to other modules (e.g., downgrading requests affects web client code)

**Prevention:**

1. **Plugin API versioning** — Define Axiom Plugin API version (e.g., v1, v2). Plugins declare `axiom_api_version="1"` in entry point metadata. Axiom rejects plugins with unsupported API versions at load time.

2. **Version pinning in plugins** — Plugins declare dependency constraints narrowly: `requests>=2.28.0,<3.0` (not `requests==2.28.0`). Allow patch updates, block major version changes.

3. **Dependency conflict detection** — At Axiom startup, query installed plugins' dependencies. Compare against installed packages; if conflict detected, raise RuntimeError with explicit list of conflicting packages and versions.

4. **Plugin isolation via containers** — Run each plugin in a separate Docker container (throwaway per job). Plugin A's `requests==2.28.0` in container A; Plugin B's `requests==2.26.0` in container B. No version conflict.

5. **Plugin registry + compatibility matrix** — Maintain (operator-facing) compatibility matrix:
   ```
   Plugin A v2.0 → Axiom v24.0+
   Plugin A v1.5 → Axiom v23.0+
   Plugin B v1.0 → Axiom v24.0+
   ```
   Operator checks before installing.

6. **Per-plugin venv** — Create isolated virtual environment per plugin (e.g., `/var/lib/axiom/plugins/my-plugin/venv`). Each plugin has its own installed packages, no cross-plugin version conflicts. (Trade-off: higher disk usage, startup latency.)

**Detection:**

- Startup check: load all plugins, log versions and dependencies
- Alert if plugin API version mismatches Axiom version
- Audit trail: log which plugin version was loaded for each job
- Monitor job failures from plugin-related errors (module import fails, interface mismatch)

**Phase to address:** Phase 3 (Plugin SDK v2) — implement version matrix + compatibility gating

---

### Pitfall 8: Plugin Database Access Security

**What goes wrong:**

Plugins need to access Axiom data (e.g., audit logs, job history) to implement features. A naive approach gives plugins direct database access (SQLAlchemy session). A malicious or buggy plugin can:

1. Exfiltrate all user passwords from User table
2. Modify audit log to hide evidence of attacks
3. Access secrets in Config table
4. Lock database with long-running transaction (DoS)

Or: Two plugins access the same database row concurrently; transaction isolation fails; data corrupts.

**Why it happens:**

- Plugins are loaded as trusted code (like Docker daemon plugins)
- Plugin sandbox is weak (running in same Python process as Axiom core)
- Plugin access pattern is similar to API endpoints (query, read, maybe write)
- No capability-based access control; plugins get all-or-nothing DB access
- Testing plugins individually; concurrent plugin + core access not tested

**Consequences:**

- Confidentiality violation: plugins exfiltrate user data
- Integrity violation: plugins modify audit logs
- Availability violation: plugins lock database (DoS)
- Malware risk: plugin updates can be compromised in supply chain

**Prevention:**

1. **Read-only plugin API** — Plugins don't access database directly. Instead, expose a read-only API (`async def get_job_history(job_id, limit=100)`, `async def get_audit_log(filters)`). Axiom core mediates all queries.

2. **Capability-based access** — Plugins declare required capabilities at load time (e.g., `capabilities=["read:job_history", "read:audit_log"]`). Axiom grants only declared capabilities. Attempt to access undeclared capability raises PermissionError.

3. **Data filtering** — API filters sensitive fields (e.g., `get_user(id)` returns {id, name, email, role} but NOT {password_hash, api_keys}). Plugin cannot access secrets even if database is open.

4. **Query isolation** — Plugin queries run in a separate database connection pool with aggressive timeouts (60s max query time). Long-running queries are auto-cancelled; deadlocks don't cascade to core.

5. **Audit logging for plugins** — Every API call from plugin is logged with plugin name + call + result. If plugin tries to access unauthorized data, log with security level WARNING.

6. **Plugin sandboxing** — (Optional for v24; consider v25) Run plugins in separate processes (using multiprocessing module + RPC) instead of in-process. Plugin cannot access Axiom memory directly.

**Detection:**

- Audit trail: log all plugin API calls with parameters
- Alert if plugin attempts capability it doesn't declare
- Monitor query performance; if plugin queries take >60s, kill query and alert
- Periodically audit plugin capabilities vs actual usage; flag plugins over-privileged

**Phase to address:** Phase 3 (Plugin SDK v2) — implement read-only API + capability gating

---

### Pitfall 9: SIEM Log Flooding at High Throughput

**What goes wrong:**

SIEM streaming sends audit log events to external SIEM (e.g., Splunk, ELK) via webhook or syslog. At high throughput (>500 jobs/min, >1000 audit events/min), the streaming service can overwhelm the SIEM with unbuffered events:

1. Job A completes; audit event fired: 1 webhook POST
2. Job B completes; audit event fired: 1 webhook POST
3. ... (500 jobs/min = ~8 webhook POSTs per second)
4. **Scenario 1:** Axiom sends unbuffered → SIEM receives 8 requests/sec → queue backs up → SIEM drops events (data loss)
5. **Scenario 2:** Axiom sends unbuffered → Network congestion → POST timeouts → Axiom retries → duplicate events sent → SIEM deduplicates but logs bloat

**Why it happens:**

- Naïve implementation sends webhook immediately on each event (synchronous)
- No batching; each audit event = 1 HTTP request
- SIEM has limited webhook throughput (often <100 req/sec; processing each event takes 10-100ms)
- Operator doesn't tune batch size / flush interval for their scale

**Consequences:**

- SIEM data loss: real events dropped when queue full
- Audit trail gaps: attack evidence missing from SIEM
- Network saturation: 8 requests/sec × 200 bytes per request = 1.6 Mbps sustained (unacceptable on limited links)
- SIEM query latency degradation (overloaded SIEM affects other teams)
- Compliance violations: "audit logs were sent to SIEM" is not true if SIEM drops them

**Prevention:**

1. **Batch and flush** — Collect audit events in memory; flush every N events or every T seconds (e.g., 100 events or 5 seconds). Reduces webhook requests by 100x.

2. **Buffering with backpressure** — Use asyncio.Queue (max_size=10000). If queue fills, log WARNING and drop oldest events (acceptable loss vs blocking core). Monitor queue depth; alert if consistently >50%.

3. **Configurable flush strategy** — Add env vars:
   ```
   SIEM_BATCH_SIZE=100 (events per batch)
   SIEM_FLUSH_INTERVAL=5 (seconds)
   SIEM_MAX_QUEUE_SIZE=10000 (events)
   ```
   Operator tunes for their scale.

4. **Compression** — Compress batch payload (gzip) before sending. 1000 events in JSON = ~100KB; gzipped = ~10KB. Reduces network load 10x.

5. **At-least-once delivery** — Track which batches were sent. If webhook fails, retry indefinitely (with exponential backoff). Store undelivered batches to disk if queue fills.

6. **SIEM acknowledgment** — SIEM responds with `X-Received-Batch-ID: <id>`. Axiom tracks confirmed deliveries. Alert if SIEM is not acknowledging (indicates SIEM lag or failure).

**Detection:**

- Monitor SIEM queue depth; alert if >50% of SIEM_MAX_QUEUE_SIZE
- Track webhook POST latency; if >1s per batch, alert (SIEM is slow)
- Audit trail: log batch-level stats (events_sent, batch_size, delivery_time)
- Monitor job dispatch rate vs SIEM delivery rate; alert if SIEM can't keep up (>2min lag)

**Phase to address:** Phase 1 (SIEM integration) — implement batching from day 1

---

### Pitfall 10: SIEM PII Leakage in Audit Streams

**What goes wrong:**

Audit logs contain sensitive information: user emails, API key snippets, job script content (which may include inline secrets), node IP addresses. If SIEM has weaker access controls than Axiom, or if SIEM is shared with other teams, PII is exposed:

1. Job submitted by user alice@company.com; audit log records submitter
2. Audit event streamed to shared Splunk instance (visible to security team + ops team)
3. Ops team member searches Splunk; sees alice's email, job script, node IPs
4. GDPR violation: PII exposed to unnecessary audience

Additionally, if SIEM webhook is intercepted (e.g., MITM on internal network), attacker can see full audit event payloads.

**Why it happens:**

- Audit logs are designed for operators (full visibility); SIEM audit logs are designed for compliance (minimal PII)
- No data masking layer; same event is sent to both Axiom operators (full) and SIEM (masked)
- SIEM webhook URL may be on internal network (not encrypted end-to-end)
- Operator doesn't consider SIEM audience when sending audit events

**Consequences:**

- PII exposure: user emails, job scripts visible in SIEM
- Compliance violations: GDPR, HIPAA, SOC 2 (audit logs with unmasked PII)
- Competitive harm: job scripts (proprietary processing logic) visible to broader team
- Attack surface: PII in SIEM can be stolen; stolen emails enable phishing

**Prevention:**

1. **Audit event masking** — Create two event types:
   - **Full audit event** (Axiom operators): all details
   - **Masked audit event** (SIEM): PII redacted
   ```python
   def mask_for_siem(event):
       event.created_by = mask_email(event.created_by)
       event.target_email = mask_email(event.target_email)
       event.script_content = "[REDACTED]" if confidential else event.script_content
       event.node_ip = mask_ip(event.node_ip)
       return event
   ```

2. **Configurable masking rules** — Add policy (operator-facing):
   ```
   SIEM_MASK_EMAILS=true
   SIEM_MASK_IPS=true
   SIEM_MASK_SCRIPT_CONTENT=true
   SIEM_ALLOWED_SCRIPT_LINES=50 (send only first N lines of script, not full)
   ```

3. **SIEM webhook authentication** — Use mTLS (client cert) for SIEM webhook connection. Prevent MITM from capturing events. Require SIEM to authenticate back (server cert validation).

4. **Separate audit tables** — Maintain two audit tables:
   - `AuditLog` (full details, operator-facing)
   - `AuditLogMasked` (redacted, SIEM-facing)
   - SIEM streams from masked table; operators read full table

5. **Sampling instead of 100%** — Send every Nth event to SIEM (e.g., 1 in 10) to reduce log volume and noise. Operator configures sample rate.

6. **Audit trail for SIEM access** — Log who accessed the SIEM webhook stream. Alert if unexpected access.

**Detection:**

- Audit trail: log every SIEM event sent; include masking policy applied
- Alert if SIEM webhook receives requests with unmasked PII patterns (regex on email, IP, secret patterns)
- Periodic audit: sample SIEM events; verify masking applied correctly
- Monitor SIEM query patterns; alert if queries extract PII (e.g., search on email)

**Phase to address:** Phase 1 (SIEM integration) — implement masking from day 1

---

### Pitfall 11: Router Modularization Circular Import Hell

**What goes wrong:**

`main.py` currently has 89 routes in a monolithic file. v24 refactors into domain routers:

```
routers/
  ├── users_router.py (auth, RBAC)
  ├── jobs_router.py (job CRUD, dispatch)
  ├── nodes_router.py (node monitoring)
  ├── foundry_router.py (Foundry/Smelter)
  ├── workflows_router.py (DAG/workflows)
  ├── audit_router.py (audit log)
  ├── admin_router.py (admin config)
```

If router modularization is not careful, circular imports appear:

1. `jobs_router.py` needs to call `audit_service.log_job_created()`
2. `audit_router.py` needs to call `jobs_service.get_job()` (for audit context)
3. `audit_router.py` imports `jobs_service`; `jobs_router.py` imports `audit_service`
4. At import time: `jobs_router` imports `audit_service`, which imports `audit_router`, which imports `jobs_service`...
5. Import cycle causes: `ImportError: cannot import name 'some_function'` (half-initialized module)

Or: Import succeeds, but module state is corrupted (e.g., scheduler not initialized when audit service starts).

**Why it happens:**

- Domain routers are interdependent (jobs depend on audit, audit depends on jobs)
- Services are tightly coupled (monolithic main.py did this implicitly; modules make it explicit)
- No circular dependency detection in development
- Tests import routers individually; integration tests skip

**Consequences:**

- Server fails to start: ImportError at lifespan startup
- Operator restarts; server still fails (import cycle not resolved)
- Silent initialization order bugs: scheduler starts before database connection ready
- Development is fragile: adding new route causes unexpected import failures

**Prevention:**

1. **Explicit dependency injection** — Pass dependencies as function arguments, not imports:
   ```python
   # WRONG: circular dependency
   from audit_service import log_event
   
   async def create_job(job_data):
       await log_event("job_created", job_data)
   
   # RIGHT: dependency injection
   async def create_job(job_data, audit_service):
       await audit_service.log_event("job_created", job_data)
   ```

2. **Lazy imports** — Import modules only when needed (inside functions):
   ```python
   async def create_job(job_data):
       from audit_service import log_event  # Import here, not at module top
       await log_event("job_created", job_data)
   ```

3. **Separate interface layer** — Create abstract interfaces / base classes that routers depend on, not concrete implementations:
   ```python
   # audit_interface.py (no dependencies)
   class AuditServiceInterface(ABC):
       async def log_event(self, event_type, data): ...
   
   # jobs_router.py
   from audit_interface import AuditServiceInterface
   async def create_job(job_data, audit_service: AuditServiceInterface):
       await audit_service.log_event(...)
   ```

4. **Startup hook coordination** — Use FastAPI lifespan events to initialize services in strict order:
   ```python
   async def lifespan(app):
       # Order matters: DB → Services → Routers
       await init_db()
       await scheduler_service.startup()
       await audit_service.startup()
       # Routes are already registered; just starting them
       yield
       # Shutdown in reverse order
       await audit_service.shutdown()
       ...
   ```

5. **Import order tests** — Add test that imports all routers in different orders; verify no ImportError:
   ```python
   def test_import_orders():
       import jobs_router
       import audit_router
       import foundry_router
       # (should not raise)
       
       # Also test in reverse order
       import importlib
       importlib.reload(...)
   ```

6. **Type stubs for services** — Create `.pyi` stub files for services (interface only, no implementation). Routers import stubs; no circular dependency.

**Detection:**

- Server startup failures with ImportError; check for "circular import" pattern
- Development warning: if adding import causes test failures in unrelated modules, likely circular dependency
- Static analysis: `python -m pydeps main.py --show-cycles` to detect cycles

**Phase to address:** Phase 1 (Router refactoring) — implement dependency injection from day 1

---

### Pitfall 12: Test Fixture Fragmentation During Router Refactoring

**What goes wrong:**

Tests currently use a monolithic `test_main.py` with shared fixtures (test DB, test client, etc.). When routers are modularized, tests fragment into `test_jobs_router.py`, `test_audit_router.py`, etc. If fixtures are not centralized, each test file creates its own DB/client, leading to:

1. Test A creates job X in its own test DB
2. Test B tries to audit-log job X; its own test DB has no job X
3. Test B fails with "job not found" (not a real bug, fixture isolation issue)
4. Or: fixtures are shared but not properly scoped; Test A's data leaks into Test B

Additionally, integration tests (testing multiple routers together) need combined fixtures, but modular tests need isolated fixtures.

**Why it happens:**

- Fixtures were tightly coupled to monolithic main.py; refactoring breaks them
- Pytest fixture scoping (function, module, session) is manual; easy to get wrong
- Integration tests are afterthought; not written until after unit tests
- Operator adds fixture but doesn't update all test files

**Consequences:**

- Flaky tests: pass when run individually, fail when run together (fixture ordering)
- False failures: test failures are fixture issues, not code bugs (wastes investigation time)
- Low confidence in test suite: operator doesn't trust tests after refactoring
- CI failures are intermittent; hard to reproduce locally

**Prevention:**

1. **Centralized fixture module** — Create `conftest.py` at project root with all shared fixtures:
   ```python
   @pytest.fixture
   def test_db_session():
       # Single fixture shared by all tests
       ...
   
   @pytest.fixture
   def test_client(test_db_session):
       # Depends on DB fixture
       ...
   ```

2. **Fixture composition** — Routers can define additional fixtures, but inherit base fixtures from conftest:
   ```python
   # routers/test_jobs_router.py
   @pytest.fixture
   def jobs_service(test_db_session):
       # Uses base test_db_session
       return JobsService(test_db_session)
   ```

3. **Test database cleanup** — Ensure each test starts with clean DB:
   ```python
   @pytest.fixture(autouse=True)
   def cleanup_db(test_db_session):
       yield  # Test runs
       test_db_session.rollback()  # Undo all changes
   ```

4. **Integration test suite** — Separate integration tests from unit tests:
   ```
   tests/
     ├── unit/
     │   ├── test_jobs_router.py
     │   ├── test_audit_router.py
     ├── integration/
     │   ├── test_job_and_audit_together.py (uses multiple routers)
   ```
   Unit tests use isolated fixtures; integration tests use shared fixtures.

5. **Fixture documentation** — Document which fixtures are required for each router:
   ```python
   # routers/test_jobs_router.py
   """
   Fixtures used: test_db_session, test_client
   Dependencies: requires audit_service to be initialized
   """
   ```

6. **Parametrized fixture tests** — Test that fixtures work with different configurations:
   ```python
   @pytest.mark.parametrize("db_type", ["sqlite", "postgres"])
   def test_fixture_with_db(test_db_session, db_type):
       # Verify fixture works for both DB types
   ```

**Detection:**

- CI test failures that don't reproduce locally; investigate fixture ordering
- Flaky tests that pass sometimes; check for shared fixture pollution
- Test run order dependency: `pytest --random-order` exposes fixture issues
- Coverage gaps: test X creates data; test Y expects that data; tests fail if Y runs first

**Phase to address:** Phase 1 (Router refactoring) — implement centralized fixtures before modularizing

---

## Moderate Pitfalls

### Pitfall 13: CE/EE Boundary Drift During Router Refactoring

When modularizing routers, the CE/EE split must be maintained: some routes return HTTP 402 in CE, others are available in both. If the refactoring is not careful, routes accidentally move between CE/EE:

1. Route `/admin/features` was EE-only (returns 402 in CE)
2. Refactoring moves it to `admin_router.py`
3. Developer forgets `@require_license("EE")` decorator
4. CE users can now access feature; CE/EE boundary broken

**Prevention:**
1. Mark all EE routes with explicit `@require_license("EE")` decorator at definition (not implicit)
2. Test matrix: run all routes against both CE and EE, verify 402 vs 200 responses match expectations
3. Router-level guards: CE mode doesn't even register EE routers (include_router conditional on IS_EE flag)

---

### Pitfall 14: Router Dependency on Uninitialized Services

If routers import services at module level, but services aren't initialized until lifespan startup:

```python
# jobs_router.py (WRONG)
from scheduler_service import scheduler  # Global; not initialized yet

@app.get("/jobs")
async def list_jobs():
    jobs = scheduler.list_jobs()  # AttributeError if scheduler not started
```

**Prevention:**
1. Use dependency injection: `async def list_jobs(scheduler = Depends(get_scheduler))`
2. Depends() helper retrieves initialized service from app state
3. Services are never accessed until after lifespan startup

---

## Integration-Specific Risks

### Risk: Vault + Ed25519 Key Rotation Coordination

If Vault rotates Ed25519 licence keys (used for EE plugin verification), and Axiom is simultaneously validating licence JWTs, a race condition can occur: old key used to verify new JWT (validation fails). Document: Vault key rotation must include grace period (both old + new keys valid for 1 hour). Axiom fetches key list from Vault with per-key validity timestamps.

### Risk: SIEM Webhook + Job Dispatch Race

Job A completes; concurrently, SIEM webhook is sent and job dispatch happens. If SIEM webhook modifies job state, and dispatch reads stale state, jobs may re-execute or be skipped. **Mitigation:** Webhook is read-only (audit only). Job dispatch reads directly from DB, not from webhook response.

### Risk: TPM Attestation + Node Mobility

Node A is enrolled with TPM attestation (PCR values recorded). Node is migrated to different hardware (physical or VM). TPM measurements change; attestation fails. **Mitigation:** On node re-enrollment, re-attest and update reference PCR values. Flag "PCR measurements changed significantly" for operator review.

### Risk: Plugin + Vault Secret Access

Plugin requires a secret (e.g., API key for external service). Plugin requests from Vault directly (not through Axiom proxy). Axiom audit log doesn't see the access. **Mitigation:** Plugins access secrets only through Axiom API (read-only proxy). Every secret access is logged.

---

## Technical Debt Patterns

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| Skip Vault optional mode; make mandatory | Simpler code path | Breaks air-gapped deployments | Never; support both |
| Don't implement lease renewal; rely on startup | Faster deployment | Leases expire mid-operation | Never; background renewal required |
| Embed secrets in signed scripts | Quick feature delivery | Secret rotation breaks jobs | Never; use env vars |
| No TPM library checks; assume present | Faster deployment | Fails on Alpine/ARM64 | Never; graceful fallback required |
| Plugin API versioning optional | Simpler plugin SDK | Version conflicts in production | Never; versioning required |
| No plugin DB access control; allow direct access | Simpler plugins | Security violations, compliance gaps | Never; read-only API required |
| Unbuffered SIEM streaming | Simple implementation | Log flooding, data loss | Never; batch and buffer required |
| No SIEM PII masking | Simpler code | Compliance violations, data exposure | Never; masking required |
| Router monolithic; skip modularization | No refactoring effort | Maintainability debt, testing hard | Never; modularize by Phase 1 end |
| Circular imports; use lazy imports | Faster development | Import failures, initialization bugs | Never; avoid circular deps |

---

## Performance Traps

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|----------------|
| Vault lease renewal on every route | High latency (>100ms per request) | Background lease renewal task; cache secrets with TTL | >100 concurrent requests |
| SIEM streaming unbuffered | 8+ POST requests/sec to SIEM; network saturation | Batch events (100 per flush) | >500 jobs/min |
| TPM attestation per request | Slow job dispatch (TPM operations take 100s-1000s ms) | Batch attestations; async background validation | >10 concurrent attestations/min |
| Plugin queries without limits | Long-running plugin queries lock DB | Timeout, query isolation per plugin | >10 concurrent plugins with queries |
| Router imports at module level | Slow startup (deep import tree) | Lazy imports; dependency injection | >20 routers |

---

## Security Mistakes

| Mistake | Risk | Prevention |
|---------|------|------------|
| Vault AppRole Secret ID not rotated | Compromised Secret ID enables infinite API access | Rotate Secret ID weekly; retire old ID immediately |
| Lease TTL not validated at job dispatch | Lease expires mid-execution; secrets unreadable | Check lease_ttl >> job.expected_runtime at dispatch |
| Secret migration incomplete | Old secrets become inaccessible; credentials lost | Mandatory migration check at startup; require --migrate flag |
| TPM attestation quote not timestamped | Replay attacks; old quote accepted as valid | Reject quotes older than 5 minutes |
| Plugin database access unrestricted | Malicious plugin exfiltrates PII | Read-only API; capability-based access control |
| SIEM webhook plaintext | MITM attacker sees full audit events (PII) | mTLS for SIEM webhook; encrypt end-to-end |
| Router CE/EE boundary not marked | EE routes accessible in CE | Explicit @require_license decorator; CE tests verify 402 responses |
| Plugin versioning not enforced | Plugin API v2 breaks with Axiom v23 | Plugin declares axiom_api_version; Axiom rejects mismatches |

---

## "Looks Done But Isn't" Checklist

- [ ] **Vault Integration:** Tested Vault startup failure (fails gracefully, not hard crash); tested lease renewal (background task doesn't block); tested secret rotation (jobs validated after rotation)
- [ ] **TPM Enrollment:** Tested on all supported OS (Debian, Ubuntu, Alpine, Windows); tested vTPM in VM (swtpm or KVM); tested fallback to non-TPM (logs gracefully, no crash)
- [ ] **Plugin System:** Two plugins with version conflicts can be installed together (no pip error); plugin API versioning enforced at load time; database access gated by capability
- [ ] **SIEM Streaming:** 500 jobs/min produces <10 webhook requests/sec to SIEM (batching works); PII masking verified (no emails/IPs in SIEM); failed SIEM webhook retries + alerts
- [ ] **Router Refactoring:** All 89 routes moved to routers; no circular imports (import -m pydeps detects none); CE/EE tests verify 402 responses; fixtures centralized, tests pass in any order

---

## Recovery Strategies

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|----------------|
| Vault unavailable (hard crash) | MEDIUM | Restore from snapshot with old key; run mitigation (grace period fallback) |
| Lease expired, audit logs corrupted | HIGH | Restore DB from backup; implement lease renewal + validation |
| Secret rotation broke jobs | MEDIUM | Re-sign affected jobs (bulk operation); migrate to env-var pattern |
| TPM not found on node | LOW | Update node image; implement graceful fallback |
| Plugin version conflict | LOW | Remove conflicting plugin; implement version matrix |
| SIEM flooded / data lost | MEDIUM | Implement batching; recover lost events from Axiom audit table |
| SIEM PII exposed | HIGH | Breach notification; implement masking; audit SIEM access logs |
| Circular import at startup | LOW | Identify circular imports (pydeps); refactor to lazy imports or dependency injection |
| Test fixtures polluted | MEDIUM | Centralize fixtures; implement cleanup; rerun full test suite |
| CE/EE boundary drifted | MEDIUM | Audit all routes; add @require_license explicitly; rerun CE tests |

---

## Pitfall-to-Phase Mapping

| Pitfall | Prevention Phase | Verification |
|---------|------------------|--------------|
| Vault hard startup (1) | Phase 1 (Vault) | Grace period fallback works; env vars still functional if Vault down |
| Lease expiry (2) | Phase 1 (Vault) | Job longer than lease TTL completes successfully; renewal is background task |
| Secret rotation (3) | Phase 1 (Vault) | After secret rotation, jobs using env vars still work; embed-secret jobs identified & re-signed |
| Fernet migration (4) | Phase 1 (Vault) | Old and new secrets decryptable; dual-key period works; reencrypt endpoint succeeds |
| TPM library availability (5) | Phase 2 (TPM) | Builds successful on Alpine, Ubuntu, Windows, ARM64; fallback to non-TPM works |
| TPM attestation validation (6) | Phase 3 (v25) | Attestation quotes timestamped; PCR values validated; nonce in quote |
| Plugin version conflicts (7) | Phase 3 (Plugin SDK) | Two plugins with conflicting deps can install + load; version matrix prevents mismatches |
| Plugin DB access (8) | Phase 3 (Plugin SDK) | Plugin cannot access secrets; read-only API enforced; capability gating works |
| SIEM log flooding (9) | Phase 1 (SIEM) | 500 jobs/min generates <10 webhook reqs/sec; no network saturation |
| SIEM PII leakage (10) | Phase 1 (SIEM) | Emails masked in SIEM; IPs masked; script content masked; no PII visible in SIEM |
| Router circular imports (11) | Phase 1 (Router refactoring) | All routers import successfully in any order; no circular dependency |
| Test fixture fragmentation (12) | Phase 1 (Router refactoring) | All tests pass when run together; pytest --random-order succeeds |
| CE/EE boundary drift (13) | Phase 1 (Router refactoring) | CE tests verify all EE routes return 402; CE mode doesn't register EE routers |

---

## Sources

### Vault & Secret Management
- [HashiCorp Vault AppRole Auth Method](https://developer.hashicorp.com/vault/docs/auth/approle)
- [Vault KV v2 Secret Engine](https://developer.hashicorp.com/vault/docs/secrets/kv/kv-v2)
- [Secret Rotation Best Practices](https://learn.hashicorp.com/tutorials/vault/database-secret-rotation)
- [Lease Management in Vault](https://developer.hashicorp.com/vault/docs/concepts/lease)

### TPM & Hardware Identity
- [TPM 2.0 Specification Overview](https://trustedcomputinggroup.org/resource/tpm-2-0-specifications/)
- [TPM 2.0 Tools & Libraries](https://github.com/tpm2-software)
- [Attestation Quote Validation](https://tpm2-software.github.io/tpm2-tools/latest/man/tpm2_quote.1/)
- [vTPM Emulation with swtpm](https://github.com/stefanberger/swtpm)
- [PCR Measurements & Boot Integrity](https://wiki.ubuntu.com/SecurityTeam/BitlockerDriveLock/SecureBoot)

### Plugin Architecture & Security
- [Python Entry Points (importlib.metadata)](https://docs.python.org/3/library/importlib.metadata.html)
- [Plugin Architecture Patterns](https://realpython.com/plugins-python/)
- [Dependency Conflict Resolution](https://pip.pypa.io/en/latest/topics/dependency-resolution/)
- [Container Isolation for Untrusted Code](https://docs.docker.com/engine/security/)

### SIEM Integration & Audit Streaming
- [CEF (Common Event Format) Specification](https://www.ibm.com/docs/en/qsip/7.4?topic=CEF-cef-format)
- [Syslog Protocol (RFC 3164 & 5424)](https://www.rfc-editor.org/rfc/rfc5424)
- [Webhook Delivery Guarantees](https://svix.com/docs/general/webhooks/)
- [PII Redaction Patterns](https://www.owasp.org/index.php/Sensitive_Data_Exposure)
- [SIEM Integration Best Practices](https://www.gartner.com/en/documents/3889770)

### FastAPI Router Patterns & Testing
- [FastAPI Routing & Dependency Injection](https://fastapi.tiangolo.com/tutorial/bigger-applications/)
- [Python Circular Import Prevention](https://realpython.com/python-circular-imports/)
- [Pytest Fixtures & Composition](https://docs.pytest.org/en/latest/how-to/fixtures.html)
- [Test Database Isolation Patterns](https://testdriven.io/blog/database-testing-fastapi/)

### Axiom Codebase References
- `puppeteer/agent_service/main.py` — Current monolithic route definitions
- `puppeteer/agent_service/services/` — All service modules (job_service, audit_service, etc.)
- `puppeteer/agent_service/db.py` — SQLAlchemy models, CE/EE split via EEBase
- `puppeteer/agent_service/security.py` — JWT, API key, mTLS logic
- `puppeteer/agent_service/ee/` — EE plugin entry point, EE routes
- `puppeteer/tests/` — Pytest test structure, fixtures, conftest

---

*Research completed: 2026-04-18*  
*Domain: HashiCorp Vault, TPM 2.0, Plugin SDK v2, SIEM Streaming, Router Modularization*  
*Ready for roadmap planning: YES — all pitfalls have prevention strategies and phase assignments*
