# Master of Puppets

## What This Is

A secure, fully-featured task and job scheduler built for hostile environments. A central orchestrator ("Puppeteer") manages a mesh of worker nodes ("Puppets") using a pull architecture — nodes poll for work according to their declared capabilities. Security is structural, not bolted-on: mTLS between all components, Ed25519-signed scripts required before execution, all jobs isolated in containers inside the puppet's environment.

Targets homelab and enterprise internal deployments where nodes may be shared or partially untrusted. Designed to integrate with CI/CD pipelines for environment-tagged deployment promotion (DEV → TEST → PROD).

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

### Active

- [ ] Job output capture — stdout/stderr, exit codes, per-execution records
- [ ] Execution history — queryable timeline of past runs per job and per node
- [ ] Retry policy — configurable retries on failure (count, backoff strategy)
- [ ] Job dependencies — job B runs only after job A succeeds
- [ ] Environment node tags — DEV / TEST / PROD tags for CI/CD promotion targeting
- [ ] CI/CD API integration — documented, machine-friendly endpoints for dispatching jobs from pipelines
- [ ] Conditional triggers — run job based on outcome of previous job or external signal

### Out of Scope

- Mobile app — web-first, API covers automation needs
- Silent security weakening — any trade-off must be explicitly documented and operator opt-in
- Built-in secrets management beyond Fernet-at-rest — use external vault for production secrets
- Real-time collaborative editing of scripts — single author, versioned by signing

## Context

Existing codebase is functional and deployed. Backend is FastAPI + SQLAlchemy (SQLite dev, Postgres prod). Frontend is React/Vite. Node agent is Python, runs inside Docker. Infrastructure uses Caddy (TLS termination) + Cloudflare tunnel for dashboard access.

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

## Planned: Milestone 8 — mop-push CLI & Job Staging

**Goal:** Zero-friction job signing and publishing from the operator's terminal. A dedicated `mop-push` CLI authenticates via OAuth device flow, signs scripts locally with Ed25519, and pushes jobs into a Staging area. Dashboard provides draft review, scheduling finalization, and one-click publish.

**Target features:**
- OAuth device flow built into MoP Control Plane (MoP is the IdP; external OIDC as v2)
- `mop-push` CLI: login, job push (draft/upsert), job create (direct active)
- Self-hosted Python package from `mop_sdk/` — private key never leaves operator machine
- `ScheduledJob` status enum: DRAFT / ACTIVE / DEPRECATED / REVOKED
- `POST /api/jobs/push` upsert endpoint with dual-token verification (JWT identity + Ed25519 integrity)
- Dashboard Staging/Drafts view: inspect, finalize scheduling, one-click publish
- Job status badges across job list; REVOKED jobs never dispatched to nodes

## Current Milestone: Milestone 7 — Advanced Foundry & Smelter

**Goal:** Transition the Foundry from a manual blueprint CRUD system to an intelligent, compatibility-aware composition engine with a built-in package registry and governance layer.

**Target features:**
- Smelter Registry: vetted ingredient catalog with CVE scanning and STRICT enforcement
- Compatibility Engine: OS-family filtering, runtime dependency mapping, API validation
- Advanced Package Management: native OS packages, PIP pre-baking, global core injection
- Custom Repos: APT/APK + GPG, built-in PyPI store (pypiserver sidecar), repo presets
- Foundry Wizard UI: 5-step guided composition replacing raw JSON blueprint editing
- Smelt-Check: mandatory dry-run validator (ephemeral container, validation_cmd per tool)
- Image BOM + Lifecycle: bill of materials in DB, ACTIVE/DEPRECATED/REVOKED enforcement
- Security: SLSA provenance docs, build-time secrets (docker --secret), resource limits

---
*Last updated: 2026-03-09 after Milestone 7 kickoff*
