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
- 🚧 **v14.0 — CE/EE Cold-Start Validation** — Phases 61–65 (in progress)

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

### 🚧 v14.0 — CE/EE Cold-Start Validation (In Progress)

**Milestone Goal:** Validate Axiom's install and operator paths end-to-end using Gemini CLI agents as first-time users inside LXC containers, covering both CE and EE scenarios across all job runtimes. Produce a friction report with actionable findings.

- [x] **Phase 61: LXC Environment and Cold-Start Compose** — Provision LXC with Docker nesting, Gemini CLI, and a stripped Axiom compose stack verified to start cleanly (completed 2026-03-24)
- [x] **Phase 62: Agent Scaffolding** — Tester GEMINI.md, checkpoint file protocol, HOME isolation, and scenario prompt scripts (completed 2026-03-25)
- [x] **Phase 63: CE Cold-Start Run** — Gemini agent follows CE getting-started docs through install and all 3 job runtimes; CE FRICTION.md produced (completed 2026-03-25)
- [x] **Phase 64: EE Cold-Start Run** — Gemini agent follows EE install path with pre-injected licence, verifies EE-gated features; EE FRICTION.md produced (completed 2026-03-25)
- [x] **Phase 65: Friction Report Synthesis** — Merge CE+EE findings into a single deliverable with cross-edition comparison and readiness verdict (completed 2026-03-25)

## Phase Details

### Phase 61: LXC Environment and Cold-Start Compose
**Goal**: A working Axiom CE stack runs inside an LXC container, all infrastructure pitfalls resolved, Gemini CLI responds headlessly
**Depends on**: Nothing (first phase)
**Requirements**: ENV-01, ENV-02, ENV-03, ENV-04
**Success Criteria** (what must be TRUE):
  1. `provision_lxc.py` starts an Ubuntu 24.04 Incus container with Docker nesting enabled and `docker run --rm hello-world` succeeds inside it
  2. `compose.cold-start.yaml` brings the full Axiom stack up (orchestrator, docs, 2 puppet nodes) and the dashboard is reachable at the Docker bridge IP with a valid TLS cert (Caddy SAN includes `172.17.0.1`)
  3. `docker exec <node> which pwsh` returns a path — PowerShell is installed and available in the node container
  4. EE test licence is generated with a 1-year expiry and stored in `mop_validation/secrets.env` under `AXIOM_EE_LICENCE_KEY`
  5. `timeout 30 gemini -p "Say hello"` returns successfully inside the LXC — Gemini CLI headless mode is operational
**Plans**: 3 plans
- [ ] 61-01-PLAN.md — LXC provisioning script + smoke verifier (ENV-01)
- [ ] 61-02-PLAN.md — cold-start compose + PowerShell fix (ENV-02, ENV-03)
- [ ] 61-03-PLAN.md — EE licence generation script (ENV-04)

### Phase 62: Agent Scaffolding
**Goal**: The Gemini tester agent is correctly constrained and the checkpoint protocol is verified to work before any scenario starts
**Depends on**: Phase 61
**Requirements**: SCAF-01, SCAF-02, SCAF-03, SCAF-04
**Success Criteria** (what must be TRUE):
  1. Tester `GEMINI.md` exists at `/workspace/gemini-context/` inside the LXC and contains only docs-site access instructions with no codebase references
  2. A complete checkpoint round-trip completes in under 60 seconds: Gemini writes `checkpoint/PROMPT.md`, `monitor_checkpoint.py` surfaces it to the host, Claude writes `RESPONSE.md` back via `incus file push`, Gemini reads and continues
  3. Running Gemini with `HOME=/root/validation-home` prevents it from loading the repo `GEMINI.md` or any prior session history
  4. Scenario prompt scripts exist for CE install, CE operator, EE install, and EE operator paths — each defines explicit pass/fail criteria and checkpoint trigger conditions
**Plans**: 3 plans
Plans:
- [ ] 62-01-PLAN.md — workspace setup + tester GEMINI.md + HOME isolation (SCAF-01, SCAF-03)
- [ ] 62-02-PLAN.md — monitor_checkpoint.py + round-trip verification (SCAF-02)
- [ ] 62-03-PLAN.md — CE and EE scenario prompt scripts (SCAF-04)

