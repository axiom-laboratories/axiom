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
- ✅ **v23.0 — DAG & Workflow Orchestration** — Phases 146–164 (shipped 2026-04-18)
- ✅ **v24.0 — Security Infrastructure & Extensibility** — Phases 165–172 (shipped 2026-04-20)
- 🚧 **v25.0 — EE Validation & Infrastructure** — Phases 173–175 (in progress)

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
- ✅ v12.0 Operator Maturity — Phases 46–56 (shipped 2026-04-24)
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
<summary>✅ v23.0 — DAG & Workflow Orchestration (Phases 146–164) — SHIPPED 2026-04-18</summary>

- [x] **Phase 146: Workflow Data Model** — Database schema, CRUD API, DAG validation, cycle detection (completed 2026-04-15)
- [x] **Phase 147: WorkflowRun Execution Engine** — BFS dispatch, atomic concurrency guards, status state machine, cascade cancellation (completed 2026-04-16)
- [x] **Phase 148: Gate Node Types** — IF conditionals, AND/JOIN, OR, parallel fan-out, signal wait (completed 2026-04-16)
- [x] **Phase 149: Triggers & Parameter Injection** — Manual trigger, cron scheduling, webhook HMAC-SHA256, WORKFLOW_PARAM_* injection (completed 2026-04-16)
- [x] **Phase 150: Dashboard Read-Only Views** — DAG visualization, live status overlay, run history, step logs (7 plans, completed 2026-04-16)
- [x] **Phase 152: Workflow Feature Documentation** — Overview, concepts, user guide, operator guide, developer guide, API reference, runbook (completed 2026-04-16)
- [x] **Phase 153: Verify Gate Node Types** — VERIFICATION.md for Phase 148; gap closure for GATE-01..06 (completed 2026-04-16)
- [x] **Phase 154: Unified Schedule View** — UI-05: JOB + FLOW badge schedule list with next-run time and last-run status (completed 2026-04-16)
- [x] **Phase 155: Visual DAG Editor** — ReactFlow drag-and-drop canvas; real-time cycle/depth validation; inline IF gate config (completed 2026-04-17)
- [x] **Phase 156: State of the Nation Report** — GO verdict: v23.0 confirmed production-ready (completed 2026-04-17)
- [x] **Phase 157: Close Deferred Technical Debt** — 36 frontend + 6 backend regression tests; MIN-6/7/8, WARN-8 verified (completed 2026-04-17)
- [x] **Phase 158: State of the Nation — Post v23.0** — STATE-OF-NATION.md (520+ lines, 9 sections); GO recommendation confirmed (completed 2026-04-17)
- [x] **Phase 159: Test Infrastructure Repair** — 2 collection errors fixed; test_admin_responses.py setup fixed; Phase 29 stubs audited (completed 2026-04-17)
- [x] **Phase 160: Workflow CRUD Unit Tests** — 13 assert-False stubs replaced with real async pytest tests (completed 2026-04-17)
- [x] **Phase 161: Compatibility Engine Route Implementation** — EE router direct import pattern; test_compatibility_engine.py fixed (completed 2026-04-17)
- [x] **Phase 162: Frontend Component Fixes** — Templates getUser mock; Admin EE gates; MainLayout zinc badge; WorkflowDetail async (completed 2026-04-17)
- [x] **Phase 163: v23.0 Tech Debt Closure** — VALIDATION.md for phases 158–162; Nyquist 16/16; milestone audit fully compliant (completed 2026-04-17)
- [x] **Phase 164: Adversarial Audit Remediation** — mTLS enforcement (SEC-01), Foundry RCE whitelist (SEC-02), Alembic migration framework (ARCH-01), Caddy internal TLS (SEC-04), public key externalization (QUAL-02), frontend-backend alignment (FEBE-01/02/03) (completed 2026-04-18)

Archive: `.planning/milestones/v23.0-ROADMAP.md`

</details>

<details>
<summary>✅ v24.0 — Security Infrastructure & Extensibility (Phases 165–172) — SHIPPED 2026-04-20</summary>

