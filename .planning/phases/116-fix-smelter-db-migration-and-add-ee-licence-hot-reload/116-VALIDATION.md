---
phase: 116
slug: fix-smelter-db-migration-and-add-ee-licence-hot-reload
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-03
---

# Phase 116 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x (backend) / vitest (frontend) |
| **Config file** | `puppeteer/pytest.ini` / `puppeteer/dashboard/vitest.config.ts` |
| **Quick run command** | `cd puppeteer && pytest tests/ -x -q` |
| **Full suite command** | `cd puppeteer && pytest && cd dashboard && npm run test` |
| **Estimated runtime** | ~45 seconds |

---

## Sampling Rate

- **After every task commit:** Run `cd puppeteer && pytest tests/ -x -q`
- **After every plan wave:** Run `cd puppeteer && pytest && cd dashboard && npm run test`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 45 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 116-01-01 | 01 | 1 | DB schema audit | manual | `diff db.py migration_v45.sql` | N/A | pending |
| 116-01-02 | 01 | 1 | Idempotent migration | integration | `sqlite3 jobs.db < migration_v46.sql` | W0 | pending |
| 116-01-03 | 01 | 1 | Licence reload service | unit | `pytest tests/test_licence_service.py` | W0 | pending |
| 116-01-04 | 01 | 1 | Reload endpoint | integration | `pytest tests/test_licence_reload.py` | W0 | pending |
| 116-01-05 | 01 | 1 | Background expiry timer | unit | `pytest tests/test_licence_reload.py` | W0 | pending |
| 116-01-06 | 01 | 1 | EE router guard | integration | `pytest tests/test_licence_reload.py` | W0 | pending |
| 116-01-07 | 01 | 1 | Backend integration tests | integration | `pytest tests/test_licence_reload.py` | W0 | pending |
| 116-02-01 | 02 | 2 | WebSocket broadcast | integration | `pytest tests/test_licence_reload.py` | W0 | pending |
| 116-02-02 | 02 | 2 | useWebSocket hook | unit | `npm run test` | W0 | pending |
| 116-02-03 | 02 | 2 | Licence UI components | unit | `npm run test` | W0 | pending |
| 116-02-04 | 02 | 2 | Admin licence section | integration | E2E Playwright | W0 | pending |
| 116-02-05 | 02 | 2 | Grace period banner | unit | `npm run test` | W0 | pending |
| 116-02-06 | 02 | 2 | E2E Playwright tests | e2e | `python test_playwright.py` | W0 | pending |
| 116-02-07 | 02 | 2 | Routing updates | manual | navigation check | N/A | pending |

*Status: pending / green / red / flaky*

---

## Wave 0 Requirements

- [ ] `puppeteer/tests/test_licence_reload.py` -- stubs for reload endpoint + timer + guard tests
- [ ] `puppeteer/tests/test_licence_service.py` -- stubs for reload_licence() + check_licence_expiry()

*Existing infrastructure covers frontend test framework (vitest already configured).*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| DB schema audit | Schema gaps identified | One-time discovery | Compare db.py models vs migration SQL |
| Admin routing | Licence section accessible | Navigation UX | Navigate to /admin, verify section visible |

---

## Validation Sign-Off

- [ ] All tasks have automated verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 45s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
