---
phase: 113
slug: script-analyzer
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-04
---

# Phase 113 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest with asyncio (existing) |
| **Config file** | `puppeteer/pyproject.toml` |
| **Quick run command** | `cd puppeteer && pytest tests/test_analyzer.py -v -k "not slow"` |
| **Full suite command** | `cd puppeteer && pytest tests/test_analyzer.py -v` |
| **Estimated runtime** | ~10 seconds |

---

## Sampling Rate

- **After every task commit:** Run `cd puppeteer && pytest tests/test_analyzer.py -v -k "not slow"`
- **After every plan wave:** Run `cd puppeteer && pytest tests/test_analyzer.py -v`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 10 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 113-01-01 | 01 | 1 | UX-01 | unit | `pytest tests/test_analyzer.py::test_python_ast_extraction -xvs` | ❌ W0 | ⬜ pending |
| 113-01-02 | 01 | 1 | UX-01 | unit | `pytest tests/test_analyzer.py::test_bash_package_extraction -xvs` | ❌ W0 | ⬜ pending |
| 113-01-03 | 01 | 1 | UX-01 | unit | `pytest tests/test_analyzer.py::test_powershell_module_extraction -xvs` | ❌ W0 | ⬜ pending |
| 113-01-04 | 01 | 1 | UX-01 | unit | `pytest tests/test_analyzer.py::test_language_auto_detection -xvs` | ❌ W0 | ⬜ pending |
| 113-01-05 | 01 | 1 | UX-01 | unit | `pytest tests/test_analyzer.py::test_stdlib_exclusion -xvs` | ❌ W0 | ⬜ pending |
| 113-01-06 | 01 | 1 | UX-01 | unit | `pytest tests/test_analyzer.py::test_malformed_script_handling -xvs` | ❌ W0 | ⬜ pending |
| 113-01-07 | 01 | 1 | UX-01 | integration | `pytest tests/test_analyzer.py::test_cross_reference_approved_ingredients -xvs` | ❌ W0 | ⬜ pending |
| 113-01-08 | 01 | 1 | UX-01 | integration | `pytest tests/test_analyzer.py::test_analyzer_endpoint_auth -xvs` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `puppeteer/tests/test_analyzer.py` — stubs for all unit + integration tests above
- [ ] Existing `conftest.py` covers fixtures — no new fixtures needed

*Existing infrastructure covers framework install.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| ScriptAnalyzerPanel renders in Smelter tab | UX-01 | UI visual check | Navigate to Foundry > Smelter, verify analyzer panel appears with textarea and language dropdown |
| Results table shows status badges correctly | UX-01 | Visual styling | Analyze a Python script, verify "new" vs "approved" badges render distinctly |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 10s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
