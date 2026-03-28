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
- 🚧 **v15.0 — Operator Readiness** — Phases 82–86 (in progress)

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

### 🚧 v15.0 — Operator Readiness (Phases 82–86)

**Milestone Goal:** Close the gap between a technically functional platform and one that operators can confidently deploy in production — with a secure licence issuance workflow, a validated node job library, package repo runbooks, dashboard screenshots in docs and marketing, and a CI-wirable docs accuracy script.

- [x] **Phase 82: Licence Tooling** — Key migration to private repo, CI guard against committed keys, `issue_licence.py` CLI, YAML audit ledger, `--no-remote` flag (completed 2026-03-28)
- [ ] **Phase 83: Node Validation Job Library** — Signed Bash/Python/PowerShell reference jobs, volume + network + resource limit validation jobs, runbook, job manifest
- [ ] **Phase 84: Package Repo Operator Docs** — devpi/APT/PWSH mirror runbooks, pip mirror validation job added to corpus
- [ ] **Phase 85: Screenshot Capture** — Playwright seeded-data capture script, 8+ view screenshots committed to docs and marketing
- [ ] **Phase 86: Docs Accuracy Validation** — OpenAPI/CLI cross-reference script, PASS/WARN/FAIL output with file+line refs, CI integration

## Phase Details

### Phase 82: Licence Tooling
**Goal**: The licence signing private key is out of the public repo and operators can issue, audit, and rotate licences safely
**Depends on**: Phase 81 (v14.4 complete)
**Requirements**: LIC-01, LIC-02, LIC-03, LIC-04, LIC-05
**Success Criteria** (what must be TRUE):
  1. Operator can run `issue_licence.py --customer X --tier EE --nodes N --expiry YYYY-MM-DD` against a private `axiom-licences` repo and receive a valid base64 licence blob
  2. Each issued licence produces a committed YAML record in `axiom-licences/licences/issued/` with `jti`, `customer_id`, `tier`, `node_limit`, `expiry`, and `issued_by` fields
  3. The public repo contains no Ed25519 private key material — the CI guard rejects any commit with `-----BEGIN PRIVATE KEY-----` content
  4. Operator can use `--no-remote` flag to write the audit record to a local file instead of committing to GitHub (air-gapped workflow)
  5. Running `issue_licence.py` without an explicit `--key` path fails with a clear error — no silent default path inside the repo
**Plans**: 2 plans
Plans:
- [ ] 82-01-PLAN.md — Private repo scaffold: keypair rotation, issue_licence.py, list_licences.py
- [ ] 82-02-PLAN.md — Public repo cleanup: new public key in licence_service.py, gitleaks CI guard

### Phase 83: Node Validation Job Library
**Goal**: Operators have a signed, runbook-backed job corpus to verify any node works correctly end-to-end across all runtimes and constraint types
**Depends on**: Phase 82
**Requirements**: JOB-01, JOB-02, JOB-03, JOB-04, JOB-05, JOB-06, JOB-07
**Success Criteria** (what must be TRUE):
  1. Operator can dispatch each of the Bash, Python, and PowerShell reference jobs and see them reach COMPLETED status on a capable node
  2. The volume mapping validation job confirms files written inside the container are readable at the expected host-side mount path after job completion
  3. The network filtering validation job confirms allowed hosts return a response and blocked hosts time out, without leaving residual iptables state on the node
  4. The memory-hog job is killed (OOM or FAILED) rather than completing when dispatched to a node with a memory limit lower than the job's allocation
  5. The CPU-spin job is throttled or killed when dispatched to a node with a CPU limit enforced at the container runtime level
**Plans**: 3 plans
Plans:
- [ ] 83-01-PLAN.md — Test scaffold + Bash/Python/PowerShell hello-world reference jobs
- [ ] 83-02-PLAN.md — Validation scripts (volume, network, memory, CPU) + manifest.yaml
- [ ] 83-03-PLAN.md — Community catalog README + MkDocs runbook + navigation

### Phase 84: Package Repo Operator Docs
**Goal**: Operators can configure a local package mirror for PyPI, APT, or PowerShell modules and validate it using a signed job
**Depends on**: Phase 83
**Requirements**: PKG-01, PKG-02, PKG-03, PKG-04
**Success Criteria** (what must be TRUE):
  1. Operator can follow the devpi runbook to configure a Blueprint's `pip.conf` to resolve from an internal mirror and verify a pip install succeeds without hitting the public internet
  2. Operator can follow the APT mirror guidance to configure `apt-cacher-ng` as a sidecar and confirm packages resolve through it during a Foundry node build
  3. Operator can follow the PWSH mirror guidance to install a module from a BaGet/PSGallery mirror inside a job script
  4. The signed pip-mirror validation job reports PASS when the internal mirror is active and FAIL when it is not reachable, giving operators a dispatch-ready smoke test
**Plans**: TBD

### Phase 85: Screenshot Capture
**Goal**: The docs and marketing homepage show real, populated dashboard screenshots that reflect actual platform state
**Depends on**: Phase 83
**Requirements**: SCR-01, SCR-02, SCR-03
**Success Criteria** (what must be TRUE):
  1. Operator can run `capture_screenshots.py` against a live Docker stack and receive 8+ named PNG files at 1440×900 without manual intervention or timing failures
  2. Every captured screenshot shows seeded demo data (at least one enrolled node, completed jobs, visible audit entries) — no empty-state or spinner captures
  3. Screenshots are committed to `docs/docs/assets/screenshots/` and rendered on the getting-started and feature docs pages
  4. Screenshots are committed to `homepage/assets/screenshots/` and displayed in the marketing homepage
**Plans**: TBD

### Phase 86: Docs Accuracy Validation
**Goal**: A CI-wirable script flags any docs that reference API routes, CLI commands, or env vars that no longer exist in the codebase
**Depends on**: Phase 85
**Requirements**: DOC-01, DOC-02, DOC-03
**Success Criteria** (what must be TRUE):
  1. Running `validate_docs.py` against the committed `openapi.json` snapshot produces a PASS/WARN/FAIL result per documented API route, with the specific docs file and line number on any FAIL
  2. The script flags any `axiom-push <subcommand>` mentioned in docs that is not registered in `mop_sdk/cli.py`, and any env var names in docs that do not match the codebase
  3. The script exits with code 1 on any FAIL result, making it usable as a CI gate
**Plans**: TBD

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
| 77. Licence Banner Polish | v14.4 | 1/1 | Complete | 2026-03-27 |
| 78. CLI Signing UX | v14.4 | 2/2 | Complete | 2026-03-27 |
| 79. Install Docs Cleanup | v14.4 | 1/1 | Complete | 2026-03-27 |
| 80. GitHub Pages Deploy + Marketing Homepage | v14.4 | 2/2 | Complete | 2026-03-27 |
| 81. Homepage Enterprise Messaging | v14.4 | 1/1 | Complete | 2026-03-28 |
| 82. Licence Tooling | 2/2 | Complete    | 2026-03-28 | - |
| 83. Node Validation Job Library | 1/3 | In Progress|  | - |
| 84. Package Repo Operator Docs | v15.0 | 0/TBD | Not started | - |
| 85. Screenshot Capture | v15.0 | 0/TBD | Not started | - |
| 86. Docs Accuracy Validation | v15.0 | 0/TBD | Not started | - |

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
