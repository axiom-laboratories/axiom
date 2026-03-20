# Feature Research

**Domain:** Adversarial validation — job orchestration + image build platform (Axiom v11.1)
**Researched:** 2026-03-20
**Confidence:** HIGH (derived from direct codebase inspection, existing test infrastructure review,
and PROJECT.md milestone documentation; no speculative gaps)

---

## Context: What This Milestone Covers

This replaces the v11.0 FEATURES.md. All v11.0 features are complete and shipped. v11.1 is
strictly **adversarial end-to-end stack validation** — not new feature development. The goal is
to stress-test every subsystem from a clean install, find hidden bugs, and capture findings for
v12.0+.

**Five test domains (from milestone scope):**
1. Fresh install (CE and CE+EE install paths from clean state)
2. CE vs CE+EE install path divergence verification
3. Job execution matrix — 4 environment-tagged LXC nodes, varying duration/memory/concurrency/failure modes
4. Foundry + Smelter deep validation — wizard, CVE enforcement, edge cases, air-gap mirror
5. Node lifecycle — enroll, heartbeat, revoke, re-enroll

**What is NOT being tested (already validated in prior milestones):**
- RBAC permission model correctness (Sprint 6)
- OAuth device flow (v8.0, tested in `test_device_flow.py`)
- Dashboard Staging view (v8.0, `test_job_staging.py`)
- Attestation badge (v10.0, `test_attestation.py`)
- MkDocs docs site content (v9.0)

---

## Domain 1: Fresh Install (CE and CE+EE)

### Table Stakes

| Scenario | Why Expected | Complexity | Notes |
|----------|--------------|------------|-------|
| **CE cold-start from `docker compose up` produces a working API** | Any orchestration platform must reach a healthy state from a clean slate without manual intervention | LOW | Verify `/api/health` 200, admin user seeded, DB initialised with all 13 CE tables |
| **CE cold-start seeds the admin user exactly once** | Re-running `docker compose up` on an existing volume must NOT reset the admin password or create duplicate admin users | LOW | Test: `docker compose down`, `docker compose up`, verify existing admin JWT still valid |
| **All 7 EE stub endpoints return 402 on CE-alone install** | Operators hitting an EE endpoint on CE must get a clear "upgrade required" signal, not a 404 (confusing) or 500 (alarming) | LOW | Hit all 7 EE routes: `/api/rbac/*`, `/api/audit-advanced/*`, etc. Assert 402 |
| **Dashboard loads and shows "Community Edition" badge** | First-time operators need visual confirmation of which edition is running | LOW | Sidebar footer `LicenceSection` — assert "CE" text present |
| **CE+EE cold-start mounts all 7 EE routers** | The EE plugin entry_points mechanism must activate and override stubs | LOW | Install `axiom-ee` wheel via devpi, restart, verify `GET /api/features` all `true` |
| **CE+EE cold-start shows "Enterprise Edition" badge** | Licence validation success must be reflected in the dashboard | LOW | Sidebar footer asserts "EE" or "Enterprise" |
| **`AXIOM_LICENCE_KEY` missing on CE+EE install gracefully degrades** | If EE wheel is installed but no licence key provided, system must fall back to CE mode without crashing | LOW | Start CE+EE with env var omitted — assert 402 stubs, no 500, clear log message |
| **`AXIOM_LICENCE_KEY` expired on CE+EE install gracefully degrades** | Expired licence must not bring down the server | LOW | Use a test licence with `exp` in the past — assert CE fallback, log "licence expired at {date}" |
| **Teardown is complete — no orphaned volumes or certs** | Repeated test cycles require clean teardown so each run starts from true zero | MEDIUM | `docker compose down -v` + verify no `secrets/` artefacts left; automate teardown sequence |

### Differentiators

