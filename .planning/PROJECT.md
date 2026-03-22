# Master of Puppets

## What This Is

**Axiom** — a secure, fully-featured task and job scheduler built for hostile environments. A central orchestrator manages a mesh of worker nodes using a pull architecture — nodes poll for work according to their declared capabilities. Security is structural, not bolted-on: mTLS between all components, Ed25519-signed scripts required before execution, all jobs isolated in containers inside the node's environment.

Targets homelab and enterprise internal deployments where nodes may be shared or partially untrusted. Ships with a full enterprise documentation site (`/docs/`) covering every operator and developer workflow, from getting started through security hardening and troubleshooting. Designed to integrate with CI/CD pipelines for environment-tagged deployment promotion (DEV → TEST → PROD).

## Core Value

Jobs run reliably — on the right node, when scheduled, with their output captured — without any step in the chain weakening the security model.

## Requirements

### Validated

- ✓ mTLS node enrollment (Root CA, client cert signing, CRL revocation) — existing
- ✓ Ed25519 job signing — scripts verified before execution — existing
- ✓ Container-isolated job execution (Docker/Podman, configurable mode) — existing
- ✓ Pull architecture — nodes poll `/work/pull`, orchestrator never pushes — existing
- ✓ Node capability matching (runtime, OS) for job targeting — existing
- ✓ Explicit node/group targeting alongside capability matching — existing
- ✓ RBAC with admin / operator / viewer roles (DB-backed permissions) — existing
- ✓ Web dashboard (React) + REST API (FastAPI) — existing
- ✓ Cron-scheduled job definitions (APScheduler) — existing
- ✓ Foundry: build custom node images from runtime + network blueprints — existing
- ✓ Node stats history + sparkline monitoring — existing
- ✓ Full audit log for security-relevant events — existing
- ✓ Service principals + API keys for machine-to-machine auth — existing
- ✓ OAuth device flow (RFC 8628) — MoP-native IdP, browser approval, JWT issuance — v8.0
- ✓ `mop-push` CLI — login/push/create, Ed25519 signing locally, private key never transmitted — v8.0
- ✓ Job lifecycle status (DRAFT/ACTIVE/DEPRECATED/REVOKED) + REVOKED dispatch enforcement — v8.0
- ✓ Dashboard Staging view — inspect drafts, finalize scheduling, one-click Publish — v8.0
- ✓ Foundry Compatibility Engine — OS-family tagging, runtime deps, two-pass blueprint validation, real-time tool filtering — v7.0
- ✓ Smelter Registry — vetted ingredient catalog, CVE scanning (pip-audit), STRICT/WARNING enforcement, compliance badging — v7.0
- ✓ Package Repository Mirroring — local PyPI + APT sidecars, auto-sync, air-gapped upload, pip.conf/sources.list injection, fail-fast — v7.0
- ✓ Foundry Wizard UI — 5-step guided composition wizard with OS filtering and Smelter integration — v7.0
- ✓ Smelt-Check + BOM + Image Lifecycle — post-build validation, JSON BOM, package index, ACTIVE/DEPRECATED/REVOKED enforcement — v7.0

### Validated — v9.0 Enterprise Documentation

- ✓ MkDocs Material docs container — standalone docs service at `/docs/`, two-stage Dockerfile, air-gapped (CDN-free) — v9.0
- ✓ Dashboard integration — sidebar "Docs" link to external docs site; in-app renderer removed — v9.0
- ✓ Auto-generated API reference — OpenAPI snapshot at build time, Swagger UI in MkDocs — v9.0
- ✓ Developer documentation — architecture guide (Mermaid), setup/deployment, contributing guide, pyproject.toml — v9.0
- ✓ User getting started guide — end-to-end first-run walkthrough (install → node → first job) — v9.0
- ✓ Feature guides — Foundry, Smelter, axiom-push CLI, job scheduling, RBAC, OAuth, Staging — v9.0
- ✓ Security & compliance guides — mTLS, cert rotation, RBAC hardening, audit log, air-gap operation — v9.0
- ✓ Runbooks & troubleshooting — symptom-first node/job/Foundry guides + FAQ — v9.0
- ✓ Axiom rebranding — CLI renamed `axiom-push`, README rewrite, CONTRIBUTING + CHANGELOG, GitHub community health files, full MkDocs naming pass — v9.0
- ✓ CI/CD pipelines — GitHub Actions CI (pytest + vitest + docker-validate) + release workflow (multi-arch GHCR + PyPI OIDC) — v9.0

### Validated — v10.0 Axiom Commercial Release

