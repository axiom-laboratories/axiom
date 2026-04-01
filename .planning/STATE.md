---
gsd_state_version: 1.0
milestone: v18.0
milestone_name: — First-User Experience & E2E Validation
status: in-progress
stopped_at: Completed 104-02-PLAN.md — PR #18 merged, all 3 PRs on main
last_updated: "2026-04-01T13:06:06Z"
last_activity: "2026-04-01 — Plan 104-02 executed: rebased and merged PR #18 (Windows E2E) to main"
progress:
  total_phases: 4
  completed_phases: 2
  total_plans: 9
  completed_plans: 6
  percent: 66
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-03-31)

**Core value:** Jobs run reliably — on the right node, when scheduled, with their output captured — without any step in the chain weakening the security model.
**Current focus:** v18.0 — First-User Experience & E2E Validation

## Current Position

Phase: 104 of 104 (PR Review & Merge) — IN PROGRESS
Plan: 104-02 complete (2 of 3 plans done)
Status: All 3 PRs (#17, #18, #19) merged to main; cleanup and milestone close remain
Last activity: 2026-04-01 — Plan 104-02 executed: rebased and merged PR #18 (Windows E2E) to main

Progress: [██████░░░░] ~66%

## Performance Metrics

**Velocity:**
- Total plans completed: 2 (this milestone)
- Average duration: 13 min
- Total execution time: 25 min

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 101-ce-ux-cleanup | 2 | 25 min | 13 min |

**Recent Trend:**
- Last 5 plans: 101-01 (15 min), 101-02 (10 min)
- Trend: —

*Updated after each plan completion*

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 102-linux-e2e-validation P02 | 1 | 66 min | 66 min |
| 104-pr-review-merge P01 | 1 | 3 min | 3 min |
| 104-pr-review-merge P02 | 1 | 4 min | 4 min |

## Accumulated Context

### Key Decisions

- [v18.0 Roadmap]: Phase 102 and 103 both depend on Phase 101 (CE UX Cleanup must land before E2E runs so testers see clean CE UI)
- [v18.0 Roadmap]: Phase 102 (Linux) and Phase 103 (Windows) are independent of each other — can run in parallel once Phase 101 is complete
- [v18.0 Roadmap]: Both E2E phases include friction fix requirements (LNX-06, WIN-06) — plan-phase must allocate a fix plan within each phase, not treat validation as read-only
- [101-01]: isEnterprise destructured at Admin component scope; EE tabs gated with {isEnterprise && (...)} on both TabsTrigger and TabsContent; + Enterprise CE upgrade panel renders UpgradePlaceholder grid
- [101-01]: Playwright confirmed CE tab bar = [Onboarding][+ Enterprise][Data], 6 EE tabs absent, upgrade panel shows 6 UpgradePlaceholder instances
- [101-02]: Tab visibility tests use queryByRole/getByRole with licence mock; exact regex /^\+ enterprise$/i used for EE-mode absence to avoid false positives from licence badge text
- [102-01]: Exit code 2 used for pre-flight image-unreachable failure (vs exit 1 for run failure) to distinguish failure modes
- [102-01]: synthesise_friction.py _derive_edition() derives edition from filename stem (CE/EE by keyword, else run prefix like LNX) enabling cross-phase reuse
- [102-02]: chromium-browser excluded from LXC apt install — pulls snapd which stalls inside LXC; Playwright chromium installed separately via playwright install chromium
- [102-02]: Claude subagent must run as non-root user — UID 0 blocks --dangerously-skip-permissions; validator user created in LXC with docker group membership
- [102-02]: FRICTION finding: Quick Start compose command hard-codes --env-file .env which fails with no .env file — this is the BLOCKER for Plan 03
- [102-02 checkpoint]: User direction — remove --env-file .env from compose flow; compose must be self-contained with no external env file required

- [104-01]: Cherry-picked useWebSocket.ts onto clean branch to strip .planning/ contamination from PR #17
- [104-01]: Code review of deps.py/main.py sufficient without Docker stack test — straightforward async audit fix and countersign addition
- [104-01]: Merge queue handles merge strategy (merge commit); functionally equivalent to squash for single-commit branches

- [104-02]: Rebase conflicts in .planning/ resolved with --theirs; doc conflicts in first-job.md resolved with --ours (PR #19 version is canonical)
- [104-02]: Code review sufficient without Docker stack test -- PR #18 changes are additive to different sections than deps.py extraction
- [104-02]: Admin merge used to bypass merge queue with pre-existing CI failures (pytest not found, History.test.tsx)

### Roadmap Evolution

- Phase 104 added: PR Review & Merge — Review and merge PRs #17 (WebSocket fix), #18 (Windows E2E), #19 (Linux E2E) into main

### Pending Todos

None.

### Blockers/Concerns

FRICTION-LNX-102.md BLOCKER (actioned): Quick Start compose command uses `--env-file .env` but no .env file is created in Quick Start instructions. User direction: remove the flag entirely. Plan 03 will implement this fix.

## Session Continuity

Last session: 2026-04-01T13:06:06Z
Stopped at: Completed 104-02-PLAN.md — PR #18 merged, all 3 PRs on main
Resume file: .planning/phases/104-review-the-three-existing-prs-for-axiom-and-get-the-code-merged/104-03-PLAN.md
