---
gsd_state_version: 1.0
milestone: v11.0
milestone_name: CE/EE Split Completion
status: defining requirements
stopped_at: —
last_updated: "2026-03-19"
last_activity: 2026-03-19 — Milestone v11.0 started
progress:
  total_phases: 0
  completed_phases: 0
  total_plans: 0
  completed_plans: 0
  percent: 0
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-03-19)

**Core value:** Jobs run reliably — on the right node, when scheduled, with their output captured — without any step in the chain weakening the security model.
**Current focus:** Planning next milestone (v11.0)

## Current Position

Phase: Not started (defining requirements)
Plan: —
Status: Defining requirements
Last activity: 2026-03-19 — Milestone v11.0 started

## v10.0 Phase Summary

| Phase | Goal | Requirements | Status |
|-------|------|--------------|--------|
| 29 — Backend Completeness | Output capture + retry wiring complete and stable | OUTPUT-01, OUTPUT-02, RETRY-01, RETRY-02 | Not started |
| 30 — Runtime Attestation | RSA-signed execution bundles verified by orchestrator | OUTPUT-05, OUTPUT-06, OUTPUT-07 | Not started |
| 31 — Environment Tags + CI/CD Dispatch | First-class env tags + structured dispatch API | ENVTAG-01, ENVTAG-02, ENVTAG-04 | Not started |
| 32 — Dashboard UI | Execution history, retry state, attestation badges, env tags | OUTPUT-03, OUTPUT-04, RETRY-03, ENVTAG-03 | Not started |
| 33 — Licence + Release | LEGAL.md, NOTICE, pyproject.toml, PyPI Trusted Publisher, GHCR | LICENCE-01..04, RELEASE-01..03 | Not started |

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
- [Phase 27-02]: H3 subsections used for install options (not pymdownx.tabbed) — tabbed extension not present in mkdocs.yml; plan explicitly prohibits adding new extensions
- [Phase 27-02]: All installer files in puppeteer/installer/ rebranded including deploy_server.sh, loader/Containerfile, and tests banner — required to satisfy must_have truth of zero MoP strings across installer directory
- [Phase 27-01]: frontend-test uses npx vitest run not npm run test to avoid watch mode hang in CI
- [Phase 27-01]: id-token:write scoped per-job to PyPI publish jobs only — not at workflow level
- [Phase 27-03]: Task 2 (PyPI Trusted Publisher + GitHub Environments setup) deferred — GitHub org axiom-laboratories and PyPI project axiom-sdk do not exist yet; intentional, to be completed when org is created
- [Phase 27-03]: GHCR image path ghcr.io/axiom-laboratories/axiom retained as-is in release.yml — intended target org; no change needed until org is created and repo transferred
- [Phase 29-01]: All new DB columns nullable-only — safe migration for existing deployments, no NOT NULL constraints
- [Phase 29-01]: job_run_id on both Job and ExecutionRecord tables — Job groups the logical run, ExecutionRecord links each attempt directly without join
- [Phase 29-01]: Wave 0 stub pattern: model-field stubs use real assertions, implementation stubs use assert False with explicit plan reference
- [Phase 29]: Source-inspection test pattern used for pull_work() and report_result() — inspect.getsource() assertions confirm structural invariants without requiring full async mock setup
- [Phase 29]: orchestrator_hash always stored on ExecutionRecord (not node_hash) — independent verifiers can reproduce it from the job payload alone; hash_mismatch logs at WARNING only — enforcement deferred to Phase 30 attestation layer
- [Phase 29]: AST-based source extraction used to test _check_execution_mode() without triggering full module import side effects
- [Phase 29]: script_hash computed after signature verification passes, before runtime.run() — attestation hash order invariant preserved
- [Phase 33-01]: paramiko removed without replacement — zero application imports, eliminates LGPL-2.1 concern entirely
- [Phase 33-01]: puppeteer/pyproject.toml gets minimal compliance stub [project] section — not distributable, exists solely for License-Expression metadata
- [Phase 33-01]: PEP 639 string format: license = "Apache-2.0" (never table format); setuptools>=77.0 required for correct wheel metadata
- [Phase 33-02]: certifi MPL-2.0 assessed as compliant: read-only CA bundle lookup does not trigger file-level copyleft (MPL-2.0 Section 3.1)
- [Phase 33-02]: /docs/ remains behind CF Access for v10.0; review triggers: CE community onboarding OR 2027-03-04 token expiry (ADR-001 in DECISIONS.md)
- [Phase 33-04]: 1.0.0a0 is first published version on both testpypi and pypi — pending publisher auto-created the project on first OIDC push
- [Phase 33-04]: production PyPI publish succeeded alongside testpypi — both RELEASE-01 and RELEASE-02 satisfied; pypi.org package live
- [Phase 33-04]: 400 Bad Request on second testpypi push is expected: PyPI uses 400 for duplicate version, not 409 — first push success confirmed
- [Phase 30-runtime-attestation]: RSA sign/verify: 3-arg sign, 4-arg verify — distinct from Ed25519 2-arg pattern in signature_service.py
- [Phase 30-runtime-attestation]: Canonical attestation bundle: json.dumps(sort_keys=True, separators=(',',':')) — determinism proven by test
- [Phase 30-runtime-attestation]: attestation_verified states: 'verified', 'failed', 'missing', None — String(16) sufficient
- [Phase 30-runtime-attestation]: _build_and_sign_attestation() is a module-level function (not a method) — no self dependency, pure function for testability and reuse
- [Phase 30-runtime-attestation]: Hash-order invariant enforced in execute_task(): stdout_hash + stderr_hash computed from raw bytes BEFORE build_output_log() — scrubbing must not precede hashing
- [Phase 30-runtime-attestation]: attestation_service.py imported as module (from . import attestation_service) — preserves namespacing for call site clarity
- [Phase 30-runtime-attestation]: cert_serial extracted from bundle JSON in GET /attestation endpoint — avoids double cert parse, serial already in signed bundle
- [Phase 30-runtime-attestation]: test_revoked_cert_stores_failed uses AsyncMock.side_effect for multi-call DB sequence — faster than in-memory SQLite, consistent with phase 29/30 source-inspection pattern
- [Phase 31-environment-tags-cicd-dispatch]: env_tag normalisation: strip().upper() with None fallback for empty/whitespace — consistent with existing os_family pattern
- [Phase 31-environment-tags-cicd-dispatch]: DispatchStatusResponse.is_terminal is a plain bool field (caller provides it) — no automatic derivation in model
- [Phase 31-environment-tags-cicd-dispatch]: pull_work source-inspection tests intentionally RED in Plan 31-01 — ENVTAG-02 implementation deferred to Plan 31-02 per wave design
- [Phase 31-environment-tags-cicd-dispatch]: migration_v34.sql uses IF NOT EXISTS — safe for existing Postgres deployments; fresh deployments handled by create_all
- [Phase 31-02]: pull_work env_tag guard placed AFTER existing env: prefix isolation block — backward compat preserved; new column check is additive
- [Phase 31-02]: node.env_tag overwritten on every heartbeat — node.py is source of truth; operator override deferred to Phase 32 (ENVTAG-03)
- [Phase 31-02]: ENV_TAG read inside heartbeat_loop() per-iteration — live reload without container restart
- [Phase 31-environment-tags-cicd-dispatch]: poll_url built with PUBLIC_URL env var fallback to request.base_url — avoids localhost URLs in Docker
- [Phase 31-environment-tags-cicd-dispatch]: _TERMINAL_STATUSES constant defined at module level in main.py adjacent to dispatch routes
- [Phase 31-environment-tags-cicd-dispatch]: scheduled_job_id added to JobCreate as Optional[str]=None — dispatch route was already passing it, model needed to accept it without validation error
- [Phase 33]: Plan 33-03 deferred to gap-closure plan 33-04 — GitHub org axiom-laboratories and PyPI project axiom-agent-sdk did not exist when 33-03 was scheduled; 33-04 completed all objectives on 2026-03-18
- [Phase 32-01]: attestation_verified exposed as Optional[str] = None on ExecutionRecordResponse — matches DB String(16) column; accepts 'verified', 'failed', 'missing', or None
- [Phase 32-01]: scheduled_job_id filter uses subquery through jobs table (not join) — ExecutionRecord has no direct FK to ScheduledJob; chain is ScheduledJob.id -> Job.scheduled_job_id -> Job.guid -> ExecutionRecord.job_guid
- [Phase Phase 32-02]: getAllByText used instead of getByText for History regression guards — filter labels appear in multiple DOM nodes
- [Phase Phase 32-02]: fireEvent used instead of userEvent.click — @testing-library/user-event not installed; avoids adding dependency for JobDefinitions tests
- [Phase 32-03]: font-mono class reserved for log area container only — header metadata uses style={{ fontFamily: 'monospace' }} to avoid querySelector collision in tests
- [Phase 32-03]: scrollIntoView called with ?. optional chaining — jsdom does not implement it, crashes without guard; behavior identical in real browsers
- [Phase 32]: JobDefinitions uses inline DefinitionHistoryPanel component (not a separate file) — master-detail split stays contained in one view file
- [Phase 32]: History.tsx definitions query uses queryKey definitions-for-filter separate from executions query — allows independent caching
- [Phase 32]: Filter dropdown only renders when env tags present; displayNodes filters grid; Radix Select scrollIntoView mocked in tests
- [Phase 32]: getAttestationBadge: verified == null guard + ?? 'missing' call-site fallback so DB NULL rows always render NO ATTESTATION badge

