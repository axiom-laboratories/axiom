---
gsd_state_version: 1.0
milestone: v14.3
milestone_name: Security Hardening + EE Licensing
status: complete
stopped_at: Milestone archived
last_updated: "2026-03-27T15:30:00.000Z"
last_activity: 2026-03-27 — v14.3 milestone archived
progress:
  total_phases: 5
  completed_phases: 5
  total_plans: 8
  completed_plans: 8
  percent: 100
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-03-27)

**Core value:** Jobs run reliably — on the right node, when scheduled, with their output captured — without any step in the chain weakening the security model.
**Current focus:** Planning next milestone — run `/gsd:new-milestone`

## Current Position

Milestone v14.3 complete — all 5 phases (72–76), 8 plans, 13/13 requirements delivered.
Status: Archived — ready for next milestone.
Last activity: 2026-03-27 — Milestone archived

Progress: [██████████] 100%

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
| Phase 72 P01 | 22 | 2 tasks | 6 files |
| Phase 72 P02 | 7 | 3 tasks | 6 files |
| Phase 73 P01 | 2 | 1 tasks | 1 files |
| Phase 73 P02 | 4 | 2 tasks | 3 files |
| Phase 73 P03 | 5min | 2 tasks | 1 files |
| Phase 74 P01 | 3m8s | 2 tasks | 6 files |
| Phase 75 P01 | 3m | 3 tasks | 9 files |
| Phase 76-v14.3-tech-debt-cleanup P01 | 8min | 3 tasks | 2 files |

## Accumulated Context

### Decisions

- [v14.2]: `openapi.json` pre-committed (not regenerated in CI) — Docker build still regenerates at container build time
- [v14.2]: `mkdocs gh-deploy --force` approach — simpler, official MkDocs Material recommendation
- [v14.2]: `offline` plugin conditional via `!ENV [OFFLINE_BUILD, false]` — Dockerfile sets `OFFLINE_BUILD=true`
- [v14.3 pre-planning]: Licence validation must live in CE code (`licence_service.py`), not inside the EE plugin's `register()` — prevents partial route registration with no clean rollback
- [v14.3 pre-planning]: Licence expiry must degrade to DEGRADED_CE, never crash — `sys.exit(1)` on expiry creates production outages for air-gapped operators
- [v14.3 pre-planning]: Absent boot-log treated as "unknown" + grace fallback, not hard stop — deleted log is indistinguishable from fresh install
- [Phase 72]: validate_path_within must be in security.py — test_vault_traversal.py imports it from there (vault_service.py Artifact import broken)
- [Phase 72]: TDD Wave 0 pattern: auth dep-override with MagicMock for ASGI tests against require_auth routes
- [Phase 72]: html.escape() for XSS prevention; validate_path_within() uses Path.is_relative_to() for path traversal guards; API_KEY removed from security.py startup
- [Phase 72]: XSS test assertion: 'payload not in text' not 'no script tag' — page has own JS; traversal URL tests check != 200 since Starlette normalizes at routing layer
- [Phase 73]: Import path for licence_service is puppeteer.agent_service.services.licence_service — consistent with existing service module pattern
- [Phase 73]: TDD Wave 0 RED tests: function-scope imports ensure ModuleNotFoundError is the failure signal, not import-time crash at collection
- [Phase 73]: pytest run from repo root (not puppeteer/) for licence tests — test_licence_service.py uses puppeteer.agent_service.* import path requiring parent dir in sys.path
- [Phase 73]: tools/licence_signing.key gitignored (correct) — private key must not be committed; operators run --generate-keypair during bootstrap
- [Phase 73]: Node limit guard placed before token validation in enroll_node() — test spec expects 402 even when token mock returns None; guard fires first for correct 402/403 ordering
- [Phase 73]: DEGRADED_CE pull_work guard returns PollResponse(job=None) silently — not HTTPException — nodes stay connected and heartbeating per LIC-04 spec
- [Phase 74]: isEnterprise computed as status !== 'ce' — valid/grace/expired all count as EE-licenced
- [Phase 74]: STATUS_BADGE/STATUS_LABEL lookup maps in Admin.tsx LicenceSection for clean status rendering
- [Phase 74]: Grace/expired banner placed between header and main in MainLayout.tsx
- [Phase 75]: check_and_record_boot() takes licence_status parameter; CE warns only, EE (VALID/GRACE/EXPIRED) raises RuntimeError on rollback — removes AXIOM_STRICT_CLOCK env var bypass vector
- [Phase 75]: main.py lifespan reordered: load_licence() first, then check_and_record_boot(licence_state.status) — clock hardening tied to licence tier at boot
- [Phase 75]: secrets-data named Docker volume mounts at /app/secrets on agent — boot.log survives compose down/up cycles
- [Phase 75]: vault_service.py deleted (dead code — Artifact not in db.py, caused ImportError on any import)
- [Phase 76-01]: EE endpoint tests correctly skip on glibc host — musllinux EE wheel incompatible locally; tests will run in CI where EE wheel installs into Docker container
- [Phase 76-01]: 9 pre-existing test failures (test_job_service, test_models, test_sec01/02) and 6 collection errors confirmed pre-existing before Phase 76; out of scope

### Pending Todos

- Fix golden path install docs (remove bundled nodes from `compose.cold-start.yaml`)
- Marketing homepage on GitHub Pages
- USP: hello world under 30 mins (signing UX)
- Dashboard amber/red banner on GRACE/DEGRADED_CE state (deferred from v14.3 — backend API lands first)

### Blockers/Concerns

- main.py path-injection line numbers in the todo have drifted (todo references 2457/2461 but file is currently ~2152 lines) — run live CodeQL scan or check GitHub Security tab to find actual alert locations before implementing SEC-03
- Licence public key identity: `licence_service.py` needs a separate Ed25519 keypair from the job-signing key — confirm keypair exists or generate before Phase 73 begins

## Session Continuity

Last session: 2026-03-27T14:33:34.596Z
Stopped at: Completed 76-01-PLAN.md
Resume file: None
