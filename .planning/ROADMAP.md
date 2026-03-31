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
- ✅ **v14.4 — Go-to-Market Polish** — Phases 77–81 (shipped 2026-03-28)
- ✅ **v15.0 — Operator Readiness** — Phases 82–86 (shipped 2026-03-29)
- ✅ **v16.0 — Competitive Observability** — Phases 87–91 (shipped 2026-03-30)
- ✅ **v16.1 — PR Merge & Backlog Closure** — Phases 92–95 (shipped 2026-03-30)
- ✅ **v17.0 �� Scale Hardening** — Phases 96–100 (shipped 2026-03-31)
- 🚧 **v18.0 — First-User Experience & E2E Validation** — Phases 101–103 (in progress)

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

<details>
<summary>✅ v14.4 — Go-to-Market Polish (Phases 77–81) — SHIPPED 2026-03-28</summary>

- [x] **Phase 77: Licence Banner Polish** — Admin-visible amber/red banner with session-scoped dismiss, role guard, and DEGRADED_CE non-dismissible variant (completed 2026-03-27)
- [x] **Phase 78: CLI Signing UX** — `AXIOM_URL` env var fix, `key generate` and `init` subcommands, first-job.md restructured with `axiom-push init` as primary path (completed 2026-03-27)
- [x] **Phase 79: Install Docs Cleanup** — Removed bundled test nodes from cold-start compose; install.md JOIN_TOKEN references purged (completed 2026-03-27)
- [x] **Phase 80: GitHub Pages Deploy + Marketing Homepage** — Docs at `/docs/` via ghp-import subtree; marketing homepage at repo root with CE/EE comparison and hero copy (completed 2026-03-27)
- [x] **Phase 81: Homepage Enterprise Messaging** — Security posture grid (mTLS/RBAC/air-gap/cryptographic audit), SAML/OIDC early-access EE card, enterprise CTA wired to conversion form (completed 2026-03-28)

Archive: `.planning/milestones/v14.4-ROADMAP.md`

</details>

<details>
<summary>✅ v15.0 — Operator Readiness (Phases 82–86) — SHIPPED 2026-03-29</summary>

- [x] **Phase 82: Licence Tooling** — Key migration to private repo, CI guard against committed keys, `issue_licence.py` CLI, YAML audit ledger, `--no-remote` flag (completed 2026-03-28)
- [x] **Phase 83: Node Validation Job Library** — Signed Bash/Python/PowerShell reference jobs, volume + network + resource limit validation jobs, runbook, job manifest (completed 2026-03-28)
- [x] **Phase 84: Package Repo Operator Docs** — devpi/APT/PWSH mirror runbooks, pip mirror validation job added to corpus (completed 2026-03-29)
- [x] **Phase 85: Screenshot Capture** — Playwright seeded-data capture script, 11-view screenshots, pre-flight check (completed 2026-03-29)
- [x] **Phase 86: Docs Accuracy Validation** — OpenAPI/CLI cross-reference script, PASS/WARN/FAIL output with file+line refs, CI integration (completed 2026-03-29)

Archive: `.planning/milestones/v15.0-ROADMAP.md`

</details>

<details>
<summary>✅ v16.0 — Competitive Observability (Phases 87–91) — SHIPPED 2026-03-30</summary>

- [x] **Phase 87: Research & Design** — Review competitor pain points report; produce design decisions for all four implementation features (completed 2026-03-29)
- [x] **Phase 88: Dispatch Diagnosis UI** — Inline dispatch diagnosis on PENDING jobs; bulk diagnosis endpoint; 10s auto-poll (completed 2026-03-29)
- [x] **Phase 89: CE Alerting** — Webhook notification on job failure; NotificationsCard in Admin; CE-accessible without EE licence (completed 2026-03-29)
- [x] **Phase 90: Job Script Versioning** — Immutable JobDefinitionVersion table; ScriptViewerModal; version fields in ExecutionRecordResponse (completed 2026-03-30)
- [x] **Phase 91: Output Validation** — validation_rules + failure_reason DB columns; process_result() engine; Validation Rules form in JobDefinitionModal; failure labels in all history views (completed 2026-03-30)

Archive: `.planning/milestones/v16.0-ROADMAP.md`

</details>

<details>
<summary>✅ v16.1 — PR Merge & Backlog Closure (Phases 92–95) — SHIPPED 2026-03-30</summary>

