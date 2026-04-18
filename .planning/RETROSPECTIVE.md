# Retrospective

## Milestone: v23.0 — DAG & Workflow Orchestration

**Shipped:** 2026-04-18
**Phases:** 19 (146–164) | **Plans:** 49
**Duration:** 3 days (2026-04-15 → 2026-04-18) | **Commits:** 26

### What Was Built

**Workflow Data Model & CRUD (Phases 146–148):**
- `Workflow`, `WorkflowStep`, `WorkflowEdge`, `WorkflowRun`, `WorkflowRunStep` SQLAlchemy models; full CRUD API with server-side DAG re-validation on every update
- DAG validation via networkx: cycle detection, topological sort, 30-level depth limit; cycle error returns node IDs for UI highlighting
- Workflow delete blocked when active WorkflowRuns exist; "Save as New" auto-pauses existing cron schedule to prevent ghost execution

**Execution Engine (Phases 149–152):**
- BFS topological dispatch releases steps level-by-level; only steps with all predecessors completed are eligible for dispatch
- `SELECT…FOR UPDATE` atomic concurrency guard in `advance_workflow()` prevents duplicate step dispatch under concurrent completions
- WorkflowRun lifecycle: RUNNING → COMPLETED / PARTIAL / FAILED / CANCELLED; cascading cancellation aborts all ASSIGNED/RUNNING downstream jobs when a step fails
- PARTIAL status correctly absorbed when FAILED-branch steps consume the failure without propagating it

**Gate Nodes (Phases 153–154):**
- IF gate evaluates conditions against `/tmp/axiom/result.json` with 6 operators (eq, neq, gt, lt, contains, exists); first matching branch wins; unmatched cascades FAILED
- AND/JOIN gate: all incoming branches must complete; OR gate: first completing branch releases downstream; PARALLEL fan-out dispatches multiple independent branches concurrently; SIGNAL_WAIT pauses until named signal posted

**Triggers & Parameters (Phases 155–157):**
- Manual trigger from dashboard with parameter values at trigger time; cron schedule via APScheduler
- Webhook endpoint (`POST /api/webhooks/{id}/trigger`) with HMAC-SHA256 signature, timestamp freshness (±5 min), and 24h nonce dedup via Redis-backed or DB-backed dedup table
- WORKFLOW_PARAM_* env var injection into each step's container — signed script content never modified post-signing

**Dashboard UI (Phases 158–163):**
- Read-only auto-layout DAG visualization using elkjs layered layout; live step status overlay during active WorkflowRun (colour-coded: PENDING/RUNNING/COMPLETED/FAILED/CANCELLED)
- WorkflowRun history list with trigger type, status, started/completed, duration; step drill-down with job output, logs, and result.json structured output
- Unified schedule view endpoint: single API call returns heterogeneous schedule entries with JOB and FLOW badges; frontend renders both types uniformly
- Visual Workflow composer: drag ScheduledJob steps onto ReactFlow canvas, connect with directed edges; real-time cycle highlighting; depth warning at 25+ steps; inline IF gate condition config panel

**Adversarial Audit Remediation (Phase 164):**
- mTLS enforcement hardened: client cert validation via `ssl.SSLSocket.getpeercert()` at Python layer (not just TLS handshake) with CRL table check
- Foundry injection recipe whitelist: exact command matching against approved package manager invocations; validated at API layer and at Dockerfile generation time
- Alembic two-layer startup: `create_all` for fresh installs, `alembic upgrade head` for existing deployments; 48 legacy SQL migration files archived
- Caddy internal TLS: agent container now reachable via HTTPS from other services; fixes internal service-to-service communication
- Public keys externalized to environment variables — no hardcoded cryptographic material in source; frontend-backend gaps (auth.ts 402 handler, /api/ prefix audit, recipe validation UI) closed

### What Worked

- **BFS over DFS for dispatch** — wave-level parallelism is natural: all steps at depth N can run concurrently without risk of deadlock; the design came out of a single planning session and held throughout
- **networkx for DAG validation** — battle-tested graph library meant zero custom graph code; `find_cycle()` returns the exact cycle edge for UI highlighting; `topological_sort()` gives dispatch order directly
- **ReactFlow for the visual editor** — first-class React integration meant drag, handles, and edge routing just worked; the main integration work was mapping Axiom step types to ReactFlow node types
- **`/tmp/axiom/result.json` contract for IF gates** — simple filesystem contract; node writes structured output, orchestrator reads it after job completes; no server-side involvement in condition evaluation; scripts can produce this output trivially
- **Phase 164 adversarial audit as a dedicated phase** — treating the security audit as a standard GSD phase (with PLAN, RESEARCH, SUMMARY) gave it the same rigour as a feature phase; all 7 items closed with tests

### What Was Inefficient

- **Three separate v23.0 milestone entries in ROADMAP.md** — the milestone had been created in three chunks (v23.0 core, v23.1, v23.0 Tech Debt Closure); collapsing these into a single shipped entry at milestone close required non-trivial ROADMAP.md surgery. Pattern: create one milestone entry per milestone from the start; avoid suffixed variants (v23.1) mid-milestone
- **Phase 149 progress table stuck at "1/3 in progress"** — stale ROADMAP.md progress table entry survived through the full milestone and was only caught by the milestone audit. Pattern: update progress table atomically when SUMMARY.md is written
- **TRIGGER-01..05 requirements split across phases 155–157** — the trigger phases were small; could have been collapsed into 1–2 phases without loss of quality. Pattern: phases under 2 plans are candidates for consolidation at planning time

### Patterns Established

- **`/tmp/axiom/result.json` as the IF gate output contract** — scripts write structured JSON there; gate evaluates it post-completion; no changes to the signing model required
- **WORKFLOW_PARAM_* env var injection pattern** — the only safe way to pass runtime values into Ed25519-signed scripts is via environment; this pattern should be extended to any future dynamic input channel
- **Two-layer Alembic startup** — `create_all` first (idempotent for fresh installs), then `alembic upgrade head` (handles schema evolution); never replace `create_all` outright or fresh installs will fail with no migration history
- **Adversarial audit as a milestone-closing phase** — Phase 164 model: run a structured audit of the milestone's security surface as the final phase before closure; produces concrete PLAN tasks, not just a report

---

## Milestone: v22.0 — Security Hardening

**Shipped:** 2026-04-15
**Phases:** 14 (132–145) | **Plans:** 165 (includes Nyquist validation and documentation cleanup)
**Duration:** 4 days (2026-04-12 → 2026-04-15) | **Commits:** 26

### What Was Built

**Container Hardening (Phases 132–136):**
- All orchestrator and node images run as `appuser` (UID 1000); volumes and app dirs owned by UID 1000; upgrade path from root containers handled
- `cap_drop: ALL` + `security_opt: no-new-privileges` on all 7 compose services; Caddy gets `cap_add: NET_BIND_SERVICE`; Postgres port restricted to `127.0.0.1:5432`
- `privileged: true` removed from node containers; Docker/Podman socket auto-detected in `runtime.py`; `node-compose.podman.yaml` variant ships alongside Docker variant
- `mem_limit` and `cpus` set on all orchestrator services; `Containerfile.node` strips Podman/iptables/krb5 packages; Foundry-generated Dockerfiles inject `USER appuser` per OS family

**EE Licence Protection (Phases 137–140):**
- `_verify_wheel_manifest()` 6-step gate (existence → JSON → required fields → SHA256 hash → base64 decode → Ed25519 verify) before any EE wheel install
- HMAC-SHA256 boot log with `hmac:` prefix on new entries; legacy plain-SHA256 accepted on read; constant-time comparison; no forced migration
- Entry point whitelist (`ep.value == "ee.plugin:EEPlugin"` exact match) validated on startup and live-reload; `ENCRYPTION_KEY` absence raises hard `RuntimeError` — no dev fallback
- `gen_wheel_key.py` (one-time keypair generation, 0600 file perms, Python bytes literal output) + `sign_wheels.py` (per-wheel manifests, `--verify` mode, `--deploy-name` flag) release CLI tools

**Quality (Phases 141–145):**
- Compliance documentation cleanup: VERIFICATION.md for Phase 139, all stale REQUIREMENTS.md checkboxes fixed
- 23 tests for wheel signing tools; 15 tests for container security; full Nyquist validation across all 11 implementation phases
- All phases marked `nyquist_compliant: true`; full regression suite (puppeteer + axiom-licenses) passing; 103 tests across EE phases

