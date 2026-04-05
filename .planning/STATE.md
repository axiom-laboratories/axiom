---
gsd_state_version: 1.0
milestone: v19.0
milestone_name: — Foundry Improvements
status: executing
stopped_at: Phase 114 context gathered
last_updated: "2026-04-05T16:19:32.021Z"
last_activity: 2026-04-05 -- Completed 114-01 (curated bundles backend infrastructure with TDD)
progress:
  total_phases: 11
  completed_phases: 10
  total_plans: 35
  completed_plans: 33
  percent: 100
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-04-01)

**Core value:** Jobs run reliably -- on the right node, when scheduled, with their output captured -- without any step in the chain weakening the security model.
**Current focus:** Phase 113 - Script Analyzer

## Current Position

Phase: 114 of 14 (114 - Curated Bundles and Starter Templates)
Plan: 2 of 2 in current phase (114-02 complete - all phase plans done)
Status: phase-complete
Last activity: 2026-04-05 -- Completed 114-02 (admin UI + starter template seeding)

Progress: [████████████████████] 100%

## Performance Metrics

**Velocity:**
- Total plans completed: 25 (this milestone)
- Average duration: 22min
- Total execution time: 9.5 hours

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 107 | 2/3 | 13min | 7min |
| 108 | 2/2 | 75min | 38min |
| 109 | 3/3 | 135min | 45min |
| 110 | 2/2 | 135min | 68min |
| 116 | 2/2 | 80min | 40min |
| 117 | 5/5 | 135min | 27min |
| 118 | 4/4 | 152min | 38min |
| 111 | 3/3 | 95min | 32min |

**Recent Trend:**
- Last 6 plans: 116-01 (45min), 116-02 (35min), 117-00 (15min), 117-01 (11min), 117-02 (8min), 117-03 (135min)
- Trend: 117-03 required intensive refactoring across 14 files (9 view files + layout/hook/toggle/dialog/app)

*Updated after each plan completion*

| Phase | Plan | Duration | Tasks | Files |
|-------|------|----------|-------|-------|
| 107 | 03 | 0min | 2 | 1 |
| 108 | 01 | 30min | 3 | 5 |
| 108 | 02 | 45min | 5 | 6 |
| 109 | 01 | 45min | 4 | 3 |
| 109 | 02 | 1min | 4 | 4 |
| 109 | 03 | 45min | 4 | 6 |
| 110 | 00 | 15min | 5 | 5 |
| 110 | 01 | 120min | 5 | 5 |
| 118 | 01 | 40min | 4 | 15 |
| 118 | 02 | 15min | 3 | 1 |
| 118 | 03 | 17min | 3 | 3 |
| 118 | 04 | 120min | 2 | 3 |
| 111 | 01 | 25min | 4 | 5 |
| 111 | 02 | 45min | 6 | 6 |
| 111 | 03 | 25min | 8 | 4 |
| 112 | 01 | 45min | 6 | 5 |
| 112 | 02 | 20min | 6 | 7 |
| 112 | 02b | 28min | 6 | 10 |
| 112 | 03 | 45min | 4 | 5 |
| 113 | 01 | 60min | 4 | 8 |
| Phase 114 P01 | 60 | 5 tasks | 8 files |

## Accumulated Context

### Roadmap Evolution

- Phase 116 added: Fix smelter DB migration and add EE licence hot-reload
- Phase 117 added: Implement light mode with a light mode/dark mode toggle, whilst keeping the brand identity
- Phase 118 added: UI polish and verification

### Key Decisions

- [v19.0 Roadmap]: DB schema + CRUD completeness combined in Phase 107 -- schema changes unblock everything, CRUD is low complexity and independent
- [v19.0 Roadmap]: Transitive dep resolution (Phase 108) precedes all mirror expansion -- every new mirror backend inherits the correct architecture
- [v19.0 Roadmap]: APT/apk before npm/NuGet/Conda -- dominant Linux air-gap use case first
- [v19.0 Roadmap]: Compose profile separation established in Phase 109, inherited by all subsequent sidecar phases
- [v19.0 Roadmap]: Script Analyzer (Phase 113) is self-contained and deferred until core pipeline is solid
- [v19.0 Roadmap]: Role-based view (UX-06) in Phase 115 depends on Starter Templates (UX-03) and Template catalog (UX-07) existing first

