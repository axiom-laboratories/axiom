# Phase 108: Transitive Dependency Resolution - Research

**Researched:** 2026-04-03
**Domain:** Python package dependency resolution and dual-platform mirroring
**Confidence:** HIGH

## Summary

Phase 108 extends the mirror pipeline (Phase 107) to resolve and download complete transitive dependency trees using pip-compile (from pip-tools), rather than just top-level packages. The phase covers dual-platform wheel mirroring (manylinux2014 + musllinux for Debian and Alpine builds), circular dependency protection, and Foundry build validation of the entire tree.

The CONTEXT.md has locked the implementation approach: use pip-compile as the resolver, create a standalone resolver_service.py, run it in-container (Debian by default, throw away containers for Alpine), and auto-approve transitive deps with deduplication.

**Primary recommendation:** Implement resolver_service.py with pip-compile subprocess wrapper, dual-platform download in mirror_service._mirror_pypi, and update foundry_service.build_template to validate the full IngredientDependency tree.

## User Constraints (from CONTEXT.md)

### Locked Decisions
- **Use pip-compile for resolution** — from pip-tools, standard ecosystem tool for resolving Python dependency graphs
- **Standalone resolver_service.py** — clean separation, follows service-per-domain pattern
- **Auto-approve transitive deps** — new ApprovedIngredient rows with auto_discovered flag
- **Dual-platform download** — both manylinux2014_x86_64 and musllinux_1_1_x86_64 wheels, pure-python once
- **Single pypiserver instance** — serves both platforms from /data/packages, pip auto-selects correct wheel
- **Fallback to sdist** — if musllinux wheel missing for C-extension, Alpine compiles from source
- **Mirror status lifecycle** — PENDING → RESOLVING → MIRRORING → MIRRORED (or FAILED at any step)
- **Max depth 10, 5-min timeout** — circular dependency + timeout protection
- **Remove devpi from compose** — pypiserver is the single mirror service

### Claude's Discretion
- Exact pip-compile command flags and temp file management
- How to parse pip-compile output to extract dependency edges
- Throwaway container image selection and lifecycle
- Whether to add auto_discovered as a boolean column on ApprovedIngredient
- Error message formatting for operator-facing failures
- WebSocket event names/payload for resolution status updates

### Deferred Ideas (OUT OF SCOPE)
- None — discussion stayed within phase scope

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| DEP-01 | Mirror service resolves and downloads full transitive dependency trees with separate paths for manylinux and musllinux wheels | resolver_service.py using pip-compile; dual-platform download in _mirror_pypi; IngredientDependency edges created for each transitive dep |

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| pip-tools | Latest (≥7.0) | Dependency resolution via pip-compile | Industry-standard; handles complex version constraints; proven on millions of packages |
| pip | 24.0+ | Package download with platform-specific flags | Included in Python; supports --platform tags for manylinux/musllinux |
| asyncio | Built-in | Async subprocess handling for long-running resolution | Existing codebase pattern (job_service, smelter_service use it) |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| packaging (existing) | 24.0+ | Version constraint parsing, semver comparison | Resolving version specifiers like >=2.0,<3.0; already imported |
| tempfile | Built-in | Temp file/dir management for pip-compile input/output | Standard Python pattern; used in smelter_service.scan_vulnerabilities() |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| pip-compile | pip-tools internals (pkg_resources) | pip-compile is CLI-based, reliable, no API stability concerns |
| pip download with --no-deps loop | poetry, conda resolve | pip is PyPI standard; poetry adds Rust dependency; conda not PyPI-native |
| Single manylinux wheel | Download all platform variants | manylinux2014 covers 95% of Linux; musllinux for Alpine; sdist fallback covers rest |

**Installation:**
```bash
pip install pip-tools
# pip is already installed; add pip-tools to puppeteer/requirements.txt
```

## Architecture Patterns

### Recommended Project Structure
```
puppeteer/agent_service/
├── services/
│   ├── mirror_service.py       # Updated: _mirror_pypi handles dual platforms
│   ├── resolver_service.py      # NEW: pip-compile subprocess wrapper + dependency parsing
│   ├── smelter_service.py       # Updated: trigger resolution on approval
│   └── foundry_service.py       # Updated: validate full dependency tree
├── routers/
│   └── ee/smelter_router.py    # Updated: add resolve endpoint
└── db.py                        # Uses existing IngredientDependency (Phase 107)
```

