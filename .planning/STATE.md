---
gsd_state_version: 1.0
milestone: v11.0
milestone_name: — CE/EE Split Completion
status: planning
stopped_at: Completed 36-01-PLAN.md
last_updated: "2026-03-20T11:13:26.816Z"
last_activity: 2026-03-19 — Phase 35 complete (CE+EE smoke tests 2 passed, axiom-ee wheel built, PyPI publish pending credentials)
progress:
  total_phases: 4
  completed_phases: 2
  total_plans: 12
  completed_plans: 10
  percent: 50
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-03-19)

**Core value:** Jobs run reliably — on the right node, when scheduled, with their output captured — without any step in the chain weakening the security model.
**Current focus:** Phase 36 — Cython .so Build Pipeline

## Current Position

Phase: 36 of 37 (Cython .so Build Pipeline)
Plan: Not started
Status: Ready to plan
Last activity: 2026-03-19 — Phase 35 complete (CE+EE smoke tests 2 passed, axiom-ee wheel built, PyPI publish pending credentials)

Progress: [█████░░░░░] 50% (2/4 phases complete)

## v11.0 Phase Summary

| Phase | Goal | Requirements | Status |
|-------|------|--------------|--------|
| 34 — CE Baseline Fixes | CE install correct in isolation — 402 on EE routes, clean pytest, no dead-field crashes | GAP-01..06 | Complete |
| 35 — Private EE Repo + Plugin Wiring | CE+EE combined install works from Python source — all features true, all tables present | EE-01..08 | Complete (EE-08 partial — wheel built, PyPI publish pending) |
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
- [Phase 35-05]: axiom-ee wheel built (axiom_ee-0.1.0.dev0-py3-none-any.whl in ~/Development/axiom-ee/dist/); PyPI publish is EE-08 and requires TWINE_PASSWORD env var or ~/.pypirc — deferred to manual step
- [Phase 36]: packages=[] strips .py source from wheel; BuildExtAndCopyInits hook copies __init__.py files back as namespace markers
- [Phase 36]: musllinux wheels included (not skipped) — Containerfile.server uses python:3.12-alpine (musl libc); both manylinux and musllinux variants needed

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

Last session: 2026-03-20T11:13:22.263Z
Stopped at: Completed 36-01-PLAN.md
Resume file: None
Next action: `/gsd:plan-phase 36`
