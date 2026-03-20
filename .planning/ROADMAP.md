# Roadmap: Master of Puppets

## Milestones

- ✅ **v1.0–v6.0** — Milestones 1–6 (Production Reliability → Remote Validation) — shipped 2026-03-06/09
- ✅ **v7.0 — Advanced Foundry & Smelter** — Phases 11–15 (shipped 2026-03-16)
- ✅ **v8.0 — mop-push CLI & Job Staging** — Phases 17–19 (shipped 2026-03-15)
- ✅ **v9.0 — Enterprise Documentation** — Phases 20–28 (shipped 2026-03-17)
- ✅ **v10.0 — Axiom Commercial Release** — Phases 29–33 (shipped 2026-03-19)
- 🚧 **v11.0 — CE/EE Split Completion** — Phases 34–37 (in progress)

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

### 🚧 v11.0 — CE/EE Split Completion (In Progress)

**Milestone Goal:** Complete the Axiom open-core split — fix 6 blocking gaps on the OSS/EE branch so CE behaves correctly in isolation, wire the EE plugin system in a private repo, compile EE to `.so` for IP protection, and publish `axiom-ce` to Docker Hub with updated docs and licence validation.

- [x] **Phase 34: CE Baseline Fixes** — Mount stub routers (402 not 404), isolate EE tests, strip NodeConfig EE fields, clean job_service dead refs (completed 2026-03-19)
- [x] **Phase 35: Private EE Repo + Plugin Wiring** — axiom-ee repo, EEPlugin.register(), EE DB tables, corrected absolute imports, entry_points, CE-alone and CE+EE smoke tests, stub wheel (completed 2026-03-19)
- [x] **Phase 36: Cython .so Build Pipeline** — Audit EE source for Cython compat, configure ext_modules, cibuildwheel CI matrix, verify no .py in published wheel, compiled CE+EE smoke test (completed 2026-03-20)
- [ ] **Phase 37: Licence Validation + Docs + Docker Hub** — Ed25519 offline licence key validation in EE plugin, axiom-ce on Docker Hub, MkDocs CE/EE admonitions

## Phase Details

### Phase 34: CE Baseline Fixes
**Goal**: The CE install behaves correctly — all EE paths return 402, the pytest suite passes clean with zero EE-attribute errors, and job dispatch works without dead-field crashes
**Depends on**: Nothing (first phase of v11.0; works on existing feature/axiom-oss-ee-split worktree)
**Requirements**: GAP-01, GAP-02, GAP-03, GAP-04, GAP-05, GAP-06
**Success Criteria** (what must be TRUE):
  1. `curl /api/blueprints` on a CE-only install returns HTTP 402 (not 404) for every EE route
  2. `pytest -m "not ee_only"` passes with zero failures and zero EE-attribute errors in the CE test suite
  3. EE-only test files are skipped automatically when the `ee_only` marker is present — no manual exclusion needed
  4. Job dispatch completes a full cycle (assign → pull → execute → report) without `AttributeError` from stripped `NodeConfig` fields in `job_service.py`
  5. `GET /api/features` returns all feature flags as `false` on a CE-only install
**Plans**: 4 plans
Plans:
- [ ] 34-01-PLAN.md — Fix load_ee_plugins(): stub router mounting + importlib.metadata (GAP-01, GAP-02)
- [ ] 34-02-PLAN.md — EE test isolation + User.role scrub (GAP-03, GAP-04)
- [ ] 34-03-PLAN.md — Strip NodeConfig from models, job_service, node.py (GAP-05, GAP-06)
- [ ] 34-04-PLAN.md — Gap closure: testpaths exclusion + test_sprint3.py skip (GAP-03)

### Phase 35: Private EE Repo + Plugin Wiring
**Goal**: The private `axiom-ee` repo exists with a working `EEPlugin` class that installs into CE via entry_points — CE+EE combined install in Python source form produces a fully functional EE instance
**Depends on**: Phase 34
**Requirements**: EE-01, EE-02, EE-03, EE-04, EE-05, EE-06, EE-07, EE-08
**Success Criteria** (what must be TRUE):
  1. `pip install -e axiom-ee/ && restart` results in `GET /api/features` returning all 8 feature flags as `true`
  2. All EE routes return real responses (not 402) after CE+EE install — `GET /api/blueprints` returns the blueprints list
  3. The DB contains all expected CE + EE tables after combined install — no missing table errors on first EE route request
  4. `python -c "import ee.plugin"` succeeds without importing `agent_service.main` — no circular import
  5. The `axiom-ee` stub wheel is published to PyPI and the package name is reserved