- [x] **Phase 165: Dependabot CVE Remediation** — Resolve all HIGH and MODERATE security vulnerabilities flagged on v23.0 release tag (completed 2026-04-18)
  - [x] Plan 01: Update cryptography >= 46.0.7 and crypto chain (python-jose, PyJWT); rebuild Docker; pytest validation
  - [x] Plan 02: Update npm packages to resolve HIGH/MODERATE CVEs; create .github/dependabot.yml automation
  - [x] Plan 03: E2E smoke tests (mop-e2e); Docker verification; final audit snapshot

- [x] **Phase 166: Router Modularization** — Refactor main.py (3,828 lines) into 6 domain-specific APIRouter modules; 105 routes across 85 paths; zero NEW test failures (6 plans, completed 2026-04-18)
  - [x] Plan 01: Extract auth_router and jobs_router; wire both into main.py (Wave 1) (completed 2026-04-18)
  - [x] Plan 02: Extract nodes_router and workflows_router; wire all 4 routers; verify pytest (Wave 1) (completed 2026-04-18)
  - [x] Plan 03: Extract admin_router and system_router; wire all 7 routers; remove duplicate routes from main.py; verify pytest (Wave 2) (completed 2026-04-18)
  - [x] Plan 04: Create openapi_diff.py; verify OpenAPI schema (105 routes, zero operation ID conflicts, zero behavior change); remove remaining duplicate handlers (Wave 2) (completed 2026-04-18)
  - [x] Plan 05: Full pytest suite regression validation (736 tests pass, zero NEW failures from refactoring) (Wave 2) (completed 2026-04-18)
  - [x] Plan 06: Final comprehensive verification (routers, main.py shell, OpenAPI completeness, pytest) (Wave 3) (completed 2026-04-18)

- [x] **Phase 167: HashiCorp Vault Integration (EE)** — External secrets management with AppRole auth, lease renewal, graceful fallback (completed 2026-04-18)
  - [x] Plan 01: Vault service layer (hvac AppRole client, secret fetch/cache, lease renewal)
  - [x] Plan 02: Job dispatch secrets injection + admin UI configuration
  - [x] Plan 03: Health-check endpoint + graceful degradation when Vault unavailable
  - [x] Plan 04: Dashboard admin panel integration + Vault status display
  - [x] Plan 05: EE-gating + CE fallback validation

- [x] **Phase 168: SIEM Audit Streaming (EE)** — Real-time audit log export with CEF/syslog formatting, batching, masking ✓ COMPLETE
  - [x] Plan 01: SIEM service layer (webhook/syslog backends, CEF formatter, batch queue) (completed 2026-04-18)
  - [x] Plan 02: EE gating + admin routes + lifespan wiring (completed 2026-04-18)
  - [x] Plan 03: Audit integration + env-var bootstrap (completed 2026-04-18)
  - [x] Plan 04: Admin Dashboard UI — SIEM configuration tab (completed 2026-04-18)
  - [x] Plan 05: Integration test suite (completed 2026-04-18)

- [x] **Phase 169: PR Review Fix — EE Licence Guard and Import Correctness (MEDIUM)** — Fix three MEDIUM issues from PR #24 review: add /api/admin/vault and /api/admin/siem to LicenceExpiryGuard.EE_PREFIXES; replace absolute imports in siem_router.py with relative imports; add test_service.shutdown() in try/finally to prevent APScheduler job leaks from test-connection calls ✓ COMPLETE

- [x] **Phase 170: PR Review Fix — Code Hygiene and Resource Safety (LOW)** — Fix four LOW issues from PR #24 review ✓ COMPLETE
  - [x] Plan 01: asyncio.get_running_loop() (D-01) + renewal_failures property (D-02) + route migrations (D-03–07) + VaultConfigSnapshot (D-08–11) (Wave 1)

- [x] **Phase 171: Security Hardening — Authorization, Credential Safety, and Vault Recovery** ✓ COMPLETE
  - [x] Plan 01: Authorization hardening — replace require_auth with require_permission on sensitive admin_router and jobs_router endpoints (token generation, bulk operations)
  - [x] Plan 02: Credential safety — scrub ADMIN_PASSWORD from startup log output; fix YAML injection in compose-file generation endpoint
  - [x] Plan 03: Vault service hardening — narrow exception catch in resolve(); add re-authentication recovery path when token expires (stuck degraded state); fix vault_router enabled-only filter blocking disabled-config CRUD
  - [x] Plan 04: Deps hardening — fix perm cache multi-worker race condition (per-request DB check or Redis-backed cache); add try/finally to WebSocket handler in system_router.py to prevent resource leak

