---
gsd_state_version: 1.0
milestone: v14.4
milestone_name: — Go-to-Market Polish
status: planning
stopped_at: Phase 77 context gathered
last_updated: "2026-03-27T16:08:02.385Z"
last_activity: 2026-03-27 — v14.4 roadmap created (phases 77–80)
progress:
  total_phases: 4
  completed_phases: 0
  total_plans: 0
  completed_plans: 0
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

## Accumulated Context

### Decisions

- [v14.2]: `mkdocs gh-deploy --force` used for docs — BUT v14.4 Phase 80 must switch to `ghp-import --dest-dir docs` to coexist with homepage at root
- [v14.3 Phase 74]: Grace/expired banner placed between header and main in MainLayout.tsx — banner component exists at lines 211-223; Phase 77 polishes it (dismiss + admin-only guard)
- [v14.4 roadmap]: Phase 80 depends on Phase 78 (signing UX) and Phase 79 (install docs) completing first — homepage cannot honestly claim "30-minute setup" until those land
- [v14.4 roadmap]: `mkdocs gh-deploy --force` has no `--dest-dir` flag (confirmed MkDocs 1.6.1) — Phase 80 must use `ghp-import --dest-dir docs` or `peaceiris/actions-gh-pages@v4`

### Pending Todos

None carried forward.

### Blockers/Concerns

- Phase 80: Verify `ghp-import --dest-dir` flag availability in the mkdocs transitive install before implementing (`ghp-import --help`). Fallback: `peaceiris/actions-gh-pages@v4` with `destination_dir` + `keep_files: true`.
- Phase 80: Audit hardcoded absolute doc links in README, dashboard sidebar, and other files before changing `mkdocs.yml` `site_url` from `/axiom/` to `/axiom/docs/` — broken canonical links will cause 404s.

## Session Continuity

Last session: 2026-03-27T16:08:02.384Z
Stopped at: Phase 77 context gathered
Resume file: .planning/phases/77-licence-banner-polish/77-CONTEXT.md
