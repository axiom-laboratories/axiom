---
gsd_state_version: 1.0
milestone: v12.0
milestone_name: — Operator Maturity
status: planning
stopped_at: Completed 49-01-PLAN.md
last_updated: "2026-03-22T21:14:08.919Z"
last_activity: 2026-03-22 — v12.0 roadmap created; 44 requirements across 8 phases
progress:
  total_phases: 8
  completed_phases: 3
  total_plans: 15
  completed_plans: 11
  percent: 0
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-03-22)

**Core value:** Jobs run reliably — on the right node, when scheduled, with their output captured — without any step in the chain weakening the security model.
**Current focus:** v12.0 — Operator Maturity (Phase 46 next)

## Current Position

Phase: 46 of 53 (Tech Debt + Security + Branding)
Plan: — (not yet planned)
Status: Ready to plan
Last activity: 2026-03-22 — v12.0 roadmap created; 44 requirements across 8 phases

Progress: [░░░░░░░░░░] 0%

## Performance Metrics

**Velocity:**
- Total plans completed: 0 (v12.0)
- Average duration: —
- Total execution time: —

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| — | — | — | — |
| Phase 46-tech-debt-security-branding P03 | 5 | 2 tasks | 6 files |
| Phase 46-tech-debt-security-branding P01 | 25min | 2 tasks | 6 files |
| Phase 46 P02 | 3min | 2 tasks | 7 files |
| Phase 47-ce-runtime-expansion P01 | 3min | 3 tasks | 3 files |
| Phase 47-ce-runtime-expansion P02 | 3min | 2 tasks | 5 files |
| Phase 47-ce-runtime-expansion P03 | 15min | 2 tasks | 1 files |
| Phase 47-ce-runtime-expansion P04 | 5min | 2 tasks | 3 files |
| Phase 48-scheduled-job-signing-safety P01 | 4min | 2 tasks | 2 files |
| Phase 48 P02 | 3min | 2 tasks | 2 files |
| Phase 49-pagination-filtering-and-search P02 | 10min | 2 tasks | 6 files |
| Phase 49-pagination-filtering-and-search P01 | 10min | 1 tasks | 1 files |

## Accumulated Context

### Decisions

- [Phase 45]: 4 critical patches applied inline (app.state.licence, EE expiry bypass, retriable=True, global declaration). 5 findings deferred to v12.0+ including MIN-06/07/08/WARN-08.
- [v12.0 Roadmap]: Phase 49 (pagination/filtering) depends only on Phase 46 — can proceed in parallel with Phase 47 (runtime expansion). Phase 50 (guided form) requires both 47 and 49.
- [v12.0 Roadmap]: Phase 53 (scheduling health + data mgmt) depends on both Phase 48 (DRAFT signing safety) and Phase 52 (queue visibility).
- [Phase 46]: BRAND-01 rename: Blueprint=Image Recipe, Template=Node Image, Capability Matrix=Tools applied to 5 Foundry TSX files; TypeScript identifiers preserved
- [Phase 46-tech-debt-security-branding]: DEBT-01: Two-step SELECT+DELETE replaces correlated subquery for SQLite-portable NodeStats pruning
- [Phase 46-tech-debt-security-branding]: DEBT-03: Permission cache pre-warmed in lifespan() startup, wrapped in try/except for CE mode compatibility
- [Phase 46-tech-debt-security-branding]: DEBT-02/04 required zero code changes — foundry_service.py cleanup and node.py sorted() were already correct
- [Phase 46]: SEC-01 audit call placed at status determination point (before db.commit()) using sync audit() from deps.py — consistent with existing audit pattern
- [Phase 46]: SEC-02 HMAC uses ENCRYPTION_KEY bytes directly as key material — avoids introducing a separate secret; message format binds payload to its specific job and signature record
- [Phase 47-ce-runtime-expansion]: Temp-file mount pattern chosen over stdin for all three runtimes; python_script task_type removed entirely; RUNTIME_EXT/RUNTIME_CMD dispatch maps inline in execute_task
- [Phase 47-ce-runtime-expansion]: python_script task_type dropped entirely — model_validator raises 422 with clear migration message (RT-06 superseded by CONTEXT.md)
- [Phase 47-ce-runtime-expansion]: Runtime merged into payload dict (not a separate WorkResponse column) so node.py reads it from payload as before
- [Phase 47-ce-runtime-expansion]: Runtime dropdown hidden for non-script task types; display_type ?? task_type fallback for backward compatibility with old python_script jobs; default form task_type changed from web_task to script
- [Phase 47-ce-runtime-expansion]: Runtime derived via getattr(s_job, 'runtime', None) or 'python' in /api/dispatch — mirrors scheduler_service.py pattern; runtime injected into both payload_dict and JobCreate kwargs
- [Phase 48]: Raw SQL used for audit_log INSERT in execute_scheduled_job — CE-safe (ORM model is EE-only, test_ce_table_count enforces audit_log not in CE Base.metadata)
- [Phase 48]: test_draft_skip_log_message creates audit_log table via DDL in test setup — avoids altering CE schema while still verifying verbatim skip message
- [Phase 48]: DRAFT warning modal placed as Dialog sibling in JobDefinitions.tsx rather than inside JobDefinitionModal — decoupled from full edit form lifecycle
- [Phase 48]: ReSignDialog implemented as standalone component inside JobDefinitionList.tsx — self-contained and co-located with the rows that trigger it
- [Phase 49-pagination-filtering-and-search]: PaginatedJobResponse defined in models.py (not job_service.py) so Plans 03 and 04 share a single import path without circular dependency risk
- [Phase 49-pagination-filtering-and-search]: POST /jobs stamps created_by via model_copy(update={'created_by': username}) — stamped at API boundary, not service layer, to keep service testable without auth context
- [Phase 49]: Wave 0 stub convention: pytest.fail as first body line (not after awaits) so all 13 stubs fail with 'not implemented' marker; future shapes in docstrings

### Pending Todos

None.

### Blockers/Concerns

- DEBT-01 through DEBT-04 and SEC-01/02 in Phase 46 are all self-contained. No stack dependency. Can start immediately.
- Phase 47 runtime expansion requires Containerfile.node changes — rebuild of the base node image needed before runtime expansion can be validated end-to-end.

## Session Continuity

Last session: 2026-03-22T21:14:08.917Z
Stopped at: Completed 49-01-PLAN.md
Next action: `/gsd:plan-phase 46`
Resume file: None
