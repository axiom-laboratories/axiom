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
- 🚧 **v16.1 — PR Merge & Backlog Closure** — Phases 92–94 (in progress)

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

### 🚧 v16.1 — PR Merge & Backlog Closure (In Progress)

**Milestone Goal:** Land all five open PRs, close the backlog-captured todos, and record research insights — leaving the codebase clean and the product story complete before v17.0 planning begins.

- [x] **Phase 92: USP Signing UX** — Test and merge PR #10 (feat/usp-signing-ux): keygen guide and Signatures banner (completed 2026-03-30)
- [x] **Phase 93: Documentation PRs** — Review and merge PRs #11, #12, #13: deployment guide, upgrade runbook, Windows getting-started (completed 2026-03-30)
- [x] **Phase 94: Research & Planning Closure** — Merge PR #14 (APScheduler scale limits) and record competitor pain-point insights (completed 2026-03-30)

## Phase Details

### Phase 92: USP Signing UX
**Goal**: New users can run a hello-world job in under 30 minutes without generating their own signing keys
**Depends on**: Nothing (first phase of v16.1 milestone)
**Requirements**: UX-01
**Success Criteria** (what must be TRUE):
  1. The Signatures page guides users through keypair generation with copy-paste commands — no auto-seeded demo keypair
  2. The Signatures page displays a banner with copy-paste signing steps that a new user can follow without consulting external docs
  3. PR #10 (feat/usp-signing-ux) passes all tests and is merged to main
**Plans**: 92-01, 92-02, 92-03

### Phase 93: Documentation PRs
**Goal**: Operators have production deployment guidance, an upgrade runbook, and a Windows getting-started path available in the published docs
**Depends on**: Phase 92
**Requirements**: DOC-01, DOC-02, DOC-03
**Success Criteria** (what must be TRUE):
  1. The docs site includes a production deployment guide covering HA, backups, recovery, and air-gap considerations
  2. The docs site includes an upgrade runbook with all migration SQL files indexed so an operator can upgrade any version to current
  3. The docs site includes an end-to-end Windows getting-started path (Docker Desktop + WSL2)
  4. PRs #11, #12, and #13 are merged to main with no unresolved review comments
**Plans**: TBD

### Phase 94: Research & Planning Closure
**Goal**: APScheduler scale-limit research is accessible for future architecture decisions, and competitor pain-point insights are recorded
**Depends on**: Phase 93
**Requirements**: RES-01, PLAN-01
**Success Criteria** (what must be TRUE):
  1. PR #14 (research/apscheduler-scale-limits) is merged and the report is accessible in mop_validation reports
  2. The APScheduler scale findings are summarised with concrete job-count thresholds and recommended migration path
  3. Competitor pain-point insights are written into a product notes file with at least three actionable observations
**Plans**: TBD

### Phase 87: Research & Design
**Goal**: Design decisions are documented for all four v16.0 features — blocking ambiguity resolved before a single line of implementation is written
**Depends on**: Phase 86 (v15.0 complete)
**Requirements**: RSH-01, RSH-02, RSH-03, RSH-04, RSH-05
**Success Criteria** (what must be TRUE):
  1. A competitor pain-points review document exists and the four chosen feature approaches are recorded with rationale
  2. Dispatch diagnosis UX decision is recorded: which view surfaces the reason, whether it auto-polls or is on-demand, and any endpoint gaps identified
  3. CE alerting mechanism is chosen (SMTP, single webhook URL, or both) with explicit CE/EE boundary documented
  4. Job script versioning DB schema and API shape are decided — immutable version table design with linkage to execution records documented
  5. Output validation contract is defined — how a script signals structured results, what fields the node reports back, and how the backend maps them to FAILED status
**Plans**: TBD

