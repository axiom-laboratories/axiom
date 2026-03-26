---
gsd_state_version: 1.0
milestone: v14.2
milestone_name: — Docs on GitHub Pages
status: completed
stopped_at: "Completed 71-02 — Phase 71 fully done, GH Pages live at https://axiom-laboratories.github.io/axiom/"
last_updated: "2026-03-26T21:52:52.790Z"
last_activity: 2026-03-26 — Phase 71 complete, GH Pages live
progress:
  total_phases: 1
  completed_phases: 1
  total_plans: 2
  completed_plans: 2
  percent: 100
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-03-26)

**Core value:** Jobs run reliably — on the right node, when scheduled, with their output captured — without any step in the chain weakening the security model.
**Current focus:** Milestone v14.2 complete — Docs on GitHub Pages

## Current Position

Phase: 71 of 1 (Deploy Docs to GitHub Pages) — COMPLETE
Plan: 2 of 2 in current phase
Status: Milestone complete
Last activity: 2026-03-26 — Phase 71 complete, GH Pages live

Progress: [██████████] 100%

## Accumulated Context

### Decisions

- [v14.2]: `openapi.json` pre-committed (not regenerated in CI) — Docker build still regenerates at container build time
- [v14.2]: CE repo is public — GitHub Pages free tier, no paid plan needed
- [v14.2]: `mkdocs gh-deploy --force` approach (not `actions/deploy-pages` artifact chain) — simpler, official MkDocs Material recommendation, requires only `contents: write`
- [v14.2]: `offline` plugin made conditional via `!ENV [OFFLINE_BUILD, false]` — Dockerfile sets `OFFLINE_BUILD=true` to preserve air-gap container behaviour
- [Phase 71-deploy-docs-to-github-pages]: docs/site/ untracked from git — 166 build output files removed from index, gitignored
- [Phase 71-deploy-docs-to-github-pages]: OFFLINE_BUILD pattern established: offline plugin disabled for GitHub Pages, enabled via env var in Docker builds
- [Phase 71]: Separate docs-deploy.yml from ci.yml for dedicated docs deploy workflow
- [Phase 71]: openapi.json pre-committed; regen_openapi.sh is the local maintenance tool

### Pending Todos

None.

### Blockers/Concerns

None — milestone v14.2 complete. Site confirmed live at https://axiom-laboratories.github.io/axiom/

## Session Continuity

Last session: 2026-03-26T21:29:57.975Z
Stopped at: Completed 71-02 — Phase 71 fully done, GH Pages live at https://axiom-laboratories.github.io/axiom/
Resume file: None
