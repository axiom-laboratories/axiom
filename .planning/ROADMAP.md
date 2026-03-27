# Roadmap: Master of Puppets

## Milestones

- ✅ **v1.0–v6.0** — Milestones 1–6 (Production Reliability → Remote Validation) — shipped 2026-03-06/09
- ✅ **v7.0 — Advanced Foundry & Smelter** — Phases 11–15 (shipped 2026-03-16)
- ✅ **v8.0 — mop-push CLI & Job Staging** — Phases 17–19 (shipped 2026-03-15)
- ✅ **v9.0 — Enterprise Documentation** — Phases 20–28 (shipped 2026-03-17)
- ✅ **v10.0 — Axiom Commercial Release** — Phases 29–33 (shipped 2026-03-19)
- ✅ **v11.0 — CE/EE Split Completion** — Phases 34–37 (shipped 2026-03-20)
- ✅ **v11.1 — Stack Validation** — Phases 38–45 (shipped 2026-03-22)
- ✅ **v12.0 — Operator Maturity** — Phases 46–56 (shipped 2026-03-24)
- ✅ **v13.0 — Research & Documentation Foundation** — Phases 57–60 (shipped 2026-03-24)
- ✅ **v14.0 — CE/EE Cold-Start Validation** — Phases 61–65 (shipped 2026-03-25)
- ✅ **v14.1 — First-User Readiness** — Phases 66–70 (shipped 2026-03-26)
- ✅ **v14.2 — Docs on GitHub Pages** — Phase 71 (shipped 2026-03-26)
- ✅ **v14.3 — Security Hardening + EE Licensing** — Phases 72–76 (shipped 2026-03-27)
- 🚧 **v14.4 — Go-to-Market Polish** — Phases 77–80 (in progress)

## Phases

<details>
<summary>✅ v7.0 — Advanced Foundry & Smelter (Phases 11–15) — SHIPPED 2026-03-16</summary>

- [x] **Phase 11: Compatibility Engine** — OS family tagging, runtime deps, API/UI enforcement (completed 2026-03-11)
- [x] **Phase 12: Smelter Registry** — Vetted ingredient catalog, CVE scanning, STRICT/WARNING enforcement (completed 2026-03-15)
- [x] **Phase 13: Package Management & Custom Repos** — Local PyPI + APT mirror sidecars, auto-sync, air-gapped upload, pip.conf/sources.list injection, fail-fast enforcement (completed 2026-03-15)
- [x] **Phase 14: Foundry Wizard UI** — 5-step guided composition wizard with real-time OS filtering and Smelter integration (completed 2026-03-16)
- [x] **Phase 15: Smelt-Check, BOM & Lifecycle** — Post-build ephemeral validation, JSON BOM, package index, image ACTIVE/DEPRECATED/REVOKED lifecycle (completed 2026-03-16)

Archive: `.planning/milestones/v7.0-ROADMAP.md`

</details>

<details>
<summary>✅ v8.0 — mop-push CLI & Job Staging (Phases 17–19) — SHIPPED 2026-03-15</summary>

- [x] **Phase 17: Backend — OAuth Device Flow & Job Staging** — RFC 8628 device flow, ScheduledJob status field, /api/jobs/push with dual-token verification, REVOKED enforcement at dispatch (completed 2026-03-12)
- [x] **Phase 18: mop-push CLI** — mop-push login/push/create commands, Ed25519 signing locally, installable SDK package (completed 2026-03-12)
- [x] **Phase 19: Dashboard Staging View & Governance Doc** — Staging tab, script inspection, one-click Publish, status badges, OIDC v2 architecture doc (completed 2026-03-15)

Archive: `.planning/milestones/v8.0-ROADMAP.md`

</details>

<details>
<summary>✅ v9.0 — Enterprise Documentation (Phases 20–28) — SHIPPED 2026-03-17</summary>