### Phase 88: Dispatch Diagnosis UI
**Goal**: An operator looking at a PENDING job can immediately see why it has not dispatched — without leaving the job list or navigating to a separate page
**Depends on**: Phase 87
**Requirements**: DIAG-01, DIAG-02, DIAG-03
**Success Criteria** (what must be TRUE):
  1. A PENDING job in the job list shows an inline indicator (badge, tooltip, or expandable row) explaining why it has not dispatched
  2. The diagnosis text names the specific reason: no capable nodes, capability mismatch, resource limit exceeded, all nodes offline, or similar discrete categories
  3. The diagnosis refreshes without a full page reload — either on a timed poll or via a manual refresh control in the UI
**Plans**: TBD

### Phase 89: CE Alerting
**Goal**: A CE operator who configures a notification destination receives an alert whenever a job fails — no EE licence, no third-party integration required
**Depends on**: Phase 87
**Requirements**: ALRT-01, ALRT-02, ALRT-03
**Success Criteria** (what must be TRUE):
  1. The Admin settings page (or equivalent) has a form where an operator can enter an SMTP address or a webhook URL as a notification destination
  2. When any job reaches FAILED status, the configured destination receives a message containing the job name, the node that ran it, and the error summary
  3. The alerting configuration form and the notification delivery are both accessible to a user with the operator role on a CE stack (no EE licence required)
**Plans**: TBD

### Phase 90: Job Script Versioning
**Goal**: Every edit to a job definition's script is preserved as an immutable version record — operators can inspect exactly which script ran for any historical execution
**Depends on**: Phase 87
**Requirements**: VER-01, VER-02, VER-03
**Success Criteria** (what must be TRUE):
  1. Editing a job definition's script content creates a new version record; the previous script is still accessible and has not been overwritten
  2. Opening the execution detail for any historical run shows a "View script" action that displays the exact script content that was active when that job executed
  3. The execution history list shows a version number or identifier column indicating which script version was in effect for each run
**Plans**: TBD

### Phase 91: Output Validation
**Goal**: An operator can declare what a successful job output looks like — a job that exits 0 but violates its validation pattern is reported as FAILED with a clear reason, not silently marked COMPLETED
**Depends on**: Phase 87
**Requirements**: VALD-01, VALD-02, VALD-03
**Success Criteria** (what must be TRUE):
  1. The job definition form includes a validation section where an operator can specify a success pattern: exit code check, a JSON field assertion, or a stdout regex
  2. A job that exits with code 0 but does not satisfy its configured validation pattern transitions to FAILED status — not COMPLETED — and the failure record includes the validation rule that was violated
  3. The execution history view and the job detail view both display validation failure reasons distinctly from execution errors (e.g. a clear "Validation failed: ..." label rather than a generic error)
**Plans**: TBD

## Progress

**Execution Order:**
Phases execute in numeric order: 87 → 88 → 89 → 90 → 91 → 92 → 93 → 94

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
| 92. USP Signing UX | v16.1 | Complete    | 2026-03-30 | 2026-03-30 |
| 93. Documentation PRs | v16.1 | Complete    | 2026-03-30 | 2026-03-30 |
| 94. Research & Planning Closure | 2/2 | Complete    | 2026-03-30 | - |

## Archived

- ✅ **v14.3 — Security Hardening + EE Licensing** (Phases 72–76) — shipped 2026-03-27 → `.planning/milestones/v14.3-ROADMAP.md`
- ✅ **v14.2 — Docs on GitHub Pages** (Phase 71) — shipped 2026-03-26 → `.planning/milestones/v14.2-ROADMAP.md`

### Phase 95: techdebt

**Goal:** Close Nyquist compliance gap and housekeeping for v16.1 milestone
**Requirements**: TBD
**Depends on:** Phase 94
**Plans:** 2/2 plans complete

Plans:
- [x] 95-01: Housekeeping — SIGN_CMD placeholder, DOC strikethroughs, plan frontmatter (completed 2026-03-30)
- [x] 95-02: Retroactive VALIDATION.md for phases 92, 93, 94 (completed 2026-03-30)
