# Project Research Summary

**Project:** Axiom v11.1 — Stack Validation
**Domain:** Adversarial end-to-end validation of a CE/EE job orchestration platform
**Researched:** 2026-03-20
**Confidence:** HIGH

## Executive Summary

Axiom v11.1 is a validation milestone, not a feature milestone. All implementation work (CE/EE plugin wiring, licence validation, Foundry/Smelter, RBAC, audit log, node lifecycle) is complete from prior sprints. The goal is to stress-test every subsystem under adversarial conditions — from a clean-slate install — across five test domains: fresh install (CE and CE+EE), CE vs EE install path divergence, a 4-node LXC job execution matrix, Foundry and Smelter deep validation, and the full node lifecycle. The research confirms that all tooling required for v11.1 is already installed on the host (Incus 6.22, Docker 29.2.1, cryptography 46.0.5) and that all new work is test harness scripts in `mop_validation/`, not product code changes.

The recommended approach is a strict CE-first, EE-second validation order. The CE pass must complete cleanly before the EE wheel is installed. EE validation requires a dev-build wheel with a test Ed25519 public key compiled in — there is no runtime path to swap the key in a Cython `.so` without a rebuild. However, for development testing the pure-Python source path (editable `pip install -e .`) avoids Cython compilation entirely: patch `_LICENCE_PUBLIC_KEY_BYTES` directly in `ee/plugin.py`, set `PYTHONPATH` to the raw source, and skip `.so` compilation. This is the recommended dev shortcut for v11.1 adversarial validation. A full Cython rebuild is required only for production-fidelity `.so` testing.

The dominant risks are infrastructure risks, not code risks. Hard teardown (`docker compose down -v`) destroys the Root CA and leaves LXC nodes with certs signed by a defunct CA — teardown and LXC node secrets clearing must be a single atomic operation. Parallel enrollment of 4 LXC nodes races on the single-use token endpoint — one token per node, generated separately, is mandatory. SQLite write locking breaks under concurrent 4-node polling; the validation stack must use Postgres. These three pitfalls are responsible for the majority of wasted time in adversarial testing. Prevention is simple if addressed before Phase 38 begins.

## Key Findings

### Recommended Stack

No new packages are needed. All tooling is already present: `incus` 6.22 on the host, `cryptography` 46.0.5, Docker 29.2.1, and `requests`/`python-dotenv` already in `mop_validation/`. New test scripts use only Python stdlib (`subprocess`, `concurrent.futures.ThreadPoolExecutor`, `base64`, `json`, `time`) plus these existing libraries. The four new scripts to create are: `teardown_fresh_install.py`, `provision_lxc_nodes.py`, `generate_licence_key.py`, and `validate_v11_1.py`.

**Core technologies:**
- `incus` 6.22: provision and manage 4 LXC test nodes — already installed and confirmed working; launch sequentially to avoid bridge IP race, configure in parallel via threads
- `cryptography` 46.0.5: generate Ed25519 test keypair and sign test licence payloads — same library the EE plugin uses for verification; zero new dependencies
- `concurrent.futures.ThreadPoolExecutor` (stdlib): submit concurrent jobs and configure LXC nodes in parallel — correct tool for parallel HTTP calls in a synchronous test script
- `docker compose down -v`: full stack teardown including named volumes — mandatory for clean-slate validation; must always be paired with LXC node `secrets/` cleanup
- Postgres (already in `compose.server.yaml`): required for all concurrent multi-node tests; SQLite write locking (`database is locked`) breaks under 4-node concurrent polling

### Expected Features

This milestone has no user-facing features. The test scope, expressed as pass/fail criteria, is the deliverable.

**Must pass to close milestone:**
- CE cold-start: 13 CE tables created, admin seeded once, all 7 EE stub routes return 402
- CE+EE cold-start: valid test licence accepted, EE badge shown, all feature flags true
- Licence expiry and missing key both degrade gracefully to CE mode without server crash
- 4 LXC nodes enrolled with distinct DEV/TEST/PROD/STAGING env tags, all ONLINE
- Env-tag routing: job targeting PROD only executes on the PROD node, never on DEV/TEST/STAGING
- Fast job completes with stdout/stderr captured in ExecutionRecord
- Memory admission: job with memory_limit exceeding node limit never dispatches to that node
- Concurrency limit: never more than N concurrent jobs on a single node at one time
- Bad signature: job never executes; node log shows rejection; no ExecutionRecord created
- Foundry wizard: image built end-to-end, node enrolled from it, job executes on it
- Smelter STRICT mode: unapproved ingredient blocks build with 422
- Air-gap: build succeeds using only local PyPI mirror with internet explicitly blocked at network level
- Node revoke: revoked node gets 403 on `/work/pull`; cert serial appears in CRL
- Node re-enroll: fresh node identity enrolls successfully after prior revocation
- Node restart: same NODE_ID reused from `secrets/`; no crash loop

