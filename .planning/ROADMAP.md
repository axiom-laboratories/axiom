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
- 🚧 **v19.0 — Foundry Improvements** — Phases 107–115 (in progress)

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
<summary>✅ v9.0–v18.0 (Phases 20–106) — SHIPPED</summary>

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

</details>

### 🚧 v19.0 — Foundry Improvements (In Progress)

**Milestone Goal:** Make the Foundry/Smelter pipeline production-grade for air-gapped deployments — transitive dependency resolution, full CRUD on all Foundry entities, multi-ecosystem mirror support, and operator-friendly UX for non-developers.

- [ ] **Phase 107: Schema Foundation + CRUD Completeness** - DB migrations and missing CRUD operations that unblock all downstream work
- [ ] **Phase 108: Transitive Dependency Resolution** - Full dep tree resolution, dual-platform mirroring, and resolver service
- [ ] **Phase 109: APT + apk Mirrors + Compose Profiles** - Linux air-gap mirror backends and the compose profile pattern for all sidecars
- [ ] **Phase 110: CVE Transitive Scan + Dependency Tree UI** - Extend CVE scanning to full dep tree and ship the interactive tree viewer
- [ ] **Phase 111: npm + NuGet + OCI Mirrors** - Extended ecosystem mirror backends with compose sidecars
- [ ] **Phase 112: Conda Mirror + Mirror Admin UI** - Conda backend with ToS warning and unified admin config for all mirror ecosystems
- [ ] **Phase 113: Script Analyzer** - Auto-detect package dependencies from pasted scripts via AST/regex analysis
- [ ] **Phase 114: Curated Bundles + Starter Templates** - Pre-built package bundles and seeded golden-image templates for non-developers
- [ ] **Phase 115: Operator UX Polish** - Simplified naming, package search, template catalog, and role-based simplified view

## Phase Details

### Phase 107: Schema Foundation + CRUD Completeness
**Goal**: Operators can fully manage all Foundry entities (blueprints, tools, approved OS) through the dashboard, with the DB schema ready for all v19.0 features
**Depends on**: Nothing (first phase of v19.0)
**Requirements**: CRUD-01, CRUD-02, CRUD-03, CRUD-04, MIRR-10
**Success Criteria** (what must be TRUE):
  1. Operator can open an existing blueprint in the wizard, edit fields, save, and see the updated definition — with a 409 error if another user edited it concurrently
  2. Operator can click Edit on a tool recipe row, modify injection_recipe/validation_cmd/runtime_dependencies, and save via the existing PATCH endpoint
  3. Admin can list, add, edit, and remove Approved OS entries from a dedicated section without using the API directly
  4. Operator sees a confirmation dialog listing all runtime tool dependencies before a blueprint build commits
  5. The ingredient model has an explicit ecosystem enum column (PYPI, APT, APK, OCI, NPM, CONDA, NUGET) and all new tables (ingredient_dependencies, curated_bundles, curated_bundle_items) exist in the schema
**Plans**: 3 plans

Plans:
- [ ] 107-01-PLAN.md — Schema migration + new tables + backend CRUD endpoints
- [ ] 107-02-PLAN.md — Blueprint edit mode + dep confirmation dialog
- [ ] 107-03-PLAN.md — Tool recipe edit UI + Approved OS tab

### Phase 108: Transitive Dependency Resolution
**Goal**: The mirror pipeline downloads complete dependency trees so air-gapped STRICT builds succeed without internet access
**Depends on**: Phase 107 (ingredient_dependencies table, ecosystem column)
**Requirements**: DEP-01
**Success Criteria** (what must be TRUE):
  1. When an operator approves a package (e.g. Flask), the mirror service resolves and downloads all transitive dependencies (Werkzeug, Jinja2, MarkupSafe, itsdangerous, click) — not just the top-level package
  2. PyPI packages are mirrored to separate paths for manylinux and musllinux wheels so Alpine and Debian images both build correctly in air-gap
  3. A Foundry build using STRICT enforcement mode completes successfully with no internet access for any blueprint whose packages have been mirrored
  4. Circular dependency chains are detected and handled gracefully (timeout + visited-set guard) without hanging the resolution worker
**Plans**: TBD

Plans:
- [ ] 108-01: Resolver service and pip-compile pipeline
- [ ] 108-02: Dual-platform mirror layout and smoke test