| Scenario | Value Proposition | Complexity | Notes |
|----------|-------------------|------------|-------|
| **Install both editions with a locally-signed test licence** | Validates the full licence issuance and validation path with a real Ed25519 keypair — not a hardcoded fixture | MEDIUM | Generate test keypair; sign test licence payload (`customer_id`, `exp` 30 days out, all features); embed public key in compiled EE binary (dev build); verify round-trip |
| **CE+EE upgrade path — CE running, EE wheel added** | Simulates the real customer experience of upgrading CE to EE without taking the server offline to rebuild from scratch | HIGH | `pip install axiom-ee` inside running container → `docker compose restart agent` → verify EE features active without DB migration |
| **Concurrent cold-starts don't corrupt DB init** | `create_all` at startup is not transactionally safe under race conditions if two processes start simultaneously | HIGH | Start two agent replicas simultaneously against shared Postgres — verify no duplicate table creation errors or constraint violations |

### Anti-Features to Test For

| Anti-Scenario | Why to Check | What System Should NOT Do |
|---------------|--------------|--------------------------|
| **Admin password reset on re-start** | `ADMIN_PASSWORD` env var re-seeds on every start in naive implementations | Must NOT overwrite existing admin password in DB on restart |
| **EE tables created on CE-alone start** | CE `create_all` must only create the 13 CE tables | Inspect `information_schema.tables` — assert exactly 13 tables, no EE table names |
| **CE crash when EE wheel installed but licence invalid** | Licence failure must be a warning, not an exception that propagates to startup | Server must start in CE mode; `GET /api/health` must return 200 |

---

## Domain 2: CE vs CE+EE Install Path Divergence

### Table Stakes

| Scenario | Why Expected | Complexity | Notes |
|----------|--------------|------------|-------|
| **GET /api/features returns all `false` on CE** | Feature flag contract — frontend uses this to show/hide EE UI | LOW | `{"rbac": false, "audit": false, "webhooks": false, ...}` |
| **GET /api/features returns all `true` on CE+EE with valid licence** | Inverse of above | LOW | All 8 flags true after EE plugin loads |
| **CE pytest suite passes clean with `pytest -m "not ee_only"`** | CI must be green on the public CE repo with no EE dependency | LOW | Run from `puppeteer/tests/` — zero failures, zero errors |
| **EE tests auto-skip on CE (not fail)** | Skip vs fail is the difference between a passing CI and a broken one | LOW | Run full suite without `-m` flag — EE tests show `s` (skipped), not `F` (failed) |
| **NodeConfig carries no EE-only fields on CE** | `concurrency_limit`, `job_memory_limit`, `job_cpu_limit` removed from CE Pydantic model | LOW | Inspect `GET /api/nodes` response — assert these keys absent on CE |
| **NodeConfig has EE fields when EE active** | EE `register()` adds back resource limit fields via EE `NodeConfig` extension | LOW | Same endpoint on CE+EE — assert `concurrency_limit`, `job_memory_limit`, `job_cpu_limit` present |
| **CE stack has no EE table artefacts after DB init** | Verifies that `create_all` only runs CE models | LOW | `SELECT table_name FROM information_schema.tables WHERE table_schema='public'` — assert no `rbac_*`, `audit_advanced_*`, or other EE table names |

### Differentiators

| Scenario | Value Proposition | Complexity | Notes |
|----------|-------------------|------------|-------|
| **Switch CE → CE+EE at runtime via wheel install + restart** | Validates no DB migration is needed for the EE table additions | HIGH | EE tables are created by EE `create_all` on first EE start. Verify EE tables created without affecting existing CE data |
| **Switch CE+EE → CE (EE wheel removed) gracefully** | Validates CE stubs activate correctly after EE removal | MEDIUM | `pip uninstall axiom-ee` → restart → all 7 routes return 402, DB EE tables still exist but unused |
| **Licence key rotation mid-lifecycle** | Replacing `AXIOM_LICENCE_KEY` env var with a new key and restarting must re-validate without residual state from the old key | MEDIUM | Set valid key, start, verify EE active. Replace with new valid key, restart, verify EE still active. Replace with invalid key, restart, verify CE fallback. |

### Anti-Features to Test For

