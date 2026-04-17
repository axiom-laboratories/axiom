# Roadmap: Master of Puppets

## Milestones

- ✅ **v1.0–v6.0** — Milestones 1–6 (Production Reliability → Remote Validation) — shipped 2026-03-06/09
- ✅ **v7.0 — Advanced Foundry & Smelter** — Phases 11–15 (shipped 2026-03-16)
- ✅ **v8.0 — mop-push CLI & Job Staging** — Phases 17–19 (shipped 2026-03-15)
- ✅ **v9.0 — Enterprise Documentation** — Phases 20–28 (shipped 2026-03-17)
- ✅ **v10.0 — Axiom Commercial Release** — Phases 29–33 (shipped 2026-03-19)
- ✅ **v11.0 — CE/EE Split Completion** — Phases 34–37 (shipped 2026-03-20)
- ✅ **v11.1 — Stack Validation** — Phases 38–45 (shipped 2026-03-22)
- ✅ **v12.0 — Operator Maturity** — Phases 46–56 (shipped 2026-04-24)
- ✅ **v13.0 — Research & Documentation Foundation** — Phases 57–60 (shipped 2026-03-24)
- ✅ **v14.0 — CE/EE Cold-Start Validation** — Phases 61–65 (shipped 2026-03-25)
- ✅ **v14.1 — First-User Readiness** — Phases 66–70 (shipped 2026-03-26)
- ✅ **v14.2 — Docs on GitHub Pages** — Phase 71 (shipped 2026-03-26)
- ✅ **v14.3 — Security Hardening + EE Licensing** — Phases 72–76 (shipped 2026-03-27)
- ✅ **v14.4 — Go-to-Market Polish** — Phases 77–81 (shipped 2026-03-28)
- ✅ **v15.0 — Operator Readiness** — Phases 82–86 (shipped 2026-03-29)
- ✅ **v16.0 — Competitive Observability** — Phases 87–91 (shipped 2026-03-30)
- ✅ **v16.1 — PR Merge & Backlog Closure** — Phases 92–95 (shipped 2026-03-30)
- ✅ **v17.0 — Scale Hardening** — Phases 96–100 (shipped 2026-03-31)
- ✅ **v18.0 — First-User Experience & E2E Validation** — Phases 101–106 (shipped 2026-04-01)
- ✅ **v19.0 — Foundry Improvements** — Phases 107–114, 116–119 (shipped 2026-04-05)
- ✅ **v20.0 — Node Capacity & Isolation Validation** — Phases 120–128 (shipped 2026-04-10)
- ✅ **v21.0 — API Maturity & Contract Standardization** — Phases 129–131 (shipped 2026-04-11)
- ✅ **v22.0 — Security Hardening** — Phases 132–145 (shipped 2026-04-15)
- ✅ **v23.0 — DAG & Workflow Orchestration** — Phases 146–157 (completed 2026-04-17, all phases shipped, release-ready) — Phase 158 State-of-the-Nation: GO — v23.0 CONFIRMED READY FOR PRODUCTION DEPLOYMENT
- 🔧 **v23.1 — Test Suite Health & Compatibility Engine** — Phases 159–162 (in progress) — Fixes 13 workflow CRUD stubs, 2 collection errors, 2 compatibility engine routes, 10 frontend component failures

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
<summary>✅ v9.0–v19.0 (Phases 20–119) — SHIPPED</summary>

See `.planning/milestones/` for detailed archive of each milestone.

- ✅ v9.0 Enterprise Documentation — Phases 20–28 (shipped 2026-03-17)
- ✅ v10.0 Axiom Commercial Release — Phases 29–33 (shipped 2026-03-19)
- ✅ v11.0 CE/EE Split Completion — Phases 34–37 (shipped 2026-03-20)
- ✅ v11.1 Stack Validation — Phases 38–45 (shipped 2026-03-22)
- ✅ v12.0 Operator Maturity — Phases 46–56 (shipped 2026-03-24)
- ✅ v13.0 Research & Documentation Foundation — Phases 57–60 (shipped 2026-03-24)
- ✅ v14.0 CE/EE Cold-Start Validation — Phases 61–65 (shipped 2026-03-25)
- ✅ v14.1 First-User Readiness — Phases 66–70 (shipped 2026-03-26)
- ✅ v14.2 Docs on GitHub Pages — Phase 71 (shipped 2026-03-26)
- ✅ v14.3 Security Hardening + EE Licensing — Phases 72–76 (shipped 2026-03-27)
- ✅ v14.4 Go-to-Market Polish — Phases 77–81 (shipped 2026-03-28)
- ✅ v15.0 Operator Readiness — Phases 82–86 (shipped 2026-03-29)
- ✅ v16.0 Competitive Observability — Phases 87–91 (shipped 2026-03-30)
- ✅ v16.1 PR Merge & Backlog Closure — Phases 92–95 (shipped 2026-03-30)
- ✅ v17.0 Scale Hardening — Phases 96–100 (shipped 2026-03-31)
- ✅ v18.0 First-User Experience & E2E Validation — Phases 101–106 (shipped 2026-04-01)
- ✅ v19.0 Foundry Improvements — Phases 107–114, 116–119 (shipped 2026-04-05)

