---
phase: 90
slug: job-script-versioning
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-29
---

# Phase 90 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x (backend) + vitest (frontend) |
| **Config file** | `puppeteer/pytest.ini` (backend), `puppeteer/dashboard/vite.config.ts` (frontend) |
| **Quick run command** | `cd puppeteer && pytest tests/test_scheduler.py -x -q` |
| **Full suite command** | `cd puppeteer && pytest -x -q` |
| **Frontend command** | `cd puppeteer/dashboard && npm run test` |
| **Estimated runtime** | ~30s (backend), ~15s (frontend) |

---

## Sampling Rate

- **After every task commit:** Run `cd puppeteer && pytest tests/test_scheduler.py -x -q`
- **After every plan wave:** Run `cd puppeteer && pytest -x -q && cd puppeteer/dashboard && npm run test`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 90-01-01 | 01 | 1 | VER-01 | unit | `cd puppeteer && pytest tests/test_scheduler.py -x -q` | ❌ W0 | ⬜ pending |
| 90-01-02 | 01 | 1 | VER-01 | unit | `cd puppeteer && pytest tests/test_scheduler.py -x -q` | ❌ W0 | ⬜ pending |
| 90-01-03 | 01 | 1 | VER-01 | unit | `cd puppeteer && pytest tests/test_scheduler.py::test_version_snapshot -x -q` | ❌ W0 | ⬜ pending |
| 90-01-04 | 01 | 1 | VER-03 | unit | `cd puppeteer && pytest tests/test_scheduler.py::test_dispatch_stamps_version -x -q` | ❌ W0 | ⬜ pending |
| 90-01-05 | 01 | 1 | VER-01,VER-02 | integration | `cd puppeteer && pytest tests/test_scheduler.py -x -q` | ❌ W0 | ⬜ pending |
| 90-01-06 | 01 | 1 | VER-02 | unit | `cd puppeteer && pytest tests/test_scheduler.py::test_version_endpoints -x -q` | ❌ W0 | ⬜ pending |
| 90-02-01 | 02 | 2 | VER-02 | manual | Visual: script viewer modal opens with correct content | N/A | ⬜ pending |
| 90-02-02 | 02 | 2 | VER-01,VER-03 | manual | Visual: history timeline shows version badges and change rows | N/A | ⬜ pending |
| 90-02-03 | 02 | 2 | VER-02,VER-03 | manual | Visual: Jobs.tsx "View script (vN)" opens correct version | N/A | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_scheduler.py` — extend with stubs for version snapshot tests (VER-01), dispatch stamping (VER-03), and version endpoint tests (VER-02)
- [ ] Shared fixtures for `ScheduledJob` and `JobDefinitionVersion` in `tests/conftest.py`

*Existing pytest infrastructure covers the runner. Wave 0 adds test stubs only.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Script viewer modal renders syntax highlighted content | VER-02 | UI rendering | Open job detail sheet, click "View script (vN)", verify modal shows script with syntax highlighting |
| Interleaved timeline shows version change rows | VER-01 | UI layout | Edit a job definition's script, open history tab, verify version change row appears above the first execution row |
| "Compare with previous" diff opens correctly | VER-01 | UI rendering | With 2+ versions, click "Compare with previous" in script viewer, verify side-by-side diff shows the actual diff |
| DRAFT badge on unsigned versions | VER-01 | UI state | Save script change without re-signing, verify DRAFT badge appears on the new version row in history |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
