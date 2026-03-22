# Roadmap: Master of Puppets

## Milestones

- ✅ **v1.0–v6.0** — Milestones 1–6 (Production Reliability → Remote Validation) — shipped 2026-03-06/09
- ✅ **v7.0 — Advanced Foundry & Smelter** — Phases 11–15 (shipped 2026-03-16)
- ✅ **v8.0 — mop-push CLI & Job Staging** — Phases 17–19 (shipped 2026-03-15)
- ✅ **v9.0 — Enterprise Documentation** — Phases 20–28 (shipped 2026-03-17)
- ✅ **v10.0 — Axiom Commercial Release** — Phases 29–33 (shipped 2026-03-19)
- ✅ **v11.0 — CE/EE Split Completion** — Phases 34–37 (shipped 2026-03-20)
- ✅ **v11.1 — Stack Validation** — Phases 38–45 (shipped 2026-03-22)
- 🚧 **v12.0 — Operator Maturity** — Phases 46–53 (in progress)

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

### 🚧 v12.0 — Operator Maturity (Phases 46–53)

**Milestone Goal:** Make day-to-day operator experience materially better — multi-runtime execution, guided job form, failure visibility, queue diagnosis, bulk operations, search/filtering/pagination, and a tech debt sweep.

## Phase Checklist

- [x] **Phase 46: Tech Debt + Security + Branding** — Foundation cleanup before new features: fix deferred gaps, add security hardening, align UI labels (completed 2026-03-22)
- [x] **Phase 47: CE Runtime Expansion** — Unified `script` task type supporting Python, Bash, and PowerShell runtimes end-to-end (completed 2026-03-22)
- [ ] **Phase 48: Scheduled Job Signing Safety** — DRAFT state for stale signatures; skipped fires logged; operator warned before script edits fire
- [ ] **Phase 49: Pagination, Filtering and Search** — Server-side pagination on Jobs and Nodes; 9-axis job filtering; free-text search; CSV export
- [ ] **Phase 50: Guided Job Form** — Structured guided form replacing raw JSON for common job submission; Advanced mode available via gate
- [ ] **Phase 51: Job Detail, Resubmit and Bulk Ops** — Job detail drawer; one-click and edit-then-resubmit; multi-select bulk cancel/resubmit/delete
- [ ] **Phase 52: Queue Visibility, Node Drawer and DRAINING** — Live Queue view; PENDING diagnosis; per-node detail drawer; DRAINING node state
- [ ] **Phase 53: Scheduling Health and Data Management** — Scheduling Health panel; missed-fire detection; job templates; execution retention + pinning

## Phase Details

### Phase 46: Tech Debt + Security + Branding
**Goal**: The platform is clean, secure by default, and correctly branded before new operator-facing features land
**Depends on**: Phase 45
**Requirements**: DEBT-01, DEBT-02, DEBT-03, DEBT-04, SEC-01, SEC-02, BRAND-01
**Success Criteria** (what must be TRUE):
  1. SQLite deployments correctly prune NodeStats on schedule; no subquery incompatibility errors appear in logs on a SQLite-backed stack
  2. After any Foundry build completes or fails, no stale `/tmp/puppet_build_*` directories remain on the host filesystem
  3. Permission lookups under repeated API load do not execute a DB query per request; permissions are resolved from cache
  4. SECURITY_REJECTED job outcomes produce an audit log entry attributed to the reporting node with script hash context visible to an admin
  5. A tampered `signature_payload` (HMAC tag mismatch) is rejected at the orchestrator before dispatch; the rejection is audit-logged
  6. The Foundry section of the dashboard uses "Image Recipe", "Node Image", and "Tool" throughout with no legacy labels visible
**Plans**: 3 plans
Plans:
- [ ] 46-01-PLAN.md — Backend debt fixes: SQLite NodeStats prune (DEBT-01), perm cache pre-warm (DEBT-03), verify foundry cleanup (DEBT-02), verify node ID sort (DEBT-04)
- [ ] 46-02-PLAN.md — Security hardening: SECURITY_REJECTED audit entry (SEC-01), HMAC integrity on signature_payload (SEC-02)
- [ ] 46-03-PLAN.md — UI label rename: Blueprint→Image Recipe, Template→Node Image, Capability Matrix→Tool (BRAND-01)

