# Master of Puppets

## What This Is

**Axiom** — a secure, fully-featured task and job scheduler built for hostile environments. A central orchestrator manages a mesh of worker nodes using a pull architecture — nodes poll for work according to their declared capabilities. Security is structural, not bolted-on: mTLS between all components, Ed25519-signed scripts required before execution, all jobs isolated in containers inside the node's environment.

Operators submit Python, Bash, or PowerShell jobs via a guided dispatch form or raw JSON, with full retry traceability, resubmit-from-detail, and bulk cancel/resubmit/delete. A live Queue view with WebSocket updates and per-node detail drawer with DRAINING state machine gives real-time visibility into job execution. Scheduling health tracking (fire logs, LATE/MISSED detection, job templates, retention config) and 9-axis job filtering make large-scale operation practical.

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

### Validated — v12.0 Operator Maturity

- ✓ SQLite-portable NodeStats pruning (two-pass DELETE), Foundry build dir cleanup, permission cache pre-warm at lifespan startup — v12.0
- ✓ SECURITY_REJECTED audit log entries with script hash context (SEC-01); HMAC-SHA256 integrity on signature_payload fields (SEC-02) — v12.0
- ✓ Foundry UI label rename: Blueprint → Image Recipe, Template → Node Image, Capability Matrix → Tool (BRAND-01) — v12.0
- ✓ Unified `script` task type supporting Python, Bash, and PowerShell via container temp-file mounts; `python_script` alias removed (returns HTTP 422) — v12.0
- ✓ Server-authoritative `display_type` field (`script (python)`, `script (bash)`, `script (powershell)`) — v12.0
- ✓ Runtime column on ScheduledJob; scheduler dispatches with `task_type="script"` + `runtime` from definition — v12.0
- ✓ Scheduled job DRAFT transition on script edit (soft, not hard HTTP 400); verbatim skip-log; APScheduler Alert on ACTIVE→DRAFT — v12.0
- ✓ Frontend DRAFT warning modal intercepts script saves; inline Re-sign dialog on DRAFT job rows — v12.0
- ✓ Cursor pagination on Jobs (load-more, `next_cursor`); page-based pagination on Nodes; both with total counts — v12.0
- ✓ 9-axis job filter bar (status, runtime, task type, node, tags, created-by, date ranges) with dismissible chips — v12.0
- ✓ Free-text job search by name or GUID; job name stamped at creation — v12.0
- ✓ Streaming GET /jobs/export CSV endpoint — v12.0
- ✓ Guided dispatch form (Name/Runtime/Script/Targeting/Sign) with live JSON preview; Advanced mode via one-way confirmation gate — v12.0
- ✓ Job detail drawer: inline stdout/stderr, node health at execution time, retry state, PENDING diagnosis — v12.0
- ✓ One-click resubmit + edit-then-resubmit with `originating_guid` provenance tracked — v12.0
- ✓ Multi-select with floating bulk action bar: bulk cancel, bulk resubmit, bulk delete — v12.0
- ✓ DRAINING node state machine (drain/undrain endpoints, pull_work guard, auto-offline transition) — v12.0
- ✓ Live Queue.tsx view (WebSocket-driven, active/recent sections, per-PENDING DRAINING badge) — v12.0
- ✓ Per-node detail drawer: running job, queued jobs, 24h history, capabilities, drain/undrain admin controls — v12.0
- ✓ Dispatch diagnosis endpoint + PENDING diagnosis callout in job detail drawer — v12.0
- ✓ APScheduler ScheduledFireLog with LATE/MISSED detection; GET /health/scheduling endpoint — v12.0
- ✓ JobDefinitions three-tab layout: Definitions / Health / Templates; HealthTab with recharts sparklines + Sheet drawer — v12.0
- ✓ Job templates CRUD (save-as-template strips signing fields; load pre-populates guided form) — v12.0
- ✓ Execution record pin/unpin (pinned records exempt from pruning); audit-logged — v12.0
- ✓ Admin retention config (global default + per-definition override); nightly pruner — v12.0
- ✓ Per-job execution CSV export from job detail drawer — v12.0
- ✓ Node identity persistence: `_load_or_generate_node_id()` scans secrets/ for existing cert on startup — v12.0
- ✓ `--userns=keep-id` removed from Podman runtime (caused sysfs OCI permission failure with VFS storage driver) — v12.0

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

### Validated — v13.0 Research & Documentation Foundation

