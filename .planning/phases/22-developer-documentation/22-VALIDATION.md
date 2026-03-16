---
phase: 22
slug: developer-documentation
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-16
---

# Phase 22 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework (backend)** | pytest |
| **Framework (frontend)** | vitest 3.0.5 |
| **Config file (backend)** | None — pytest discovers automatically |
| **Config file (frontend)** | `puppeteer/dashboard/vitest.config.ts` |
| **Quick run command** | `cd puppeteer && pytest tests/ -x -q` |
| **Full suite command** | `cd puppeteer && pytest` + `cd puppeteer/dashboard && npm run test` |
| **Estimated runtime** | ~30 seconds |

---

## Sampling Rate

- **After every task commit:** Run `cd puppeteer && pytest tests/ -x -q` + `cd puppeteer/dashboard && npm run test -- --run`
- **After every plan wave:** Run full suite: `cd puppeteer && pytest` + `cd puppeteer/dashboard && npm run test`
- **Before `/gsd:verify-work`:** Full suite must be green + `docker build -f docs/Dockerfile .` succeeds
- **Max feedback latency:** ~30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 22-01-01 | 01 | 1 | DEVDOC-01 | smoke | `docker build -f docs/Dockerfile .` | ❌ W0 | ⬜ pending |
| 22-01-02 | 01 | 1 | DEVDOC-01 | manual | Verify Mermaid diagrams render (≥4 diagrams visible) | N/A | ⬜ pending |
| 22-02-01 | 02 | 2 | DEVDOC-02 | manual | Follow setup guide on clean machine, reach running local stack | N/A | ⬜ pending |
| 22-03-01 | 03 | 3 | DEVDOC-03 | manual | Verify guide specifies test commands and migration pattern | N/A | ⬜ pending |
| 22-03-02 | 03 | 3 | DEVDOC-03 | smoke | `cd puppeteer && pytest tests/ -x -q` (no regressions from file deletions) | ✅ | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] Verify `docs/Dockerfile` build test passes with `pymdownx.superfences` + Mermaid config added to `mkdocs.yml` — this is the primary automated gate for DEVDOC-01

*No new pytest or vitest test files required — this phase adds no new Python or TypeScript code.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Architecture guide renders ≥4 Mermaid diagrams in browser | DEVDOC-01 | Requires visual verification that `<div class="mermaid">` renders, not `<code>` | Build docs Docker image, open browser, verify all diagrams render |
| Setup guide enables clean-machine local stack | DEVDOC-02 | Requires following guide on a machine without pre-existing env setup | Follow guide step-by-step, confirm stack reaches healthy state |
| Contributing guide specifies exact test commands and migration pattern | DEVDOC-03 | Text content review — no automated check for documentation completeness | Read guide, confirm `pytest`, `npm run test`, migration SQL pattern are all present |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