### Phase 47: CE Runtime Expansion
**Goal**: Operators can submit Bash and PowerShell jobs through the same unified task type, with full backend validation and frontend display
**Depends on**: Phase 46
**Requirements**: RT-01, RT-02, RT-03, RT-04, RT-05, RT-07
**Note**: RT-06 (python_script alias) dropped per planning decision — python_script returns HTTP 422; use script+runtime=python
**Success Criteria** (what must be TRUE):
  1. Operator can submit a Bash job via `script` task type with `runtime: bash`; the job executes on a standard node and returns output
  2. Operator can submit a PowerShell job via `script` task type with `runtime: powershell`; the job executes on a standard node and returns output
  3. Submitting a job with an unrecognised `runtime` value returns HTTP 422 with a clear validation error message
  4. The Jobs list shows a computed `display_type` column (`script (bash)`, `script (python)`, `script (powershell)`) — value comes from the server, not from frontend JSON parsing
  5. A job definition can specify a `runtime` field; a Bash or PowerShell scheduled job fires correctly on its cron schedule
**Plans**: 3 plans
Plans:
- [ ] 47-01-PLAN.md — Test scaffold (Wave 0) + Containerfile.node PowerShell install (RT-03) + node.py script execution branch (RT-01, RT-02)
- [ ] 47-02-PLAN.md — Backend API: runtime validation, display_type computation, ScheduledJob.runtime column, scheduler update, migration_v38.sql (RT-04, RT-05, RT-07)
- [ ] 47-03-PLAN.md — Frontend: runtime dropdown in submission form, display_type column in jobs table (RT-05)

### Phase 48: Scheduled Job Signing Safety
**Goal**: Stale scheduled jobs cannot silently dispatch with an invalidated signature — script changes require fresh signing before the job resumes firing
**Depends on**: Phase 47
**Requirements**: SCHED-01, SCHED-02, SCHED-03, SCHED-04
**Success Criteria** (what must be TRUE):
  1. Editing and saving a scheduled job's script content transitions the job to DRAFT state; subsequent cron fires do not dispatch
  2. Each skipped cron fire for a DRAFT job produces a log entry with the reason "Skipped: job in DRAFT state, pending re-signing"
  3. Operator sees a modal warning before confirming a script change that will transition the job to DRAFT, with the option to cancel
  4. A DRAFT-state transition causes a notification to appear in the Dashboard notification bell and a WARNING entry in the alerts table linked to the scheduled job
**Plans**: TBD

### Phase 49: Pagination, Filtering and Search
**Goal**: Operators can navigate large job and node datasets efficiently using server-side pagination and multi-axis filtering without frontend performance degradation
**Depends on**: Phase 46
**Requirements**: SRCH-01, SRCH-02, SRCH-03, SRCH-04, SRCH-05
**Success Criteria** (what must be TRUE):
  1. The Jobs view loads using cursor-based pagination; "load more" appends the next page without replacing the current list; a count shows "Showing N of M"
  2. The Nodes view uses page-based pagination with page controls and a total node count
  3. Operator can filter the Jobs view by any combination of: status, runtime, task type, target node, target tags, created-by, and date ranges; each active filter appears as a dismissible chip
  4. Operator can search for jobs by name or GUID using a free-text box; operator can optionally name a job at submission time via the guided form
  5. The current filtered/searched Jobs view can be downloaded as a CSV file
**Plans**: TBD

### Phase 50: Guided Job Form
**Goal**: Operators have a structured, validated path for job submission that reduces errors and eliminates manual JSON authoring for the common case
**Depends on**: Phase 47, Phase 49
**Requirements**: JOB-01, JOB-02, JOB-03
**Success Criteria** (what must be TRUE):
  1. Operator can submit a job using a guided form with fields for runtime, script content, target environment, and capability tags — no JSON authoring required
  2. Guided form shows a read-only panel displaying the generated JSON payload; the raw JSON is not editable in this mode
  3. Operator can switch to Advanced (raw JSON) mode via a one-way confirmation gate; the JSON editor validates against schema before submission is permitted
**Plans**: TBD

