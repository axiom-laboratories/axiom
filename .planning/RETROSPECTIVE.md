# Retrospective

## Milestone: v7.0 — Advanced Foundry & Smelter

**Shipped:** 2026-03-16
**Phases:** 5 (11–15) | **Plans:** 34

### What Was Built
- Compatibility Engine — OS-family tagging on tools, two-pass blueprint validation (OS mismatch + dep confirmation), real-time tool filtering; 12/12 Playwright checks passed
- Smelter Registry — vetted ingredient catalog with CVE scanning (pip-audit), STRICT/WARNING enforcement modes, compliance badging on templates
- Package Repository Mirroring — local PyPI (pypiserver) + APT (Caddy) sidecars, auto-sync on ingredient add, air-gapped manual upload, pip.conf/sources.list injection, fail-fast enforcement at build time
- Foundry Wizard UI — 5-step guided composition wizard (Identity → Base Image → Ingredients → Tools → Review), JSON editor mode, full Smelter Registry integration
- Smelt-Check + BOM + Lifecycle — post-build ephemeral validation containers, JSON Bill of Materials capture, package index for fleet-wide BOM search, image lifecycle (ACTIVE/DEPRECATED/REVOKED) enforced at enrollment and work-pull

### What Worked
- Parallel execution of v7.0 and v8.0 phases (Phases 17-19 shipped while v7.0 was in progress) — milestones are independent enough to develop concurrently
- Soft-delete patterns (is_active, ingredient delete) caught early reduced future migration pain
- Unconditional fail-fast for mirror enforcement (separate from enforcement_mode gating) kept the two concerns cleanly separated and the behavior predictable

### What Was Inefficient
- Phase 13 required 3 gap-closure plans (13-06, 13-07, 13-08) after verification revealed missing frontend and test coverage — original 5 plans underestimated scope
- Phase 12 required 1 gap-closure plan (12-10) for SMLT-04 mirror-status enforcement gate that was missed in initial verification
- Test suite for Phase 13 failed on imports — pyproject.toml pythonpath config was missing and had to be added in gap-closure; should be a standard project convention
- ROADMAP.md became out of sync when v8.0 was archived before v7.0 completed — caused confusion at milestone close

### Patterns Established
- `pyproject.toml pythonpath=['puppeteer']` is required for test imports — document as project standard
- Sequential `side_effect` list in mock DB avoids brittle SQL-repr string matching (bound parameters make literal search unreliable)
- Gap-closure plans numbered N-06, N-07, N-08 after the N-05 verification plan — established as the standard recovery pattern

### Key Lessons
- Budget gap-closure plans in the original plan count — phases with complex service interactions (mirroring, enforcement) should expect 1-2 gap-closure plans
- Run full pytest suite after every plan, not just phase-targeted tests — regressions in adjacent modules are cheaper to catch early
- ROADMAP.md milestone ordering should match development order; shipping milestones out of order (v8.0 before v7.0) creates tracking confusion

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

## Milestone: v9.0 — Enterprise Documentation

**Shipped:** 2026-03-17
**Phases:** 9 (20–28) | **Plans:** 27

### What Was Built
- MkDocs Material docs site at `/docs/` — two-stage Dockerfile, Caddy routing, air-gapped (CDN-free via privacy + offline plugins)
- Auto-generated API reference from FastAPI OpenAPI schema at container build time
- Complete operator documentation: getting started E2E walkthrough, all 7 feature guides, security & compliance (mTLS, RBAC, audit, air-gap), symptom-first runbooks and FAQ
- Axiom rebranding: CLI renamed `axiom-push`, README, CONTRIBUTING, CHANGELOG, GitHub community health files, full MkDocs naming pass
- GitHub Actions CI/CD pipelines for multi-arch GHCR and PyPI OIDC release

