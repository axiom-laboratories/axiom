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
- ✅ **v19.0 — Foundry Improvements** — Phases 107–114, 116–118 (shipped 2026-04-05)

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
- ✅ v14.1 First-User Readiness — Phases 66–70 (shipped 2026-04-01)
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

- [x] **Phase 107: Schema Foundation + CRUD Completeness** - DB migrations and missing CRUD operations that unblock all downstream work (completed 2026-04-03)
- [x] **Phase 108: Transitive Dependency Resolution** - Full dep tree resolution, dual-platform mirroring, and resolver service (completed 2026-04-03)
- [x] **Phase 109: APT + apk Mirrors + Compose Profiles** - Linux air-gap mirror backends and the compose profile pattern for all sidecars (completed 2026-04-03)
- [x] **Phase 110: CVE Transitive Scan + Dependency Tree UI** - Extend CVE scanning to full dep tree and ship the interactive tree viewer (completed 2026-04-04)
- [x] **Phase 111: npm + NuGet + OCI Mirrors** - Extended ecosystem mirror backends with compose sidecars (completed 2026-04-04)
- [x] **Phase 112: Conda Mirror + Mirror Admin UI** - Conda backend with ToS warning and unified admin config for all mirror ecosystems (Plans 01, 02, 02b completed 2026-04-04)
- [x] **Phase 113: Script Analyzer** - Auto-detect package dependencies from pasted scripts via AST/regex analysis (completed 2026-04-04)
- [x] **Phase 114: Curated Bundles + Starter Templates** - Pre-built package bundles and seeded golden-image templates for non-developers (in progress)
- ~~Phase 115: Operator UX Polish~~ — **deferred to v20.0** (UX polish, not blocking air-gap)
- [x] **Phase 119: v19.0 Traceability Closure** — Check unchecked requirement boxes, add SUMMARY frontmatter, create VERIFICATION.md for all phases (completed 2026-04-05)

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
**Plans**: 3/3 plans

Plans:
- [x] 107-01-PLAN.md — Schema migration + new tables + backend CRUD endpoints (completed 2026-04-01)
- [x] 107-02-PLAN.md — Blueprint edit mode + dep confirmation dialog (completed 2026-04-02)
- [x] 107-03-PLAN.md — Tool recipe edit UI + Approved OS tab (completed 2026-04-03)

### Phase 108: Transitive Dependency Resolution
**Goal**: The mirror pipeline downloads complete dependency trees so air-gapped STRICT builds succeed without internet access
**Depends on**: Phase 107 (ingredient_dependencies table, ecosystem column)
**Requirements**: DEP-01
**Success Criteria** (what must be TRUE):
  1. When an operator approves a package (e.g. Flask), the mirror service resolves and downloads all transitive dependencies (Werkzeug, Jinja2, MarkupSafe, itsdangerous, click) — not just the top-level package
  2. PyPI packages are mirrored to separate paths for manylinux and musllinux wheels so Alpine and Debian images both build correctly in air-gap
  3. A Foundry build using STRICT enforcement mode completes successfully with no internet access for any blueprint whose packages have been mirrored
  4. Circular dependency chains are detected and handled gracefully (timeout + visited-set guard) without hanging the resolution worker
**Plans**: 3 plans (2 execution + 1 gap closure)

Plans:
- [x] 108-01-PLAN.md — Resolver service with pip-compile, transitive edge creation, auto-discovered deduplication (completed 2026-04-03)
- [x] 108-02-PLAN.md — Dual-platform mirror backend, full tree validation, devpi removal (completed 2026-04-03)

### Phase 109: APT + apk Mirrors + Compose Profiles
**Goal**: Operators can mirror APT and Alpine packages for air-gapped Debian and Alpine image builds, with all mirror sidecars behind a compose profile
**Depends on**: Phase 108 (throwaway container pattern, ecosystem dispatch)
**Requirements**: MIRR-01, MIRR-02, MIRR-07
**Success Criteria** (what must be TRUE):
  1. Operator can approve a Debian package and it is mirrored via the APT backend (completing the existing stub in mirror_service.py)
  2. Operator can approve an Alpine package and it is mirrored via the apk backend with an nginx sidecar serving the repository
  3. All mirror sidecars (including existing PyPI) are defined as compose services behind `--profile mirrors` — not started by default, only when the operator opts in
  4. A Foundry build for a Debian-based or Alpine-based image with APT/apk packages succeeds in air-gap using the local mirrors
