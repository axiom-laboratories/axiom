---
gsd_state_version: 1.0
milestone: v14.4
milestone_name: — Go-to-Market Polish
status: completed
stopped_at: Completed 79-install-docs-cleanup-01-PLAN.md
last_updated: "2026-03-27T20:19:48.164Z"
last_activity: "2026-03-27 — Phase 78-02 complete: first-job.md restructured with axiom-push init as primary path"
progress:
  total_phases: 4
  completed_phases: 3
  total_plans: 4
  completed_plans: 4
  percent: 25
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-03-27)

**Core value:** Jobs run reliably — on the right node, when scheduled, with their output captured — without any step in the chain weakening the security model.
**Current focus:** v14.4 — Go-to-Market Polish (Phase 77: Licence Banner Polish)

## Current Position

Phase: 78 of 80 (CLI Signing UX)
Plan: 02 of 02 complete
Status: Phase 78 complete — ready for Phase 79
Last activity: 2026-03-27 — Phase 78-02 complete: first-job.md restructured with axiom-push init as primary path

Progress: [██░░░░░░░░] 25%

## Performance Metrics

**Velocity:**
- Total plans completed: 0 (this milestone)
- Average duration: —
- Total execution time: —

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 77. Licence Banner Polish | TBD | - | - |
| 78. CLI Signing UX | TBD | - | - |
| 79. Install Docs Cleanup | TBD | - | - |
| 80. GitHub Pages + Homepage | TBD | - | - |
| Phase 77 P01 | 2 | 2 tasks | 2 files |
| Phase 78-cli-signing-ux P01 | 35 | 3 tasks | 5 files |
| Phase 78-cli-signing-ux P02 | ~2h | 2 tasks | 1 file |
| Phase 79-install-docs-cleanup P01 | 1min | 2 tasks | 2 files |

## Accumulated Context

### Decisions

- [v14.2]: `mkdocs gh-deploy --force` used for docs — BUT v14.4 Phase 80 must switch to `ghp-import --dest-dir docs` to coexist with homepage at root
- [v14.3 Phase 74]: Grace/expired banner placed between header and main in MainLayout.tsx — banner component exists at lines 211-223; Phase 77 polishes it (dismiss + admin-only guard)
- [v14.4 roadmap]: Phase 80 depends on Phase 78 (signing UX) and Phase 79 (install docs) completing first — homepage cannot honestly claim "30-minute setup" until those land
- [v14.4 roadmap]: `mkdocs gh-deploy --force` has no `--dest-dir` flag (confirmed MkDocs 1.6.1) — Phase 80 must use `ghp-import --dest-dir docs` or `peaceiris/actions-gh-pages@v4`
- [Phase 77]: Two independent banner branches for GRACE and DEGRADED_CE prevent graceDismissed state cross-contamination
- [Phase 77]: isAdmin derived from existing user constant — no second getUser() call per render
- [Phase 77]: sessionStorage key axiom_licence_grace_dismissed stored in named constant in component body
- [Phase 78]: MOPClient imported at module level in cli.py for test-patchability (mop_sdk.cli.MOPClient)
- [Phase 78]: AXIOM_URL replaces MOP_URL entirely in cli.py — no fallback kept to avoid confusion
- [Phase 78-02]: Quick Start leads with AXIOM_URL export as first user-facing line — sets context before any command
- [Phase 78-02]: axiom-push init describes all 3 auto-steps inline — no separate key ceremony in Quick Start
- [Phase 78-02]: axiom-push key generate in ??? tip block — accessible but not promoted as primary path
- [Phase 78-02]: openssl ceremony demoted to Manual Setup — preserved for CE users and advanced operators
- [Phase 79-install-docs-cleanup]: compose.cold-start.yaml trimmed to 5 core services only — puppet nodes require separate JOIN token flow not appropriate for Quick Start
- [Phase 79-install-docs-cleanup]: Tab label renamed from 'Cold-Start Install' to 'Quick Start' across Steps 2, 3, 4 — aligns with user mental model for a first-run compose

### Pending Todos

None carried forward.

### Blockers/Concerns

- Phase 80: Verify `ghp-import --dest-dir` flag availability in the mkdocs transitive install before implementing (`ghp-import --help`). Fallback: `peaceiris/actions-gh-pages@v4` with `destination_dir` + `keep_files: true`.
- Phase 80: Audit hardcoded absolute doc links in README, dashboard sidebar, and other files before changing `mkdocs.yml` `site_url` from `/axiom/` to `/axiom/docs/` — broken canonical links will cause 404s.

## Session Continuity

Last session: 2026-03-27T20:19:48.161Z
Stopped at: Completed 79-install-docs-cleanup-01-PLAN.md
Resume file: None
