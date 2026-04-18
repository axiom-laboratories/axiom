# Research Summary: Axiom v24.0 — Security Infrastructure & Extensibility

**Project:** Axiom (Master of Puppets)
**Domain:** Orchestration platform with security hardening + extensibility
**Researched:** 2026-04-18
**Milestone:** v24.0
**Confidence:** MEDIUM-HIGH

## Executive Summary

v24.0 introduces **five interconnected features** that strengthen Axiom for enterprise deployments: external secrets management via HashiCorp Vault, hardware-backed node identity via TPM 2.0, third-party plugin SDK, real-time SIEM audit streaming, and router modularization. These features are optional/additive (zero breaking changes) and segment into clear tiers:

**Tier 1 (Recommended v24.0 ship):** Router refactoring (prerequisite), Vault integration (low-risk enterprise table stake), SIEM audit streaming (compliance requirement)

**Tier 2 (Defer to v24.1/v25.0):** TPM identity (OS library fragmentation), Plugin SDK v2 (version conflict hazards, API stability required)

**Critical insight:** All five features depend on modular router architecture. Router refactoring must execute first. Vault + SIEM are low-risk, high-value enterprise foundations; ship together. TPM and Plugin SDK are strategic differentiators with higher complexity; defer unless critical enterprise blockers exist.

Research identifies **14 distinct pitfalls** across features with explicit prevention strategies. Top 5 critical: (1) Vault hard startup dependency, (2) secret lease expiry during long jobs, (3) TPM library availability across OS variants, (4) plugin version conflicts, (5) SIEM log flooding. The team must prioritize Vault grace-period fallback and router circular-import prevention as blocking gates.

## Key Findings

### Recommended Stack

**New Libraries (All Optional):**

| Library | Version | Purpose | Why Recommended | Confidence |
|---------|---------|---------|-----------------|-----------|
| **hvac** | >= 1.2.0 | Vault API client | Official, AppRole auth, production-grade, 95KB footprint | HIGH |
| **tpm2-pytss** | >= 0.5.0 | TPM 2.0 bindings | Official TSS, stable, no Python alternatives | MEDIUM-HIGH |
| **tpm2-tools** | >= 5.4 | TPM CLI tools | System package; variable OS availability | MEDIUM |
| **syslogcef** | >= 0.3.0 | CEF/LEEF formatting | Production-grade, edge-case handling, 95% SIEM support | HIGH |
| **rfc5424-logging-handler** | >= 1.4.3 | RFC 5424 syslog | Official RFC 5424, cross-platform | HIGH |
| **graypy** | >= 2.2.0 | Graylog GELF handler | Battle-tested, community standard (optional) | HIGH |
| **importlib.metadata** | stdlib | Plugin discovery | Built-in Python 3.11+, no external dependency | HIGH |

**Router Modularization:** No new libraries; uses FastAPI's built-in `APIRouter` + `Depends()`.

**Security Fixes:** `cryptography >= 46.0.7` (buffer overflow CVE) + all HIGH-priority Dependabot findings.

**Installation Strategy:** All new libraries optional in wheel; skipped at runtime if not configured. CE deployments functional without Vault, TPM, SIEM libraries.

### Expected Features

**Tier 1 (Ship v24.0 — Low Risk, High Value):**
- **Vault Integration** — External secrets, AppRole auth, no hardcoded env vars (enterprise table stake)
- **SIEM Audit Streaming** — Webhook/syslog/CEF export to Splunk, Elastic, QRadar (compliance requirement)
- **Router Refactoring** — 89 routes → 6 domain routers; improves maintainability, testability, enables middleware injection

**Tier 2 (Defer v24.1+ — Higher Complexity):**
- **TPM-Based Node Identity** — Hardware attestation enrollment (differentiator; deferred: OS support matrix needed, PCR baseline management complex)
- **Plugin System v2 SDK** — Third-party extensibility via entry_points (strategic; deferred: version conflicts, API stability required)

**Anti-Features (Do NOT build):**
- Vault agent sidecar (unnecessary complexity)
- Per-job TPM attestation (TPM too slow for high frequency)
- Plugin hot-reload (memory leak/dangling reference risk)
- Untrusted plugin sandboxing (Python unfixable; plugins = trusted code)

**MVP Recommendation:** Build Vault + SIEM + Router refactoring in v24.0. Defer TPM + Plugin SDK to v24.1+.

### Architecture Approach

All features are **additive, non-breaking extensions** of existing patterns:

1. **Vault** — Secrets injected into job context; optional Fernet fallback
2. **TPM** — Augments existing mTLS (not replacement); optional attestation layer
3. **Plugin SDK** — Extends EE plugin model (entry_points); public-facing with versioning
4. **SIEM Streaming** — Async middleware above AuditLog table; optional export
5. **Router Modularization** — **Prerequisite blocker** for Vault + SIEM (enables injectable middleware, dependency injection)

**Critical Constraint:** Router refactoring must precede Vault + SIEM because monolithic main.py (89 routes) doesn't support injectable middleware cleanly.

**New Components:**
- **Services:** vault_service.py, siem_service.py, tpm_service.py, plugin_registry.py
- **DB Tables:** VaultSecret, AuditLogDelivery, NodeAttestation
- **Routers:** auth_router.py, jobs_router.py, nodes_router.py, workflows_router.py, foundry_router.py, admin_router.py, system_router.py
- **Models:** VaultConfig, SIEMConfig, PluginBase, PluginRegistry

