---
phase: 59
slug: documentation
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-24
---

# Phase 59 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | mkdocs build --strict (primary), smoke shell assertions |
| **Config file** | `docs/mkdocs.yml` |
| **Quick run command** | `cd /home/thomas/Development/master_of_puppets/docs && mkdocs build --strict 2>&1 | tail -5` |
| **Full suite command** | `cd /home/thomas/Development/master_of_puppets/docs && mkdocs build --strict` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `cd /home/thomas/Development/master_of_puppets/docs && mkdocs build --strict 2>&1 | tail -5`
- **After every plan wave:** Run `cd /home/thomas/Development/master_of_puppets/docs && mkdocs build --strict`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 59-01-01 | 01 | 1 | DOCS-01 | smoke | `test -f .env.example && grep -q SECRET_KEY .env.example && grep -q ENCRYPTION_KEY .env.example && grep -q API_KEY .env.example` | ❌ W0 | ⬜ pending |
| 59-01-02 | 01 | 1 | DOCS-02 | smoke | `mkdocs build --strict` | ❌ W0 | ⬜ pending |
| 59-01-03 | 01 | 1 | DOCS-03 | smoke | `mkdocs build --strict` | ❌ W0 | ⬜ pending |
| 59-01-04 | 01 | 1 | DOCS-04 | smoke | `mkdocs build --strict` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `docs/docs/assets/` directory — must exist before `logo.svg` is referenced in `mkdocs.yml`
- [ ] `docs/docs/getting-started/docker-deployment.md` — new file stub for DOCS-02 (prevents strict build failure)
- [ ] `docs/docs/feature-guides/jobs.md` — new file stub for DOCS-04
- [ ] `docs/docs/feature-guides/nodes.md` — new file stub for DOCS-04

*Wave 0 gaps are content files, not test infrastructure — created at start of plan execution before nav references are added to mkdocs.yml*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Docs site visually matches dashboard (fonts, color) | DOCS-03 | Requires browser render to confirm Fira Sans loads and crimson primary is visible | Open docs locally: `cd docs && mkdocs serve`, navigate to any page, confirm Fira Sans in browser DevTools and crimson nav bar |
| `.env.example` format readable by new operator | DOCS-01 | Content quality, not syntax | Read `.env.example` top-to-bottom — every var should be self-explanatory from its comment alone |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