- [x] **Phase 172: PR Review Fix — Critical CE/EE Table Isolation, Permission Cache Cleanup, and SIEM/Vault Hardening** — Fix remaining CRITICAL, HIGH, and MEDIUM issues from PR #24 review (completed 2026-04-20)
  - [x] Plan 01: Critical fixes — remove ghost perm-cache import from main.py; create EE_Base split to fix failing test_ce_table_count
  - [x] Plan 02: Hardening — cap Vault reauth retry loop; expand SIEM SENSITIVE_KEYS; add SIEM hot-reload rollback; add queue-overflow admin alert

Archive: `.planning/milestones/v24.0-ROADMAP.md`

</details>

## Active Phases

### 🚧 v25.0 — EE Validation & Infrastructure (Phases 173–175)

**Milestone Goal:** Confirm CE/EE segregation, licence gating, wheel security chain, and boot log enforcement all hold under adversarial conditions; consolidate Axiom tooling repos; produce a concrete licence storage architecture recommendation.

---

### Phase 173: EE Behavioural Validation Test Suite
**Goal**: Build a comprehensive automated test suite in `mop_validation` covering all 14 CE/EE behavioural scenarios (VAL-01 through VAL-14) — zero manual-only steps.
**Depends on**: Nothing
**Requirements**: VAL-01, VAL-02, VAL-03, VAL-04, VAL-05, VAL-06, VAL-07, VAL-08, VAL-09, VAL-10, VAL-11, VAL-12, VAL-13, VAL-14
**Success Criteria** (what must be TRUE):
  1. CE-only fixture: exactly 15 tables present, no EE schema, all feature flags false, 7 stub routes return 402
  2. EE fixture: 41 tables (15 CE + 26 EE) with valid licence; all EE flags true; `GET /api/licence` returns `status=VALID`
  3. Licence state machine: GRACE banner visible, EXPIRED triggers DEGRADED_CE (pull_work empty, not 402), absent/tampered licence → CE mode + no crash
  4. Wheel security chain: tampered SHA256 manifest raises `RuntimeError`; non-whitelisted entry point raises `RuntimeError`; EE does not load in either case
  5. Boot log HMAC: clock-rollback raises `RuntimeError` on EE; CE emits warning only
  6. Node limit: enrollment returns 402 when `active_nodes ≥ node_limit`; existing enrolled nodes continue
  7. All 14 VAL scenarios covered by automated pytest tests; `pytest mop_validation/tests/` passes with zero skips

Plans:
- [x] **173-01: Test fixtures + CE validation (VAL-01, VAL-02, VAL-03)** — shared pytest fixtures for CE-only and EE installs; table count assertion; feature flag endpoint; stub route sweep (PLAN created)
- [x] **173-02: Licence state machine tests (VAL-04 through VAL-09)** — valid, GRACE, EXPIRED, absent, tampered-signature scenarios (PLAN created)
- [x] **173-03: Wheel + boot log security tests (VAL-10, VAL-11, VAL-13)** — bad SHA256 manifest, non-whitelisted entry point, clock-rollback HMAC (PLAN created)
- [x] **173-04: Node limit test + coverage assertion (VAL-12, VAL-14)** — enrollment 402 at capacity; assert all VAL scenarios covered (PLAN created)

---

### Phase 174: mop_validation Repo Migration
**Goal**: Transfer `mop_validation` to the `axiom` GitHub organisation as a private repo; update all references so tooling, scripts, and CI continue to work without modification.
**Depends on**: Phase 173 (tests exist and pass before moving the repo)
**Requirements**: MIG-01, MIG-02, MIG-03, MIG-04
**Success Criteria** (what must be TRUE):
  1. `mop_validation` is accessible at `github.com/axiom/mop_validation` (private repo)
  2. All scripts in `mop_validation/scripts/` execute correctly from the new remote
  3. Local git remote `origin` points to `github.com/axiom/mop_validation`
  4. `CLAUDE.md` and `GEMINI.md` in `master_of_puppets` updated to reference the new org URL

