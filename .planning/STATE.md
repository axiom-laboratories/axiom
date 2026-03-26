---
gsd_state_version: 1.0
milestone: v14.2
milestone_name: — Docs on GitHub Pages
status: defining_requirements
stopped_at: Milestone started
last_updated: "2026-03-26T00:00:00.000Z"
last_activity: 2026-03-26 — Milestone v14.2 started
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
**Current focus:** Defining requirements for v14.2 — Docs on GitHub Pages

## Current Position

Phase: Not started (defining requirements)
Plan: —
Status: Defining requirements
Last activity: 2026-03-26 — Milestone v14.2 started

Progress: [░░░░░░░░░░] 0%

## Accumulated Context

### Decisions

- [v14.2 Approach]: openapi.json will be pre-committed (not regenerated in CI) — keeps GH Actions workflow light; Docker build still regenerates it at container build time
- [v14.2 Approach]: CE repo is public → GitHub Pages free tier, no paid plan needed
- [v14.2 Approach]: GH Actions uses only docs/requirements.txt + mkdocs build — no FastAPI app deps needed in CI

### Roadmap Evolution

(none yet)

### Pending Todos

None.

### Blockers/Concerns

None.
