---
gsd_state_version: 1.0
milestone: v19.0
milestone_name: — Foundry Improvements
status: executing
stopped_at: Phase 109 context gathered
last_updated: "2026-04-03T19:55:07.849Z"
last_activity: 2026-04-03 -- Completed 107-03-PLAN.md (Tool Recipe Edit + Approved OS Tab)
progress:
  total_phases: 12
  completed_phases: 4
  total_plans: 12
  completed_plans: 12
  percent: 100
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-04-01)

**Core value:** Jobs run reliably -- on the right node, when scheduled, with their output captured -- without any step in the chain weakening the security model.
**Current focus:** Phase 107 - Schema Foundation + CRUD Completeness

## Current Position

Phase: 107 of 12 (107 - Schema Foundation + CRUD Completeness)
Plan: 3 of 3 in current phase (COMPLETED 107-03)
Status: executing
Last activity: 2026-04-03 -- Completed 107-03-PLAN.md (Tool Recipe Edit + Approved OS Tab)

Progress: [██████████████████] 100%

## Performance Metrics

**Velocity:**
- Total plans completed: 5 (this milestone)
- Average duration: 8min
- Total execution time: 0.68 hours

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 107 | 2/3 | 13min | 7min |
| 116 | 2/2 | 80min | 40min |
| 117 | 4/5 | 135min | 34min |

**Recent Trend:**
- Last 6 plans: 116-01 (45min), 116-02 (35min), 117-00 (15min), 117-01 (11min), 117-02 (8min), 117-03 (135min)
- Trend: 117-03 required intensive refactoring across 14 files (9 view files + layout/hook/toggle/dialog/app)

*Updated after each plan completion*

| Phase | Plan | Duration | Tasks | Files |
|-------|------|----------|-------|-------|
| 107 | 03 | 0min | 2 | 1 |
| 108 | 01 | 30min | 3 | 5 |
| 108 | 02 | 45min | 5 | 6 |

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

0 pending (all Phase 108-01 and 108-02 completed):
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

### Blockers/Concerns

- BaGetter API key auth flow for `nuget push` in throwaway container needs spike validation before Phase 111 planning
- pypiserver subdirectory serving for dual manylinux/musllinux layout needs confirmation during Phase 108 planning

## Session Continuity

Last session: 2026-04-03T19:55:07.841Z
Stopped at: Phase 109 context gathered
Ready for: Plan 117-04 verification or Phase 118 (next phase in roadmap)