**Deferred (not blocking milestone close):**
- Concurrent Foundry builds (MIN-7 build dir leak)
- NodeStats SQLite pruning compat (MIN-6)
- Heartbeat timeout to IN_PROGRESS job auto-transition (WARN-8 adjacent — needs configurable timeout)
- Fleet-wide BOM CVE search query
- Per-request DB query optimisation in `require_permission` (MIN-8)

**Gaps identified by research:**
- No existing script tests licence lifecycle (expiry, rotation, degradation to CE) — new test needed in Phase 42
- No existing script tests CE vs CE+EE table count divergence explicitly — new `information_schema` assertion needed
- No existing script covers full node revoke → re-enroll cycle in a single flow — new test needed

### Architecture Approach

The v11.1 validation stack layers new test harness scripts on top of the fixed v11.0 architecture. No production code is modified. The control plane (agent/db/cert-manager/devpi/registry/mirror) runs in Docker Compose as-is. The 4 LXC nodes (Incus, Ubuntu 24.04, `security.nesting=true`, `EXECUTION_MODE=direct`) communicate with the control plane via the Incus bridge host IP — not `172.17.0.1`, which is the Docker bridge and unreachable from Incus containers. Phase ordering is strictly enforced by hard dependencies: teardown before install, CE validation before EE, nodes enrolled before job tests, EE licence confirmed before EE feature tests.

**Major components (new for v11.1):**
1. `teardown_fresh_install.py` — atomic hard teardown: `docker compose down -v --remove-orphans` plus clearing all LXC node `secrets/` in the same operation
2. `provision_lxc_nodes.py` — launches 4 Incus containers sequentially, configures them in parallel, injects per-node JOIN_TOKEN and env-tagged `node-compose.yaml` via `incus file push`
3. `generate_licence_key.py` — generates Ed25519 test keypair, patches `ee/plugin.py` `_LICENCE_PUBLIC_KEY_BYTES`, builds dev wheel or runs in pure-Python editable mode, produces signed test licence key
4. `validate_v11_1.py` — orchestrates the full validation suite across all 5 domains, produces structured pass/fail output for the gap report
5. `lxc-{dev,test,prod,staging}/node-compose.yaml` — per-env-tag Docker Compose files for each LXC node, with `ENV_TAG`, `AGENT_URL`, `JOIN_TOKEN`, and `EXECUTION_MODE=direct`

**EE keypair patching — resolved conflict between ARCHITECTURE.md and PITFALLS.md:**
ARCHITECTURE.md recommends `pip install -e .` (editable install, patch `.py` source, skip Cython compilation) for dev testing. PITFALLS.md correctly states that compiled `.so` attributes are read-only and cannot be patched at runtime. Both are correct in different contexts. Patching the `.py` source and using an editable install avoids the compiled `.so` entirely — this is the recommended path for v11.1 adversarial dev validation. A full Cython rebuild (`cibuildwheel` or `python -m build --wheel`) is required only for production-fidelity `.so` testing (verifying the compiled binary works, not just the Python source). Use the editable install path for all local adversarial validation in v11.1.

**LXC networking:**
LXC containers sit on the `incusbr0` bridge, not the Docker bridge. `AGENT_URL` must be set to `https://<incusbr0-host-ip>:8001`, discovered dynamically via `ip addr show incusbr0 | grep 'inet ' | awk '{print $2}' | cut -d/ -f1`. Nodes communicate with the FastAPI agent directly on port 8001 (self-signed cert, `VERIFY_SSL=false`), not through Caddy on 443.

### Critical Pitfalls

1. **Hard teardown destroys Root CA without clearing LXC node certs** — define two teardown modes: soft (`docker compose down`, volumes intact, safe between test runs) and hard (`docker compose down -v` AND `rm -rf secrets/` on all LXC nodes as a single atomic script). Never run hard teardown without the LXC cleanup step or nodes will present certs from a defunct CA.