- [x] **Phase 20: Container Infrastructure & Routing** — MkDocs Material container, multi-stage Dockerfile, Caddy routing, nginx alias config, site_url alignment, CF Access policy (completed 2026-03-16)
- [x] **Phase 21: API Reference + Dashboard Integration** — OpenAPI export pipeline, Swagger UI rendering, dashboard Docs.tsx replacement with external link (completed 2026-03-16)
- [x] **Phase 22: Developer Documentation** — Architecture guide with Mermaid diagrams, setup & deployment guide, contributing guide (completed 2026-03-17)
- [x] **Phase 23: Getting Started & Core Feature Guides** — End-to-end first-run walkthrough, Foundry guide, axiom-push CLI guide — establishes nav architecture (completed 2026-03-17)
- [x] **Phase 24: Extended Feature Guides & Security** — Job scheduling, RBAC, OAuth guides + full mTLS, audit log, air-gap security & compliance section (completed 2026-03-17)
- [x] **Phase 25: Runbooks & Troubleshooting** — Symptom-first node, job, and Foundry troubleshooting guides + FAQ (completed 2026-03-17)
- [x] **Phase 26: Axiom Branding & Community Foundation** — CLI rename (axiom-push), README rewrite, CONTRIBUTING + CHANGELOG, GitHub community health files, MkDocs naming pass (completed 2026-03-17)
- [x] **Phase 27: CI/CD, Packaging & Distribution** — GitHub Actions CI + release workflows, installer rebranding, PyPI prerequisites (completed 2026-03-17)
- [x] **Phase 28: Infrastructure Gap Closure** — Restored privacy + offline MkDocs plugins; CDN-free docs build verified; INFRA-06 closed (completed 2026-03-17)

Archive: `.planning/milestones/v9.0-ROADMAP.md`

</details>

<details>
<summary>✅ v10.0 — Axiom Commercial Release (Phases 29–33) — SHIPPED 2026-03-19</summary>

- [x] **Phase 29: Backend Completeness — Output Capture + Retry Wiring** — stdout/stderr capture, script hash, retry fields (attempt_number, job_run_id, retry_after, backoff), timeout enforcement (completed 2026-03-18)
- [x] **Phase 30: Runtime Attestation** — Ed25519 bundle signing on node, RSA PKCS1v15 server verification, attestation_service.py, export endpoint (completed 2026-03-18)
- [x] **Phase 31: Environment Tags + CI/CD Dispatch** — env_tag on nodes/jobs, heartbeat storage, pull_work routing, POST /api/dispatch + status endpoint (completed 2026-03-18)
- [x] **Phase 32: Dashboard UI — Execution History, Retry State, Env Tags** — History view, ExecutionLogModal with attestation badge + attempt tabs, DefinitionHistoryPanel, env tag badges and filter (completed 2026-03-19)
- [x] **Phase 33: Licence Compliance + Release Infrastructure** — LEGAL.md, NOTICE, PEP 639 pyproject.toml, axiom-laboratories org, PyPI OIDC Trusted Publisher, v10.0.0-alpha.1 published (completed 2026-03-18)

Archive: `.planning/milestones/v10.0-ROADMAP.md`

</details>

<details>
<summary>✅ v11.0 — CE/EE Split Completion (Phases 34–37) — SHIPPED 2026-03-20</summary>

- [x] **Phase 34: CE Baseline Fixes** — Stub routers return 402, importlib.metadata, ee_only pytest marker, CE suite clean (completed 2026-03-19)
- [x] **Phase 35: Private EE Repo + Plugin Wiring** — axiom-ee repo, EEPlugin.register(), 15 EE tables, absolute imports, entry_points, CE+EE smoke tests (completed 2026-03-20)
- [x] **Phase 36: Cython .so Build Pipeline** — 12 compiled wheels (py3.11/3.12/3.13 × amd64/aarch64), devpi hosting, compiled wheel smoke tests pass (completed 2026-03-20)
- [x] **Phase 37: Licence Validation + Docs** — Ed25519 offline licence validation, edition badge in dashboard, MkDocs enterprise admonitions (completed 2026-03-20)

Archive: `.planning/milestones/v11.0-ROADMAP.md`

</details>

<details>
<summary>✅ v11.1 — Stack Validation (Phases 38–45) — SHIPPED 2026-03-22</summary>

