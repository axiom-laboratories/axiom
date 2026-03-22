# Roadmap: Master of Puppets

## Milestones

- ✅ **v1.0–v6.0** — Milestones 1–6 (Production Reliability → Remote Validation) — shipped 2026-03-06/09
- ✅ **v7.0 — Advanced Foundry & Smelter** — Phases 11–15 (shipped 2026-03-16)
- ✅ **v8.0 — mop-push CLI & Job Staging** — Phases 17–19 (shipped 2026-03-15)
- ✅ **v9.0 — Enterprise Documentation** — Phases 20–28 (shipped 2026-03-17)
- ✅ **v10.0 — Axiom Commercial Release** — Phases 29–33 (shipped 2026-03-19)
- ✅ **v11.0 — CE/EE Split Completion** — Phases 34–37 (shipped 2026-03-20)
- 🚧 **v11.1 — Stack Validation** — Phases 38–45 (in progress)

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

### 🚧 v11.1 — Stack Validation (In Progress)

**Milestone Goal:** Adversarial end-to-end validation of the full Axiom CE/EE stack from a clean install — CE/EE split verification, 4 LXC environment-tagged nodes, exhaustive job testing, Foundry/Smelter deep pass, and a gap report feeding v12.0+.

- [x] **Phase 38: Clean Teardown + Fresh CE Install** — Teardown scripts (soft/hard), CE cold-start verification, admin re-seed safety (completed 2026-03-20)
- [x] **Phase 39: EE Test Keypair + Dev Install** — Ed25519 test keypair, editable EE install with patched key, licence lifecycle edge cases (completed 2026-03-20)
- [x] **Phase 40: LXC Node Provisioning** — 4 Incus containers (DEV/TEST/PROD/STAGING), per-node enrollment, env-tag verification, revoke/re-enroll cycle (completed 2026-03-20)
- [x] **Phase 41: CE Validation Pass** — EE stubs return 402, CE table count assertion, basic job dispatch on CE (completed 2026-03-21)
- [x] **Phase 42: EE Validation Pass** — CE+EE combined install, 28-table assertion, licence gating, admin endpoint RBAC (completed 2026-03-21)
- [x] **Phase 43: Job Test Matrix** — 9 job scenarios: fast/slow/memory/concurrent/env-routing/promotion/crash/bad-sig/revoked-definition (completed 2026-03-21)
- [x] **Phase 44: Foundry + Smelter Deep Pass** — Full wizard flow, STRICT/WARNING modes, build failure edge case, air-gap mirror, build dir cleanup (completed 2026-03-22)
- [ ] **Phase 45: Gap Report Synthesis + Critical Fixes** — Living gap report, inline critical patches with regression tests, prioritised v12.0+ backlog

## Phase Details

### Phase 38: Clean Teardown + Fresh CE Install
**Goal**: A known-clean CE stack exists, verified from cold start, with teardown scripts that are safe to run repeatedly
**Depends on**: Nothing (first phase of v11.1)
**Requirements**: INST-01, INST-02, INST-03, INST-04
**Success Criteria** (what must be TRUE):
  1. Soft teardown script stops containers and clears DB data without touching Root CA or node `secrets/` dirs — safe to run between test runs
  2. Hard teardown script removes all named Docker volumes AND all LXC node `secrets/` dirs in a single atomic operation — no defunct CA certs left on nodes
  3. After hard teardown + CE cold start, `docker exec` confirms exactly 13 CE tables exist and `GET /api/features` returns all false
  4. `GET /api/licence` returns `{"edition": "community"}` on CE-only install
  5. Admin re-seed: changing `ADMIN_PASSWORD` env var on a stack where admin already exists does NOT overwrite the DB password
**Plans**: 2 plans
Plans:
- [ ] 38-01-PLAN.md — Teardown scripts (soft + hard)
- [ ] 38-02-PLAN.md — CE install verification script

### Phase 39: EE Test Keypair + Dev Install
**Goal**: A local Ed25519 test keypair is in place and the EE plugin is running with the test public key, enabling all licence lifecycle tests without a Cython rebuild
**Depends on**: Nothing (runs in parallel with Phase 38)
**Requirements**: EEDEV-01, EEDEV-02, EEDEV-03, EEDEV-04, EEDEV-05
**Success Criteria** (what must be TRUE):
  1. Test Ed25519 keypair (public + private) exists in `mop_validation/secrets/` and is NOT the production keypair
  2. `axiom-ee` installs as an editable source package (`pip install -e`) with `_LICENCE_PUBLIC_KEY_BYTES` patched to the test public key — no Cython compilation required
  3. A signed test licence is generated; after injecting `AXIOM_LICENCE_KEY` and restarting, `GET /api/licence` returns correct `customer_id`, `exp`, and `features` values
  4. After injecting an expired test licence and restarting, `GET /api/features` returns all false and `GET /api/licence` shows expired state
  5. When `AXIOM_LICENCE_KEY` is absent entirely, the stack starts without crashing and `GET /api/features` returns all false (CE-degraded mode)
