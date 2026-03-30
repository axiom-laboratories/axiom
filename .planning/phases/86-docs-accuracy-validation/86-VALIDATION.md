---
phase: 86
slug: docs-accuracy-validation
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-29
---

# Phase 86 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (existing backend suite) + direct script invocation |
| **Config file** | `puppeteer/pytest.ini` |
| **Quick run command** | `cd puppeteer && pytest tests/ -x -q` |
| **Full suite command** | `cd puppeteer && pytest tests/` |
| **Estimated runtime** | ~30 seconds (pytest) + ~5 seconds (validate_docs.py) |

---

## Sampling Rate

- **After every task commit:** Run `cd puppeteer && pytest tests/ -x -q`
- **After every plan wave:** Run `cd puppeteer && pytest tests/`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 35 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 86-01-01 | 01 | 1 | DOC-01 | syntax | `python -m py_compile tools/generate_openapi.py` | ❌ W0 | ⬜ pending |
| 86-01-02 | 01 | 1 | DOC-01,DOC-02 | syntax | `python -m py_compile tools/validate_docs.py` | ❌ W0 | ⬜ pending |
| 86-01-03 | 01 | 2 | DOC-01 | manual | `python tools/generate_openapi.py --url http://localhost:8080` | ❌ W0 | ⬜ pending |
| 86-01-04 | 01 | 2 | DOC-01,DOC-02 | smoke | `python tools/validate_docs.py` | ❌ W0 | ⬜ pending |
| 86-02-01 | 02 | 3 | DOC-03 | file | `grep -q docs-validate .github/workflows/ci.yml` | ✅ | ⬜ pending |
| 86-02-02 | 02 | 3 | DOC-03 | manual | Push branch to GitHub, verify CI passes | ✅ | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tools/generate_openapi.py` — must be created by Plan 86-01 Task 1
- [ ] `tools/validate_docs.py` — must be created by Plan 86-01 Task 2

*These are deliverables, not test infrastructure. No separate Wave 0 test scaffold is needed — the scripts themselves are the artifacts under test. Existing pytest suite covers backend regression.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| `generate_openapi.py` populates openapi.json with real routes | DOC-01 | Requires live Docker stack | Run `python tools/generate_openapi.py --url http://localhost:8080`, verify `openapi.json` has >0 paths |
| `validate_docs.py` produces correct PASS/WARN/FAIL output | DOC-01,DOC-02 | Requires populated snapshot | Run `python tools/validate_docs.py` and review output for accuracy |
| CI gate blocks a PR that introduces a bad route reference | DOC-03 | Requires GitHub Actions run | Add a fake `GET /api/nonexistent` to a docs file, open PR, verify CI fails |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 35s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
