---
gsd_state_version: 1.0
milestone: v14.3
milestone_name: Security Hardening + EE Licensing
status: defining_requirements
stopped_at: "Milestone v14.3 started — defining requirements"
last_updated: "2026-03-26"
last_activity: 2026-03-26 — Milestone v14.3 started
progress:
  total_phases: 0
  completed_phases: 0
  total_plans: 0
  completed_plans: 0
  percent: 0
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-03-26)

**Core value:** Jobs run reliably — on the right node, when scheduled, with their output captured — without any step in the chain weakening the security model.
**Current focus:** Milestone v14.3 — Security Hardening + EE Licensing

## Current Position

Phase: Not started (defining requirements)
Plan: —
Status: Defining requirements
Last activity: 2026-03-26 — Milestone v14.3 started

## Accumulated Context

### Decisions

- [v14.2]: `openapi.json` pre-committed (not regenerated in CI) — Docker build still regenerates at container build time
- [v14.2]: CE repo is public — GitHub Pages free tier, no paid plan needed
- [v14.2]: `mkdocs gh-deploy --force` approach (not `actions/deploy-pages` artifact chain) — simpler, official MkDocs Material recommendation, requires only `contents: write`
- [v14.2]: `offline` plugin made conditional via `!ENV [OFFLINE_BUILD, false]` — Dockerfile sets `OFFLINE_BUILD=true` to preserve air-gap container behaviour

### Pending Todos

Deferred from this milestone:
- Fix golden path install docs (remove bundled nodes from `compose.cold-start.yaml`)
- Marketing homepage on GitHub Pages
- USP: hello world under 30 mins (signing UX)

### Blockers/Concerns

None.

## Session Continuity

Last session: 2026-03-26
Stopped at: Milestone v14.3 started — defining requirements
Resume file: None