- ✓ PyPI Trusted Publisher activation — `axiom-laboratories` org created, OIDC configured on test.pypi.org + pypi.org, v10.0.0-alpha.1 published — v10.0
- ✓ GHCR multi-arch image publishing on version tag — release.yml triggered on tag push — v10.0
- ✓ Public documentation access — CF Access protects `/docs/`; open-source release strategy documented — v10.0
- ✓ Job output capture — stdout/stderr, exit codes stored per execution in ExecutionRecord — v10.0
- ✓ Execution history — queryable via GET /api/executions with node/status/job/run filters, dashboard History view — v10.0
- ✓ Runtime attestation — Ed25519 bundle signing on node, RSA PKCS1v15 server verification, export endpoint, UI badge — v10.0
- ✓ Retry policy — configurable max_retries + backoff, each attempt separate ExecutionRecord; max_retries in API response — v10.0
- ✓ Environment tags (DEV/TEST/PROD) — nodes declare in heartbeat, jobs target by env_tag, CI/CD dispatch API (POST /api/dispatch) — v10.0
- ✓ Licence compliance — LEGAL.md certifi decision, axiom-sdk licence field, NOTICE file, paramiko assessment complete — v10.0

### Validated — v11.1 Stack Validation

- ✓ Idempotent soft teardown (PKI-preserving) + hard teardown (true clean slate) scripts — v11.1
- ✓ CE install verification: 13-table count, all features false, admin re-seed safety — v11.1
- ✓ EE test keypair infrastructure: editable axiom-ee install with patched public key, no Cython rebuild — v11.1
- ✓ Licence lifecycle edge cases verified: valid / expired / absent AXIOM_LICENCE_KEY — v11.1
- ✓ 4 LXC nodes (DEV/TEST/PROD/STAGING) provisioned with unique per-node JOIN_TOKENs, revoke/re-enroll verified — v11.1
- ✓ CE/EE validation pass: 7 EE stub routes return 402 on CE; 28 tables on CE+EE; all feature flags true; licence startup-gating — v11.1
- ✓ Job test matrix: 8/9 scenarios PASS with genuine live execution — fast/slow/concurrent/env-routing/promotion/crash/bad-sig/revoked — v11.1
- ✓ Foundry + Smelter deep pass scripted: STRICT CVE block, bad-base 500 error, air-gap mirror with iptables isolation, WARNING mode — v11.1
- ✓ v11.1 gap report: 11 findings, 4 critical patches applied inline with regression tests, v12.0+ backlog seeded — v11.1

### Validated — v11.0 CE/EE Split Completion

- ✓ CE stub routers return 402 (not 404) for all 7 EE routes on CE-only install — v11.0
- ✓ `importlib.metadata` replaces deprecated `pkg_resources` for EE plugin discovery — v11.0
- ✓ `ee_only` pytest marker auto-skips EE tests in CE runs; CE suite passes clean — v11.0
- ✓ `NodeConfig` stripped of EE-only fields; `job_service.py` dead-field refs removed — v11.0
- ✓ `axiom-ee` private repo: `EEPlugin` wires 7 routers + 15 EE SQLAlchemy tables via `entry_points` — v11.0
- ✓ Absolute imports throughout EE codebase; async `load_ee_plugins` correctly awaited in CE lifespan — v11.0
- ✓ Cython `.so` build pipeline: 12 compiled wheels (py3.11/3.12/3.13 × amd64/aarch64 × manylinux/musllinux) — v11.0
- ✓ devpi internal wheel index in compose.server.yaml; compiled wheel CE+EE smoke tests pass — v11.0
- ✓ Ed25519 offline licence validation gates all EE features at startup (air-gap safe) — v11.0
- ✓ CE/EE edition badge in dashboard sidebar (useLicence hook + LicenceSection in Admin) — v11.0
- ✓ MkDocs `!!! enterprise` admonitions on 5 EE feature pages; `licensing.md` CE/EE explainer — v11.0

### Active — Future Milestones

- [ ] Job dependencies — job B runs only after job A succeeds (linear then DAG)
- [ ] Conditional triggers — run job based on outcome of previous job or external signal
- [ ] SLSA provenance — Ed25519-signed build provenance, resource limits, --secret credentials (deferred from v7.0)
- [ ] DIST-02: `axiom-ce` image on Docker Hub (deferred from v11.0 — GHCR covers current use)
- [ ] EE-08: Full `axiom-ee` stub wheel publication to PyPI (deferred from v11.0)
- [ ] DIST-04: Licence issuance portal — web UI or automated pipeline for signed licence key delivery
- [ ] DIST-05: Periodic licence re-validation (currently startup-only)
- [ ] EE-09: OIDC/SAML SSO integration
- [ ] EE-10: Custom RBAC roles + fine-grained permissions

