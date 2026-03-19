---
gsd_state_version: 1.0
milestone: v11.0
milestone_name: — CE/EE Split Completion
status: planning
stopped_at: Phase 34 context gathered
last_updated: "2026-03-19T18:57:06.440Z"
last_activity: 2026-03-19 — v11.0 roadmap created
progress:
  total_phases: 4
  completed_phases: 0
  total_plans: 0
  completed_plans: 0
  percent: 0
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-03-19)

**Core value:** Jobs run reliably — on the right node, when scheduled, with their output captured — without any step in the chain weakening the security model.
**Current focus:** Phase 34 — CE Baseline Fixes

## Current Position

Phase: 34 of 37 (CE Baseline Fixes)
Plan: Not started
Status: Ready to plan
Last activity: 2026-03-19 — v11.0 roadmap created

Progress: [░░░░░░░░░░] 0%

## v11.0 Phase Summary

| Phase | Goal | Requirements | Status |
|-------|------|--------------|--------|
| 34 — CE Baseline Fixes | CE install correct in isolation — 402 on EE routes, clean pytest, no dead-field crashes | GAP-01..06 | Not started |
| 35 — Private EE Repo + Plugin Wiring | CE+EE combined install works from Python source — all features true, all tables present | EE-01..08 | Not started |
| 36 — Cython .so Build Pipeline | EE compiled to .so, multi-arch wheel, no .py source, compiled smoke test passes | BUILD-01..05 | Not started |
| 37 — Licence Validation + Docs + Docker Hub | Offline licence key enforced at startup, axiom-ce on Docker Hub, CE/EE admonitions in docs | DIST-01..03 | Not started |

## Accumulated Context

### Decisions

- v11.0: Cython 3.2.4 + cibuildwheel 3.4.0 chosen — no new runtime packages; build-time only in EE pyproject.toml
- v11.0: `importlib.metadata.entry_points(group="axiom.ee")` replaces deprecated `pkg_resources.iter_entry_points()` in CE
- v11.0: EE models must import CE `Base` from `agent_service.db` — never define a new Base (create_all is Base-scoped)
- v11.0: `__init__.py` must never be compiled to .so — CPython bug #59828; leave as plain Python importing compiled submodules
- v11.0: Stub routers guarded with `if not ctx.{feature}:` after `register()` completes — prevents silent FastAPI duplicate route shadowing
- v11.0: Ed25519 offline licence validation only — no online call-home; air-gapped deployments are a core use case

### Pending Todos

- [ ] Inspect pre-split `db.py` git history during Phase 35 to confirm the full 15 EE table list before writing `ee/db_models.py`
- [ ] Document the restart-required licence re-validation policy in `ee/README.md` at v11.0 release (v11.1 adds periodic re-check)

### Blockers/Concerns

None — v10.0 complete. Starting clean on v11.0:
- All work targets the `feature/axiom-oss-ee-split` worktree at `.worktrees/axiom-split/`
- Phase 34 gap fixes are independent of each other and can be parallelised within a single phase
- Phase 35 depends on Phases 34 gaps 1 and 3 being clean before EE router work begins
- Licence validation code (DIST-01) must be designed before Phase 36 closes so it compiles into the .so

## Session Continuity

Last session: 2026-03-19T18:57:06.438Z
Stopped at: Phase 34 context gathered
Resume file: .planning/phases/34-ce-baseline-fixes/34-CONTEXT.md
Next action: `/gsd:plan-phase 34`