### Phase 63: CE Cold-Start Run
**Goal**: A Gemini agent acting as a first-time user completes the CE install and operator path from scratch, producing an evidence-backed friction report
**Depends on**: Phase 62
**Requirements**: CE-01, CE-02, CE-03, CE-04, CE-05
**Success Criteria** (what must be TRUE):
  1. Gemini agent reaches a running Axiom CE stack with at least one enrolled node by following only the getting-started docs — no checkpoint steering needed for this step
  2. Gemini agent dispatches a Python job via the guided dispatch form and confirms `COMPLETED` status with stdout captured in the job history view
  3. Gemini agent dispatches a Bash job via the guided dispatch form and confirms `COMPLETED` status with stdout captured in the job history view
  4. Gemini agent dispatches a PowerShell job via the guided dispatch form and confirms `COMPLETED` status with stdout captured in the job history view
  5. `checkpoint/FRICTION.md` contains a per-step PASS/FAIL log, verbatim doc quotes for every friction point, checkpoint steering interventions disclosed, and BLOCKER/NOTABLE/MINOR classification per finding
**Plans**: 3 plans
Plans:
- [ ] 63-01-PLAN.md — stack reset + readiness verification + run orchestration script (CE-01)
- [ ] 63-02-PLAN.md — CE install scenario (ce-install.md) with checkpoint monitoring and operator gate (CE-01, CE-05)
- [ ] 63-03-PLAN.md — CE operator scenario (ce-operator.md) — 3-runtime job dispatch and CE-05 acceptance gate (CE-02, CE-03, CE-04, CE-05)

### Phase 64: EE Cold-Start Run
**Goal**: A Gemini agent completes the EE install path with licence injection and verifies EE-specific features, producing an EE friction report comparable to the CE report
**Depends on**: Phase 63
**Requirements**: EE-01, EE-02, EE-03, EE-04
**Success Criteria** (what must be TRUE):
  1. `GET /api/admin/features` returns `ee_status: loaded` and the dashboard sidebar shows the EE edition badge after the agent follows EE install docs with the pre-generated licence injected
  2. Gemini agent dispatches Python, Bash, and PowerShell jobs via the EE operator path and confirms `COMPLETED` status with stdout captured for each runtime
  3. Gemini agent exercises at least one EE-gated feature (execution history, attestation badge, or environment tag routing) and confirms it is accessible and functioning
  4. EE `FRICTION.md` is produced to the same standard as CE-05, with EE-specific findings annotated separately from findings also present in the CE run
**Plans**: 3 plans
Plans:
- [ ] 64-01-PLAN.md — EE image rebuild (local wheel), push to LXC, EE stack reset with licence key, readiness verification (EE-01)
- [ ] 64-02-PLAN.md — ee-install Gemini scenario + operator EE-loaded gate (EE-01, EE-04)
- [ ] 64-03-PLAN.md — ee-operator scenario (3 runtimes + Execution History) + CE-gating confirmation + FRICTION pull (EE-02, EE-03, EE-04)

### Phase 65: Friction Report Synthesis
**Goal**: CE and EE friction findings are merged into a single deliverable with cross-edition comparison, severity triage, and a verdict on first-user readiness
**Depends on**: Phase 64
**Requirements**: RPT-01
**Success Criteria** (what must be TRUE):
  1. `synthesise_friction.py` pulls both `FRICTION.md` files from their respective LXC containers and produces `mop_validation/reports/cold_start_friction_report.md`
  2. The report contains a cross-edition comparison table showing which findings are CE-only, EE-only, or shared
  3. Every BLOCKER and NOTABLE finding has an actionable recommendation with the specific doc section or code path that needs to change
  4. The report ends with a binary first-user readiness verdict (READY / NOT READY) with the blocking criteria listed
**Plans**: 1 plan
Plans:
- [ ] 65-01-PLAN.md — synthesise_friction.py + cold_start_friction_report.md (RPT-01)

## Progress

**Execution Order:**
Phases execute in numeric order: 61 → 62 → 63 → 64 → 65

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
| 61. LXC Environment and Cold-Start Compose | 3/3 | Complete    | 2026-03-24 | - |
| 62. Agent Scaffolding | 3/3 | Complete    | 2026-03-25 | - |
| 63. CE Cold-Start Run | 3/3 | Complete    | 2026-03-25 | - |
| 64. EE Cold-Start Run | 3/3 | Complete    | 2026-03-25 | - |
| 65. Friction Report Synthesis | 1/1 | Complete    | 2026-03-25 | - |

## Archived

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
