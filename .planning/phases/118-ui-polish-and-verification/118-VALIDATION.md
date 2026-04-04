---
phase: 118
slug: ui-polish-and-verification
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-04
---

# Phase 118 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | Vitest 3.0.5 (unit/component), Playwright (E2E) |
| **Config file** | puppeteer/dashboard/vitest.config.ts |
| **Quick run command** | `cd puppeteer/dashboard && npm run test -- run` |
| **Full suite command** | `cd puppeteer/dashboard && npm run test -- run && cd ../.. && cd puppeteer && pytest` |
| **Estimated runtime** | ~30 seconds (Vitest) + ~20 seconds (pytest) |

---

## Sampling Rate

- **After every task commit:** Run `cd puppeteer/dashboard && npm run test -- run`
- **After every plan wave:** Run full suite command
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 60 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 118-01-01 | 01 | 1 | POL-01 | component | `npx vitest run src/components/foundry/CVEBadge.test.tsx` | ❌ W0 | ⬜ pending |
| 118-01-02 | 01 | 1 | POL-02 | component | `npm run test -- run` | ❌ W0 | ⬜ pending |
| 118-01-03 | 01 | 1 | POL-04 | component | `npx vitest run src/views/Nodes.test.tsx` | ❌ W1 | ⬜ pending |
| 118-01-04 | 01 | 1 | POL-07 | component | `npx vitest run src/components/ui/skeleton.test.tsx` | ❌ W0 | ⬜ pending |
| 118-02-01 | 02 | 2 | POL-05 | component + visual | `npm run test -- run` | ❌ W2 | ⬜ pending |
| 118-02-02 | 02 | 2 | POL-03 | manual + automated | Axe-core in Playwright | ❌ W1 | ⬜ pending |
| 118-03-01 | 03 | 2 | GH-20 | integration | `cd puppeteer && pytest tests/test_jobs.py -x` | ✅ | ⬜ pending |
| 118-03-02 | 03 | 2 | GH-21 | E2E | Playwright verification script | ❌ W3 | ⬜ pending |
| 118-03-03 | 03 | 2 | GH-22 | E2E + component | Playwright + vitest | ❌ W3 | ⬜ pending |
| 118-04-01 | 04 | 3 | POL-06 | E2E | `python ~/Development/mop_validation/scripts/test_ui_polish.py` | ❌ W3 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `src/components/ui/skeleton.tsx` — Skeleton component + test stubs for POL-07
- [ ] `src/components/foundry/CVEBadge.test.tsx` — theme compliance tests for POL-01
- [ ] Backend test for `GET /api/jobs?status=...` endpoint validation for GH-20

*Existing infrastructure covers most phase requirements. Wave 0 adds missing test stubs.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Visual density feels "comfortable balanced" | POL-05 | Subjective UX judgment | Review screenshots from Playwright script, compare spacing in both themes |
| Status badge color intensity appropriate per context | POL-01 | Context-sensitive color choice | Visually inspect CVE badges vs job status badges in screenshots |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 60s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
