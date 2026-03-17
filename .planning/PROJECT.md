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

### Active — v10.0 Axiom Commercial Release

- [ ] PyPI Trusted Publisher activation — create `axiom-laboratories` org, `axiom-sdk` project, configure OIDC (RELEASE-01)
- [ ] GHCR multi-arch image publishing on version tag — activate existing release workflow (RELEASE-02)
- [ ] Public documentation access — evaluate `/docs/` public exposure for open-source adoption (RELEASE-03)
- [ ] Job output capture — stdout/stderr, exit codes stored per execution (OUTPUT-01, OUTPUT-02)
- [ ] Execution history — queryable timeline of past runs per job and per node (OUTPUT-03, OUTPUT-04)
- [ ] Runtime attestation — node signs execution result bundle with mTLS client key; orchestrator verifies (OUTPUT-05, OUTPUT-06, OUTPUT-07)
- [ ] Retry policy — configurable retry count + backoff on failure; each attempt a separate execution record (RETRY-01, RETRY-02, RETRY-03)
- [ ] Environment tags (DEV/TEST/PROD) — nodes declare at enrollment, jobs target by env, CI/CD dispatch API (ENVTAG-01, ENVTAG-02, ENVTAG-03, ENVTAG-04)
- [ ] Licence compliance — LEGAL.md certifi decision, mop-sdk licence field, NOTICE file, paramiko assessment (LICENCE-01..04)

### Planned — Future Milestones

- [ ] Job dependencies (v11.0) — job B runs only after job A succeeds (linear then DAG)
- [ ] Conditional triggers (v11.0) — run job based on outcome of previous job or external signal
- [ ] SLSA provenance — Ed25519-signed build provenance, resource limits, --secret credentials (deferred from v7.0)

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
| Environment tags for CI/CD targeting | Enables DEV→TEST→PROD promotion patterns without separate orchestrator instances | — Pending |
| Job output stored server-side | Nodes are stateless — results must flow back to orchestrator | — Pending |
| MoP-native OAuth device flow (not external OIDC) | Avoids external IdP dependency for v1; OIDC documented as v2 path | ✓ Good |
| Job staging (DRAFT→ACTIVE via dashboard) | Operators review and finalize scheduling before jobs run in production | ✓ Good |
| Private key stays on operator machine | Ed25519 signing in CLI; only signature transmitted to server | ✓ Good |
| Soft-delete for CapabilityMatrix tools | Preserves tool history; reversible; admin can view inactive entries | ✓ Good |
| Smelter enforcement_mode in Config table | No new table; reuses existing key/value store; runtime-configurable | ✓ Good |
| Mirror fail-fast unconditional (enforcement_mode gates only unapproved check) | Prevents silent external fetching; two separate enforcement concerns | ✓ Good |
| Soft-purge for ingredient delete | Preserves mirror files and audit history; is_active=False flag | ✓ Good |
| Image lifecycle status (ACTIVE/DEPRECATED/REVOKED) on puppet_templates | Enrollment and work-pull enforcement without DB joins; status is the authority | ✓ Good |
| Phase 16 (Security & Governance) deferred | No production blockers; provenance/--secret deferred to avoid over-engineering v7.0 | ⚠️ Revisit |
| MkDocs Material over DB-backed wiki | Git-backed markdown, no DB, portable, all Insider features free (9.7.0+) | ✓ Good |
| Two-stage Dockerfile for docs (builder + nginx) | mkdocs serve is not production-safe (GitHub issue #1825) | ✓ Good |
| Caddy `handle /docs/*` + nginx `alias` | `handle_path` strips prefix → silently breaks all CSS/JS asset resolution | ✓ Good |
| openapi.json generated at container build time | No running server required; dummy env vars (postgresql+asyncpg, API_KEY) in Dockerfile builder stage | ✓ Good |
| CLI renamed `axiom-push`; package `axiom-sdk` | Axiom brand alignment; mop-push name retired | ✓ Good |
| CDN verification uses `https://` prefix match | Privacy plugin stores assets under `assets/external/fonts.googleapis.com/` — bare domain grep matches local paths (false positive) | ✓ Good |
| PyPI Trusted Publisher setup deferred | GitHub org `axiom-laboratories` and PyPI project `axiom-sdk` do not exist yet | — Pending |

## Current Milestone: v10.0 Axiom Commercial Release

**Goal:** Activate release infrastructure (PyPI + GHCR), add production-grade job observability with cryptographic runtime attestation, environment-based CI/CD targeting, retry policy, and licence compliance for the dual-licence model.

**Target features:**
- Release infrastructure — PyPI Trusted Publisher + GHCR activation + public docs strategy
- Job output capture + execution history — per-run stdout/stderr, queryable timeline
- Runtime attestation — node signs execution bundle with mTLS client key; orchestrator verifies
- Retry policy — configurable retries + backoff on failure
- Environment tags — DEV/TEST/PROD node tags + job targeting + CI/CD dispatch API
- Licence compliance — LEGAL.md, NOTICE file, mop-sdk licence field, paramiko assessment

## Current State — v9.0 Complete (2026-03-17)

Axiom (formerly Master of Puppets) now ships with a full enterprise documentation site at `/docs/`. The docs container is a standalone MkDocs Material service — air-gapped (CDN-free), auto-generated API reference, task/audience-oriented navigation covering getting started through security hardening and troubleshooting.

The CLI is now `axiom-push` (installable as `axiom-sdk`). GitHub Actions CI/CD pipelines are in place and verified; only the `axiom-laboratories` GitHub org and PyPI project need to be created to activate automated publishing.

**Shipped in v9.0:** Docs container infrastructure (CDN-free, CF Access protected), API reference pipeline, developer docs (architecture + setup + contributing), full operator docs (getting started, Foundry, axiom-push, job scheduling, RBAC, OAuth, mTLS, audit, air-gap), runbooks + FAQ, Axiom rebranding, CI/CD pipelines.

---
*Last updated: 2026-03-17 after v10.0 milestone start — Axiom Commercial Release requirements defined*