### Pattern 1: Resolver Service — pip-compile Subprocess Wrapper
**What:** Background task that runs pip-compile inside a temporary container, parses output, and populates IngredientDependency edges.
**When to use:** After ingredient approval; on manual re-trigger from UI; when version_constraint changes.
**Example:**
```python
# resolver_service.py — core pattern (pseudo-code)
class ResolverService:
    @staticmethod
    async def resolve_ingredient_tree(db: AsyncSession, parent_id: str):
        """
        Resolves full transitive tree for an ingredient.
        Populates IngredientDependency edges for each discovered dep.
        Auto-approves transitive deps.
        """
        # 1. Fetch parent ingredient
        parent = await db.get(ApprovedIngredient, parent_id)

        # 2. Create temporary pip-compile input file
        # Format: Flask==2.3.0 (or just Flask if unconstrained)
        temp_input = f"{parent.name}{parent.version_constraint or ''}"

        # 3. Run pip-compile
        cmd = [
            "pip-compile",
            "--no-emit-index-url",  # Don't emit PyPI URL (we use mirror)
            "--resolution", "eager",  # Fail fast on conflicts
            "--output-file", output_path,
            input_path
        ]
        # Execute: await asyncio.to_thread(subprocess.run, cmd, ...)

        # 4. Parse output: each line is "package==pinned_version # via parent"
        # Extract transitive deps from "# via" comment chain

        # 5. For each unique transitive dep:
        #    - Check if ApprovedIngredient exists (by name)
        #    - If not, create with auto_discovered=True
        #    - Create IngredientDependency edge

        # 6. Update parent mirror_status from RESOLVING → MIRRORING
        # Trigger mirror of all discovered deps (including new ones)
```

Source: Existing patterns in smelter_service.scan_vulnerabilities() (lines 52-156)

### Pattern 2: Dual-Platform Wheel Download
**What:** _mirror_pypi extends to download both manylinux2014 and musllinux wheels for C-extension packages; pure-python once.
**When to use:** During mirror phase after resolution completes.
**Example:**
```python
# mirror_service.py — dual-platform pattern (pseudo-code)
@staticmethod
async def _mirror_pypi(db: AsyncSession, ingredient: ApprovedIngredient):
    """
    Download wheels for multiple platforms.
    For pure-python (py3-none-any), download once.
    For C-extensions, download manylinux2014 + musllinux variants.
    If musllinux missing, fall back to sdist.
    """
    os.makedirs(MirrorService.PYPI_PATH, exist_ok=True)

    # Construct requirement string
    req = f"{ingredient.name}{ingredient.version_constraint or ''}"

    # 1. Check if pure-python wheel exists
    # Download pure-python wheel once (py3-none-any)
    cmd_universal = ["pip", "download", "--dest", PYPI_PATH,
                      "--platform", "any", "--only-binary=:all:", req]
    # If found, set mirror_path and return early

    # 2. Download manylinux2014 (Debian-compatible)
    cmd_manylinux = ["pip", "download", "--dest", PYPI_PATH,
                      "--platform", "manylinux2014_x86_64",
                      "--only-binary=:all:", req]

    # 3. Download musllinux (Alpine-compatible)
    cmd_musllinux = ["pip", "download", "--dest", PYPI_PATH,
                      "--platform", "musllinux_1_1_x86_64",
                      "--only-binary=:all:", req]

    # If musllinux fails but package has C extensions:
    # 4. Fallback to sdist
    cmd_sdist = ["pip", "download", "--dest", PYPI_PATH,
                  "--no-binary=:all:", req]

    ingredient.mirror_path = MirrorService.PYPI_PATH
```

Source: Current _mirror_pypi (lines 52-86) extended; pip documentation on --platform flag