| Anti-Scenario | Why to Check | What System Should NOT Do |
|---------------|--------------|--------------------------|
| **EE routes return 200 on CE (stubs bypassed)** | If stub registration logic has a bug, EE routes might fall through to unrelated handlers | Every EE route must return exactly 402 on CE, not 200/404/500 |
| **EE tables persist after wheel uninstall and block CE operation** | EE tables in the DB should be invisible to CE (SQLAlchemy `create_all` ignores unknown tables) but must not cause query errors | CE operation must be unaffected by presence of EE tables in the DB |

---

## Domain 3: Job Execution Matrix (4 Nodes × Multiple Failure Modes)

### Table Stakes

| Scenario | Why Expected | Complexity | Notes |
|----------|--------------|------------|-------|
| **4 LXC nodes enrolled with distinct env tags (DEV/TEST/PROD/STAGING)** | Foundation for all env-tag routing tests | MEDIUM | Each LXC node: Ubuntu 24.04, Podman or Docker, `EXECUTION_MODE=direct`, distinct `env_tag` in compose |
| **Job dispatched to `env_tag=DEV` runs only on DEV node** | Env tag routing is the CI/CD promotion mechanism — misrouting is a correctness failure | LOW | Submit 5 jobs with `env_tag=DEV` while other nodes are online; verify all 5 execution records show DEV node |
| **Job dispatched without env_tag runs on any available node** | Untagged jobs must not be artificially restricted | LOW | Submit job without env_tag — assert it routes to any online node |
| **Job with `env_tag=PROD` is not dispatched to DEV node** | Negative routing correctness — prevents premature prod execution | LOW | All nodes online; submit with `env_tag=PROD`; verify DEV/TEST/STAGING nodes never receive it |
| **Fast job completes in < 5s and result captured in ExecutionRecord** | Basic job execution correctness — stdout/stderr persisted, exit code 0 | LOW | `time.sleep(1)` job; assert `status=COMPLETED`, `stdout` non-empty, `exit_code=0` |
| **Slow job (30s) completes without timeout** | Default timeout must accommodate reasonable job durations | LOW | `time.sleep(30)` job; verify completion; confirm `duration_ms` in the expected range |
| **Slow job is not re-assigned to a second node while running** | The job must be locked to the first node during execution — duplicate execution is a correctness failure | HIGH | Submit 30s job; while it is `IN_PROGRESS`, submit identical job; verify second submission gets a new job GUID, not the same one |
| **Memory-light job (< 64 MB) runs on all nodes** | No node should reject a trivially small job | LOW | Job with `memory_limit=64m`; assert all 4 nodes can accept it |
| **Memory-heavy job (4 GB) rejected by nodes with < 4 GB free RAM** | Admission control must refuse over-limit jobs rather than OOM-killing them | MEDIUM | Configure node `job_memory_limit=1g`; submit job with `memory_limit=4g`; verify job stays `PENDING`, not dispatched to that node |
| **Concurrent jobs on same node (within concurrency limit)** | Concurrency limit must be respected — excess jobs stay `PENDING` | HIGH | Set `concurrency_limit=2` on DEV node; submit 5 jobs simultaneously; verify only 2 are `IN_PROGRESS` at any time |
| **Job failure (exit code ≠ 0) recorded with stderr** | Operators must be able to diagnose failures — stderr must be captured | LOW | Job: `sys.exit(1)` with stderr message; assert `status=FAILED`, `exit_code=1`, `stderr` non-empty |
| **Job crash (SIGKILL / exception) recorded as FAILED** | Unhandled exceptions inside the container must not leave jobs stuck in `IN_PROGRESS` | MEDIUM | Job that raises unhandled exception; node agent must catch and report FAILED |
| **Bad signature rejected before execution** | Signature check is the final security gate — must fire even for correctly-structured jobs | HIGH | Submit signed job; corrupt the signature bytes; assert `status=FAILED` with signature error reason, script never executes |
| **REVOKED job signature rejected at dispatch** | Revoked signatures must block dispatch, not just execution | LOW | Mark a signature as REVOKED; attempt dispatch with it; assert 422 or job rejected |
| **Retry policy executes up to max_retries on failure** | Retry machinery must actually retry, not just record a counter | MEDIUM | Job that fails on first attempt, succeeds on second; assert two ExecutionRecords under same `job_run_id`, final status `COMPLETED` |
| **Max_retries=0 job does not retry** | Retry=0 is a valid operator configuration — must not silently retry | LOW | Set `max_retries=0`; fail the job; assert exactly one ExecutionRecord, status `FAILED` |

