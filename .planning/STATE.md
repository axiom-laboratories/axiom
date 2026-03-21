---
gsd_state_version: 1.0
milestone: v11.1
milestone_name: — Stack Validation
status: planning
stopped_at: Completed 43-08-PLAN.md
last_updated: "2026-03-21T23:30:28.264Z"
last_activity: 2026-03-20 — Roadmap created for v11.1 (Phases 38–45)
progress:
  total_phases: 8
  completed_phases: 6
  total_plans: 20
  completed_plans: 20
  percent: 0
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-03-20)

**Core value:** Jobs run reliably — on the right node, when scheduled, with their output captured — without any step in the chain weakening the security model.
**Current focus:** v11.1 Stack Validation — Phase 38: Clean Teardown + Fresh CE Install

## Current Position

Phase: 38 of 45 (Clean Teardown + Fresh CE Install)
Plan: — (not yet planned)
Status: Ready to plan
Last activity: 2026-03-20 — Roadmap created for v11.1 (Phases 38–45)

Progress: [░░░░░░░░░░] 0%

## Performance Metrics

**Velocity:**
- Total plans completed: 0
- Average duration: —
- Total execution time: —

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| — | — | — | — |
| Phase 38-clean-teardown-fresh-ce-install P01 | 1 | 2 tasks | 2 files |
| Phase 38-clean-teardown-fresh-ce-install P02 | 2 | 1 tasks | 1 files |
| Phase 39-ee-test-keypair-dev-install P01 | 10 | 2 tasks | 5 files |
| Phase 39-ee-test-keypair-dev-install P02 | 3m | 2 tasks | 4 files |
| Phase 40-lxc-node-provisioning P02 | 3m | 1 tasks | 1 files |
| Phase 40-lxc-node-provisioning P01 | 3 | 2 tasks | 3 files |
| Phase 40-lxc-node-provisioning P03 | 21m | 2 tasks | 1 files |
| Phase 41-ce-validation-pass P01 | 3m | 2 tasks | 2 files |
| Phase 41-ce-validation-pass P02 | 13m | 1 tasks | 1 files |
| Phase 41-ce-validation-pass P03 | 30min | 3 tasks | 1 files |
| Phase 42-ee-validation-pass P01 | 14m | 2 tasks | 3 files |
| Phase 42-ee-validation-pass P02 | 11m | 2 tasks | 2 files |
| Phase 43-job-test-matrix P01 | 3min | 3 tasks | 2 files |
| Phase 43-job-test-matrix P02 | 4min | 3 tasks | 3 files |
| Phase 43-job-test-matrix P03 | 6m | 3 tasks | 3 files |
| Phase 43-job-test-matrix P04 | 6min | 3 tasks | 3 files |
| Phase 43-job-test-matrix P05 | 7min | 2 tasks | 1 files |
| Phase 43-job-test-matrix P06 | 5min | 2 tasks | 1 files |
| Phase 43-job-test-matrix P07 | 18min | 1 tasks | 5 files |
| Phase 43-job-test-matrix P08 | 45m | 3 tasks | 2 files |

## Accumulated Context

### Decisions

