# Feature Research: Container Security Hardening + EE Licence Protection

**Domain:** Infrastructure security, software supply chain, operational licensing

**Researched:** 2026-04-12

**Confidence:** HIGH (Docker/Podman security practices well-documented; EE patterns derive from existing codebase; Python wheel integrity follows established PEPs; HMAC boot log is straightforward cryptographic application; all features are operationally validated in similar systems)

---

## Feature Landscape

### Table Stakes (Users Expect These)

Features operators assume exist in a production orchestration platform. Missing these = deployment fails security compliance audits.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| **Non-root user execution** | All modern orchestration platforms (Kubernetes, Docker, systemd) require containers to run as unprivileged users; root containers trigger automated security scanners | MEDIUM | Requires: USER directive in Containerfile, permission setup for read/execute paths, volume ownership (appuser:appuser for logs/config) |
| **Linux capability dropping** | Security hardening standard since Docker 1.x; prevents container processes from exploiting privileged syscalls | LOW | Requires: `cap_drop: ALL` in compose + selective `cap_add` if truly needed (rare for Python agents) |
| **No new privileges enforcement** | Prevents setuid/setgid escapes; standard in CIS benchmarks, NIST guidelines, OWASP top 10 | LOW | Requires: `security_opt: no-new-privileges:true` in compose or `--security-opt=no-new-privileges` at runtime |
| **Read-only root filesystem** | Prevents persistent malware installation; standard in Kubernetes Pod Security Standards | MEDIUM | Requires: explicitly writable mount volumes for runtime state (logs, temp, sockets); agent needs `/tmp`, `/app/secrets` writable |
| **Resource limits enforcement** | Prevents container from starving host or consuming runaway memory; operators expect per-service limits in compose | LOW | Requires: `memory`, `cpus`, `cpu_shares` set in compose for each service; coordinated with DB connection pool sizing |
| **Hardened Dockerfile base images** | Docker Hardened Images initiative (DHI) provides pre-scanned, minimal-attack-surface bases; operators expect availability | LOW | Requires: evaluate Docker's official hardened alpine / python variants; currently using generic `python:3.12-alpine` and `postgres:15-alpine` |
| **Socket-based rather than privileged mode** | Docker socket mount (`/var/run/docker.sock`) is well-known attack surface; modern practice is explicit socket mount + unprivileged user, not `privileged: true` | MEDIUM | Requires: agent runs as appuser, Docker socket mounted as `rw`, Docker CLI in PATH, host Docker daemon must allow socket access to agent UID |
| **Podman compatibility** | Operators in air-gapped or rootless environments prefer Podman; two-runtime support expected in enterprise software | HIGH | Requires: separate `node-compose.podman.yaml` with Podman socket instead of Docker; validate `podman.sock` socket location/permissions |

### Differentiators (Competitive Advantage)

Features that set Axiom apart and justify premium positioning.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| **Signed wheel manifest for axiom-ee** | Prevents wheel tampering during air-gapped deployment; operators can verify package integrity without PyPI; differentiates from competitors who ship wheels unsigned | HIGH | Requires: `sign_wheels.py` CLI tool; Ed25519 offline signing; per-release manifest JSON with wheel hash + signature; `pip install` hook to verify before extraction; integration with release pipeline |
| **HMAC boot log clock-rollback detection** | Protects EE licensing from clock-based exploits (set system time backwards to extend trial); competing products use simple hash chain (easy to replay); HMAC-keyed detection is cryptographically sound | MEDIUM | Requires: `secrets/boot.log` with HMAC-SHA256 of previous record keyed on `ENCRYPTION_KEY`; on-upgrade boot log migration; validation both at startup and on node re-enrollment |
| **Entry point whitelist validation** | Prevents malicious plugins from hijacking EE plugin discovery; ensures only authentic `EEPlugin` class loads; zero-trust plugin loading model | LOW | Requires: `load_ee_plugins()` validates `ep.value == "ee.plugin:EEPlugin"` before `load()`; gating in main.py lifespan; test coverage for invalid ep names |
| **Per-node licence seat management** | Nodes counted against `node_limit` in licence at enrollment; competitors batch-limit but don't enforce per-node; provides granular license compliance | MEDIUM | Requires: `POST /api/enroll` checks active node count ≥ `node_limit` → HTTP 402; audit log on license-limit rejection; dashboard display of node count vs limit |
| **Graceful EE→CE fallback with HMAC verification** | On licence expiry or invalid signature, system demotes to CE safely; no crash, no data loss; operators run normally under CE constraints; transparent operational model | MEDIUM | Requires: GRACE period (default 30 days) before DEGRADED_CE transition; background job monitors expiry every 60s; WebSocket broadcast on state change; operator runbook for license renewal |
| **Offline licence generation & validation** | Operators issue licences from offline air-gapped issuer machine; nodes validate against hardcoded Ed25519 public key; never requires network call to validate license; critical for air-gapped ops | MEDIUM | Requires: `issue_licence.py` CLI on issuer; `licence_service.py` validates JWT signature; hardcoded public key in binary; per-customer ID tracking in JWT payload |

