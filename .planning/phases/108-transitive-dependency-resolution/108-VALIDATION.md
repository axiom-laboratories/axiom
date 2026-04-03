---
phase: 108
slug: transitive-dependency-resolution
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-03
---

# Phase 108 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (existing, backend tests in puppeteer/tests/) |
| **Config file** | puppeteer/pytest.ini or pyproject.toml |
| **Quick run command** | `cd puppeteer && pytest tests/test_resolver.py -x -v` |
| **Full suite command** | `cd puppeteer && pytest tests/test_resolver.py tests/test_mirror.py tests/test_foundry.py -v` |
| **Estimated runtime** | ~30 seconds (unit), ~120 seconds (full with subprocess) |

---

## Sampling Rate

- **After every task commit:** Run `cd puppeteer && pytest tests/test_resolver.py tests/test_mirror.py -x`
- **After every plan wave:** Run `cd puppeteer && pytest tests/ -k "resolver or mirror or foundry" -v`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 120 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 108-01-01 | 01 | 0 | DEP-01 | unit | `pytest tests/test_resolver.py -x` | ❌ W0 | ⬜ pending |
| 108-01-02 | 01 | 1 | DEP-01 | unit | `pytest tests/test_resolver.py::test_resolve_creates_edges -x` | ❌ W0 | ⬜ pending |
| 108-01-03 | 01 | 1 | DEP-01 | unit | `pytest tests/test_resolver.py::test_circular_timeout -x` | ❌ W0 | ⬜ pending |
| 108-02-01 | 02 | 0 | DEP-01 | unit | `pytest tests/test_mirror.py -x` | ❌ W0 | ⬜ pending |
| 108-02-02 | 02 | 1 | DEP-01 | unit | `pytest tests/test_mirror.py::test_dual_platform_download -x` | ❌ W0 | ⬜ pending |
| 108-02-03 | 02 | 1 | DEP-01 | unit | `pytest tests/test_foundry.py::test_validate_tree -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_resolver.py` — stubs for resolver_service unit tests (pip-compile subprocess, output parsing, transitive edge creation, circular detection)
- [ ] `tests/test_mirror.py` — extended mirror tests (dual-platform download, pure-python detection, musllinux fallback to sdist)
- [ ] `tests/test_foundry.py` — extended build validation (walk IngredientDependency tree, fail if any dep not MIRRORED)
- [ ] `tests/conftest.py` — add fixtures for mock ApprovedIngredient + IngredientDependency seeding
- [ ] `pip-tools` added to `puppeteer/requirements.txt`

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| STRICT Foundry build succeeds air-gapped | DEP-01 | Requires Docker stack with no internet | Rebuild stack, disconnect network, run Foundry build for blueprint with mirrored packages |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 120s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
