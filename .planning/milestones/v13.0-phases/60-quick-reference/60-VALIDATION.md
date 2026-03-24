---
phase: 60
slug: quick-reference
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-24
---

# Phase 60 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | Shell (grep/ls/mkdocs) — no pytest or vitest changes needed |
| **Config file** | `docs/mkdocs.yml` |
| **Quick run command** | `cd docs && mkdocs build --strict` |
| **Full suite command** | `cd docs && mkdocs build --strict` |
| **Estimated runtime** | ~10 seconds |

---

## Sampling Rate

- **After every task commit:** Run `cd docs && mkdocs build --strict`
- **After every plan wave:** Run `cd docs && mkdocs build --strict`
- **Before `/gsd:verify-work`:** Full suite must be green + manual content review
- **Max feedback latency:** ~10 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 60-01-01 | 01 | 1 | QREF-01 | smoke | `cd docs && mkdocs build --strict` | ✅ existing | ⬜ pending |
| 60-01-02 | 01 | 1 | QREF-01 | manual | `ls docs/docs/quick-ref/ && ! ls master_of_puppets_*.html 2>/dev/null` | N/A | ⬜ pending |
| 60-02-01 | 02 | 1 | QREF-02 | automated | `grep -c "Master of Puppets\|MoP" docs/docs/quick-ref/course.html` → expect 0 | ❌ Wave 0 | ⬜ pending |
| 60-02-02 | 02 | 1 | QREF-04 | automated | `grep -c "python_script" docs/docs/quick-ref/course.html` → expect 0 | ❌ Wave 0 | ⬜ pending |
| 60-03-01 | 03 | 1 | QREF-03 | automated | `grep -c "Scheduling Health" docs/docs/quick-ref/operator-guide.html` → expect ≥1 | ❌ Wave 0 | ⬜ pending |
| 60-03-02 | 03 | 1 | QREF-03 | automated | `grep -c "Queue" docs/docs/quick-ref/operator-guide.html` → expect ≥1 | ❌ Wave 0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

*Existing infrastructure covers all phase requirements.* Shell grep/ls commands are the only verification needed — no new test files required. No pytest or vitest changes.

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Root HTML files deleted | QREF-01 | File system state | `ls master_of_puppets_*.html` — expect no such files |
| Scheduling Health prose is accurate | QREF-03 | Semantic correctness of prose | Read the new section; verify LATE/MISSED semantics match `scheduler_service.py` |
| Course hero subtitle added | QREF-02 | Visual/structural quality | Open `docs/docs/quick-ref/course.html` in browser — confirm "Axiom" appears in hero section |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