### What Worked

- **Separation of concerns between container hardening and EE protection** — the two workstreams were genuinely independent and could be developed in any order; the roadmap correctly identified this and laid them out as separate phase groups
- **6-step manifest verification gate structure** — each step catches a distinct failure class; the step-by-step design made test coverage straightforward and error messages informative
- **`hmac:` prefix approach for boot log** — zero-migration backward compat at no cost; mixed-format logs coexist transparently; the same pattern is reusable if further digest schemes are added
- **Nyquist validation phases (143–145) as explicit milestone phases** — treating test validation as first-class milestone work (not an afterthought) meant test coverage was verified before the milestone was marked shipped
- **`/proc/1/status` for UID verification** — platform-independent; caught the `ps` flag divergence between Alpine and Debian early

### What Was Inefficient

- **Phase 138 had 2 stale test expectations found during Nyquist validation** — the initial test implementation used regex patterns from an earlier design draft; both failed under Phase 144. Pattern: write tests closer in time to the implementation they cover, or use a TDD approach
- **Progress table in ROADMAP.md had malformed v22.0 rows** — some rows had columns shifted or missing; these were not caught during phase execution and required cleanup at milestone close. Pattern: validate progress table format as part of plan completion protocol
- **gsd-tools `roadmap analyze` returned empty phases** — the tool reads ROADMAP.md, not v22.0-ROADMAP.md; phase data for the active milestone lives in a separate file that the tool doesn't know about. Workaround: read files directly. Pattern: tool is designed for archived milestones; active milestone data requires direct file access

### Patterns Established

- Two-file container security approach: `Containerfile` changes (hardening) paired with compose changes (caps, ports, limits) — both needed for full effect; verify together
- `pytest.skip()` (not `xfail`) when a test depends on optional infrastructure (e.g., node container not running in server-only compose) — semantically correct; skip = inapplicable, xfail = expected to fail
- Nyquist validation phases at 3 levels: implementation (phase-level automated tests), integration (cross-phase regression), milestone audit (requirement coverage) — all three are distinct and complementary

---

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

## Milestone: v12.0 — Operator Maturity

**Shipped:** 2026-03-24
**Phases:** 11 (46–56) | **Plans:** 38

### What Was Built
- Multi-runtime execution: Python, Bash, and PowerShell via unified `script` task type with container temp-file mounts, Ed25519 verification, and server-authoritative `display_type` labels
- Guided dispatch form: structured Name/Runtime/Script/Targeting/Sign form with live JSON preview; Advanced mode via one-way confirmation gate; GuidedDispatchCard initialValues for edit-then-resubmit
- Job detail drawer: inline stdout/stderr, node health snapshot at execution time, retry countdown, resubmit + bulk actions (cancel/resubmit/delete with floating bar)
- Live Queue view: WebSocket-driven two-section table (Active/Recent), DRAINING node badges, adjustable recency window; DRAINING state machine (drain/undrain endpoints, auto-offline transition)
- Per-node detail drawer: running job, queued jobs, 24h history, capabilities; dispatch diagnosis callout on PENDING jobs
- 9-axis cursor-paginated job filtering: status/runtime/task/node/tags/created-by/dates; dismissible chips; streaming CSV export; page-based node list
- Scheduling health: ScheduledFireLog, LATE/MISSED detection, recharts sparklines in HealthTab; job templates CRUD; execution pin/unpin; admin retention config; per-job CSV export
- Security hardening: HMAC-SHA256 on signature_payload (SEC-02), SECURITY_REJECTED audit log entries (SEC-01), scheduled job DRAFT state on stale signature (SCHED-01–04)
- Integration fixes: script_content key alignment (INT-01), Queue URL prefix fix (INT-02), CSV export route fix (INT-03), retry/provenance fields in list_jobs (INT-04) — all 7/7 E2E tests passing

### What Worked
- Milestone audit before completion was effective — the audit surfaced 4 real integration bugs (INT-01 through INT-04) that became Phase 54/56 targets; the milestone closed cleaner than any prior feature milestone
- Wave-based parallelism inside phases worked well for TDD phases (Wave 0 stubs → Wave 1 service → Wave 2 routes → Wave 3 frontend); kept each plan independently verifiable
- Having a dedicated "Bug Fix Blitz" phase (54) and "Integration Bug Fixes" phase (56) explicitly for gap closure gave those fixes first-class tracking instead of buried amendment commits
- Verification phases (55) for retroactive VERIFICATION.md gaps were worth the overhead — Phase 48 had been unverified for the entire milestone

### What Was Inefficient
- INT-01 (`script` vs `script_content` key mismatch) survived from Phase 50 through Phase 54 because guided-form jobs appeared to succeed at the API level (201 returned) but silently failed at node execution — no server-side validation of the payload key after dispatch
- Phase 56 was essentially Phase 54 repeated — the same 4 integration gaps had to be re-fixed because Phase 54's fixes were applied to the wrong layer or didn't propagate to the E2E test stack correctly; a live-stack smoke test after Phase 54 would have caught this immediately
- 24 human-verify items were outstanding at audit time — accumulating these across phases creates a verification debt that's hard to clear at milestone close
- Phase 47 had 4 human-verify items deferred for "live-stack confirmation" that were never explicitly resolved in verification artifacts

### Patterns Established
- Integration bug phases (54, 56) work best when paired with a concrete E2E test file (`test_phase56_integration.py`) — the test file makes the fix criteria unambiguous and provides pass/fail evidence in one place
- Milestone audit should be run before the final 1-2 phases, not after all phases complete — gives time to plan gap-closure phases inside the milestone rather than retrofitting
- Retrospective VERIFICATION.md phases (like Phase 55) are cheaper when done close to the original phase; the Phase 48 case required re-reading all the code to reconstruct what had been built

### Key Lessons
- Any new dispatch path (guided form, scheduled job, resubmit) should have an E2E smoke test that confirms the script reaches the node with a non-empty payload — this would have caught INT-01 immediately
- Do not accumulate human-verify items across phases; resolve them inline or create a dedicated verification plan within the same phase
- A "verification pass" phase at the end of every other feature phase cluster is worth the overhead; Phase 55 cleared 4 weeks of verification debt in 2 plans

### Cost Observations
- 11 phases, 38 plans, 47 feat commits over 2 days (2026-03-22 → 2026-03-24)
- 263 files changed, +31,143 / -17,271 lines
- Mix of TDD phases (49, 50, 51, 52, 53), direct-implementation phases (46, 47, 48), and gap-closure phases (54, 55, 56)
- Parallelism was higher than v11.1 (feature work); wave-based execution within phases kept each plan 30-60 min

## Milestone: v13.0 — Research & Documentation Foundation

**Shipped:** 2026-03-24
**Phases:** 4 (57–60) | **Plans:** 8

### What Was Built
- Parallel job swarming design doc: fan-out vs work-queue use case analysis, pull-model race condition solution (pre-pin reservation), `swarm_records` data model sketch, external system comparison (Celery, Kubernetes Jobs, Ray), tiered build/defer recommendation with draft POST /api/jobs/swarm API shape
- Organisational SSO design doc: OIDC protocol recommendation over SAML (5 IdPs covered), JWT bridge exchange flow with `token_version` invalidation, IdP group → MoP role mapping, Cloudflare Access integration pattern, EE plugin air-gap isolation strategy, TOTP 2FA interaction policy
- Complete `.env.example` operator reference with grouped sections and inline generation commands for SECRET_KEY, ENCRYPTION_KEY, and API_KEY
- Docker deployment guide covering end-to-end env var requirements for the release container
- Axiom docs site branding: Fira Sans (code: Fira Code), crimson primary colour, geometric SVG logo — visual identity now matches the dashboard
- Jobs and Nodes feature guides: unified `script` task type, guided form, bulk ops, Queue Monitor, DRAINING state
- Scheduling Health section extended with fire log metrics, LATE/MISSED explanation, API endpoint reference, and retention guidance
- Quick-reference HTML files moved to `docs/docs/quick-ref/`, rebranded to Axiom, course accuracy-reviewed for deprecated terminology, operator guide updated with Queue and Scheduling Health content