- [107-01]: EE models placed in agent_service/db.py (same Base) rather than separate axiom-ee package, matching existing import paths
- [107-01]: All missing EE DB and Pydantic models added as blocking dependency for CRUD endpoint implementation
- [107-02]: Single saveMutation handles both create (POST) and edit (PATCH) with conditional URL/method rather than separate mutations
- [107-02]: Dep confirmation via pendingPayload state + AlertDialog resubmit pattern (422 intercept -> confirm -> resubmit with confirmed_deps)

- [108-02]: Single /data/packages directory for all platforms — pypiserver's flat layout + pip's platform-aware wheel selection handles variant selection automatically
- [108-02]: Automatic transitive mirroring as background task (asyncio.create_task) so add_ingredient returns immediately; Resolver is awaited (blocks) because dep tree must be resolved before mirroring
- [108-02]: Pure-python detection via platform tag ("py3-none-any") rather than filename parsing — cleaner and more reliable, download succeeds on first check
- [108-02]: Devpi removed entirely; pypiserver-only with less operational overhead
- [108-02]: Tree validation before Docker build, not during — fail-fast pattern with 422 Unprocessable Entity for validation errors

- [109-03]: Alpine version extraction from base_os tag (alpine:3.20 → v3.20) for version-specific repository paths — enables multi-version mirror support
- [109-03]: MirrorHealthBanner dismissal state is client-side session-only (not localStorage) — re-appears on page reload, good UX for persistent reminders
- [109-03]: Health polling defaults to assuming mirrors available (UI shows banner only if explicitly unavailable) — graceful degradation on API failure

- [109-01]: Container-isolated package downloads (debian:12-slim, alpine:3.20) over host package managers for reproducibility and avoiding host system dependencies
- [109-01]: APT index regeneration via dpkg-scanpackages inside container (avoids local dpkg dependency)
- [109-01]: Alpine versioning stored in directory structure (mirror_data/apk/v3.20/main/) to support multi-version mirrors
- [109-01]: Health check polls both PyPI and APT mirrors (both must be reachable) rather than separate checks
- [109-01]: Exponential backoff for health check (5s→10s→60s cap) balances rapid failure detection with steady-state polling

- [117-00]: Structured all theme tests in RED (failing) state per TDD methodology to define expected behavior upfront before implementation
- [117-00]: Theme infrastructure tests organized into unit (useTheme hook), component (ThemeToggle), integration (CSS variables), context (ThemeProvider), and E2E (Playwright) categories
- [117-00]: localStorage key is 'mop_theme' with values 'dark' | 'light'; DOM class is '.dark' on document.documentElement
- [117-00]: FOWT prevention via inline script in index.html that runs before React hydration; theme toggle placement in sidebar footer (post-auth only)

- [117-02]: Use React Context API for theme state (sufficient for app-wide state, no Redux needed)
- [117-02]: .dark class pattern follows Tailwind's darkMode: ["class"] configuration (standard approach)
- [117-02]: Hydration-safe: mounted state prevents hydration mismatches on initial render
- [117-02]: Toaster notifications made theme-aware: dynamic theme prop based on user's selection
- [117-02]: Fixed FOWT prevention script to use .dark class (Plan 01 used incorrect .light class)
- [117-02]: Auto-wrapped tests with ThemeProvider (needed for hook to work without throwing)

- [118-04]: Playwright verification as permanent test infrastructure (not one-time manual verification) for reuse in future UI phases
- [118-04]: Script location in mop_validation/scripts/ (shared validation repo, not main codebase) for consistency with CLAUDE.md separation
- [118-04]: Full-page screenshot capture with both light and dark themes as baseline for regression testing
- [118-04]: Console error allowlist (ResizeObserver loop, Non-Error promise, Invalid header) to eliminate false positives

### Completed in Phase 112

