---
phase: 70
slug: fix-getting-started-doc-regressions
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-26
---

# Phase 70 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | mkdocs build --strict (docs); manual file inspection |
| **Config file** | `docs/mkdocs.yml` |
| **Quick run command** | `cd docs && mkdocs build --strict 2>&1 | tail -5` |
| **Full suite command** | `cd docs && mkdocs build --strict` |
| **Estimated runtime** | ~10 seconds |

---

## Sampling Rate

- **After every task commit:** Run `cd docs && mkdocs build --strict 2>&1 | tail -5`
- **After every plan wave:** Run `cd docs && mkdocs build --strict`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 70-01-01 | 01 | 1 | DOCS-03 | file-check | `grep "d\['token'\]" docs/docs/getting-started/enroll-node.md` | ✅ | ⬜ pending |
| 70-01-02 | 01 | 1 | DOCS-01 | file-check | `grep "Cold-Start" docs/docs/getting-started/install.md` | ✅ | ⬜ pending |
| 70-01-03 | 01 | 1 | DOCS-08 | build | `cd docs && mkdocs build --strict` | ✅ | ⬜ pending |
| 70-01-04 | 01 | 1 | DOCS-08 | ci-check | `grep "mkdocs build --strict" .github/workflows/ci.yml` | ✅ | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

Existing infrastructure covers all phase requirements. This phase is documentation-only — no new test files needed.

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| CLI token extraction returns non-empty string | DOCS-03 | Requires live API call to verify runtime behavior | Run `curl -X POST .../admin/generate-token` and confirm token field is present in response |
| Cold-Start tab renders in browser | DOCS-01 | Visual tab rendering in mkdocs site | `cd docs && mkdocs serve`, open install.md Steps 3/4, verify Cold-Start tab present and shows correct docker compose command |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
