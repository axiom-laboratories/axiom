---
phase: 36-cython-so-build-pipeline
plan: "01"
subsystem: axiom-ee build system
tags: [cython, cibuildwheel, build, wheel, packaging]
dependency_graph:
  requires: []
  provides: [BUILD-01, BUILD-02, BUILD-03]
  affects: [axiom-ee wheel build, Plan 36-02 cibuildwheel execution]
tech_stack:
  added: [cython>=3.2.4, cibuildwheel, twine]
  patterns: [packages=[], BuildExtAndCopyInits hook, ext_modules glob pattern]
key_files:
  created:
    - ~/Development/axiom-ee/setup.py
    - ~/Development/axiom-ee/Makefile
  modified:
    - ~/Development/axiom-ee/pyproject.toml
    - ~/Development/axiom-ee/.gitignore
key_decisions:
  - "packages=[] strips .py source from wheel; __init__.py files copied back as namespace markers via BuildExtAndCopyInits hook"
  - "musllinux wheels included (not skipped) because Containerfile.server uses python:3.12-alpine (musl libc)"
  - "version bumped from 0.1.0.dev0 to 0.1.0 to produce release-quality wheel"
  - "nthreads=4 in cythonize() for parallel .c file generation during wheel build"
metrics:
  duration: "77 seconds"
  completed: "2026-03-20T11:12:43Z"
  tasks_completed: 2
  tasks_total: 2
  files_created: 2
  files_modified: 2
---

# Phase 36 Plan 01: Cython Build System Configuration Summary

**One-liner:** setup.py with cythonize() over 21 EE source files + cibuildwheel config targeting cp311/cp312/cp313 on amd64/aarch64/musllinux.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Create setup.py with Cython ext_modules and BuildExtAndCopyInits hook | 2aa1db2 | setup.py (created) |
| 2 | Update pyproject.toml + create Makefile + update .gitignore | ad71e05 | pyproject.toml, Makefile, .gitignore |

## What Was Built

**setup.py** (`~/Development/axiom-ee/setup.py`):
- Globs `ee/**/*.py` recursively, filters out `__init__.py` files, produces exactly 21 `Extension` objects
- `BuildExtAndCopyInits` subclasses `build_ext` — after `.so` compilation, copies all `ee/**/__init__.py` files into the build directory as plain Python namespace markers
- `packages=[]` ensures no `.py` source lands in the wheel; compiled `.so` files are the only code
- `language_level=3` directive for Cython 3.2.4 compatibility with `from __future__ import annotations`
- `nthreads=4` for parallel `.c` generation

**pyproject.toml** (`~/Development/axiom-ee/pyproject.toml`):
- `build-system.requires` gains `cython>=3.2.4` alongside `setuptools>=77.0`
- `version` bumped from `0.1.0.dev0` to `0.1.0`
- `[tool.cibuildwheel]`: builds `cp311-*`, `cp312-*`, `cp313-*`
- `[tool.cibuildwheel.linux]`: `archs = ["auto", "aarch64"]`, `manylinux_2_28` images for both
- musllinux variants are NOT skipped — required because `Containerfile.server` is `python:3.12-alpine` (musl libc)

**Makefile** (`~/Development/axiom-ee/Makefile`):
- `qemu-setup`: registers QEMU binfmt for aarch64 emulation (idempotent)
- `build`: depends on `qemu-setup`, runs `cibuildwheel --platform linux .`
- `upload`: twine upload to local devpi at `http://localhost:3141/root/dev/`
- `clean`: removes `wheelhouse/`, `build/`, `*.egg-info`, Cython C files and `.so` artifacts

**.gitignore** (`~/Development/axiom-ee/.gitignore`):
- Added `wheelhouse/` and `ee/**/*.c` to existing entries

## Verification Results

| Check | Result |
|-------|--------|
| SOURCES count == 21 | PASS |
| `__init__.py` excluded from SOURCES | PASS |
| `packages=[]` present in setup.py | PASS (count: 3 matches) |
| `version = "0.1.0"` in pyproject.toml | PASS |
| `cython>=3.2.4` in build-system.requires | PASS |
| `aarch64` in cibuildwheel config | PASS |
| `cp311` target present | PASS |
| Makefile exists with cibuildwheel | PASS |
| `.gitignore` has wheelhouse/ | PASS |

Note: `python setup.py --version` fails in current dev environment (Cython not installed locally) — expected. Cython is a build-time dependency provided by cibuildwheel inside its build container.

## Deviations from Plan

None — plan executed exactly as written.

## Self-Check: PASSED