### v10.0 Research Flags (carry into planning)

- **Phase 30 (Attestation):** Node mTLS key is RSA-2048 — NOT Ed25519. Attestation signing uses `key.sign(data, padding.PKCS1v15(), hashes.SHA256())` (3 args). RSA verify on orchestrator uses 4 args. Do NOT copy from `signature_service.py`. Unit test RSA sign/verify round-trip with a test cert fixture before implementing node-side code.
- **Phase 29/30:** Attestation hash order invariant — hash raw bytes FIRST, then scrub, then truncate, then store. Computing hashes after scrubbing means independent verifiers cannot reproduce them.
- **Phase 29:** Output retention pruning must use SQLite-compatible delete pattern — `DELETE WHERE rowid IN (SELECT rowid ... LIMIT N)`, NOT `DELETE WHERE id IN (SELECT ... LIMIT N)`.
- **Phase 31 (CI/CD Dispatch):** The 409 response contract when no eligible node exists must be confirmed stable before being documented as the CI/CD integration API — once published it cannot change without a breaking-change notice.
- **Phase 33:** paramiko LGPL-2.1 linkage assessment: if EE wheel bundling creates static linking scenario, replace paramiko with asyncssh (MIT). This becomes an implementation task in Phase 33.
- **Phase 33:** PyPI pending publisher must be configured before the first version tag — configure and immediately dry-run against test.pypi.org to catch OIDC name mismatches.

