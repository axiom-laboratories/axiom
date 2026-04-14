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
- ✅ **v17.0 — Scale Hardening** — Phases 96–100 (shipped 2026-03-31)
- ✅ **v18.0 — First-User Experience & E2E Validation** — Phases 101–106 (shipped 2026-04-01)
- ✅ **v19.0 — Foundry Improvements** — Phases 107–114, 116–119 (shipped 2026-04-05)
- ✅ **v20.0 — Node Capacity & Isolation Validation** — Phases 120–128 (shipped 2026-04-10)
- ✅ **v21.0 — API Maturity & Contract Standardization** — Phases 129–131 (shipped 2026-04-11)
- 🔄 **v22.0 — Security Hardening** — Phases 132–142 (in progress)

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
<summary>🔄 v22.0 — Security Hardening (Phases 132–142) — IN PROGRESS</summary>

- [x] **Phase 132: Non-Root User Foundation** — All containers run as non-root appuser (UID 1000) with correct volume ownership (completed 2026-04-12)
  - [ ] Plan 01: Update Containerfile.server and Containerfile.node with appuser + chown + USER directives (Wave 1)
  - [ ] Plan 02: Integration tests + verification script + stack validation (Wave 2)
- [x] **Phase 133: Network & Security Capabilities** — Drop capabilities, disable privilege escalation, restrict Postgres to loopback (completed 2026-04-12)
- [x] **Phase 134: Socket Mount & Podman Support** — Remove privileged mode, auto-detect Podman socket (completed 2026-04-12)
  - [x] Plan 01: Socket-first detection in runtime.py + network_ref wiring (Wave 1; completed 2026-04-12)
  - [ ] Plan 02: Docker + Podman compose variants + node.py integration (Wave 2)
- ⬜ **Phase 135: Resource Limits & Package Cleanup** — Define memory/CPU limits, strip unnecessary node packages (1 plan planned)
  - [ ] Plan 01: compose.server.yaml resource limits + Containerfile.node package cleanup (Wave 1)
- [x] **Phase 136: User Propagation to Generated Images** — Foundry Dockerfiles append USER appuser (completed 2026-04-12)
- [x] **Phase 137: Signed EE Wheel Manifest** — Verify Ed25519 manifest before EE wheel install (completed 2026-04-12)
- [x] **Phase 138: HMAC-Keyed Boot Log** — HMAC-SHA256 boot log with backward-compatible SHA256 reads (completed 2026-04-12)
  - [x] Plan 01: HMAC helpers + boot log entry detection + read/write refactor (completed 2026-04-12)
- [x] **Phase 139: Entry Point Whitelist & Enforcement** — Validate entry points, enforce ENCRYPTION_KEY presence (completed 2026-04-13)
  - [ ] Plan 01: ENCRYPTION_KEY hard requirement + entry point whitelist validation (Wave 1)
- [x] **Phase 140: Wheel Signing Release Tool** — CLI to sign wheel manifests at release time (completed 2026-04-13)
  - [ ] Plan 01: gen_wheel_key.py + sign_wheels.py implementation + 23 unit tests (Wave 1)
- ⬜ **Phase 141: v22.0 Compliance Documentation Cleanup** — Create Phase 139 phase-level VERIFICATION.md; fix 10 stale REQUIREMENTS.md checkboxes and traceability rows (gap closure phase)
- ⬜ **Phase 142: Wheel Signing Tool Tests** — Implement 23 test stubs in axiom-licenses/tests/tools/ for sign_wheels.py and gen_wheel_key.py (3 plans)
  - [x] Plan 01: test_sign_wheels.py (12 tests) — Wave 1 (completed 2026-04-14)
  - [x] Plan 02: test_key_resolution.py (6 tests) — Wave 1 (completed 2026-04-14)
  - [x] Plan 03: test_gen_wheel_key.py (5 tests) — Wave 1 (completed 2026-04-14)

Full details: `.planning/v22.0-ROADMAP.md`

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
| 132. Non-Root User Foundation | v22.0 | Complete    | 2026-04-12 | — |
| 133. Network & Security Capabilities | v22.0 | 1/1 | Complete | 2026-04-12 |
| 134. Socket Mount & Podman Support | v22.0 | Complete    | 2026-04-12 | — |
| 138. HMAC-Keyed Boot Log | v22.0 | Complete    | 2026-04-12 | 2026-04-12 |

## Archived

- ✅ **v21.0 — API Maturity & Contract Standardization** (Phases 129–131) — shipped 2026-04-11 → `.planning/milestones/v21.0-ROADMAP.md`
- ✅ **v20.0 — Node Capacity & Isolation Validation** (Phases 120–128) — shipped 2026-04-10 → `.planning/milestones/v20.0-ROADMAP.md`
- ✅ **v19.0 — Foundry Improvements** (Phases 107–114, 116–119) — shipped 2026-04-05 → `.planning/milestones/v19.0-ROADMAP.md`
- ✅ **v18.0 — First-User Experience & E2E Validation** (Phases 101–106) — shipped 2026-04-01 → `.planning/milestones/v18.0-ROADMAP.md`
- ✅ **v16.1 — PR Merge & Backlog Closure** (Phases 92–95) — shipped 2026-03-30 → `.planning/milestones/v16.1-ROADMAP.md`
- ✅ **v14.3 — Security Hardening + EE Licensing** (Phases 72–76) — shipped 2026-03-27 → `.planning/milestones/v14.3-ROADMAP.md`
- ✅ **v14.2 — Docs on GitHub Pages** (Phase 71) — shipped 2026-03-26 → `.planning/milestones/v14.2-ROADMAP.md`