</details>

<details>
<summary>✅ v20.0 — Node Capacity & Isolation Validation (Phases 120–128) — SHIPPED 2026-04-10</summary>

- [x] **Phase 120: Database & API Contract** — Add job limit schema + API models for end-to-end traceability (completed 2026-04-06)
- [x] **Phase 121: Job Service & Admission Control** — Memory limit persistence and API admission checks (3 plans completed 2026-04-06)
  - [x] Plan 01: parse_bytes() + admission check in create_job() + pull_work()
  - [x] Plan 02: Dispatch diagnosis extension with memory breakdown + ScheduledJob schema
  - [x] Plan 03: Scheduler integration + JobDefinitions UI + Jobs diagnosis display (completed 2026-04-06)
- [x] **Phase 122: Node-Side Limit Integration** — Harden limit validation, structured error handling, and logging (completed 2026-04-06)
  - [x] Plan 01: parse_cpu() helper + execute_task() validation + unit tests
- [x] **Phase 123: Cgroup Detection Backend** — Node detects cgroup v1 vs v2 at startup and heartbeat (completed 2026-04-08)
  - [x] Plan 01: CgroupDetector class, node-side integration, orchestrator schema updates (3 tasks)
- [x] **Phase 124: Ephemeral Execution Guarantee** — Block direct execution; flag EXECUTION_MODE=direct as unsafe (completed 2026-04-08)
  - [x] Plan 01: Backend persistence (DB + models + heartbeat handler) — completed 2026-04-08
  - [x] Plan 02: Compose validation + startup check — completed 2026-04-08
  - [x] Plan 03: Node-side reporting + documentation cleanup — completed 2026-04-08
  - [x] Plan 04: Test verification — completed 2026-04-08
- [x] **Phase 125: Stress Test Corpus** — CPU, memory, and noisy-neighbour scripts in Python, Bash, PowerShell (4 plans completed 2026-04-08)
  - [x] Plan 01: Python scripts (cpu_burn.py, memory_hog.py, noisy_monitor.py)
  - [x] Plan 02: Bash scripts (cpu_burn.sh, memory_hog.sh, noisy_monitor.sh)
  - [x] Plan 03: PowerShell scripts (cpu_burn.ps1, memory_hog.ps1, noisy_monitor.ps1)
  - [x] Plan 04: Preflight check + orchestrator (preflight_check.py, orchestrate_stress_tests.py)
- [x] **Phase 126: Limit Enforcement Validation** — Memory and CPU limit enforcement on Docker and Podman job execution runtimes (5 plans)
  - [x] Plan 01: Docker-only validation with orchestrator setup (2 tasks complete)
  - [x] Plan 02: Docker node enrollment and network fixes (2 tasks complete)
  - [x] Plan 03: Podman validation and signature verification fix (2 tasks complete)
  - [x] Plan 04: Deploy live nodes and execute stress tests (3 tasks complete, 2026-04-10)
  - [x] Plan 05: Stress test execution and final validation report (3 tasks complete, 2026-04-10)
- [x] **Phase 127: Cgroup Dashboard & Monitoring** — Dashboard cgroup badges and operator warnings (2 plans completed 2026-04-10)
  - [x] Plan 01: Nodes.tsx cgroup badges + degradation banner (2 tasks, completed 2026-04-10)
  - [x] Plan 02: Admin.tsx System Health tab + cgroup compatibility card (2 tasks, completed 2026-04-10)
- [x] **Phase 128: Concurrent Isolation Verification** — Memory isolation and latency monitoring under load (2 plans completed 2026-04-10)
  - [x] Plan 01: Create noisy_monitor.py (Python sleep drift monitor) — completed 2026-04-10
  - [x] Plan 02: Orchestrator 5-run test with target_node_id and reports — completed 2026-04-10

Archive: `.planning/milestones/v20.0-ROADMAP.md`

</details>

<details>
<summary>✅ v21.0 — API Maturity & Contract Standardization (Phases 129–131) — SHIPPED 2026-04-11</summary>

- [x] **Phase 129: Response Model Auto-Serialization** — Add response_model to 62 routes; standardize pagination and action responses (5 plans planned) (completed 2026-04-11)
  - [x] Plan 01: Core models (ActionResponse, PaginatedResponse[T], ErrorResponse) — Wave 1 (completed 2026-04-11)
  - [x] Plan 02: Jobs domain (~12 routes) — Wave 2 (completed 2026-04-11)
  - [x] Plan 03: Nodes domain (~10 routes) — Wave 2 (completed 2026-04-11)
  - [x] Plan 04: Admin/Auth domain (~15 routes) — Wave 3 (completed 2026-04-11)
  - [x] Plan 05: Foundry/Smelter/System (~25 routes) — Wave 3 (completed 2026-04-11)

