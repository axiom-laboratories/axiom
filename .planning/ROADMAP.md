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
- 🚧 **v14.3 — Security Hardening + EE Licensing** — Phases 72–75 (in progress)

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

### 🚧 v14.3 — Security Hardening + EE Licensing (In Progress)

**Milestone Goal:** Close all CodeQL security alerts, remove the legacy API_KEY crash, and deliver a production-grade EE licence key system with Ed25519 cryptographic validation, grace-period state machine, clock-rollback detection, and air-gap-safe node limit enforcement.

- [x] **Phase 72: Security Fixes** — Close 5 CodeQL error-severity alerts (XSS, path injection x4, ReDoS), remove API_KEY hard crash and node-route dependency (completed 2026-03-26)
- [x] **Phase 73: EE Licence System** — Offline licence CLI, Ed25519 signature validation at startup, grace period state machine, boot-log clock-rollback detection, extended /api/licence response, node limit enforcement at enrollment (completed 2026-03-27)
- [x] **Phase 74: Fix EE Licence Display** — Align `useLicence.ts` field mapping with backend response; restore EE badge and Admin licence section (completed 2026-03-27)
- [ ] **Phase 75: Secrets Volume + Dead Code Cleanup** — Add `secrets-data` volume to compose so boot.log persists across restarts; remove `vault_service.py` dead code; add `AXIOM_STRICT_CLOCK` to compose; remove `main.py.bak` from git

## Phase Details

### Phase 72: Security Fixes
**Goal**: Operators can deploy Axiom with zero open CodeQL error or warning alerts and without requiring an API_KEY environment variable
**Depends on**: Nothing (Phase 71 complete)
**Requirements**: SEC-01, SEC-02, SEC-03, SEC-04, SEC-05, SEC-06
**Success Criteria** (what must be TRUE):
  1. Operator submitting a crafted `user_code` query parameter to `/auth/device/approve` receives an HTML-escaped response with no reflected XSS payload execution
  2. Operator can start Axiom with no `API_KEY` in `secrets.env` and the process boots cleanly without a crash or error log entry about the missing variable
  3. Node-facing routes (`/api/enroll`, `/work/pull`, `/heartbeat`) continue to function correctly for enrolled nodes after `verify_api_key` dependency is removed
  4. Operator can confirm via the GitHub Security tab that all 5 CodeQL error-severity alerts and 1 warning-severity alert show as resolved after the fixes land on `main`
  5. A job with output containing a crafted email-like string that previously caused catastrophic regex backtracking in `mask_pii()` returns a response within normal processing time
**Plans**: 2 plans
Plans:
- [ ] 72-01-PLAN.md — Test scaffolds (Wave 0 RED tests for all 6 SEC requirements)
- [ ] 72-02-PLAN.md — Security fixes (XSS, path traversal x2, ReDoS, API_KEY removal, nosniff)

### Phase 73: EE Licence System
**Goal**: Axiom Labs can generate signed licence keys offline and EE deployments enforce cryptographic licence validity, expiry grace periods, clock-rollback detection, and node limits — all without requiring network access
**Depends on**: Phase 72
**Requirements**: LIC-01, LIC-02, LIC-03, LIC-04, LIC-05, LIC-06, LIC-07
**Success Criteria** (what must be TRUE):
  1. Axiom Labs operator runs `tools/generate_licence.py` offline and receives a base64url-encoded signed licence key that encodes customer ID, tier, node limit, feature list, expiry date, and grace days — with no network call required
  2. An EE deployment given a licence key whose Ed25519 signature does not match the embedded public key fails to activate EE features at startup and logs a clear rejection message
  3. An EE deployment whose licence has expired but is within `grace_days` boots successfully, activates all EE features, and emits a log warning indicating days remaining in the grace period
  4. An EE deployment whose grace period has also ended returns HTTP 402 on all EE feature routes (matching CE stub behaviour) without crashing or logging unhandled exceptions
  5. `GET /api/licence` returns a JSON response containing `status` (valid/grace/expired), `days_until_expiry`, `node_limit`, and `tier` fields readable by an operator
  6. `POST /api/enroll` returns HTTP 402 when the number of non-OFFLINE non-REVOKED nodes already enrolled equals or exceeds the `node_limit` in the signed licence payload
**Plans**: 3 plans
Plans:
- [ ] 73-01-PLAN.md — RED test scaffold (7 failing tests for LIC-01 through LIC-07)
- [ ] 73-02-PLAN.md — licence_service.py + tools/generate_licence.py (LIC-01 to LIC-05 GREEN)
- [ ] 73-03-PLAN.md — main.py integration: lifespan, /api/licence, enroll limit, pull_work guard (LIC-06/07 GREEN)

### Phase 74: Fix EE Licence Display
**Goal**: Operators with a valid EE licence see correct edition, expiry, and tier in the dashboard
**Depends on**: Phase 73
**Requirements**: LIC-06
**Gap Closure**: Closes gaps from v14.3 audit
**Success Criteria** (what must be TRUE):
  1. Admin with a valid EE licence loads the Admin page and sees tier "enterprise" (not "Community") in the licence section
  2. MainLayout.tsx EE badge shows "EE" (not "CE") when a valid EE licence is loaded
  3. Expiry date renders as a human-readable date derived from `days_until_expiry`
**Plans**: 1 plan
Plans:
- [ ] 74-01-PLAN.md — Fix useLicence.ts interface, update Admin.tsx and MainLayout.tsx; add grace/expired banner and status badge

### Phase 75: Secrets Volume + Dead Code Cleanup
**Goal**: Clock-rollback detection survives container restarts; vault dead code removed; compose fully documents env vars
**Depends on**: Phase 73
**Requirements**: LIC-05, SEC-02
**Gap Closure**: Closes gaps from v14.3 audit
**Success Criteria** (what must be TRUE):
  1. `docker compose down && docker compose up -d` preserves `secrets/boot.log` across the restart cycle
  2. `vault_service.py` is removed from the codebase (or fully wired with Artifact ORM + routes); no `ImportError` on import
  3. `main.py.bak` is no longer tracked by git
  4. `AXIOM_STRICT_CLOCK` is present (commented) in `compose.server.yaml` agent service env block
**Plans**: 1 plan
Plans:
- [ ] 75-01-PLAN.md — RED tests (LIC-05 strict mode + SEC-02 vault sentinel) + licence_service refactor + vault deletion + compose volumes + git cleanup

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
| 74. Fix EE Licence Display | 1/1 | Complete    | 2026-03-27 | — |
| 75. Secrets Volume + Dead Code Cleanup | v14.3 | 0/1 | Pending | — |

## Archived

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