### Differentiators

| Scenario | Value Proposition | Complexity | Notes |
|----------|-------------------|------------|-------|
| **Env tag cascade test (DEV → TEST → PROD promotion)** | Validates the CI/CD promotion pattern end-to-end: same script, different env tags, sequential execution | HIGH | Submit job to DEV; on COMPLETED, submit to TEST; on COMPLETED, submit to PROD; verify full chain completes |
| **Concurrent jobs across all 4 nodes simultaneously** | Validates that the orchestrator's node selection under load is correct and fair | HIGH | 20 simultaneous job submissions; verify even distribution across 4 nodes based on load; no node starved |
| **Job output capture under high stdout volume** | Large stdout should not cause OOM on the orchestrator or truncation in the DB | MEDIUM | Job that prints 10 MB of stdout; verify full capture in ExecutionRecord (or documented truncation limit) |
| **Node goes offline mid-job — job marked FAILED** | Heartbeat timeout mechanism must detect dead nodes and fail their in-progress jobs | HIGH | Submit long job to a node; kill the node container mid-execution; verify job eventually transitions to FAILED after heartbeat timeout |
| **Job dispatched to node with stale heartbeat is re-queued** | If a node's last heartbeat is older than the timeout, it should not receive new work | MEDIUM | Stop node heartbeats (pause container); submit job; verify it does NOT dispatch to the stale node |
| **Attestation bundle present on every completed job** | Runtime attestation is an EE feature — every completed job execution must produce a verifiable bundle | MEDIUM | Retrieve attestation for 10 completed jobs; verify Ed25519 signature valid on all 10 |

### Anti-Features to Test For

| Anti-Scenario | Why to Check | What System Should NOT Do |
|---------------|--------------|--------------------------|
| **Duplicate job execution (same job runs on two nodes)** | Race condition in node selection — could run the same job twice | A job GUID must appear in at most one node's execution history |
| **Job stuck forever in `IN_PROGRESS` after node death** | Heartbeat timeout cleanup must run and transition the job | `IN_PROGRESS` jobs must transition to `FAILED` within 2× the heartbeat interval after node disappears |
| **Unsigned job runs if signature header is absent** | The orchestrator must require a signature — absence is not the same as valid | Submitting a job with no `signature_id` set must be rejected at dispatch |
| **env_tag mismatch silently drops the job** | If no node matches the env_tag, the job must stay `PENDING` with a clear reason, not silently disappear | Job with `env_tag=NONEXISTENT` stays `PENDING`; never transitions to FAILED without a matching node timeout |

---

## Domain 4: Foundry + Smelter + Air-Gap Mirror

### Table Stakes

