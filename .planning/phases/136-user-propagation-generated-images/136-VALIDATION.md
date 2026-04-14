---
phase: 136
slug: user-propagation-generated-images
status: draft
nyquist_compliant: true
wave_0_complete: true
created: 2026-04-12
---

# Phase 136 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x |
| **Config file** | `puppeteer/pytest.ini` (or default discovery) |
| **Quick run command** | `cd puppeteer && pytest tests/test_foundry.py -x -q` |
| **Full suite command** | `cd puppeteer && pytest -x -q` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `cd puppeteer && pytest tests/test_foundry.py -x -q`
- **After every plan wave:** Run `cd puppeteer && pytest -x -q`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 136-01-01 | 01 | 1 | CONT-08 | unit | `cd puppeteer && pytest tests/test_foundry.py -x -q -k "test_user_injection"` | ❌ W0 | ⬜ pending |
| 136-01-02 | 01 | 1 | CONT-08 | unit | `cd puppeteer && pytest tests/test_foundry.py -x -q -k "test_windows_skip"` | ❌ W0 | ⬜ pending |
| 136-01-03 | 01 | 1 | CONT-08 | unit | `cd puppeteer && pytest tests/test_foundry.py -x -q -k "test_chown_user_placement"` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_foundry.py` — unit test stubs for CONT-08 (user injection per OS family, WINDOWS skip, chown+USER placement)

*Existing pytest infrastructure covers the framework; only new test file needed.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Built Foundry image runs as uid 1000 | CONT-08 | Requires Docker build + container exec | Build a template via Foundry API, then `docker run --rm <image> id` — confirm uid=1000(appuser) |
| Jobs execute as appuser in generated images | CONT-08 | Requires live stack + node enrollment | Dispatch job to node running generated image; check output for appuser context |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
