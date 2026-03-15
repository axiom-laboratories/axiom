# Retrospective

## Milestone: v8.0 — mop-push CLI & Job Staging

**Shipped:** 2026-03-15
**Phases:** 3 (17, 18, 19) | **Plans:** 14

### What Was Built
- RFC 8628 OAuth device flow — MoP as its own IdP, browser approval page, JWT issuance
- `ScheduledJob` lifecycle status (DRAFT/ACTIVE/DEPRECATED/REVOKED) with scheduler enforcement
- `POST /api/jobs/push` upsert with dual-token verification (JWT identity + Ed25519 integrity)
- `mop-push` CLI — login, job push (DRAFT), job create (ACTIVE), Ed25519 signing locally
- Dashboard Staging tab — inspect script, finalize scheduling, one-click Publish
- OIDC v2 integration path documented in `docs/architecture/OIDC_INTEGRATION.md`

### What Worked
- Wave-based parallel plan execution kept phases fast (Phase 17 delivered in 5 plans)
- Playwright tests caught two real bugs: DASH-04 status field not persisted, PATCH route wrongly prefixed with `/api/`
- Keeping the CLI as a local `pip install ./mop_sdk` avoided PyPI complexity entirely

### What Was Inefficient
- Phase 17/18 commits landed but REQUIREMENTS.md checkboxes were never updated — required manual reconciliation at milestone close
- Dashboard build was not redeployed after Phase 19 code changes — tests initially hit stale JS

### Key Lessons
- After any backend route change, verify through the Caddy proxy (not direct to port 8001) — route prefixes interact with the `/api/*` strip rule
- Always redeploy dashboard build before running Playwright tests against the live stack
- DB migrations must be applied before restarting the agent container after schema-changing commits

## Cross-Milestone Trends

| Milestone | Phases | Plans | Key pattern |
|-----------|--------|-------|-------------|
| v8.0 | 3 | 14 | CLI + backend + UI in one milestone; Playwright as final gate |