| Scenario | Why Expected | Complexity | Notes |
|----------|--------------|------------|-------|
| **Foundry Wizard completes all 5 steps and builds a valid image** | The wizard is the primary operator interface for image building | MEDIUM | Full wizard flow: Identity → Base Image → Ingredients → Tools → Review → Build; assert image pushed to registry |
| **Built image runs the node agent successfully** | An image that doesn't execute jobs is not a valid Foundry output | MEDIUM | Enroll a node using Foundry-built image; submit a simple job; verify COMPLETED |
| **Blueprint with Alpine base builds correctly** | OS-family detection must route to Alpine recipes (APK) not Debian (APT) | MEDIUM | Blueprint with `alpine` in `base_os`; verify Dockerfile uses `apk add`, not `apt-get` |
| **Blueprint with Debian/Ubuntu base builds correctly** | Inverse of Alpine test | LOW | Blueprint with `debian` or `ubuntu` in `base_os`; verify `apt-get install` in Dockerfile |
| **Smelter STRICT mode blocks build on unapproved ingredient** | STRICT enforcement is the hard security gate | LOW | Set `enforcement_mode=STRICT`; add an unapproved ingredient to a blueprint; attempt build; assert 422 or build rejected |
| **Smelter WARNING mode allows build but logs warning** | WARNING is the permissive mode — operators get signal without being blocked | LOW | Set `enforcement_mode=WARNING`; same unapproved ingredient; assert build proceeds but warning in response |
| **CVE-positive ingredient blocked in STRICT mode** | `pip-audit` CVE detection must prevent builds that include known-vulnerable packages | MEDIUM | Add an ingredient with a known-CVE package version (e.g., old `requests`); STRICT mode must reject |
| **CVE scan result cached — repeated builds don't re-audit** | Re-scanning identical ingredients on every build is wasteful and slow | LOW | Verify two consecutive builds with same ingredients don't trigger two pip-audit runs |
| **Air-gapped build uses local PyPI mirror** | `pip.conf` injected into Dockerfile must point to local pypiserver | MEDIUM | Stop external network on build host; trigger build; verify packages installed from `http://pypi-mirror:8080` |
| **Air-gapped build fails fast when mirror missing** | If mirror is configured but unreachable, build must fail immediately, not hang | LOW | Stop pypiserver sidecar; trigger build; assert build fails within 30s with pip connection error |
| **Smelt-Check runs after build and captures BOM** | Post-build validation is part of the Smelter contract | MEDIUM | After successful build, verify a JSON BOM file is stored with all installed packages and versions |
| **Image lifecycle status enforced at enrollment** | REVOKED image must not allow new node enrollments | LOW | Mark a `PuppetTemplate` as REVOKED; attempt to enroll a node using that image; assert enrollment rejected with clear error |
| **Image lifecycle status enforced at work-pull** | DEPRECATED/REVOKED image should prevent nodes from receiving new work | LOW | Mark image DEPRECATED; verify node receives a warning in heartbeat response (or stops receiving work per policy) |

### Differentiators

| Scenario | Value Proposition | Complexity | Notes |
|----------|-------------------|------------|-------|
| **Foundry Wizard edge case: ingredient version conflict** | Two ingredients requiring incompatible versions of the same transitive dependency | HIGH | Construct such a blueprint; verify pip detects the conflict at build time; error surfaced in build log, not silent |
| **Foundry build with missing base image (registry unreachable)** | Build context validation before `docker build` runs | MEDIUM | Specify a non-existent base image tag; verify build fails with a clear error (not a cryptic Docker daemon error) |
| **Foundry build dir cleanup after failed build** | `MIN-7` from gap report — temp dirs leak on failure | MEDIUM | Trigger a build failure; verify `/tmp/puppet_build_*` dir is cleaned up; no disk space leak |
| **Multiple concurrent Foundry builds** | Build endpoint must be non-blocking (async subprocess); two simultaneous builds should not deadlock | HIGH | Submit two template builds simultaneously; verify both complete without one timing out the other |
| **Smelter ingredient soft-delete preserves mirror files** | After `is_active=False`, the mirrored `.whl` must still exist for existing images | LOW | Delete an ingredient via API; verify `.whl` still present in pypiserver storage |
| **BOM package index searchable fleet-wide** | Given a known CVE package, find all images that contain it across the fleet | MEDIUM | Query package index endpoint with a package name; verify all template BOMs containing that package are returned |
| **Air-gapped APT mirror provides packages to build** | APT sidecar must serve packages for `apt-get install` in Debian-based builds | HIGH | Stop external APT access; build Debian blueprint with `apt` packages; verify installed from local APT mirror |

### Anti-Features to Test For

| Anti-Scenario | Why to Check | What System Should NOT Do |
|---------------|--------------|--------------------------|
| **Foundry build silently succeeds when COPY fails** | If the Docker COPY of node agent files fails, the image is broken but build returns 200 | Build must fail and report the COPY error; never return a "successful" image that can't run jobs |
| **pip install silently falls back to PyPI when mirror is unavailable** | `fail-fast` enforcement means mirror unreachability must be fatal, not a silent fallback | When mirror is configured, pip must NOT reach out to pypi.org — any external fetch is a policy violation |
| **Smelter allows a build to proceed with no BOM** | If Smelt-Check container fails to start, BOM must still be recorded (or build must fail — no silent success) | A build with no BOM record should be treated as unvalidated, flagged in UI |
| **REVOKED image enrolls a node when validation is bypassed** | Enrollment endpoint must check `PuppetTemplate.status` — ensure there's no code path that skips this check | Node using REVOKED image must never reach `ACTIVE` status |