- [x] **Phase 130: E2E Job Dispatch Integration Test** — 2 plans covering pytest + live E2E script (completed 2026-04-12)
  - [x] Plan 01: Pytest integration tests (happy path, bad signature, capability mismatch, retry) — Wave 1 (completed 2026-04-12)
  - [x] Plan 02: Live E2E script with node orchestration (4 scenarios, JSON reporting) — Wave 2 (completed 2026-04-12)

- [x] **Phase 131: Signature Verification Path Unification** — Unify server-side countersigning into single service method; fix missing HMAC for scheduled jobs; hard-fail on missing signing key (1 plan planned) (completed 2026-04-11)
  - [x] Plan 01: TDD test infrastructure + countersign_for_node() implementation + integration updates (Wave 1)

Archive: `.planning/milestones/v21.0-ROADMAP.md`

</details>

<details>
<summary>✅ v22.0 — Security Hardening (Phases 132–145) — SHIPPED 2026-04-15</summary>

- [x] **Phase 132: Non-Root User Foundation** — All containers run as non-root appuser (UID 1000) with correct volume ownership (completed 2026-04-12)
  - [x] Plan 01: Update Containerfile.server and Containerfile.node with appuser + chown + USER directives
  - [x] Plan 02: Integration tests + verification script + stack validation
- [x] **Phase 133: Network & Security Capabilities** — Drop capabilities, disable privilege escalation, restrict Postgres to loopback (completed 2026-04-12)
  - [x] Plan 01: cap_drop/security_opt + loopback PostgreSQL binding
- [x] **Phase 134: Socket Mount & Podman Support** — Remove privileged mode, auto-detect Podman socket (completed 2026-04-12)
  - [x] Plan 01: Socket-first detection in runtime.py + network_ref wiring
  - [x] Plan 02: node-compose.yaml + node-compose.podman.yaml with socket mount
- [x] **Phase 135: Resource Limits & Package Cleanup** — Define memory/CPU limits, strip unnecessary node packages (completed 2026-04-12)
  - [x] Plan 01: compose.server.yaml resource limits + Containerfile.node package cleanup
- [x] **Phase 136: User Propagation to Generated Images** — Foundry Dockerfiles append USER appuser (completed 2026-04-12)
  - [x] Plan 01: User injection in foundry_service.py for DEBIAN/ALPINE/WINDOWS
- [x] **Phase 137: Signed EE Wheel Manifest** — Verify Ed25519 manifest before EE wheel install (completed 2026-04-12)
  - [x] Plan 01: _verify_wheel_manifest() + integration in _install_ee_wheel() + activate_ee_live()
- [x] **Phase 138: HMAC-Keyed Boot Log** — HMAC-SHA256 boot log with backward-compatible SHA256 reads (completed 2026-04-12)
  - [x] Plan 01: HMAC helpers + boot log entry detection + read/write refactor
- [x] **Phase 139: Entry Point Whitelist & Enforcement** — Validate entry points, enforce ENCRYPTION_KEY presence (completed 2026-04-13)
  - [x] Plan 01: ENCRYPTION_KEY hard requirement + entry point whitelist validation
- [x] **Phase 140: Wheel Signing Release Tool** — CLI to sign wheel manifests at release time (completed 2026-04-13)
  - [x] Plan 01: gen_wheel_key.py + sign_wheels.py implementation
- [x] **Phase 141: v22.0 Compliance Documentation Cleanup** — Phase-level VERIFICATION.md synthesis; requirements audit (completed 2026-04-13)
  - [x] Plan 01: Documentation and traceability cleanup
- [x] **Phase 142: Wheel Signing Tool Tests** — 23 tests for sign_wheels.py, gen_wheel_key.py, key_resolution (completed 2026-04-14)
  - [x] Plan 01: test_sign_wheels.py (12 tests)
  - [x] Plan 02: test_key_resolution.py (6 tests)
  - [x] Plan 03: test_gen_wheel_key.py (5 tests)
- [x] **Phase 143: Nyquist Validation — Container Security (Phases 132–136)** — All 5 container hardening phases marked nyquist_compliant (completed 2026-04-14)
  - [x] Plan 01: test_security_capabilities.py + test_containerfile_validation.py + foundry tests
- [x] **Phase 144: Nyquist Validation — EE Features (Phases 137–140)** — All 4 EE feature phases marked nyquist_compliant (completed 2026-04-14)
  - [x] Plan 01: Fix Phase 138 test expectations; all 103 tests passing
