---
gsd_state_version: 1.0
milestone: v9.0
milestone_name: — Enterprise Documentation
status: completed
stopped_at: Completed 26-03-PLAN.md — Axiom naming pass on docs
last_updated: "2026-03-17T20:31:27.299Z"
last_activity: 2026-03-16 — Plan 21-02 checkpoint approved, all verification passed
progress:
  total_phases: 9
  completed_phases: 8
  total_plans: 24
  completed_plans: 24
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
- [Phase 23-getting-started-core-feature-guides]: Local mkdocs build --strict cannot pass without openapi.json (pre-existing Phase 21 constraint) — non-strict build passes cleanly with no new warnings from the four Getting Started pages
- [Phase 23-getting-started-core-feature-guides]: Getting Started pages use admonition-as-gotcha pattern: warning/danger admonitions highlight known failure modes inline with each step (API_KEY crash, ADMIN_PASSWORD first-start, JOIN_TOKEN raw vs enhanced, EXECUTION_MODE=direct)
- [Phase 24]: Stub-first nav pattern: all Phase 24 files created as stubs before content plans run, ensuring Docker mkdocs build --strict passes throughout
- [Phase 24]: 5-field cron documented explicitly; 6-field (seconds) documented as unsupported to prevent operator silent failures
- [Phase 24]: API key scoped permissions documented as reserved for future use — matching actual _authenticate_api_key() behaviour
- [Phase 24]: rbac.md is the operational guide (UI workflow); rbac-reference.md is the canonical permission table — separation keeps both pages focused
- [Phase 24]: service principals documented as dedicated H2 in rbac.md (not mixed with human user management) — audience and flow are distinct
- [Phase 24-extended-feature-guides-security]: 3 danger admonitions in mtls.md: Root CA key protection, revocation permanence, and point-of-no-return before old cert revoke
- [Phase 24-extended-feature-guides-security]: Prerequisites checklist uses Markdown task list syntax so operators can mentally check off before executing
- [Phase 24-extended-feature-guides-security]: Audit attribution section distinguishes human/sp/scheduler actors in audit log for compliance reviewers
- [Phase 24-extended-feature-guides-security]: Air-gap checklist embedded as fenced markdown block for copy-paste offline use
- [Phase 25-01]: Stub-first nav pattern reused from Phase 24 — four runbook nav entries added in plan 01 so Wave 2 content plans can write into existing files without breaking strict mode
- [Phase 25-01]: Runbooks overview uses symptom-first framing to orient operators toward observable state rather than internal component names
- [Phase 25-runbooks-troubleshooting]: Zombie reaper (zombie_timeout_minutes, default 30 min, configurable) documented as the effective operator-visible job timeout — 30-second direct-subprocess fallback intentionally omitted
- [Phase 25-runbooks-troubleshooting]: DEAD_LETTER job status carries danger admonition (cannot be retried in-place — must resubmit new job) to prevent operator confusion
- [Phase 25-02]: nodes.md H3 headers use plain-text symptom descriptions (not backtick-wrapped log lines) to ensure reliable MkDocs anchor slug generation for jump table links
- [Phase 25-02]: faq.md anchor cross-link included in nodes.md despite faq.md being a stub — link resolves when plan 25-04 fills FAQ content
- [Phase 25-04]: Foundry runbook clusters mirror failure surface: Build Failures / Smelt-Check Failures / Registry Issues — matching how operators observe failures in dashboard
- [Phase 25-04]: FAQ Ed25519 signing entry uses danger admonition with explicit wording that no flag/env/API option exists to disable verification
- [Phase 25-04]: ADMIN_PASSWORD FAQ entry directs to dashboard Reset Password flow with warning admonition against dropping the DB
- [Phase 26-02]: README under 80 lines — links to MkDocs docs site for all depth; no architecture diagrams or env var tables
- [Phase 26-02]: CE/EE split presented as a feature table (transparent, factual) not marketing prose
- [Phase 26-02]: CONTRIBUTING.md implicit CLA (no bot, no sign-off requirement) matching Apache 2.0 model
- [Phase 26-02]: CHANGELOG retroactive entries for v0.7.0-v0.9.0 with note that they predate Axiom rename
- [Phase 28-infrastructure-gap-closure]: CDN verification uses https:// prefix match — privacy plugin stores assets under assets/external/fonts.googleapis.com/ so plain domain grep matches local asset paths (false positive)
- [Phase 28-infrastructure-gap-closure]: Plugin ordering locked for docs: search -> privacy -> offline -> swagger-ui-tag; privacy downloads CDN assets at build time for air-gap compliance
- [Phase 26-axiom-branding-community-foundation]: Mermaid subgraph node IDs preserved as internal identifiers — only display labels updated to Axiom Orchestrator/Axiom Node branding
- [Phase 26-axiom-branding-community-foundation]: [Phase 26-03]: mop-push CLI renamed to axiom-push throughout all 21 docs files; mkdocs.yml site_name updated to Axiom

### Roadmap Evolution

- Phase 26 added: Axiom Branding & Community Foundation (from AXIOM_RELEASE_PLAN.md Phase 3)
- Phase 27 added: CI/CD, Packaging & Distribution (from AXIOM_RELEASE_PLAN.md Phase 4)

### Pending Todos

- [ ] Investigate `test_report_result` pre-existing failure (noted in Phase 17 summary as baseline, not a regression)
- [ ] Cryptographically signed job execution

### Blockers/Concerns

- [Phase 20]: CF Access policy scope decision needed before starting — gate all /docs/* or only /docs/security/*? Affects Caddyfile design.
- [Phase 21]: Test export_openapi.py locally against a clean Python env as first task — SQLAlchemy async engine may require dummy env vars (DATABASE_URL, ENCRYPTION_KEY) at import time.

## Session Continuity

Last session: 2026-03-17T20:21:04.760Z
Stopped at: Completed 26-03-PLAN.md — Axiom naming pass on docs
Resume file: None
