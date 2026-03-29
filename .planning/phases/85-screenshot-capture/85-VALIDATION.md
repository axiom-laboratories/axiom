---
phase: 85
slug: screenshot-capture
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-29
---

# Phase 85 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (existing backend suite) |
| **Config file** | `puppeteer/pytest.ini` |
| **Quick run command** | `cd puppeteer && pytest tests/ -x -q` |
| **Full suite command** | `cd puppeteer && pytest tests/` |
| **Estimated runtime** | ~30 seconds |

---

## Sampling Rate

- **After every task commit:** Run `cd puppeteer && pytest tests/ -x -q`
- **After every plan wave:** Run `cd puppeteer && pytest tests/`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 85-01-01 | 01 | 1 | SCR-01 | syntax | `python -c "import ast; ast.parse(open('tools/capture_screenshots.py').read())"` | ❌ W0 | ⬜ pending |
| 85-01-02 | 01 | 1 | SCR-01 | unit | `cd puppeteer && pytest tests/ -x -q` | ✅ | ⬜ pending |
| 85-01-03 | 01 | 1 | SCR-01 | syntax | `python -c "import ast; ast.parse(open('tools/capture_screenshots.py').read())"` | ❌ W0 | ⬜ pending |
| 85-02-01 | 02 | 2 | SCR-02 | file | `test -d docs/docs/assets/screenshots && echo OK` | ❌ W0 | ⬜ pending |
| 85-02-02 | 02 | 2 | SCR-02 | grep | `grep -r "assets/screenshots" docs/docs/getting-started/` | ✅ | ⬜ pending |
| 85-02-03 | 02 | 2 | SCR-03 | grep | `grep -q "See it in action" homepage/index.html && echo OK` | ✅ | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tools/capture_screenshots.py` — create the script file (stub acceptable, must parse cleanly)
- [ ] `docs/docs/assets/screenshots/` — create directory with `.gitkeep`
- [ ] `homepage/assets/screenshots/` — create directory with `.gitkeep`

*Wave 0 covers file-existence checks before integration tasks run.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| 10+ PNGs produced at 1440×900 | SCR-01 | Requires live Docker stack + enrolled node | Run `python tools/capture_screenshots.py --url http://localhost:8080` against running stack, verify 10+ PNG files in `docs/docs/assets/screenshots/` |
| Screenshots show populated data (no empty-state/spinner) | SCR-01 | Visual inspection required | Open captured PNGs and confirm seeded data visible (node names, job rows, audit entries) |
| Homepage screenshots render correctly | SCR-03 | Visual/layout check | Open `homepage/index.html` in browser, verify screenshot grid layout is readable and images load |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
