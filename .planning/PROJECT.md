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

### Validated — v14.2 Docs on GitHub Pages

- ✓ `docs/site/` untracked from git; build output gitignored — clean history for CI deploys — v14.2
- ✓ `.nojekyll` in docs source root — prevents Jekyll stripping MkDocs underscore assets on GitHub Pages — v14.2
- ✓ `mkdocs.yml` `site_url` set to `https://axiom-laboratories.github.io/axiom/` — correct relative URL generation — v14.2
- ✓ Offline plugin conditional on `OFFLINE_BUILD` env var — disabled for GH Pages, enabled in Docker air-gap builds — v14.2
- ✓ `docs-deploy.yml` GitHub Actions workflow — path-filtered auto-deploy on `docs/**` push to main, `mkdocs gh-deploy --force` — v14.2
- ✓ `docs/scripts/regen_openapi.sh` — local operator script to regenerate `openapi.json` after API schema changes — v14.2

### Validated — v14.1 First-User Readiness

- ✓ CE-gated all 7 execution-history API routes with 402 stubs; `ee/interfaces/executions.py` + `ee/routers/executions_router.py` via EE plugin — v14.1
- ✓ PowerShell arm64 platform guard in `Containerfile.node` (`TARGETARCH` conditional) — silent build failure on non-amd64 hosts eliminated — v14.1
- ✓ `install.md` rewritten: admin password setup step, CLI/Cold-Start tab pairs, GHCR install path for users without GitHub access — v14.1
- ✓ `enroll-node.md` rewritten: CLI `curl` JOIN_TOKEN path, correct `AGENT_URL` table (`https://agent:8001` for cold-start), Docker socket mount note, `EXECUTION_MODE=docker` — v14.1
- ✓ `first-job.md`: pre-dispatch `!!! danger` callout + Dashboard/CLI tab pair; `axiom-push` as CLI hero command; CE curl fallback in collapsible block — v14.1
- ✓ EE docs: all `/api/admin/features` references replaced with `/api/features`; `AXIOM_EE_LICENCE_KEY` purged from `licensing.md` — v14.1
- ✓ `setuptools-scm` dynamic versioning in `pyproject.toml` — eliminates TestPyPI duplicate-version 400 errors — v14.1
- ✓ `release.yml` Docker metadata tag fix (`type=ref,event=tag` replacing broken semver patterns) — v14.1
- ✓ `d['token']` field extraction fix in `enroll-node.md` CLI tab (was silently returning empty string) — v14.1
- ✓ Cold-Start install tabs added to `install.md` Steps 3–4; `mkdocs --strict` CI gate added to `ci.yml` — v14.1

### Validated — v14.0 CE/EE Cold-Start Validation

- ✓ LXC Docker-in-LXC provisioner (`provision_coldstart_lxc.py`) with AppArmor pivot_root workaround, Gemini CLI, Playwright — v14.0
- ✓ `compose.cold-start.yaml` cold-start stack with hardcoded `SERVER_HOSTNAME` for SAN correctness, PowerShell 7.6 direct .deb install — v14.0
- ✓ EE test licence generator with 1-year expiry, `axiom-coldstart-test` customer ID, upserts `AXIOM_EE_LICENCE_KEY` in `secrets.env` — v14.0
- ✓ Tester `GEMINI.md` with docs-only first-user persona, HOME isolation (`/root/validation-home`) preventing session bleed — v14.0
- ✓ File-based checkpoint protocol (`monitor_checkpoint.py`): Gemini writes `PROMPT.md`, host operator steers via `RESPONSE.md`, 5-minute graceful timeout — v14.0
- ✓ CE/EE scenario scripts with per-step PASS/FAIL checklists and checkpoint trigger conditions — v14.0
- ✓ CE cold-start run: 6 critical doc/code gaps identified and patched (EXECUTION_MODE, node image tag, AGENT_URL, admin password, JOIN_TOKEN CLI path, docs site path) — v14.0
- ✓ EE cold-start run: EE plugin activated with injected licence; all 3 runtimes (Python/Bash/PowerShell) confirmed COMPLETED; Execution History EE feature verified — v14.0
- ✓ CE-gating gap found: `/api/executions` returns HTTP 200 in CE mode (not 402) — ungated in `main.py`; documented for next milestone — v14.0
- ✓ `synthesise_friction.py` (stdlib-only, offline) + `cold_start_friction_report.md` — NOT READY verdict; 5 BLOCKERs; cross-edition comparison table — v14.0