---

## Domain 5: Node Lifecycle (Enroll → Heartbeat → Revoke → Re-enroll)

### Table Stakes

| Scenario | Why Expected | Complexity | Notes |
|----------|--------------|------------|-------|
| **Node enrolls from a valid JOIN_TOKEN** | Primary enrollment path — baseline correctness | LOW | Decode token, verify Root CA PEM, sign CSR, assert node appears in `/api/nodes` |
| **Node heartbeat updates `last_seen` and `stats`** | Heartbeat is the liveness signal — stale `last_seen` means operators think nodes are dead | LOW | Heartbeat every 5s for 30s; verify `last_seen` advances; `stats.cpu` and `stats.ram` updated |
| **Node stats history populates `NodeStats` table** | Sparkline charts depend on history — must accumulate across heartbeats | LOW | 10 heartbeats; verify 10 `NodeStats` rows per node (pruned to 60 max) |
| **Node revocation removes node from work-pull eligibility** | Revoked nodes must not receive jobs | LOW | Revoke node via API; verify next `/work/pull` from that node returns 403 |
| **Revoked node cert appears in CRL** | Revocation must propagate to the CRL endpoint | LOW | `GET /system/crl.pem`; verify revoked node's cert serial appears |
| **Revoked node cannot re-enroll with old cert** | Re-enrollment using a revoked client cert must be blocked | LOW | Attempt `/api/enroll` with previously-revoked cert; assert 403 |
| **Node re-enrollment with new CSR (fresh node identity) succeeds** | After revocation, a clean node (new cert) must be able to enroll again | MEDIUM | New `NODE_ID`, new CSR; enroll; verify new node entry in DB |
| **Node concurrency limit enforced** | Node must not run more concurrent jobs than its `concurrency_limit` | MEDIUM | Set `concurrency_limit=1`; submit 3 jobs; verify only 1 is `IN_PROGRESS` at any time on that node |
| **Node resource limit reflected in job admission** | `job_memory_limit` on node must gate which jobs are dispatched | MEDIUM | Set `job_memory_limit=512m`; submit job with `memory_limit=1g`; assert job never dispatched to that node |

### Differentiators

| Scenario | Value Proposition | Complexity | Notes |
|----------|-------------------|------------|-------|
| **Node ID persistence across container restart** | `_load_or_generate_node_id()` — node must reuse existing cert on restart, not generate a new identity | HIGH | Stop node container; restart; verify node appears with same ID in `/api/nodes`, cert reused from secrets volume |
| **NodeStats table pruning at 60 entries** | `MIN-6` from gap report — SQLite compat concern for `DELETE ... ORDER BY LIMIT` | MEDIUM | Send 70 heartbeats to a single node; verify `NodeStats` row count never exceeds 60; verify no SQL error on SQLite |
| **Simultaneous enrollment of all 4 LXC nodes** | Enrollment endpoint must handle concurrent CSR signing without DB constraint violations | HIGH | Start all 4 nodes simultaneously; verify all 4 enroll successfully with unique cert serials |
| **Heartbeat from unknown node_id returns 404 not 500** | Unknown node must be handled gracefully | LOW | Send heartbeat with fabricated node_id; assert 404 with clear error message |
| **Node tags updated via heartbeat** | Node self-reports `env_tag` in heartbeat; orchestrator must accept and persist the update | LOW | Change `ENV_TAG` env var on a running node; verify next heartbeat updates the DB record |

### Anti-Features to Test For