### What Worked
- All 4 phases ran fully in parallel (no dependencies between them) — the wave structure was trivial and all plans executed cleanly in one day
- Research-only phases (57, 58) produced real design artefacts that future phases can consume directly — no architecture decisions needed to be re-made during planning
- MkDocs `--strict` as the documentation build gate was effective — caught nav configuration issues immediately before any SUMMARY was written
- Targeted per-occurrence HTML replacements (rather than global find-replace) prevented corruption of base64-encoded content inside the course HTML

### What Was Inefficient
- No milestone audit was run; the milestone was low-risk (no executable code) so this was fine here, but the pattern of skipping audits for "lightweight" milestones is worth flagging for future reference
- The progress table in ROADMAP.md had malformed rows for phases 57–60 (missing Milestone column) — a minor formatting inconsistency that accumulated because these phases were added in a hurry during milestone start

### Patterns Established
- Research phases work well as a parallel pair at the start of a milestone — they can produce design docs without any other phase unblocking them, and the docs become consumable input for the next feature milestone's planning
- HTML quick-reference files inside MkDocs work as passthrough static files — no special plugin needed, `mkdocs.yml` nav just references them by path

### Key Lessons
- A "research + docs" milestone is a legitimate way to reset between large feature milestones — it grounds the next build cycle and clears accumulated documentation debt without the complexity or risk of feature work
- Design documents should specify API shapes and data models, not just concept descriptions — the swarming doc's draft `POST /api/jobs/swarm` shape makes it directly actionable; the SSO doc's JWT bridge spec does the same

### Cost Observations
- 4 phases, 8 plans, 1 day (2026-03-24)
- 46 files changed, +10,962 / -69 lines
- Pure documentation/content work; no backend or frontend code changes
- All 4 phases executed in parallel in two waves; fastest milestone execution by plan-count ratio

## Milestone: v14.0 — CE/EE Cold-Start Validation

**Shipped:** 2026-03-25
**Phases:** 5 (61–65) | **Plans:** 14

### What Was Built
- LXC cold-start environment: Docker-in-LXC provisioner (`provision_coldstart_lxc.py`) with AppArmor pivot_root workaround, `compose.cold-start.yaml` with hardcoded SAN, PowerShell 7.6 direct .deb install, EE test licence generator
- Agent scaffolding: Tester `GEMINI.md` with docs-only first-user persona; HOME isolation at `/root/validation-home`; `monitor_checkpoint.py` file-based checkpoint protocol; CE/EE scenario scripts with per-step checklists
- CE cold-start run: 6 critical doc/code gaps found and patched mid-milestone (EXECUTION_MODE, node image tag, AGENT_URL, admin password discovery, JOIN_TOKEN CLI path, docs site path reference)
- EE cold-start run: EE plugin activation verified with injected licence; all 3 runtimes (Python/Bash/PowerShell) confirmed to COMPLETED; Execution History EE feature verified; CE-gating gap found (`/api/executions` ungated)
- Friction synthesis: `synthesise_friction.py` (stdlib-only, offline) + `cold_start_friction_report.md` — NOT READY verdict; 5 open product BLOCKERs; cross-edition comparison table; actionable per-finding recommendations

### What Worked
- Orchestrator-assisted fallback when Gemini hit quota limits: running the scenario manually via doc-following + API dispatch still produced valid friction evidence — the checkpoint protocol wasn't needed for the fallback, but the scenario scripts were essential
- Pre-loading Docker images from host into LXC via `docker save | docker load` was the correct pattern — compose build contexts are not available inside the container
- Unique FRICTION file names (FRICTION-CE-INSTALL.md, FRICTION-CE-OPERATOR.md etc.) prevented silent overwrites across 4 separate friction files
- Fixing blockers mid-Phase-63 rather than pausing preserved context and allowed the CE operator run to proceed without context reset