**Plans**: 4 plans

Plans:
- [x] 109-01-PLAN.md — APT mirror backend (_mirror_apt), apk backend (_mirror_apk), health check infrastructure, unit tests (completed 2026-04-03)
- [x] 109-02-PLAN.md — Compose CE/EE separation (compose.ee.yaml), Caddy multi-path routing, .env.example (completed 2026-04-03)
- [x] 109-03-PLAN.md — Foundry Alpine integration (repositories injection), MirrorHealthBanner dashboard component, integration tests (completed 2026-04-03)
- [x] 109-04-PLAN.md — Verification checkpoint (end-to-end testing of mirrors, compose, Foundry, dashboard) (completed 2026-04-03)

**Wave Structure:**
- Wave 1: Mirror backends (APT + apk methods, health check) — independent
- Wave 2: Compose separation + Caddy routing — depends on Wave 1 for health check availability
- Wave 3: Foundry integration + dashboard — depends on Waves 1-2 for mirror infrastructure
- Wave 4: Verification checkpoint — blocks before marking phase complete

### Phase 110: CVE Transitive Scan + Dependency Tree UI
**Goal**: Operators can see the full dependency tree for any package and CVE scans cover transitive dependencies — not just top-level packages
**Depends on**: Phase 108 (ingredient_dependencies rows must exist)
**Requirements**: DEP-02, DEP-03, DEP-04
**Success Criteria** (what must be TRUE):
  1. Operator can click a tree icon on any ingredient and see an interactive visual tree showing the full provenance chain (e.g. MarkupSafe <- Jinja2 <- Flask)
  2. CVE scanning includes all transitive dependencies — a vulnerable transitive dep (e.g. CVE in MarkupSafe pulled by Jinja2 pulled by Flask) is flagged before build
  3. Operator can trigger dependency discovery for any ingredient via a button that returns the full tree with a one-click "Approve All" action to bulk-approve the entire chain
**Plans**: 2 plans (2 complete)

Plans:
- [x] 110-01-PLAN.md — Backend: CVE scan extension to transitive deps + tree API + discover endpoint (completed 2026-04-03)
- [x] 110-02-PLAN.md — Frontend: Dependency tree viewer component + CVE badges + discover button integration (completed 2026-04-04)

**Wave Structure:**
- Wave 1: Backend (CVE scan extension, tree API, discover endpoint, comprehensive tests) — COMPLETE
- Wave 2: Frontend (tree modal component, CVE badges, discover button integration in Smelter Registry) — COMPLETE

### Phase 111: npm + NuGet + OCI Mirrors
**Goal**: Operators can mirror npm, NuGet, and OCI (Docker) packages for air-gapped environments using proven Docker-native sidecar services
**Depends on**: Phase 109 (compose profile pattern established)
**Requirements**: MIRR-03, MIRR-04, MIRR-05
**Success Criteria** (what must be TRUE):
  1. Operator can approve an npm package and it is mirrored via Verdaccio pull-through proxy with a compose sidecar
  2. Operator can approve a NuGet package and it is mirrored via BaGetter with a compose sidecar
  3. OCI base images used by Foundry are cached through a registry:2 pull-through proxy so image pulls work in air-gap
  4. All three new sidecars use the `--profile mirrors` compose pattern established in Phase 109
**Plans**: 3 plans (3 complete)

Plans:
- [x] 111-01-PLAN.md — npm mirror backend + Verdaccio sidecar + Smelter integration (completed 2026-04-04)
- [x] 111-02-PLAN.md — NuGet mirror backend + BaGetter sidecar + OCI pull-through config (completed 2026-04-04)
- [x] 111-03-PLAN.md — Gap closure: ecosystem dispatch + integration tests (completed 2026-04-04)