2. **EE public key cannot be swapped into compiled `.so` at runtime** — Cython module attributes are read-only at the C level; `setattr()` raises `AttributeError`. For v11.1 dev validation, use `pip install -e .` on raw `axiom-ee/` source and patch `_LICENCE_PUBLIC_KEY_BYTES` directly in the `.py` file — no Cython rebuild needed. For production-fidelity testing, rebuild the wheel with the test key substituted before compilation.

3. **Parallel LXC enrollment races on single-use tokens** — the enrollment endpoint marks tokens `used=True` immediately on first access. Generate one unique JOIN_TOKEN per node via 4 separate calls to `POST /admin/tokens` before provisioning. Never share one token across all 4 nodes.

4. **SQLite write locking breaks under 4-node concurrent polling** — use Postgres for all multi-node validation. Confirm `DATABASE_URL` points to `postgresql+asyncpg://...` before running any concurrent job tests. SQLite's `DEFERRED` isolation and single write lock serialise all `/work/pull` polls, causing `database is locked` errors under load.

5. **Air-gap test passes even when internet is available** — pip silently falls back to PyPI if the local mirror returns a 404 and `--index-url` is not set in `pip.conf`. Actual network isolation (iptables block on the test container) is required; verify `curl https://pypi.org/` fails from inside the container during the test. Also verify `/etc/pip.conf` was injected into the Foundry-built image before the test.

## Implications for Roadmap

The phase structure is already defined in ARCHITECTURE.md as Phases 38–45. The ordering is enforced by hard dependencies. All phases are new test harness work in `mop_validation/` — no changes to the Axiom product code.

### Phase 38: Clean Teardown + Fresh CE Install
**Rationale:** Cannot test anything else without a known-clean stack state. Teardown must be destructive enough to catch PKI re-initialisation bugs that only surface on true first run — residual volumes mask these bugs entirely.
**Delivers:** `teardown_fresh_install.py` script (safe to run repeatedly); verified CE cold-start; CE regression baseline via existing `test_local_stack.py`; confirmation `GET /api/licence` returns `community`.
**Addresses:** CE cold-start table stakes (13 tables, admin seeded once, 7 stubs return 402).
**Avoids:** Pitfall 1 (teardown without LXC secrets cleanup leaves nodes with defunct CA certs).

### Phase 39: EE Test Keypair + Dev Wheel
**Rationale:** No stack dependency — can overlap with Phase 38. But its output (`test_licence.key`) is required before Phase 42 can begin. Establishing the dev keypair early avoids blocking the EE validation pass.
**Delivers:** `generate_licence_key.py`; patched `ee/plugin.py` with test public key; editable EE install (or compiled dev wheel); `mop_validation/secrets/test_licence.key` ready for injection.
**Addresses:** CE+EE cold-start domain; licence lifecycle edge cases (expiry, missing key, degradation).
**Avoids:** Pitfall 2 (attempting to patch the compiled `.so` at runtime — use editable install instead).

### Phase 40: LXC Node Provisioning
**Rationale:** Depends on Phase 38 (stack healthy, JOIN_TOKEN endpoint live). All job execution and node lifecycle tests require enrolled nodes; nothing in Domain 3 or 5 can proceed without this.
**Delivers:** `provision_lxc_nodes.py`; 4 LXC containers (DEV/TEST/PROD/STAGING) enrolled and ONLINE; per-env-tag `node-compose.yaml` files; Postgres confirmed as `DATABASE_URL` before concurrent tests.
**Addresses:** 4-node LXC enrollment, env-tag routing foundation, concurrent enrollment correctness.
**Avoids:** Pitfall 3 (per-node token generation in provisioning script) and Pitfall 4 (Postgres confirmed here before any concurrent test runs).

### Phase 41: CE Validation Pass
**Rationale:** CE baseline must be clean before EE is layered on. Failures here are definitively CE bugs, not EE interaction bugs. This is the control condition.
**Delivers:** CE env-tag routing verified; job matrix (fast/slow/crash/bad-sig/retry/concurrent) executed on CE; cron job firing verified; all anti-features confirmed absent.
**Addresses:** Job execution matrix table stakes; node lifecycle table stakes; failure mode diagnostic steps defined and verified.
**Avoids:** Pitfall 7 (failure modes all look identical — per-failure diagnostic steps defined before running; node container logs checked within 15s for bad-signature jobs).

