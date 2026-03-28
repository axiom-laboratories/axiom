---
gsd_state_version: 1.0
milestone: v14.4
milestone_name: — Go-to-Market Polish
status: completed
stopped_at: Completed 81-01-PLAN.md — homepage enterprise messaging, SSO narrative, and conversion optimisation
last_updated: "2026-03-28T08:21:03.608Z"
last_activity: "2026-03-27 — Phase 78-02 complete: first-job.md restructured with axiom-push init as primary path"
progress:
  total_phases: 5
  completed_phases: 5
  total_plans: 7
  completed_plans: 7
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
| Phase 80 P01 | 1min | 2 tasks | 2 files |
| Phase 80 P02 | 2 | 2 tasks | 3 files |
| Phase 81 P01 | 2 | 2 tasks | 2 files |
| Phase 81 P01 | 3min | 3 tasks | 2 files |

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
- [Phase 80]: Use ghp-import -n -p -f -x docs site instead of mkdocs gh-deploy --force to restrict docs deploy to docs/ subtree only
- [Phase 80]: site_url in mkdocs.yml updated to /axiom/docs/ to match new canonical path after subtree deploy
- [Phase 80]: Stash homepage files to /tmp before git checkout gh-pages — avoids working-tree wipe on branch switch
- [Phase 80]: homepage-deploy scoped to homepage/** only — never writes to docs/ preserving MkDocs coexistence
- [Phase 81]: Security cards use var(--axiom-bg) not --axiom-surface for contrast against section-alt background
- [Phase 81]: GOOGLE_FORM_URL_PLACEHOLDER sentinel used instead of empty href so broken enterprise links are visible before launch
- [Phase Phase 81]: CE code snippet spacing: .dual-cta-block pre scoped to display:block so margin-bottom works in inline formatting context

### Roadmap Evolution

- Phase 81 added: Homepage enterprise messaging — SSO narrative, compliance framing, and conversion optimisation

### Pending Todos

None carried forward.

### Blockers/Concerns

- Phase 80: Verify `ghp-import --dest-dir` flag availability in the mkdocs transitive install before implementing (`ghp-import --help`). Fallback: `peaceiris/actions-gh-pages@v4` with `destination_dir` + `keep_files: true`.
- Phase 80: Audit hardcoded absolute doc links in README, dashboard sidebar, and other files before changing `mkdocs.yml` `site_url` from `/axiom/` to `/axiom/docs/` — broken canonical links will cause 404s.

## Session Continuity

Last session: 2026-03-28T08:21:03.605Z
Stopped at: Completed 81-01-PLAN.md — homepage enterprise messaging, SSO narrative, and conversion optimisation
Resume file: None