### Phase 112: Conda Mirror + Mirror Admin UI
**Goal**: Operators can mirror Conda packages with proper licensing awareness, and configure all mirror URLs from the Admin dashboard
**Depends on**: Phase 111 (all mirror backends exist for the admin UI to configure)
**Requirements**: MIRR-06, MIRR-08, MIRR-09
**Success Criteria** (what must be TRUE):
  1. Operator can approve a Conda package and it is mirrored; selecting the Anaconda `defaults` channel shows a blocking ToS warning recommending conda-forge
  2. Admin mirror configuration UI includes URL fields for all ecosystems (PyPI, APT, apk, OCI, npm, Conda, NuGet) — not just PyPI and APT
  3. Operator can enable/disable mirror services from the Admin dashboard with one-click provisioning (start/stop compose services via Docker socket)
**Plans**: 3/3 plans

Plans:
- [x] 112-01-PLAN.md — Conda mirror backend + .condarc injection + Caddyfile routing (MIRR-06 backend) (completed 2026-04-04)
- [x] 112-02-PLAN.md — Mirror admin UI with 8 ecosystem cards (MIRR-08) (completed 2026-04-04)
- [x] 112-02b-PLAN.md — Docker provisioning + ToS backend (MIRR-09, MIRR-06 backend) (completed 2026-04-04)
- [x] 112-03-PLAN.md — Conda ToS blocking modal in Smelter UI (MIRR-06 UI) (completed 2026-04-04)

**Wave Structure**:
- Wave 1: Conda mirror backend (mirror_service._mirror_conda, .condarc injection, Caddyfile)
- Wave 2: Admin UI (mirror cards, health badges) + provisioning service (depends on Wave 1)
- Wave 3: Smelter ToS modal UI (depends on Wave 2 for ToS acknowledgment endpoint)

### Phase 113: Script Analyzer
**Goal**: Operators can paste a script and get automatic package suggestions without knowing package names or ecosystems
**Depends on**: Phase 107 (queries approved_ingredients table with ecosystem column)
**Requirements**: UX-01
**Success Criteria** (what must be TRUE):
  1. Operator can paste a Python script and see auto-detected import-to-package suggestions (e.g. `import cv2` suggests `opencv-python`) with stdlib modules excluded
  2. Operator can paste a Bash script and see `apt-get install` / `yum install` package suggestions extracted via regex
  3. Operator can paste a PowerShell script and see `Import-Module` suggestions mapped to PSGallery packages
  4. Suggested packages are cross-referenced against already-approved ingredients so the operator sees what is new vs. already in the registry
**Plans**: 2/2 plans

Plans:
- [x] 113-01-PLAN.md — Backend analyzer service + endpoints + approval queue (Wave 1)
- [x] 113-02-PLAN.md — Frontend ScriptAnalyzerPanel + ApprovalQueuePanel UI (Wave 2)

### Phase 114: Curated Bundles + Starter Templates
**Goal**: Non-developer operators can build node images by picking from pre-built bundles and starter templates instead of manually selecting individual packages
**Depends on**: Phase 108 (transitive deps resolved when bundles are applied), Phase 107 (curated_bundles tables)
**Requirements**: UX-02, UX-03
**Success Criteria** (what must be TRUE):
  1. Operator can browse curated bundles (Data Science, Web/API, Network Ops, File Processing, Windows Automation) and one-click add a bundle to a blueprint — bulk-approving all packages with transitive deps
  2. Pre-built starter templates (Python General, Data Science, Network Tools, Windows Automation) are seeded on first EE startup and visible in a Template Gallery
  3. A non-technical operator can go from Template Gallery pick to a built node image without using the full wizard or knowing any package names
**Plans**: 3/3 plans

Plans:
- [x] 114-01-PLAN.md — Backend infrastructure: bundles CRUD endpoints + apply logic + tests (Wave 1) — completed 2026-04-05
- [x] 114-02-PLAN.md — Admin UI + starter seeding: BundleAdminPanel + Templates.tsx integration + 5 starters (Wave 2) — planned 2026-04-05
- [x] 114-03-PLAN.md — Operator gallery + build flow: UseTemplateDialog + BuildConfirmationDialog + clone/build endpoints (Wave 3) — planned 2026-04-05

**Wave Structure:**
- Wave 1: Backend (bundles endpoints, ApplyBundleResult, SmelterService integration, 10 tests) — independent
- Wave 2: Admin UI (BundleAdminPanel component, Templates.tsx Bundles tab, starter seeding, 5 starters, migration_v48.sql) — depends on Wave 1
- Wave 3: Operator gallery (UseTemplateDialog, BuildConfirmationDialog, clone/build endpoints with auto-approval) — depends on Waves 1-2