### Phase 42: EE Validation Pass
**Rationale:** Depends on Phase 39 (test keypair) and Phase 41 (clean CE baseline). First assertion must be `GET /api/licence` → `{"edition": "enterprise"}` — gate all EE tests on this; a silent CE fallback (wrong public key) will make all EE tests fail with confusing 402 errors.
**Delivers:** EE cold-start verified; all feature flags true; EE routes respond with real data; Foundry/RBAC/audit log smoke-tested; resource limits admission verified; licence lifecycle edge cases (expiry, missing, rotation) covered.
**Addresses:** CE vs CE+EE install path divergence domain (table count, NodeConfig field presence, feature flag contract).
**Avoids:** Pitfall 5 (testing EE features before confirming licence loaded — `GET /api/licence` assertion is the first EE test).

### Phase 43: Job Test Matrix
**Rationale:** Depends on Phase 42 (full EE stack, 4 LXC nodes enrolled). Concurrent submission uses `ThreadPoolExecutor`. The concurrency limit enforcement under 4-node load is the highest-risk test in the matrix.
**Delivers:** Full job matrix results documented: fast/slow/light-memory/heavy-memory/concurrent/crash/bad-sig/multi-env/retry cases with pass/fail and timing data.
**Addresses:** Job execution matrix differentiators and anti-features (duplicate execution, stuck ASSIGNED, unsigned job bypass, env-tag mismatch silent drop).
**Avoids:** Pitfall 4 (Postgres confirmed in Phase 40 before this runs).

### Phase 44: Foundry + Smelter Deep Pass
**Rationale:** Depends on Phase 42 (EE stack). Independent of Phase 43 (job matrix). Foundry builds are independent of job execution unless specifically validating Foundry-built image nodes.
**Delivers:** Foundry wizard end-to-end build verified; CVE enforcement (STRICT/WARNING modes); air-gap mirror test with real iptables network isolation; image lifecycle enforcement (REVOKED/DEPRECATED); Smelt-Check BOM verified.
**Addresses:** Foundry + Smelter domain table stakes and anti-features (silent COPY failure, pip fallback to PyPI, BOM missing on build failure).
**Avoids:** Pitfall 5 (pre-flight checklist: base image `localhost/master-of-puppets-node:latest` must exist before Foundry tests; `/tmp` cleanup between builds); Pitfall 6 (air-gap test with actual iptables isolation, not just behavioral check of `pip.conf`).

### Phase 45: Gap Report Synthesis
**Rationale:** Depends on all previous phases. Gap findings must be logged inline during each phase — not reconstructed at the end. A retrospective gap report is always less accurate than inline logging.
**Delivers:** `v11_1_validation_report.md` with CRITICAL/MODERATE/DEFERRED triage; inline critical fixes where straightforward; every entry includes severity, component, reproduction steps, expected behaviour, and DEFERRED milestone reference where applicable.
**Addresses:** Gap report quality anti-patterns (vague entries, flat severity list, no reproduction steps, no DEFERRED tracking).

### Phase Ordering Rationale

- Phase 38 must be first: a clean stack is the precondition for all other phases; residual volumes mask cold-start bugs.
- Phase 39 can overlap Phase 38 (no stack dependency) but must complete before Phase 42.
- Phase 40 requires Phase 38 (JOIN_TOKEN endpoint must be live).
- Phase 41 (CE pass) must precede Phase 42 (EE pass) — non-negotiable. EE can paper over CE bugs.
- Phases 43 and 44 both depend on Phase 42 and are independent of each other; order between them does not matter.
- Phase 45 depends on all prior phases; gap entries must be logged inline throughout, not at the end.

### Research Flags

Phases with standard, well-documented patterns (no additional research needed):
- **Phase 38:** Stack teardown and cold-start follow existing `test_local_stack.py` patterns exactly.
- **Phase 39:** Ed25519 key generation is verified and documented in phase 37 research; editable install is standard Python tooling.
- **Phase 40:** Incus provisioning follows `manage_node.py` — extending to 4 nodes with env tags is mechanical.
- **Phase 41:** CE job execution patterns are covered by `run_signed_job.py` and `test_concurrent_job.py`.