**Plans**: 2 plans
Plans:
- [ ] 39-01-PLAN.md — Ed25519 test keypair generation + axiom-ee editable install with patched key
- [ ] 39-02-PLAN.md — Signed test licence generation + API-level lifecycle verification script

### Phase 40: LXC Node Provisioning
**Goal**: Four environment-tagged LXC nodes are enrolled, heartbeating, and ready for all job and Foundry validation tests
**Depends on**: Phase 38 (stack must be healthy; JOIN_TOKEN endpoint must be live)
**Requirements**: NODE-01, NODE-02, NODE-03, NODE-04, NODE-05
**Success Criteria** (what must be TRUE):
  1. Four Incus containers (`axiom-node-dev`, `axiom-node-test`, `axiom-node-prod`, `axiom-node-staging`) are running with correct `OPERATOR_TAGS=env:DEV/TEST/PROD/STAGING` respectively
  2. Each node received a unique per-node JOIN_TOKEN (not shared); all 4 complete mTLS enrollment without token collision errors
  3. `GET /api/nodes` shows 4 nodes with correct `env_tag` values and `HEALTHY` status
  4. `AGENT_URL` on each LXC node is set to the `incusbr0` bridge host IP (discovered dynamically, not hardcoded as `172.17.0.1`)
  5. Revoking a node causes it to receive HTTP 403 on `/work/pull`; re-enrolling with a fresh token restores `HEALTHY` heartbeat status
**Plans**: 2 plans
Plans:
- [ ] 40-01-PLAN.md — LXC compose template + teardown update + provision_lxc_nodes.py
- [ ] 40-02-PLAN.md — verify_lxc_nodes.py (NODE-01 through NODE-05)

### Phase 41: CE Validation Pass
**Goal**: The CE install is confirmed clean — correct stub behaviour, correct table isolation, and a verified job execution baseline — before EE is layered on
**Depends on**: Phase 38 (clean CE stack), Phase 40 (enrolled nodes)
**Requirements**: CEV-01, CEV-02, CEV-03
**Success Criteria** (what must be TRUE):
  1. All 7 EE routes return HTTP 402 (not 404, not 500) on a CE-only install with 4 nodes active
  2. After hard teardown + CE reinstall, `information_schema` query confirms exactly 13 tables — zero EE table leakage
  3. A signed job script submitted to a DEV-tagged node executes successfully, stdout is captured, and the execution record is visible in the dashboard history
**Plans**: 3 plans
Plans:
- [ ] 41-01-PLAN.md — verify_ce_stubs.py (CEV-01) + verify_ce_tables.py (CEV-02)
- [ ] 41-02-PLAN.md — verify_ce_job.py: end-to-end signed job execution (CEV-03)
- [ ] 41-03-PLAN.md — Gap closure: run CEV-01 and CEV-02 scripts against CE-only stack, capture passing evidence

### Phase 42: EE Validation Pass
**Goal**: The CE+EE combined install is confirmed working — all feature flags true, correct table count, EE routes responding, and licence lifecycle edge cases verified
**Depends on**: Phase 39 (test keypair), Phase 41 (clean CE baseline)
**Requirements**: EEV-01, EEV-02, EEV-03
**Success Criteria** (what must be TRUE):
  1. After CE+EE install with valid test licence, `GET /api/features` returns all true and `GET /api/licence` returns `{"edition": "enterprise"}` — this assertion is the gate for all subsequent EE tests
  2. Database contains exactly 28 tables (13 CE + 15 EE); EE routes return real responses, not 402
  3. Licence gating is startup-only: swapping to an expired licence at runtime leaves features true until restart, then false after restart
  4. `GET /api/licence` returns full licence detail for admin; operator and viewer roles receive HTTP 403
**Plans**: 2 plans
Plans:
- [ ] 42-01-PLAN.md — Backend patch: GET /api/licence admin-only + EE image rebuild
- [ ] 42-02-PLAN.md — Write and execute verify_ee_pass.py (EEV-01, EEV-02, EEV-03)

