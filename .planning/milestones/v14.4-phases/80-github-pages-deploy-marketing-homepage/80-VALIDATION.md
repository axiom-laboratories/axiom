---
phase: 80
slug: github-pages-deploy-marketing-homepage
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-27
---

# Phase 80 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | None (CI-only validation — no local test runner applicable) |
| **Config file** | `.github/workflows/docs-deploy.yml`, `.github/workflows/homepage-deploy.yml` |
| **Quick run command** | `git ls-tree --name-only origin/gh-pages` (verify branch structure) |
| **Full suite command** | Push to `main` and verify GitHub Pages URLs respond correctly |
| **Estimated runtime** | ~60 seconds (CI pipeline) |

---

## Sampling Rate

- **After every task commit:** Run `git ls-tree --name-only origin/gh-pages` to verify branch structure
- **After every plan wave:** Run full smoke tests against live URLs
- **Before `/gsd:verify-work`:** Both curl smoke tests must pass
- **Max feedback latency:** ~60 seconds (CI + GitHub Pages propagation)

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 80-01-01 | 01 | 1 | MKTG-01 | smoke | `git ls-tree --name-only origin/gh-pages docs` | ❌ W0 | ⬜ pending |
| 80-01-02 | 01 | 1 | MKTG-01 | smoke | `curl -sf https://axiom-laboratories.github.io/axiom/docs/ \| grep -q "Axiom"` | ❌ W0 | ⬜ pending |
| 80-01-03 | 01 | 1 | MKTG-01 | smoke | `curl -sf https://axiom-laboratories.github.io/axiom/ \| grep -q "Distributed job execution"` (root untouched after docs deploy) | ❌ W0 | ⬜ pending |
| 80-02-01 | 02 | 1 | MKTG-02 | smoke | `curl -sf https://axiom-laboratories.github.io/axiom/ \| grep -q "Distributed job execution"` | ❌ W0 | ⬜ pending |
| 80-02-02 | 02 | 1 | MKTG-02 | manual | Visual inspection: hero, security section, CE/EE comparison, install snippet visible | N/A | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `mop_validation/scripts/test_pages_deploy.sh` — curl smoke tests for MKTG-01 and MKTG-02
- [ ] `homepage/index.html` — source file for MKTG-02 (does not exist yet)
- [ ] `homepage/style.css` — source file for MKTG-02 (does not exist yet)

*Note: Wave 0 for this phase creates the source files themselves — they are pre-conditions for the deploy workflows.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Marketing page visual layout | MKTG-02 | Requires visual inspection — layout, brand colours, section order | Open `axiom-laboratories.github.io/axiom/` in browser; verify hero tagline, security section, CE/EE table, install snippet, and "View Docs" CTA link |
| Root `.nojekyll` present at branch root | MKTG-01 | `git ls-tree` check — not a URL test | Run `git ls-tree --name-only origin/gh-pages` and confirm `.nojekyll` appears at root |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 120s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