### Anti-Features (Commonly Requested, Often Problematic)

Features that seem appealing but create architectural or operational problems.

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|-----------------|-------------|
| **Per-image hardening (build-time Dockerfile.* variants)** | Operators want separate hardened vs. standard images; feels like explicit security | Multiplies testing burden, CI pipeline complexity, upgrade scenarios; standard practice is single hardened base for all variants | Single hardened base image (non-root, cap_drop:ALL, no-new-privs) applies to all services; optional hardening knob (RO_FILESYSTEM env var) for operators who need write access |
| **Privilege escalation via `sudo` in container** | Sounds good for "elevated" jobs; some operators request it | Breaks isolation model; if job escapes container, escalates to host; violates non-root architecture; requires remount of secrets | Run jobs in separate unprivileged containers; if elevated access needed (e.g., kernel patching), dispatch as separate privileged batch job with explicit approval |
| **Dynamic entry point discovery without whitelist** | Sounds flexible; allows any plugin to self-register | Allows malicious wheels to inject fake EE plugins; signature verification on plugin code is better than discovery trust | Hardcode entry point name + validate before load; add new plugins via release process, not runtime discovery |
| **Encrypted secrets at rest via EE-only encryption** | Upsell opportunity; operators may want premium encryption | CE users feel vulnerable; creates CE/EE schema mismatch; operational complexity (key rotation, migration) | Use same `ENCRYPTION_KEY`-based Fernet for both CE and EE; encryption is not a license gate, it's a baseline security requirement |
| **Automatic boot log cleanup on license expiry** | Sounds like privacy; audit-log "self-destruct" on license end | Destroys licensing compliance evidence; breaks forensics; operators can't audit past expirations; violates SOC 2 requirements | Boot log is immutable append-only; never delete; create `boot.log.archived` for historical analysis; operators responsible for retention policy |
| **Node images with hardening baked into Foundry templates** | Sounds convenient; auto-hardening from blueprint selection | Hides security config from operators; harder to audit deployed images; CI/CD can't validate Containerfile; violates GitOps principle | Generated Containerfiles explicitly include USER/cap_drop/no-new-privs directives; operators see and review exact Containerfile before build; defaults are hardened but visible |

---

## Feature Dependencies

```
Container Hardening (Phase A)
├── Non-root USER in Containerfile
│   └──requires──> Writable volume mounts (/tmp, /app/secrets, /var/log)
│   └──requires──> File ownership setup (appuser:appuser)
│
├── Linux cap_drop:ALL
│   └──enhances──> Non-root execution (defense in depth)
│
├── no-new-privileges:true
│   └──enhances──> Non-root execution
│
├── Resource limits (memory/cpu)
│   └──requires──> Compose schema updates (version 3+)
│   └──requires──> Test validation at peak load
│
├── Docker socket mount + remove privileged
│   └──requires──> Non-root user (appuser can access /var/run/docker.sock)
│   └──requires──> Host Docker daemon allows appuser UID access
│   └──conflicts──> privileged:true mode (must choose one)
│
└── Podman variant (node-compose.podman.yaml)
    └──requires──> Docker socket feature complete
    └──requires──> /run/podman/podman.sock path validation

EE Licence Protection (Phase B)
├── Signed wheel manifest (sign_wheels.py)
│   └──requires──> Ed25519 private key (from existing pki)
│   └──requires──> Per-release manifest JSON generation
│   └──requires──> pip install hook (verify before extract)
│
├── HMAC boot log migration
│   └──requires──> Existing hash-chained boot.log (Phase 14.3)
│   └──requires──> Migration path for existing deployments
│   └──requires──> Backward-compat for old-format boot logs (reads as hash chain, writes as HMAC)
│
├── Entry point whitelist validation
│   └──requires──> importlib.metadata integration (already exists)
│   └──requires──> EEPlugin class defined + hardcoded ep name
│
└── Per-node licence seat enforcement
    └──requires──> Existing node enrollment endpoint
    └──requires──> Existing JWT licence validation
    └──requires──> Active node count query + audit logging
```

---

## Operator-Facing Feature Definitions

### 1. Container Non-Root User Execution
- All services run as `appuser:appuser` (UID 1000)
- Volume mounts owned by `appuser:appuser`
- No `Permission denied` errors on startup

### 2. Linux Capability Dropping
- `cap_drop: ALL` in all compose services
- No elevated capabilities available to containers
- Job execution unaffected

### 3. No-New-Privileges Enforcement
- `security_opt: no-new-privileges:true` prevents setuid escalation
- Containers cannot gain privilege via binary execution

### 4. Resource Limits
- Memory limits: Agent 1GB, DB 2GB, other services 256-512MB
- CPU limits coordinated with expected load
- OOM kills restart service automatically

### 5. Docker Socket Mount (Remove privileged: true)
- Agent and node access Docker via `/var/run/docker.sock`
- No `privileged: true` mode
- Job execution + Foundry builds work via socket