- [x] **Phase 92: USP Signing UX** — Merge PR #10: keypair generation guide on Signatures page (completed 2026-03-30)
- [x] **Phase 93: Documentation PRs** — Merge PRs #11, #12, #13: production deployment guide, upgrade runbook, Windows getting-started (completed 2026-03-30)
- [x] **Phase 94: Research & Planning Closure** — Merge PR #14: APScheduler scale limits research; record competitor pain-point product notes (completed 2026-03-30)
- [x] **Phase 95: Tech Debt** — Housekeeping: SIGN_CMD placeholder, DOC strikethroughs, plan frontmatter; retroactive VALIDATION.md for phases 92–94 (completed 2026-03-30)

Archive: `.planning/milestones/v16.1-ROADMAP.md`

</details>

<details>
<summary>✅ v17.0 — Scale Hardening (Phases 96–100) — SHIPPED 2026-03-31</summary>

- [x] **Phase 96: Foundation** - APScheduler version pin and IS_POSTGRES dialect flag (completed 2026-03-30)
- [x] **Phase 97: DB Pool Tuning** - Connection pool right-sized for 20 concurrent nodes with health checks (completed 2026-03-30)
- [x] **Phase 98: Dispatch Correctness** - Composite index + SKIP LOCKED eliminates double-assignment races (completed 2026-03-30)
- [x] **Phase 99: Scheduler Hardening** - Incremental sync and dispatcher isolation fix dark window and event loop saturation (completed 2026-03-31)
- [x] **Phase 100: Observability + Sign-off** - Health endpoint, admin dashboard metrics, and operations docs (completed 2026-03-31)

Archive: `.planning/milestones/v17.0-ROADMAP.md`

</details>

### 🚧 v18.0 — First-User Experience & E2E Validation (In Progress)

**Milestone Goal:** A first-time user on Linux or Windows can follow the Quick Start guide from cold start to a completed job with zero undocumented friction. The CE dashboard presents only CE-relevant UI.

- [x] **Phase 101: CE UX Cleanup** — Hide EE-only tabs in CE mode, add upgrade prompts, verify no black pages (completed 2026-03-31)
- [ ] **Phase 102: Linux E2E Validation** — LXC clean-environment cold-start through first job; all friction catalogued and fixed
- [ ] **Phase 103: Windows E2E Validation** — Dwight SSH cold-start through first PowerShell job; all friction catalogued and fixed

## Phase Details

### Phase 101: CE UX Cleanup
**Goal**: CE users see a clean dashboard scoped to CE features — no EE tabs cluttering the navigation, no blank pages on EE routes, and clear upgrade prompts where EE features would otherwise appear
**Depends on**: Nothing (first phase of v18.0)
**Requirements**: CEUX-01, CEUX-02, CEUX-03
**Success Criteria** (what must be TRUE):
  1. A CE user navigating the Admin settings page sees only CE-relevant tabs; EE-only tabs (Smelter Registry, BOM Explorer, Tools, Artifact Vault, Rollouts, Automation) are absent from the rendered tab list
  2. Any UI surface that previously showed an EE tab now shows a visible upgrade prompt in its place — not a blank area or a broken/empty panel
  3. No dashboard route renders a black or empty page in CE mode; every route either renders its CE content or shows a graceful feature-gate message
**Plans**:
- [x] **101-01**: CE tab gating + upgrade panel in Admin.tsx (completed 2026-03-31)
- [x] **101-02**: CE/EE tab visibility tests in Admin.test.tsx (completed 2026-03-31)

### Phase 102: Linux E2E Validation
**Goal**: A fresh Linux user following the Quick Start guide inside a clean LXC environment reaches a completed job with no undocumented steps and no friction points left unresolved
**Depends on**: Phase 101
**Requirements**: LNX-01, LNX-02, LNX-03, LNX-04, LNX-05, LNX-06
**Success Criteria** (what must be TRUE):
  1. A clean LXC container can complete the cold-start deployment following only the published Quick Start guide — no commands outside the docs are needed
  2. Logging in with admin/admin immediately shows the forced password change prompt, which completes successfully and grants dashboard access
  3. A node enrolls following the documented enrollment steps and appears as ONLINE in the Nodes view
  4. A Python or Bash job dispatched through the guided form runs to COMPLETED status and its output is visible in the dashboard
  5. All documented CE features (job dispatch, scheduling, node management, audit log) are reachable and functional with no missing or broken UI elements
  6. Every friction point found during the Linux run is catalogued in a report and fixed before the phase is marked complete
**Plans**: 3 plans
Plans:
- [ ] 102-01-PLAN.md — Validation infrastructure (orchestrator, persona prompt, synthesise_friction.py patch)
- [ ] 102-02-PLAN.md — Live golden path run in fresh LXC + friction catalogue
- [ ] 102-03-PLAN.md — Fix all BLOCKERs, iterate until clean, produce READY synthesis sign-off