### ~~Phase 115: Operator UX Polish~~ — DEFERRED to v20.0
**Reason:** UX polish (simplified labels, search-by-description, simplified mode toggle, usage stats) is quality-of-life — not blocking air-gap functionality.
**Requirements deferred:** UX-04, UX-05, UX-06, UX-07

### Phase 119: v19.0 Traceability Closure
**Goal:** Close all documentation/traceability gaps identified by the v19.0 milestone audit — check unchecked requirement boxes, add missing SUMMARY frontmatter, and create VERIFICATION.md for all phases
**Depends on**: Phase 118 (all implementation phases complete)
**Requirements**: MIRR-03, MIRR-04, MIRR-05, MIRR-09, UX-01, UX-02, UX-03, DEP-01, DEP-02, DEP-03, DEP-04, MIRR-08
**Gap Closure:** Closes all gaps from v19.0-MILESTONE-AUDIT.md
**Success Criteria** (what must be TRUE):
  1. All 7 unsatisfied requirement checkboxes in REQUIREMENTS.md are checked (MIRR-03/04/05, MIRR-09, UX-01/02/03)
  2. All 12 gap requirements have `requirements_completed` entries in their phase SUMMARY.md frontmatter
  3. All 11 v19.0 phases have a VERIFICATION.md file documenting code evidence
  4. REQUIREMENTS.md traceability table shows all 17 in-scope requirements as Complete
  5. Re-audit passes with 0 gaps

Plans: 2/2 plans (COMPLETE)

Plans:
- [x] 119-01-PLAN.md — Wave 1: Verify 7 unchecked requirements + update REQUIREMENTS.md checkboxes + add SUMMARY.md frontmatter (completed 2026-04-05)
- [x] 119-02-PLAN.md — Wave 2: Create VERIFICATION.md for all 11 v19.0 phases (completed 2026-04-05)

## Progress

**Execution Order:**
Phases execute in numeric order: 107 → 108 → 109 → 110 → 111 → 112 → 113 → 114 (Phase 115 deferred to v20.0)

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 107. Schema Foundation + CRUD Completeness | 3/3 | Complete | 2026-04-03 |
| 108. Transitive Dependency Resolution | 2/2 | Complete | 2026-04-03 |
| 109. APT + apk Mirrors + Compose Profiles | 4/4 | Complete | 2026-04-03 |
| 110. CVE Transitive Scan + Dependency Tree UI | 2/2 | Complete | 2026-04-04 |
| 111. npm + NuGet + OCI Mirrors | 3/3 | Complete | 2026-04-04 |
| 112. Conda Mirror + Mirror Admin UI | 4/4 | Complete    | 2026-04-04 |
| 113. Script Analyzer | 2/2 | Complete    | 2026-04-04 |
| 114. Curated Bundles + Starter Templates | 1/3 | Complete    | 2026-04-05 |
| 116. Fix smelter DB migration + EE licence hot-reload | 2/2 | Complete | 2026-04-04 |
| 117. Light/dark mode toggle | 5/5 | Complete | 2026-04-04 |
| 118. UI polish and verification | 4/4 | Complete | 2026-04-04 |
| 115. Operator UX Polish | — | Deferred to v20.0 | - |
| 119. v19.0 Traceability Closure | 2/2 | Complete    | 2026-04-05 |

## Archived

- ✅ **v18.0 — First-User Experience & E2E Validation** (Phases 101–106) — shipped 2026-04-01 → `.planning/milestones/v18.0-ROADMAP.md`
- ✅ **v16.1 — PR Merge & Backlog Closure** (Phases 92–95) — shipped 2026-03-30 → `.planning/milestones/v16.1-ROADMAP.md`
- ✅ **v14.3 — Security Hardening + EE Licensing** (Phases 72–76) — shipped 2026-03-27 → `.planning/milestones/v14.3-ROADMAP.md`
- ✅ **v14.2 — Docs on GitHub Pages** (Phase 71) — shipped 2026-03-26 → `.planning/milestones/v14.2-ROADMAP.md`

