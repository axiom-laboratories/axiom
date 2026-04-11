---
phase: 129
slug: response-model-auto-serialization
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-11
---

# Phase 129 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.x |
| **Config file** | `puppeteer/tests/conftest.py` |
| **Quick run command** | `cd puppeteer && pytest tests/test_models_core.py tests/test_jobs_responses.py tests/test_nodes_responses.py tests/test_admin_responses.py tests/test_foundry_responses.py -x` |
| **Full suite command** | `cd puppeteer && pytest` |
| **Estimated runtime** | ~30 seconds |

---

## Sampling Rate

- **After every task commit:** Run `cd puppeteer && pytest tests/test_{domain}_responses.py -x`
- **After every plan wave:** Run `cd puppeteer && pytest`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 129-01-01 | 01 | 1 | Core models | unit | `pytest tests/test_models_core.py -x` | ❌ W0 | ⬜ pending |
| 129-02-01 | 02 | 2 | Jobs response models | integration | `pytest tests/test_jobs_responses.py -x` | ❌ W0 | ⬜ pending |
| 129-03-01 | 03 | 2 | Nodes response models | integration | `pytest tests/test_nodes_responses.py -x` | ❌ W0 | ⬜ pending |
| 129-04-01 | 04 | 2 | Admin/Auth response models | integration | `pytest tests/test_admin_responses.py -x` | ❌ W0 | ⬜ pending |
| 129-05-01 | 05 | 2 | Foundry/System response models | integration | `pytest tests/test_foundry_responses.py -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_models_core.py` — unit tests for ActionResponse, PaginatedResponse[T], ErrorResponse serialization
- [ ] `tests/test_jobs_responses.py` — integration snapshot tests for Jobs domain routes
- [ ] `tests/test_nodes_responses.py` — integration snapshot tests for Nodes domain routes
- [ ] `tests/test_admin_responses.py` — integration snapshot tests for Admin/Auth routes
- [ ] `tests/test_foundry_responses.py` — integration snapshot tests for Foundry/Smelter/System routes
- [ ] Pydantic v2 Generic import verified in models.py

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| OpenAPI docs quality | Documentation | Visual inspection | Browse `/docs`, verify descriptions and examples render on 5 sample routes |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
