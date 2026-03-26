---
gsd_state_version: 1.0
milestone: v14.2
milestone_name: — Docs on GitHub Pages
status: planning
stopped_at: Completed 71-deploy-docs-to-github-pages/71-01-PLAN.md
last_updated: "2026-03-26T17:22:06.872Z"
last_activity: 2026-03-26 — Roadmap created
progress:
  total_phases: 1
  completed_phases: 0
  total_plans: 2
  completed_plans: 1
  percent: 0
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-03-26)

**Core value:** Jobs run reliably — on the right node, when scheduled, with their output captured — without any step in the chain weakening the security model.
**Current focus:** Phase 71 — Deploy Docs to GitHub Pages

## Current Position

Phase: 71 of 1 (Deploy Docs to GitHub Pages)
Plan: 0 of ? in current phase
Status: Ready to plan
Last activity: 2026-03-26 — Roadmap created

Progress: [░░░░░░░░░░] 0%

## Accumulated Context

### Decisions

- [v14.2]: `openapi.json` pre-committed (not regenerated in CI) — Docker build still regenerates at container build time
- [v14.2]: CE repo is public — GitHub Pages free tier, no paid plan needed
- [v14.2]: `mkdocs gh-deploy --force` approach (not `actions/deploy-pages` artifact chain) — simpler, official MkDocs Material recommendation, requires only `contents: write`
- [v14.2]: `offline` plugin made conditional via `!ENV [OFFLINE_BUILD, false]` — Dockerfile sets `OFFLINE_BUILD=true` to preserve air-gap container behaviour
- [Phase 71-deploy-docs-to-github-pages]: docs/site/ untracked from git — 166 build output files removed from index, gitignored
- [Phase 71-deploy-docs-to-github-pages]: OFFLINE_BUILD pattern established: offline plugin disabled for GitHub Pages, enabled via env var in Docker builds

### Pending Todos

None.

### Blockers/Concerns

- Confirm exact GH Pages URL (`https://axiom-laboratories.github.io/axiom/`) before writing `site_url` in `mkdocs.yml`
- Confirm `docs/.cache/` privacy plugin cache completeness so GH Actions deploy does not hit CDN

## Session Continuity

Last session: 2026-03-26T17:22:06.871Z
Stopped at: Completed 71-deploy-docs-to-github-pages/71-01-PLAN.md
Resume file: None