Plans:
- [ ] 174-01: GitHub org transfer — initiate repo transfer to `axiom` org; verify clone, push, and all scripts work from new URL
- [ ] 174-02: Reference updates — update local git remote; update `CLAUDE.md` and `GEMINI.md` sister repo section

---

### Phase 175: Licence Architecture Analysis
**Goal**: Produce a structured, evidence-based comparison of three issued-licence storage approaches and deliver a concrete recommendation with rationale — not just a comparison table.
**Depends on**: Nothing (purely analytical; can run in parallel with 173/174)
**Requirements**: LIC-01, LIC-02, LIC-03
**Success Criteria** (what must be TRUE):
  1. Comparison covers all three options (current Git repo, DB-embedded, hybrid DB+Git) across all six dimensions (security, auditability, air-gap compatibility, operational complexity, CI/CD integration, recovery from data loss)
  2. "Why this over the others" rationale section is present with a single concrete recommendation
  3. If recommendation differs from current Git repo approach, a migration path is documented with effort estimate
  4. Delivered as `.planning/LIC-ANALYSIS.md`

Plans:
- [ ] 175-01: Research + comparison + recommendation — investigate `axiom-licences` repo structure; survey three options; write `LIC-ANALYSIS.md` with table, rationale, and (if needed) migration path

---

## Progress

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 173. EE Behavioural Validation | 4/4 | Planned ✓ | 2026-04-20 |
| 174. mop_validation Repo Migration | 0/2 | Not started | - |
| 175. Licence Architecture Analysis | 0/1 | Not started | - |

## Historical Progress

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
| 149. Triggers & Parameter Injection | v23.0 | 3/3 | Complete | 2026-04-16 |
| 150. Dashboard Read-Only Views | v23.0 | 7/7 | Complete | 2026-04-16 |
| 152. Workflow Feature Documentation | v23.0 | 4/4 | Complete | 2026-04-16 |
| 153. Verify Gate Node Types | v23.0 | 3/3 | Complete | 2026-04-16 |
| 154. Unified Schedule View | v23.0 | 2/2 | Complete | 2026-04-16 |
| 155. Visual DAG Editor | v23.0 | 3/3 | Complete | 2026-04-17 |
| 156. State of the Nation Report | v23.0 | 1/1 | Complete | 2026-04-17 |
| 157. Close Deferred Technical Debt | v23.0 | 3/3 | Complete | 2026-04-17 |
| 158. State of the Nation — Post v23.0 | v23.0 | 1/1 | Complete | 2026-04-17 |
| 159. Test Infrastructure Repair | v23.0 | 1/1 | Complete | 2026-04-17 |
| 160. Workflow CRUD Unit Tests | v23.0 | 1/1 | Complete | 2026-04-17 |
| 161. Compatibility Engine Route Implementation | v23.0 | 1/1 | Complete | 2026-04-17 |
| 162. Frontend Component Fixes | v23.0 | 1/1 | Complete | 2026-04-17 |
| 163. v23.0 Tech Debt Closure | v23.0 | 2/2 | Complete | 2026-04-17 |
| 164. Adversarial Audit Remediation | v23.0 | 4/4 | Complete | 2026-04-18 |
| 165. Dependabot CVE Remediation | v24.0 | 3/3 | Complete | 2026-04-18 |
| 166. Router Modularization | v24.0 | 6/6 | Complete | 2026-04-18 |
| 167. Vault Integration (EE) | v24.0 | 5/5 | Complete | 2026-04-18 |
| 168. SIEM Streaming (EE) | v24.0 | 5/5 | Complete | 2026-04-18 |
| 169. PR Review Fix — EE Licence Guard and Import Correctness | v24.0 | 1/1 | Complete | 2026-04-19 |
| 170. PR Review Fix — Code Hygiene and Resource Safety | v24.0 | 1/1 | Complete | 2026-04-19 |
| 171. Security Hardening — Authorization, Credential Safety, and Vault Recovery | v24.0 | 4/4 | Complete | 2026-04-19 |
| 172. PR Review Fix — Critical CE/EE Table Isolation, Permission Cache Cleanup, and SIEM/Vault Hardening | v24.0 | 2/2 | Complete | 2026-04-20 |
