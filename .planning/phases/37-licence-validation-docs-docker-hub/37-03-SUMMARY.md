---
phase: 37-licence-validation-docs-docker-hub
plan: "03"
subsystem: docs
tags: [mkdocs, material, admonition, css, enterprise, ce, ee, licensing]

requires:
  - phase: 37-licence-validation-docs-docker-hub
    provides: "37-01 implemented offline licence validation; docs setup (mkdocs.yml extra_css, licensing.md, extra.css) was included in 37-01 commit"

provides:
  - "!!! enterprise admonitions on 5 EE feature guide pages (foundry, rbac, rbac-reference, oauth, axiom-push)"
  - "Amber/gold enterprise admonition CSS in docs/docs/stylesheets/extra.css"
  - "CE/EE licensing explainer page at docs/docs/licensing.md"
  - "mkdocs.yml with extra_css and Licensing nav entry"
  - "mkdocs build --strict passes (pre-existing broken anchor links fixed, openapi.json stub created)"

affects: [docs, feature-guides, licensing]

tech-stack:
  added: []
  patterns:
    - "MkDocs Material custom admonition type: .admonition.enterprise with amber/gold #f59e0b border and title background"
    - "!!! enterprise admonition syntax (label-only, no body text) placed before first EE-specific ## heading"

key-files:
  created:
    - ".worktrees/axiom-split/docs/docs/stylesheets/extra.css"
    - ".worktrees/axiom-split/docs/docs/licensing.md"
    - ".worktrees/axiom-split/docs/docs/api-reference/openapi.json"
  modified:
    - ".worktrees/axiom-split/docs/mkdocs.yml"
    - ".worktrees/axiom-split/docs/docs/feature-guides/foundry.md"
    - ".worktrees/axiom-split/docs/docs/feature-guides/rbac.md"
    - ".worktrees/axiom-split/docs/docs/feature-guides/rbac-reference.md"
    - ".worktrees/axiom-split/docs/docs/feature-guides/oauth.md"
    - ".worktrees/axiom-split/docs/docs/feature-guides/axiom-push.md"
    - ".worktrees/axiom-split/docs/docs/runbooks/faq.md"
    - ".worktrees/axiom-split/docs/docs/runbooks/foundry.md"
    - ".worktrees/axiom-split/docs/docs/runbooks/nodes.md"

key-decisions:
  - "Admonition label-only (no body text under !!! enterprise) — per CONTEXT.md decision"
  - "Enterprise admonition placed before first ## heading after intro paragraph on each page"
  - "openapi.json stub created to satisfy swagger-ui-tag plugin in strict mode"

patterns-established:
  - "Enterprise feature marker: !!! enterprise admonition placed before first EE-only section"
  - "Custom MkDocs admonition: .md-typeset .admonition.enterprise with amber border-color #f59e0b"

requirements-completed: [DIST-03]

duration: 4min
completed: "2026-03-20"
---

# Phase 37 Plan 03: MkDocs Enterprise Admonitions Summary

**Amber enterprise admonition callouts added to 5 EE feature guide pages using custom CSS in MkDocs Material; licensing.md explains CE/EE split and AXIOM_LICENCE_KEY setup; mkdocs build --strict passes clean**

## Performance

- **Duration:** 4 min
- **Started:** 2026-03-20T16:16:01Z
- **Completed:** 2026-03-20T16:20:44Z
- **Tasks:** 2
- **Files modified:** 9

## Accomplishments

- `!!! enterprise` admonition inserted before first EE-specific `##` section on all 5 feature guide pages (foundry, rbac, rbac-reference, oauth, axiom-push)
- Custom amber/gold CSS for `.admonition.enterprise` type in `docs/docs/stylesheets/extra.css`
- `docs/docs/licensing.md` created: CE/EE table, `AXIOM_LICENCE_KEY` Docker Compose setup, offline validation, expiry behaviour table, `GET /api/licence` response example
- `mkdocs.yml` updated with `extra_css: [stylesheets/extra.css]` and `Licensing: licensing.md` nav entry
- Pre-existing `mkdocs build --strict` failures fixed (broken anchor double-dash slugs in runbooks, missing `openapi.json` stub)

## Task Commits

Each task was committed atomically:

1. **Task 1: enterprise CSS, licensing.md, mkdocs.yml** — already committed in `64b6484` / `6d6acc7` (included in 37-01 execution)
2. **Task 2: enterprise admonitions on 5 feature guides** — `0a69c54` (feat)

**Plan metadata:** see final docs commit below

## Files Created/Modified