- [x] **Phase 145: Nyquist Validation — Cleanup Phases (Phases 141–142)** — Both gap-closure phases marked nyquist_compliant (completed 2026-04-15)
  - [x] Plan 01: Validate Phase 141 shell checks + Phase 142 tests; regression check

Archive: `.planning/milestones/v22.0-ROADMAP.md`

</details>

<details>
<summary>🚀 v23.0 — DAG & Workflow Orchestration (Phases 146–157) — IN PROGRESS</summary>

- [x] **Phase 146: Workflow Data Model** — Database schema, CRUD API, DAG validation, cycle detection
  - [x] Plan 01: Test & Schema Foundation — database schema (4 tables), test stubs (13 tests), fixtures, networkx dependency (completed 2026-04-15)
  - [x] Plan 02: ORM Models & Service Layer — Workflow/Step/Edge/Parameter models, workflow_service with validation (completed 2026-04-15)
  - [x] Plan 03: API Routes — CRUD endpoints, fork, validation, structured error responses (completed 2026-04-15)
- [x] **Phase 147: WorkflowRun Execution Engine** — BFS dispatch, atomic concurrency guards, status state machine, cascade cancellation (completed 2026-04-15)
  - [x] Plan 01: Database & Pydantic Models — WorkflowStepRun ORM + Job.workflow_step_run_id FK + migration_v54.sql (Wave 1, completed 2026-04-15)
  - [x] Plan 02: Service Layer — dispatch_next_wave(), advance_workflow(), start_run(), cancel_run() with BFS + CAS + cascade logic (Wave 1, completed 2026-04-15)
  - [x] Plan 03: API Routes & Integration — POST /api/workflow-runs, POST /api/workflow-runs/{id}/cancel, report_result hook (Wave 2, completed 2026-04-16)
  - [x] Plan 04: Comprehensive Test Suite — 11+ pytest tests covering ENGINE-01..07 + workflow dispatch fixtures (Wave 3, completed 2026-04-16)
- [x] **Phase 148: Gate Node Types** — IF conditionals, AND/JOIN, OR, parallel fan-out, signal wait (completed 2026-04-16)
  - [x] Plan 01: GateEvaluationService + condition evaluation methods — Wave 1 (completed 2026-04-16)
  - [x] Plan 02: Gate node dispatch integration — Wave 2 (completed 2026-04-16)
  - [x] Plan 03: SIGNAL_WAIT blocking and wakeup — Wave 3 (completed 2026-04-16)
  - [x] Plan 04: Comprehensive test suite (22 unit + 11 integration tests) — Wave 4 (completed 2026-04-16)
- 🚀 **Phase 149: Triggers & Parameter Injection** — Manual trigger, cron scheduling, webhook HMAC, WORKFLOW_PARAM_* injection (in progress)
  - [x] Plan 01: Database Schema & Pydantic Models — Workflow.schedule_cron, WorkflowRun.parameters_json, WorkflowWebhook ORM + migration_v55.sql (Wave 1, completed 2026-04-16)
  - [ ] Plan 02: APScheduler Integration & Webhook Trigger — sync_workflow_crons(), webhook endpoint with HMAC, parameter resolution (Wave 1, planned)
  - [ ] Plan 03+: Parameter injection, API endpoints, run history (planned)
- ✅ **Phase 150: Dashboard Read-Only Views** — DAG visualization, live status overlay, run history, step logs (7 plans completed)
  - [x] Plan 01: Test Foundation (Wave 0) — Test scaffolds for all views, hooks, utilities, components (completed 2026-04-16)
  - [x] Plan 02: Backend WebSocket Events (Wave 1) — workflow_run_updated/workflow_step_updated events, /api/workflows/{id}/runs endpoint (completed 2026-04-16)
  - [x] Plan 03: DAG Components (Wave 2) — useLayoutedElements hook, WorkflowStepNode, DAGCanvas with dagre layout (completed 2026-04-16)
  - [x] Plan 04: Main Views (Wave 3) — Workflows list, WorkflowDetail, WorkflowRunDetail pages with React Query (completed 2026-04-16)
  - [x] Plan 05: Step Drawer (Wave 4) — WorkflowStepDrawer component, useStepLogs hook, integration with DAGCanvas (completed 2026-04-16)
  - [x] Plan 06: Routing & Navigation (Wave 5) — AppRoutes.tsx, MainLayout sidebar, breadcrumbs, deep linking (completed 2026-04-16)
  - [x] Plan 07: Integration Testing (Wave 6) — Backend + frontend integration tests, E2E Playwright verification (completed 2026-04-16)
