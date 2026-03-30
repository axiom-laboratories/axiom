---
gsd_state_version: 1.0
milestone: v17.0
milestone_name: Scale Hardening
status: defining_requirements
stopped_at: —
last_updated: "2026-03-30T00:00:00.000Z"
last_activity: 2026-03-30 — Milestone v17.0 started
progress:
  total_phases: 0
  completed_phases: 0
  total_plans: 0
  completed_plans: 0
  percent: 0
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-03-30)

**Core value:** Jobs run reliably — on the right node, when scheduled, with their output captured — without any step in the chain weakening the security model.
**Current focus:** Defining requirements for v17.0 Scale Hardening

## Current Position

Phase: Not started (defining requirements)
Plan: —
Status: Defining requirements
Last activity: 2026-03-30 — Milestone v17.0 started

Progress: [░░░░░░░░░░] 0%

## Accumulated Context

### Milestone Goals

Target reliable operation at:
- 20 concurrent polling nodes
- 200+ pending jobs in queue
- 1,000 active scheduled job definitions
- 100 cron fires per minute

All four dimensions currently exceed comfortable operating ceilings. APScheduler scale research (mop_validation/reports/apscheduler_scale_research.md) identified DB connection pool exhaustion as the primary constraint, followed by double-assignment races, O(N) sync_scheduler rebuild, and event loop saturation.

### Key Decisions

(none yet — milestone just started)

### Pending Todos

(none)

### Blockers/Concerns

(none)

## Session Continuity

Last session: 2026-03-30
Stopped at: Milestone start — proceeding to research
Resume file: None