### Out of Scope

- Mobile app — web-first, API covers automation needs
- Silent security weakening — any trade-off must be explicitly documented and operator opt-in
- Built-in secrets management beyond Fernet-at-rest — use external vault for production secrets
- Real-time collaborative editing of scripts — single author, versioned by signing

## Context

Codebase is functional, deployed, and fully documented. Backend is FastAPI + SQLAlchemy (SQLite dev, Postgres prod). Frontend is React/Vite. Node agent is Python, runs inside Docker. Infrastructure uses Caddy (TLS termination) + Cloudflare tunnel for dashboard access.

Documentation site lives at `/docs/` — MkDocs Material, git-backed markdown in `docs/`, containerised with nginx, air-gapped (CDN-free). API reference is auto-generated from FastAPI OpenAPI schema at container build time.

CLI is `axiom-push` (formerly `mop-push`) — installable as `axiom-sdk` Python package. GitHub Actions CI/CD pipelines in place for multi-arch GHCR images and PyPI publishing (awaiting `axiom-laboratories` org creation).

Known deferred issues: SQLite NodeStats pruning compat (MIN-6), Foundry build dir cleanup (MIN-7), per-request DB query in require_permission (MIN-8), non-deterministic node ID scan order (WARN-8). See `.agent/reports/core-pipeline-gaps.md`.

The security model is zero-trust by default. Any feature that requires relaxing mTLS, skipping signature verification, or running jobs outside containers must be treated as a configuration option with explicit documentation of the risk — never a code default.

## Constraints