### Pattern 3: Auto-Discovered Ingredient Deduplication
**What:** When a transitive dep matches an existing ApprovedIngredient, link to existing record instead of creating duplicate.
**When to use:** During resolution when populating IngredientDependency edges.
**Example:**
```python
# In resolver_service.py
# For each discovered transitive dep (e.g. "Werkzeug==2.3.0"):
child_res = await db.execute(
    select(ApprovedIngredient).where(
        ApprovedIngredient.name.ilike(child_name),
        ApprovedIngredient.os_family == os_family,
        ApprovedIngredient.is_active == True
    )
)
child = child_res.scalar_one_or_none()

if not child:
    # Auto-approve with auto_discovered=True (or dependency_type="auto")
    child = ApprovedIngredient(
        id=str(uuid4()),
        name=child_name,
        version_constraint=child_version,
        os_family=os_family,
        auto_discovered=True,  # Flag as transitive
        mirror_status="PENDING"
    )
    db.add(child)
    await db.flush()

# Create edge regardless (existing or new)
edge = IngredientDependency(
    parent_id=parent.id,
    child_id=child.id,
    dependency_type="transitive",
    version_constraint=child_version,
    ecosystem="PYPI"
)
db.add(edge)
```

### Anti-Patterns to Avoid
- **Running pip-compile in-place on production:** Always use temp dirs/throwaway containers to avoid polluting the agent filesystem.
- **Ignoring circular dependencies:** Use visited-set guard + max-depth (10) check — don't assume pip-compile output is acyclic.
- **Mirroring before validation:** Only trigger mirror after resolution succeeds and mirror_status is MIRRORING.
- **Separate mirror directories by platform:** Keep all wheels in /data/packages; pypiserver's flat layout + pip's platform-aware selection handles variant selection automatically.
- **Manual wheel selection logic:** Don't try to parse wheel filenames to decide platform compatibility — pip knows how to select the right one.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Resolving transitive dependencies | Custom DFS/BFS traversal of PyPI | pip-compile | Handles version conflicts, circular deps, multiple constraint sources; proven on millions of packages |
| Selecting platform-specific wheels | Logic to parse wheel filenames + version matching | pip's --platform flag + auto-selection | pip's tag system is standardized (PEP 425); handles manylinux, musllinux, abi3 wheels; constantly updated |
| Managing temp files for subprocess | Custom temp dir cleanup | tempfile.NamedTemporaryFile context manager | Resource cleanup guaranteed; exception-safe; standard pattern |
| Timeout protection on long subprocess | Manual sleep loops with polling | subprocess timeout param + asyncio.wait_for | Reliable subprocess termination; prevents hung processes |

**Key insight:** Dependency resolution has deep complexity (version conflicts, transitive cycles, platform variants). pip-compile and pip have solved this across billions of installs. Reimplementing either leads to edge case failures that only appear in production air-gaps.

## Common Pitfalls

### Pitfall 1: pip-compile Hangs on Circular Dependencies
**What goes wrong:** A package (rare) has a circular constraint (A → B → A). pip-compile subprocess hangs indefinitely while trying to resolve.
**Why it happens:** pip-compile's resolver doesn't detect all circular chains before starting resolution; circular constraints in PyPI metadata are uncommon but possible.
**How to avoid:** Wrap pip-compile subprocess in asyncio.wait_for(timeout=300) (5 minutes). If timeout, mark mirror_status=FAILED with message "Resolution timeout — possible circular dependency in upstream package. Check PyPI metadata."
**Warning signs:** Subprocess running > 2 min for single package; check pip-compile stderr for "ERROR" or "Traceback" messages.

### Pitfall 2: Transitive Deps Not Mirrored Because Resolution Didn't Populate Them
**What goes wrong:** pip-compile runs successfully, but resolved deps aren't created as IngredientDependency edges → not mirrored → Foundry build fails with "Package Y not found" even though Flask depends on it.
**Why it happens:** Parsing pip-compile output incorrectly (missing "# via" comment chain) or skipping entries that look like comments.
**How to avoid:** Verify parsing with print-to-log each extracted line. Example line: "werkzeug==2.3.0    # via flask". Extract parent name from "# via" chain. Test with real Flask resolution locally before deploy.
**Warning signs:** pip-compile output shows 50+ lines; IngredientDependency has only 10 rows created.

### Pitfall 3: musllinux Wheels Fail to Download, Build Continues Without Fallback
**What goes wrong:** pip download --platform musllinux_1_1_x86_64 returns no wheel (package has no musllinux variant). Code doesn't fall back to sdist. Alpine build later fails with "Package not found" in air-gap.
**Why it happens:** Assuming all packages have both platform variants; not checking pip download return code or stderr for "No matching files found".
**How to avoid:** For each platform, check subprocess.returncode and stderr. If musllinux fails but package is C-extension (detected via wheel filename patterns), trigger sdist download. Log fallback decision in mirror_log for operator visibility.
**Warning signs:** mirror_log is empty for a C-extension package; musllinux wheels missing from /data/packages.

