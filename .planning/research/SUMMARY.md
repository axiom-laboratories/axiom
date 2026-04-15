# Project Research Summary

**Project:** Master of Puppets Axiom — Integrated Hardening Initiative (Container Security + EE Licensing + Foundry/Smelter + DAG Workflows)  
**Domain:** Enterprise container orchestration platform with security hardening, software supply chain integrity, multi-ecosystem package management, and workflow automation  
**Researched:** 2026-04-01 to 2026-04-15  
**Confidence:** HIGH (direct codebase inspection, established standards, production-validated patterns)

---

## Executive Summary

Master of Puppets Axiom is entering a major evolution: transitioning from a single-job dispatch platform to a comprehensive enterprise automation system with four interconnected hardening workstreams. This research synthesizes findings across **Container Security Hardening** (eliminate privilege escalation via non-root execution + capability dropping), **EE Licence Protection** (software supply chain integrity via signed wheels + clock-rollback detection), **Foundry/Smelter Improvements** (multi-ecosystem package management with transitive dependency resolution + CVE scanning), and **DAG/Workflow Orchestration** (complex multi-step jobs with conditional branching + webhook triggers).

The recommended approach is **phased rollout with clear infrastructure gates**: Core infrastructure work (container hardening, wheel signing, workflow DAG model) happens in early phases, followed by ecosystem expansion (APT/APK/npm/NuGet mirrors) and operator UX refinement. This ordering avoids five critical pitfalls identified in the research: **race conditions in concurrent step completion, partial failure states breaking cascade logic, depth limit bypasses enabling DoS, webhook replay attacks, and backward compatibility gaps** with existing scheduled jobs.

**Key strategic insight:** All work leverages existing infrastructure (Python stdlib, cryptography v46, Docker socket, APScheduler) with **zero new third-party dependencies required** for container hardening and EE licensing features. The stack is mature, battle-tested in production systems, and requires only targeted additions for Foundry ecosystem expansion (pip-tools, verdict sidecars). **Critical risk mitigation:** The workflow engine introduces five concurrency and security hazards that must be mitigated atomically in Phase 3 — no feature can ship without explicit guards for concurrent completion, output validation, and replay protection.

---

## Key Findings

### Recommended Stack

**Container Hardening & EE Licensing use ONLY existing dependencies.**

**Core production technologies (no changes):**
- Python 3.12 stdlib (hmac, hashlib, importlib.metadata, json, pathlib, zipfile) — all required for HMAC boot log integrity, wheel signature verification, entry point validation, and secure file operations
- cryptography v46.0.5 (existing) — Ed25519 operations verified working for licence JWTs; identical APIs used for wheel manifest verification
- PyJWT v2.7.0+ (existing) — EdDSA support (RFC 8037) for licence tokens
- Docker Compose v3.7+ (existing) — cap_drop, cap_add, security_opt, deploy.resources directives supported since 2019
- Standard Linux userland (addgroup/useradd/usermod) — no packages needed

**Foundry/Smelter ecosystem expansion (new packages — optional features only):**
- pip-tools ≥7.4 — deterministic transitive dep resolution via `pip-compile`
- bandit ≥1.8 — Python script security scanning (subprocess mode)
- react-d3-tree@3.6.6 (frontend) — interactive dep-tree viewer (React 19 compatible)
- Mirror sidecars: pypiserver (existing), Caddy (existing), nginx:alpine, Verdaccio:6 (npm), BaGetter (NuGet), miniconda3 (Conda), registry:2 (OCI)

**Confidence: HIGH.** All components documented in official sources; proven in production systems.

---

### Expected Features

**Must Have (Table Stakes):**

*Container Security:*
- Non-root user execution (appuser:appuser, UID 1000)
- Linux capability dropping (cap_drop: ALL)
- No-new-privileges enforcement (setuid/setgid prevention)
- Resource limits (memory + CPU per service)
- Hardened Dockerfile base images (Alpine/Debian)
- Docker socket mount (remove privileged: true)
- Podman compatibility (two-runtime support)
- Read-only root filesystem support