- **Security**: mTLS + signed code + container isolation are non-negotiable architectural constants. Trade-offs may be documented for operator opt-in but never silently defaulted.
- **Tech stack**: FastAPI (Python) backend, React/TypeScript frontend, SQLAlchemy ORM. No migrations framework — `create_all` at startup, manual ALTER for existing DBs.
- **Execution model**: Pull-only. Orchestrator never initiates connections to nodes. Nodes are stateless between polls.
- **Compatibility**: SQLite for dev/homelab, Postgres for production. New features must work on both.

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Pull architecture (nodes poll orchestrator) | No inbound firewall rules on nodes; works across NAT/hostile networks | ✓ Good |
| Ed25519 signing required for all jobs | Prevents arbitrary code execution even if orchestrator is compromised | ✓ Good |
| Container-per-job isolation | Memory leak containment, runtime isolation, OS-level security boundary | ✓ Good |
| RBAC seeded from DB, not config files | Supports org-wide teams without redeployment | ✓ Good |
| Environment tags for CI/CD targeting | Enables DEV→TEST→PROD promotion patterns without separate orchestrator instances | ✓ Good |
| Job output stored server-side | Nodes are stateless — results must flow back to orchestrator | ✓ Good |
| MoP-native OAuth device flow (not external OIDC) | Avoids external IdP dependency for v1; OIDC documented as v2 path | ✓ Good |
| Job staging (DRAFT→ACTIVE via dashboard) | Operators review and finalize scheduling before jobs run in production | ✓ Good |
| Private key stays on operator machine | Ed25519 signing in CLI; only signature transmitted to server | ✓ Good |
| Soft-delete for CapabilityMatrix tools | Preserves tool history; reversible; admin can view inactive entries | ✓ Good |
| Smelter enforcement_mode in Config table | No new table; reuses existing key/value store; runtime-configurable | ✓ Good |
| Mirror fail-fast unconditional (enforcement_mode gates only unapproved check) | Prevents silent external fetching; two separate enforcement concerns | ✓ Good |
| Soft-purge for ingredient delete | Preserves mirror files and audit history; is_active=False flag | ✓ Good |
| Image lifecycle status (ACTIVE/DEPRECATED/REVOKED) on puppet_templates | Enrollment and work-pull enforcement without DB joins; status is the authority | ✓ Good |
| Phase 16 (Security & Governance) deferred | No production blockers; provenance/--secret deferred to avoid over-engineering v7.0 | ⚠️ Revisit |
| Cython over Nuitka for EE compilation | Nuitka multi-module wheel workflow undocumented; Cython is established standard with cibuildwheel support | ✓ Good |
| `packages=[]` + `exclude_package_data` to strip .py from wheel | Prevents source exposure while keeping `__init__.py` for package structure | ✓ Good |
| `__init__.py` excluded from `ext_modules` | CPython bug #59828 — compiled `__init__` breaks relative imports; `__init__.py` must stay as plain Python | ✓ Good |
| Ed25519 offline licence validation (no call-home) | Air-gapped deployments are a core use case — online validation would block them | ✓ Good |
| devpi for internal EE wheel hosting | Simple HTTP index in compose.server.yaml; no auth needed for internal use; easy to swap for PyPI later | ✓ Good |
| DIST-02 (Docker Hub CE publish) deferred to v12.0+ | GHCR covers all current deployment scenarios; Docker Hub adds registry maintenance burden for no immediate benefit | ✓ Good |
| MkDocs Material over DB-backed wiki | Git-backed markdown, no DB, portable, all Insider features free (9.7.0+) | ✓ Good |
| Two-stage Dockerfile for docs (builder + nginx) | mkdocs serve is not production-safe (GitHub issue #1825) | ✓ Good |
| Caddy `handle /docs/*` + nginx `alias` | `handle_path` strips prefix → silently breaks all CSS/JS asset resolution | ✓ Good |
| openapi.json generated at container build time | No running server required; dummy env vars (postgresql+asyncpg, API_KEY) in Dockerfile builder stage | ✓ Good |
| CLI renamed `axiom-push`; package `axiom-sdk` | Axiom brand alignment; mop-push name retired | ✓ Good |
| CDN verification uses `https://` prefix match | Privacy plugin stores assets under `assets/external/fonts.googleapis.com/` — bare domain grep matches local paths (false positive) | ✓ Good |
| PyPI Trusted Publisher + OIDC via GitHub Actions | Avoids long-lived tokens; OIDC trust between GitHub Actions and PyPI is zero-credential | ✓ Good |
| job_run_id groups all retry attempts | Enables per-run history queries without denormalising attempt data | ✓ Good |
| Attestation verification never raises exceptions | Verification failure is a status (attestation_verified="FAILED"), not a crash — keeps execution record regardless | ✓ Good |
| outerjoin Job on list_executions for max_retries | ExecutionRecord has no max_retries column — join pulls it from the parent Job; NULL for orphaned records | ✓ Good |

## Current Milestone: v12.0 — Operator Maturity

**Goal:** Make the day-to-day operator experience materially better — multi-runtime job execution, guided job form, failure visibility, queue diagnosis, bulk operations, search/filtering/pagination, and a tech debt sweep.

**Target features:**
- CE runtime expansion (Python/Bash/PowerShell unified `script` task type)
- Guided job form + Advanced mode + job detail drawer + resubmit
- Bulk job operations (cancel/resubmit/delete)
- PENDING diagnosis + live Queue dashboard + node detail drawer + DRAINING
- Scheduling Health panel on Dashboard; scheduled job DRAFT state for stale signing
- Server-side pagination + 9-axis job filtering + job templates + execution retention
- Tech debt: MIN-06/07/08, WARN-08
- Security: SECURITY_REJECTED audit log, HMAC signature payload integrity
- EE UI label rename (Blueprint → Image Recipe, PuppetTemplate → Node Image)

---

## Current State — v11.1 Complete (2026-03-22)

Axiom v11.1 completed an adversarial end-to-end validation of the full CE/EE stack. The platform is confirmed deployable from a clean install through a reproducible teardown/install cycle, with 4 environment-tagged LXC nodes covering the full job execution matrix (9 scenarios), licence lifecycle edge cases (valid/expired/absent), and Foundry/Smelter scripted validation. A gap report (11 findings) was synthesised; 4 critical issues were patched inline with regression tests; the v12.0+ backlog is seeded.

The stack is stable and fully documented. The CE/EE open-core architecture (Cython `.so` EE extensions, Ed25519 offline licence validation, devpi wheel hosting) was validated operationally. Known deferred gaps: MIN-06/07/08/WARN-08 and the EE-stack Foundry pass (requires EE stack with AXIOM_LICENCE_KEY).

**Shipped in v11.1:** Teardown scripts (Phase 38), EE test infrastructure (Phase 39), LXC provisioning (Phase 40), CE/EE validation passes (Phases 41–42), job matrix (Phase 43), Foundry/Smelter pass (Phase 44), gap synthesis + patches (Phase 45).

**Known deferred:** EE-08 (PyPI stub wheel), DIST-02 (Docker Hub CE publish), MIN-06/07/08/WARN-08 (tech debt from gap report — addressed in v12.0).

---
*Last updated: 2026-03-22 after v12.0 milestone started — Operator Maturity*