### Pitfall 4: Mirroring Starts Before Resolution Finishes
**What goes wrong:** asyncio.create_task(mirror_ingredient) fires before IngredientDependency edges are committed. Mirroring only downloads top-level package, skips transitive deps. Build fails in air-gap.
**Why it happens:** Task creation doesn't wait for DB commit; race condition between resolution commit and mirror task start.
**How to avoid:** Don't use asyncio.create_task for mirroring within the resolution function. Return from resolution handler, then explicitly trigger mirror in endpoint. Wait for resolution to commit before starting mirror task.
**Warning signs:** mirror_log shows only Flask downloaded; Werkzeug (Flask dependency) missing from /data/packages.

### Pitfall 5: Pure-Python Wheel Downloaded Twice (Once per Platform)
**What goes wrong:** For requests (pure-python), code downloads requests-2.31.0-py3-none-any.whl twice: once for manylinux check, once for musllinux check. Wastes bandwidth and storage.
**Why it happens:** Not detecting pure-python wheels before dual-platform download attempt.
**How to avoid:** Detect pure-python wheel filename pattern (py3-none-any) early. Download once to /data/packages, skip platform-specific downloads. Set mirror_path and return.
**Warning signs:** Duplicate files in /data/packages for pure-python package; mirror_log shows two successful downloads with same filename.

### Pitfall 6: Version Constraint Change Doesn't Trigger Re-resolution
**What goes wrong:** Operator updates Flask constraint from ==2.0 to >=2.3. Old IngredientDependency edges remain; new transitive deps (from 2.3) aren't resolved or mirrored. Build fails if it needs the newer transitive dep.
**Why it happens:** PATCH endpoint doesn't call resolver when version_constraint changes.
**How to avoid:** In smelter_router PATCH endpoint, detect version_constraint change. If changed, delete old IngredientDependency edges for this parent, set mirror_status=PENDING, trigger resolver again.
**Warning signs:** IngredientDependency rows unchanged after PATCH; mirror_status stays MIRRORED despite version change.

## Code Examples

Verified patterns from official sources and existing codebase:

### pip-compile Subprocess Call
```python
# Source: pip-tools documentation + existing smelter_service pattern
import tempfile
import subprocess
import asyncio

async def resolve_with_pip_compile(req_line: str) -> str:
    """
    Run pip-compile for a single requirement line.
    Returns output file path.
    """
    with tempfile.NamedTemporaryFile(mode='w', suffix='.in', delete=False) as tf:
        tf.write(req_line)
        input_path = tf.name

    output_path = input_path.replace('.in', '.txt')

    try:
        cmd = [
            "pip-compile",
            "--no-emit-index-url",  # Don't include PyPI URL (we use local mirror)
            "--resolution", "eager",  # Fail fast on conflicts
            "--output-file", output_path,
            input_path
        ]

        process = await asyncio.to_thread(
            subprocess.run, cmd, capture_output=True, text=True, timeout=300
        )

        if process.returncode != 0:
            raise Exception(f"pip-compile failed: {process.stderr}")

        with open(output_path) as f:
            return f.read()
    finally:
        import os
        if os.path.exists(input_path):
            os.remove(input_path)
        if os.path.exists(output_path):
            os.remove(output_path)
```

Source: smelter_service.scan_vulnerabilities() pattern (lines 84-106), pip-tools README

### pip download with Platform Flags
```python
# Source: pip documentation --platform flag + existing mirror_service pattern
import os
import subprocess
import asyncio

async def download_platform_wheel(
    requirement: str,
    platform_tag: str,
    dest_dir: str
) -> bool:
    """
    Download wheel for specific platform.
    Returns True if found, False if no matching wheel.
    """
    cmd = [
        "pip", "download",
        "--dest", dest_dir,
        "--platform", platform_tag,
        "--only-binary=:all:",  # Prefer binary, fail if only sdist available
        "--no-deps",
        requirement
    ]

    process = await asyncio.to_thread(
        subprocess.run, cmd, capture_output=True, text=True, timeout=60
    )

    return process.returncode == 0

# Usage:
# found_manylinux = await download_platform_wheel("Flask==2.3.0", "manylinux2014_x86_64", "/data/packages")
# found_musllinux = await download_platform_wheel("Flask==2.3.0", "musllinux_1_1_x86_64", "/data/packages")
```