### Phase 109: APT + apk Mirrors + Compose Profiles
**Goal**: Operators can mirror APT and Alpine packages for air-gapped Debian and Alpine image builds, with all mirror sidecars behind a compose profile
**Depends on**: Phase 108 (throwaway container pattern, ecosystem dispatch)
**Requirements**: MIRR-01, MIRR-02, MIRR-07
**Success Criteria** (what must be TRUE):
  1. Operator can approve a Debian package and it is mirrored via the APT backend (completing the existing stub in mirror_service.py)
  2. Operator can approve an Alpine package and it is mirrored via the apk backend with an nginx sidecar serving the repository
  3. All mirror sidecars (including existing PyPI) are defined as compose services behind `--profile mirrors` — not started by default, only when the operator opts in
  4. A Foundry build for a Debian-based or Alpine-based image with APT/apk packages succeeds in air-gap using the local mirrors
**Plans**: TBD

Plans:
- [ ] 109-01: APT mirror backend + apk mirror backend + nginx sidecar
- [ ] 109-02: Compose profile separation for all mirror services

### Phase 110: CVE Transitive Scan + Dependency Tree UI
**Goal**: Operators can see the full dependency tree for any package and CVE scans cover transitive dependencies — not just top-level packages
**Depends on**: Phase 108 (ingredient_dependencies rows must exist)
**Requirements**: DEP-02, DEP-03, DEP-04
**Success Criteria** (what must be TRUE):
  1. Operator can click a tree icon on any ingredient and see an interactive visual tree showing the full provenance chain (e.g. MarkupSafe <- Jinja2 <- Flask)
  2. CVE scanning includes all transitive dependencies — a vulnerable transitive dep (e.g. CVE in MarkupSafe pulled by Jinja2 pulled by Flask) is flagged before build
  3. Operator can trigger dependency discovery for any ingredient via a button that returns the full tree with a one-click "Approve All" action to bulk-approve the entire chain
**Plans**: TBD

Plans:
- [ ] 110-01: CVE scan extension to transitive deps
- [ ] 110-02: Dependency tree viewer + discovery endpoint with Approve All

### Phase 111: npm + NuGet + OCI Mirrors
**Goal**: Operators can mirror npm, NuGet, and OCI (Docker) packages for air-gapped environments using proven Docker-native sidecar services
**Depends on**: Phase 109 (compose profile pattern established)
**Requirements**: MIRR-03, MIRR-04, MIRR-05
**Success Criteria** (what must be TRUE):
  1. Operator can approve an npm package and it is mirrored via Verdaccio pull-through proxy with a compose sidecar
  2. Operator can approve a NuGet package and it is mirrored via BaGetter with a compose sidecar
  3. OCI base images used by Foundry are cached through a registry:2 pull-through proxy so image pulls work in air-gap
  4. All three new sidecars use the `--profile mirrors` compose pattern established in Phase 109
**Plans**: TBD

Plans:
- [ ] 111-01: npm mirror backend + Verdaccio sidecar
- [ ] 111-02: NuGet mirror backend + BaGetter sidecar + OCI pull-through config

### Phase 112: Conda Mirror + Mirror Admin UI
**Goal**: Operators can mirror Conda packages with proper licensing awareness, and configure all mirror URLs from the Admin dashboard
**Depends on**: Phase 111 (all mirror backends exist for the admin UI to configure)
**Requirements**: MIRR-06, MIRR-08, MIRR-09
**Success Criteria** (what must be TRUE):
  1. Operator can approve a Conda package and it is mirrored; selecting the Anaconda `defaults` channel shows a blocking ToS warning recommending conda-forge
  2. Admin mirror configuration UI includes URL fields for all ecosystems (PyPI, APT, apk, OCI, npm, Conda, NuGet) — not just PyPI and APT
  3. Operator can enable/disable mirror services from the Admin dashboard with one-click provisioning (start/stop compose services via Docker socket)
**Plans**: TBD

Plans:
- [ ] 112-01: Conda mirror backend with ToS warning
- [ ] 112-02: Mirror admin UI + one-click provisioning

### Phase 113: Script Analyzer
**Goal**: Operators can paste a script and get automatic package suggestions without knowing package names or ecosystems
**Depends on**: Phase 107 (queries approved_ingredients table with ecosystem column)
**Requirements**: UX-01
**Success Criteria** (what must be TRUE):
  1. Operator can paste a Python script and see auto-detected import-to-package suggestions (e.g. `import cv2` suggests `opencv-python`) with stdlib modules excluded
  2. Operator can paste a Bash script and see `apt-get install` / `yum install` package suggestions extracted via regex
  3. Operator can paste a PowerShell script and see `Import-Module` suggestions mapped to PSGallery packages
  4. Suggested packages are cross-referenced against already-approved ingredients so the operator sees what is new vs. already in the registry