| Anti-Scenario | Why to Check | What System Should NOT Do |
|---------------|--------------|--------------------------|
| **Node generates new ID on every container restart (crash loop)** | `WARN-8` from gap report — non-deterministic node ID scan order can cause this | Node must reuse the ID found in `secrets/` — must NOT generate a fresh UUID if a cert file exists |
| **Revoked node silently receives jobs** | If `/work/pull` CRL check is not consistently applied | Every revoked node attempt at `/work/pull` must return 403, never a job payload |
| **CRL grows unbounded** | Every revocation adds an entry — CRL must be bounded or periodically re-issued | No functional test here for v11.1 but verify CRL is parseable by `openssl crl` after 10 revocations |
| **Node can enroll twice simultaneously (duplicate enrollment race)** | Two instances of the same node enrolling at the same time could produce two DB entries | Simultaneous enrollment from the same `NODE_ID` must produce exactly one DB record |

---

## Feature Dependencies

```
[LXC nodes provisioned with env tags]
    └──required-by──> [Domain 3: Job execution matrix]
    └──required-by──> [Domain 5: Node lifecycle]

[CE cold-start validated]
    └──required-by──> [CE vs CE+EE divergence tests]
    └──required-by──> [Any Foundry/job tests that depend on working API]

[Signing key uploaded + test job signed]
    └──required-by──> [All job dispatch tests]
    └──required-by──> [Bad signature rejection tests]

[Valid test licence keypair generated]
    └──required-by──> [CE+EE cold-start tests]
    └──required-by──> [Licence expiry/rotation tests]

[Foundry Wizard completes + image built]
    └──required-by──> [Foundry-built image node enrollment test]
    └──required-by──> [Image lifecycle enforcement tests]

[Smelter STRICT mode validated]
    └──required-by──> [CVE enforcement edge case tests]
    └──required-by──> [Air-gap mirror validation]
```

### Dependency Notes

- **Node enrollment must precede all job execution tests.** Without enrolled nodes, the job dispatcher has no targets. The 4 LXC nodes must be enrolled and heartbeating before Domain 3 begins.
- **Signing infrastructure must exist before any job tests.** `generate_signing_key.py` must run before jobs can be signed. The signing key must be registered as a `Signature` in the DB.
- **CE cold-start must be verified before CE+EE tests.** The clean-baseline CE test is the control against which CE+EE divergence is measured.
- **Foundry builds are independent of job execution tests** unless the job tests specifically target Foundry-built images. The standard node image (existing LXC deploy) can be used for Domain 3 without Foundry completing first.

---

## Complexity Assessment Per Area

| Area | Complexity | Dominant Risk | Mitigation |
|------|------------|--------------|------------|
| Fresh install (CE) | LOW | Admin re-seed on restart | Check `User` table before seeding |
| Fresh install (CE+EE) | MEDIUM | Entry_points not found / wrong group name | Verify devpi wheel index reachable before test |
| Licence lifecycle | MEDIUM | Test keypair mismatch with compiled binary | Use a dev EE build with swappable public key |
| CE/EE table divergence | LOW | EE tables leak into CE start | Inspect `information_schema.tables` explicitly |
| Job execution — basic | LOW | EXECUTION_MODE=direct required inside Docker | All LXC nodes must have `EXECUTION_MODE=direct` |
| Job execution — concurrency | HIGH | Non-deterministic node selection | Use single-node concurrency test to isolate variable |
| Job execution — node death | HIGH | Heartbeat timeout interval makes this slow | Reduce heartbeat timeout in test config |
| Foundry wizard | MEDIUM | Docker socket not mounted in LXC | Confirm `/var/run/docker.sock` present in agent container |
| Smelter CVE scan | MEDIUM | `pip-audit` not installed in test environment | Verify `pip-audit` in `requirements.txt` |
| Air-gap mirror | HIGH | pypiserver sidecar not started | Ensure `compose.server.yaml` includes mirror sidecars |
| Node lifecycle | MEDIUM | NodeStats SQLite pruning (MIN-6) | Test explicitly against SQLite dev stack |
| Concurrent enrollment | HIGH | CSR signing race condition | Use 4 distinct node IDs with no overlap |

---

## MVP for v11.1 (Minimum Set to Call Validation Complete)

### Must Pass to Close Milestone

