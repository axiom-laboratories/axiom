---
gsd_state_version: 1.0
milestone: v18.0
milestone_name: — First-User Experience & E2E Validation
status: completed
stopped_at: Phase 104 context gathered
last_updated: "2026-04-01T12:28:40.881Z"
last_activity: 2026-03-31 — Plan 103-03 executed (Windows E2E golden path; WIN-03 confirmed; node image blocker found)
progress:
  total_phases: 4
  completed_phases: 1
  total_plans: 9
  completed_plans: 4
  percent: 10
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-03-31)

**Core value:** Jobs run reliably — on the right node, when scheduled, with their output captured — without any step in the chain weakening the security model.
**Current focus:** v18.0 — First-User Experience & E2E Validation

## Current Position

Phase: 103 of 103 (Windows E2E Validation) — IN PROGRESS
Plan: 103-03 complete (3 of 4 plans done)
Status: Golden path run complete; 2 BLOCKERs found; 103-04 (fix phase) is next
Last activity: 2026-03-31 — Plan 103-03 executed (Windows E2E golden path; WIN-03 confirmed; node image blocker found)

Progress: [██░░░░░░░░] ~10%

## Performance Metrics

**Velocity:**
- Total plans completed: 2 (this milestone)
- Average duration: 13 min
- Total execution time: 25 min

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 101-ce-ux-cleanup | 2 | 25 min | 13 min |
| 103-windows-e2e-validation | 1 | 32 min | 32 min |

**Recent Trend:**
- Last 5 plans: 101-01 (15 min), 101-02 (10 min), 103-01 (32 min)
- Trend: —

*Updated after each plan completion*

## Accumulated Context

### Key Decisions

- [v18.0 Roadmap]: Phase 102 and 103 both depend on Phase 101 (CE UX Cleanup must land before E2E runs so testers see clean CE UI)
- [v18.0 Roadmap]: Phase 102 (Linux) and Phase 103 (Windows) are independent of each other — can run in parallel once Phase 101 is complete
- [v18.0 Roadmap]: Both E2E phases include friction fix requirements (LNX-06, WIN-06) — plan-phase must allocate a fix plan within each phase, not treat validation as read-only
- [101-01]: isEnterprise destructured at Admin component scope; EE tabs gated with {isEnterprise && (...)} on both TabsTrigger and TabsContent; + Enterprise CE upgrade panel renders UpgradePlaceholder grid
- [101-01]: Playwright confirmed CE tab bar = [Onboarding][+ Enterprise][Data], 6 EE tabs absent, upgrade panel shows 6 UpgradePlaceholder instances
- [101-02]: Tab visibility tests use queryByRole/getByRole with licence mock; exact regex /^\+ enterprise$/i used for EE-mode absence to avoid false positives from licence badge text
- [103-01]: Option B tab renamed to include OS qualifier so Windows tab can coexist as a parallel MkDocs Material tab without nesting
- [103-01]: Windows job signing uses Python cryptography library (no openssl dependency) matching key generation approach
- [103-01]: PowerShell TLS bypass pattern (add-type TrustAll) used consistently across all Invoke-RestMethod calls to self-signed endpoints
- [103-03]: docker save/load is the correct bypass for Docker Desktop credential store in SSH automation — pre-loading images sidesteps the credential helper layer entirely
- [103-03]: Node image (localhost/master-of-puppets-node:latest) must be published to GHCR and referenced in enroll-node.md — not buildable from the cold-start Quick Start path
- [103-03]: WIN-03 (forced password change) confirmed working on Windows: admin/admin returns must_change_password=true, PATCH /auth/me returns new JWT

### Pending Todos

None.

### Roadmap Evolution

- Phase 104 added: Review the three existing PRs for Axiom, and get the code merged

### Blockers/Concerns

None.

## Session Continuity

Last session: 2026-04-01T12:28:40.879Z
Stopped at: Phase 104 context gathered
Resume file: .planning/phases/104-review-the-three-existing-prs-for-axiom-and-get-the-code-merged/104-CONTEXT.md