**Plan 112-01 (Conda Mirror Backend):**
- Implemented _mirror_conda() async method using throwaway miniconda:latest containers
- conda create --download-only pattern with 120s timeout, directory structure handling, status updates
- Implemented _regenerate_conda_index() helper using `conda index` command inside container
- Implemented get_condarc_content() YAML generator with channel deduplication and conda-forge prioritization
- Integrated Conda ecosystem branch into foundry_service.build_template() with base image validation
- Added /conda/ Caddyfile handler with static file serving and cache headers
- Added CONDA_MIRROR_URL environment variable to .env.example
- Comprehensive unit test suite: 7 Conda-specific tests covering download flow, version parsing, config generation
- All 43 mirror tests passing (7 new Conda + 36 existing PyPI/APT/Alpine/npm/NuGet)
- Total: 6 tasks, 5 files modified, 45 min duration

**Plan 112-02 (Unified Admin Mirror Configuration UI):**
- Extended MirrorConfigUpdate + MirrorConfigResponse Pydantic models with all 8 ecosystem URL fields
- Implemented GET/PUT /api/admin/mirror-config endpoints with admin-only access control (foundry:read/write permissions)
- Idempotent database seeding of Config table with all 8 mirror URL defaults via seed_mirror_config()
- Created MirrorConfigCard React component with read-only toggle, health status badges (icons + text), URL edit on blur
- Implemented MirrorsTab in Admin.tsx with 8-card grid, non-admin warning banner, useQuery/useMutation hooks
- Gated Mirrors tab visibility with {features.foundry &&} feature flag for Enterprise-only display
- Backend test suite: test_get_mirror_config_all_ecosystems, test_put_mirror_config_updates_database, test_mirror_config_permission_check, test_mirror_config_health_status (4 tests)
- Frontend test suite: test_admin_mirrors_tab_renders, test_mirror_card_shows_health_badge (2 tests)
- All 6 tests passing; requirement MIRR-08 satisfied; health_status dict ready for Phase 113 enhancement
- Total: 6 tasks, 7 files (1 new component + 6 modified), 20 min duration

**Plan 112-03 (Smelter Conda Defaults ToS Modal UI):**
- Implemented POST /api/admin/conda-defaults-acknowledge endpoint with per-user Config DB persistence (key: CONDA_DEFAULTS_TOS_ACKNOWLEDGED_BY_{user_id})
- Idempotent endpoint design: returns 200 "Already acknowledged" on duplicate calls (never 422)
- Updated GET /api/admin/mirror-config to include conda_defaults_acknowledged_by_current_user field
- Created CondaDefaultsToSModal component (155 lines): Dialog with AlertTriangle icon, 3 content sections, cancel/acknowledge buttons
- Created SmelterIngredientSelector component (223 lines): Ecosystem/channel dropdowns, ingredient form, modal integration
- State management: useQuery for mirror-config, useMutation for acknowledgment, 3 useEffect hooks for state coordination
- Modal blocking logic: Pre-selects conda-forge on CONDA ecosystem selection; shows modal + disables approval when defaults selected
- Permission gating: foundry:write required for acknowledgment endpoint
- Comprehensive test suite: 8 integration tests + 4 unit tests (12 total, all passing)
- Tests verify: pre-selection, modal appearance, blocking behavior, acknowledgment flow, API calls, cancellation, reset
- Total: 4 tasks, 5 files (3 created + 2 modified), 45 min duration

### Completed in Phase 109

**Plan 109-03 (Alpine Support + Mirror Health UI):**
- Implemented Alpine Dockerfile generation in foundry_service.build_template()
- Added per-version mirror URL injection from MirrorService.get_apk_repos_content()
- Post-processing of Dockerfile to inject --allow-untrusted flag into all apk add commands
- Created useSystemHealth React hook polling /api/system/health every 30s
- Created MirrorHealthBanner component: dismissible amber alert showing when EE mirrors unreachable
- Integrated MirrorHealthBanner into Admin.tsx and Templates.tsx views
- Written 4 comprehensive integration tests for Alpine Dockerfile generation and version parsing
- All 6 tests passing (4 new + 2 existing), frontend build successful
- Total: 4 tasks, 6 files modified/created, 100% task completion

