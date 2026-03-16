---
gsd_state_version: 1.0
milestone: v9.0
milestone_name: — Enterprise Documentation
status: planning
stopped_at: Phase 20 context gathered
last_updated: "2026-03-16T21:25:35.966Z"
last_activity: 2026-03-16 — v9.0 roadmap created, phases 20–25 defined
progress:
  total_phases: 6
  completed_phases: 0
  total_plans: 0
  completed_plans: 0
  percent: 0
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-03-16)

**Core value:** Jobs run reliably — on the right node, when scheduled, with output captured — without weakening the security model.
**Current focus:** Phase 20 — Container Infrastructure & Routing

## Current Position

Phase: 20 of 25 (Container Infrastructure & Routing)
Plan: 0 of 2 in current phase
Status: Ready to plan
Last activity: 2026-03-16 — v9.0 roadmap created, phases 20–25 defined

Progress: [░░░░░░░░░░] 0% (v9.0 not started)

## Accumulated Context

### Decisions

- v9.0: MkDocs Material chosen — git-backed markdown, no DB, static build, portable, all Insider features now free (9.7.0+)
- v9.0: Two-stage Dockerfile (python:3.12-slim builder + nginx:alpine serve) — mkdocs serve is not production-safe (GitHub issue #1825)
- v9.0: Caddy must use `handle /docs/*` (NOT handle_path) + nginx `alias` — prefix stripping silently breaks all CSS/JS assets
- v9.0: site_url must be `https://dev.master-of-puppets.work/docs/` in mkdocs.yml — bakes subpath into all asset references
- v9.0: /docs/* must be behind CF Access policy before any content goes live — security guide contains mTLS/token architecture details
- v9.0: openapi.json generated via app.openapi() import in builder stage (no running server) — watch for SQLAlchemy env var side effects at import time
- v9.0: Nav is task/audience-oriented from Phase 23 (Getting Started / Feature Guides / Security / Developer / API Reference) — must not be restructured after content is written

### Pending Todos

- [ ] Investigate `test_report_result` pre-existing failure (noted in Phase 17 summary as baseline, not a regression)
- [ ] Cryptographically signed job execution

### Blockers/Concerns

- [Phase 20]: CF Access policy scope decision needed before starting — gate all /docs/* or only /docs/security/*? Affects Caddyfile design.
- [Phase 21]: Test export_openapi.py locally against a clean Python env as first task — SQLAlchemy async engine may require dummy env vars (DATABASE_URL, ENCRYPTION_KEY) at import time.

## Session Continuity

Last session: 2026-03-16T21:25:35.964Z
Stopped at: Phase 20 context gathered
Resume file: .planning/phases/20-container-infrastructure-routing/20-CONTEXT.md