**Plans**: 5 plans
Plans:
- [x] 35-01-PLAN.md — axiom-ee repo scaffold: pyproject.toml, EEBase, EEPlugin skeleton (EE-01, EE-05)
- [x] 35-02-PLAN.md — EE DB models: all 15 tables in ee/{feature}/models.py (EE-03)
- [x] 35-03-PLAN.md — Router migration: 7 routers + services, absolute imports, EEPlugin.register() (EE-02, EE-04)
- [x] 35-04-PLAN.md — CE async wiring: load_ee_plugins async, deps.audit() guard fix (EE-05, EE-06)
- [x] 35-05-PLAN.md — Smoke tests + PyPI stub wheel (EE-06, EE-07, EE-08 partial)

### Phase 36: Cython .so Build Pipeline
**Goal**: The EE codebase compiles to `.so` extension modules via Cython and cibuildwheel, producing a multi-arch wheel with no `.py` source — and the compiled wheel passes the same CE+EE validation as the Python source install
**Depends on**: Phase 35
**Requirements**: BUILD-01, BUILD-02, BUILD-03, BUILD-04, BUILD-05
**Success Criteria** (what must be TRUE):
  1. EE source passes a pre-Cython audit with zero `@dataclass` decorators and no `__init__.py` in `ext_modules`
  2. `cibuildwheel` CI builds wheels for Python 3.11, 3.12, 3.13 on both amd64 and arm64 without errors
  3. `unzip -l axiom_ee-*.whl | grep "\.py$"` returns only `__init__.py` — no other Python source in the published wheel
  4. Installing the compiled wheel in a clean virtualenv and running CE+EE produces the same outcome as the Phase 35 source install — all features true, all routes live, all tables present
**Plans**: 3 plans
Plans:
- [ ] 36-01-PLAN.md — Cython build config: setup.py + pyproject.toml + Makefile (BUILD-01, BUILD-02, BUILD-03)
- [ ] 36-02-PLAN.md — Run cibuildwheel: produce multi-arch wheels + verify no .py source (BUILD-03, BUILD-04)
- [ ] 36-03-PLAN.md — devpi service + Containerfile EE install + compiled wheel smoke test (BUILD-05)

### Phase 37: Licence Validation + Docs + Docker Hub
**Goal**: EE enforces an Ed25519 offline licence key at startup, operators can pull `axiom-ce` from Docker Hub, and the MkDocs docs distinguish CE and EE features with enterprise admonitions
**Depends on**: Phase 36 (licence code must be compiled into the .so; Docker Hub and docs can proceed in parallel after Phase 35)
**Requirements**: DIST-01, DIST-02, DIST-03
**Success Criteria** (what must be TRUE):
  1. Starting EE with an expired `AXIOM_LICENCE_KEY` disables all EE features on the next restart — `GET /api/features` returns all false
  2. Licence validation passes with `iptables -I OUTPUT -j DROP` active — no online call-home required
  3. `docker pull axiom-laboratories/axiom-ce` succeeds and the image starts correctly
  4. Every EE-only feature page in the MkDocs docs site displays an `!!! enterprise` admonition block
**Plans**: 3 plans
Plans:
- [ ] 37-01-PLAN.md — EE plugin licence validation + GET /api/licence endpoint (DIST-01)
- [ ] 37-02-PLAN.md — Dashboard edition badge (useLicence hook + sidebar + Admin panel) (DIST-03)
- [ ] 37-03-PLAN.md — MkDocs enterprise admonitions + licensing.md page (DIST-03)

## Progress

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
| 34. CE Baseline Fixes | 4/4 | Complete    | 2026-03-19 | - |
| 35. Private EE Repo + Plugin Wiring | 5/5 | Complete    | 2026-03-20 | - |
| 36. Cython .so Build Pipeline | 3/3 | Complete    | 2026-03-20 | - |
| 37. Licence Validation + Docs + Docker Hub | v11.0 | 0/TBD | Not started | - |

---

## Archived

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