- [x] **Phase 38: Clean Teardown + Fresh CE Install** — Teardown scripts (soft/hard), CE cold-start verification, admin re-seed safety (completed 2026-03-20)
- [x] **Phase 39: EE Test Keypair + Dev Install** — Ed25519 test keypair, editable EE install with patched key, licence lifecycle edge cases (completed 2026-03-20)
- [x] **Phase 40: LXC Node Provisioning** — 4 Incus containers (DEV/TEST/PROD/STAGING), per-node enrollment, env-tag verification, revoke/re-enroll cycle (completed 2026-03-20)
- [x] **Phase 41: CE Validation Pass** — EE stubs return 402, CE table count assertion, basic job dispatch on CE (completed 2026-03-21)
- [x] **Phase 42: EE Validation Pass** — CE+EE combined install, 28-table assertion, licence gating, admin endpoint RBAC (completed 2026-03-21)
- [x] **Phase 43: Job Test Matrix** — 9 job scenarios: fast/slow/memory/concurrent/env-routing/promotion/crash/bad-sig/revoked-definition (completed 2026-03-21)
- [x] **Phase 44: Foundry + Smelter Deep Pass** — Full wizard flow, STRICT/WARNING modes, build failure edge case, air-gap mirror, build dir cleanup (completed 2026-03-22)
- [x] **Phase 45: Gap Report Synthesis + Critical Fixes** — Living gap report, inline critical patches with regression tests, prioritised v12.0+ backlog (completed 2026-03-22)

Archive: `.planning/milestones/v11.1-ROADMAP.md`

</details>

<details>
<summary>✅ v12.0 — Operator Maturity (Phases 46–56) — SHIPPED 2026-03-24</summary>

- [x] **Phase 46: Tech Debt + Security + Branding** — Foundation cleanup before new features: fix deferred gaps, add security hardening, align UI labels (completed 2026-03-22)
- [x] **Phase 47: CE Runtime Expansion** — Unified `script` task type supporting Python, Bash, and PowerShell runtimes end-to-end (completed 2026-03-22)
- [x] **Phase 48: Scheduled Job Signing Safety** — DRAFT state for stale signatures; skipped fires logged; operator warned before script edits fire (completed 2026-03-22)
- [x] **Phase 49: Pagination, Filtering and Search** — Server-side pagination on Jobs and Nodes; 9-axis job filtering; free-text search; CSV export (completed 2026-03-22)
- [x] **Phase 50: Guided Job Form** — Structured guided form replacing raw JSON for common job submission; Advanced mode available via gate (completed 2026-03-23)
- [x] **Phase 51: Job Detail, Resubmit and Bulk Ops** — Job detail drawer; one-click and edit-then-resubmit; multi-select bulk cancel/resubmit/delete (completed 2026-03-23)
- [x] **Phase 52: Queue Visibility, Node Drawer and DRAINING** — Live Queue view; PENDING diagnosis; per-node detail drawer; DRAINING node state (completed 2026-03-23)
- [x] **Phase 53: Scheduling Health and Data Management** — Scheduling Health panel; missed-fire detection; job templates; execution retention + pinning (completed 2026-03-23)
- [x] **Phase 54: Bug Fix Blitz** — Four targeted code fixes closing 7 gap-closure requirements (completed 2026-03-23)
- [x] **Phase 55: Verification + Docs Cleanup** — Retroactive Phase 48 verification + RT-06 design-decision documentation update (completed 2026-03-24)
- [x] **Phase 56: Integration Bug Fixes** — E2E verification; all 7/7 integration tests passing; 7 requirements closed (completed 2026-03-24)

Archive: `.planning/milestones/v12.0-ROADMAP.md`

</details>

<details>
<summary>✅ v13.0 — Research & Documentation Foundation (Phases 57–60) — SHIPPED 2026-03-24</summary>

- [x] **Phase 57: Research — Parallel Job Swarming** — Design doc covering use case analysis, pull-model impact, and complexity/value recommendation for fan-out swarming (completed 2026-03-24)
- [x] **Phase 58: Research — Organisational SSO** — Design doc covering protocol choice, JWT bridge, RBAC mapping, CF Access integration, air-gap isolation, and 2FA policy (completed 2026-03-24)
- [x] **Phase 59: Documentation** — `.env.example`, Docker deployment section, docs/wiki branding alignment with dashboard, v12.0 feature updates across existing docs (completed 2026-03-24)
- [x] **Phase 60: Quick Reference** — Move HTML files to `quick-ref/`, rebrand to Axiom, update operator guide and course for v12.0 and current architecture (completed 2026-03-24)