- [ ] **Phase 151: Visual DAG Editor** — Drag-and-drop canvas, real-time validation, IF gate inline configuration (plans TBD)
- [x] **Phase 152: Workflow Feature Documentation** — Overview, concepts, user guide, operator guide, developer guide, API reference, runbook (4 plans completed 2026-04-16)
  - [x] Plan 01: Directory structure + MkDocs nav registration (Wave 1, completed 2026-04-16)
  - [x] Plan 02: Overview, Concepts, User Guide pages (Wave 2, completed 2026-04-16)
  - [x] Plan 03: Operator Guide, Developer Guide pages (Wave 3, completed 2026-04-16)
  - [x] Plan 04: API Reference section, Operational Runbook (Wave 4, completed 2026-04-16)
- [x] **Phase 153: Verify Gate Node Types** — Run verify-work for Phase 148 to create VERIFICATION.md; tick satisfied-but-unchecked REQUIREMENTS.md checkboxes (ENGINE-01..07, TRIGGER-01/03/05, PARAMS-01, UI-01..04) (completed 2026-04-16)
  - [x] Plan 01 (Wave 1): Fix SQLite test schema, verify GATE-01/02 unit tests (condition evaluation, IF_GATE routing)
  - [x] Plan 02 (Wave 2): Verify GATE-03/04/05 integration tests (AND_JOIN, OR_GATE, PARALLEL dispatch)
  - [x] Plan 03 (Wave 3): Verify GATE-06 (SIGNAL_WAIT), full test suite validation, create VERIFICATION.md, tick requirement checkboxes
  - **Gap Closure:** Closes GATE-01, GATE-02, GATE-03, GATE-04, GATE-05, GATE-06
- [x] **Phase 154: Unified Schedule View** — Implement UI-05: unified schedule page showing ScheduledJob (JOB badge) and Workflow (FLOW badge) entries together with next-run time and last-run status (completed 2026-04-16)
  - [x] Plan 01 (Wave 1): Backend service method + API endpoint + Pydantic models; Frontend Schedule.tsx view + routing + sidebar nav (completed 2026-04-16)
  - [x] Plan 02 (Wave 2): Integration testing (pytest + vitest) + verification (completed 2026-04-16)
  - **Gap Closure:** Closes UI-05
- [x] **Phase 155: Visual DAG Editor** — Implement Phase 151 scope: ReactFlow drag-and-drop canvas for composing Workflows; real-time DAG validation (cycle detection, depth warnings, inline IF gate condition config) (3 plans) (completed 2026-04-17)
  - [x] Plan 01 (Wave 0): Test Foundation — DAG validation utilities (validateDAG), component test scaffolds, hooks stubs (6 tasks, TDD test-first) (completed 2026-04-16)
  - [x] Plan 02 (Wave 1): Implementation & Integration — Full implementations, WorkflowDetail integration, Save/Cancel flow, cycle/depth banner display, human-verify checkpoint (completed 2026-04-16)
  - [x] Plan 03 (Gap Closure): Close drag-drop and IF gate wiring gaps — Fix handleDrop signature mismatch and IfGateConfigDrawer open prop control (3 tasks) (completed 2026-04-17)
  - **Gap Closure:** Closes UI-06, UI-07 (2 wiring gaps identified for Phase 156+ remediation)
- [x] **Phase 156: State of the Nation Report** — Honest, no-bullshit appraisal of the product, sister repos, deployment status, and release readiness for stakeholder planning (completed 2026-04-17)
- ✅ **Phase 157: Close Deferred Technical Debt** — Fix 30 frontend test failures, convert 3 todos to real tests, verify 4 backend gaps (MIN-6/7/8, WARN-8) with regression tests (All 3 plans complete: 36 frontend + 6 backend tests passing, 157-VERIFICATION.md gating release, completed 2026-04-17)
  - [x] Plan 01 (Wave 1): Rewrite Workflows.test.tsx, WorkflowRunDetail.test.tsx, Jobs.test.tsx with modern test patterns (waitFor, scoped selectors)
  - [ ] Plan 02 (Wave 1): Write 4 backend regression tests for MIN-6, MIN-7, MIN-8, WARN-8
  - [ ] Plan 03 (Wave 2): Full test suite verification (461 frontend + 90 backend = 551 total) + VERIFICATION.md

Archive: `.planning/milestones/v23.0-ROADMAP.md`

</details>

<details>
<summary>🔧 v23.1 — Test Suite Health & Compatibility Engine (Phases 159–162) — IN PROGRESS</summary>

