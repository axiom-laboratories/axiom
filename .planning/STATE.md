---
gsd_state_version: 1.0
milestone: v14.3
milestone_name: — Security Hardening + EE Licensing
status: planning
stopped_at: Phase 72 context gathered
last_updated: "2026-03-26T22:35:27.758Z"
last_activity: 2026-03-26 — Roadmap created (2 phases, 13/13 requirements mapped)
progress:
  total_phases: 2
  completed_phases: 0
  total_plans: 0
  completed_plans: 0
  percent: 0
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-03-26)

**Core value:** Jobs run reliably — on the right node, when scheduled, with their output captured — without any step in the chain weakening the security model.
**Current focus:** Milestone v14.3 — Phase 72: Security Fixes

## Current Position

Phase: 72 of 73 (Security Fixes)
Plan: 0 of TBD in current phase
Status: Ready to plan
Last activity: 2026-03-26 — Roadmap created (2 phases, 13/13 requirements mapped)

Progress: [░░░░░░░░░░] 0%

## Performance Metrics

**Velocity:**
- Total plans completed: 0 (this milestone)
- Average duration: —
- Total execution time: —

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 72. Security Fixes | TBD | - | - |
| 73. EE Licence System | TBD | - | - |

## Accumulated Context

### Decisions

- [v14.2]: `openapi.json` pre-committed (not regenerated in CI) — Docker build still regenerates at container build time
- [v14.2]: `mkdocs gh-deploy --force` approach — simpler, official MkDocs Material recommendation
- [v14.2]: `offline` plugin conditional via `!ENV [OFFLINE_BUILD, false]` — Dockerfile sets `OFFLINE_BUILD=true`
- [v14.3 pre-planning]: Licence validation must live in CE code (`licence_service.py`), not inside the EE plugin's `register()` — prevents partial route registration with no clean rollback
- [v14.3 pre-planning]: Licence expiry must degrade to DEGRADED_CE, never crash — `sys.exit(1)` on expiry creates production outages for air-gapped operators
- [v14.3 pre-planning]: Absent boot-log treated as "unknown" + grace fallback, not hard stop — deleted log is indistinguishable from fresh install

### Pending Todos

- Fix golden path install docs (remove bundled nodes from `compose.cold-start.yaml`)
- Marketing homepage on GitHub Pages
- USP: hello world under 30 mins (signing UX)
- Dashboard amber/red banner on GRACE/DEGRADED_CE state (deferred from v14.3 — backend API lands first)

### Blockers/Concerns

- main.py path-injection line numbers in the todo have drifted (todo references 2457/2461 but file is currently ~2152 lines) — run live CodeQL scan or check GitHub Security tab to find actual alert locations before implementing SEC-03
- Licence public key identity: `licence_service.py` needs a separate Ed25519 keypair from the job-signing key — confirm keypair exists or generate before Phase 73 begins

## Session Continuity

Last session: 2026-03-26T22:35:27.757Z
Stopped at: Phase 72 context gathered
Resume file: .planning/phases/72-security-fixes/72-CONTEXT.md