### 6. Podman Variant (node-compose.podman.yaml)
- Alternative compose file for Podman environments
- Socket path: `/run/podman/podman.sock` (or rootless equivalent)
- Transparent compatibility with Docker variant

### 7. Signed Wheel Manifest (axiom-ee)
- Release includes `WHEELS.json` with Ed25519 signature
- pip install verifies hash before extraction
- Tampering detected with clear error messages

### 8. HMAC Boot Log Clock-Rollback Detection
- Boot log uses HMAC-SHA256 integrity (keyed on ENCRYPTION_KEY)
- Clock rollback detected and prevented (EE mode) or warned (CE mode)
- Migration from old SHA256 format automatic

### 9. Entry Point Whitelist Validation
- EE plugin load validates entry point name
- Invalid plugins rejected at startup (not loaded silently)

### 10. Per-Node Licence Seat Management
- Enrollment fails with HTTP 402 if node_limit reached
- Dashboard shows active nodes vs limit
- Audit log records rejections

---

## Feature Complexity Summary

| Feature | Effort | Risk | Testing |
|---------|--------|------|---------|
| Non-root user | 2-3 days | LOW | Startup, volume ownership, operations |
| cap_drop:ALL | 1 day | VERY LOW | Security scan |
| no-new-privileges | 1 day | VERY LOW | Compose check |
| Resource limits | 2-3 days | MEDIUM | Peak load stress test |
| Docker socket | 3-4 days | HIGH | Job execution, Foundry, enrollment |
| Podman variant | 2-3 days | MEDIUM | Podman deployment |
| Signed wheel | 4-5 days | MEDIUM | Wheel verify, air-gap install |
| HMAC boot log | 3-4 days | MEDIUM | Boot sequence, migration |
| Entry point | 1-2 days | LOW | EE plugin load |
| Per-node seat | 2-3 days | LOW | Enroll multiple nodes |

**Total: 24-28 days sequential | Parallelizable: 40-50% speedup possible**

---

## Sources

### Container Security Best Practices (2026)
- [Docker Security Documentation](https://docs.docker.com/engine/security/)
- [Docker Container Security Best Practices 2026 - TechSaaS](https://www.techsaas.cloud/blog/docker-container-security-best-practices-2026/)
- [Docker Container Best Practices 2026 - Jishu Labs](https://jishulabs.com/blog/docker-container-best-practices-2026)
- [OWASP Docker Security Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Docker_Security_Cheat_Sheet.html)
- [Dockerfile Best Practices for Container Security - Sysdig](https://www.sysdig.com/learn-cloud-native/dockerfile-best-practices)

### Podman vs Docker Security (2026)
- [Podman vs Docker: Complete 2026 Comparison - Xurrent](https://www.xurrent.com/blog/podman-vs-docker-complete-2025-comparison-guide-for-devops-teams)
- [Docker vs Podman: Developer Guide 2026 - DEV Community](https://dev.to/_d7eb1c1703182e3ce1782/docker-vs-podman-developer-guide-to-container-runtimes-2026-4e1i)
- [Podman vs Docker: Rootless Security Guide - Petronella Cybersecurity](https://petronellatech.com/blog/podman-the-modern-daemonless-alternative-to-docker/)

### Python Wheel Integrity & Supply Chain
- [PEP 427 - Wheel Binary Package Format 1.0](https://peps.python.org/pep-0427/)
- [PEP 491 - Wheel Binary Package Format 1.9](https://peps.python.org/pep-0491/)
- [Python Packaging: Binary Distribution Format](https://packaging.python.org/specifications/binary-distribution-format/)
- [Red Hat Trusted Libraries Blog](https://developers.redhat.com/blog/2026/02/27/red-hat-trusted-libraries-trust-and-integrity-your-software-supply-chain/)
- [Secure Installs - pip Documentation](https://pip.pypa.io/en/stable/topics/secure-installs/)

### Python Entry Points & Plugin Loading
- [importlib.metadata Documentation](https://docs.python.org/3/library/importlib.metadata.html)
- [setuptools Entry Points Documentation](https://setuptools.pypa.io/en/stable/userguide/entry_point.html)
- [Python Packaging Entry Points Specification](https://packaging.python.org/specifications/entry-points/)

### HMAC & Boot Log Security
- [HMAC (Hash-Based Message Authentication Codes) - Frontegg](https://frontegg.com/blog/hmac)
- [What is HMAC - Okta](https://www.okta.com/identity-101/hmac/)
- [How HMAC Works: Step-by-Step - Medium](https://medium.com/@short_sparrow/how-hmac-works-step-by-step-explanation-with-examples-f4aff5efb40e)

---

**Research Complete:** 2026-04-12

**Confidence Assessment:** HIGH

Docker/Podman practices documented in current standards. EE patterns derive from existing v14.3+ codebase (Ed25519 JWT, hash-chained boot log). Python wheel integrity follows established PEPs. HMAC boot log is straightforward cryptographic application. All features validated in similar systems (Kubernetes, Docker Compose, air-gapped deployments).