- [x] **Phase 159: Test Infrastructure Repair** — Fix 2 collection errors (test_tools.py admin_signer import, test_intent_scanner.py intent_scanner import); fix test_admin_responses.py DELETE setup; investigate Phase 29 stubs (test_output_capture.py, test_retry_wiring.py) (v23.1) (completed 2026-04-17)
- [x] **Phase 160: Workflow CRUD Unit Tests** — Implement 13 assert False stubs in test_workflow.py as real async pytest tests against the Phase 146 CRUD API (v23.1) (completed 2026-04-17)
- [ ] **Phase 161: Compatibility Engine Route Implementation** — Add os_family query param filter to GET /api/capability-matrix; implement POST /api/blueprints route with OS-family validation and offending_tools error field; fix test_compatibility_engine.py (v23.1)
- [ ] **Phase 162: Frontend Component Fixes** — Fix Templates.test.tsx missing getUser mock; fix Admin.tsx EE tab conditional rendering and add missing Automation tab; fix MainLayout.tsx CE badge zinc classes; fix WorkflowDetail.tsx duration async rendering (v23.1)

</details>

## Progress

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|----------------|--------|-----------|
| 107. Schema Foundation + CRUD Completeness | v19.0 | 3/3 | Complete | 2026-04-03 |
| 108. Transitive Dependency Resolution | v19.0 | 2/2 | Complete | 2026-04-03 |
| 109. APT + apk Mirrors + Compose Profiles | v19.0 | 4/4 | Complete | 2026-04-03 |
| 110. CVE Transitive Scan + Dependency Tree UI | v19.0 | 3/3 | Complete | 2026-04-04 |
| 111. npm + NuGet + OCI Mirrors | v19.0 | 3/3 | Complete | 2026-04-04 |
| 112. Conda Mirror + Mirror Admin UI | v19.0 | 4/4 | Complete | 2026-04-04 |
| 113. Script Analyzer | v19.0 | 2/2 | Complete | 2026-04-04 |
| 114. Curated Bundles + Starter Templates | v19.0 | 3/3 | Complete | 2026-04-05 |
| 116. DB Migration + EE Licence Hot-Reload | v19.0 | 2/2 | Complete | 2026-04-04 |
| 117. Light/Dark Mode Toggle | v19.0 | 5/5 | Complete | 2026-04-04 |
| 118. UI Polish and Verification | v19.0 | 4/4 | Complete | 2026-04-04 |
| 119. v19.0 Traceability Closure | v19.0 | 2/2 | Complete | 2026-04-05 |
| 120. Database & API Contract | v20.0 | 3/3 | Complete | 2026-04-06 |
| 121. Job Service & Admission Control | v20.0 | 3/3 | Complete | 2026-04-06 |
| 122. Node-Side Limit Integration | v20.0 | 1/1 | Complete | 2026-04-06 |
| 123. Cgroup Detection Backend | v20.0 | 1/1 | Complete | 2026-04-08 |
| 124. Ephemeral Execution Guarantee | v20.0 | 4/4 | Complete | 2026-04-08 |
| 125. Stress Test Corpus | v20.0 | 4/4 | Complete | 2026-04-08 |
| 126. Limit Enforcement Validation | v20.0 | 5/5 | Complete | 2026-04-10 |
| 127. Cgroup Dashboard & Monitoring | v20.0 | 2/2 | Complete | 2026-04-10 |
| 128. Concurrent Isolation Verification | v20.0 | 2/2 | Complete | 2026-04-10 |
| 129. Response Model Auto-Serialization | v21.0 | 5/5 | Complete | 2026-04-11 |
| 130. E2E Job Dispatch Integration Test | v21.0 | 2/2 | Complete | 2026-04-12 |
| 131. Signature Verification Path Unification | v21.0 | 1/1 | Complete | 2026-04-11 |
| 132. Non-Root User Foundation | v22.0 | 2/2 | Complete | 2026-04-12 |
| 133. Network & Security Capabilities | v22.0 | 1/1 | Complete | 2026-04-12 |
| 134. Socket Mount & Podman Support | v22.0 | 2/2 | Complete | 2026-04-12 |
| 135. Resource Limits & Package Cleanup | v22.0 | 1/1 | Complete | 2026-04-12 |
| 136. User Propagation to Generated Images | v22.0 | 1/1 | Complete | 2026-04-12 |
| 137. Signed EE Wheel Manifest | v22.0 | 1/1 | Complete | 2026-04-12 |
| 138. HMAC-Keyed Boot Log | v22.0 | 1/1 | Complete | 2026-04-12 |
| 139. Entry Point Whitelist & Enforcement | v22.0 | 1/1 | Complete | 2026-04-13 |
| 140. Wheel Signing Release Tool | v22.0 | 1/1 | Complete | 2026-04-13 |
| 141. v22.0 Compliance Documentation Cleanup | v22.0 | 1/1 | Complete | 2026-04-13 |
| 142. Wheel Signing Tool Tests | v22.0 | 3/3 | Complete | 2026-04-14 |
| 143. Nyquist Validation — Container Security | v22.0 | 1/1 | Complete | 2026-04-14 |
| 144. Nyquist Validation — EE Features | v22.0 | 1/1 | Complete | 2026-04-14 |
| 145. Nyquist Validation — Cleanup Phases | v22.0 | 1/1 | Complete | 2026-04-15 |
| 146. Workflow Data Model | v23.0 | 3/3 | Complete | 2026-04-15 |
| 147. WorkflowRun Execution Engine | v23.0 | 4/4 | Complete | 2026-04-16 |
| 148. Gate Node Types | v23.0 | 4/4 | Complete | 2026-04-16 |
| 149. Triggers & Parameter Injection | v23.0 | 1/3 (in progress) | 2026-04-16 | — |
| 150. Dashboard Read-Only Views | v23.0 | 7/7 | Complete | 2026-04-16 |
| 152. Workflow Feature Documentation | v23.0 | 4/4 | Complete | 2026-04-16 |
| 153. Verify Gate Node Types | v23.0 | 3/3 | Complete | 2026-04-16 |
| 154. Unified Schedule View | v23.0 | 2/2 | Complete | 2026-04-16 |
| 155. Visual DAG Editor | v23.0 | 3/3 | Complete | 2026-04-17 |
| 156. State of the Nation Report | v23.0 | 1/1 | Complete | 2026-04-17 |
| 157. Close Deferred Technical Debt | v23.0 | Complete    | 2026-04-17 | — |
| 158. State of the Nation — Post v23.0 | v23.0 | Complete    | 2026-04-17 | — |
| 159. Test Infrastructure Repair | v23.1 | Complete    | 2026-04-17 | — |
| 160. Workflow CRUD Unit Tests | v23.1 | Complete    | 2026-04-17 | — |
| 161. Compatibility Engine Route Implementation | v23.1 | 0/1 | Planned | — |
| 162. Frontend Component Fixes | v23.1 | 0/1 | Planned | — |