### What Was Inefficient
- Phase 63 required an unplanned Plan 63-04 to fix 6 doc/code gaps before Plan 03 could run — should budget a "gap fix" sub-plan in adversarial validation phases
- Gemini free-tier quota (20–250 RPD) hit on both CE and EE runs — free tier is not viable for any scenario requiring 80–120 API calls; a paid API key should be a prerequisite check before Phase 63 starts, not discovered mid-run
- `confirm_ce_gating()` in Phase 64 used `docker compose restart` (doesn't re-read env vars) instead of `--force-recreate` — script bug not caught until the finding was documented in Phase 65
- HOME isolation approach (settings.json only in `/root/validation-home`) is a workaround; a proper Gemini CLI `--no-config` flag would be cleaner

### Patterns Established
- **Adversarial validation phase budget**: Add a "gap fix" sub-plan as Plan N+1 in any phase where doc accuracy is being tested — blockers are expected, not exceptional
- **Gemini API tier check**: Verify Tier 1 paid key is available before any scenario run phase — free tier is too restrictive for full-session tester agents
- **Unique friction file naming**: `FRICTION-{EDITION}-{PHASE}.md` prevents silent overwrites and makes synthesis deterministic
- **Stdlib-only synthesis**: Offline friction synthesis with no LLM calls is faster, cheaper, and reproducible — use for all report generation

### Key Lessons
- First-user doc accuracy is harder to validate than first-user functionality — the CE installation path failed on doc gaps (wrong image tag, missing EXECUTION_MODE) not code bugs
- A Gemini agent following docs cold is a much more rigorous test than a developer running the same steps — developers skip undocumented prerequisites implicitly
- The CE-gating gap (`/api/executions` returning 200 in CE mode) was only discovered because the EE operator path explicitly confirmed Execution History was available, then re-tested on CE

### Cost Observations
- 5 phases, 14 plans, 2 days (2026-03-24 → 2026-03-25)
- 178 files changed, +39,323 / -1,614 lines (includes a 6MB EE wheel binary)
- Mixed milestone: infrastructure scripting (Python), docs fixes, one backend fix, synthesis script
- Gemini API quota limits forced orchestrator-assisted mode — cost-efficient but reduced autonomy

## Milestone: v14.1 — First-User Readiness

**Shipped:** 2026-03-26
**Phases:** 5 (66–70) | **Plans:** 9

### What Was Built
- Backend: CE-gated all 7 execution-history routes with 402 stubs in `ee/interfaces/executions.py`; real implementations moved to EE router; PowerShell arm64 `TARGETARCH` platform guard in `Containerfile.node`
- Getting-started docs: `install.md`, `enroll-node.md`, `first-job.md` fully rewritten with pymdownx.tabbed tab pairs, CLI alternatives for all GUI steps, admin password setup step, GHCR install path, Docker socket mount note, pre-dispatch `!!! danger` callout
- EE docs: `/api/admin/features` purged from all EE getting-started pages; `AXIOM_EE_LICENCE_KEY` removed from `licensing.md`; full 9-key feature JSON shown verbatim
- CI/CD: `setuptools-scm` dynamic versioning in `pyproject.toml` (no more hardcoded `1.0.0`); Docker metadata tag fixed to `type=ref,event=tag`; `mkdocs --strict` CI gate added
- Gap closure (Phase 70): `d['token']` field extraction fixed in `enroll-node.md` CLI tab; Cold-Start install tabs added to `install.md` Steps 3–4

### What Worked
- Phase 70 gap closure was clean because the v14.1 audit (`/gsd:audit-milestone`) identified the exact two integration failures (MISS-01, FLOW-01) before completion was declared — audit-before-complete prevented a false READY verdict
- All 17 requirements satisfied by the time auditing ran — only integration gaps (not requirement gaps) needed closure
- Keeping CE stubs in `ee/interfaces/executions.py` rather than inline in `main.py` preserved the CE/EE boundary clearly — easier to review and test in isolation
- Tab pair pattern (`=== "Dashboard"` / `=== "CLI"`) established in Phase 67 was immediately reusable in Phase 68 EE docs without re-litigating the syntax

### What Was Inefficient
- Phases 67–68 planned for 3+1 plans but the integration audit found Phase 70 was needed — the Phase 67 verification plan (67-03) should have included a more comprehensive CLI path end-to-end check to catch the `d['token']` regression before audit
- Phase 69 (CI fixes) was inserted as a gap between original scope (66–68) and completion — CI pipeline correctness should be scoped into release-adjacent milestones from the start, not discovered via gaps

### Patterns Established
- **Audit before complete**: `/gsd:audit-milestone` as a hard gate before `/gsd:complete-milestone` caught two integration failures that would have shipped as doc-silent regressions
- **`mkdocs --strict` in CI**: Any milestone touching docs should gate on `mkdocs build --strict` — catches anchor, tab, and admonition errors before they reach users
- **CE stub pattern**: EE-gated routes follow `interfaces/<feature>.py` (stub) + `routers/<feature>_router.py` (real) + mount in `ee/__init__.py` — consistent structure enables systematic testing

### Key Lessons
- A "remediation milestone" (fixing known bugs and doc gaps) is faster than a feature milestone but requires the same verification rigor — every fix can introduce regressions
- The `d['token']` regression in `enroll-node.md` was introduced during Phase 67 rewriting; `enroll-node.md` was freshly rewritten but the CLI tab used the wrong field name. Tab-pair rewrites need explicit API contract verification, not just content migration
- `synthesise_friction.py` from v14.0 was reusable for v14.1 gap synthesis — stdlib-only offline tools are long-lived

### Cost Observations
- 5 phases, 9 plans, 1 day (2026-03-25 → 2026-03-26)
- 266 files changed, +8,579 / -31,261 lines (net -22,682: large doc restructure deleted generated site files)
- Remediation milestone: primarily docs + 1 backend change + 1 CI change — low LOC cost relative to impact
- 59 commits; no context resets required

## Milestone: v14.3 — Security Hardening + EE Licensing

**Shipped:** 2026-03-27
**Phases:** 5 (72–76) | **Plans:** 8

### What Was Built
- Phase 72 — Security hardening: `html.escape()` for XSS on device-approve, `validate_path_within()` path traversal guard (vault + docs), bounded email regex for ReDoS, API_KEY hard crash removed, `nosniff` header on CSV export; 18 security tests GREEN
- Phase 73 — EE licence system: `licence_service.py` with EdDSA JWT validation, VALID/GRACE/EXPIRED/CE state machine, hash-chained boot-log clock-rollback detection; `tools/generate_licence.py` offline CLI; `/api/licence` endpoint, `enroll_node` node-limit 402, DEGRADED_CE `pull_work` guard
- Phase 74 — Dashboard alignment: `useLicence.ts` rewritten to match actual backend response; EE badge colour states, grace/expired banner, Admin licence section with status badge and expiry date; 15 frontend tests GREEN
- Phase 75 — Operational hardening: `secrets-data` named volume for persistent `boot.log`; `vault_service.py` dead code deleted; `check_and_record_boot(licence_status)` ties enforcement to licence tier; `main.py.bak` removed
- Phase 76 — Tech debt closure: stale `test_licence.py` endpoint tests updated; dead `API_KEY` removed from `compose.cold-start.yaml`; orphaned `vault_service.cpython-312.pyc` deleted

### What Worked
- TDD RED→GREEN pattern executed cleanly — Phase 72 Wave 0 scaffold (6 security tests RED) turned GREEN in 7 minutes; Phase 73 7 RED tests turned GREEN in 9 minutes combined; consistency across phases shows the pattern is repeatable
- Audit before completion (`v14.3-MILESTONE-AUDIT.md`) correctly flagged the 3 tech debt items that became Phase 76 — the audit-first workflow is paying off
- Licence validation placed in CE code from the start (not EE plugin) prevented the architectural trap of circular import at plugin load time — pre-planning decision note in STATE.md saved a false start
- `validate_path_within()` placed in `security.py` rather than `vault_service.py` — the Phase 72 RED phase discovered the broken `Artifact` import early, before any implementation was written; auto-fix at RED phase is the right time to catch this

### What Was Inefficient
- Phase 74 could have been merged into Phase 73 — the `useLicence.ts` misalignment was predictable given the backend `/api/licence` shape was being defined in Phase 73; a "wire frontend while backend lands" wave would have caught it sooner
- Phase 76 (tech debt closure) is recurring pattern across milestones — should be a standing wave-4 sub-plan in any milestone with a prior audit, not a separate phase
- `vault_service.py` dead code (broken `Artifact` import) had been present since Phase 72 RED scaffolding — should have been deleted in Phase 72, not deferred to Phase 75

### Patterns Established
- `check_and_record_boot(licence_status)` — parameter-driven enforcement instead of env bypass var; CE warns, EE enforces; clean separation without AXIOM_STRICT_CLOCK leak
- `validate_path_within(base, candidate)` in `security.py` — canonical cross-route path safety helper; tested directly in unit tests when route-level testing is blocked by broken imports
- EdDSA JWT for offline licence keys — PyJWT OKP key type; `verify_exp=False` with manual grace arithmetic; hardcoded public key constant (operators cannot rotate without code change)
- `secrets-data` named Docker volume pattern for non-secret operational files that must survive container restarts (boot.log, licence.key)

### Key Lessons
- Security milestones benefit from Wave 0 being purely test scaffolds (RED) — it documents all security properties before any fix is written, and the RED phase is where broken deps surface without blocking anything
- Frontend alignment phases (Phase 74) should be in-milestone sub-tasks, not their own phases — the backend API contract should drive the frontend interface at plan-write time
- Audit findings → tech debt phases: the 3 audit items in Phase 76 were small (< 1 hour each) — bundle them into the milestone's final wave rather than a standalone phase

### Cost Observations
- 5 phases, 8 plans, ~50 min total execution time
- 2-day delivery (2026-03-26 → 2026-03-27)
- TDD discipline: all 6 security tests RED first, then GREEN; all 7 licence tests RED first, then GREEN — consistent across both phases

## Milestone: v14.4 — Go-to-Market Polish

**Shipped:** 2026-03-28
**Phases:** 5 (77–81) | **Plans:** 7

### What Was Built
- Role-gated licence banner: amber GRACE (sessionStorage dismiss) + red DEGRADED_CE (non-dismissible), hidden from operator/viewer roles (Phase 77)
- `axiom-push init` + `key generate` — zero-ceremony Ed25519 keypair and registration flow; credentials migrated from `~/.mop/` to `~/.axiom/` with backward-compat; `AXIOM_URL` fixes silent MOP_URL mismatch (Phase 78)
- `first-job.md` restructured: `axiom-push init` as primary path, openssl ceremony demoted to Manual Setup collapsible (Phase 78)
- `compose.cold-start.yaml` trimmed to 5 core services; all JOIN_TOKEN and bundled-node refs purged from `install.md` (Phase 79)
- GitHub Pages: MkDocs at `/docs/` via ghp-import subtree; marketing homepage at root via scoped homepage-deploy job; both in single `gh-pages-deploy.yml` (Phase 80)
- Marketing homepage: security posture grid (4 cards), SAML/OIDC early-access EE card, enterprise CTAs with form placeholder sentinel (Phase 81)

### What Worked
- Audit-before-complete workflow: the `tech_debt` status (not `gaps_found`) confirmed all 13 requirements satisfied, giving clean signal to proceed — no last-minute remediation phases needed
- Fixing tech debt found in audit (3 items: CLI prog name, error message, migration fallback) before tagging is the right habit — 5-minute fix, not a full gap-closure phase
- Phase 81 (homepage enterprise messaging) added mid-milestone as Phase 80 dependency with clean scope definition — insert-phase workflow handled it without disrupting prior phases
- `GOOGLE_FORM_URL_PLACEHOLDER` sentinel pattern: broken enterprise links are grep-able and visible before launch rather than silently pointing nowhere

### What Was Inefficient
- Phase 80 `site_url` change (`/axiom/` → `/axiom/docs/`) required auditing hardcoded absolute links — should have been a prerequisite check before the plan rather than discovered during execution
- `ghp-import --dest-dir` vs `mkdocs gh-deploy --force` confusion required extra research; the constraint (no `--dest-dir` in `mkdocs gh-deploy`) should have been confirmed in the discuss-phase step

### Patterns Established
- `ghp-import --dest-dir docs` is the correct pattern for MkDocs coexisting with other content on GitHub Pages — document in future docs deploy phases
- Enterprise CTA placeholder sentinel (`GOOGLE_FORM_URL_PLACEHOLDER`) — use for any unconfirmed external URL; easier to audit than empty `href="#"`
- Tech debt found in audit that takes < 15 min to fix: fix before tagging, no phase needed; tech debt taking longer: create gap-closure phase

### Key Lessons
- Go-to-market milestones (homepage, UX polish, docs) are less predictable than feature milestones — scope expands naturally as Phase 80 homepage led directly to Phase 81 messaging improvements
- `from_store()` migration edge case (missing `base_url` in old credential files) is the kind of thing that never appears in tests but breaks real users — worth catching in audit tech debt review

### Cost Observations
- 5 phases, 7 plans, 2-day delivery (2026-03-27 → 2026-03-28)
- Tech debt cleanup post-audit: 3 items, all 1-liners, committed in single pass — clean close
- Phase 81 added as a scope extension after Phase 80 revealed the homepage needed enterprise messaging — planned and executed same session

## Milestone: v15.0 — Operator Readiness

**Shipped:** 2026-03-29
**Phases:** 5 (82–86) | **Plans:** 11

### What Was Built
- Licence tooling: `issue_licence.py` CLI moves signing to private repo; `list_licences.py` audit summary; `--no-remote` air-gap mode; gitleaks CI guard blocks PEM commits to public repo
- Node validation job corpus: Bash/Python/PowerShell reference jobs; volume/network/memory/CPU constraint validation scripts; `sign_corpus.py`; `manifest.yaml`; community catalog README + MkDocs runbook
- Package repo docs: devpi PyPI mirror runbook (Caddy-proxied URL clarification critical), apt-cacher-ng APT mirror, BaGet PWSH mirror; `verify_pypi_mirror.py` validation job in corpus
- Screenshot capture: `capture_screenshots.py` with `seed_demo_data.py` (ephemeral Ed25519 keypair); 11 named PNGs; integrated into docs getting-started, feature guides, and marketing homepage
- Docs accuracy validation: `generate_openapi.py` snapshot tool; `validate_docs.py` (250 PASS / 0 WARN / 0 FAIL against 116 routes); `docs-validate` CI job exits non-zero on FAIL

### What Worked
- Tooling-layer milestone pattern: all 5 phases added `tools/` scripts or `docs/` content — no DB schema changes, no migrations, clean execution
- Wave 0 TDD for job corpus: test scaffold committed before scripts exist; test failures provide helpful messages; RED→GREEN pattern kept quality high without slowing delivery
- Pre-execution verification step for devpi (Phase 84): confirming Caddy-proxied URL and index paths before writing runbook prose prevented a common documentation error
- Static OpenAPI snapshot approach: `validate_docs.py` runs in CI without a live stack; consistent with CLAUDE.md "never use local dev servers" rule

### What Was Inefficient
- Two REQUIREMENTS.md checkboxes left unchecked (SCR-01, DOC-03) despite both features being shipped — indicates final milestone requirements sweep should be a distinct closing step
- Phase 85 plan count mismatch in Phase Details (showed "1 plan" when 2 were executed) — plan count in Phase Details section should be updated at plan creation time, not retroactively

### Patterns Established
- `resolve_key()` explicit `--key` / env var pattern (no silent default path) — apply to any tool that touches secrets
- CLI regex restriction to lowercase tokens in docs validators prevents prose false positives — reusable for future doc-lint tooling
- Screenshot `.gitkeep` structure-first pattern: directories committed before PNGs exist; screenshots added by operator on release prep run
- Resource limit validation jobs gate on capability flag: scripts exit 1 with descriptive message when capability absent — safer than assuming enforcement

### Key Lessons
- Checkbox hygiene matters at milestone close: both unchecked requirements were fully shipped — a final `grep '- \[ \]' REQUIREMENTS.md` check before archiving would catch these
- Operator tooling milestones (v15.0) are shorter and more predictable than feature milestones: no API surface changes, no frontend risk, scope is additive
- devpi URL structure is a common operator trip point: `root/pypi/+simple/` not `root/+simple/` — worth a dedicated callout in any package mirror runbook

### Cost Observations
- 5 phases, 11 plans, 1-day delivery (2026-03-28 → 2026-03-29)
- 86 commits, 175 files changed, 27,147 insertions — primarily tooling scripts and documentation
- No backend/frontend code changes — tooling-only milestone achieved clean execution budget

## Milestone: v18.0 — First-User Experience & E2E Validation

**Shipped:** 2026-04-01
**Phases:** 6 (101–106) | **Plans:** 15 | **Requirements:** 15/15

### What Was Built
- Phase 101: CE UX cleanup — 6 EE-only Admin tabs gated behind `isEnterprise`; `+ Enterprise` upgrade panel with UpgradePlaceholder cards; no blank pages in CE mode
- Phase 102: Linux E2E validation — fresh LXC cold-start through first completed job; 4 BLOCKERs found and fixed; reusable `synthesise_friction.py` with `--files` flag
- Phase 103: Windows E2E validation — Dwight SSH cold-start with PowerShell-only docs; 8 BLOCKERs across 8 iterative runs; complete PowerShell tabs in all getting-started docs
- Phase 104: PR merge — PRs #17 (WebSocket fix), #18 (Windows E2E), #19 (Linux E2E) squash-merged; History.test.tsx fixed; full vitest suite 64/64 pass
- Phase 105: CRLF countersign fix — server-side normalization before user-sig verification and countersigning; admin bootstrap forced password change; PowerShell tabs in first-job.md
- Phase 106: Docs signing pipeline fix — `signature_key_id`→`signature_id` field name; TrustAll→`-SkipCertificateCheck`; client-side CRLF normalization in signing snippet

### What Worked
- Milestone audit caught real integration gaps that phase verification missed: `signature_key_id` vs `signature_id` field name mismatch was invisible to LXC validation (which used internal scripts with the correct field name)
- Iterative FRICTION run approach (8 runs on Windows) was effective at shaking out cumulative issues — each run built on the previous fixes
- Gap-closure phases (105, 106) were correctly scoped to one audit gap each — fast execution (1-2 min per plan), no scope creep
- The three-source requirements cross-reference (VERIFICATION + SUMMARY frontmatter + REQUIREMENTS.md traceability) caught documentation gaps that single-source checks missed

### What Was Inefficient
- Commit `6970440` (CRLF signing normalization) was lost during PR #18 rebase — three separate phases (103, 105, 106) each partially addressed the same underlying issue before it was fully resolved
- The integration checker on the final audit found a gap (client-side CRLF in signing snippet) that should have been caught during Phase 105's verification — the "server handles CRLF transparently" framing was correct for countersign→node but wrong for user-sig→server-verify
- Phase 103 ran 8 iterative friction runs against a remote Windows host — the feedback loop was slow (SSH + Docker restart cycles); a local Windows dev environment would have been faster
- LNX-06 and WIN-06 never made it into SUMMARY frontmatter despite being verified — the verification step catches this but it shouldn't be needed

### Patterns Established
- CRLF normalization must be applied at all three layers: (1) client signing script normalizes before signing, (2) server normalizes before user-sig verification and countersigning, (3) node normalizes before countersig verification
- `must_change_password=True` forced at admin bootstrap with `ADMIN_SKIP_FORCE_CHANGE` opt-out — explicit flag is safer than inferring from password value
- Milestone audit after gap-closure phases: re-run the audit to verify the gaps are actually closed — don't assume the fix addresses all dimensions of the original gap
- First-user validation personas must test the exact doc snippets, not equivalent internal scripts — the LXC validation masked the `signature_key_id` bug because it bypassed the docs

### Key Lessons
- Lost commits during PR rebase are a recurring risk: the same fix (CRLF normalization) was implemented, lost, and reimplemented across three phases — a pre-merge `git diff` against the audit gap list would have caught this
- Integration checker agents are worth their cost: the final audit's integration check found the client-side CRLF gap that three prior phases and two human reviews missed
- "Server handles it transparently" is only true if you control both endpoints — when the user is one endpoint (signing script in docs), the server can't retroactively fix what was signed with wrong bytes

### Cost Observations
- 6 phases, 15 plans, 2-day delivery (2026-03-31 → 2026-04-01)
- 82 commits, 65 files changed, 7,888 insertions
- 3 gap-closure phases (104, 105, 106) were needed after the initial 3 validation phases — 50% of phases were remediation
- Integration checker agent (sonnet) found the final gap that manual review missed

## Milestone: v19.0 — Foundry Improvements

**Shipped:** 2026-04-05
**Phases:** 12 (107–114, 116–119) | **Plans:** 37 | **Requirements:** 21/21

### What Was Built
- Phase 107: Schema foundation + full CRUD — blueprint edit with optimistic locking, tool recipe edit, Approved OS management, dep confirmation dialog, ecosystem enum + 3 new tables
- Phase 108: Transitive dependency resolution — pip-compile resolver, dual-platform mirroring (manylinux + musllinux), auto-mirror on approval, circular dep detection, devpi removal
- Phase 109: APT + apk mirror backends — container-isolated downloads, compose CE/EE split (compose.ee.yaml overlay), Caddy multi-path routing, MirrorHealthBanner
- Phase 110: CVE transitive scan + tree UI — BFS walk for full dependency graph CVE scanning, interactive DependencyTreeModal, discover endpoint with "Approve All"
- Phase 111: npm + NuGet + OCI mirrors — Verdaccio, BaGetter, registry:2 pull-through proxies, all behind `--profile mirrors`
- Phase 112: Conda mirror + admin UI — Conda backend with Anaconda defaults ToS blocking modal, 8-ecosystem MirrorConfigCard grid, one-click Docker provisioning
- Phase 113: Script analyzer — 250+ import-to-package mappings (Python AST, Bash regex, PowerShell Import-Module), cross-reference against approved ingredients
- Phase 114: Curated bundles + starter templates — 5 pre-built bundles, Template Gallery, 3-click build flow, auto-approval pipeline
- Phase 116: DB migration fix + EE licence hot-reload — idempotent migration_v46.sql, background expiry timer, WebSocket broadcast
- Phase 117: Light/dark mode toggle — CSS variable theming, warm stone palette, FOWT prevention, localStorage persistence, all 9 views theme-aware
- Phase 118: UI polish + verification — skeleton loaders, responsive design, GH #20/#21/#22 fixes, permanent Playwright test framework
- Phase 119: Traceability closure — all 21 requirement checkboxes verified, VERIFICATION.md for all 12 phases

### What Worked
- Clean first-pass execution for the core feature phases (107–114) — no gap-closure phases needed for the primary Foundry pipeline
- Compose profile pattern (`--profile mirrors`) established in Phase 109 and inherited cleanly by all subsequent mirror phases (111, 112) — zero rework
- Container-isolated package downloads (debian:12-slim, alpine:3.20 throwaway containers) kept the host system clean and made downloads reproducible
- TDD RED→GREEN for Phase 117 light/dark mode — Wave 0 test infrastructure defined expected behavior upfront, all implementation verified against pre-existing tests
- Milestone audit (passed on first run) validated all 21 requirements with 3-source cross-reference — no surprises at completion time

### What Was Inefficient
- Phase 115 (Operator UX Polish) was planned, discussed, and context-gathered before being deferred to v20.0 — the decision to defer should have been made at roadmap creation (it was always quality-of-life, not blocking air-gap)
- 11/12 phases have Nyquist validation gaps (PARTIAL compliance) — test coverage wasn't consistently generated during execution
- SUMMARY frontmatter `requirements_completed` field was missing from 12 requirements across 7 phases — had to create Phase 119 specifically for traceability closure
- Phase 117 Wave 3 (component styling migration) took 135 min — refactoring 14 files for theme-awareness was underestimated in plan scope

### Patterns Established
- Mirror backend pattern: throwaway container download → host filesystem storage → Caddy/nginx serving → compose sidecar with `--profile mirrors`
- CSS variable theming pattern: `:root` light defaults + `.dark` overrides, FOWT prevention inline script in index.html, `useTheme` Context API hook
- Compose CE/EE separation: `compose.server.yaml` (CE-only) + `compose.ee.yaml` (overlay with EE services) activated via `docker compose -f ... -f ...`
- Ecosystem dispatch pattern: `_mirror_{ecosystem}()` methods in mirror_service.py, routed by ingredient.ecosystem enum value

### Key Lessons
- Traceability closure should be continuous, not a final phase — SUMMARY frontmatter and REQUIREMENTS.md checkboxes should be updated in the same plan that implements the feature
- Nyquist validation (test generation for requirements) is valuable but was skipped under time pressure — making it a mandatory gate rather than optional toggle would prevent the accumulation of test debt
- The 5-day timeline for 12 phases / 37 plans demonstrates that a well-structured dependency chain (each mirror phase inherits the previous pattern) scales efficiently — the longest phase was 135 min, most were under 60 min

### Cost Observations
- 12 phases, 37 plans, 5-day delivery (2026-04-01 → 2026-04-05)
- 278 commits, 275 files changed, 58,605 insertions
- Average plan duration: 22 min (from STATE.md velocity metrics)
- Only 1 gap-closure phase (119, traceability) needed — 92% of phases were primary implementation
- Quality model profile used throughout — no budget or balanced compromises

## Cross-Milestone Trends

| Milestone | Phases | Plans | Key pattern |
|-----------|--------|-------|-------------|
| v7.0 | 5 | 34 | Infrastructure-heavy; gap-closure plans expected for complex service interactions |
| v8.0 | 3 | 14 | CLI + backend + UI in one milestone; Playwright as final gate |
| v9.0 | 9 | 27 | Documentation milestone; stub-first nav pattern; regression gap closure required |
| v10.0 | 5 | 21 | Security + observability + release; audit-before-close gate caught cross-phase propagation gap |
| v11.0 | 4 | 15 | Open-core split; Cython build pipeline as key technical risk; EE plugin via entry_points |
| v11.1 | 8 | 27 | Adversarial validation milestone; scripted evidence per requirement; gap-closure plans serial on live infra |
| v12.0 | 11 | 38 | Operator UX milestone; audit surfaced 4 critical integration gaps; gap-closure phases (54, 56) with E2E test file |
| v13.0 | 4 | 8 | Research + docs reset milestone; all phases parallel; no code changes; two design docs ground next build cycle |
| v14.0 | 5 | 14 | Adversarial validation milestone; Gemini-as-first-user; doc accuracy failures dominate; gap-fix sub-plan needed for doc-test phases |
| v14.1 | 5 | 9 | Remediation milestone; audit-before-complete mandatory; tab-pair pattern established; d['token'] regression shows freshly-rewritten docs need contract verification |
| v14.2 | 1 | 2 | Infra milestone; single-day; human-verify checkpoint for live Pages confirmation was the only gate; OFFLINE_BUILD conditional pattern reusable for future dual-deploy configs |
| v14.3 | 5 | 8 | Security + EE licensing; TDD RED→GREEN; audit-before-complete caught 3 tech debt items; frontend alignment phase predictable from backend API shape |
| v14.4 | 5 | 7 | Go-to-market milestone; tech debt found post-audit cleaned before close; ghp-import subtree pattern solves docs/homepage coexistence on GitHub Pages |
| v15.0 | 5 | 11 | Operator readiness milestone; tooling-only (no DB/API changes); Wave 0 TDD for job corpus; static OpenAPI snapshot for CI-safe docs validation |
| v16.0 | 5 | 9 | Competitive observability milestone; 5 new features across backend + frontend; audit-before-close caught stale requirements traceability |
| v16.1 | 4 | 7 | PR backlog closure + docs quality; parallel PR merge + retroactive Nyquist compliance; 1-day turnaround |
| v17.0 | 5 | 6 | Scale hardening; clean first-pass execution across all phases; no gap-closure plans needed |
| v18.0 | 6 | 15 | E2E validation milestone; 50% phases were gap-closure; integration checker found final gap; lost-commit risk pattern |
| v19.0 | 12 | 37 | Foundry production-grade; clean first-pass (1 traceability phase only); compose profile inheritance; 22min avg plan; 5-day delivery |
| v20.0 | 9 | 22 | Node capacity + isolation; cgroup detection; stress corpus; ephemeral-only enforcement; clean first-pass; real hardware validation |
| v21.0 | 3 | 9 | API contract milestone; response_model on all 89 routes; TDD RED→GREEN for Phase 131; audit passed first run; 2-day delivery |

## Milestone: v16.1 — PR Merge & Backlog Closure

**Shipped:** 2026-03-30
**Phases:** 4 (92–95) | **Plans:** 7

### What Was Built
- PR #10 merged: Signatures page keypair generation guide (KeygenGuideModal, KEYGEN_CMD/SIGN_CMD/REGISTER_CMD copy-paste steps); no auto-seeded demo keypair
- PRs #11, #12, #13 merged: production deployment guide, upgrade runbook with 36-migration index, Windows Docker Desktop + WSL2 getting-started path
- PR #14 merged: APScheduler scale limits research with concrete thresholds; competitor pain-point product notes with 3+ actionable observations
- Phase 95 housekeeping: SIGN_CMD placeholder corrected, DOC-01/03 strikethroughs applied, 94-01/02 plan frontmatter phantom IDs fixed
- Retroactive VALIDATION.md files created for phases 92–94 closing Nyquist compliance gap

### What Worked
- Parallel execution of plans 95-01 and 95-02 (independent targets: code files vs planning files) — no conflict, both completed in parallel with no coordination overhead
- `plan-and-execute` single command for the final phase — clean isolation of planning context from execution context
- PRs #11–13 required cherry-pick tactics to avoid re-merging already-present `.planning/` changes — docs-only cherry-pick is a reusable pattern for documentation PRs on branches with mixed commits

### What Was Inefficient
- REQUIREMENTS.md traceability table was never updated for v16.0 phases 88–91 (all marked "Pending" even after phases completed) — traceability should be updated at phase completion, not just at milestone close
- v16.0 was never formally archived via `complete-milestone` before v16.1 began — REQUIREMENTS.md ended up covering two milestones; archived together at v16.1 close

### Patterns Established
- Cherry-pick docs-only commit from a mixed branch (docs + `.planning/`) to avoid re-merging already-present infra/planning changes
- Retroactive VALIDATION.md creation is the recovery path for phases that predate Nyquist validation requirement
- `tech_debt` audit status (vs `passed` or `gaps_found`) is a safe-to-proceed signal for milestone close

### Key Lessons
- Requirements traceability: update the traceability table at phase completion as a required post-execution step, not deferred to milestone close
- Milestone boundary hygiene: formally `complete-milestone` before starting a follow-on minor version, even if the next milestone is small
- Docs PRs with planning file side-effects: cherry-pick the docs commit, close the original PR with a merge-note comment

### Cost Observations
- 4 phases, 7 plans, 1-day delivery (2026-03-30)
- ~46 commits, ~65 files changed
- No new backend/frontend features — PR merge + docs + housekeeping; minimal code-review overhead

## Milestone: v17.0 — Scale Hardening

**Shipped:** 2026-03-31
**Phases:** 5 (96–100) | **Plans:** 6 | **Requirements:** 19/19

### What Was Built
- APScheduler pinned to `>=3.10,<4.0` with startup assertion; `IS_POSTGRES` flag exported from `db.py`; global `job_defaults` (`misfire_grace_time=60`, `coalesce=True`, `max_instances=1`) set at constructor level
- asyncpg pool right-sized for 20 concurrent nodes (`pool_size=20`, `max_overflow=10`, `pool_timeout=30`, `pool_recycle=300`, `pool_pre_ping=True`); tunable via `ASYNCPG_POOL_SIZE` env var
- Two-phase `SELECT FOR UPDATE SKIP LOCKED` in `pull_work()` on Postgres: 50-row unlocked scan + FOR UPDATE on chosen row; composite index `ix_jobs_status_created_at`; `migration_v44.sql` for existing deployments
- Diff-based `sync_scheduler()`: internal `__`-prefixed jobs protected from CRUD sync; only affected APScheduler job modified per operation; `asyncio.create_task()` cron callback via `_make_cron_callback()`
- `GET /health/scale` endpoint returning pool stats, APScheduler job count, pending job depth; null-safe on SQLite; Admin Repository Health card shows live metrics; `upgrade.md` gains `migration_v44` entry with `CONCURRENTLY` caveat

### What Worked
- Agent-driven planning + execution: each phase had a clear, bounded goal — phases 96–100 executed cleanly with no gap-closure plans needed
- Parallel phase independence: Phase 99 (Scheduler Hardening) could be planned immediately after Phase 96 without waiting for 97/98 — the dependency graph was correctly identified upfront
- The two-phase SKIP LOCKED design (unlocked scan + locked pick) was identified in the design phase and implemented correctly first time — no contention regression

### What Was Inefficient
- REQUIREMENTS.md traceability was not updated incrementally after each phase — requirements stayed in "Active" state throughout the milestone and were only moved to "Validated" at milestone close
- The `CONCURRENTLY` transaction-block caveat for `migration_v44.sql` was not identified until the observability/docs phase (Phase 100) — it should be caught at the migration authoring step

### Patterns Established
- `IS_POSTGRES` as a module-level boolean (not a function check) is the correct pattern for dialect-conditional code — no asyncpg import side-effects at test time
- `_pool_kwargs` at module level (not function-scoped) enables clean test imports; `max_overflow` hardcoded keeps operator tuning surface minimal
- `CREATE INDEX CONCURRENTLY` migrations must carry an explicit comment warning that psql `-1` (single-transaction mode) cannot be used — this is a recurring operational gotcha

### Key Lessons
- Always test Postgres-path features through the actual Caddy proxy layer, not just FastAPI's `TestClient` — proxy routing can mask correctness issues that only surface at integration time
- APScheduler v4 is a complete rewrite with no migration path — version pinning is a hard prerequisite before any scheduler code changes; document the rationale in the pin itself
- The `CONCURRENTLY` caveat for index creation should be part of the migration authoring checklist, not discovered during docs review

### Cost Observations
- 5 phases, 6 plans, 3-day delivery (2026-03-29 → 2026-03-31)
- 52 files changed, 6,255 insertions, 89 deletions
- Sonnet model throughout; no gap-closure plans required — clean first-pass execution across all phases

## Milestone: v16.0 — Competitive Observability

**Shipped:** 2026-03-30
**Phases:** 5 (87–91) | **Plans:** 9

### What Was Built
- Phase 87: Competitor pain points reviewed; design decisions documented for all 4 features
- Phase 88: Dispatch Diagnosis UI — bulk `/api/jobs/diagnose` endpoint, inline PENDING badge with reason text, 10s auto-poll in job list
- Phase 89: CE Alerting — NotificationsCard in Admin settings (webhook URL), failure-triggered POST notification, CE-accessible without EE licence
- Phase 90: Job Script Versioning — immutable `JobDefinitionVersion` table, `ScriptViewerModal` for any historical execution, version number column in execution history list
- Phase 91: Output Validation — `validation_rules` + `failure_reason` columns, exit-code/JSON-field/stdout-regex pattern types, exit-0 jobs fail to FAILED with "Validation failed:" label

### What Worked
- Research-first phase (87) eliminated design ambiguity — no backtracking mid-implementation
- All 4 features CE-accessible (no EE gate) — clean implementation boundary from design phase
- 5 features across 5 phases with clear sequential dependency chain — each phase built on stable prior output

### What Was Inefficient
- Requirements traceability not updated at phase completion — 12 "Pending" items at milestone close for already-completed phases
- v16.0 milestone not formally closed before v16.1 began — both milestones shared one REQUIREMENTS.md

### Patterns Established
- Research phase as Wave 0 for a features milestone: outputs locked design decisions, eliminates costly backtracking
- Parallel feature phases (88/89/90/91 all depend only on 87, not each other) — could be parallelized in future

### Key Lessons
- Mark requirements Complete in traceability table immediately after verification passes for a phase
- CE/EE boundary decision belongs in the design phase, not implementation — avoids retrofit gating

### Cost Observations
- 5 phases, 9 plans, ~1 day
- All 17 requirements satisfied
- Research phase (87) was 1 plan but unblocked 4 parallel implementation phases

## Milestone: v14.2 — Docs on GitHub Pages

**Shipped:** 2026-03-26
**Phases:** 1 (Phase 71) | **Plans:** 2

### What Was Built
- Untracked 166 docs/site/ build output files; `docs/site/` gitignored
- `.nojekyll` marker added to docs source root — prevents Jekyll interference with MkDocs underscore-prefixed assets
- `mkdocs.yml` site_url set for GitHub Pages; offline plugin made conditional on `OFFLINE_BUILD` env var
- `docs/Dockerfile` updated: `OFFLINE_BUILD=true` preserves air-gap container behaviour
- `docs-deploy.yml` GitHub Actions workflow — path-filtered auto-deploy on every `docs/**` push to main
- `docs/scripts/regen_openapi.sh` — local operator tool for refreshing pre-committed `openapi.json`

### What Worked
- Two-plan wave structure was correct: housekeeping first (71-01) unblocked the deploy workflow (71-02) — no rework
- Human-verify checkpoint at the end of 71-02 was the right gate; the MoP-as-first-user approach (automated checks + human final confirmation) worked well for live infrastructure
- `!ENV [OFFLINE_BUILD, false]` pattern cleanly served two deployment targets with one `mkdocs.yml` — worth reusing for any future dual-path doc builds

### What Was Inefficient
- No audit file existed for v14.2 — the milestone was small enough that audit wasn't blocking, but the missing preflight check had to be skipped manually

### Patterns Established
- `OFFLINE_BUILD` conditional for docs: disabled by default (GH Pages), `true` in Dockerfile (air-gap container) — single config, no forking
- `.nojekyll` in MkDocs source root (not site root) — copied into built site by mkdocs, lands at GH Pages root automatically
- `fetch-depth: 0` required in any workflow using MkDocs Material's `git_revision_date_localized` plugin

### Key Lessons
- For infra milestones touching live external services (Pages, GHCR, PyPI), the human-verify checkpoint at the final plan is the correct pattern — automate everything up to the live confirmation
- `docs/site/` should have been gitignored when the docs container was first set up (v9.0) — build output tracking in git is a recurring problem across projects; add it to the "new docs project" checklist

### Cost Observations
- 1 phase, 2 plans, 16 commits — smallest milestone to date
- Single-day delivery (2026-03-26)
- Checkpoint added ~20 min for live Pages activation (GitHub UI step required)

## Milestone: v20.0 — Node Capacity & Isolation Validation

**Shipped:** 2026-04-10
**Phases:** 9 (120–128) | **Plans:** 22 | **Requirements:** all

### What Was Built
- Phase 120–122: Job memory/CPU limit schema, API admission control, `parse_bytes()` helper, node-side limit validation — full limit lifecycle from DB through API through node enforcement
- Phase 123: `CgroupDetector` class — v1 vs v2 detection at node startup and heartbeat, orchestrator schema updates to surface cgroup mode per node
- Phase 124: Ephemeral execution guarantee — block `EXECUTION_MODE=direct`, startup enforcement check, node reporting, compose validation
- Phase 125: Stress test corpus — CPU burn, memory hog, noisy-neighbour scripts across Python/Bash/PowerShell; preflight check + orchestrator script
- Phase 126: Limit enforcement validation — Docker/Podman node enrollment, live network fixes, signature verification fix, stress test execution, final validation report
- Phase 127: Cgroup dashboard — node cgroup badges, degradation banner, Admin System Health tab with cgroup compatibility card
- Phase 128: Concurrent isolation — `noisy_monitor.py` sleep-drift monitor, 5-run orchestrator with `target_node_id`, isolation reports

### What Worked
- Real hardware validation approach (live Docker/Podman nodes) rather than mocked enforcement — discovered actual issues (signature verification, network routing) that would have been invisible in unit tests
- Stress corpus scripts across all 3 runtimes (Python/Bash/PowerShell) validated the ephemeral execution model under load
- Cgroup detection as a first-class feature (not just a diagnostic) — surfaced as dashboard UI, giving operators actionable visibility

### What Was Inefficient
- Phase 126 required 5 plans due to iterative discovery: Docker enrollment, network fixes, Podman validation, live node deployment, final execution — the complexity of live-infrastructure validation phases is consistently underestimated
- Two phase 121 plans covered overlapping concerns (dispatcher diagnosis extension + scheduler integration) — could have been one combined plan

### Patterns Established
- `CgroupDetector` startup detection pattern: run once at init, persist result in heartbeat payload — operator doesn't need to configure anything
- Stress corpus directory structure: `mop_validation/stress_tests/{python,bash,powershell}/` with `preflight_check.py` + `orchestrate_*.py` at root — reusable for future validation milestones
- Validation report format: JSON results file + markdown summary per stress test run — consistent with MATRIX EVIDENCE pattern from v11.1

### Key Lessons
- Live-infra phases should budget for 4-5 plans (not 2-3) — network, auth, and signature issues are only discoverable at execution time
- Ephemeral-only enforcement (`EXECUTION_MODE=direct` blocked) is a hard prerequisite for any isolation claim — defer the isolation milestone until enforcement is confirmed
- Cgroup v1 vs v2 detection belongs in the node, not operator docs — automatic detection removes the most common node misconfiguration

### Cost Observations
- 9 phases, 22 plans, 5-day delivery (2026-04-06 → 2026-04-10)
- 89 files changed, 11,264 insertions
- Phase 126 (live validation) was 5 plans alone — live infra phases are disproportionately plan-heavy

## Milestone: v21.0 — API Maturity & Contract Standardization

**Shipped:** 2026-04-11
**Phases:** 3 (129–131) | **Plans:** 9

### What Was Built
- Phase 129: `ActionResponse`, `PaginatedResponse[T]` (Pydantic v2 Generic), `ErrorResponse` added as core models; `response_model=` applied to all 89 API routes (143% of original 62-route target); zero untyped routes remain; full test coverage per response shape
- Phase 130: Pytest integration test suite — 4 service-layer test cases (happy path, bad signature, capability mismatch, retry); live E2E orchestration script with 4 scenarios and JSON reporting; 4/4 pass
- Phase 131: `SignatureService.countersign_for_node()` unified static method; HMAC stamping for scheduled jobs at dispatch time (SEC-02 compliance); hard-fail semantics (HTTP 500) when signing key absent; TDD RED→GREEN with 112 new tests across 7 test files

### What Worked
- TDD methodology for Phase 131 produced a correct implementation on first green pass — RED phase caught 3 separate gaps (missing HMAC for scheduled jobs, missing hard-fail, non-unified code paths) before implementation began
- `PaginatedResponse[T]` as a Pydantic v2 Generic resolved the type safety problem for list endpoints without requiring per-type response models — pattern is reusable for any future paginated endpoint
- Audit-before-close passed on first run with 0 gaps and 7 non-critical tech debt items — highest first-run audit score to date
- Wave-based plan execution (Phase 129 in 5 waves, 130 in 2 waves) kept each plan bounded and verifiable

### What Was Inefficient
- Phase 129 target was 62 routes; 89 were actually found — the route count in the plan was based on an outdated estimate. Actual scope was 44% larger than planned, though execution still completed cleanly
- Phase 131 was originally dated "completed 2026-04-11" in ROADMAP.md but Phase 130 was completed 2026-04-12 — the phase ordering in the milestone didn't match completion order (131 completed before 130)

### Patterns Established
- `countersign_for_node(job_guid, script, signature_id)` static method as the single signing entry point — all callers (manual dispatch, scheduled dispatch, staged jobs) route through one method
- HMAC stamping at dispatch time for scheduled jobs — ensures the same SEC-02 compliance path as manually-dispatched jobs
- Hard-fail (`raise HTTPException(500)`) on missing signing key — explicit failure mode rather than silent no-signature dispatch
- `PaginatedResponse[T]` Generic pattern for typed list endpoints — avoids per-type boilerplate while preserving full OpenAPI type information

### Key Lessons
- Route count estimates in plans should be derived from `grep -c 'async def.*route\|@router\.' main.py` at plan time, not carried forward from design documents — the 62→89 gap caused no execution problem here but could have in a more constrained plan
- TDD's RED phase is worth the investment: Phase 131's RED tests identified 3 security gaps before a single line of implementation code was written — prevents the "passes tests that don't test the right thing" failure mode
- HMAC/signing coverage must be explicitly audited per dispatch path, not assumed to be covered by "signature verification tests" — the SEC-02 gap (scheduled jobs not HMAC-stamped) was invisible to path-specific tests

### Cost Observations
- 3 phases, 9 plans, 2-day delivery (2026-04-11 → 2026-04-12)
- 46 files changed, +10,649 / -352 lines, 39 commits
- Smallest plan count per phase ratio to date (3 plans/phase average) — clean problem decomposition
- 112 new tests added; 110/112 pass (2 intentional EE-only expected failures)