- `.worktrees/axiom-split/docs/docs/stylesheets/extra.css` — Amber/gold enterprise admonition CSS (`.admonition.enterprise`, border `#f59e0b`)
- `.worktrees/axiom-split/docs/docs/licensing.md` — CE/EE edition table, AXIOM_LICENCE_KEY env var setup, offline validation description, expiry behaviour, GET /api/licence reference
- `.worktrees/axiom-split/docs/docs/api-reference/openapi.json` — Minimal stub satisfying swagger-ui-tag plugin
- `.worktrees/axiom-split/docs/mkdocs.yml` — `extra_css` block, `Licensing: licensing.md` in Feature Guides nav
- `.worktrees/axiom-split/docs/docs/feature-guides/foundry.md` — `!!! enterprise` before `## Concepts`
- `.worktrees/axiom-split/docs/docs/feature-guides/rbac.md` — `!!! enterprise` before `## Roles Overview`
- `.worktrees/axiom-split/docs/docs/feature-guides/rbac-reference.md` — `!!! enterprise` before `## Default Role Assignments`
- `.worktrees/axiom-split/docs/docs/feature-guides/oauth.md` — `!!! enterprise` before `## Authentication Methods`
- `.worktrees/axiom-split/docs/docs/feature-guides/axiom-push.md` — `!!! enterprise` before `## Install`
- `.worktrees/axiom-split/docs/docs/runbooks/faq.md` — Fixed double-dash anchor slugs in Quick Reference table
- `.worktrees/axiom-split/docs/docs/runbooks/foundry.md` — Fixed double-dash anchor slugs in Quick Reference table
- `.worktrees/axiom-split/docs/docs/runbooks/nodes.md` — Fixed mismatched faq.md anchor target

## Decisions Made

- Label-only admonition (`!!! enterprise` with no body text) per CONTEXT.md specification — avoids repetitive "This is an Enterprise feature" boilerplate
- Placement before first `##` heading (after intro paragraph) not at top-of-page — keeps intro accessible to all readers
- `openapi.json` stub is a minimal valid OpenAPI 3.1 document pointing users to the live `/openapi.json` endpoint

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Fixed pre-existing broken anchor links in runbooks preventing `mkdocs build --strict`**
- **Found during:** Task 1 verification
- **Issue:** Three runbook files used double-dash slugs (`--`) in anchor links which MkDocs Material generates as single-dash (`-`). Additionally, `nodes.md` linked to `faq.md#why-does-my-node-appear-multiple-times-in-the-dashboard` but the actual heading is "in the Nodes view". These pre-existed before plan 37-03 work but blocked the success criterion (`mkdocs build --strict` exits 0).
- **Fix:** Updated 4 anchor links in `runbooks/faq.md`, `runbooks/foundry.md`, and `runbooks/nodes.md` to use correct single-dash slugs/correct heading text
- **Files modified:** `docs/runbooks/faq.md`, `docs/runbooks/foundry.md`, `docs/runbooks/nodes.md`
- **Verification:** `mkdocs build --strict` passes with no warnings
- **Committed in:** `64b6484` (part of 37-01 task commit)

**2. [Rule 3 - Blocking] Created `openapi.json` stub to satisfy swagger-ui-tag plugin**
- **Found during:** Task 1 verification
- **Issue:** `api-reference/index.md` references `openapi.json` via `<swagger-ui src="openapi.json">` but the file didn't exist, causing `mkdocs_swagger_ui_tag: WARNING` that aborted strict build
- **Fix:** Created minimal valid `openapi.json` stub (OpenAPI 3.1.0, empty paths)
- **Files modified:** `docs/docs/api-reference/openapi.json`
- **Verification:** `mkdocs build --strict` passes with no warnings
- **Committed in:** `64b6484` (part of 37-01 task commit)

---

**Total deviations:** 2 auto-fixed (both Rule 3 — blocking pre-existing issues required for success criterion)
**Impact on plan:** Both fixes necessary for `mkdocs build --strict` to pass. No scope creep.

## Issues Encountered

- Task 1 artifacts (extra.css, licensing.md, mkdocs.yml updates, runbook fixes, openapi.json stub) were already committed in the worktree HEAD by plan 37-01 execution. Detected by comparing `git show HEAD:` with working files — all diffs were empty. Task 2 (enterprise admonitions on 5 feature guides) was not yet done and was completed normally.

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

- DIST-03 complete: all 5 EE feature guide pages show enterprise admonition callouts
- `mkdocs build --strict` passes cleanly
- Documentation is ready for Docker Hub / release packaging (DIST-01, DIST-02)
- Phase 37 plan 37-04 (Docker Hub push) can proceed

---
*Phase: 37-licence-validation-docs-docker-hub*
*Completed: 2026-03-20*
