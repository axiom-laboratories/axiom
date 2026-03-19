---
gsd_state_version: 1.0
milestone: v11.0
milestone_name: — CE/EE Split Completion
status: planning
stopped_at: "Checkpoint reached in 35-05-PLAN.md (human-verify: CE+EE smoke + PyPI publish)"
last_updated: "2026-03-19T21:46:57.960Z"
last_activity: 2026-03-19 — v11.0 roadmap created
progress:
  total_phases: 4
  completed_phases: 2
  total_plans: 9
  completed_plans: 9
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
- [Phase 34-ce-baseline-fixes]: Active pytest config is root pyproject.toml — markers added there, not puppeteer/pyproject.toml
- [Phase 34-ce-baseline-fixes]: test_bootstrap_admin.py import paths fixed from puppeteer.* to agent_service.* (Rule 1 auto-fix during GAP-04 work)
- [Phase 34-ce-baseline-fixes]: importlib.metadata.entry_points(group='axiom.ee') replaces deprecated pkg_resources in load_ee_plugins()
- [Phase 34-ce-baseline-fixes]: _mount_ce_stubs() called in both CE paths (no-plugin else branch and except handler) — single helper pattern
- [Phase 34]: NodeUpdateRequest replaces NodeConfig for PATCH /nodes/{node_id} — only tags and env_tag (CE-safe fields)
- [Phase 34]: PollResponse carries env_tag directly as Optional[str] = None — no config nesting, eliminates EE-field AttributeError on CE
- [Phase 34-ce-baseline-fixes]: testpaths = ['puppeteer/agent_service/tests'] excludes EE test dir from CE default run; puppeteer/tests/ remains opt-in
- [Phase 34-ce-baseline-fixes]: pre-existing test_sprint3.py 422 vs 200 mismatches marked skip with Phase 34 attribution — deferred to Phase 35+
- [Phase 35-private-ee-repo-plugin-wiring]: axiom-ee dependencies=[] intentionally empty — CE venv is the shared runtime peer, not a pip dependency
- [Phase 35-private-ee-repo-plugin-wiring]: EEPlugin.register() is async — deferred router imports prevent circular startup imports; sync DDL via engine.sync_engine
- [Phase 35]: All intra-EEBase FKs dropped as plain String per plan spec — avoids DDL ordering dependencies and simplifies Cython compilation in Phase 36
- [Phase 35]: Trigger.job_definition_id made nullable=True — without FK constraint NULL is valid; preserves semantic without DB enforcement
- [Phase 35]: EE Pydantic models co-located in ee/{feature}/models.py alongside SQLAlchemy models — avoids a separate pydantic/ layer per feature
- [Phase 35]: WebhookService.dispatch_event uses httpx for real outbound HTTP — CE stub was no-op
- [Phase 35]: load_ee_plugins made async so EEPlugin.register() can be properly awaited — without this, register() silently returned a coroutine object making EEContext truthy in CE mode
- [Phase 35]: Base.metadata.tables guard removed from deps.audit() — AuditLog is in EEBase.metadata; try/except is the sole CE/EE boundary in audit()
- [Phase 35]: test_ce_stub_routers_return_402 calls stub handlers directly — httpx ASGITransport skips ASGI lifespan, so lifespan-mounted stubs are never registered during unit tests

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

Last session: 2026-03-19T21:46:53.399Z
Stopped at: Checkpoint reached in 35-05-PLAN.md (human-verify: CE+EE smoke + PyPI publish)
Resume file: None
Next action: `/gsd:plan-phase 34`
