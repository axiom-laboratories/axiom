# Phase 36: Cython .so Build Pipeline - Context

**Gathered:** 2026-03-20
**Status:** Ready for planning

<domain>
## Phase Boundary

Compile all `axiom-ee` Python source modules to Cython `.so` extension modules and produce a multi-arch wheel (amd64 + arm64, Python 3.11/3.12/3.13) with no `.py` source files (except `__init__.py` package markers). Validate the compiled wheel passes the same CE+EE full-stack smoke test as the Phase 35 source install. No PyPI publish in this phase — that's Phase 37.

</domain>

<decisions>
## Implementation Decisions

### CI platform
- No GitHub Actions budget — local `cibuildwheel` IS the CI for BUILD-03 purposes
- Use QEMU emulation on local x86 machine to cross-compile both amd64 and arm64 wheels from one machine (no Pi SSH needed)
- cibuildwheel output goes to `wheelhouse/` directory in `~/Development/axiom-ee/` (git-ignored)
- A `Makefile` or `build.sh` script wraps the cibuildwheel invocation — documents the exact local build command
- GitHub remote for `axiom-ee` exists but CI workflow is not executed (no budget)

### Smoke test location and approach
- Smoke test lives in `mop_validation/scripts/` — consistent with existing test infrastructure
- Test is a **full stack test**: brings up Docker stack with compiled EE wheel installed, runs `test_local_stack.py` assertions
- EE wheel is installed from a **local devpi server** (containerized in Docker, added to the axiom project's compose setup)
- The devpi container is global/reusable across projects — not axiom-specific
- mop_validation will be pushed to the `axiom-laboratories` GitHub org as a private repo alongside axiom-ee

### devpi server
- Run as a Docker container, added to the local dev compose configuration
- Serves the `axiom-ee` compiled wheels to the Docker stack during smoke tests
- `pip install --index-url http://devpi:3141/root/pypi/+simple/ axiom-ee` pattern inside the agent container

### `__init__.py` handling
- All `ee/{feature}/__init__.py` files are kept as empty plain Python files — they are required as package namespace markers
- All `__init__.py` files are **excluded** from `ext_modules` in pyproject.toml (CPython bug #59828 — Cython cannot compile `__init__.py`)
- Final wheel contains only `__init__.py` as `.py` source; all other modules become `.so` compiled extensions
- BUILD-04 success criterion: `unzip -l axiom_ee-*.whl | grep "\.py$"` returns only `__init__.py` entries — confirmed valid target

### Version strategy
- Bump `axiom-ee` from `0.1.0.dev0` to **`0.1.0`** — the compiled wheel is the first stable release
- PyPI publish of 0.1.0 is **deferred to Phase 37** (alongside licence validation and Docker Hub publish)
- Phase 36 validates locally (devpi + stack test) only
- cibuildwheel produces **separate per-platform wheels** (standard practice) — pip picks the right one on install

### Claude's Discretion
- Exact cibuildwheel configuration options (build matrix, `CIBW_*` env vars)
- Whether to use a `setup.py` alongside `pyproject.toml` for Cython `ext_modules`, or use `pyproject.toml` only
- Devpi container image choice and port mapping
- Exact Makefile target names for the build script
- How to handle `ee/rbac/` which has no router.py — whether it has any compilable modules at all

</decisions>

<specifics>
## Specific Ideas

- BUILD-03 success is redefined as: "cibuildwheel runs locally and produces wheels for amd64 + arm64 × Python 3.11/3.12/3.13 without errors" — not GitHub Actions
- devpi is intended as a persistent shared tool, not a per-phase throwaway — design it to be reusable across other Python projects in the lab
- mop_validation GitHub repo push is a deliverable of this phase (needed to establish the private test infra repo alongside axiom-ee)

</specifics>

<code_context>
## Existing Code Insights

### Reusable Assets
- `~/Development/axiom-ee/pyproject.toml`: uses `setuptools>=77.0` build backend — Cython `ext_modules` integrates via `setuptools.Extension`; needs `cython>=3.2.4` added to `[build-system].requires`
- `~/Development/axiom-ee/ee/`: 8 subdirectories, each with `__init__.py` (empty) + `router.py`, `models.py`, `services.py` — ~25 Python files total to compile
- Phase 35 smoke test in `mop_validation/scripts/test_ce_ee_smoke.py` — extend this or create `test_compiled_wheel.py` alongside it

### Established Patterns
- `axiom-ee` has no existing build scripts — start fresh
- `cibuildwheel` expects either `setup.py`, `pyproject.toml`, or `setup.cfg` with `ext_modules` declared
- Cython 3.2.4 + cibuildwheel 3.4.0 are the pinned versions (from STATE.md v11.0 decisions)
- `@dataclass` audit: no decorators found in EE source ✓ — BUILD-01 pre-condition already met

### Integration Points
- `pyproject.toml` in `axiom-ee`: add `cython` + `setuptools` to `[build-system].requires`, add `ext_modules` configuration
- `compose.server.yaml` (or a local dev compose): add devpi service for local PyPI server
- `mop_validation/scripts/`: new smoke test script that installs from devpi and runs stack assertions

</code_context>

<deferred>
## Deferred Ideas

- PyPI publish of compiled 0.1.0 wheel — Phase 37
- GitHub Actions CI workflow for axiom-ee (blocked on budget) — future, when Actions budget available
- Periodic devpi cache sync / mirror of public PyPI — could make devpi a full airgapped mirror; out of scope for now

</deferred>

---

*Phase: 36-cython-so-build-pipeline*
*Context gathered: 2026-03-20*