### Validated — v13.0 Research & Documentation Foundation

- ✓ Parallel job swarming design doc — use case analysis, pull-model race condition solution, tiered build/defer recommendation — v13.0
- ✓ Organisational SSO design doc — OIDC recommendation, JWT bridge, RBAC group mapping, 5 IdP coverage, CF Access integration, EE air-gap isolation, 2FA interaction policy — v13.0
- ✓ `.env.example` operator reference — all required and optional environment variables documented with descriptions and generation commands — v13.0
- ✓ Docker deployment guide added to docs site covering env var requirements end-to-end — v13.0
- ✓ Axiom branding aligned across docs site — Fira Sans fonts, crimson primary colour, geometric SVG logo matching dashboard identity — v13.0
- ✓ Jobs and Nodes feature guides created — unified `script` type, guided form, bulk ops, Queue Monitor, DRAINING state all documented — v13.0
- ✓ Quick-reference HTML files integrated into MkDocs under `docs/docs/quick-ref/`; root originals removed; course rebranded to Axiom; operator guide updated for v12.0 — v13.0

### Validated — v14.3 Security Hardening + EE Licensing

- ✓ `html.escape()` on OAuth device-approve `user_code` — XSS reflected injection eliminated (SEC-01) — v14.3
- ✓ `validate_path_within()` helper in `security.py` — path traversal guards for vault artifact paths and docs download route (SEC-02, SEC-03) — v14.3
- ✓ Bounded email regex `{1,64}` / `{1,63}` quantifiers in `mask_pii()` — catastrophic ReDoS eliminated (SEC-04) — v14.3
- ✓ API_KEY hard crash removed — server boots cleanly with no API_KEY env var; `verify_api_key` removed from all node-facing routes (SEC-05) — v14.3
- ✓ `X-Content-Type-Options: nosniff` on CSV export — content-sniffing XSS vector closed (SEC-06) — v14.3
- ✓ `tools/generate_licence.py` offline CLI — Ed25519-signed JWT keys with customer ID, tier, node limit, expiry, grace days; no network call required (LIC-01) — v14.3
- ✓ `licence_service.py` EdDSA JWT verification — VALID/GRACE/EXPIRED/CE state machine; invalid signatures fall to CE; grace period arithmetic; `GET /api/licence` returns 6-field response (LIC-02, LIC-03, LIC-04, LIC-06) — v14.3
- ✓ Hash-chained `secrets/boot.log` clock-rollback detection — EE raises on rollback; CE warns only; `check_and_record_boot(licence_status)` parameter-driven (LIC-05) — v14.3
- ✓ `POST /api/enroll` HTTP 402 when active node count ≥ `node_limit` — air-gap-safe node limit enforcement (LIC-07) — v14.3
- ✓ `secrets-data` named Docker volume — `boot.log` and `licence.key` persist across `compose down/up` cycles — v14.3
- ✓ Dashboard EE badge, grace/expired banner, Admin licence section aligned to backend response shape — v14.3

### Active — Future Milestones

