---
phase: 35-private-ee-repo-plugin-wiring
plan: "01"
subsystem: infra
tags: [python, setuptools, entry-points, sqlalchemy, importlib-metadata]

# Dependency graph
requires: []
provides:
  - "~/Development/axiom-ee/ git repo initialised with pyproject.toml"
  - "axiom.ee entry_point registered: ee = ee.plugin:EEPlugin"
  - "EEBase declarative base isolated from CE Base"
  - "EEPlugin skeleton with async register() stub"
  - "8 EE feature subdirectories: foundry, audit, auth_ext, smelter, triggers, webhooks, users, rbac"
  - "pip install -e ~/Development/axiom-ee/ installs axiom-ee-0.1.0.dev0 into CE venv"
affects:
  - "35-02"
  - "35-03"
  - "35-04"
  - "35-05"

# Tech tracking
tech-stack:
  added:
    - "axiom-ee package (setuptools, pyproject.toml, editable install)"
  patterns:
    - "entry_points(group='axiom.ee') plugin discovery — importlib.metadata, not pkg_resources"
    - "EEBase separate from CE Base — EE DDL never executed by CE create_all"
    - "No module-level router imports in plugin.py — all deferred inside register() to prevent circular imports"
    - "sync_engine for DDL — EEBase.metadata.create_all(engine.sync_engine), not AsyncEngine"

key-files:
  created:
    - "~/Development/axiom-ee/pyproject.toml"
    - "~/Development/axiom-ee/ee/__init__.py"
    - "~/Development/axiom-ee/ee/base.py"
    - "~/Development/axiom-ee/ee/plugin.py"
    - "~/Development/axiom-ee/ee/foundry/__init__.py"
    - "~/Development/axiom-ee/ee/audit/__init__.py"
    - "~/Development/axiom-ee/ee/auth_ext/__init__.py"
    - "~/Development/axiom-ee/ee/smelter/__init__.py"
    - "~/Development/axiom-ee/ee/triggers/__init__.py"
    - "~/Development/axiom-ee/ee/webhooks/__init__.py"
    - "~/Development/axiom-ee/ee/users/__init__.py"
    - "~/Development/axiom-ee/ee/rbac/__init__.py"
  modified: []

key-decisions:
  - "axiom-ee dependencies = [] intentionally empty — CE venv is the shared runtime peer, not a pip dependency"
  - "Entry point name 'ee' (not 'axiom-ee') per plan spec — CE's load_ee_plugins discovers any entry in group axiom.ee"
  - "EEPlugin.register() is async — matches CE's async lifespan context; sync DDL done via sync_engine wrapper"

patterns-established:
  - "Pattern 1: EEBase isolation — never import CE Base into EE; create_all is Base-scoped"
  - "Pattern 2: Deferred router imports inside register() — prevents circular startup imports"
  - "Pattern 3: sync_engine for DDL — SA 2.x requires sync connection for create_all, not AsyncEngine"

requirements-completed:
  - EE-01
  - EE-05

# Metrics
duration: 2min
completed: 2026-03-19
---

# Phase 35 Plan 01: axiom-ee Repo Scaffold Summary

**axiom-ee pip-installable package at ~/Development/axiom-ee/ with importlib.metadata entry_point wiring and EEPlugin async register() stub**

## Performance

- **Duration:** 2 min
- **Started:** 2026-03-19T21:20:11Z
- **Completed:** 2026-03-19T21:21:37Z
- **Tasks:** 2
- **Files modified:** 13

## Accomplishments
- axiom-ee git repo initialised at ~/Development/axiom-ee/ with 2 commits
- pyproject.toml with `[project.entry-points."axiom.ee"]` wiring; `ee = "ee.plugin:EEPlugin"` discoverable via `importlib.metadata.entry_points(group="axiom.ee")`
- EEBase declarative base isolated from CE's Base — EE DDL never touched by CE create_all
- EEPlugin skeleton with async `register()` that calls `EEBase.metadata.create_all(engine.sync_engine)` and sets `ctx.resource_limits = True` as stub
- All 8 EE feature subdirectories scaffolded with empty `__init__.py`
- Package installed in editable mode into CE venv (`axiom-ee-0.1.0.dev0`)

## Task Commits

Each task was committed atomically in the axiom-ee repo:

1. **Task 1: Initialise axiom-ee git repo and pyproject.toml** - `912eaf7` (init)
2. **Task 2: Create ee/ package structure — base.py and EEPlugin skeleton** - `08cc986` (feat)

## Files Created/Modified
- `~/Development/axiom-ee/pyproject.toml` - Package definition with axiom.ee entry_point, setuptools>=77.0
- `~/Development/axiom-ee/.gitignore` - Standard Python ignores
- `~/Development/axiom-ee/ee/__init__.py` - Empty (no eager loading)
- `~/Development/axiom-ee/ee/base.py` - EEBase(DeclarativeBase) isolated from CE Base
- `~/Development/axiom-ee/ee/plugin.py` - EEPlugin with async register() stub; deferred imports pattern
- `~/Development/axiom-ee/ee/foundry/__init__.py` - Empty stub
- `~/Development/axiom-ee/ee/audit/__init__.py` - Empty stub
- `~/Development/axiom-ee/ee/auth_ext/__init__.py` - Empty stub
- `~/Development/axiom-ee/ee/smelter/__init__.py` - Empty stub
- `~/Development/axiom-ee/ee/triggers/__init__.py` - Empty stub
- `~/Development/axiom-ee/ee/webhooks/__init__.py` - Empty stub
- `~/Development/axiom-ee/ee/users/__init__.py` - Empty stub
- `~/Development/axiom-ee/ee/rbac/__init__.py` - Empty stub

## Decisions Made
- `dependencies = []` in pyproject.toml — CE venv is the shared runtime peer, not a pip dependency
- Entry point name is `ee` (not `axiom-ee`) per plan spec — CE's `load_ee_plugins` iterates all entries in group `axiom.ee`
- `EEPlugin.register()` is `async` — matches CE's async lifespan; sync DDL done via `engine.sync_engine`

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- axiom-ee package discoverable by CE via entry_point — ready for Plan 02 (EE DB models)
- EEBase in place for EE SQLAlchemy models to subclass
- EEPlugin.register() stub ready to receive router mounts in Plan 03
- All 8 feature subdirectory stubs ready for Plan 03 router implementations

---
*Phase: 35-private-ee-repo-plugin-wiring*
*Completed: 2026-03-19*