- [ ] CE cold-start: 13 tables, admin seeded, 7 stubs return 402
- [ ] CE+EE cold-start: valid licence, EE badge, all features true
- [ ] Licence expiry degrades gracefully to CE (no crash)
- [ ] 4 LXC nodes enrolled with DEV/TEST/PROD/STAGING env tags
- [ ] env_tag routing: job to PROD only runs on PROD node
- [ ] Fast job COMPLETED with stdout captured
- [ ] Memory admission: job with memory_limit > node limit never dispatches
- [ ] Concurrency limit: never more than N concurrent jobs per node
- [ ] Bad signature: job never executes, FAILED with reason
- [ ] Foundry Wizard: image built, node enrolled from it, job runs
- [ ] Smelter STRICT: unapproved ingredient blocks build
- [ ] Air-gap: build succeeds from local PyPI mirror with no external fetch
- [ ] Node revoke: revoked node gets 403 on /work/pull
- [ ] Node re-enroll: fresh identity enrolls after revocation
- [ ] Node restart: same NODE_ID reused, no crash loop

### Deferred to Gap Report (Not Blocking Milestone Close)

- [ ] Concurrent Foundry builds (MIN-7 build dir leak, low urgency)
- [ ] NodeStats SQLite pruning compat (MIN-6, low urgency)
- [ ] Heartbeat timeout → IN_PROGRESS job transition (WARN-8 adjacent, needs timeout config)
- [ ] Full fleet-wide BOM CVE search query
- [ ] per-request DB query optimisation in `require_permission` (MIN-8)

---

## Existing Test Infrastructure — What Already Exists

The `mop_validation/scripts/` directory contains substantial test infrastructure that feeds directly into v11.1:

| Existing Script | Applicable to Domain | Reuse Plan |
|----------------|---------------------|-----------|
| `test_local_stack.py` | Domain 1 (fresh install) | Extend with CE/EE divergence assertions |
| `test_playwright.py` | Domain 1 (dashboard badge) | Add CE/EE edition badge check |
| `generate_signing_key.py` | Domain 3 (signing setup) | Run as prerequisite step |
| `run_signed_job.py` | Domain 3 (basic job) | Template for matrix test variations |
| `test_concurrent_job.py` | Domain 3 (concurrency) | Exists — verify against 4-node setup |
| `test_rce_protection.py` | Domain 3 (bad signature) | Covers signature rejection path |
| `test_local_stack.py` phases 0-7 | Domain 4 (Foundry) | Phases include template build steps |
| `test_installer_lxc.py` | Domain 5 (node lifecycle) | LXC enrollment test — extend for full lifecycle |
| `e2e_api_test.py` | All domains | Comprehensive API-level assertions |

**Gap:** No existing script tests licence lifecycle (expiry, rotation, degradation). New test needed.
**Gap:** No existing script tests the CE vs CE+EE table count divergence explicitly. New assertion needed.
**Gap:** No existing script covers the full node revoke → re-enroll cycle end-to-end in one flow.

---

## Sources

- `/home/thomas/Development/master_of_puppets/.planning/PROJECT.md` — milestone scope, validated
  features, deferred items — HIGH confidence (primary source)
- `/home/thomas/Development/master_of_puppets/.agent/reports/core-pipeline-gaps.md` — MIN-6,
  MIN-7, MIN-8, WARN-8 deferred issues — HIGH confidence (primary source)
- `/home/thomas/Development/master_of_puppets/.planning/MILESTONES.md` — v11.0 known gaps,
  EE-08 / DIST-02 deferred — HIGH confidence (primary source)
- `/home/thomas/Development/mop_validation/scripts/` — existing test scripts inventory — HIGH
  confidence (direct filesystem inspection)
- `/home/thomas/Development/master_of_puppets/puppeteer/tests/` — backend unit test files — HIGH
  confidence (direct filesystem inspection)
- Prior FEATURES.md (v11.0 CE/EE split research) — feature area analysis for licence validation,
  entry_points mechanics, CE/EE table divergence — HIGH confidence (same codebase, one milestone prior)

---

*Feature research for: Axiom v11.1 — adversarial stack validation*
*Researched: 2026-03-20*
