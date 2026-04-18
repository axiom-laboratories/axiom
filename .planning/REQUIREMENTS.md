# Requirements: Axiom (Master of Puppets)

**Defined:** 2026-04-18
**Core Value:** Secure, pull-based job orchestration across heterogeneous node fleets — with mTLS identity, Ed25519-signed execution, and container-isolated runtime

## v24.0 Requirements

Requirements for milestone v24.0 — Security Infrastructure & Extensibility.

### Security — CVE Remediation

- [ ] **SEC-03**: Axiom ships with `cryptography >= 46.0.7`, resolving the HIGH buffer-overflow CVE flagged on the v23.0 tag
- [ ] **SEC-04**: All Dependabot HIGH and MODERATE alerts on the v23.0 tag are resolved and tests pass

### Architecture — Router Modularization

- [ ] **ARCH-01**: Backend routes are split into 6 domain APIRouter modules (auth, jobs, nodes, workflows, foundry, admin/system)
- [ ] **ARCH-02**: All existing API endpoints function identically after the refactor (zero behavior change, same paths/responses)
- [ ] **ARCH-03**: Domain routers support per-domain middleware injection via FastAPI `Depends()`
- [ ] **ARCH-04**: Full backend test suite passes with unchanged coverage after the refactor

### Vault Integration (EE)

- [ ] **VAULT-01**: EE administrator can configure Vault connection (address + AppRole credentials) via admin UI or env vars
- [ ] **VAULT-02**: Platform fetches secrets from Vault at startup with automatic fallback to env vars when Vault is unreachable
- [ ] **VAULT-03**: Job dispatch injects Vault-sourced secrets into the execution context without embedding them in the job definition
- [ ] **VAULT-04**: Platform actively renews secret leases before expiry during long-running jobs
- [ ] **VAULT-05**: Admin dashboard shows Vault connectivity status (healthy / degraded / disabled)
- [ ] **VAULT-06**: Platform starts successfully and degrades gracefully when Vault is offline at boot

### SIEM Audit Streaming (EE)

- [ ] **SIEM-01**: EE administrator can configure a SIEM destination (webhook URL or syslog host + format) via admin UI
- [ ] **SIEM-02**: Audit events are streamed in batches (flush at 100 events or every 5 seconds, whichever comes first)
- [ ] **SIEM-03**: SIEM webhook payloads are formatted as CEF
- [ ] **SIEM-04**: Sensitive fields (secrets, tokens, passwords) are masked before transmission to the SIEM
- [ ] **SIEM-05**: Failed webhook deliveries are retried with exponential backoff and surface an admin alert
- [ ] **SIEM-06**: SIEM streaming can be disabled without affecting the local audit log

## Future Requirements

Deferred — not in v24.0 roadmap.

### Plugin System

- **PLUGIN-01**: Third-party plugins are discoverable via Python entry_points without modifying core code
- **PLUGIN-02**: Plugin API is versioned with a documented compatibility contract
- **PLUGIN-03**: Plugins have read-only access to job and node data via a capability-gated API
- **PLUGIN-04**: Conflicting plugin dependencies are detected at startup before loading
- **PLUGIN-05**: Plugin loading can be disabled entirely via config flag

## Out of Scope

Explicitly excluded for v24.0.

| Feature | Reason |
|---------|--------|
| TPM-based node identity | Axiom nodes run in containers — hardware attestation is impractical in this environment |
| Vault agent sidecar | Unnecessary complexity; native hvac AppRole auth is sufficient |
| Per-job TPM attestation | TPM support removed entirely from v24.0 |
| Plugin hot-reload | Memory leak / dangling reference risk; deferred with Plugin SDK |
| Splunk HEC native format | CEF covers Splunk via HTTP Event Collector adapter; native HEC deferred |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| SEC-03 | — | Pending |
| SEC-04 | — | Pending |
| ARCH-01 | — | Pending |
| ARCH-02 | — | Pending |
| ARCH-03 | — | Pending |
| ARCH-04 | — | Pending |
| VAULT-01 | — | Pending |
| VAULT-02 | — | Pending |
| VAULT-03 | — | Pending |
| VAULT-04 | — | Pending |
| VAULT-05 | — | Pending |
| VAULT-06 | — | Pending |
| SIEM-01 | — | Pending |
| SIEM-02 | — | Pending |
| SIEM-03 | — | Pending |
| SIEM-04 | — | Pending |
| SIEM-05 | — | Pending |
| SIEM-06 | — | Pending |

**Coverage:**
- v24.0 requirements: 18 total
- Mapped to phases: 0 (pending roadmap creation)
- Unmapped: 18 ⚠️

---
*Requirements defined: 2026-04-18*
*Last updated: 2026-04-18 after initial definition*