### Phase 43: Job Test Matrix
**Goal**: All 9 job scenarios — covering normal execution, edge cases, and failure modes — are exercised against the full EE stack with 4 LXC nodes
**Depends on**: Phase 42 (confirmed EE stack), Phase 40 (4 enrolled nodes)
**Requirements**: JOB-01, JOB-02, JOB-03, JOB-04, JOB-05, JOB-06, JOB-07, JOB-08, JOB-09
**Success Criteria** (what must be TRUE):
  1. Fast job (< 5s) and slow job (90s sleep) both complete with stdout captured in execution history; slow job shows node as live in heartbeat during execution
  2. Five concurrent jobs submitted to the same node all complete — no duplicate execution of the same job GUID on two nodes
  3. Env-tag routing is strictly enforced: a DEV-tagged job never executes on the PROD node; a cross-tag submission where no eligible node exists returns an appropriate response from the orchestrator
  4. A job configured with `sys.exit(1)` produces `FAILED` status, triggers retry up to `max_retries`, and all attempts appear in execution history with correct `attempt_number` values
  5. A job submitted with a bad Ed25519 signature is rejected by the node before execution; no execution record is created for the actual script run; a revoked job definition is blocked at the orchestrator and never reaches any node
**Plans**: 7 plans (5 original + 2 gap-closure)
Plans:
- [ ] 43-01-PLAN.md — Backend fixes: REVOKED dispatch guard + no-eligible-node 422 (JOB-05, JOB-09 enablers)
- [ ] 43-02-PLAN.md — Basic execution scripts: verify_job_01_fast.py, verify_job_02_slow.py, verify_job_03_memory.py (JOB-01, JOB-02, JOB-03)
- [ ] 43-03-PLAN.md — Routing scripts: verify_job_04_concurrent.py, verify_job_05_env_routing.py, verify_job_06_promotion.py (JOB-04, JOB-05, JOB-06)
- [ ] 43-04-PLAN.md — Failure scripts: verify_job_07_retry_crash.py, verify_job_08_bad_sig.py, verify_job_09_revoked.py (JOB-07, JOB-08, JOB-09)
- [ ] 43-05-PLAN.md — Runner: run_job_matrix.py + execute full matrix (all JOB-*)
- [ ] 43-06-PLAN.md — Gap closure: fix HTTP 500 wrapping bug in POST /jobs route (JOB-05)
- [ ] 43-07-PLAN.md — Gap closure: provision DEV node + signing key + re-run matrix for genuine PASS evidence (all JOB-*)

### Phase 44: Foundry + Smelter Deep Pass
**Goal**: Foundry and Smelter are verified end-to-end — wizard flow, CVE enforcement, build failure handling, air-gap mirror, and known gap documentation
**Depends on**: Phase 42 (EE stack confirmed)
**Requirements**: FOUNDRY-01, FOUNDRY-02, FOUNDRY-03, FOUNDRY-04, FOUNDRY-05, FOUNDRY-06
**Success Criteria** (what must be TRUE):
  1. Full wizard flow completes: runtime blueprint → network blueprint → Foundry build → image tag visible in Docker → node deployed from Foundry-built image and enrolled
  2. Smelter STRICT mode blocks a blueprint containing a known-CVE ingredient (`cryptography<40.0.0`) from being used in a build; the API returns a non-200 response with a clear error
  3. A build triggered with a bad base image tag returns HTTP 500 with error detail — not a silent 200
  4. Air-gap mirror test: with outbound internet blocked via `iptables` on the build container, a blueprint using the local PyPI mirror installs its ingredient successfully from the mirror; `curl https://pypi.org/` fails from inside the container during the test, confirming isolation
  5. Smelter WARNING mode: a moderate-risk ingredient proceeds through a build but the audit log records the warning; build dir cleanup result (pass or fail) is documented as a finding for MIN-07
**Plans**: 5 plans
Plans:
- [ ] 44-01-PLAN.md — STRICT CVE block (FOUNDRY-02) + bad base image failure (FOUNDRY-03)
- [ ] 44-02-PLAN.md — Build dir gap documentation (FOUNDRY-04) + WARNING mode (FOUNDRY-06)
- [ ] 44-03-PLAN.md — Full wizard flow API + Playwright (FOUNDRY-01)
- [ ] 44-04-PLAN.md — Air-gap mirror with iptables isolation (FOUNDRY-05)
- [ ] 44-05-PLAN.md — Runner: run_foundry_matrix.py + execute full matrix (all FOUNDRY-*)

