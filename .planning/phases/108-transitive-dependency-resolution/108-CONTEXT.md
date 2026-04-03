# Phase 108: Transitive Dependency Resolution - Context

**Gathered:** 2026-04-03
**Status:** Ready for planning

<domain>
## Phase Boundary

When an operator approves a package, the mirror service resolves and downloads the complete transitive dependency tree so air-gapped STRICT builds succeed without internet access. Covers PyPI ecosystem only (APT/apk/npm/NuGet mirrors are separate phases). Includes dual-platform wheel mirroring (manylinux + musllinux), circular dependency protection, and Foundry build validation of the full tree.

</domain>

<decisions>
## Implementation Decisions

### Resolution approach
- Use **pip-compile** (from pip-tools) to resolve full transitive dependency trees
- Add `pip-tools` to `requirements.txt`
- Create standalone `resolver_service.py` — clean separation from mirror_service.py (follows existing service-per-domain pattern)
- Default: run pip-compile inside the agent container (Debian-based)
- Fallback: if resolution fails or target OS is Alpine, spin up a throwaway Docker container matching the target OS and run pip-compile there
- pip-compile output is **transient** — parse it to populate `IngredientDependency` rows, then discard. The dependency table IS the audit trail
- Discovered transitive deps are **auto-approved** as new `ApprovedIngredient` rows with `auto_discovered=True` flag
- When a transitive dep matches an already-approved ingredient, **link to existing record** and skip re-mirroring (deduplication)
- Any PATCH to `version_constraint` auto-triggers fresh re-resolution (old edges replaced, new deps mirrored)
- FoundryService build check must validate the **entire dependency tree** is mirrored, not just top-level packages

### Dual-platform mirroring
- Download **both** manylinux2014_x86_64 and musllinux_1_1_x86_64 wheels for every resolved dep
- Pure-python wheels (py3-none-any) downloaded once — detect and skip redundant platform download
- All wheels stored in the **same pypiserver directory** (`/data/packages/`). One pypiserver instance serves both platforms. pip inside build containers auto-selects the correct wheel
- If a musllinux wheel doesn't exist for a C-extension package, **fall back to sdist** (source distribution). Alpine builds compile from source (requires build tools in Dockerfile)
- No storage duplication: if Flask and Django both depend on Jinja2, same wheel file exists once on disk. `IngredientDependency` edges link to the same `ApprovedIngredient` row

### Auto-resolve trigger
- Resolution triggers **automatically on ingredient approval** — same pattern as existing auto-mirror (asyncio.create_task)
- New `mirror_status` lifecycle: PENDING -> RESOLVING -> MIRRORING -> MIRRORED (or FAILED at any step)
- Background task with **WebSocket status push** — ingredient row shows spinner in UI until resolution completes
- Add **re-resolve button** on each ingredient in the Smelter UI for manual re-trigger (e.g. after upstream releases new versions)
- Concurrent resolution of the same ingredient blocked via **mirror_status check** — if already RESOLVING, return 409

### Circular dependency & failure handling
- **Max depth limit: 10** for dependency tree traversal (most Python trees are 3-5 deep)
- **Visited-set guard** to break actual circular chains
- **5-minute global timeout** on the pip-compile subprocess — mark FAILED with timeout message if exceeded
- On failure: set `mirror_status=FAILED`, store pip-compile stderr in `mirror_log`
- Operator gets choice to **rollback** (delete dependency edges and auto-approved ingredients from this run) or **keep** what was resolved
- Lock via mirror_status: if status is RESOLVING, reject concurrent resolution with 409

### Infrastructure cleanup
- **Remove devpi** from compose.server.yaml — unused, pypiserver is the chosen mirror
- Keep pypiserver as the single PyPI mirror service

### Claude's Discretion
- Exact pip-compile command flags and temp file management
- How to parse pip-compile output to extract dependency edges
- Throwaway container image selection and lifecycle
- Whether to add `auto_discovered` as a boolean column on ApprovedIngredient or track via dependency_type
- Error message formatting for operator-facing failures
- WebSocket event names/payload for resolution status updates

</decisions>

<specifics>
## Specific Ideas

- Follow the established `asyncio.to_thread(subprocess.run, cmd, ...)` pattern from mirror_service.py and smelter_service.py
- The `IngredientDependency` table already has all needed columns (parent_id, child_id, dependency_type, version_constraint, ecosystem, discovered_at) — Phase 107 created it
- New endpoint needed: `POST /api/smelter/ingredients/{id}/resolve` for manual re-trigger
- Phase 13 decision carries forward: "auto-mirror on approval", "fail-fast if not mirrored", "STRICT enforcement, no overrides"
- Deduplication is natural: same wheel file on disk, same ApprovedIngredient row in DB, multiple IngredientDependency edges pointing to it

</specifics>

<code_context>
## Existing Code Insights

### Reusable Assets
- `MirrorService._mirror_pypi()` (`mirror_service.py:52-86`): pip download pattern with subprocess, captures stdout/stderr, updates mirror_status. Phase 108 extends this with dual-platform downloads
- `SmelterService.scan_vulnerabilities()` (`smelter_service.py:52-156`): pip-audit subprocess + JSON parsing + temp file pattern. Resolver follows same shape
- `asyncio.create_task()` pattern in `smelter_service.py:30`: background task spawning for mirror jobs
- `IngredientDependency` model (`db.py:312-325`): ready-made schema with unique constraint on (parent_id, child_id, ecosystem)
- `ApprovedIngredient` model (`db.py:295-309`): ecosystem column, mirror_status/mirror_path/mirror_log fields

### Established Patterns
- Async subprocess: `asyncio.to_thread(subprocess.run, cmd, capture_output=True, text=True)`
- Temp file management: `tempfile.NamedTemporaryFile` with cleanup in finally block
- Background task DB sessions: `async with AsyncSessionLocal()` (avoid parent session lifecycle issues)
- JSON subprocess output parsing with JSONDecodeError handling

### Integration Points
- `smelter_router.py`: add `/api/smelter/ingredients/{id}/resolve` endpoint
- `smelter_service.py:add_ingredient()`: chain resolution after mirroring
- `mirror_service.py:mirror_ingredient()`: call resolver first, then mirror entire tree
- `foundry_service.py:build_template()`: extend validation to walk IngredientDependency tree
- `compose.server.yaml`: remove devpi service
- `requirements.txt`: add pip-tools

</code_context>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 108-transitive-dependency-resolution*
*Context gathered: 2026-04-03*
