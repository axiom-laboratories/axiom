---
phase: 166
slug: router-modularization
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-18
---

# Phase 166 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x |
| **Config file** | `puppeteer/pytest.ini` or default pytest discovery |
| **Quick run command** | `cd puppeteer && pytest tests/ -x -q --tb=short` |
| **Full suite command** | `cd puppeteer && pytest tests/` |
| **Estimated runtime** | ~30–60 seconds |

---

## Sampling Rate

- **After every task commit:** Run `cd puppeteer && pytest tests/ -x -q --tb=short`
- **After every plan wave:** Run `cd puppeteer && pytest tests/`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 60 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 166-01-01 | 01 | 1 | ARCH-01 | — | Auth routes only exported via auth_router | unit | `cd puppeteer && pytest tests/ -x -q -k auth` | ✅ | ⬜ pending |
| 166-01-02 | 01 | 1 | ARCH-01 | — | Jobs routes only exported via jobs_router | unit | `cd puppeteer && pytest tests/ -x -q -k job` | ✅ | ⬜ pending |
| 166-01-03 | 01 | 1 | ARCH-01 | — | Nodes routes only exported via nodes_router | unit | `cd puppeteer && pytest tests/ -x -q -k node` | ✅ | ⬜ pending |
| 166-01-04 | 01 | 1 | ARCH-01 | — | Workflows routes only exported via workflows_router | unit | `cd puppeteer && pytest tests/ -x -q -k workflow` | ✅ | ⬜ pending |
| 166-02-01 | 02 | 1 | ARCH-01 | — | Admin routes only exported via admin_router | unit | `cd puppeteer && pytest tests/ -x -q -k admin` | ✅ | ⬜ pending |
| 166-02-02 | 02 | 1 | ARCH-01 | — | System/health/schedule routes in system_router | unit | `cd puppeteer && pytest tests/ -x -q -k system` | ✅ | ⬜ pending |
| 166-02-03 | 02 | 1 | ARCH-01 | — | Smelter routes wired in via smelter_router | unit | `cd puppeteer && pytest tests/ -x -q -k smelter` | ✅ | ⬜ pending |
| 166-03-01 | 03 | 2 | ARCH-02 | — | OpenAPI schema identical before/after refactor | integration | `python scripts/openapi_diff.py` | ❌ W0 | ⬜ pending |
| 166-04-01 | 04 | 2 | ARCH-04 | — | Full pytest suite passes with no new failures | regression | `cd puppeteer && pytest tests/` | ✅ | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `scripts/openapi_diff.py` — script to export and diff OpenAPI JSON before/after refactor (for task 166-03-01)

*All other test infrastructure already exists: 82 pytest test files cover all 89 routes.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| WebSocket `/ws` endpoint connects and receives live events | ARCH-02 | Requires live Docker stack + WS client | Start stack, connect WS client with valid JWT, verify events stream |
| Zero `@app.` route decorators remain in main.py | ARCH-01 | Structural check (grep) | `grep -n "@app\." puppeteer/agent_service/main.py` — must return 0 route handlers |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 60s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