- ✓ Parallel job swarming design doc — use case analysis, pull-model race condition solution, tiered build/defer recommendation — v13.0
- ✓ Organisational SSO design doc — OIDC recommendation, JWT bridge, RBAC group mapping, 5 IdP coverage, CF Access integration, EE air-gap isolation, 2FA interaction policy — v13.0
- ✓ `.env.example` operator reference — all required and optional environment variables documented with descriptions and generation commands — v13.0
- ✓ Docker deployment guide added to docs site covering env var requirements end-to-end — v13.0
- ✓ Axiom branding aligned across docs site — Fira Sans fonts, crimson primary colour, geometric SVG logo matching dashboard identity — v13.0
- ✓ Jobs and Nodes feature guides created — unified `script` type, guided form, bulk ops, Queue Monitor, DRAINING state all documented — v13.0
- ✓ Quick-reference HTML files integrated into MkDocs under `docs/docs/quick-ref/`; root originals removed; course rebranded to Axiom; operator guide updated for v12.0 — v13.0

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
| Unified `script` task type; `python_script` alias dropped (RT-06) | Cleaner dispatch model; alias would require maintaining two validation paths; returns HTTP 422 with clear message | ✓ Good |
| DRAFT transition (soft) over hard HTTP 400 on stale-signature script edit | Hard reject blocked operators from even seeing the edit form; DRAFT lets them save and re-sign in a separate step | ✓ Good |
| Cursor pagination for jobs, page-based for nodes | Jobs table is large and filtered — cursor avoids expensive COUNT(*) on every page; nodes are small — page numbers are useful UX | ✓ Good |
| One-way Advanced mode gate (guided → advanced, cannot return without reset) | Prevents JSON corruption from partial form state; resets to blank guided form instead of roundtripping | ✓ Good |
| `originating_guid` on Job model for resubmit lineage | No separate table needed; single nullable FK captures full provenance chain for n-depth resubmit | ✓ Good |
| DRAINING auto-offline after no heartbeat (not immediate) | Graceful degradation — DRAINING node finishes running jobs, then auto-transitions OFFLINE only when heartbeat stops | ✓ Good |
| ScheduledFireLog as separate table (not on Job) | Jobs table is already large and hot; fire log is append-only analytics — separation keeps job queries fast | ✓ Good |
| `--userns=keep-id` removed from Podman runtime | Caused sysfs OCI permission denied (exit 126) when running Podman inside Docker with VFS storage driver; rootless mapping unnecessary for job containers | ✓ Good |
| Two-stage Dockerfile for docs (builder + nginx) | mkdocs serve is not production-safe (GitHub issue #1825) | ✓ Good |
| Caddy `handle /docs/*` + nginx `alias` | `handle_path` strips prefix → silently breaks all CSS/JS asset resolution | ✓ Good |
| openapi.json generated at container build time | No running server required; dummy env vars (postgresql+asyncpg, API_KEY) in Dockerfile builder stage | ✓ Good |
| CLI renamed `axiom-push`; package `axiom-sdk` | Axiom brand alignment; mop-push name retired | ✓ Good |
| CDN verification uses `https://` prefix match | Privacy plugin stores assets under `assets/external/fonts.googleapis.com/` — bare domain grep matches local paths (false positive) | ✓ Good |
| PyPI Trusted Publisher + OIDC via GitHub Actions | Avoids long-lived tokens; OIDC trust between GitHub Actions and PyPI is zero-credential | ✓ Good |
| job_run_id groups all retry attempts | Enables per-run history queries without denormalising attempt data | ✓ Good |
| Attestation verification never raises exceptions | Verification failure is a status (attestation_verified="FAILED"), not a crash — keeps execution record regardless | ✓ Good |
| outerjoin Job on list_executions for max_retries | ExecutionRecord has no max_retries column — join pulls it from the parent Job; NULL for orphaned records | ✓ Good |

## Current Milestone: v14.0 CE/EE Cold-Start Validation

**Goal:** Validate Axiom's install and operator paths end-to-end using Gemini CLI agents as first-time users inside LXC containers, covering both CE and EE scenarios across all job runtimes.

**Target features:**
- LXC-based test environment (full Axiom Docker stack + puppet nodes inside a single container)
- Gemini CLI tester agents with docs-only access and file-based checkpoint steering
- CE cold-start: install path + operator path (Python, Bash, PowerShell jobs)
- EE cold-start: install path + operator path + EE-gated features (with pre-generated licence)
- Friction report synthesising findings from both runs

## Previous State — v13.0 Complete (2026-03-24)

Axiom v13.0 delivered the Research & Documentation Foundation milestone — 4 phases, 8 plans, all 17 requirements satisfied. Two design documents now exist as build artefacts: a parallel job swarming architecture doc (use case analysis, pull-model race conditions, tiered build/defer recommendation) and an organisational SSO design doc (OIDC protocol choice, JWT bridge, RBAC group mapping for 5 IdPs, Cloudflare Access integration, EE air-gap isolation pattern, 2FA interaction policy). These ground the next feature milestone without requiring protocol or architecture decisions to be re-litigated.

On the documentation side: `.env.example` is now a complete operator reference with generation commands for cryptographic vars; a "Running with Docker" deployment guide was added; the docs site visual identity (Fira Sans, crimson palette, geometric SVG logo) now matches the dashboard; and existing feature guides were updated to cover v12.0 additions (unified `script` type, guided form, bulk ops, Queue Monitor, DRAINING state, Scheduling Health). The two standalone HTML quick-reference files were moved from the project root into the MkDocs tree under `docs/docs/quick-ref/`, the course was fully rebranded to Axiom, and the operator guide was updated with Queue and Scheduling Health content.

**~23,500 LOC (Python + TypeScript). Stack: FastAPI + SQLAlchemy + React/Vite + Caddy + APScheduler + MkDocs Material.**

**Known deferred:** EE-08 (PyPI stub wheel), DIST-02 (Docker Hub CE publish), Phase 16 SLSA provenance, job dependencies/DAG, SSO implementation (design complete, v14.0+ candidate), swarming implementation (deferred pending further spike).

---
*Last updated: 2026-03-24 after v14.0 milestone start — CE/EE Cold-Start Validation*
