---
phase: 71
slug: deploy-docs-to-github-pages
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-26
---

# Phase 71 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | bash smoke checks + mkdocs build --strict |
| **Config file** | `docs/mkdocs.yml` |
| **Quick run command** | `cd docs && mkdocs build --strict` |
| **Full suite command** | `cd docs && mkdocs build --strict && git ls-files docs/site/ | wc -l` (expect 0) |
| **Estimated runtime** | ~30 seconds |

---

## Sampling Rate

- **After every task commit:** Run `cd docs && mkdocs build --strict`
- **After every plan wave:** Run full suite + all smoke checks below
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 71-01-01 | 01 | 1 | HOUSE-01 | smoke | `git ls-files docs/site/ \| wc -l` (expect 0) | ❌ Wave 0 | ⬜ pending |
| 71-01-02 | 01 | 1 | HOUSE-02 | smoke | `test -f docs/docs/.nojekyll` | ❌ Wave 0 | ⬜ pending |
| 71-01-03 | 01 | 1 | CONFIG-01 | unit | `grep 'axiom-laboratories.github.io/axiom/' docs/mkdocs.yml` | ❌ Wave 0 | ⬜ pending |
| 71-01-04 | 01 | 1 | CONFIG-02 | unit | `grep 'OFFLINE_BUILD' docs/mkdocs.yml` | ❌ Wave 0 | ⬜ pending |
| 71-01-05 | 01 | 1 | CONFIG-03 | unit | `grep 'OFFLINE_BUILD=true' docs/Dockerfile` | ❌ Wave 0 | ⬜ pending |
| 71-01-06 | 01 | 1 | CONFIG-02+03 | integration | `cd docs && mkdocs build --strict` | ❌ Wave 0 | ⬜ pending |
| 71-01-07 | 01 | 1 | DEPLOY-01 | smoke | `test -f .github/workflows/docs-deploy.yml` | ❌ Wave 0 | ⬜ pending |
| 71-01-08 | 01 | 1 | DEPLOY-02 | smoke | `test -f .github/workflows/docs-deploy.yml && test -f .github/workflows/ci.yml` | ❌ Wave 0 | ⬜ pending |
| 71-01-09 | 01 | 1 | MAINT-01 | smoke | `test -x docs/scripts/regen_openapi.sh` | ❌ Wave 0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `docs/docs/.nojekyll` — covers HOUSE-02
- [ ] `.github/workflows/docs-deploy.yml` — covers DEPLOY-01, DEPLOY-02
- [ ] `docs/scripts/regen_openapi.sh` — covers MAINT-01

*All other requirements are satisfied by modifying existing files (mkdocs.yml, Dockerfile, .gitignore).*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Site loads at `https://axiom-laboratories.github.io/axiom/` with correct CSS | DEPLOY-01 | Requires GH Pages to be live after first workflow run | Visit URL in browser; check nav, CSS, asset paths load correctly |
| Enable GH Pages in repo settings | DEPLOY-01 | GitHub UI action required after first `gh-pages` branch is created | Go to Settings → Pages → Source: Deploy from branch → `gh-pages` / `/ (root)` |
| `docs-deploy.yml` workflow runs and deploys successfully | DEPLOY-02 | Requires push to `main` and live GH Actions run | Merge a docs change; confirm workflow run succeeds in Actions tab |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