### Phase 103: Windows E2E Validation
**Goal**: A fresh Windows user following the Quick Start (Windows) guide on Dwight reaches a completed PowerShell job with no undocumented steps and no friction points left unresolved
**Depends on**: Phase 101
**Requirements**: WIN-01, WIN-02, WIN-03, WIN-04, WIN-05, WIN-06
**Success Criteria** (what must be TRUE):
  1. The Docker stack starts on Dwight via SSH following only the published Windows Quick Start guide; credentials come from `mop_validation/secrets.env`
  2. All shell interactions with the stack use PowerShell (PWSH) — no CMD commands appear in any documented step or tested path
  3. Logging in with admin/admin immediately shows the forced password change prompt, which completes successfully and grants dashboard access
  4. A node enrolls on Dwight following the documented Windows enrollment steps and appears as ONLINE in the Nodes view
  5. A PowerShell job dispatched through the dashboard runs to COMPLETED status and its output is visible
  6. Every friction point found during the Windows run is catalogued in a report and fixed before the phase is marked complete
**Plans**: TBD

## Progress

**Execution Order:**
Phases execute in numeric order: 101 → 102 → 103

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
| 77. Licence Banner Polish | v14.4 | 1/1 | Complete | 2026-03-27 |
| 78. CLI Signing UX | v14.4 | 2/2 | Complete | 2026-03-27 |
| 79. Install Docs Cleanup | v14.4 | 1/1 | Complete | 2026-03-27 |
| 80. GitHub Pages Deploy + Marketing Homepage | v14.4 | 2/2 | Complete | 2026-03-27 |
| 81. Homepage Enterprise Messaging | v14.4 | 1/1 | Complete | 2026-03-28 |
| 82. Licence Tooling | v15.0 | 2/2 | Complete | 2026-03-28 |
| 83. Node Validation Job Library | v15.0 | 3/3 | Complete | 2026-03-28 |
| 84. Package Repo Operator Docs | v15.0 | 2/2 | Complete | 2026-03-29 |
| 85. Screenshot Capture | v15.0 | 2/2 | Complete | 2026-03-29 |
| 86. Docs Accuracy Validation | v15.0 | 2/2 | Complete | 2026-03-29 |
| 87. Research & Design | v16.0 | 1/1 | Complete | 2026-03-29 |
| 88. Dispatch Diagnosis UI | v16.0 | 2/2 | Complete | 2026-03-29 |
| 89. CE Alerting | v16.0 | 2/2 | Complete | 2026-03-29 |
| 90. Job Script Versioning | v16.0 | 2/2 | Complete | 2026-03-30 |
| 91. Output Validation | v16.0 | 2/2 | Complete | 2026-03-30 |
| 92. USP Signing UX | v16.1 | 3/3 | Complete | 2026-03-30 |
| 93. Documentation PRs | v16.1 | 2/2 | Complete | 2026-03-30 |
| 94. Research & Planning Closure | v16.1 | 2/2 | Complete | 2026-03-30 |
| 95. Tech Debt | v16.1 | 2/2 | Complete | 2026-03-30 |
| 96. Foundation | v17.0 | 1/1 | Complete | 2026-03-30 |
| 97. DB Pool Tuning | v17.0 | 1/1 | Complete | 2026-03-30 |
| 98. Dispatch Correctness | v17.0 | 1/1 | Complete | 2026-03-30 |
| 99. Scheduler Hardening | v17.0 | 1/1 | Complete | 2026-03-31 |
| 100. Observability + Sign-off | v17.0 | 2/2 | Complete | 2026-03-31 |
| 101. CE UX Cleanup | v18.0 | Complete    | 2026-03-31 | 2026-03-31 |
| 102. Linux E2E Validation | 2/3 | In Progress|  | - |
| 103. Windows E2E Validation | v18.0 | 0/TBD | Not started | - |

## Archived

- ✅ **v16.1 — PR Merge & Backlog Closure** (Phases 92–95) — shipped 2026-03-30 → `.planning/milestones/v16.1-ROADMAP.md`
- ✅ **v14.3 — Security Hardening + EE Licensing** (Phases 72–76) — shipped 2026-03-27 → `.planning/milestones/v14.3-ROADMAP.md`
- ✅ **v14.2 — Docs on GitHub Pages** (Phase 71) — shipped 2026-03-26 → `.planning/milestones/v14.2-ROADMAP.md`
