---
phase: 78-cli-signing-ux
plan: "02"
subsystem: docs
tags: [axiom-push, cli, signing, onboarding, mkdocs]

# Dependency graph
requires:
  - phase: 78-cli-signing-ux
    provides: axiom-push CLI with key generate and init subcommands
provides:
  - first-job.md restructured with axiom-push init as primary onboarding path
affects: [79-install-docs-cleanup, 80-github-pages-homepage]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Docs: EE-only note placed before Quick Start steps to gate CE users early"
    - "Docs: collapsible ??? tip block for standalone key generate alternative"
    - "Docs: Manual Setup section at bottom preserves openssl commands as fallback"

key-files:
  created: []
  modified:
    - docs/docs/getting-started/first-job.md

key-decisions:
  - "Quick Start leads with AXIOM_URL export as first user-facing line — sets context before any command"
  - "axiom-push init is Step 1 describing all 3 auto-steps (login, key gen, registration) — no separate ceremony"
  - "axiom-push key generate lives in a collapsible ??? tip block — accessible but not promoted"
  - "openssl ceremony demoted to Manual Setup section — preserved for CE users and advanced operators"

patterns-established:
  - "Pattern 1: EE gate admonition appears before Quick Start block, not after title — catches CE users before they start"
  - "Pattern 2: CLI path uses === tab syntax alongside Dashboard path for parity"

requirements-completed:
  - CLI-04

# Metrics
duration: ~2h (split across checkpoint)
completed: 2026-03-27
---

# Phase 78 Plan 02: CLI Signing UX — first-job.md Restructure Summary

**first-job.md rewritten to lead with `axiom-push init` as a 3-step one-command onboarding path, with openssl demoted to a collapsible Manual Setup fallback**

## Performance

- **Duration:** ~2h (included human-verify checkpoint)
- **Started:** 2026-03-27T16:30:00Z
- **Completed:** 2026-03-27T18:35:13Z
- **Tasks:** 2 (1 auto + 1 checkpoint:human-verify)
- **Files modified:** 1

## Accomplishments

- Restructured first-job.md so AXIOM_URL export is the first user-facing line in Quick Start
- `axiom-push init` is now Step 1 with its 3 automatic sub-steps (login, key gen, registration) described inline — no separate key ceremony
- `axiom-push key generate` documented as standalone alternative in a collapsible `??? tip` block
- EE-only note placed before Quick Start steps to gate CE users to Manual Setup early
- openssl ceremony preserved intact in Manual Setup section at bottom of page
- Human reviewer verified all checklist items and approved

## Task Commits

Each task was committed atomically:

1. **Task 1: Restructure first-job.md with axiom-push init as primary path** - `a51b5ac` (docs)
2. **Task 2: Human review checkpoint** - approved (no code commit)

**Plan metadata:** (docs commit in final step)

## Files Created/Modified

- `docs/docs/getting-started/first-job.md` - Restructured getting-started guide with init-first structure

## Decisions Made

- Quick Start section opens with `export AXIOM_URL=...` as the very first line — establishes the required env var before any command is run
- `axiom-push init` describes all 3 automatic steps inline rather than linking out — reduces cognitive load for new users
- `axiom-push key generate` placed in a collapsible `??? tip` block — accessible for users who want keys without login, but not promoted as the primary path
- openssl commands moved entirely to Manual Setup — not removed, preserving utility for CE users and operators who prefer manual control

## Deviations from Plan

None — plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

- first-job.md is ready for Phase 80 homepage which needs to claim "30-minute setup" honestly
- Phase 79 (install docs cleanup) can reference the updated first-job.md structure as the target flow
- axiom-push CLI (Phase 78-01) and this docs restructure (Phase 78-02) together complete the CLI-04 requirement

---
*Phase: 78-cli-signing-ux*
*Completed: 2026-03-27*
