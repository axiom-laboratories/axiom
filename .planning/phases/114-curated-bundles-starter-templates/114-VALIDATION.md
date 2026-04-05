---
phase: 114
slug: curated-bundles-starter-templates
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-05
---

# Phase 114 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (backend) + vitest (frontend) |
| **Config file** | puppeteer/conftest.py (pytest); puppeteer/dashboard/vitest.config.ts (vitest) |
| **Quick run command** | `cd puppeteer && pytest tests/test_smelter.py -k bundle -x` |
| **Full suite command** | `cd puppeteer && pytest tests/test_smelter.py && cd dashboard && npm run test` |
| **Estimated runtime** | ~30 seconds |

---

## Sampling Rate

- **After every task commit:** Run `cd puppeteer && pytest tests/test_smelter.py -k bundle -x`
- **After every plan wave:** Run `cd puppeteer && pytest tests/test_smelter.py && cd dashboard && npm run test`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 114-01-01 | 01 | 1 | UX-02 | integration | `pytest tests/test_smelter.py::test_bundle_apply_bulk_approval -x` | ❌ W0 | ⬜ pending |
| 114-01-02 | 01 | 1 | UX-02 | unit | `pytest tests/test_smelter.py::test_bundle_apply_feedback_message -x` | ❌ W0 | ⬜ pending |
| 114-01-03 | 01 | 1 | UX-02 | integration | `pytest tests/test_smelter.py::test_bundle_apply_duplicate_skip -x` | ❌ W0 | ⬜ pending |
| 114-01-04 | 01 | 1 | UX-02 | integration | `pytest tests/test_smelter.py::test_bundle_mixed_ecosystem_resolve -x` | ❌ W0 | ⬜ pending |
| 114-01-05 | 01 | 1 | UX-02 | unit | `pytest tests/test_smelter.py::test_bundle_apply_permission_gate -x` | ❌ W0 | ⬜ pending |
| 114-02-01 | 02 | 1 | UX-03 | integration | `pytest tests/test_foundry.py::test_starter_templates_seeded -x` | ❌ W0 | ⬜ pending |
| 114-02-02 | 02 | 1 | UX-03 | unit | `pytest tests/test_foundry.py::test_starter_immutability -x` | ❌ W0 | ⬜ pending |
| 114-02-03 | 02 | 1 | UX-03 | integration | `vitest run src/views/__tests__/Templates.test.tsx -t "build now"` | ❌ W0 | ⬜ pending |
| 114-02-04 | 02 | 1 | UX-03 | integration | `vitest run src/views/__tests__/Templates.test.tsx -t "customize first"` | ❌ W0 | ⬜ pending |
| 114-02-05 | 02 | 1 | UX-03 | unit | `vitest run src/components/__tests__/BuildConfirmationDialog.test.tsx` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_smelter.py` — bundle CRUD + apply tests (covers UX-02)
- [ ] `tests/test_foundry.py` — starter template seeding + immutability tests (covers UX-03)
- [ ] `dashboard/src/views/__tests__/Templates.test.tsx` — gallery UI + dialog interaction tests (covers UX-03)
- [ ] `dashboard/src/components/__tests__/UseTemplateDialog.test.tsx` — "Build now" vs "Customize first" logic (covers UX-03)
- [ ] `dashboard/src/components/__tests__/BuildConfirmationDialog.test.tsx` — package count display (covers UX-03)

*Existing infrastructure covers framework installation (pytest + vitest already in place).*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Gallery visual layout matches app-store aesthetic | UX-03 | CSS/visual design review | Open Foundry > Node Images tab, verify starter cards show above custom templates with "Starter" badge |
| 3-click operator path end-to-end | UX-03 | Full Docker build required | Pick starter > "Build now" > confirm > verify image appears in Docker |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