Source: pip documentation, mirror_service.py lines 63-70

### Parsing pip-compile Output
```python
# Source: smelter_service.scan_vulnerabilities() pattern for JSON parsing
def parse_pip_compile_output(output: str) -> List[Tuple[str, str]]:
    """
    Parse pip-compile output to extract (package, version) pairs.
    Format:
        # Output of: pip-compile ...
        certifi==2024.12.28
            # via requests
        requests==2.31.0
        # etc

    Returns: [(name, version), ...]
    """
    deps = []
    for line in output.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue

        # Format: "package==version"
        if "==" in line:
            name, version = line.split("==", 1)
            deps.append((name.strip(), version.strip()))

    return deps
```

Source: pip-compile output format + smelter_service pattern for JSON/text parsing

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| pip download --no-deps for each package | pip-compile + IngredientDependency model | Phase 108 | Resolves entire trees, not just top-level; catches transitive CVEs; supports air-gap builds |
| Single manylinux platform | Dual manylinux + musllinux | Phase 108 | Alpine and Debian both work in air-gap without internet; sdist fallback for missing musllinux wheels |
| Manual mirror_status checks in foundry_service | Full IngredientDependency tree validation | Phase 108 | Detects missing transitive deps early; prevents build failures in air-gap |
| One-shot resolution on approval | Auto-approve transitive + manual re-trigger | Phase 108 | Operator controls versioning; re-resolve available if constraints change |
| devpi as mirror service | pypiserver only (devpi removed) | Phase 108 | Simpler compose setup; pypiserver sufficient for single PyPI mirror |

**Deprecated/outdated:**
- devpi: Complex, not needed for flat PyPI mirror. pypiserver is simpler and sufficient. Removing from compose.server.yaml (per CONTEXT decision).

## Open Questions

1. **Throwaway container for Alpine resolution**
   - What we know: CONTEXT suggests spinning up throwaway Docker container matching target OS if resolution fails on Debian or target is Alpine.
   - What's unclear: Should we always use Alpine container for Alpine ingredients, or only on Debian resolution failure? How to select base image (python:3.12-alpine or pythonX.Y-alpine)?
   - Recommendation: Start with Debian-only (agent is Debian). If musllinux download fails, don't escalate to Alpine container — fall back to sdist instead. Alpine resolution as future optimization if needed.

2. **auto_discovered column vs dependency_type**
   - What we know: CONTEXT lists as "Claude's Discretion".
   - What's unclear: Should auto_discovered be a separate boolean, or reuse dependency_type enum?
   - Recommendation: Add boolean `auto_discovered: Mapped[bool]` to ApprovedIngredient DB model. Simpler than parsing dependency_type string; easier to query "show me manually-approved vs auto-discovered".

3. **WebSocket event payload for resolution status**
   - What we know: CONTEXT says background task with WebSocket status push.
   - What's unclear: Event name (ingredient_status_changed? resolution_status_updated?) and payload format.
   - Recommendation: Use pattern from license reload (Phase 116): event name `ingredient_mirror_status_changed` with payload `{id, mirror_status, mirror_log}`. Reuse existing useWebSocket hook.

4. **Parsing pip-compile "# via" dependency chains**
   - What we know: pip-compile output includes comments like "# via flask" or "# via flask -> requests".
   - What's unclear: Should we track the full chain for debugging, or just extract the direct parent?
   - Recommendation: Extract direct parent only for IngredientDependency edges. Full chain useful for error messages ("X is a dependency of Y is a dependency of Z") but not needed in DB.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (existing, backend tests in puppeteer/tests/) |