**CE/EE Boundary:** Preserved via optional feature flags. Vault/SIEM candidate CE features; TPM/Plugin SDK may be EE-only (TBD in phase planning).

### Critical Pitfalls (Top 5)

1. **Vault Hard Startup Dependency** — If Vault unavailable at bootstrap, platform crashes. Mitigation: grace-period fallback, optional mode, health-check endpoint, secret caching. **Phase gate: Required before shipping Vault.**

2. **Secret Lease Expiry During Long-Running Jobs** — Jobs longer than secret TTL fail mid-execution. Mitigation: lease TTL validation at dispatch, active renewal (30% margin), per-job AppRole tokens. **Phase gate: Lease renewal background task required.**

3. **TPM Library Availability Across OS Variants** — tpm2-tools not available on Alpine ARM64, vTPM fragile in VMs. Mitigation: OS support matrix (Debian/Ubuntu stable, Alpine amd64 only, Windows TBD), graceful fallback.

4. **Plugin Version Conflicts** — Two plugins requiring different lib versions cause pip failure or runtime mismatch. Mitigation: Plugin API versioning, dependency conflict detection at startup, version pinning.

5. **SIEM Log Flooding** — Unbuffered streaming at >500 jobs/min overwhelms SIEM; data loss. Mitigation: batch + flush (100 events or 5s), in-memory queue, compression, at-least-once delivery. **Phase gate: Batching from day 1.**

Additional pitfalls: Secret rotation breaks embedded-secret jobs, Fernet migration path incomplete, router circular imports, test fixture fragmentation, CE/EE boundary drift, SIEM PII leakage.

## Implications for Roadmap

### Suggested Phase Execution

**Phase 1: Dependabot Fixes**
- Fix HIGH/MODERATE CVEs before feature work begins
- Delivers: Patched `cryptography` + security-critical packages; all tests pass

**Phase 2: Router Modularization — BLOCKER**
- Prerequisite for Vault + SIEM middleware injection
- Delivers: 89 routes → 6 domain routers; zero behavior change; all tests pass
- Pitfalls addressed: Circular imports, test fragmentation, CE/EE drift

**Phase 3: Vault Integration**
- Enterprise table stake; low risk; foundational for job secrets
- Delivers: Startup-time secret fetch; env-var fallback; health-check endpoint; lease renewal background task
- Pitfalls addressed: Vault hard startup, lease expiry, secret rotation, Fernet migration

**Phase 4: SIEM Streaming**
- Compliance requirement; low risk; pairs with Vault as enterprise foundation
- Delivers: Webhook/syslog/CEF streaming; batching (100 events or 5s); PII masking; retry logic
- Pitfalls addressed: SIEM log flooding, SIEM PII leakage

**Phase 5: TPM Identity (Optional — v24.1)**
- Differentiator; medium-high complexity; defer if schedule constrained
- Delivers: TPM 2.0 enrollment (identity only); full attestation in v25

**Phase 6: Plugin System v2 (Optional — v24.1+)**
- Strategic differentiator; high complexity; defer if schedule constrained
- Delivers: Entry-point plugin discovery; versioned API contract; read-only data API; capability gating

### Phase Ordering Rationale

1. **Router refactoring first:** All downstream features depend on modular structure
2. **Vault + SIEM together:** Both enterprise foundational, low risk, depend on router refactoring
3. **TPM deferred:** Requires OS-specific validation; PCR baseline management complex
4. **Plugin SDK deferred:** Requires stable API contract; rushing risks breaking plugin ecosystem early

### Research Flags

**Phases needing deeper research during planning:**
- **TPM:** OS library availability matrix (Alpine, Windows, ARM64, vTPM) — allocate 1d research before implementation
- **Plugin SDK:** Plugin versioning semantics — requires design session

**Standard patterns (skip research-phase):** Dependabot, Router, Vault, SIEM

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| **Stack (Libraries)** | HIGH | All chosen libraries production-grade, actively maintained |
| **Features (Tier 1)** | HIGH | Vault + SIEM + Router are industry-standard patterns; enterprise expects all three |
| **Features (Tier 2)** | MEDIUM | TPM requires OS-specific testing; Plugin SDK requires careful API design |
| **Architecture** | MEDIUM | Patterns established; CE/EE boundary and job secrets flow are Axiom-specific |
| **Pitfalls** | HIGH | 14 pitfalls identified with explicit prevention strategies and phase assignments |
| **Overall** | MEDIUM-HIGH | Tier 1 is low-risk, high-value; Tier 2 defer if time-constrained |

### Open Gaps

1. **Vault licensing & CE/EE boundary** — CE-native or EE-only?
2. **TPM OS support matrix** — Windows + vTPM + ARM64 status unclear
3. **Plugin SDK API stability** — Versioning contract decision required
4. **SIEM format support** — CEF only, or add Splunk HEC native?
5. **Secret lifecycle documentation** — When embed secrets vs use env vars?

## Sources

- `.planning/research/STACK-v24.md` — Library selection, versions, rationale
- `.planning/research/FEATURES-v24.0.md` — Feature landscape, tiers, anti-features, MVP recommendation
- `.planning/research/ARCHITECTURE-v24.md` — Integration patterns, new components, CE/EE preservation
- `.planning/research/PITFALLS-v24.0.md` — 14 pitfalls with prevention strategies, phase gates, recovery costs