Archive: `.planning/milestones/v13.0-ROADMAP.md`

</details>

<details>
<summary>✅ v14.0 — CE/EE Cold-Start Validation (Phases 61–65) — SHIPPED 2026-03-25</summary>

- [x] **Phase 61: LXC Environment and Cold-Start Compose** — Docker-in-LXC provisioner with AppArmor workaround, cold-start compose, PowerShell node fix, EE licence generator (completed 2026-03-24)
- [x] **Phase 62: Agent Scaffolding** — Tester GEMINI.md, HOME isolation, checkpoint protocol, CE/EE scenario scripts (completed 2026-03-25)
- [x] **Phase 63: CE Cold-Start Run** — 6 doc/code gaps found and fixed; all 3 runtimes verified; FRICTION-CE reports produced (completed 2026-03-25)
- [x] **Phase 64: EE Cold-Start Run** — EE plugin activation verified; 3 runtimes confirmed; Execution History EE feature verified; CE-gating gap found (completed 2026-03-25)
- [x] **Phase 65: Friction Report Synthesis** — `cold_start_friction_report.md` — NOT READY verdict; 5 BLOCKERs; cross-edition comparison (completed 2026-03-25)

Archive: `.planning/milestones/v14.0-ROADMAP.md`

</details>

<details>
<summary>✅ v14.1 — First-User Readiness (Phases 66–70) — SHIPPED 2026-03-26</summary>

- [x] **Phase 66: Backend Code Fixes** — CE-gate all execution routes via EE stub; PowerShell arm64 guard; node image verified (completed 2026-03-25)
- [x] **Phase 67: Getting-Started Documentation** — install.md, enroll-node.md, first-job.md rewritten with tab pairs and CLI alternatives (completed 2026-03-26)
- [x] **Phase 68: EE Documentation** — /api/features endpoint and AXIOM_LICENCE_KEY naming corrected throughout (completed 2026-03-26)
- [x] **Phase 69: Fix CI release pipeline version pinning and semver tags** — setuptools-scm dynamic versioning; Docker metadata tag fix (completed 2026-03-26)
- [x] **Phase 70: Fix Getting-Started Doc Regressions** — d['token'] field fix; Cold-Start install tabs; mkdocs --strict CI gate (completed 2026-03-26)

</details>

<details>
<summary>✅ v14.2 — Docs on GitHub Pages (Phase 71) — SHIPPED 2026-03-26</summary>

- [x] **Phase 71: Deploy Docs to GitHub Pages** — Untrack docs/site/, .nojekyll, site_url + offline plugin conditional, OFFLINE_BUILD in Dockerfile, docs-deploy.yml GH Actions workflow, regen_openapi.sh maintenance script (completed 2026-03-26)

Archive: `.planning/milestones/v14.2-ROADMAP.md`

</details>

<details>
<summary>✅ v14.3 — Security Hardening + EE Licensing (Phases 72–76) — SHIPPED 2026-03-27</summary>

- [x] **Phase 72: Security Fixes** — Close 5 CodeQL error-severity alerts (XSS, path injection x4, ReDoS), remove API_KEY hard crash and node-route dependency (completed 2026-03-26)
- [x] **Phase 73: EE Licence System** — Offline licence CLI, Ed25519 signature validation at startup, grace period state machine, boot-log clock-rollback detection, extended /api/licence response, node limit enforcement at enrollment (completed 2026-03-27)
- [x] **Phase 74: Fix EE Licence Display** — Align `useLicence.ts` field mapping with backend response; restore EE badge and Admin licence section (completed 2026-03-27)
- [x] **Phase 75: Secrets Volume + Dead Code Cleanup** — Add `secrets-data` volume to compose so boot.log persists across restarts; remove `vault_service.py` dead code; add `AXIOM_STRICT_CLOCK` to compose; remove `main.py.bak` from git (completed 2026-03-27)
- [x] **Phase 76: v14.3 Tech Debt Cleanup** — Fix stale CI tests in test_licence.py (wrong response shape + renamed app state key), remove dead API_KEY env var from compose.cold-start.yaml, delete orphaned vault_service __pycache__ bytecode (completed 2026-03-27)

