---
phase: 31
slug: environment-tags-cicd-dispatch
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-18
---

# Phase 31 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (existing) |
| **Config file** | `puppeteer/pytest.ini` (or project root inference) |
| **Quick run command** | `cd puppeteer && pytest tests/test_env_tag.py -x` |
| **Full suite command** | `cd puppeteer && pytest` |
| **Estimated runtime** | ~30 seconds |

---

## Sampling Rate

- **After every task commit:** Run `cd puppeteer && pytest tests/test_env_tag.py -x`
- **After every plan wave:** Run `cd puppeteer && pytest`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 31-01-01 | 01 | 0 | ENVTAG-01 | unit | `cd puppeteer && pytest tests/test_env_tag.py::test_node_has_env_tag -x` | ❌ W0 | ⬜ pending |
| 31-01-02 | 01 | 0 | ENVTAG-01 | unit | `cd puppeteer && pytest tests/test_env_tag.py::test_job_has_env_tag -x` | ❌ W0 | ⬜ pending |
| 31-01-03 | 01 | 0 | ENVTAG-01 | unit | `cd puppeteer && pytest tests/test_env_tag.py::test_heartbeat_accepts_env_tag -x` | ❌ W0 | ⬜ pending |
| 31-02-01 | 02 | 0 | ENVTAG-02 | unit | `cd puppeteer && pytest tests/test_env_tag.py::test_pull_work_env_tag_mismatch_skipped -x` | ❌ W0 | ⬜ pending |
| 31-02-02 | 02 | 0 | ENVTAG-02 | unit | `cd puppeteer && pytest tests/test_env_tag.py::test_pull_work_env_tag_match_assigned -x` | ❌ W0 | ⬜ pending |
| 31-02-03 | 02 | 0 | ENVTAG-02 | unit | `cd puppeteer && pytest tests/test_env_tag.py::test_pull_work_no_env_tag_assigned -x` | ❌ W0 | ⬜ pending |
| 31-03-01 | 03 | 0 | ENVTAG-04 | unit | `cd puppeteer && pytest tests/test_env_tag.py::test_dispatch_request_model -x` | ❌ W0 | ⬜ pending |
| 31-03-02 | 03 | 0 | ENVTAG-04 | unit | `cd puppeteer && pytest tests/test_env_tag.py::test_dispatch_response_model -x` | ❌ W0 | ⬜ pending |
| 31-03-03 | 03 | 0 | ENVTAG-04 | unit | `cd puppeteer && pytest tests/test_env_tag.py::test_dispatch_status_response_model -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `puppeteer/tests/test_env_tag.py` — stubs covering ENVTAG-01, ENVTAG-02, ENVTAG-04 model assertions and source inspection tests
- [ ] No new fixture files needed — existing pytest patterns (model instantiation + `inspect.getsource`) are sufficient

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Node started with `ENV_TAG=PROD` env var reports tag in heartbeat payload and it persists in DB | ENVTAG-01 | Requires live Docker node + running stack | Start a local node with `ENV_TAG=PROD`, call `GET /nodes`, confirm `env_tag: "PROD"` in response |
| `POST /api/dispatch` end-to-end via service principal with a running PROD node | ENVTAG-04 | Full integration (SP auth + dispatch + poll) | Use `mop_validation/scripts/` pattern with SP credentials; poll until terminal |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