### Phase 51: Job Detail, Resubmit and Bulk Ops
**Goal**: Operators can investigate failed jobs in context, resubmit them quickly or with edits, and operate on multiple jobs at once without repetitive individual actions
**Depends on**: Phase 50
**Requirements**: JOB-04, JOB-05, JOB-06, BULK-01, BULK-02, BULK-03, BULK-04
**Success Criteria** (what must be TRUE):
  1. Operator can open a job detail drawer from the Jobs view showing stdout/stderr, node health at time of execution, retry state, and any SECURITY_REJECTED reason in plain English
  2. Operator can resubmit a retries-exhausted failed job with one click; a new GUID is assigned; the originating job GUID is recorded on the new job
  3. Operator can open a failed job in the guided form pre-populated with that job's payload; signing state is cleared; fresh signing is required before resubmission
  4. Operator can multi-select jobs using checkboxes; a floating action bar appears with applicable bulk actions for the selected set
  5. Bulk cancel (PENDING/RUNNING), bulk resubmit (FAILED retries-exhausted), and bulk delete (terminal state) each display a count confirmation before executing
**Plans**: TBD

### Phase 52: Queue Visibility, Node Drawer and DRAINING
**Goal**: Operators can diagnose why a PENDING job is stuck, see the full live queue in one place, inspect per-node state in detail, and safely drain a node without forcefully terminating jobs
**Depends on**: Phase 51
**Requirements**: VIS-01, VIS-02, VIS-03, VIS-04
**Success Criteria** (what must be TRUE):
  1. A PENDING job's detail drawer shows an automatic plain-English dispatch diagnosis (e.g., "No nodes match capability X", "All eligible nodes busy — queue position 3") that refreshes live via WebSocket
  2. A dedicated Queue view shows PENDING, RUNNING, and recently completed jobs; the list updates in real time via WebSocket without any page refresh or polling
  3. The Nodes page includes a per-node detail drawer showing: currently running job, jobs queued for that node, recent execution history, and the node's reported capabilities
  4. An admin can set a node to DRAINING from the node detail drawer; the DRAINING status is visible in both the Nodes view and the Queue view; no new jobs are dispatched to a DRAINING node
**Plans**: TBD

### Phase 53: Scheduling Health and Data Management
**Goal**: Operators have a clear picture of scheduled job health over time, can reuse job configurations via templates, and the platform self-manages execution record growth with operator control over retention
**Depends on**: Phase 48, Phase 52
**Requirements**: VIS-05, VIS-06, SRCH-06, SRCH-07, SRCH-08, SRCH-09, SRCH-10
**Success Criteria** (what must be TRUE):
  1. Dashboard shows a Scheduling Health panel with aggregate fired/skipped/failed counts and per-definition health indicators; time window is switchable (24h / 7d / 30d)
  2. The Scheduling Health panel detects missed fires (expected cron fires vs actual execution records); definitions with missed fires show a red health indicator
  3. Operator can save a job configuration as a named reusable template (without signing state); loading a template pre-populates the guided form with all fields editable before submission
  4. Admin can configure a global execution record retention period (default 14 days); a nightly pruning task hard-deletes expired records while skipping pinned records; pin/unpin actions are audit-logged
  5. Operator can download all execution records for a specific job as a CSV file from the job detail drawer
**Plans**: TBD

## Progress

**Execution Order:**
46 → 47 → 48 → 49 → 50 → 51 → 52 → 53
Note: Phase 49 may proceed in parallel with Phase 47 (both depend only on Phase 46). Phase 50 requires both 47 and 49 complete. Phase 53 requires both 48 and 52 complete.

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 46. Tech Debt + Security + Branding | 3/3 | Complete    | 2026-03-22 |
| 47. CE Runtime Expansion | 4/4 | Complete   | 2026-03-22 |
| 48. Scheduled Job Signing Safety | 0/TBD | Not started | - |
| 49. Pagination, Filtering and Search | 0/TBD | Not started | - |
| 50. Guided Job Form | 0/TBD | Not started | - |
| 51. Job Detail, Resubmit and Bulk Ops | 0/TBD | Not started | - |
| 52. Queue Visibility, Node Drawer and DRAINING | 0/TBD | Not started | - |
| 53. Scheduling Health and Data Management | 0/TBD | Not started | - |

## Archived

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