### Phase 116: Fix smelter DB migration and add EE licence hot-reload

**Goal:** Fix database schema gaps in EE models (especially ApprovedIngredient.mirror_log) and implement EE licence hot-reload for zero-downtime licence updates.

**Requirements**: None specified (maintenance + feature phase)

**Depends on:** Phase 115

**Plans:** 2/2 plans complete

Plans:
- [x] 116-01-PLAN.md — DB migration gap audit + idempotent schema fixes
- [x] 116-02-PLAN.md — Licence reload endpoint + background timer + Admin UI

**Wave Structure:**
- Wave 1: DB migration fixes (independent, unblocks Smelter UI)
- Wave 2: Licence hot-reload (depends on Wave 1 for serial execution)

**Success Criteria:**
- ApprovedIngredient model fully synchronized with DB schema (mirror_log + mirror_path columns)
- All EE models audited for gaps and fixed in migration_v46.sql
- POST /api/admin/licence/reload endpoint allows admin-only licence reload without restart
- Background timer checks licence expiry every 60s and broadcasts status changes via WebSocket
- Admin dashboard shows licence metadata with reload button and grace period warnings
- CE→EE transitions register EE routers dynamically; EE→CE transitions return 402 on expiry
- Audit trail logs all licence reload events

### Phase 117: Implement light mode with a light mode/dark mode toggle, whilst keeping the brand identity

**Goal:** Add a complete light theme to the React dashboard with a user-facing toggle in the sidebar footer, preserving the existing dark theme as the default and maintaining brand identity across both modes.

**Depends on:** Phase 116

**Requirements**: None specified

**Plans:** 5/5 plans complete

Plans:
- [x] 117-00-PLAN.md — Test infrastructure foundation (Wave 0 TDD RED phase) — completed 2026-04-02
- [x] 117-01-PLAN.md — CSS variables foundation + FOWT prevention (Wave 1) — completed 2026-04-02
- [x] 117-02-PLAN.md — Theme provider hook + toggle component (Wave 2) — completed 2026-04-02
- [x] 117-03-PLAN.md — Component styling migration to theme-aware classes (Wave 3) — completed 2026-04-03
- [x] 117-04-PLAN.md — Verification checkpoint for light/dark mode functionality (Wave 4) — verified 2026-04-04

**Wave Structure:**
- Wave 0: Comprehensive test coverage defining expected behavior (TDD RED phase) — completed 2026-04-02
- Wave 1: CSS variables, FOWT script, Tailwind config (foundational)
- Wave 2: Theme provider, toggle component, component styling updates (parallelizable)
- Wave 3: Visual verification checkpoint (blocks execution until approved)

**Success Criteria:**
- Light mode palette (warm stone colors) renders correctly on all dashboard views
- Dark mode unchanged from existing behavior (no regressions)
- Theme toggle appears in sidebar footer with sun/moon icons and pink slider dot
- Theme persists to localStorage and is restored on page reload
- FOWT prevention prevents theme flash on page load
- All interactive components (charts, modals, toasts, badges) are theme-aware
- Brand identity invariants preserved (pink primary, Fira fonts, focus ring color)


### Phase 118: UI polish and verification

**Goal:** Polish UI consistency across all dashboard views and add permanent Playwright-based verification tests

**Requirements**: None specified (quality/testing phase)

**Depends on:** Phase 117

**Plans:** 4/4 plans complete

Plans:
- [x] 118-01-PLAN.md — CSS variable theming and skeleton component (completed 2026-04-04)
- [x] 118-02-PLAN.md — Visual polish and responsive design (completed 2026-04-04)
- [x] 118-03-PLAN.md — GitHub issue fixes (GH #20, #21, #22) (completed 2026-04-04)
- [x] 118-04-PLAN.md — UI polish verification and Playwright test framework (completed 2026-04-04)

**Wave Structure:**
- Wave 1: CSS + skeleton component
- Wave 2: Visual polish
- Wave 3: Bug fixes
- Wave 4: Verification framework

**Success Criteria:**
- All 9 dashboard views have consistent spacing, responsive design, and theme-aware styling
- Status filter supports comma-separated values
- Dashboard node counts correct and consistent
- Node status indicators display correct colors
- Full-page screenshot comparison tests pass for light/dark themes