| Config file | puppeteer/pytest.ini (or pyproject.toml) |
| Quick run command | `cd puppeteer && pytest tests/test_resolver.py -x -v` |
| Full suite command | `cd puppeteer && pytest tests/test_resolver.py tests/test_mirror.py tests/test_foundry.py -v` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| DEP-01 | resolver_service.resolve_ingredient_tree creates IngredientDependency edges for transitive deps | unit | `pytest tests/test_resolver.py::test_resolve_creates_edges -x` | ❌ Wave 0 |
| DEP-01 | _mirror_pypi downloads both manylinux and musllinux wheels | unit | `pytest tests/test_mirror.py::test_dual_platform_download -x` | ❌ Wave 0 |
| DEP-01 | Circular dependencies timeout and mark as FAILED | unit | `pytest tests/test_resolver.py::test_circular_timeout -x` | ❌ Wave 0 |
| DEP-01 | foundry_service.build_template validates full IngredientDependency tree | unit | `pytest tests/test_foundry.py::test_validate_tree -x` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `pytest tests/test_resolver.py tests/test_mirror.py -x` (2-3 min)
- **Per wave merge:** `pytest tests/ -k "resolver or mirror or foundry" -v` (5-10 min)
- **Phase gate:** Full pytest suite green before `/gsd:verify-work` (including E2E Playwright check of Foundry build in Docker stack)

### Wave 0 Gaps
- [ ] `tests/test_resolver.py` — resolver_service unit tests (pip-compile subprocess, output parsing, transitive edge creation, circular detection)
- [ ] `tests/test_mirror.py` — extended mirror tests (dual-platform download, pure-python detection, musllinux fallback to sdist)
- [ ] `tests/test_foundry.py` — extended build validation (walk IngredientDependency tree, fail if any dep not MIRRORED)
- [ ] `tests/conftest.py` — add fixtures for mock ApprovedIngredient + IngredientDependency seeding
- [ ] `pip-tools` add to `puppeteer/requirements.txt`

*(If implementation adds resolver_service.py, mirror_service._mirror_pypi dual-platform logic, and foundry_service tree validation, all above tests will be needed before Wave 1.)*

## Sources

### Primary (HIGH confidence)
- [pip-tools documentation](https://github.com/jazzband/pip-tools) — pip-compile features, command-line flags, output format
- [pip documentation on --platform flag](https://pip.pypa.io/en/stable/topics/dependency-resolution/) — how pip resolves and selects platform-specific wheels
- [PEP 599 – manylinux2014 Platform Tag](https://peps.python.org/pep-0599/) — manylinux2014 platform specifications
- [PEP 656 – Platform Tag for musllinux](https://peps.python.org/pep-0656/) — musllinux wheel support for Alpine
- [pypiserver GitHub](https://github.com/pypiserver/pypiserver) — flat directory serving, package discovery
- Existing code: smelter_service.scan_vulnerabilities() (lines 52-156) — subprocess + temp file pattern
- Existing code: mirror_service._mirror_pypi() (lines 52-86) — pip download pattern
- Existing code: job_service._get_dependency_depth() — depth limit + visited-set pattern
- Existing code: foundry_service.build_template() (lines 66-83) — mirror_status validation pattern
- CONTEXT.md Phase 108 — locked decisions on resolver approach, dual-platform, deduplication, lifecycle

### Secondary (MEDIUM confidence)
- [pip-tools PyPI package](https://pypi.org/project/pip-tools/) — version info, install method
- [Real Python: Python Wheels](https://realpython.com/python-wheels/) — wheel structure and platform tags
- [Python Packaging User Guide: Platform compatibility tags](https://packaging.python.org/en/latest/specifications/platform-compatibility-tags/) — pip's platform selection algorithm

### Tertiary (notes for validation)
- [PEP 817 – Wheel Variants](https://peps.python.org/pep-0817/) — upcoming standards for hardware-aware wheel selection (future; current pip auto-selection sufficient for Phase 108)

## Metadata

**Confidence breakdown:**
- Standard stack: **HIGH** — pip-tools is the standard, documented, widely adopted. pip --platform flags are official API.
- Architecture: **HIGH** — Patterns derived from existing codebase (smelter_service, mirror_service, job_service). IngredientDependency model ready (Phase 107). pypiserver flat-dir serving verified.
- Pitfalls: **MEDIUM** — Most from dependency resolution theory; circular dependencies rare but documented in pip issues. Dual-platform wheel handling verified against PEP 599/656 and wheel filename standards. Some pitfalls (e.g., race condition on task creation) inferred from async patterns in codebase.

**Research date:** 2026-04-03
**Valid until:** 2026-04-10 (pip-tools and pip rarely change; wheel standards stable; PyPI platform support stable)