*EE Licensing:*
- Signed wheel manifest verification (PEP 427 Ed25519 signature)
- HMAC boot log clock-rollback detection (keyed on ENCRYPTION_KEY)
- Per-node licence seat management (HTTP 402 on enrollment limit)
- Entry point whitelist validation (prevent plugin hijacking)

*Foundry/Smelter:*
- Transitive dependency resolution (full dep tree visibility)
- Multi-ecosystem package management (APT, APK, npm, NuGet, Conda, OCI)
- CVE scan of transitive deps (pre-build vulnerability discovery)

*Workflows:*
- DAG/workflow orchestration (multi-step jobs with conditional branching)
- Graceful EE→CE fallback (license expiry → DEGRADED_CE, no crash)
- Workflow versioning + pause/resume (prevent ghost execution from cron)

**Should Have (Competitive Differentiators):**

- Entry point whitelist (zero-trust plugin loading)
- Offline licence generation (air-gapped issuers)
- Script analyzer (static AST/regex import detection + bundle recommendations)
- Curated bundles (Data Science, Web Scraping, Infrastructure, Monitoring)
- Webhook replay protection (nonce tracking + timestamp validation)
- IF gate sandboxing (restrict to single-field comparisons, no eval)

**Defer (v20+):**
- Conda full channel sync (HIGH storage footprint; defer unless data science is explicit ICP)
- Custom seccomp profiles (host-level config; defer to ops docs)
- Advanced IF gate logic (AND/OR/nested conditions; v19 ships single-field only)
- Workflow execution analytics + critical path tracing

---

### Architecture Approach

The architecture is a **layered, modular extension** of existing services. Core patterns remain unchanged; new components follow established patterns (throwaway containers for resource-heavy operations, async semaphores for concurrency control, DB tables via EEBase for EE features).

**New service components:**

1. **resolver_service.py** — Spawns throwaway Docker containers per ecosystem to resolve full transitive dependency trees. Uses same Docker socket + asyncio pattern as existing Foundry builds. Gated by `_resolve_semaphore = asyncio.Semaphore(3)`.

2. **script_analyzer_service.py** — In-process synchronous Python AST/regex analysis to extract package imports from job scripts. Returns matched ingredients + bundle suggestions. <50ms latency; no async overhead.

3. **wheel_service.py** — Verifies signed wheels (ZIP format per PEP 427). Validates Ed25519 signature on RECORD manifest. Checks file hashes. Called before `pip install` in EE plugin bootstrap.

4. **workflow_service.py** — CRUD for Workflow + WorkflowStep models. DAG validation (depth limit 12, cycle detection, resource reservation). Dispatches workflow as job sequence with IF gates + transitive failure propagation.

**Extended service components:**

- **foundry_service.py** — Injects multi-ecosystem package manager configs (pip.conf, apt sources.list, npm .npmrc, conda condarc, nuget.config). Appends `USER appuser` to generated Dockerfiles.

- **mirror_service.py** — Ecosystem dispatch table replaces OS-family-based routing. Each `_mirror_<eco>()` uses throwaway containers. Separate named volumes per ecosystem.

- **job_service.py** — BFS cascade refactored to atomic SELECT...FOR UPDATE + single background sweep task (100ms interval). Validates result.json before unblocking dependents.

**DB tables (EE — created via EEBase):**
- `ingredient_dependencies` (parent_id, dep_name, version, ecosystem, depth, auto_approved, mirror_status)
- `curated_bundles` (name, description, category, is_builtin)
- `curated_bundle_items` (bundle_id, ingredient_name, version_constraint, ecosystem)

---

### Critical Pitfalls

