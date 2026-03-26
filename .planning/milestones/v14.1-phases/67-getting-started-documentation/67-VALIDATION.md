---
phase: 67
slug: getting-started-documentation
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-26
---

# Phase 67 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | mkdocs build --strict (built-in MkDocs validation) |
| **Config file** | `docs/mkdocs.yml` |
| **Quick run command** | `cd /home/thomas/Development/master_of_puppets/docs && mkdocs build --strict` |
| **Full suite command** | `cd /home/thomas/Development/master_of_puppets/docs && mkdocs build --strict` |
| **Estimated runtime** | ~10 seconds |

---

## Sampling Rate

- **After every task commit:** Run `cd /home/thomas/Development/master_of_puppets/docs && mkdocs build --strict`
- **After every plan wave:** Run `cd /home/thomas/Development/master_of_puppets/docs && mkdocs build --strict`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 67-01-01 | 01 | 1 | DOCS-02 | smoke | `grep "tabbed" docs/mkdocs.yml` | ✅ | ⬜ pending |
| 67-01-02 | 01 | 1 | DOCS-08 | build smoke + content | `grep "docker compose pull" docs/docs/getting-started/install.md` | ✅ | ⬜ pending |
| 67-01-03 | 01 | 1 | DOCS-01 | build smoke | `cd docs && mkdocs build --strict` | ✅ | ⬜ pending |
| 67-02-01 | 02 | 2 | DOCS-03 | build smoke | `cd docs && mkdocs build --strict` | ✅ | ⬜ pending |
| 67-02-02 | 02 | 2 | DOCS-04 | content check | `grep "master-of-puppets-node:latest" docs/docs/getting-started/enroll-node.md` | ✅ | ⬜ pending |
| 67-02-03 | 02 | 2 | DOCS-05 | content check | `grep -c "EXECUTION_MODE=direct" docs/docs/getting-started/enroll-node.md` (expect 0) | ✅ | ⬜ pending |
| 67-02-04 | 02 | 2 | DOCS-06 | content check | `grep "agent:8001" docs/docs/getting-started/enroll-node.md` | ✅ | ⬜ pending |
| 67-02-05 | 02 | 2 | DOCS-07 | content check | `grep "docker.sock" docs/docs/getting-started/enroll-node.md` | ✅ | ⬜ pending |
| 67-03-01 | 03 | 3 | DOCS-09 | build smoke | `cd docs && mkdocs build --strict` | ✅ | ⬜ pending |
| 67-03-02 | 03 | 3 | DOCS-10 | content check | `grep "axiom-push job push" docs/docs/getting-started/first-job.md` | ✅ | ⬜ pending |
| 67-03-03 | 03 | 3 | DOCS-11 | content check | `grep "Register your signing key first" docs/docs/getting-started/first-job.md` | ✅ | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

*Existing infrastructure covers all phase requirements. `mkdocs build --strict` is available and passes on the current unmodified codebase. No Wave 0 stubs needed.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Tab pairs render correctly in browser | DOCS-02, DOCS-03, DOCS-08, DOCS-10 | Visual rendering of tab UI cannot be verified by build alone | Open `mkdocs serve` and click each tab in the affected pages to confirm Dashboard/CLI pair renders and switches |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
