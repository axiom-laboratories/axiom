---
gsd_state_version: 1.0
milestone: v9.0
milestone_name: — Enterprise Documentation
status: executing
stopped_at: Completed 21-02-PLAN.md (dashboard cleanup; awaiting human verify checkpoint)
last_updated: "2026-03-16T22:30:08Z"
last_activity: 2026-03-16 — Plan 21-02 complete (removed Docs.tsx, added external Docs link)
progress:
  total_phases: 6
  completed_phases: 1
  total_plans: 2
  completed_plans: 2
  percent: 100
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-03-16)

**Core value:** Jobs run reliably — on the right node, when scheduled, with output captured — without weakening the security model.
**Current focus:** Phase 21 — API Reference & Dashboard Integration

## Current Position

Phase: 21 of 25 (API Reference & Dashboard Integration)
Plan: 2 of N in current phase
Status: In progress (checkpoint awaiting human verify for 21-02)
Last activity: 2026-03-16 — Plan 21-02 complete (removed Docs.tsx, added external Docs link)

Progress: [██████████] 100% (plans completed vs total discovered)

## Accumulated Context

### Decisions

- v9.0: MkDocs Material chosen — git-backed markdown, no DB, static build, portable, all Insider features now free (9.7.0+)
- v9.0: Two-stage Dockerfile (python:3.12-slim builder + nginx:alpine serve) — mkdocs serve is not production-safe (GitHub issue #1825)
- v9.0: Caddy must use `handle /docs/*` (NOT handle_path) + nginx `alias` — prefix stripping silently breaks all CSS/JS assets
- v9.0: site_url must be `https://dev.master-of-puppets.work/docs/` in mkdocs.yml — bakes subpath into all asset references
- v9.0: /docs/* must be behind CF Access policy before any content goes live — security guide contains mTLS/token architecture details
- v9.0: openapi.json generated via app.openapi() import in builder stage (no running server) — watch for SQLAlchemy env var side effects at import time
- v9.0: Nav is task/audience-oriented from Phase 23 (Getting Started / Feature Guides / Security / Developer / API Reference) — must not be restructured after content is written
- [Phase 20]: mkdocs build --strict enforced in builder stage — any MkDocs warning fails Docker build
- [Phase 20]: nginx alias (not root) used for /docs/ location — root breaks subpath asset resolution
- [Phase 20]: Privacy plugin downloads external assets at build time — zero outbound font/JS requests at runtime
- [Phase 20-container-infrastructure-routing]: handle /docs/* used (not handle_path) in Caddy — preserves URI prefix for nginx alias subpath routing
- [Phase 20-container-infrastructure-routing]: CF Access protection for /docs/* deferred by user — local routing confirmed working, CF Access to be configured in a future session
- [Phase 21-02]: External sidebar links use plain <a> (not NavLink) with matching inactive CSS — NavLink cannot open external URLs and would never have active state
- [Phase 21-02]: Catch-all route placed inside PrivateRoute wrapper so unauthenticated users hitting unknown paths still see Login redirect

### Pending Todos

- [ ] Investigate `test_report_result` pre-existing failure (noted in Phase 17 summary as baseline, not a regression)
- [ ] Cryptographically signed job execution

### Blockers/Concerns

- [Phase 20]: CF Access policy scope decision needed before starting — gate all /docs/* or only /docs/security/*? Affects Caddyfile design.
- [Phase 21]: Test export_openapi.py locally against a clean Python env as first task — SQLAlchemy async engine may require dummy env vars (DATABASE_URL, ENCRYPTION_KEY) at import time.

## Session Continuity

Last session: 2026-03-16T22:30:08Z
Stopped at: Completed 21-02-PLAN.md (dashboard cleanup; awaiting human verify checkpoint)
Resume file: None