### Roadmap Evolution

- Phase 26 added: Axiom Branding & Community Foundation (from AXIOM_RELEASE_PLAN.md Phase 3)
- Phase 27 added: CI/CD, Packaging & Distribution (from AXIOM_RELEASE_PLAN.md Phase 4)
- v10.0 roadmap created 2026-03-17: Phases 29–33 derived from 21 requirements

### Pending Todos

- [ ] Investigate `test_report_result` pre-existing failure (noted in Phase 17 summary as baseline, not a regression)
- [ ] Confirm public /docs/ access decision (RELEASE-03) before Phase 33 closes
- [ ] Decide on `failed_node_ids` retry exclusion column during Phase 29 planning (research flag — defer as MIN or include in v10.0)

### Blockers/Concerns

None — v9.0 complete. Key open items for v10.0:
- PyPI Trusted Publisher setup blocked on `axiom-laboratories` GitHub org creation (Phase 33)
- CF Access policy enforcement for /docs/* deferred (local routing confirmed working) — decision required for RELEASE-03
- paramiko LGPL-2.1 assessment pending (Phase 33 — may trigger asyncssh migration)

## Session Continuity

Last session: 2026-03-19T14:24:07.772Z
Stopped at: Completed 32-06-PLAN.md
Resume file: None
Next action: `/gsd:plan-phase 29`
