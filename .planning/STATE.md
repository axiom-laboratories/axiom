---
gsd_state_version: 1.0
milestone: v9.0
milestone_name: — Enterprise Documentation
status: completed
stopped_at: Completed 23-03-PLAN.md
last_updated: "2026-03-17T12:08:31.425Z"
last_activity: 2026-03-16 — Plan 21-02 checkpoint approved, all verification passed
progress:
  total_phases: 6
  completed_phases: 3
  total_plans: 11
  completed_plans: 10
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
Status: Complete — all tasks and checkpoint approved
Last activity: 2026-03-16 — Plan 21-02 checkpoint approved, all verification passed

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
- [Phase 21-api-reference-dashboard-integration]: postgresql+asyncpg dummy URL required in Dockerfile builder stage — aiosqlite not in requirements.txt
- [Phase 21-api-reference-dashboard-integration]: API_KEY env var must be set as dummy in builder — security.py calls sys.exit(1) at import time if missing
- [Phase 21-api-reference-dashboard-integration]: All new routes in main.py must include tags= parameter — 17 tag groups established for OpenAPI grouping
- [Phase 22-01]: Only architecture.md added to nav in plan 01 — setup-deployment.md and contributing.md nav entries deferred to plans 02/03 (mkdocs build --strict requires listed files to exist)
- [Phase 22-01]: admonition + pymdownx.details + tables extensions added to mkdocs.yml — required by architecture guide admonition boxes and tables
- [Phase 22]: Production Docker Compose section placed before Local Dev — most readers are deploying, not hacking
- [Phase 22]: aiosqlite and API_KEY sys.exit gotchas prominently documented with warning admonitions in setup guide
- [Phase 22-03]: pyproject.toml added as config file only — Black/Ruff not run on existing code this phase (deferred to separate PR to keep diffs reviewable)
- [Phase 22-03]: Contributing guide uses warning admonition for no-Alembic migration gotcha — establishes pattern for documenting critical contributor traps
- [Phase 23-01]: mkdocs build --strict requires Docker build (openapi.json generated in builder stage) — local CLI cannot pass strict mode without it; stub-first nav pattern established for all phase 23+ content files
- [Phase 23-04]: Pre-existing openapi.json strict-mode warning is a known infrastructure issue (Docker build only) — does not block mop-push guide
- [Phase 23]: mkdocs build --strict passes only via Docker builder stage — pre-existing limitation for local CLI (openapi.json missing locally)
- [Phase 23]: [Phase 23-03]: danger admonition used for packages dict-format gotcha (plain list silently fails); lifecycle tables include how-to-change column

### Pending Todos

- [ ] Investigate `test_report_result` pre-existing failure (noted in Phase 17 summary as baseline, not a regression)
- [ ] Cryptographically signed job execution

### Blockers/Concerns

- [Phase 20]: CF Access policy scope decision needed before starting — gate all /docs/* or only /docs/security/*? Affects Caddyfile design.
- [Phase 21]: Test export_openapi.py locally against a clean Python env as first task — SQLAlchemy async engine may require dummy env vars (DATABASE_URL, ENCRYPTION_KEY) at import time.

## Session Continuity

Last session: 2026-03-17T12:08:31.423Z
Stopped at: Completed 23-03-PLAN.md
Resume file: None