1. **Race Condition in Concurrent Step Completion** — Multiple independent jobs completing simultaneously causes BFS unblock engine to process them serially without atomic guards, resulting in double-execution or orphaned jobs. **Mitigation:** SELECT...FOR UPDATE transaction locks, idempotent guard (last_unblock_attempt_at), single background sweep task, concurrent completion test suite.

2. **PARTIAL Failures Break Cascade Logic** — Jobs complete successfully but output validation fails. IF gate reads corrupted result.json, routes to wrong step silently. **Mitigation:** Add VALIDATION_FAILED status (terminal, non-COMPLETED), validate result.json atomically at completion, transitive failure isolation via failed_upstream_guid.

3. **Depth Limit Bypass via Conditional Unblocking** — Depth check only at creation; conditional dependencies not checked. Attacker bypasses limit, creates exponential cascade on single failure. **Mitigation:** Transitive depth check on all depends_on, batch unblock with backoff, circuit breaker at 1000 unblocks per event.

4. **Webhook Replay Attacks → State Corruption** — Same webhook fires multiple times (network retry, operator error). All jobs unblock 4x, re-execute, corrupt state. **Mitigation:** Nonce tracking (24h TTL), timestamp validation (±300s), X-Webhook-Signature + X-Webhook-Timestamp + X-Webhook-Nonce headers, database-backed idempotency.

5. **Structured Output Injection via IF Gates** — IF gate reads result.json to decide routing. User-controlled output can inject malicious JSON, manipulate control flow. **Mitigation:** JSON schema validation, restrict to single-field comparisons, sandbox expression language (no eval), sign result.json with node key, verify signature.

---

## Implications for Roadmap

Based on combined research, **12-phase phased rollout with clear infrastructure gates:**

### Phase 1: Container Security Hardening
**Delivers:** Non-root execution, cap_drop, no-new-privileges, resource limits, read-only filesystem support, Docker socket mount, Podman variant.  
**Effort:** 5-7 days | **Research flag:** None (CIS/NIST standards)

### Phase 2: Wheel Signing + Boot Log HMAC  
**Delivers:** wheel_service.py, HMAC boot log, entry point whitelist, per-node licence seats, audit logging.  
**Effort:** 4-5 days | **Research flag:** None (PEP 427 standard)

### Phase 3: Workflow DAG Model (Core) — WITH CONCURRENCY SAFEGUARDS
**Delivers:** Workflow + WorkflowStep models, atomic BFS cascade (SELECT...FOR UPDATE), VALIDATION_FAILED status, depth validation, background sweep task, result.json atomicity, pause/resume API, feature flag.  
**Effort:** 7-9 days | **Research flag: REQUIRES RESEARCH PHASE** (atomicity design, deadlock analysis, concurrent completion test matrix)

### Phase 4: Result Validation + IF Gates — WITH INJECTION HARDENING
**Delivers:** Single-field IF gates, JSON schema validation, sandboxed expression language, result.json signing + verification, missing file defaults, IF gate logging.  
**Effort:** 5-6 days | **Research flag:** MEDIUM (Jinja2 vs Lua performance trade-offs)

### Phase 5: DB Schema Additions + Foundry Extensions
**Delivers:** approved_ingredients.ecosystem column (migration), IngredientDependency table, CuratedBundle + CuratedBundleItem tables.  
**Effort:** 2-3 days | **Research flag:** None (standard SQLAlchemy)

### Phase 6: Resolver Service + Mirror Dispatch
**Delivers:** ResolverService, throwaway containers per ecosystem, IngredientDependency population, auto-mirror + CVE scan, dep-tree endpoints.  
**Effort:** 6-8 days | **Research flag:** None (documented CLI tools)

### Phase 7: Mirror Ecosystem Backends + Sidecars
**Delivers:** _mirror_apt/apk/npm/conda/nuget implementations, new sidecars (nginx, Verdaccio, BaGetter), mirror URL config, semaphore limits.  
**Effort:** 8-10 days | **Research flag:** None (standard mirror patterns)