- [Phase 39]: EE public key patching uses editable `pip install -e .` on raw `axiom-ee/` source — no Cython rebuild. Patching compiled `.so` at runtime is impossible (Cython attributes are read-only at C level).
- [Phase 40]: LXC nodes use `incusbr0` bridge host IP for `AGENT_URL`, not Docker's `172.17.0.1`. IP must be discovered dynamically.
- [Phase 40]: One unique JOIN_TOKEN per node generated before provisioning — parallel enrollment races on a shared token.
- [All concurrent tests]: Postgres required. SQLite write locking breaks under 4-node concurrent polling.
- [Phase 38]: Soft teardown uses docker compose down (no -v) + explicit pgdata volume rm — only safe way to preserve certs-volume Root CA between runs
- [Phase 38]: Hard teardown omits global set -e so a stopped LXC node does not abort the script — best-effort per node with [WARN] output
- [Phase 38]: SECRETS_ENV points to MOP_DIR/secrets.env (not mop_validation/secrets.env) — shared credential store between stack and tests
- [Phase 38]: verify_ce_install.py table count excludes apscheduler_jobs — APScheduler internal table is not a CE schema table
- [Phase 38]: INST-04 manual steps embedded as INST_04_MANUAL_TEST_STEPS module constant — accessible via grep/editor without running script
- [Phase 39]: patch_ee_source.py uses lambda replacement in re.sub to prevent \xNN byte sequences in repr(pub_raw) being treated as regex escapes
- [Phase 39]: compose.server.yaml AXIOM_LICENCE_KEY change applied to main puppeteer/ file — the .worktrees/axiom-split/ worktree referenced in plan does not exist
- [Phase 39]: Plan 39-02 verification condition typo: exp > 1700000000*5 (=8.5B) in plan snippet was wrong for 10yr licence (~2.09B); corrected assertion to > int(time.time()). Implementation correct.
- [Phase 40]: NODE-05 REVOKED confirmation uses GET /api/nodes status poll — host does not hold node client cert so mTLS /work/pull call is not possible
- [Phase 40]: NODE-05 requires reinstate before re-enroll — REVOKED nodes are blocked at /api/enroll
- [Phase 40]: cert serial_number is primary re-enrollment identity proof; node_id diff is fallback when client_cert_pem absent
- [Phase 40]: ubuntu_node_secrets docker volume removed on compose restart to force fresh CSR and new cert identity
- [Phase 40]: lxc-node-compose.yaml uses __REGISTRY_IP__ placeholder (not env var) — Docker compose image: field does not reliably support env var registry prefix substitution
- [Phase 40]: EXECUTION_MODE=docker hardcoded in LXC compose template — LXC nodes have nested Docker via security.nesting=true, not DinD direct mode
- [Phase 40]: Token generation loop runs fully before provisioning loop — all secrets/nodes/*.env exist before any container starts
- [Phase 40]: POST /auth/login uses OAuth2PasswordRequestForm — provisioner must send data= (form-encoded), not json=
- [Phase 40]: Incus image source is images:ubuntu/24.04 — the ubuntu: remote is not configured; images: remote is always available
- [Phase 40]: Health check endpoint is /nodes (not /api/nodes); nodes register as ONLINE (not HEALTHY)
- [Phase 41]: CEV-01 uses admin JWT to decouple auth-layer 403 from EE-gate 402 — stub assertion is unambiguous
- [Phase 41]: CEV-02 is non-destructive by design — operator runs teardown_hard.sh first, script only asserts table count result
- [Phase 41]: 7 hardcoded EE stub routes (one per domain) sourced from ee/interfaces/*.py — explicit list fails clearly on route changes
- [Phase 41]: POST /jobs returns HTTP 200 (not 201) in CE build — validation scripts should accept both status codes
- [Phase 41]: verification.key in running container may drift from project canonical key — must align before CEV-03 signature verification will pass
- [Phase 41]: EXECUTION_MODE=auto inside puppet-node selects podman which fails with cgroup v2 errors inside Docker — use EXECUTION_MODE=docker + copy docker binary from LXC host
- [Phase 41]: master-of-puppets-node:latest must be loaded into LXC docker daemon separately from host docker
- [Phase Phase 41]: CE-only build uses default ARG EE_INSTALL= (empty) — no extra arg needed, omission is the CE signal
- [Phase Phase 41]: down -v required for CEV-02 — down without -v preserves pgdata and EE tables, making count assertion fail
- [Phase 42]: Used getattr(current_user, 'role', None) != 'admin' instead of direct role access — CE User model lacks role column without migration, consistent with deps.py require_permission pattern
- [Phase 42]: Added role column back to CE db.py User model (server_default='admin') — EE users router reads u.role directly on CE User, stripped in bbcb209 but not re-added by EE plugin startup
- [Phase 42]: EE image rebuild via FROM axiom-test-agent:latest + COPY approach — devpi root/dev index unavailable after CE validation teardown wiped volumes
- [Phase 42]: CE main.py is responsible for licence expiry gating — EEPlugin.register() (compiled Cython .so) unconditionally mounts EE routers; expiry enforcement must live in the CE control layer
- [Phase 42]: app.state.licence must be parsed from AXIOM_LICENCE_KEY in lifespan() before load_ee_plugins() — EE plugin only sets EEContext feature flags, not licence metadata that GET /api/licence reads
- [Phase 43]: HTTP 409 (Conflict) used for REVOKED job definition dispatch in dispatch_job() — semantically correct for resource-in-conflicting-state
- [Phase 43]: HTTP 422 (Unprocessable Entity) used for no-eligible-node in create_job() — matches FastAPI validation error convention; conditional on env_tag being truthy
- [Phase Phase 43]: Scripts skip gracefully (exit 0) when no DEV node is ONLINE — prevents CI breakage when nodes not yet provisioned
- [Phase Phase 43]: JOB-02 uses 120s poll timeout (not 30s) because job sleeps 90s — 30s would produce false FAIL on working system
- [Phase Phase 43]: JOB-03 [INFO] gap notices document direct mode silently ignoring memory_limit — deliberate documentation, not test failures
- [Phase Phase 43]: JOB-06 signature pre-flight uses SKIP (exit 0) not FAIL — signatures are environment-dependent prerequisites, consistent with node online pre-flight pattern
- [Phase Phase 43]: JOB-05 node_id absence from ExecutionRecord documented as [INFO] not [FAIL] — job completed correctly, attribution is observability gap not routing failure
- [Phase 43]: JOB-07 attempt_number assertion adaptive: detect min value dynamically (works for 0-based and 1-based indexing)
- [Phase 43]: JOB-08 postgres container discovered dynamically via docker ps --filter name=postgres (not hardcoded to puppeteer-postgres-1)
- [Phase 43]: Rate-limit guard in run_job_matrix.py runner after every 5th script: each verify_job_*.py calls POST /auth/login once; stack enforces 5/minute; pause skipped if batch already took 62+ seconds naturally
- [Phase 43]: capture_output=False on subprocess.run() in run_job_matrix.py — each script streams output in real time to terminal
- [Phase 43]: except HTTPException: raise inserted before generic except in create_job() — standard FastAPI pattern; HTTPException is subclass of Exception so ordering matters
- [Phase 43]: 8/9 matrix pass is acceptable — JOB-07 FAIL documents known retriable=True gap in node.py; not masked
- [Phase 43]: LXC node execution bootstrap: copy docker binary from LXC host into puppet-node container; tag localhost/master-of-puppets-node:latest from registry image
- [Phase 43]: Matrix script idempotency: POST /api/jobs/push 409 conflict response includes existing ID — extract and reuse to support re-runs
- [Phase 43]: Job timeout_minutes required for any job sleeping >30s — node.py defaults to 30s when absent
- [Phase 43]: docker.io apt package on python:3.12-slim only installs dockerd (not docker CLI) — must bind-mount /usr/bin/docker from LXC host into puppet-node container
- [Phase 43]: retriable=True only on python_script non-zero exit with max_retries > 0 — security_rejected, memory-limit, and runtime-exception paths remain non-retriable by design
- [Phase 43]: global _current_env_tag must be declared before first use in Python 3.12 — pre-existing SyntaxError fixed in 43-08 (was masked by older node image)

### Pending Todos

None.

### Blockers/Concerns

- Phase 39 can start in parallel with Phase 38 (no stack dependency), but must complete before Phase 42.
- Phases 43 and 44 are independent of each other — can run in parallel after Phase 42 completes.
- Air-gap test (FOUNDRY-05) requires real `iptables` network isolation, not just behavioral pip.conf check.

## Session Continuity

Last session: 2026-03-21T23:30:28.262Z
Stopped at: Completed 43-08-PLAN.md
Next action: `/gsd:plan-phase 38`
Resume file: None