- [ ] Job dependencies — job B runs only after job A succeeds (linear then DAG)
- [ ] Conditional triggers — run job based on outcome of previous job or external signal
- [ ] SLSA provenance — Ed25519-signed build provenance, resource limits, --secret credentials (deferred from v7.0)
- [ ] DIST-02: `axiom-ce` image on Docker Hub (deferred from v11.0 — GHCR covers current use)
- [ ] EE-08: Full `axiom-ee` stub wheel publication to PyPI (deferred from v11.0)
- [ ] DIST-04: Licence issuance portal — web UI or automated pipeline for signed licence key delivery
- [ ] DIST-05: Periodic licence re-validation (currently startup-only; APScheduler 6h re-check deferred to v15+)
- [ ] EE-09: OIDC/SAML SSO integration (design doc complete in v13.0)
- [ ] EE-10: Custom RBAC roles + fine-grained permissions
- [ ] Dashboard GRACE/DEGRADED_CE amber/red banner (backend API landed in v14.3; frontend component deferred)

### Out of Scope

- Mobile app — web-first, API covers automation needs
- Silent security weakening — any trade-off must be explicitly documented and operator opt-in
- Built-in secrets management beyond Fernet-at-rest — use external vault for production secrets
- Real-time collaborative editing of scripts — single author, versioned by signing

## Context

Codebase is functional, deployed, security-hardened, and commercially ready (v14.3). Backend is FastAPI + SQLAlchemy (SQLite dev, Postgres prod). Frontend is React/Vite. Node agent is Python, runs inside Docker. Infrastructure uses Caddy (TLS termination) + Cloudflare tunnel for dashboard access.

Documentation site lives at `/docs/` (containerised, air-gapped) and is **publicly accessible at `https://axiom-laboratories.github.io/axiom/`** (GitHub Pages, auto-deployed via `docs-deploy.yml` on every `docs/**` push to `main`). MkDocs Material, CDN-free, `mkdocs --strict` enforced in CI. API reference is auto-generated from FastAPI OpenAPI schema at container build time; `docs/scripts/regen_openapi.sh` refreshes the pre-committed snapshot locally.

CLI is `axiom-push` (formerly `mop-push`) — installable as `axiom-sdk` Python package. GitHub Actions CI/CD pipelines in place for multi-arch GHCR images and PyPI publishing via OIDC Trusted Publisher. Version is derived dynamically from git tags via `setuptools-scm`.

Getting-started docs (install → enroll-node → first-job) are complete and verified against a real cold-start flow. Both CE and EE paths are documented end-to-end with CLI alternatives for all GUI steps.