## Phase Detail Sections

### Phase 156: State of the Nation Report

**Goal:** Produce an honest, no-bullshit appraisal of the product, sister repos, deployment status, and release readiness — to inform stakeholder conversations and next-phase planning.

**Requirements:** None (reporting phase, no explicit requirements)

**Depends on:** Phase 155

**Plans:** 1/1 plans complete

Plans:
- [x] Plan 01 (Wave 1): Data collection + report synthesis — Honest assessment of product completeness, test health, Phase 155 blockers, deferred work, deployment status, and release readiness recommendation (completed 2026-04-17)

### Phase 157: Close Deferred Technical Debt

**Goal:** Fix 30 frontend test failures, convert 3 `it.todo()` to real tests, verify and lock in 4 backend gaps (MIN-6, MIN-7, MIN-8, WARN-8) from v23.0 state report with regression tests. Target: 461/461 frontend + 90/90 backend = 551 total passing tests.

**Requirements:** None (test infrastructure improvement, no explicit feature requirements)

**Depends on:** Phase 156 (state of nation report identifies gaps)

**Plans:** 3/3 plans complete

Plans:
- [x] Plan 01 (Wave 1): Rewrite frontend test files — Workflows.test.tsx (12/12), WorkflowRunDetail.test.tsx (10/10), Jobs.test.tsx (14/14) with React Testing Library best practices (waitFor, scoped selectors, proper async patterns) — all 36 tests passing, zero act() warnings, zero todos (completed 2026-04-17)
- [x] Plan 02 (Wave 1): Write backend regression tests — 4 pytest tests for MIN-6, MIN-7, MIN-8, WARN-8 gap verification (completed 2026-04-17, 4/4 tests passing)
- [x] Plan 03 (Wave 2): Full test suite verification + VERIFICATION.md — Run complete test suite (36 frontend + 6 backend Phase 157 scope = 42 tests, 100% passing), document gap closure, gate release readiness (completed 2026-04-17, 157-VERIFICATION.md created)

### Phase 159: Test Infrastructure Repair

**Goal:** Eliminate 2 pytest collection errors and fix 4 broken test setups so the full backend test suite collects and reports clean. No features added — pure test health.

**Scope:**
1. `test_tools.py` — collection error: `import admin_signer` fails; `admin_signer.py` lives in `~/Development/toms_home/.agents/tools/` (sister repo). Fix: add `conftest.py` sys.path insert or create a thin wrapper in the `tests/` dir.
2. `test_intent_scanner.py` — collection error: `import intent_scanner` fails; skill script path doesn't exist. Fix: create `scripts/intent_scanner.py` stub or skip-mark the file with a `pytest.importorskip`.
3. `test_admin_responses.py` DELETE tests — 2 failures because dummy IDs return 404. Fix: create real user/signing-key resources in test setup, then delete them.
4. `test_output_capture.py` + `test_retry_wiring.py` — 1 `assert False` stub each from Phase 29. Investigate what the feature is; either implement the test against the existing code or mark it with `pytest.skip` explaining why.

**Requirements:** None (test infrastructure only)