Archive: `.planning/milestones/v14.3-ROADMAP.md`

</details>

### 🚧 v14.4 — Go-to-Market Polish (In Progress)

**Milestone Goal:** Remove the three biggest first-user friction points (licence UX, signing ceremony, install docs) and establish an external conversion surface (marketing homepage on GitHub Pages).

- [x] **Phase 77: Licence Banner Polish** — Admin-visible amber/red banner with session-scoped dismiss, role guard, and DEGRADED_CE non-dismissible variant (completed 2026-03-27)
- [x] **Phase 78: CLI Signing UX** — Fix `AXIOM_URL` env var, add `key generate` and `init` subcommands, update signing docs (completed 2026-03-27)
- [x] **Phase 79: Install Docs Cleanup** — Remove bundled test nodes from cold-start compose and update install.md atomically (completed 2026-03-27)
- [x] **Phase 80: GitHub Pages Deploy + Marketing Homepage** — Fix docs deploy workflow to `/docs/` subdirectory, then add marketing homepage to repo root (completed 2026-03-27)

## Phase Details

### Phase 77: Licence Banner Polish
**Goal**: Admin users can see and act on licence state warnings without other roles being distracted by unactionable alerts
**Depends on**: Nothing (banner component already exists in MainLayout.tsx)
**Requirements**: BNR-01, BNR-02, BNR-03, BNR-04, BNR-05
**Success Criteria** (what must be TRUE):
  1. Admin user visiting any dashboard page sees an amber banner when the licence is in GRACE state
  2. Admin user visiting any dashboard page sees a red banner when the licence is in DEGRADED_CE state
  3. Admin user can dismiss the amber GRACE banner and it does not reappear for the rest of that browser session
  4. The red DEGRADED_CE banner has no dismiss control and remains visible until the licence state changes
  5. Operator and viewer users see no licence banner regardless of licence state
**Plans**: 1 plan

Plans:
- [ ] 77-01-PLAN.md — Role-guard + dismiss: MainLayout banner polish

### Phase 78: CLI Signing UX
**Goal**: A new user can generate a signing keypair and register it with the server using only the `axiom-push` CLI, with no openssl ceremony required
**Depends on**: Nothing (CLI changes are additive, no backend API changes needed)
**Requirements**: CLI-01, CLI-02, CLI-03, CLI-04
**Success Criteria** (what must be TRUE):
  1. Running `axiom-push` with `AXIOM_URL` set connects to the correct server (the `MOP_URL` silent mismatch is fixed)
  2. Running `axiom-push key generate` produces a local Ed25519 keypair without requiring openssl or any external tool
  3. Running `axiom-push init` completes login, key generation, and public key registration in a single interactive flow
  4. `first-job.md` presents `axiom-push init` as the primary getting-started path with `key generate` documented as the standalone alternative
**Plans**: 2 plans

Plans:
- [ ] 78-01-PLAN.md — CLI implementation: AXIOM_URL fix, key generate, init flow (mop_sdk/)
- [ ] 78-02-PLAN.md — Doc restructure: first-job.md with axiom-push init as primary path

### Phase 79: Install Docs Cleanup
**Goal**: A new user following `install.md` starts a clean Axiom stack with no phantom node services or stale JOIN_TOKEN references
**Depends on**: Nothing (pure YAML deletion + doc prose update, no code changes)
**Requirements**: INST-01, INST-02
**Success Criteria** (what must be TRUE):
  1. Running `docker compose -f compose.cold-start.yaml up -d` starts only Axiom services — no puppet-node-1, puppet-node-2, or their associated volumes
  2. `install.md` contains no references to bundled JOIN_TOKENs, JOIN_TOKEN_1, or JOIN_TOKEN_2
**Plans**: 1 plan

Plans:
- [ ] 79-01-PLAN.md — Atomic cleanup: remove bundled node services from compose, rename tabs and fix prose in install.md