Phases likely to surface unexpected findings (log inline; do not defer):
- **Phase 42:** EE licence loading at startup has not been adversarially tested. Silent CE fallback (public key mismatch) is the main risk and is invisible from the API until `GET /api/licence` is checked explicitly.
- **Phase 43:** Concurrent job dispatch race conditions (duplicate execution, stuck ASSIGNED) have not been tested under 4-node load. `concurrency_limit` column enforcement is the highest-risk area.
- **Phase 44:** Air-gap mirror validation has never been run with real network isolation. The `pip.conf` injection path in `foundry_service.py` is the highest-risk code path — verify the built image contains `/etc/pip.conf` before running the air-gap test.

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | All tools verified live on host (`incus --version`, `docker --version`, `python3 -c "from cryptography..."`); no new dependencies; patterns match existing test scripts exactly |
| Features | HIGH | Derived from direct inspection of `PROJECT.md` milestone definition, `core-pipeline-gaps.md`, and `mop_validation/scripts/` inventory; test domains fully specified with complexity ratings |
| Architecture | HIGH | All components derived from direct inspection of `compose.server.yaml`, existing node compose files, `manage_node.py`, and v11.0 architecture; LXC networking pitfall confirmed from existing CLAUDE.md note about bridge IP |
| Pitfalls | HIGH | All 7 critical pitfalls derived from direct code inspection: token mark-as-used at line 1919 of `main.py`, `aiosqlite` without WAL mode in `db.py`, Cython read-only attribute constraint, named volume list from `compose.server.yaml`, air-gap fallback behaviour from pip documentation |

**Overall confidence:** HIGH

### Gaps to Address

- **Licence lifecycle log messages:** The exact log output for "licence expired" and "licence key missing" has not been verified against the current EE plugin source — check during Phase 42 setup so tests can assert the correct log lines.
- **`concurrency_limit` enforcement under concurrent load:** The column exists and `job_service.py` reads it, but concurrent admission under 4-node polling has not been stress-tested. This is the test most likely to reveal a timing bug. Run exclusively on Postgres.
- **Foundry `pip.conf` injection path:** Whether `pip.conf` is correctly injected into Foundry-built images depends on the recipe in `foundry_service.py`. Verify the built image contains `/etc/pip.conf` pointing to the local mirror before the air-gap test runs.
- **Incus bridge host IP variability:** The `incusbr0` bridge IP (`10.x.x.x`) varies between host configurations. All provisioning scripts must derive it dynamically — never hardcode it.

## Sources

### Primary (HIGH confidence)

- `puppeteer/compose.server.yaml` — service topology, named volumes (`pgdata`, `certs-volume`, `caddy_data`, `mirror-data`), Docker socket mount, port exposures
- `puppeteer/agent_service/db.py` — SQLite default with `aiosqlite`; no WAL mode configured; no `connect_args`
- `puppeteer/agent_service/main.py` lines 1912–1919 — token marked `used=True` immediately on first request before CSR is processed
- `.agent/skills/manage-test-nodes/scripts/manage_node.py` — Incus provisioning pattern, `security.nesting=true`, Ubuntu 24.04 base, SSH key injection
- `mop_validation/scripts/test_local_stack.py` — existing test harness structure, AGENT_URL pattern, auth flow, phase 0–7 structure
- `mop_validation/scripts/test_concurrent_job.py` — signing pattern, job submission structure, `requests` session use
- `mop_validation/local_nodes/node_alpha/node-compose.yaml` and `node_beta/node-compose.yaml` — ENV_TAG per-node pattern, EXECUTION_MODE=direct confirmed
- `.planning/milestones/v11.0-phases/37-licence-validation-docs-docker-hub/37-CONTEXT.md` — licence key wire format (`base64url(payload).base64url(sig)`), `AXIOM_LICENCE_KEY`, `_LICENCE_PUBLIC_KEY_BYTES` location in `ee/plugin.py`
- `.planning/axiom-oss-ee-split.md` — CE/EE table split (13 CE tables, 15 EE tables)
- `.planning/PROJECT.md` — v11.1 milestone goals, 5 test domains, deferred items
- `.agent/reports/core-pipeline-gaps.md` — MIN-6, MIN-7, MIN-8, WARN-8 deferred issues
- `puppets/secrets/` — confirms secrets persist in volume (`node-3d795c2c.crt`, `node-3d795c2c.key`, `root_ca.crt`, `verification.key` present)

### Secondary (MEDIUM confidence)

- SQLite WAL mode documentation — concurrent reader/single-writer model; `DEFERRED` default isolation behaviour under `aiosqlite` concurrent writes
- Cython documentation — compiled module attributes are read-only at the C level; `AttributeError` on attribute assignment in compiled submodules

---
*Research completed: 2026-03-20*
*Ready for roadmap: yes*