EE licence system is fully operational: `tools/generate_licence.py` generates signed keys offline; `licence_service.py` validates at startup; grace period and DEGRADED_CE state machine are enforced. `secrets/boot.log` clock-rollback detection is hardened to use licence status (EE enforces, CE warns). All 6 CodeQL alerts closed.

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
| `raw.apparmor=pivot_root` override for Docker-in-LXC | Ubuntu 24.04 kernel 6.8.x AppArmor policy blocks pivot_root syscall; override required for Docker nesting in Incus (issue #791) | ✓ Good |
| HOME isolation for Gemini tester (`/root/validation-home`) | Prevents session bleed and auto-loading of developer `GEMINI.md` context between test runs | ✓ Good |
| File-based checkpoint protocol (PROMPT.md/RESPONSE.md) | Allows orchestrator to steer blocked Gemini agent without API coupling; 5-minute graceful timeout prevents deadlock | ✓ Good |
| Fixed-during-run BLOCKERs still count as open for verdict | BLOCKERs resolved by orchestrator intervention expose UX/doc gaps even when technically working; NOT READY verdict is correct | ✓ Good |
| `synthesise_friction.py` uses stdlib only | No external API calls or LLM calls for synthesis — deterministic, offline-safe, reproducible output | ✓ Good |
| CE execution stubs in `ee/interfaces/executions.py` (not inline in `main.py`) | Keeps CE/EE boundary clean; real implementations movable to EE router without touching main route file | ✓ Good |
| `setuptools-scm` dynamic versioning (no hardcoded version in `pyproject.toml`) | Eliminates duplicate-version 400 errors on TestPyPI; version derived from git tag automatically | ✓ Good |
| Docker metadata `type=ref,event=tag` (not semver pattern) for release image tags | semver pattern requires exact `vX.Y.Z` format with no pre-release suffix; `event=tag` applies to any tag | ✓ Good |
| `mkdocs --strict` CI gate in `ci.yml` | Catches anchor errors, missing tab extensions, and broken admonitions before they reach main | ✓ Good |
| `d['token']` not `d.get('enhanced_token', d.get('join_token', ''))` for JOIN_TOKEN extraction | `/admin/generate-token` returns `{token: ...}` only — the chained `.get()` silently returned empty string | ✓ Good |
| `!ENV [OFFLINE_BUILD, false]` pattern for offline plugin | Single config file; offline plugin off by default (GitHub Pages), on in Docker builds — no separate mkdocs config files needed | ✓ Good |
| `.nojekyll` in docs source root (not site root) | MkDocs copies it into the built site, landing at GH Pages root — no post-build injection needed | ✓ Good |
| `openapi.json` pre-committed; `regen_openapi.sh` is operator tool | Avoids schema regeneration in CI (no running server); operator runs script locally and commits updated file | ✓ Good |
| `fetch-depth: 0` in docs-deploy.yml | MkDocs Material uses git history for `git_revision_date_localized` on page footers — shallow clone produces wrong dates | ✓ Good |
| `validate_path_within()` in `security.py` (not vault_service.py) | vault_service.py had broken Artifact import — placing helper in security.py makes it importable across all routes without introducing the broken import | ✓ Good |
| EdDSA JWT for licence keys (not RSA) | Ed25519 keys are small, fast, and standard for offline signing; PyJWT supports OKP keys directly | ✓ Good |
| `licence_service.py` in CE code (not EE plugin) | Licence validation must run before EE plugin loads — CE must be able to decide whether to activate EE; placing in EE plugin creates circular dependency | ✓ Good |
| `check_and_record_boot(licence_status)` parameter approach | Removes `AXIOM_STRICT_CLOCK` env bypass; ties enforcement directly to licence tier — EE always enforces, CE always warns; no escape hatch needed for air-gapped ops | ✓ Good |
| Node limit guard before token validation in `enroll_node()` | 402 must fire before 403 so limit is checked even for expired tokens; also prevents consuming a token when limit is already hit | ✓ Good |
| `DEGRADED_CE pull_work` returns `PollResponse(job=None)` silently | HTTPException would disconnect nodes; silent empty response keeps nodes heartbeating while CE features are degraded | ✓ Good |
| `secrets-data` named volume (not bind mount) for boot.log | Named volumes survive `compose down` without operator needing to specify a host path; correct semantics for secrets that must outlive container lifecycle | ✓ Good |

## Previous State — v14.3 Complete (2026-03-27)

Axiom v14.3 delivered Security Hardening + EE Licensing — 5 phases, 8 plans, all 13/13 requirements satisfied. All 6 CodeQL alerts (XSS, path traversal ×4, ReDoS, API_KEY crash, nosniff) are resolved. The EE licence system is fully operational: offline JWT key generation, startup signature validation, VALID/GRACE/EXPIRED/CE state machine, hash-chained boot-log clock-rollback detection (EE enforces, CE warns), node-limit enforcement at enrollment, and a `secrets-data` Docker volume so boot.log persists across restarts. The frontend licence display is aligned to the backend response — EE badge, Admin licence section, and grace/expired banner all work correctly. Three audit tech debt items (stale tests, dead env var, orphaned bytecode) were also closed.

## Previous State — v14.2 Complete (2026-03-26)

Axiom v14.2 delivered Docs on GitHub Pages — 1 phase, 2 plans, all 8 requirements satisfied. The CE documentation site is now publicly accessible at `https://axiom-laboratories.github.io/axiom/` and auto-deploys via GitHub Actions on every push to `main` that touches `docs/**`. The `docs/site/` build output (166 files) was removed from git tracking. The offline MkDocs plugin is now conditional on `OFFLINE_BUILD` so GitHub Pages builds run clean while Docker air-gap container builds retain the bundled asset behaviour. A local `regen_openapi.sh` script lets operators update `openapi.json` when the FastAPI schema changes.

## Previous State — v14.1 Complete (2026-03-26)

Axiom v14.1 delivered the First-User Readiness milestone — 5 phases, 9 plans, 17/17 requirements satisfied. All 12 BLOCKERs from the v14.0 cold-start friction report are resolved. A first-time user following only the published docs can now install Axiom, enroll a node, and dispatch a signed job to completion on both CE and EE — from either the dashboard or the CLI.

Code changes: Execution History routes CE-gated (7 stubs in `ee/interfaces/executions.py`), PowerShell arm64 guard in `Containerfile.node`, `d['token']` extraction fix. Doc changes: `install.md`, `enroll-node.md`, `first-job.md` fully rewritten with tab pairs and CLI alternatives; EE docs corrected (endpoint names, env var naming). CI changes: `setuptools-scm` dynamic versioning, Docker `type=ref,event=tag`, `mkdocs --strict` CI gate.

Tech debt note (from audit): `licensing.md` `/api/licence` JSON example lists 5 of 9 EE features (non-blocking; all 9 shown correctly in `install.md`).

## Previous State — v14.0 Complete (2026-03-25)

Axiom v14.0 delivered the CE/EE Cold-Start Validation milestone — 5 phases, 14 plans, 18 requirements satisfied. A Gemini CLI tester agent was used as a first-time user inside an LXC container running the full Axiom Docker stack. The CE cold-start run uncovered 6 critical doc/code gaps — all fixed mid-milestone (EXECUTION_MODE docs, node image tag, AGENT_URL format, admin password discovery, JOIN_TOKEN CLI path, docs site path). The EE run confirmed the EE plugin activates correctly with a pre-injected licence and all 3 runtimes execute to COMPLETED. The final friction report (`cold_start_friction_report.md`) delivers a NOT READY verdict with 5 open product BLOCKERs for the next milestone to address. A secondary finding — `/api/executions` ungated in CE mode — is also documented. The Gemini API free tier (20–250 RPD) was insufficient for a full autonomous run; Tier 1 paid key required for future runs.

## Previous State — v13.0 Complete (2026-03-24)

Axiom v13.0 delivered the Research & Documentation Foundation milestone — 4 phases, 8 plans, all 17 requirements satisfied. Two design documents now exist as build artefacts: a parallel job swarming architecture doc (use case analysis, pull-model race conditions, tiered build/defer recommendation) and an organisational SSO design doc (OIDC protocol choice, JWT bridge, RBAC group mapping for 5 IdPs, Cloudflare Access integration, EE air-gap isolation pattern, 2FA interaction policy). These ground the next feature milestone without requiring protocol or architecture decisions to be re-litigated.

On the documentation side: `.env.example` is now a complete operator reference with generation commands for cryptographic vars; a "Running with Docker" deployment guide was added; the docs site visual identity (Fira Sans, crimson palette, geometric SVG logo) now matches the dashboard; and existing feature guides were updated to cover v12.0 additions (unified `script` type, guided form, bulk ops, Queue Monitor, DRAINING state, Scheduling Health). The two standalone HTML quick-reference files were moved from the project root into the MkDocs tree under `docs/docs/quick-ref/`, the course was fully rebranded to Axiom, and the operator guide was updated with Queue and Scheduling Health content.

**~23,500 LOC (Python + TypeScript). Stack: FastAPI + SQLAlchemy + React/Vite + Caddy + APScheduler + MkDocs Material.**

**Known deferred:** EE-08 (PyPI stub wheel), DIST-02 (Docker Hub CE publish), Phase 16 SLSA provenance, job dependencies/DAG, SSO implementation (design complete, v14.0+ candidate), swarming implementation (deferred pending further spike).

---
*Last updated: 2026-03-27 after v14.3 milestone — Security Hardening + EE Licensing*
