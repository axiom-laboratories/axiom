---
phase: 156
slug: state-of-the-nation-report
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-16
---

# Phase 156 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x (backend) / vitest (frontend) |
| **Config file** | `puppeteer/pytest.ini` / `puppeteer/dashboard/vitest.config.ts` |
| **Quick run command** | `cd puppeteer && pytest tests/ -q --tb=short` |
| **Full suite command** | `cd puppeteer && pytest && cd dashboard && npm run test` |
| **Estimated runtime** | ~60 seconds |

---

## Sampling Rate

- **After every task commit:** Run `cd puppeteer && pytest tests/ -q --tb=short`
- **After every plan wave:** Run `cd puppeteer && pytest && cd dashboard && npm run test`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 60 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 156-01-01 | 01 | 1 | STATE-NATION | manual | N/A — document generation | ✅ | ⬜ pending |
| 156-01-02 | 01 | 1 | STATE-NATION | manual | N/A — document generation | ✅ | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

*Existing infrastructure covers all phase requirements. Phase 156 is a document-generation phase — no new test files needed.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| STATE-OF-NATION.md produced and complete | Phase 156 goal | Document generation with human judgment | Verify file exists at `.planning/STATE-OF-NATION.md`; check all sections present; confirm blockers/readiness assessment is accurate |
| Product completeness assessment accurate | STATE-NATION | Requires live inspection of code and containers | Cross-check requirements traceability, run test suite, inspect Docker stack |
| Phase 155 blocker status correct | STATE-NATION | Must reflect actual current state of code | Read WorkflowDetail.tsx and DAGCanvas.tsx; verify blocker descriptions match actual gaps |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 60s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