### Phase 45: Gap Report Synthesis + Critical Fixes
**Goal**: All findings from Phases 38–44 are synthesised into a prioritised gap report; critical bugs are patched with regression tests; the v12.0+ backlog is seeded
**Depends on**: Phase 43 (job matrix complete), Phase 44 (Foundry pass complete)
**Requirements**: GAP-01, GAP-02, GAP-03
**Success Criteria** (what must be TRUE):
  1. `mop_validation/reports/v11.1-gap-report.md` exists and contains every finding from all phases, each with severity (critical/major/minor), area, reproduction steps, and v12.0+ fix candidate
  2. All findings rated critical are patched inline during this phase; each patch has an accompanying regression test that fails before the fix and passes after
  3. The final gap report includes a prioritised backlog section ready to seed v12.0+ milestone planning, with deferred items cross-referenced to existing known gaps (MIN-06, MIN-07, MIN-08, WARN-08)
**Plans**: 2 plans
Plans:
- [ ] 45-01-PLAN.md — v11.1 gap report synthesis (GAP-01, GAP-03)
- [ ] 45-02-PLAN.md — MIN-07 regression test + verify_foundry_04 assertion inversion (GAP-02)

## Progress

**Execution Order:**
38 → (39 in parallel with 38) → 40 → 41 → 42 → (43 and 44 in parallel) → 45

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|----------------|--------|-----------|
| 11. Compatibility Engine | v7.0 | 6/6 | Complete | 2026-03-11 |
| 12. Smelter Registry | v7.0 | 10/10 | Complete | 2026-03-15 |
| 13. Package Management & Custom Repos | v7.0 | 8/8 | Complete | 2026-03-15 |
| 14. Foundry Wizard UI | v7.0 | 5/5 | Complete | 2026-03-16 |
| 15. Smelt-Check, BOM & Lifecycle | v7.0 | 5/5 | Complete | 2026-03-16 |
| 17. Backend — OAuth Device Flow & Job Staging | v8.0 | 5/5 | Complete | 2026-03-12 |
| 18. mop-push CLI | v8.0 | 4/4 | Complete | 2026-03-12 |
| 19. Dashboard Staging View & Governance Doc | v8.0 | 5/5 | Complete | 2026-03-15 |
| 20. Container Infrastructure & Routing | v9.0 | 2/2 | Complete | 2026-03-16 |
| 21. API Reference + Dashboard Integration | v9.0 | 2/2 | Complete | 2026-03-16 |
| 22. Developer Documentation | v9.0 | 3/3 | Complete | 2026-03-17 |
| 23. Getting Started & Core Feature Guides | v9.0 | 4/4 | Complete | 2026-03-17 |
| 24. Extended Feature Guides & Security | v9.0 | 5/5 | Complete | 2026-03-17 |
| 25. Runbooks & Troubleshooting | v9.0 | 4/4 | Complete | 2026-03-17 |
| 26. Axiom Branding & Community Foundation | v9.0 | 3/3 | Complete | 2026-03-17 |
| 27. CI/CD, Packaging & Distribution | v9.0 | 3/3 | Complete | 2026-03-17 |
| 28. Infrastructure Gap Closure | v9.0 | 1/1 | Complete | 2026-03-17 |
| 29. Backend Completeness — Output Capture + Retry Wiring | v10.0 | 3/3 | Complete | 2026-03-18 |
| 30. Runtime Attestation | v10.0 | 3/3 | Complete | 2026-03-18 |
| 31. Environment Tags + CI/CD Dispatch | v10.0 | 4/4 | Complete | 2026-03-18 |
| 32. Dashboard UI — Execution History, Retry State, Env Tags | v10.0 | 7/7 | Complete | 2026-03-19 |
| 33. Licence Compliance + Release Infrastructure | v10.0 | 4/4 | Complete | 2026-03-18 |
| 34. CE Baseline Fixes | v11.0 | 4/4 | Complete | 2026-03-19 |
| 35. Private EE Repo + Plugin Wiring | v11.0 | 5/5 | Complete | 2026-03-20 |
| 36. Cython .so Build Pipeline | v11.0 | 3/3 | Complete | 2026-03-20 |
| 37. Licence Validation + Docs + Docker Hub | v11.0 | 3/3 | Complete | 2026-03-20 |
| 38. Clean Teardown + Fresh CE Install | 2/2 | Complete    | 2026-03-20 | - |
| 39. EE Test Keypair + Dev Install | 2/2 | Complete    | 2026-03-20 | - |
| 40. LXC Node Provisioning | 3/3 | Complete    | 2026-03-21 | - |
| 41. CE Validation Pass | 3/3 | Complete    | 2026-03-21 | - |
| 42. EE Validation Pass | 2/2 | Complete    | 2026-03-21 | - |
| 43. Job Test Matrix | 8/8 | Complete    | 2026-03-21 | - |
| 44. Foundry + Smelter Deep Pass | 5/5 | Complete    | 2026-03-22 | - |
| 45. Gap Report Synthesis + Critical Fixes | 1/2 | In Progress|  | - |

---

## Archived

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
