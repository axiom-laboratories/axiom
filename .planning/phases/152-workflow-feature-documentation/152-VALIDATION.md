---
phase: 152
slug: workflow-feature-documentation
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-16
---

# Phase 152 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | MkDocs build validation (no unit tests — pure docs phase) |
| **Config file** | `docs/mkdocs.yml` |
| **Quick run command** | `cd docs && mkdocs build --strict 2>&1 | tail -5` |
| **Full suite command** | `cd docs && mkdocs build --strict && grep -r "TODO\|FIXME\|PLACEHOLDER" docs/docs/workflows/ docs/docs/api-reference/ docs/docs/runbooks/workflows.md 2>/dev/null | grep -v ".pyc" || echo "No unresolved markers"` |
| **Estimated runtime** | ~10 seconds |

---

## Sampling Rate

- **After every task commit:** Run `cd docs && mkdocs build --strict 2>&1 | tail -5`
- **After every plan wave:** Run `cd docs && mkdocs build --strict && grep -r "TODO\|FIXME\|PLACEHOLDER" docs/docs/workflows/ docs/docs/api-reference/ docs/docs/runbooks/workflows.md 2>/dev/null | grep -v ".pyc" || echo "No unresolved markers"`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 10 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 152-01-01 | 01 | 1 | DOC structure | build | `cd docs && mkdocs build --strict 2>&1 | tail -5` | ❌ W0 | ⬜ pending |
| 152-01-02 | 01 | 1 | Nav registered | build | `grep -n "workflows" docs/mkdocs.yml` | ❌ W0 | ⬜ pending |
| 152-02-01 | 02 | 2 | concepts.md | build | `cd docs && mkdocs build --strict 2>&1 | tail -5` | ❌ W0 | ⬜ pending |
| 152-02-02 | 02 | 2 | user-guide.md | build | `cd docs && mkdocs build --strict 2>&1 | tail -5` | ❌ W0 | ⬜ pending |
| 152-03-01 | 03 | 3 | operator-guide.md | build | `cd docs && mkdocs build --strict 2>&1 | tail -5` | ❌ W0 | ⬜ pending |
| 152-03-02 | 03 | 3 | developer-guide.md | build | `cd docs && mkdocs build --strict 2>&1 | tail -5` | ❌ W0 | ⬜ pending |
| 152-04-01 | 04 | 4 | api-reference | build | `cd docs && mkdocs build --strict 2>&1 | tail -5` | ❌ W0 | ⬜ pending |
| 152-04-02 | 04 | 4 | runbook | build | `test -f docs/docs/runbooks/workflows.md && echo "EXISTS" || echo "MISSING"` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `docs/docs/workflows/` — directory created
- [ ] `docs/mkdocs.yml` — nav entries added for all new workflow pages
- [ ] Verify `cd docs && mkdocs build --strict` passes before content writing begins

*Wave 0 is minimal for this docs-only phase: create directory structure and register nav entries so build validation works throughout.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Mermaid ERD renders in browser | Developer guide accuracy | MkDocs build doesn't render Mermaid | Browse to deployed docs, verify ERD diagram renders in developer-guide.md |
| Screenshot placeholder callouts visible | User guide completeness | Image files don't exist yet | Check user-guide.md renders callout blocks with placeholder text |
| Cross-links between docs pages work | Navigation integrity | mkdocs build may not catch broken relative links | Click through from index.md to each sub-page in browser |
| API endpoint examples match live API | API reference accuracy | Cannot automate response verification | Manually test 2-3 example curl commands against running stack |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 10s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
