---
gsd_state_version: 1.0
milestone: v19.0
milestone_name: — Foundry Improvements
status: executing
stopped_at: Phase 116 Plan 01 completed
last_updated: "2026-04-02T20:49:00.000Z"
last_activity: 2026-04-02 -- Completed 116-01-PLAN.md
progress:
  total_phases: 10
  completed_phases: 0
  total_plans: 3
  completed_plans: 3
  percent: 10
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-04-01)

**Core value:** Jobs run reliably -- on the right node, when scheduled, with their output captured -- without any step in the chain weakening the security model.
**Current focus:** Phase 107 - Schema Foundation + CRUD Completeness

## Current Position

Phase: 116 of 10 (116 - Fix Smelter DB Migration + EE Licence Hot-Reload)
Plan: 1 of 2 in current phase (COMPLETED)
Status: executing
Last activity: 2026-04-02 -- Completed 116-01-PLAN.md

Progress: [███░░░░░░░] 10%

## Performance Metrics

**Velocity:**
- Total plans completed: 2 (this milestone)
- Average duration: 7min
- Total execution time: 0.22 hours

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 107 | 2/3 | 13min | 7min |
| 116 | 1/2 | 45min | 45min |

**Recent Trend:**
- Last 5 plans: 107-01 (9min), 107-02 (4min), 116-01 (45min)
- Trend: stable (infrastructure/backend work inherently longer)

*Updated after each plan completion*

## Accumulated Context

### Roadmap Evolution

- Phase 116 added: Fix smelter DB migration and add EE licence hot-reload

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

### Pending Todos

0 pending (Phase 116-01 completed both):
- ~~**Hot-reload EE licence at runtime** (api)~~ — 2026-04-02 ✓ DONE
- ~~**Fix missing mirror_log column on approved_ingredients table** (api)~~ — 2026-04-02 ✓ DONE

### Completed in Phase 116-01

- migration_v46.sql with mirror_log column addition
- reload_licence() and check_licence_expiry() service functions
- POST /api/admin/licence/reload endpoint (200 on success, 422 on invalid)
- Background licence expiry timer (60s interval, VALID→GRACE→EXPIRED transitions)
- LicenceExpiryGuard middleware (402 Payment Required on EXPIRED status)
- Integration tests for reload and expiry workflows (all passing)

### Blockers/Concerns

- BaGetter API key auth flow for `nuget push` in throwaway container needs spike validation before Phase 111 planning
- pypiserver subdirectory serving for dual manylinux/musllinux layout needs confirmation during Phase 108 planning

## Session Continuity

Last session: 2026-04-02T20:49:00.000Z
Stopped at: Phase 116 Plan 01 completed
Ready for: Phase 116 Plan 02 (Wave 2: Dashboard UI + WebSocket broadcast)