**Plan 109-02 (Compose CE/EE Separation + Mirror Routing):**
- Refactored compose.server.yaml to CE-only (removed pypi, mirror services, mirror-data volume, MIRROR_DATA_PATH env)
- Created new compose.ee.yaml overlay file with agent volume overrides, pypi service, mirror service, mirror-data volume
- Updated mirror/Caddyfile with multi-path handle blocks (/apt/, /apk/, /simple/) for package serving
- Added mirror environment variables to .env.example: MIRROR_DATA_PATH, PYPI_MIRROR_URL, APT_MIRROR_URL, APK_MIRROR_URL, MIRROR_HEALTH_CHECK_INTERVAL, DEFAULT_ALPINE_VERSION
- Compose overlay pattern enables explicit EE activation: `docker compose -f compose.server.yaml -f compose.ee.yaml up -d`
- All four docker compose configurations validated and parsing without errors
- Total: 4 tasks, 4 files modified/created

**Plan 109-01 (APT/APK Mirror Backends):**
- Implemented _mirror_apt() for Debian .deb downloads via throwaway debian:12-slim container using apt-get download
- Added _regenerate_apt_index() helper using dpkg-scanpackages to generate Packages.gz inside container
- Implemented _mirror_apk() for Alpine .apk downloads via alpine:3.20 container using apk fetch
- Added _regenerate_apk_index() helper using apk index to generate APKINDEX.tar.gz
- Version constraint parsing converts ==X.Y.Z format to package specs (curl=7.68.0) for both APT and APK
- All subprocess calls use asyncio.to_thread() with 120s timeout for non-blocking execution
- Mirror health check background task: polls PYPI_MIRROR_URL and APT_MIRROR_URL every ~60s
- Health check implements exponential backoff (5s→10s→60s cap) on failure
- app.state.mirrors_available flag set based on both mirrors returning 200-399
- 14 comprehensive unit tests covering APT/APK download, version parsing, failure handling, Alpine version fallback
- Total: 4 tasks, 3 files modified, 14 tests passing

### Completed in Phase 107

**Plan 107-03 (Tool Recipe Edit + Approved OS Tab):**
- Tool recipe edit dialog with pencil icon on each tool row in Tools tab
- Pre-populated edit form: Tool ID, OS Family (DEBIAN/ALPINE), Validation Command, Injection Recipe, Runtime Dependencies
- PATCH /api/capability-matrix/{id} with only changed fields, toast success/error
- Approved OS tab in Foundry page with full inline CRUD (add, edit, delete)
- Inline edit mode: pencil icon toggles row to Input fields, Save/Cancel buttons
- PATCH /api/approved-os/{id} with changed fields only
- DELETE with 409 referential integrity error handling + detailed toast message
- OS family restricted to DEBIAN/ALPINE (no FEDORA) in all forms
- Build ✓ PASSED (16.37s), Lint ✓ PASSED (no errors)
- Total: 2 tasks, 1 file modified (Templates.tsx: 1,237 lines)

### Completed in Phase 108

**Plan 108-02 (Dual-Platform Mirror & Foundry Validation):**
- Extended mirror_service._mirror_pypi() with dual-platform download logic (manylinux2014, musllinux, sdist fallback)
- Added MirrorService._download_wheel() helper for platform-specific wheel/sdist downloads via pip
- Added MirrorService.mirror_ingredient_and_dependencies() for background auto-mirroring of resolved trees
- Integrated ResolverService hook + auto-mirror trigger into smelter_service.add_ingredient()
- Added FoundryService._validate_ingredient_tree() for full dependency tree validation before builds
- Integrated validation into foundry_service.build_template() with fail-fast 422 response
- Removed devpi service entirely from compose.server.yaml (pypiserver as single mirror)
- Added 5 dual-platform mirror tests (pure-python, C-extension, sdist fallback, logging, tree mirroring)
- Added 4 foundry validation tests (success all mirrored, fail parent, fail transitive, error messages)
- Total: 5 tasks, 6 files modified/created, ~430 lines of code + tests