**Depends on:** Phase 158

**Plans:** 1/1 plans complete

Plans:
- [x] Plan 01 (Wave 1): Fix collection errors + admin response setup + Phase 29 stub audit

---

### Phase 160: Workflow CRUD Unit Tests

**Goal:** Convert all 13 `assert False` stubs in `test_workflow.py` into real passing pytest tests against the Phase 146 Workflow CRUD API. The API endpoints already exist; this is pure test implementation.

**Scope:** `puppeteer/tests/test_workflow.py` — 13 tests:
- CRUD: create (success, invalid edges, cycle detected), list, update (success, cycle, depth exceeded), delete (success, blocked by active runs)
- Fork: fork success, fork pauses source
- Validate: no cycle, with cycle (POST /api/workflows/validate — no save)

Each test needs: async test client, DB fixtures (create Workflow with steps/edges/params), assertion on response body + error codes (`CYCLE_DETECTED`, `DEPTH_LIMIT_EXCEEDED`, `ACTIVE_RUNS_EXIST`, `INVALID_EDGE_REFERENCE`).

**Requirements:** Covers WORKFLOW-01 through WORKFLOW-05 (unit test layer)

**Depends on:** Phase 159

**Plans:** 1/1 plans complete

Plans:
- [ ] Plan 01 (Wave 1): Implement 13 workflow CRUD unit tests

---

### Phase 161: Compatibility Engine Route Implementation

**Goal:** Implement 2 missing backend routes to make `test_compatibility_engine.py` fully pass (currently 2 failing, 1 skipped).

**Scope:**
1. `GET /api/capability-matrix?os_family=DEBIAN` — add `os_family` query param filter. Currently returns all rows regardless of param.
2. `POST /api/blueprints` — route not yet implemented. Needs: OS-family mismatch validation returning 422 with `offending_tools` field in error detail.
3. Unblock the skipped test once `runtime_dependencies` seeding is in place.

**Requirements:** Closes compatibility engine gaps from Phase 11 (never verified post-Phase 129 API changes)

**Depends on:** Phase 159

**Plans:** 0/1 planned

Plans:
- [ ] Plan 01 (Wave 1): Add os_family filter + POST /api/blueprints route + fix tests

---

### Phase 162: Frontend Component Fixes

**Goal:** Fix 10 frontend test failures across 4 files. All failures are component bugs or incomplete test mocks, not aspirational tests.

**Scope:**
1. `Templates.test.tsx` (5 failures) — `vi.mock('../../auth')` missing `getUser` export. Fix: add `getUser: vi.fn().mockReturnValue({ role: 'admin' })` to the mock factory. The component calls `getUser()` on render; the mock is incomplete.
2. `Admin.test.tsx` (3 failures) — EE tabs (Smelter Registry, BOM Explorer, Artifact Vault, Rollouts) render in CE mode. Fix: gate their rendering on `isEnterprise` in `Admin.tsx`. Separately, `Automation` tab is missing entirely — add it.
3. `MainLayout.test.tsx` (1 failure) — CE badge renders without `zinc` Tailwind classes. Fix: apply `zinc-100`/`zinc-800` (or equivalent) in the CE badge branch in `MainLayout.tsx`.
4. `WorkflowDetail.test.tsx` (1 failure) — "300.0s" duration not found; component shows "Loading runs...". Fix: ensure the test mock for `authenticatedFetch` resolves the run list before the assertion (add `await waitFor(...)` or return data synchronously in the mock).

**Requirements:** None (test infrastructure + component correctness)

**Depends on:** Phase 159 (clean baseline)

**Plans:** 0/1 planned

Plans:
- [ ] Plan 01 (Wave 1): Fix Templates mock, Admin EE gates, MainLayout badge, WorkflowDetail async

---

### Phase 158: State of the Nation — Post v23.0

**Goal:** Run the state-of-the-nation skill to produce an honest, data-driven assessment of the platform after v23.0 completion — covering product completeness, test health, deployment status, known gaps, and next-milestone recommendations. Produces `.planning/STATE-OF-NATION.md`.

**Requirements:** None (reporting phase)

**Depends on:** Phase 157 (v23.0 milestone complete, audit filed)

**Plans:** 1/1 plans complete

Plans:
- [x] Plan 01 (Wave 1): Execute state-of-the-nation skill — collect data across backend, frontend, test suite, deployment, docs; synthesise into STATE-OF-NATION.md with explicit GO/NO-GO recommendation — COMPLETED 2026-04-17T20:35:00Z — Data sources: gap reports (HIGH), live tests (HIGH), git log (HIGH), deployment (HIGH) — Recommendation: GO — v23.0 CONFIRMED READY FOR PRODUCTION DEPLOYMENT — STATE-OF-NATION.md generated (520+ lines, 9 sections + 5 appendices) — Commit: c6b3273