### Phase 80: GitHub Pages Deploy + Marketing Homepage
**Goal**: The project has a public marketing homepage at the GitHub Pages root that coexists with the MkDocs docs site at `/docs/` without either overwriting the other on push
**Depends on**: Phase 78 (homepage can honestly claim a sub-30-minute setup path only after signing UX is fixed), Phase 79 (homepage install instructions must match the clean compose)
**Requirements**: MKTG-01, MKTG-02
**Success Criteria** (what must be TRUE):
  1. Pushing a docs change triggers `docs-deploy.yml` and the rendered MkDocs output appears at `axiom-laboratories.github.io/axiom/docs/` without touching the homepage
  2. Pushing a homepage change triggers `homepage-deploy.yml` and the updated `index.html` appears at `axiom-laboratories.github.io/axiom/` without touching the docs subdirectory
  3. A visitor to `axiom-laboratories.github.io/axiom/` sees a marketing page with hero copy, security positioning, CE/EE comparison, and a link to the docs
**Plans**: 2 plans

Plans:
- [ ] 80-01-PLAN.md — Docs deploy fix: ghp-import prefix mode + site_url update
- [ ] 80-02-PLAN.md — Marketing homepage: source files + homepage-deploy workflow

## Progress

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|----------------|--------|-----------|
| 46. Tech Debt + Security + Branding | v12.0 | 3/3 | Complete | 2026-03-22 |
| 47. CE Runtime Expansion | v12.0 | 4/4 | Complete | 2026-03-22 |
| 48. Scheduled Job Signing Safety | v12.0 | 2/2 | Complete | 2026-03-22 |
| 49. Pagination, Filtering and Search | v12.0 | 6/6 | Complete | 2026-03-22 |
| 50. Guided Job Form | v12.0 | 3/3 | Complete | 2026-03-23 |
| 51. Job Detail, Resubmit and Bulk Ops | v12.0 | 4/4 | Complete | 2026-03-23 |
| 52. Queue Visibility, Node Drawer and DRAINING | v12.0 | 5/5 | Complete | 2026-03-23 |
| 53. Scheduling Health and Data Management | v12.0 | 6/6 | Complete | 2026-03-23 |
| 54. Bug Fix Blitz | v12.0 | 2/2 | Complete | 2026-03-23 |
| 55. Verification + Docs Cleanup | v12.0 | 2/2 | Complete | 2026-03-24 |
| 56. Integration Bug Fixes | v12.0 | 1/1 | Complete | 2026-03-24 |
| 57. Research — Parallel Job Swarming | v13.0 | 1/1 | Complete | 2026-03-24 |
| 58. Research — Organisational SSO | v13.0 | 1/1 | Complete | 2026-03-24 |
| 59. Documentation | v13.0 | 3/3 | Complete | 2026-03-24 |
| 60. Quick Reference | v13.0 | 3/3 | Complete | 2026-03-24 |
| 61. LXC Environment and Cold-Start Compose | v14.0 | 3/3 | Complete | 2026-03-24 |
| 62. Agent Scaffolding | v14.0 | 3/3 | Complete | 2026-03-25 |
| 63. CE Cold-Start Run | v14.0 | 4/4 | Complete | 2026-03-25 |
| 64. EE Cold-Start Run | v14.0 | 3/3 | Complete | 2026-03-25 |
| 65. Friction Report Synthesis | v14.0 | 1/1 | Complete | 2026-03-25 |
| 66. Backend Code Fixes | v14.1 | 3/3 | Complete | 2026-03-25 |
| 67. Getting-Started Documentation | v14.1 | 3/3 | Complete | 2026-03-26 |
| 68. EE Documentation | v14.1 | 1/1 | Complete | 2026-03-26 |
| 69. Fix CI release pipeline version pinning and semver tags | v14.1 | 1/1 | Complete | 2026-03-26 |
| 70. Fix Getting-Started Doc Regressions | v14.1 | 1/1 | Complete | 2026-03-26 |
| 71. Deploy Docs to GitHub Pages | v14.2 | 2/2 | Complete | 2026-03-26 |
| 72. Security Fixes | v14.3 | 2/2 | Complete | 2026-03-26 |
| 73. EE Licence System | v14.3 | 3/3 | Complete | 2026-03-27 |
| 74. Fix EE Licence Display | v14.3 | 1/1 | Complete | 2026-03-27 |
| 75. Secrets Volume + Dead Code Cleanup | v14.3 | 1/1 | Complete | 2026-03-27 |
| 76. v14.3 Tech Debt Cleanup | v14.3 | 1/1 | Complete | 2026-03-27 |
| 77. Licence Banner Polish | 1/1 | Complete    | 2026-03-27 | - |
| 78. CLI Signing UX | 2/2 | Complete    | 2026-03-27 | - |
| 79. Install Docs Cleanup | 1/1 | Complete    | 2026-03-27 | - |
| 80. GitHub Pages Deploy + Marketing Homepage | 2/2 | Complete    | 2026-03-27 | - |