### What Worked
- Stub-first nav pattern: create all stub files before content plans so `mkdocs build --strict` passes throughout — no broken builds between plans
- Admonition-as-gotcha pattern: warning/danger admonitions for known operator failure modes inline with the relevant step (not in a separate "Gotchas" section)
- Wave-based parallel execution: Phase 24 and 25 each delivered 4-5 guides in parallel waves without conflicts
- Symptom-first framing for runbooks: H3 headers are observable states ("Node shows offline but container is running") not component names — immediately searchable by operators in distress
- The CDN verification pattern (https:// prefix match vs. bare domain) caught a real false positive that would have shipped a broken air-gap claim

### What Was Inefficient
- INFRA-06 gap closure (Phase 28) was caused by a regression in Phase 22 that should have been caught at plan verification time — the privacy/offline plugin configuration was an explicit requirement in the Phase 20 plan
- ROADMAP.md milestones header was stale (listed "Phases 20-25, 28" missing 26 and 27) because phases were added late
- PyPI Trusted Publisher setup required manual org creation outside the milestone scope — this dependency should have been identified and either resolved or explicitly deferred before Phase 27 was planned

### Patterns Established
- `npx vitest run` (not `npm run test`) in CI to avoid watch mode hang
- id-token:write scoped per-job to PyPI publish jobs only — not at workflow level
- CDN verification: `grep -rq 'https://fonts.googleapis.com\|https://cdn.jsdelivr.net' /usr/share/nginx/html && echo FAIL || echo PASS`
- Docs container dummy env vars: `postgresql+asyncpg://dummy/dummy` and `API_KEY=dummy` required in Dockerfile builder stage for openapi.json generation
- Plugin ordering locked: `search → privacy → offline → swagger-ui-tag`

### Key Lessons
- Plan for dependency validation before documentation phases — if a guide describes a feature, verify the feature is actually in the state the guide claims (air-gap guide + INFRA-06)
- For branding milestones, do a grep pass for the old name before calling the phase complete — 21 docs files is a lot to audit manually
- PyPI/GitHub org dependencies should be explicit "pre-flight checklist" items at the start of a distribution phase, not discovered at the end

### Cost Observations
- 9 phases, 27 plans, 134 commits in 2 days
- Primarily documentation work — heavy on write/edit operations, light on Bash execution compared to infrastructure milestones
- Wave-based parallel execution effective: phases with 4-5 plans completed in the same number of agent invocations as phases with 2 plans

## Milestone: v10.0 — Axiom Commercial Release

**Shipped:** 2026-03-19
**Phases:** 5 (29–33) | **Plans:** 21

### What Was Built
- Job execution pipeline: stdout/stderr capture, script hash verification, retry machinery (attempt_number, job_run_id, retry_after, configurable backoff), timeout enforcement
- Runtime attestation: Ed25519 bundle signing on node, RSA PKCS1v15 server-side verification, attestation export endpoint, VERIFIED/FAILED/MISSING UI badge
- Environment tags (DEV/TEST/PROD): nodes declare in heartbeat, jobs route by env_tag, scheduler propagates, CI/CD dispatch API (POST /api/dispatch + status poll)
- Dashboard execution UI: History view with job/node/run/status filters, terminal-style stdout/stderr, attestation badge, attempt tabs, DefinitionHistoryPanel, env tag badges and filter on Nodes
- Licence compliance + release infra: LEGAL.md, NOTICE, PEP 639 pyproject.toml, axiom-laboratories org, PyPI OIDC Trusted Publisher, v10.0.0-alpha.1 on PyPI and GHCR

### What Worked
- Wave-based parallel execution for Phase 32 (7 plans): backend gap (32-01), test scaffolds (32-02), and feature plans (32-03 to 32-07) separated cleanly by dependency
- Audit-before-milestone-close workflow caught the RETRY-03 max_retries gap before archiving — the fix (outerjoin Job on list_executions) was a 3-line change that would have been a silent runtime bug
- Phase 33 (licence + release) was fully independent of all feature phases — running it in parallel with Phase 32 had zero conflicts
- outerjoin pattern for enriching ExecutionRecord with Job fields is clean and reusable — established as the pattern for future execution query enrichment

### What Was Inefficient
- Phase 32 required a gap-closure plan (32-07) for an attestation badge null guard that should have been caught during 32-03 implementation — small defensive check missed in the first pass
- RETRY-03 max_retries was not caught until the post-milestone audit: the field was implemented in the DB (Phase 29) but never joined through to the API response (Phase 32) — cross-phase field propagation needs explicit verification
- Nyquist VALIDATION.md files left in draft status across all 5 phases — compliance tracking process was not followed during this milestone

### Patterns Established
- `outerjoin(Job, Job.guid == ExecutionRecord.job_guid)` for enriching execution records with job-level fields (max_retries, env_tag, etc.) — avoids denormalising ExecutionRecord
- Attestation verification never raises exceptions: verification failure is a string status value, not a raised exception — keeps ExecutionRecord rows complete regardless of verification outcome
- job_run_id groups all retry attempts: UUID generated at dispatch and propagated through each retry attempt — enables per-run history queries without denormalising attempt data

### Key Lessons
- Cross-phase field propagation (DB column added in phase N, API response updated in phase M) needs an explicit checklist item in the phase M plan — "verify all DB fields introduced in prior phases appear in API responses"
- The audit-before-milestone-close gate is valuable: RETRY-03 was a silent bug (tests pass, badge never shows) that required the integration checker to surface — worth running before every milestone close
- Nyquist compliance tracking should be a plan-level gate, not a milestone-level optional — leaving VALIDATION.md in draft status across 5 phases accumulates process debt that's harder to pay down retroactively

### Cost Observations
- 5 phases, 21 plans, 92 commits over 2 days
- Mix of backend (29, 30, 31), frontend (32), and compliance/infra (33) — balanced workload across agent capabilities
- Phase 33 (release infra) required significant human operator work outside the codebase (GitHub org creation, PyPI publisher setup, tag push) — accounted for in timeline but not in plan count

## Milestone: v11.0 — CE/EE Split Completion

**Shipped:** 2026-03-20
**Phases:** 4 (34–37) | **Plans:** 15

### What Was Built
- CE isolation: stub routers return 402 for all EE routes, `ee_only` pytest marker, `NodeConfig` stripped of EE-only fields, CE pytest suite passes cleanly
- `axiom-ee` private repo: `EEPlugin` with 7 FastAPI routers + 15 EE SQLAlchemy tables; absolute imports throughout; async plugin loading wired into CE lifespan via `entry_points`
- Cython `.so` build pipeline: 12 binary wheels (py3.11/3.12/3.13 × amd64/aarch64 × manylinux/musllinux) via `cibuildwheel`; devpi internal wheel index in compose.server.yaml
- Ed25519 offline licence validation at EE startup; CE/EE edition badge in dashboard sidebar; MkDocs enterprise admonitions + licensing page

### What Worked
- `packages=[]` + `exclude_package_data` pattern for stripping `.py` from the wheel was the right call — Cython handles everything else automatically
- `entry_points` for EE plugin discovery is clean and keeps the CE codebase completely unaware of EE — no conditional imports, no try/except blocks in CE
- Excluding `__init__.py` from `ext_modules` (CPython bug #59828) was caught early in the Cython audit before any CI time was wasted

### What Was Inefficient
- REQUIREMENTS.md had EE-08 as Pending at milestone close — the commit message (Phase 35) said it was resolved, but the traceability table wasn't updated. Adds ambiguity at milestone review.
- No pre-flight audit was run before closing — the audit step was skipped. This meant gap discovery happened at completion rather than during development when gaps are cheaper to close.

### Patterns Established
- Cython `ext_modules` pattern: glob all `.py` files in `ee/`, exclude `__init__.py`, set `packages=[]` to avoid installing source
- `Annotated[int, Path()]` pattern required for FastAPI routers compiled with Cython (bare `path_param: int = Path()` triggers Cython compilation failure)
- async DDL via `run_sync` required in compiled modules — Cython can't handle `await engine.run_sync(Base.metadata.create_all)` directly

### Key Lessons
- Update traceability table at plan completion, not milestone close — stale Pending rows create noise at retrospective
- Run `/gsd:audit-milestone` before marking complete — skipping it produced 2 known gaps that could have been addressed during development
- devpi works well as an internal index but requires manual upload step on each EE version bump — document this in the runbook for whoever manages EE releases

### Cost Observations
- 4 phases, 15 plans, 44 commits over 2 days
- Cython compilation was the highest-risk unknown; resolved cleanly with cibuildwheel approach
- Phase 36 (build pipeline) was the densest in new tooling: cibuildwheel, devpi, manylinux/musllinux matrix — all new to the project

## Milestone: v11.1 — Stack Validation

**Shipped:** 2026-03-22
**Phases:** 8 (38–45) | **Plans:** 27

### What Was Built
- Teardown + install scripts: idempotent soft (PKI-preserving) and hard (true clean slate) teardown; CE verification covering table count, feature flags, admin re-seed safety
- EE test infrastructure: Ed25519 test keypair, editable `axiom-ee` install with patched public key — no Cython rebuild needed for validation
- 4 LXC nodes (DEV/TEST/PROD/STAGING): unique per-node JOIN_TOKENs, dynamic `incusbr0` bridge IP discovery, revoke/re-enroll cycle verified
- CE/EE validation passes: 7 CE stub routes return 402; 13-table CE assertion; 28-table EE assertion; licence startup-gating; RBAC on `/api/licence`
- Job test matrix: 8/9 scenarios genuinely PASS with real LXC nodes — fast/slow/concurrent/env-routing/promotion/crash/bad-sig/revoked-definition
- Foundry + Smelter scripted validation: STRICT CVE block, bad-base HTTP 500, dual-outcome build-dir test, air-gap mirror with iptables isolation, WARNING mode audit entry
- Gap report: 11 findings synthesised (0 critical, 2 major, 9 minor); 4 critical patches applied inline with regression tests; v12.0+ backlog seeded

### What Worked
- Scripted validation approach (Python scripts instead of manual checks) produced durable, re-runnable evidence for each requirement
- Dual-outcome test pattern for FOUNDRY-04 — treating both GAP CONFIRMED and GAP FIXED as [PASS] avoids test brittleness on implementation state
- Gap-closure plans (43-06, 43-07) as a mechanism to add real execution evidence after dry-run passes — clean separation of scripting from evidence gathering
- SKIP-not-FAIL pattern for environment-gated scripts (CE stack can't run EE Foundry) — honest pass rate without masking failures

### What Was Inefficient
- Phase 43 required 3 gap-closure plans (43-06, 43-07, 43-08) after initial runs hit the HTTP 500 wrapping bug, non-ONLINE nodes, and Python 3.12 global declaration syntax error — each discovered in sequence rather than caught in planning
- LXC node execution bootstrap (copy docker binary, tag image from registry) is undocumented; re-discovering it in Phase 43 cost multiple debug cycles
- Phase 42 fixed two production bugs (`app.state.licence` never populated, EE licence expiry bypass) that should have been caught in Phase 35/37 — CE+EE integration tests were missing
- run_job_matrix.py and run_foundry_matrix.py have no node pre-flight gate — SKIP exits count as passes; offline cluster reports 9/9 passed

### Patterns Established
- Per-requirement validation scripts in `mop_validation/scripts/verify_*.py` — one file per scenario, self-gating via SKIP, produces evidence in `reports/`
- `43-NN-MATRIX-EVIDENCE.md` as an evidence log format — captures terminal output, timestamps, pass/fail per scenario
- Rate-limit guard pattern (pause 60s after every 5th POST /auth/login call) for scripts that batch-authenticate
- MATRIX EVIDENCE file as the canonical source of truth for human-needed verification (not just VERIFICATION.md assertions)

### Key Lessons
- Provision LXC nodes earlier and keep them alive — node state drift between phases caused repeated re-enrollment work
- Add a node pre-flight gate to all matrix runners — SKIP-on-offline is honest but the runner should surface it explicitly
- Gap closure plans should be planned at phase start, not discovered during verification — budget 1-2 gap-closure slots per phase involving live infra
- `retriable=True` was absent from `node.py` (JOB-07 gap) — a node-side feature must be tested on a node, not just the orchestrator

### Cost Observations
- 8 phases, 27 plans, 134 commits over 3 days (2026-03-20 → 2026-03-22)
- 387 files changed; heavy on validation scripts and evidence documents
- Validation milestone is inherently serial (phases depend on prior phase infra) — less parallelism than feature milestones

## Cross-Milestone Trends

| Milestone | Phases | Plans | Key pattern |
|-----------|--------|-------|-------------|
| v7.0 | 5 | 34 | Infrastructure-heavy; gap-closure plans expected for complex service interactions |
| v8.0 | 3 | 14 | CLI + backend + UI in one milestone; Playwright as final gate |
| v9.0 | 9 | 27 | Documentation milestone; stub-first nav pattern; regression gap closure required |
| v10.0 | 5 | 21 | Security + observability + release; audit-before-close gate caught cross-phase propagation gap |
| v11.0 | 4 | 15 | Open-core split; Cython build pipeline as key technical risk; EE plugin via entry_points |
| v11.1 | 8 | 27 | Adversarial validation milestone; scripted evidence per requirement; gap-closure plans serial on live infra |