**Plan 108-01 (Transitive Dependency Resolver):**
- Added ApprovedIngredient model with mirror_status, mirror_log, mirror_path, ecosystem fields
- Added IngredientDependency model with parent_id, child_id, dependency_type, version_constraint edges
- Implemented ResolverService.resolve_ingredient_tree() using pip-compile for transitive resolution
- Added validation to prevent circular dependencies
- Created test cases for resolver edge cases (missing packages, circular deps, pure-python packages)

### Pending Todos

0 pending (all Phase 118 completed):
- ~~**Create comprehensive test coverage for theme system** (frontend)~~ — 2026-04-02 ✓ DONE
- ~~**Implement useTheme hook + ThemeProvider** (Wave 2)~~ — 2026-04-02 ✓ DONE
- ~~**Implement CSS variables and FOWT prevention** (Wave 1)~~ — 2026-04-02 ✓ DONE
- ~~**Migrate UI components to theme-aware styling** (Wave 3)~~ — 2026-04-02 ✓ DONE

### Completed in Phase 117

**Plan 117-03 (Theme-Aware Dashboard Styling - Wave 3):**
- Refactored MainLayout.tsx: sidebar, header, main container, dialog, nav items all using CSS variables
- Updated Dialog overlay: bg-black/60 light mode, dark:bg-black/80 dark mode
- Updated ThemeToggle: bg-muted instead of hardcoded colors
- Batch updated 8 dashboard views: Dashboard, Nodes, Jobs, JobDefinitions, Templates, Signatures, Users, AuditLog
- Replaced 10+ hardcoded dark classes with theme-aware utilities across all views
- Updated Recharts tooltips to use CSS variables for theme-aware styling
- Dynamic Sonner Toaster: theme prop synced with useTheme hook via AppContent wrapper
- Build verified: no TypeScript errors, 2870 modules transformed successfully
- 8 commits with atomic, descriptive messages

**Plan 117-02 (Theme Toggle & State Management - Wave 2):**
- useTheme hook with Context API for state management (49 lines)
- ThemeProvider component for app-wide theme state
- ThemeToggle component with Sun/Moon icons and slider styling (54 lines)
- localStorage persistence with key "mop_theme" (values: 'light' | 'dark')
- Hydration-safe component initialization (mounted state check)
- Toaster component made theme-aware (dynamic theme prop)
- FOWT prevention script fixed to use .dark class
- All 13 theme-related tests passing (6 useTheme + 7 ThemeToggle)
- Build verified with no errors

**Plan 117-01 (CSS Variables & Tailwind Foundation - Wave 1):**
- CSS variable restructuring for light/dark theme switching
- Tailwind config extended with warm stone palette
- FOWT prevention inline script in index.html
- All 3 tasks completed successfully

**Plan 117-00 (Test Infrastructure - Wave 0):**
- useTheme hook unit tests (7 tests)
- ThemeToggle component tests (7 tests)
- CSS variables integration tests (9 tests)
- ThemeProvider context tests (5 tests)
- Playwright E2E tests for theme toggle (1 comprehensive test in Test 9)
- Total: 28 tests in RED state, defining expected behavior

### Completed in Phase 116

**Plan 116-01 (Backend):**
- migration_v46.sql with mirror_log column addition
- reload_licence() and check_licence_expiry() service functions
- POST /api/admin/licence/reload endpoint (200 on success, 422 on invalid)
- Background licence expiry timer (60s interval, VALID→GRACE→EXPIRED transitions)
- LicenceExpiryGuard middleware (402 Payment Required on EXPIRED status)
- Integration tests for reload and expiry workflows (all passing)

**Plan 116-02 (Frontend UI & WebSocket):**
- WebSocket broadcast integration in reload_licence_endpoint and background expiry checker
- Extended useWebSocket hook with LicenceStatusChangeData interface and optional onLicenceStatusChanged callback
- Three licence UI components: LicenceStatus (metadata card), LicenceReloadButton (admin-only), GracePeriodBanner (dismissible alert)
- Admin Licence tab with real-time WebSocket updates and query invalidation pattern
- Playwright E2E test (Test 8) for admin licence management workflow
- Grace period notifications with localStorage-persisted dismissal

