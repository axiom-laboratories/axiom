---
gsd_state_version: 1.0
milestone: v14.4
milestone_name: — Go-to-Market Polish
status: planning
stopped_at: Completed 78-01-PLAN.md
last_updated: "2026-03-27T18:04:14.499Z"
last_activity: 2026-03-27 — v14.4 roadmap created (phases 77–80)
progress:
  total_phases: 4
  completed_phases: 1
  total_plans: 3
  completed_plans: 2
  percent: 0
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-03-27)

**Core value:** Jobs run reliably — on the right node, when scheduled, with their output captured — without any step in the chain weakening the security model.
**Current focus:** v14.4 — Go-to-Market Polish (Phase 77: Licence Banner Polish)

## Current Position

Phase: 77 of 80 (Licence Banner Polish)
Plan: — (not yet planned)
Status: Ready to plan
Last activity: 2026-03-27 — v14.4 roadmap created (phases 77–80)

Progress: [░░░░░░░░░░] 0%

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

### Pending Todos

None carried forward.

### Blockers/Concerns

- Phase 80: Verify `ghp-import --dest-dir` flag availability in the mkdocs transitive install before implementing (`ghp-import --help`). Fallback: `peaceiris/actions-gh-pages@v4` with `destination_dir` + `keep_files: true`.
- Phase 80: Audit hardcoded absolute doc links in README, dashboard sidebar, and other files before changing `mkdocs.yml` `site_url` from `/axiom/` to `/axiom/docs/` — broken canonical links will cause 404s.

## Session Continuity

Last session: 2026-03-27T18:04:14.497Z
Stopped at: Completed 78-01-PLAN.md
Resume file: None
