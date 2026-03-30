---
phase: 80-github-pages-deploy-marketing-homepage
plan: "02"
subsystem: infra
tags: [github-actions, github-pages, marketing, html, css, gh-pages]

requires:
  - phase: 80-github-pages-deploy-marketing-homepage
    provides: MkDocs docs site deployed to gh-pages at /docs/ subdirectory

provides:
  - Static marketing homepage source (homepage/index.html + homepage/style.css)
  - GitHub Actions workflow deploying homepage to gh-pages root (index.html, style.css)
  - axiom-laboratories.github.io/axiom/ shows marketing page, not MkDocs

affects:
  - gh-pages branch root (index.html, style.css, .nojekyll written by workflow)
  - Phase 80-01 docs workflow (must not conflict — homepage-deploy never touches docs/)

tech-stack:
  added: []
  patterns:
    - "Homepage files stashed to /tmp before git checkout gh-pages to survive branch switch"
    - "git diff --cached --quiet || git commit guards against empty-commit CI failures"
    - "Workflow scoped to homepage/** path — only triggers on homepage changes"

key-files:
  created:
    - homepage/index.html
    - homepage/style.css
    - .github/workflows/homepage-deploy.yml
  modified: []

key-decisions:
  - "Stash homepage files to /tmp before git checkout gh-pages — avoids working-tree wipe on branch switch"
  - "git diff --cached --quiet || git commit guard prevents empty-commit errors on no-op pushes"
  - "homepage-deploy scoped to homepage/** only — never writes to docs/ preserving MkDocs coexistence"
  - "No JavaScript, no CSS frameworks — pure HTML/CSS for zero-maintenance static page"

patterns-established:
  - "gh-pages coexistence: separate workflows own separate subdirectories (docs-deploy owns docs/, homepage-deploy owns root)"

requirements-completed: [MKTG-02]

duration: 2min
completed: 2026-03-27
---

# Phase 80 Plan 02: Marketing Homepage Summary

**Dark-slate HTML/CSS marketing homepage with hero, security positioning, CE/EE comparison, and install snippet — deployed to gh-pages root via a scoped GitHub Actions workflow that never touches the docs/ subdirectory**

## Performance

- **Duration:** ~2 min
- **Started:** 2026-03-27T21:17:42Z
- **Completed:** 2026-03-27T21:19:16Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments
- `homepage/index.html` with hero tagline, mTLS/Ed25519 security section, CE/EE two-column card comparison, Docker Compose install snippet, and CTA linking to `./docs/`
- `homepage/style.css` with full brand token set (`--axiom-primary`, `--axiom-bg`, `--axiom-surface`, `--axiom-border`, `--axiom-text`, `--axiom-text-muted`), Fira Sans/Code fonts, mobile-responsive grid below 640px
- `.github/workflows/homepage-deploy.yml` scoped to `homepage/**`, uses /tmp stash pattern for branch-switch safety, `git diff --cached --quiet ||` empty-commit guard, never writes to `docs/`

## Task Commits

1. **Task 1: Create homepage/index.html and homepage/style.css** - `7ed6f15` (feat)
2. **Task 2: Create .github/workflows/homepage-deploy.yml** - `fe9fd0b` (feat)

## Files Created/Modified
- `homepage/index.html` - Static marketing page: hero, security, CE/EE comparison, quick install
- `homepage/style.css` - Dark slate + crimson CSS variables, responsive layout, no frameworks
- `.github/workflows/homepage-deploy.yml` - CI deploy to gh-pages root, scoped trigger, empty-commit guard

## Decisions Made
- Stash homepage source files to `/tmp/homepage-deploy/` before `git checkout gh-pages` — without this, checking out gh-pages wipes the working tree and the `cp` commands would fail
- `git diff --cached --quiet || git commit` guard prevents the workflow from failing on no-op pushes where files haven't changed
- Workflow path trigger `homepage/**` ensures docs-deploy and homepage-deploy never interfere with each other

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required. The workflow will run automatically on the next push that modifies `homepage/**` on main.

## Next Phase Readiness

Phase 80 complete. The marketing homepage source and deploy workflow are in place:
- Pushing any change to `homepage/` on main triggers `homepage-deploy.yml`
- The workflow safely coexists with `docs-deploy.yml` — each owns its own part of gh-pages
- `axiom-laboratories.github.io/axiom/` will serve the marketing page; `/axiom/docs/` serves MkDocs

---
*Phase: 80-github-pages-deploy-marketing-homepage*
*Completed: 2026-03-27*