### Phase 8: Script Analyzer + Bundle CRUD
**Delivers:** ScriptAnalyzerService, import_to_pypi.json mapping, analyze-script endpoint, CuratedBundle CRUD, seeded starter packs, frontend "Analyze" button.  
**Effort:** 4-5 days | **Research flag:** None (AST + regex standard)

### Phase 9: CVE Scan Extension + Transitive Include
**Delivers:** Extended scan_vulnerabilities() with IngredientDependency rows.  
**Effort:** 2-3 days | **Research flag:** None (pip-audit standard)

### Phase 10: Webhook Support + Nonce Tracking
**Delivers:** WebhookNonce table, POST /api/webhooks endpoint, header validation (Signature/Timestamp/Nonce), signal emission, audit logging.  
**Effort:** 4-5 days | **Research flag:** None (standard webhook patterns)

### Phase 11: EE CRUD Completeness (Edit Blueprint, Tool Recipe, Approved OS)
**Delivers:** PUT /api/blueprints/{id} with version + HTTP 409, PATCH capability-matrix, Approved OS CRUD, runtime dep confirmation modal, frontend edit UI.  
**Effort:** 3-4 days | **Research flag:** None (standard CRUD)

### Phase 12: Backward Compatibility Testing + APScheduler Pause/Resume
**Delivers:** Feature flag ENABLE_WORKFLOW_ENGINE, dual-path tests, startup sanity check, APScheduler pause/resume API, workflow status column, migration guide.  
**Effort:** 4-5 days | **Research flag:** None (feature flags standard)

### Phase Ordering Rationale

**Tier 1 (Sequential):** Phases 1-2-5 (foundation; prerequisites for all downstream)  
**Tier 2 (Parallel infrastructure):** Phases 3, 6-7 (critical-path + ecosystem)  
**Tier 3 (Parallel features):** Phases 4, 8-11 (depends on Phase 3 or 6, orthogonal otherwise)  
**Tier 4 (Validation):** Phase 12 (final gate before workflow launch)

---

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| **Stack** | HIGH | Python stdlib stable (3.8+). cryptography v46 current + backward compatible. Docker Compose v3.7+ production standard (2019+). |
| **Features** | HIGH | Container hardening mandated (NIST/CIS/OWASP). EE patterns from existing codebase v14.3+. Wheel signing follows PEP 427. DAG patterns established (Airflow, Temporal, AWS Step Functions). |
| **Architecture** | HIGH | Direct codebase inspection. Resolver + mirrors follow existing throwaway container pattern. Atomicity (SELECT...FOR UPDATE) standard in distributed systems. Modular + testable. |
| **Pitfalls** | HIGH | Race conditions well-documented; SELECT...FOR UPDATE is standard mitigation. Webhook replay attacks extensively documented (Svix, Hookbin, Cloudflare). Output injection follows LLM prompt injection threat model. Backward compatibility gaps common in migrations. |

**Overall: HIGH**

---

## Sources

- Python stdlib documentation (hmac, hashlib, importlib.metadata, json, pathlib, zipfile)
- cryptography library v46.0.5 Ed25519 API (cryptography.io)
- PEP 427 — Wheel Binary Package Format
- Docker Security Documentation (docs.docker.com)
- OWASP Docker Security Cheat Sheet
- NIST SP 800-190: Container Security
- Webhook Security Best Practices (Svix, hooklistener.com, webhooks.fyi)
- Apache Airflow Troubleshooting & Pitfalls
- Temporal Workflow Orchestration (temporal.io)
- AWS Step Functions: State Machine Design
- Direct codebase inspection: foundry_service.py, mirror_service.py, smelter_service.py, job_service.py, db.py, ee/models/

---

*Research completed: 2026-04-15*  
*Synthesized from STACK.md, FEATURES.md, ARCHITECTURE.md, PITFALLS.md*  
*Ready for roadmap creation: YES*