## Archived

- ✅ **v14.3 — Security Hardening + EE Licensing** (Phases 72–76) — shipped 2026-03-27 → `.planning/milestones/v14.3-ROADMAP.md`
- ✅ **v14.2 — Docs on GitHub Pages** (Phase 71) — shipped 2026-03-26 → `.planning/milestones/v14.2-ROADMAP.md`
- ✅ **v14.1 — First-User Readiness** (Phases 66–70) — shipped 2026-03-26 → `.planning/milestones/v14.1-ROADMAP.md`
- ✅ **v14.0 — CE/EE Cold-Start Validation** (Phases 61–65) — shipped 2026-03-25 → `.planning/milestones/v14.0-ROADMAP.md`
- ✅ **v13.0 — Research & Documentation Foundation** (Phases 57–60) — shipped 2026-03-24 → `.planning/milestones/v13.0-ROADMAP.md`
- ✅ **v12.0 — Operator Maturity** (Phases 46–56) — shipped 2026-03-24 → `.planning/milestones/v12.0-ROADMAP.md`
- ✅ **v11.1 — Stack Validation** (Phases 38–45) — shipped 2026-03-22 → `.planning/milestones/v11.1-ROADMAP.md`
- ✅ **v11.0 — CE/EE Split Completion** (Phases 34–37) — shipped 2026-03-20 → `.planning/milestones/v11.0-ROADMAP.md` | phases → `v11.0-phases/`
- ✅ **v10.0 — Axiom Commercial Release** (Phases 29–33) — shipped 2026-03-19 → `.planning/milestones/v10.0-ROADMAP.md`
- ✅ **v9.0 — Enterprise Documentation** (Phases 20–28) — shipped 2026-03-17 → `.planning/milestones/v9.0-ROADMAP.md`
- ✅ **v8.0 — mop-push CLI & Job Staging** (Phases 17–19) — shipped 2026-03-15 → `.planning/milestones/v8.0-ROADMAP.md`
- ✅ **v7.0 — Advanced Foundry & Smelter** (Phases 11–15) — shipped 2026-03-16 → `.planning/milestones/v7.0-ROADMAP.md`
- ✅ **v6.0 — Remote Environment Validation** (Phases 6–10) — shipped 2026-03-06/09 → `.planning/milestones/v6.0-phases/`
- ✅ **v5.0 — Notifications & Webhooks** (Phases 1–3) — shipped 2026-03-06 → `.planning/milestones/v5.0-phases/`
- ✅ **v4.0 — Automation & Integration** (Phases 1–3) — shipped 2026-03-06 → `.planning/milestones/v4.0-phases/`
- ✅ **v3.0 — Advanced Foundry & Hot-Upgrades** (Phases 1–4) — shipped 2026-03-05 → `.planning/milestones/v3.0-phases/`
- ✅ **v2.0 — Foundry & Node Lifecycle** (Phases 1–4) — shipped 2026-03-05 → `.planning/milestones/v2.0-phases/`
- ✅ **v1.0 — Production Reliability** (Phases 1–6) — shipped 2026-03-05 → `.planning/milestones/v1.0-phases/`

### Phase 81: Homepage enterprise messaging — SSO narrative, compliance framing, and conversion optimisation

**Goal:** The Axiom marketing homepage has a credible enterprise trust section, a working conversion path to a Google Form, and EE framing that signals early-access availability rather than vaporware
**Requirements**: TBD
**Depends on:** Phase 80
**Plans:** 1 plan

Plans:
- [ ] 81-01-PLAN.md — Security posture section, EE card update, CTA anchor fixes, and early-access badge
