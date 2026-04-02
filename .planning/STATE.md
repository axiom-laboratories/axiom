---
gsd_state_version: 1.0
milestone: v19.0
milestone_name: — Foundry Improvements
status: executing
stopped_at: Phase 117 Plan 01 completed
last_updated: "2026-04-02T22:50:00.000Z"
last_activity: 2026-04-02 -- Completed 117-01-PLAN.md (CSS Variables & Tailwind Foundation)
progress:
  total_phases: 11
  completed_phases: 1
  total_plans: 5
  completed_plans: 2
  percent: 40
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-04-01)

**Core value:** Jobs run reliably -- on the right node, when scheduled, with their output captured -- without any step in the chain weakening the security model.
**Current focus:** Phase 107 - Schema Foundation + CRUD Completeness

## Current Position

Phase: 117 of 11 (117 - Implement Light Mode with Dark Mode Toggle)
Plan: 2 of 5 in current phase (COMPLETED 117-01)
Status: executing
Last activity: 2026-04-02 -- Completed 117-01-PLAN.md (CSS Variables & Tailwind Foundation)

Progress: [██████████] 40%

## Performance Metrics

**Velocity:**
- Total plans completed: 4 (this milestone)
- Average duration: 7min
- Total execution time: 0.45 hours

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 107 | 2/3 | 13min | 7min |
| 116 | 2/2 | 80min | 40min |
| 117 | 2/5 | 25min | 12min |

**Recent Trend:**
- Last 5 plans: 107-01 (9min), 107-02 (4min), 116-01 (45min), 116-02 (35min), 117-00 (15min)
- Trend: stable (test infrastructure work is medium complexity)

*Updated after each plan completion*

## Accumulated Context

### Roadmap Evolution

- Phase 116 added: Fix smelter DB migration and add EE licence hot-reload
- Phase 117 added: Implement light mode with a light mode/dark mode toggle, whilst keeping the brand identity

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

- [117-00]: Structured all theme tests in RED (failing) state per TDD methodology to define expected behavior upfront before implementation
- [117-00]: Theme infrastructure tests organized into unit (useTheme hook), component (ThemeToggle), integration (CSS variables), context (ThemeProvider), and E2E (Playwright) categories
- [117-00]: localStorage key is 'mop_theme' with values 'dark' | 'light'; DOM class is '.dark' on document.documentElement
- [117-00]: FOWT prevention via inline script in index.html that runs before React hydration; theme toggle placement in sidebar footer (post-auth only)

### Pending Todos

0 pending (Phase 117-00 completed test infrastructure):
- ~~**Create comprehensive test coverage for theme system** (frontend)~~ — 2026-04-02 ✓ DONE
- **Implement useTheme hook + ThemeProvider** (Wave 1-02) — pending
- **Implement CSS variables and FOWT prevention** (Wave 1-01) — pending
- **Migrate UI components to theme-aware styling** (Wave 1-03) — pending

### Completed in Phase 117

**Plan 117-00 (Test Infrastructure - Wave 0):**
- useTheme hook unit tests (7 tests)
- ThemeToggle component tests (7 tests)
- CSS variables integration tests (9 tests)
- ThemeProvider context tests (5 tests)
- Playwright E2E tests for theme toggle (1 comprehensive test in Test 9)
- Total: 28 tests in RED state, defining expected behavior for subsequent waves

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

Last session: 2026-04-02T21:23:40.694Z
Stopped at: Phase 117 context gathered
Ready for: Phase 117+ (next phase in roadmap)
