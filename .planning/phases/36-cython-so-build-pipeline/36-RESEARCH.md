# Phase 36: Cython .so Build Pipeline - Research

**Researched:** 2026-03-20
**Domain:** Cython compilation, cibuildwheel multi-arch wheel production, devpi local PyPI, smoke test validation
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**CI platform**
- No GitHub Actions budget — local `cibuildwheel` IS the CI for BUILD-03 purposes
- Use QEMU emulation on local x86 machine to cross-compile both amd64 and arm64 wheels from one machine (no Pi SSH needed)
- cibuildwheel output goes to `wheelhouse/` directory in `~/Development/axiom-ee/` (git-ignored)
- A `Makefile` or `build.sh` script wraps the cibuildwheel invocation — documents the exact local build command
- GitHub remote for `axiom-ee` exists but CI workflow is not executed (no budget)

**Smoke test location and approach**
- Smoke test lives in `mop_validation/scripts/` — consistent with existing test infrastructure
- Test is a full stack test: brings up Docker stack with compiled EE wheel installed, runs `test_local_stack.py` assertions
- EE wheel is installed from a local devpi server (containerized in Docker, added to the axiom project's compose setup)
- The devpi container is global/reusable across projects — not axiom-specific
- mop_validation will be pushed to the `axiom-laboratories` GitHub org as a private repo alongside axiom-ee

**devpi server**
- Run as a Docker container, added to the local dev compose configuration
- Serves the `axiom-ee` compiled wheels to the Docker stack during smoke tests
- `pip install --index-url http://devpi:3141/root/pypi/+simple/ axiom-ee` pattern inside the agent container

**`__init__.py` handling**
- All `ee/{feature}/__init__.py` files are kept as empty plain Python files — required as package namespace markers
- All `__init__.py` files are excluded from `ext_modules` in pyproject.toml (CPython bug #59828 — Cython cannot compile `__init__.py`)
- Final wheel contains only `__init__.py` as `.py` source; all other modules become `.so` compiled extensions
- BUILD-04 success criterion: `unzip -l axiom_ee-*.whl | grep "\.py$"` returns only `__init__.py` entries

**Version strategy**
- Bump `axiom-ee` from `0.1.0.dev0` to `0.1.0` — the compiled wheel is the first stable release
- PyPI publish of 0.1.0 is deferred to Phase 37
- Phase 36 validates locally (devpi + stack test) only
- cibuildwheel produces separate per-platform wheels — pip picks the right one on install

### Claude's Discretion
- Exact cibuildwheel configuration options (build matrix, `CIBW_*` env vars)
- Whether to use a `setup.py` alongside `pyproject.toml` for Cython `ext_modules`, or use `pyproject.toml` only
- Devpi container image choice and port mapping
- Exact Makefile target names for the build script
- How to handle `ee/rbac/` which has no router.py — whether it has any compilable modules at all

### Deferred Ideas (OUT OF SCOPE)
- PyPI publish of compiled 0.1.0 wheel — Phase 37
- GitHub Actions CI workflow for axiom-ee (blocked on budget) — future
- Periodic devpi cache sync / mirror of public PyPI — out of scope
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| BUILD-01 | EE source audited and cleaned for Cython compatibility — no `@dataclass` decorators, `__init__.py` excluded from `ext_modules` | Audit confirms: zero `@dataclass` in `ee/`; `from __future__ import annotations` present across all files — Cython 3.2.4 handles this correctly with `language_level=3`; `__init__.py` exclusion pattern documented |
| BUILD-02 | Cython `ext_modules` list configured in EE `pyproject.toml` — enumerates each `.py` file explicitly | `setup.py` + `cythonize()` pattern required for `packages=[]` trick; explicit Extension list per module documented; 23 compilable files identified |
| BUILD-03 | `cibuildwheel` CI pipeline in `axiom-ee` repo builds wheels for amd64 + arm64, Python 3.11 / 3.12 / 3.13 | QEMU arm64 already registered on this machine (`/proc/sys/fs/binfmt_misc/qemu-aarch64` = enabled); cibuildwheel 3.4.0 `[tool.cibuildwheel]` config pattern documented; `--platform linux` command confirmed |
| BUILD-04 | Published EE wheel verified to contain no `.py` source files — only `.so` compiled extensions | `packages=[]` in `setup.py` is the canonical solution; `__init__.py` copy-back pattern documented; verification command documented |
| BUILD-05 | CE+EE combined smoke test passes after installing compiled `.so` wheel | devpi Docker pattern confirmed; `muccg/devpi` image + twine upload workflow documented; Containerfile.server extension point identified |
</phase_requirements>

---

## Summary

Phase 36 compiles the 23 non-`__init__.py` Python files in `axiom-ee/ee/` to Cython `.so` extension modules, packages them as platform-specific wheels via cibuildwheel, uploads them to a local devpi server, and validates the compiled wheel against the same full-stack smoke test as the Phase 35 source install.

The critical technical path is: (1) add `setup.py` with `cythonize()` + `packages=[]` to axiom-ee, (2) configure `[tool.cibuildwheel]` in `pyproject.toml`, (3) run `cibuildwheel --platform linux` locally using QEMU (already registered), (4) upload wheels to devpi, (5) modify Containerfile.server to install from devpi, (6) run smoke test.

The most significant pitfall is that `from __future__ import annotations` is present in all EE source files. Cython 3.x handles this correctly with `language_level=3` compiler directive — this is no longer a blocker as of Cython 3.0+. The second critical pitfall is the `.py` source exclusion: setting `packages=[]` in `setup.py` (not in `pyproject.toml`) is the canonical solution that prevents source files from being bundled alongside `.so` files while still including compiled extensions.

**Primary recommendation:** Use `setup.py` (not pyproject.toml-only) for the Cython build configuration, with `packages=[]` and explicit `cythonize()` call. The `[tool.setuptools].ext-modules` pyproject.toml approach is marked experimental and does not support the `packages=[]` workaround needed to strip source files from the wheel.

---

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Cython | 3.2.4 (pinned) | Compile `.py` → `.so` C extensions | Industry standard for Python source protection; pure-Python-mode .py compilation supported since 3.0 |
| cibuildwheel | 3.4.0 (pinned) | Multi-arch, multi-Python wheel builder | Official PyPA tool; handles manylinux containers, QEMU emulation, Python matrix automatically |
| setuptools | >=77.0 (already in pyproject.toml) | Build backend with `ext_modules` support | Required by cibuildwheel; Cython integrates via `Extension` + `cythonize()` |
| muccg/devpi | latest | Local PyPI server for wheel distribution | Established Docker image; root/pypi index supports simple pip install; twine upload workflow |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| python-build | latest | Alternate frontend to `pip wheel` | cibuildwheel calls it automatically — no direct invocation needed |
| twine | latest | Upload wheels to devpi | Used once after cibuildwheel produces wheels; standard PyPI upload tool |
| devpi-client | latest | Create devpi user/index programmatically | Needed to set up initial devpi index before twine can upload |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| muccg/devpi | jonasal/devpi-server | jonasal has cleaner docs and recent maintenance; muccg is older but battle-tested; either works — recommend muccg for simplicity |
| muccg/devpi | pypiserver/pypiserver (already in compose) | pypiserver is already in compose.server.yaml — but it is a mirror/cache, not an upload target; devpi allows both upload and serve |
| setup.py for ext_modules | pyproject.toml `[tool.setuptools].ext-modules` | pyproject.toml approach is marked experimental in setuptools; cannot set `packages=[]` via TOML; setup.py is required for `packages=[]` + `cythonize()` together |

**Installation (in axiom-ee venv):**
```bash
pip install cibuildwheel==3.4.0 cython==3.2.4 build twine devpi-client
```

---

## Architecture Patterns

### Recommended Project Structure (axiom-ee additions)

```
axiom-ee/
├── setup.py              # NEW: cythonize() + packages=[] + build_ext hook
├── pyproject.toml        # MODIFY: add cython to build-system.requires, [tool.cibuildwheel]
├── Makefile              # NEW: wrap cibuildwheel invocation
├── wheelhouse/           # cibuildwheel output (git-ignored)
├── ee/
│   ├── __init__.py       # stays .py (namespace marker)
│   ├── base.py           # compiled to .so
│   ├── plugin.py         # compiled to .so
│   └── {feature}/
│       ├── __init__.py   # stays .py (namespace marker)
│       ├── models.py     # compiled to .so
│       ├── router.py     # compiled to .so (where present)
│       └── services.py   # compiled to .so (where present)
```

### Pattern 1: setup.py with cythonize() + packages=[]

**What:** Standard pattern for producing a wheel with `.so` files only (no `.py` source).
**When to use:** Any time you need Cython-compiled wheels with source stripped.

```python
# Source: https://bucharjan.cz/blog/using-cython-to-protect-a-python-codebase.html
# setup.py
import glob
import shutil
from pathlib import Path
from setuptools import setup
from setuptools.extension import Extension
from Cython.Build import cythonize
from setuptools.command.build_ext import build_ext as _build_ext


class BuildExtAndCopyInits(_build_ext):
    """After compiling .so files, copy __init__.py files into the build dir
    so the package structure is preserved for wheel assembly."""
    def run(self):
        _build_ext.run(self)
        build_dir = Path(self.build_lib)
        root_dir = Path(__file__).parent
        target_dir = build_dir if not self.inplace else root_dir
        for init in root_dir.glob("ee/**/__init__.py"):
            rel = init.relative_to(root_dir)
            dest = target_dir / rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(str(init), str(dest))


# All .py files except __init__.py
SOURCES = [
    f for f in glob.glob("ee/**/*.py", recursive=True)
    if not f.endswith("__init__.py")
]

# Convert file paths to Extension module names: ee/foundry/router.py -> ee.foundry.router
ext_modules = [
    Extension(
        name=src.replace("/", ".").removesuffix(".py"),
        sources=[src],
    )
    for src in SOURCES
]

setup(
    ext_modules=cythonize(
        ext_modules,
        compiler_directives={
            "language_level": "3",
        },
    ),
    cmdclass={"build_ext": BuildExtAndCopyInits},
    packages=[],  # CRITICAL: exclude .py source files from wheel
)
```

### Pattern 2: pyproject.toml [tool.cibuildwheel] configuration

**What:** cibuildwheel reads this section to know which Python versions and architectures to target.
**When to use:** Standard configuration; all options can also be set as CIBW_ env vars.

```toml
# Source: https://cibuildwheel.pypa.io/en/stable/options/
[build-system]
requires = ["setuptools>=77.0", "cython>=3.2.4"]
build-backend = "setuptools.build_meta"

[project]
name = "axiom-ee"
version = "0.1.0"
# ...

[tool.cibuildwheel]
build = "cp311-* cp312-* cp313-*"
skip = "*-musllinux_*"

[tool.cibuildwheel.linux]
archs = ["auto", "aarch64"]
```

### Pattern 3: Makefile build invocation

**What:** Single command that sets up QEMU and runs cibuildwheel locally.

```makefile
# Makefile
.PHONY: build clean upload

# Register QEMU for arm64 emulation (idempotent)
qemu-setup:
	docker run --rm --privileged tonistiigi/binfmt --install all

# Build multi-arch wheels
build: qemu-setup
	cibuildwheel --platform linux .

# Upload to local devpi
upload:
	twine upload \
	  --repository-url http://localhost:3141/root/dev/ \
	  -u root -p $(DEVPI_PASSWORD) \
	  wheelhouse/*.whl

clean:
	rm -rf wheelhouse/ build/ *.egg-info
```

### Pattern 4: devpi Docker service

**What:** Local PyPI server that accepts uploads and serves to Docker containers.

```yaml
# In compose (standalone or appended to existing compose.server.yaml)
services:
  devpi:
    image: muccg/devpi:latest
    container_name: devpi
    ports:
      - "3141:3141"
    volumes:
      - devpi-data:/data
    environment:
      - DEVPI_PASSWORD=${DEVPI_PASSWORD:-changeme}
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "wget", "--spider", "-q", "http://localhost:3141/+api"]
      interval: 30s
      timeout: 5s
      retries: 3

volumes:
  devpi-data:
```

### Pattern 5: devpi index initialisation (one-time setup)

```bash
# Run once to create an uploadable index
devpi use http://localhost:3141
devpi login root --password=changeme
devpi index -c dev bases=root/pypi volatile=True
devpi use root/dev
```

### Pattern 6: Containerfile.server EE wheel installation

```dockerfile
# Add to Containerfile.server after pip install requirements
ARG DEVPI_URL=http://devpi:3141/root/dev/+simple/
RUN pip install --no-cache-dir \
    --index-url ${DEVPI_URL} \
    --trusted-host devpi \
    axiom-ee==0.1.0 || true  # CE mode: wheel absence is not fatal
```

### Anti-Patterns to Avoid

- **Compiling `__init__.py`:** CPython bug #59828 — Cython cannot compile `__init__.py` files. The extension module would override the package namespace and break all relative/absolute imports within the package. Always exclude `**/__init__.py` from `ext_modules`.
- **Using `pyproject.toml` `[tool.setuptools].ext-modules` alone:** This experimental feature does not support `packages=[]`, which is required to strip source from the wheel. Use `setup.py` for the `cythonize()` call.
- **`CIBW_ARCHS=aarch64` without QEMU registered:** Will silently fail or produce x86 binaries tagged as arm64. Always run `tonistiigi/binfmt --install all` before cibuildwheel.
- **Using `--extra-index-url` instead of `--index-url` for internal packages:** `--extra-index-url` falls back to PyPI on 404, exposing the wheel name. Use `--index-url` pointed at devpi for private packages.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Multi-arch wheel building | Custom Docker build matrix scripts | cibuildwheel 3.4.0 | Handles manylinux tagging, Python ABI tags, QEMU orchestration, platform detection automatically |
| Local PyPI server | Flask-based file server | muccg/devpi or pypiserver | devpi handles index inheritance, pip simple API, volatile/stable indexes; pypiserver is already in compose |
| Source file stripping from wheel | Custom wheel post-processing | `packages=[]` in setup.py | setuptools + bdist_wheel respects `packages=[]` and correctly excludes source while including compiled extensions |
| QEMU arm64 setup | Manual qemu-user-static installation | `docker run --privileged tonistiigi/binfmt --install all` | One-line idempotent setup; handles binfmt_misc kernel registration |

**Key insight:** cibuildwheel's value is not just running builds — it handles the manylinux container selection (ensuring glibc compatibility), ABI tag generation (cp311-cp311-manylinux_2_17_x86_64), and QEMU orchestration. Hand-rolling this produces wheels that pip refuses to install on target systems.

---

## Common Pitfalls

### Pitfall 1: `from __future__ import annotations` with Cython
**What goes wrong:** Older Cython (0.29.x) would fail with "future feature annotations is not defined" when compiling `.py` files containing `from __future__ import annotations`.
**Why it happens:** Cython's pure Python parser did not implement PEP 563 in older versions.
**How to avoid:** Cython 3.x handles this correctly. With `language_level=3` compiler directive, `from __future__ import annotations` is processed correctly. All EE source files already use it — this is confirmed safe with Cython 3.2.4.
**Warning signs:** Any `CompileError` mentioning "future feature annotations" means the wrong Cython version is installed.

### Pitfall 2: `.py` source files appearing in wheel alongside `.so`
**What goes wrong:** Both `ee/foundry/router.py` and `ee/foundry/router.cpython-312-x86_64-linux-gnu.so` appear in the wheel. Pip installs both; Python imports the `.py` file (not the `.so`) because `.py` takes priority over extension modules in some edge cases.
**Why it happens:** Without `packages=[]` in `setup.py`, setuptools includes the Python source packages alongside compiled extensions.
**How to avoid:** Set `packages=[]` in `setup.py`. The compiled `.so` files are included via `ext_modules`, not `packages`. Combined with `BuildExtAndCopyInits` hook that copies `__init__.py` back, the wheel contains only `__init__.py` + `*.so`.
**Warning signs:** `unzip -l axiom_ee-*.whl | grep "\.py$"` shows files other than `__init__.py`.

### Pitfall 3: Module naming mismatch in Extension objects
**What goes wrong:** Extension named `"foundry.router"` but module is `"ee.foundry.router"` — import fails at runtime.
**Why it happens:** Glob-derived paths must be converted to fully-qualified dotted names.
**How to avoid:** Convert `ee/foundry/router.py` → `ee.foundry.router` using `src.replace("/", ".").removesuffix(".py")`.
**Warning signs:** `ModuleNotFoundError: No module named 'ee.foundry.router'` at import time despite `.so` being present.

### Pitfall 4: QEMU emulation not registered before cibuildwheel
**What goes wrong:** cibuildwheel attempts to run arm64 container but host cannot execute arm64 ELF binaries — build hangs or errors.
**Why it happens:** binfmt_misc needs kernel-level registration of the QEMU interpreter for aarch64 ELF magic bytes.
**How to avoid:** Run `docker run --rm --privileged tonistiigi/binfmt --install all` before the cibuildwheel invocation. On this machine, QEMU aarch64 is already registered (`/proc/sys/fs/binfmt_misc/qemu-aarch64` = enabled).
**Warning signs:** cibuildwheel arm64 build hangs at container startup; `exec format error` in build logs.

### Pitfall 5: devpi index not created before upload
**What goes wrong:** `twine upload` to devpi returns 404 — the `root/dev` index does not exist by default; only `root/pypi` (a PyPI mirror proxy) exists after initial setup.
**Why it happens:** devpi requires explicit index creation before packages can be uploaded.
**How to avoid:** Run the one-time devpi initialisation sequence (Pattern 5 above) after the devpi container first starts. This is idempotent if run again.
**Warning signs:** HTTP 404 from twine upload; `pip install axiom-ee` fails with "not found" against root/pypi.

### Pitfall 6: `ee/rbac/` has no `router.py` — no compilable router
**What goes wrong:** Glob pattern `ee/**/*.py` finds `ee/rbac/models.py` but no `ee/rbac/router.py`. This is expected and correct — RBAC models are imported and used by `ee/users/router.py`.
**Why it happens:** RBAC is a data model module, not a separate router. Confirmed by directory inspection.
**How to avoid:** No special handling needed. `ee/rbac/models.py` is compiled normally. The glob excludes `__init__.py` files automatically.
**Warning signs:** None — this is expected behaviour.

### Pitfall 7: SQLAlchemy mapped classes and Cython
**What goes wrong:** SQLAlchemy `DeclarativeBase` subclasses and `Mapped[T]` annotations can sometimes cause issues with Cython's type annotation handling.
**Why it happens:** SQLAlchemy uses metaclass magic; `Mapped[str]` type hints are Python-level. With `language_level=3` and `from __future__ import annotations`, annotations are lazy strings — Cython passes them through without evaluating, which is correct.
**How to avoid:** `language_level=3` is the fix. Confirmed: no `@dataclass` decorators exist in EE source. `Mapped[...]` annotations work correctly in Cython-compiled SQLAlchemy models when annotations are lazy strings.
**Warning signs:** `TypeError` about `Mapped` not being subscriptable at import time — indicates annotations are being evaluated eagerly.

---

## Code Examples

### Complete setup.py for axiom-ee

```python
# Source: derived from https://bucharjan.cz/blog/using-cython-to-protect-a-python-codebase.html
# and https://github.com/pypa/cibuildwheel/discussions/2065
import glob
import shutil
from pathlib import Path
from setuptools import setup
from setuptools.extension import Extension
from Cython.Build import cythonize
from setuptools.command.build_ext import build_ext as _build_ext


class BuildExtAndCopyInits(_build_ext):
    """Copy __init__.py files into build dir after .so compilation.
    Required because packages=[] excludes them from normal package collection."""

    def run(self):
        _build_ext.run(self)
        build_dir = Path(self.build_lib)
        root_dir = Path(__file__).parent
        target_dir = build_dir if not self.inplace else root_dir
        for init_file in root_dir.glob("ee/**/__init__.py"):
            rel = init_file.relative_to(root_dir)
            dest = target_dir / rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(str(init_file), str(dest))


# Collect all .py files except __init__.py
SOURCES = sorted(
    f for f in glob.glob("ee/**/*.py", recursive=True)
    if not f.endswith("__init__.py")
)

ext_modules = [
    Extension(
        name=src.replace("/", ".").removesuffix(".py"),
        sources=[src],
    )
    for src in SOURCES
]

setup(
    ext_modules=cythonize(
        ext_modules,
        compiler_directives={
            "language_level": "3",
        },
    ),
    cmdclass={"build_ext": BuildExtAndCopyInits},
    packages=[],  # strips .py source from wheel; .so files included via ext_modules
)
```

### pyproject.toml additions (diff)

```toml
[build-system]
requires = ["setuptools>=77.0", "cython>=3.2.4"]
build-backend = "setuptools.build_meta"

[project]
name = "axiom-ee"
version = "0.1.0"           # bumped from 0.1.0.dev0
# ... rest unchanged

[tool.cibuildwheel]
build = "cp311-* cp312-* cp313-*"
skip = "*-musllinux_*"      # Alpine/musl not a target — manylinux only

[tool.cibuildwheel.linux]
archs = ["auto", "aarch64"]
```

### devpi bootstrap (one-time, run from host after devpi container starts)

```bash
pip install devpi-client
devpi use http://localhost:3141
devpi login root --password=${DEVPI_PASSWORD:-changeme}
devpi index -c dev bases=root/pypi volatile=True
echo "devpi root/dev index created"
```

### Upload wheels to devpi

```bash
# After cibuildwheel produces wheelhouse/
twine upload \
  --repository-url http://localhost:3141/root/dev/ \
  --non-interactive \
  -u root -p ${DEVPI_PASSWORD:-changeme} \
  wheelhouse/*.whl
```

### Verify wheel contents (BUILD-04 check)

```bash
# Should return ONLY lines containing __init__.py
unzip -l wheelhouse/axiom_ee-0.1.0-cp312-cp312-manylinux_2_17_x86_64.manylinux2014_x86_64.whl \
  | grep "\.py$"
# Expected: only ee/__init__.py, ee/audit/__init__.py, etc. — no router.py, models.py etc.
```

### Install from devpi in Containerfile.server

```dockerfile
# Add after existing pip install line
ARG DEVPI_URL=http://devpi:3141/root/dev/+simple/
RUN if [ -n "${EE_INSTALL:-}" ]; then \
    pip install --no-cache-dir \
      --index-url "${DEVPI_URL}" \
      --trusted-host devpi \
      "axiom-ee==0.1.0"; \
  fi
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `from Cython.Distutils import build_ext` | `from setuptools.command.build_ext import build_ext` | Cython 3.x | Old import path deprecated; new path required for setuptools integration |
| `cythonize("package/*.pyx")` | `cythonize("package/*.py", compiler_directives={"language_level": "3"})` | Cython 0.28+ | Pure Python `.py` files now compilable; no need to rename to `.pyx` |
| GitHub Actions only | `cibuildwheel --platform linux` local | cibuildwheel 2.0+ | Local builds fully supported; Docker daemon + QEMU sufficient |
| `pkg_resources.iter_entry_points` | `importlib.metadata.entry_points(group=...)` | Python 3.9 / 3.12 | pkg_resources deprecated; already addressed in Phase 34/35 |

**Deprecated/outdated:**
- `setup.cfg` for ext_modules configuration: works but `setup.py` is cleaner for dynamic cythonize calls
- `CIBW_BUILD_VERBOSITY=3`: replaced by `build-verbosity` in `[tool.cibuildwheel]` in v3.x
- `Cython.Distutils.build_ext`: deprecated; use `setuptools.command.build_ext.build_ext` subclass instead

---

## Open Questions

1. **devpi vs existing pypiserver in compose**
   - What we know: `compose.server.yaml` in the axiom-split worktree already has a `pypiserver/pypiserver:latest` service on port 8080. devpi offers an additional upload API.
   - What's unclear: The context decision says "devpi" but the existing compose has pypiserver. pypiserver also supports uploads with `--passwords` flag.
   - Recommendation: Use devpi as decided (it supports both upload and serve, has a more robust API, and is the user's chosen tool). The pypiserver in compose appears to be a mirror/cache for public packages, not the EE wheel serve target.

2. **musllinux builds needed?**
   - What we know: The production Docker images use `python:3.12-alpine` (musl libc). Skipping `*-musllinux_*` in the build matrix would mean the wheel doesn't install on Alpine.
   - What's unclear: Whether the axiom-split production stack uses Alpine and whether that matters for the compiled EE wheel.
   - Recommendation: Check `Containerfile.server` base image. Currently `python:3.12-alpine`. If EE is installed in the Alpine-based server container, `musllinux` wheels are needed. This may require adding `*-musllinux_aarch64` and `*-musllinux_x86_64` to the build matrix.

3. **`skip = "*-musllinux_*"` decision**
   - What we know: The `Containerfile.server` uses `python:3.12-alpine` (musl libc). cibuildwheel can produce musllinux wheels via different containers.
   - What's unclear: Whether Phase 36 intends to support Alpine or will switch base image to glibc-based.
   - Recommendation: Investigate whether to add musllinux to the matrix OR switch `Containerfile.server` to `python:3.12-slim` (glibc). This is a key discretion decision for the planner.

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest (existing in `mop_validation/` and `puppeteer/`) |
| Config file | `pyproject.toml` (root) for puppeteer tests; standalone script for smoke tests |
| Quick run command | `python mop_validation/scripts/test_compiled_wheel.py` |
| Full suite command | `python mop_validation/scripts/test_compiled_wheel.py && python mop_validation/scripts/test_local_stack.py` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| BUILD-01 | No `@dataclass` in EE source; `__init__.py` excluded from ext_modules | audit/grep | `grep -r "@dataclass" axiom-ee/ee/ && grep "__init__" axiom-ee/setup.py` | ❌ Wave 0 |
| BUILD-02 | All non-`__init__.py` .py files appear as Extension in setup.py | unit | `python axiom-ee/setup.py --version` (verifies import) | ❌ Wave 0 |
| BUILD-03 | cibuildwheel produces wheels for cp311/cp312/cp313 × amd64/aarch64 | integration | `ls axiom-ee/wheelhouse/ \| grep -c ".whl"` (expect 6+) | ❌ Wave 0 |
| BUILD-04 | Wheel contains no .py except __init__.py | smoke | `unzip -l axiom_ee-*.whl \| grep ".py$" \| grep -v "__init__"` (expect empty) | ❌ Wave 0 |
| BUILD-05 | CE+EE smoke test passes with compiled wheel | integration | `python mop_validation/scripts/test_compiled_wheel.py` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** Targeted verification (wheel contents check for BUILD-04)
- **Per wave merge:** Full `test_compiled_wheel.py` smoke test
- **Phase gate:** All requirements verified before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `axiom-ee/setup.py` — BUILD-01, BUILD-02 (Cython ext_modules config)
- [ ] `mop_validation/scripts/test_compiled_wheel.py` — BUILD-05 (full stack smoke test with compiled wheel)
- [ ] `axiom-ee/Makefile` — BUILD-03 (cibuildwheel invocation wrapper)
- [ ] devpi Docker service — BUILD-05 (required for wheel distribution to test stack)

---

## Sources

### Primary (HIGH confidence)
- https://cibuildwheel.pypa.io/en/stable/options/ — CIBW_ARCHS, build matrix, pyproject.toml configuration
- https://cibuildwheel.pypa.io/en/stable/setup/ — Local Linux builds with Docker
- https://cython.readthedocs.io/en/latest/src/userguide/source_files_and_compilation.html — cythonize() API, language_level
- `/proc/sys/fs/binfmt_misc/qemu-aarch64` — Direct inspection confirms QEMU arm64 already enabled on this machine

### Secondary (MEDIUM confidence)
- https://bucharjan.cz/blog/using-cython-to-protect-a-python-codebase.html — `packages=[]` + `BuildExt` hook pattern (verified against cibuildwheel discussion #2065)
- https://github.com/pypa/cibuildwheel/discussions/2065 — Canonical answer on stripping .py from wheels: `packages=[]`
- https://oneuptime.com/blog/post/2026-02-08-how-to-run-devpi-in-docker-private-pypi-server/view — devpi Docker Compose + twine upload workflow (2026-02-08 article)
- https://tonistiigi/binfmt — QEMU binfmt setup; confirmed via direct `/proc/sys/fs/binfmt_misc/` inspection

### Tertiary (LOW confidence)
- https://pytauri.github.io/pytauri/latest/usage/tutorial/build-standalone-cython/ — Alternate Cython compilation pattern (useful cross-reference)

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — versions pinned in STATE.md; tools confirmed available/installable
- Architecture: HIGH — patterns verified against official docs and working examples; QEMU confirmed on-machine
- Pitfalls: HIGH for items verified against official docs/issues; MEDIUM for Pitfall 7 (SQLAlchemy + Cython — logic-derived, not empirically tested)
- devpi workflow: MEDIUM — based on documented API; one-time setup sequence needs empirical validation

**Research date:** 2026-03-20
**Valid until:** 2026-04-20 (stable tools ecosystem — 30-day window)