**Plans**: TBD

Plans:
- [ ] 113-01: Script analyzer service + endpoint
- [ ] 113-02: Script analyzer UI panel in Foundry

### Phase 114: Curated Bundles + Starter Templates
**Goal**: Non-developer operators can build node images by picking from pre-built bundles and starter templates instead of manually selecting individual packages
**Depends on**: Phase 108 (transitive deps resolved when bundles are applied), Phase 107 (curated_bundles tables)
**Requirements**: UX-02, UX-03
**Success Criteria** (what must be TRUE):
  1. Operator can browse curated bundles (Data Science, Web/API, Network Ops, File Processing, Windows Automation) and one-click add a bundle to a blueprint — bulk-approving all packages with transitive deps
  2. Pre-built starter templates (Python General, Data Science, Network Tools, Windows Automation) are seeded on first EE startup and visible in a Template Gallery
  3. A non-technical operator can go from Template Gallery pick to a built node image without using the full wizard or knowing any package names
**Plans**: TBD

Plans:
- [ ] 114-01: Curated bundles CRUD + seeded data + bundle picker UI
- [ ] 114-02: Starter templates seeding + Template Gallery view

### Phase 115: Operator UX Polish
**Goal**: The Foundry is accessible to service-desk operators through simplified naming, search, usage stats, and a role-based simplified view
**Depends on**: Phase 114 (starter templates and bundles must exist for simplified view to be useful)
**Requirements**: UX-04, UX-05, UX-06, UX-07
**Success Criteria** (what must be TRUE):
  1. All user-facing labels are simplified: Ingredient->Package, Smelter Registry->Package Registry, Capability Matrix/Tool->Add-on Tool, etc. (API field names unchanged)
  2. Operator can search packages by description (e.g. typing "excel" finds openpyxl) — not just exact name match
  3. Operator/viewer users see a simplified Foundry view by default (Template Gallery + Upload Script + My Images) with a toggle to access the full UI; admin always sees full UI
  4. Template catalog shows usage stats (created_by, nodes using it, last_used_at) so proven templates surface first for service desk operators
**Plans**: TBD

Plans:
- [ ] 115-01: Simplified naming + package search
- [ ] 115-02: Template catalog with usage stats + role-based simplified view

## Progress

**Execution Order:**
Phases execute in numeric order: 107 → 108 → 109 → 110 → 111 → 112 → 113 → 114 → 115

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 107. Schema Foundation + CRUD Completeness | 2/3 | In Progress|  |
| 108. Transitive Dependency Resolution | 0/2 | Not started | - |
| 109. APT + apk Mirrors + Compose Profiles | 0/2 | Not started | - |
| 110. CVE Transitive Scan + Dependency Tree UI | 0/2 | Not started | - |
| 111. npm + NuGet + OCI Mirrors | 0/2 | Not started | - |
| 112. Conda Mirror + Mirror Admin UI | 0/2 | Not started | - |
| 113. Script Analyzer | 0/2 | Not started | - |
| 114. Curated Bundles + Starter Templates | 0/2 | Not started | - |
| 115. Operator UX Polish | 0/2 | Not started | - |

## Archived

- ✅ **v18.0 — First-User Experience & E2E Validation** (Phases 101–106) — shipped 2026-04-01 → `.planning/milestones/v18.0-ROADMAP.md`
- ✅ **v16.1 — PR Merge & Backlog Closure** (Phases 92–95) — shipped 2026-03-30 → `.planning/milestones/v16.1-ROADMAP.md`
- ✅ **v14.3 — Security Hardening + EE Licensing** (Phases 72–76) — shipped 2026-03-27 → `.planning/milestones/v14.3-ROADMAP.md`
- ✅ **v14.2 — Docs on GitHub Pages** (Phase 71) — shipped 2026-03-26 → `.planning/milestones/v14.2-ROADMAP.md`

### Phase 116: Fix smelter DB migration and add EE licence hot-reload

**Goal:** [To be planned]
**Requirements**: TBD
**Depends on:** Phase 115
**Plans:** 2/2 plans complete

Plans:
- [x] TBD (run /gsd:plan-phase 116 to break down) (completed 2026-04-02)