### Completed in Phase 110

**Plan 110-00 (Test Scaffolds for CVE Transitive Scan + Dependency Tree UI - Wave 0):**
- Created test stubs for 5 backend tests (4 in test_smelter.py, 1 in test_foundry.py)
- Created test stubs for 13 frontend tests (6 in DependencyTreeModal.test.tsx, 4 in CVEBadge.test.tsx, 3 in Admin.test.tsx)
- All 18 test stubs discoverable by pytest/vitest, all pass execution
- RED phase complete: test infrastructure ready for Wave 1 implementation
- Total: 5 tasks, 5 files (2 created + 3 modified), 18 test stubs

### Completed in Phase 118

**Plan 118-04 (UI Polish Verification and Test Framework - Wave 4):**
- Built Playwright-based verification script (test_ui_polish.py) that automates UI quality checks
- Script navigates all 9 dashboard routes in both light and dark themes
- Captures 18 full-page screenshots (light + dark for each route)
- Validates no console errors (with allowlist for benign messages), no layout overflow, accessible component names
- Generates JSON results and markdown reports
- Saved as permanent reusable script in mop_validation/scripts/ for future regression testing
- Created comprehensive documentation (index.md) explaining report usage and interpretation
- All checks passing: theme consistency, responsive design, accessibility compliance
- Phase 118 complete: all 4 waves (theme audit, visual polish, bug fixes, verification) finished
- Total: 2 tasks, 3 files created (+ generated screenshots/reports)

**Plan 118-03 (GitHub Issue Fixes - GH #20, #21, #22):**
- GH #20: Fixed status filter parsing to support comma-separated values (e.g., COMPLETED,FAILED,CANCELLED)
- GH #20: Updated job_service._build_job_filter_queries() to split and validate multiple status values
- GH #21: Fixed Dashboard node count to show total (was showing ONLY online nodes)
- GH #21: Dashboard Nodes card now consistent with Nodes page header and list counts
- GH #22: Fixed node status indicator color logic to treat ACTIVE/BUSY as green (like ONLINE)
- GH #22: All node statuses now display correct colors (ONLINE/ACTIVE/BUSY=green, OFFLINE=red, etc)
- Frontend build verified: npm run build succeeds with 0 errors
- Backend API verified: Comma-separated status filtering works correctly
- Total: 3 tasks, 3 files modified

**Plan 118-02 (Visual Polish and Responsive Design):**
- Verified all 9 main dashboard views have consistent spacing (space-y-8 baseline, p-4/p-6 padding)
- Confirmed skeleton loaders in place for all loading states (bg-muted animate-pulse pattern)
- Replaced remaining "Loading..." text in Users.tsx with 3 skeleton rows matching table structure
- Verified responsive design at 768px breakpoint: sidebar collapses to hamburger menu on mobile/tablet
- Verified Button component has proper hover states (opacity/background changes) and focus rings (pink --ring)
- Phase 117 completed most polish work; 118-02 verified and finalized remaining items
- Build verified: npm run build succeeds with 0 errors, eslint clean
- Total: 3 tasks, 1 file modified (Users.tsx: +6, -2 lines)

**Plan 118-01 (CSS Variable Theming and Skeleton Component):**
- Implemented CSS variables for light/dark theme switching
- Created reusable Skeleton component (bg-muted animate-pulse)
- Configured Tailwind with extended color palette and animations
- Total: 4 tasks, 15 files (created/modified)

### Blockers/Concerns

- BaGetter API key auth flow for `nuget push` in throwaway container needs spike validation before Phase 111 planning
- pypiserver subdirectory serving for dual manylinux/musllinux layout needs confirmation during Phase 108 planning

## Session Continuity

Last session: 2026-04-05T15:58:20.789Z
Stopped at: Phase 114 context gathered
Ready for: Phase 111-03 (next plan) or Phase 119 (next phase after Phase 111 complete)
