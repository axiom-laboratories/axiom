# Pitfalls Research

**Domain:** Adversarial validation of a CE/EE job orchestration platform — stack teardown/spinup safety, EE test keypair patching in Cython-compiled binaries, LXC node enrollment at scale, SQLite concurrency limits, Foundry Docker-in-Docker, air-gap mirror testing, and gap report quality
**Researched:** 2026-03-20
**Confidence:** HIGH (based on direct codebase inspection of `puppeteer/compose.server.yaml`, `puppeteer/agent_service/db.py`, `puppeteer/agent_service/main.py`, `puppets/node-compose.yaml`, `puppets/secrets/`, `puppets/environment_service/`, plus confirmed knowledge of Axiom v11.0 architecture)

---

## Critical Pitfalls

### Pitfall 1: Teardown Destroys Named Volumes — PKI Root CA and Node Certs Lost

**What goes wrong:**
Running `docker compose -f compose.server.yaml down -v` (or `docker compose down` with `--volumes`) destroys the `certs-volume`, `pgdata`, `caddy_data`, `caddy_config`, and `mirror-data` named volumes. The Root CA keypair lives in `certs-volume`. After teardown all LXC nodes hold client certs signed by a CA that no longer exists. Re-spinup generates a new Root CA with a different key — the old client certs are cryptographically invalid against the new CA, but the nodes still present them. The server accepts or rejects them depending on whether `verify_client_cert()` checks the full chain, creating an unpredictable enrollment state. Node ID persistence (the `secrets/node-*.crt` pattern that prevents re-randomization on restart) means nodes try to reuse a cert that is now from a defunct CA.

Additionally, `pgdata` destruction drops all enrollment tokens, node records, and job history. A clean DB combined with old node certs leads to the node believing it is enrolled (it has certs) while the DB has no record of it — `/work/pull` returns 403 forever until the secrets volume on the node is also cleared.

**Why it happens:**
`-v` is a common cleanup reflex during testing. The distinction between "stop and remove containers" (safe) and "destroy volumes" (destructive) is easy to overlook under time pressure. The teardown feels complete but leaves LXC nodes in a broken state.

**How to avoid:**
Define two distinct teardown procedures:
- **Soft teardown** (between test runs): `docker compose down` with no flags. Containers stop, volumes intact. Re-spinup uses existing certs and DB state.
- **Hard teardown** (full clean slate): `docker compose down -v` AND clear all LXC node `secrets/` directories in the same operation. Make this a single script (`scripts/nuke.sh`) so they cannot be done independently.

Before any hard teardown, snapshot the current Root CA PEM (`docker exec puppeteer-agent-1 cat /app/global_certs/root_ca.crt > backup_root_ca.pem`) for recovery purposes.

**Warning signs:**
- LXC nodes log `SSL handshake failed` or `certificate verify failed` after a stack restart.
- `/work/pull` returns 403 with "Node not found" for a node that was previously enrolled.
- `docker exec puppeteer-agent-1 ls /app/global_certs/` returns a newly generated cert with a different serial than before the restart.
- Nodes have `secrets/node-*.crt` but the orchestrator DB has no matching node record.

**Phase to address:** Phase 1 (stack teardown + fresh install) — define and test both teardown procedures as the first deliverable before any other testing begins.

---

### Pitfall 2: EE Test Keypair Cannot Be Swapped Into a Compiled `.so` Without a Rebuild

**What goes wrong:**
The EE licence validation public key is compiled into the `.so` binary. There is no runtime injection path — the key is a byte constant embedded in the Cython-generated C code. To test EE licence validation with a locally-generated Ed25519 test keypair, you must rebuild the `.so` with the test public key compiled in. Attempts to patch the `.so` after the fact (via binary editing, `LD_PRELOAD`, or monkey-patching the module attribute at runtime) are fragile and unreliable. Specifically:

- Binary editing: the key is embedded as raw bytes in a C string literal. `strings(1)` can find it, but byte offsets shift with any recompile. A wrong patch crashes the process on the first validation call.
- Runtime monkey-patch: Cython-compiled modules expose attributes as `__pyx_cython_string_constants` — they are read-only at the C level. `module.PUBLIC_KEY = new_key` raises `AttributeError: readonly attribute` in compiled modules.
- `LD_PRELOAD` shim: intercepts libc calls but not Python-level attribute access, so this approach fails for Python-embedded key constants.

The result: teams assume they can swap the key without a rebuild and waste hours on approaches that do not work, then discover the key is immutable in the `.so`.

**Why it happens:**
The EE binary is treated as a black box during testing. The test plan says "swap the public key" without specifying that this requires a Cython rebuild with the test key substituted in the source before compilation. This is a workflow gap, not a code bug.

**How to avoid:**
Define a `dev` build variant of the EE wheel from the start:
1. Keep the public key as a named constant in the EE source: `LICENCE_PUBLIC_KEY_BYTES = b"..."`.
2. Make the build script accept a `--test-key path/to/test_public_key.pem` flag that substitutes the constant before Cython compilation.
3. Produce two wheels per CI run: `axiom_ee-*-prod.whl` (production key) and `axiom_ee-*-dev.whl` (test key). The dev wheel is never shipped to customers.
4. The adversarial validation test plan uses only the dev wheel. The test keypair is generated locally with `python -m cryptography hazmat ...` or reusing the existing `toms_home/.agents/tools/admin_signer.py --generate` infrastructure.

Never attempt to patch the production `.so` binary. Always rebuild for test key substitution.

**Warning signs:**
- The test plan says "swap the public key" without specifying a wheel rebuild step.
- The test environment installs the production `axiom_ee` wheel and attempts to inject a different key at runtime.
- `setattr(ee_module, 'LICENCE_PUBLIC_KEY_BYTES', test_key)` appears in any test script.
- `LD_PRELOAD` or `ctypes` patching used to intercept key loading in the compiled module.

**Phase to address:** Phase 2 (EE test infrastructure) — define the dev-wheel build procedure before writing any EE validation test. A dev wheel rebuild must be part of the validation environment setup script.

---

### Pitfall 3: Parallel LXC Node Enrollment Race — Token Consumed Before CSR Arrives

**What goes wrong:**
The enrollment endpoint marks the token as `used = True` immediately on first access (line 1919 of `main.py`). When 4 LXC nodes are provisioned simultaneously with `JOIN_TOKEN`-based enrollment, two failure modes emerge:

**A) Shared token race:** If the provisioning script reuses the same enrollment token for all 4 nodes (e.g., generating one token and embedding it in all 4 node compose files), the first node to arrive invalidates the token. Nodes 2-4 get `403 Invalid or Expired Enrollment Token` — they are silently stuck in the startup enrollment loop. The node agent retries enrollment, but the token is permanently used, so retries also return 403. The node appears running (container is up) but never appears in the dashboard.

**B) Per-node tokens, DB write conflict:** Even with one token per node, 4 simultaneous `POST /api/enroll` requests hit the async DB session. SQLite (if used in dev) serializes writes. Under aiosqlite's default serialization, 4 concurrent `UPDATE tokens SET used=True` operations will serialize correctly but may all read the token as "not used" before any commit lands, depending on isolation level. Under SQLite's default `DEFERRED` transaction isolation, the second concurrent write sees the pre-commit state and also marks the token as "used" — but the token was already invalidated by the first writer after commit. This creates a window where two nodes believe they enrolled with the same token and the second DB write silently updates the node record to the second node's CSR/cert.

**Why it happens:**
The pull model and token-based enrollment design assumes sequential enrollment (one node, then another). Parallel provisioning of 4 nodes was not in scope for earlier sprints. The enrollment endpoint is not designed with concurrent access in mind.

**How to avoid:**
- Generate one unique token per LXC node before provisioning. Never reuse tokens. Use `POST /admin/tokens` 4 times, capture each token, and inject into the corresponding node's environment.
- For the adversarial test: add a `SELECT ... FOR UPDATE` (Postgres) or `BEGIN IMMEDIATE` (SQLite) around the token lookup to prevent read-then-write race. In Postgres (production stack), `SELECT ... FOR UPDATE` is the correct pattern — already safe if using Postgres for the validation stack.
- Stage enrollments: start all 4 nodes, but add a staggered delay (`NODE_ENROLL_DELAY_SECONDS=N*5` where N is node index) in the node startup script to prevent the 4 CSRs from landing simultaneously.
- Verify enrollment by polling `GET /nodes` after all 4 containers start. All 4 node IDs must appear before proceeding.

**Warning signs:**
- Only 1-3 nodes appear in the dashboard after starting 4 LXC containers.
- Node container logs show `403 Invalid or Expired Enrollment Token` on the first enrollment attempt.
- Enrollment token list shows all 4 tokens as `used=True` but fewer than 4 nodes exist in the DB.
- Two nodes share the same `node_id` hostname (if hostnames were not unique).

**Phase to address:** Phase 3 (LXC node provisioning) — pre-generate unique tokens for each node and make this part of the provisioning script. Document the single-token-per-node invariant.

---

### Pitfall 4: SQLite Write Locking Under Concurrent Job Polling

**What goes wrong:**
The dev stack uses SQLite via `aiosqlite`. SQLite has a single write lock — only one writer at a time. During the concurrent job test (multiple nodes polling `/work/pull` simultaneously), each poll is a read-modify-write cycle: `SELECT` pending jobs, `UPDATE job SET status=ASSIGNED, node_id=...`. With 4 nodes polling every few seconds:

- Each poll acquires a write lock for the UPDATE.
- Concurrent polls queue behind the lock — no deadlock, but latency spikes.
- Under load (short poll intervals, many pending jobs), the queue depth grows until aiosqlite connection timeout is reached — the poll request fails with `sqlite3.OperationalError: database is locked`.
- The node catches the error and retries after its poll interval, but if the retry also locks, the node effectively stops receiving jobs.

The deferred gap MIN-6 (SQLite `NodeStats` pruning compat) is a related issue — pruning queries under load can hold write locks for extended periods.

**Why it happens:**
SQLite's writer-serialization model is correct for single-process dev usage. Concurrent async access via `aiosqlite` with multiple simultaneous request handlers hits the write lock limit. This was not a problem with 1-2 test nodes but manifests with 4 nodes all polling at the same interval.

**How to avoid:**
- **Use Postgres for the validation stack**, not SQLite. The compose stack already has Postgres via `pgdata`. Set `DATABASE_URL` to the Postgres URL in `puppeteer/.env` before starting the validation stack. Postgres has row-level locking and handles concurrent writes without database-level locks.
- If SQLite is required for any test scenario: enable WAL mode explicitly at startup via `PRAGMA journal_mode=WAL`. Add to `db.py` engine creation: `connect_args={"check_same_thread": False}` for aiosqlite, plus a `@event.listens_for(engine.sync_engine, "connect")` hook that runs `PRAGMA journal_mode=WAL` on every new connection. WAL mode allows concurrent readers while a single writer is active, dramatically reducing lock contention.
- Stagger node poll intervals: set different `POLL_INTERVAL` values per node (e.g., 3s, 4s, 5s, 6s) to prevent synchronized polling storms.

**Warning signs:**
- `/work/pull` returns 500 with `sqlite3.OperationalError: database is locked` in server logs.
- Nodes stop receiving jobs under load despite jobs being in PENDING state.
- SQLite `jobs.db` file size grows unexpectedly (WAL file accumulates if checkpointing is not triggered).
- Server logs show many concurrent requests to `/work/pull` timing out simultaneously.

**Phase to address:** Phase 4 (job test matrix with concurrent nodes) — switch to Postgres before concurrent testing. If SQLite is intentionally tested, add WAL mode first.

---

### Pitfall 5: Foundry Build Touches Docker Socket From Inside the Compose Stack — Wrong Context Path

**What goes wrong:**
Foundry builds via `foundry_service.py` run `docker build` using the Docker socket mounted at `/var/run/docker.sock` inside the `agent` container. The build context path is resolved relative to the container filesystem. The compose file mounts `../puppets:/app/puppets:ro`. Inside the container, `foundry_service.py` uses `/app/puppets` as the build context.

However, `docker build` is executed via the Docker socket — which means the Docker daemon receives the build context from the socket client (the agent container). The build context is sent as a tar archive from the *agent container's* filesystem perspective. If `foundry_service.py` constructs the build context path as `/tmp/puppet_build_{id}` (the correct pattern after BUG-5 was fixed), this temp directory is inside the agent container. The Docker daemon (running on the host) receives the tar correctly.

The new failure mode in adversarial testing: Foundry builds initiated during validation may use `localhost/master-of-puppets-node:latest` as the `FROM` image. If this image does not exist in the host Docker registry (only in the local LXC nodes or only built once), the build fails with `manifest unknown`. The validation environment must pre-build and tag the base node image before Foundry tests.

Additionally, `docker build` inside the compose stack runs as root inside the `agent` container and writes temp directories to `/tmp`. These are never cleaned up (deferred gap MIN-7). Over a long validation run with many Foundry builds, `/tmp` fills up and subsequent builds fail with `No space left on device`.

**Why it happens:**
Foundry is tested in isolation (one build at a time) during development. Adversarial testing triggers multiple builds in sequence or parallel, exposing the cleanup gap. The base image requirement is implicit — it is assumed to exist because the developer has previously built it locally.

**How to avoid:**
- Before any Foundry test: `docker build -t localhost/master-of-puppets-node:latest -f puppets/Containerfile.node puppets/` on the host and verify with `docker images`.
- After each Foundry build test: `docker exec puppeteer-agent-1 rm -rf /tmp/puppet_build_*` to manually clear the build dirs, or add a cleanup call to the Foundry test script.
- If testing Foundry builds with a local registry, ensure the registry container is running and accessible before the test: `curl http://localhost:5000/v2/_catalog` must return a valid response.
- For adversarial concurrency tests (multiple simultaneous Foundry builds): add a unique suffix to the temp dir name (already uses `{id}`) and increase `/tmp` tmpfs size in the agent container via `tmpfs: /tmp:size=2g` in `compose.server.yaml`.

**Warning signs:**
- Foundry build fails with `manifest for localhost/master-of-puppets-node:latest not found`.
- Build fails with `No space left on device` during `docker build`.
- `docker exec puppeteer-agent-1 ls /tmp/puppet_build_*` shows many stale directories from prior test runs.
- Registry returns 503 or connection refused when Foundry tries to push the built image.

**Phase to address:** Phase 5 (Foundry + Smelter deep test) — pre-flight checklist must include base image existence and `/tmp` cleanup. Add a cleanup step between Foundry tests.

---

### Pitfall 6: Air-Gap Mirror Test Requires Network Isolation — Without It, pip Falls Back to PyPI Silently

**What goes wrong:**
The air-gap mirror test verifies that `pip install` from Foundry-built images uses only the local PyPI mirror (hosted at port 8080). The failure mode: the test passes even when the local mirror is broken, because pip silently falls back to the real PyPI if the mirror returns a 404 or connection error. The test appears to succeed (packages install) but is not actually testing air-gap operation — it is testing normal internet-connected install.

The mirror `fail-fast` flag in Axiom enforces that the mirror must be used, but this enforcement is at the `mirror_service.py` level (for mirror sync operations). At the node level, `pip install` uses a generated `pip.conf` that points to the local mirror. If a package is not present in the local mirror, pip returns an error (no fallback, because `--index-url` was set). However, if the `pip.conf` was not injected correctly (e.g., the Foundry build did not include the `pip.conf` injection recipe), pip uses its default PyPI URL with no error.

**Why it happens:**
Testing the air-gap scenario without actual network isolation relies on behavioral correctness of the `pip.conf` injection, not actual absence of internet. The test cannot distinguish "mirror worked" from "mirror failed, but PyPI worked" without blocking internet.

**How to avoid:**
- Use a network namespace or iptables rules to block outbound internet from the test container during air-gap tests:
  ```bash
  # On the host, before the test
  iptables -I DOCKER-USER -s <node_container_ip> -d 0.0.0.0/0 ! -d 192.168.0.0/16 -j REJECT
  # Run Foundry build — pip must succeed using only the local mirror
  # After test
  iptables -D DOCKER-USER ...
  ```
  Alternatively, run the Foundry build inside an LXC container with no external network profile.
- After the Foundry build, verify `pip.conf` was injected: `docker run --rm <built_image> cat /etc/pip.conf` must show `index-url = http://<mirror_host>:8080/simple`.
- Check the local PyPI mirror contains the required packages before the test: `curl http://localhost:8080/simple/<package_name>/` must return a valid index page.

**Warning signs:**
- Air-gap test passes but `curl http://pypi.org/simple/requests/` from inside the test container succeeds (network is not blocked).
- Built image has no `/etc/pip.conf` or the file points to `pypi.org` rather than the local mirror.
- `pip install` during the test takes longer than normal (internet latency instead of LAN mirror latency).
- Local mirror is empty (`curl http://localhost:8080/simple/` returns no packages) but test still passes.

**Phase to address:** Phase 5 (Foundry + Smelter deep test) — air-gap test must include an explicit network isolation step. Document the iptables procedure in the test script.

---

### Pitfall 7: Job Failure Test — Bad Signature vs Expired Licence vs Crashed Script All Look the Same in Logs

**What goes wrong:**
Three distinct failure modes in adversarial job testing produce similar symptoms at the node level:
1. **Bad signature**: the node rejects the job before executing it. The job stays ASSIGNED indefinitely (the node does not report a failure result).
2. **Expired licence (EE only)**: EE features gate job dispatch in certain configurations. The job may never reach the node or may be rejected at pickup with no clear error returned to the server.
3. **Crashed script**: the job executes, the script exits with non-zero code, the node reports FAILED with exit code in the result.

All three appear as "job stuck in ASSIGNED" or "job FAILED" without indicating which layer failed. The gap: the orchestrator `ExecutionRecord` captures stdout/stderr from crashed scripts, but signature rejection and licence rejection at the node level produce no `ExecutionRecord` at all — the job is simply never completed, and the node's rejection reason is only in the node's container log, not in the orchestrator DB.

**Why it happens:**
The pull model means nodes pull work and reject silently if local checks fail. There is no push-back mechanism for "I pulled this job but refused to run it" — the node simply does not post a result, and the job stays in ASSIGNED until timeout (if any timeout is implemented).

**How to avoid:**
- For adversarial signature tests: after submitting a bad-signature job, check the node container logs directly (`docker logs <lxc-node-container>`) for the signature rejection message within 15 seconds. Do not wait for the orchestrator dashboard to show a failure.
- Define expected outcomes per failure mode in the test plan:
  | Failure | Expected node log | Expected orchestrator state |
  |---------|-------------------|-----------------------------|
  | Bad signature | `Signature verification failed` | Job stuck ASSIGNED |
  | Expired licence | EE gate rejection at `/work/pull` or in EE plugin | Job stays PENDING (not assigned) or ASSIGNED with no result |
  | Crashed script | Exit code N in node log | Job FAILED with stdout/stderr in ExecutionRecord |
- For the "bad signature" test specifically: after confirming the node log shows the rejection, manually set the job status to FAILED via a direct DB update or admin API call, so the test can continue without a stuck ASSIGNED job blocking node capacity.
- Add a timeout to job assignment: if a job stays ASSIGNED for more than N seconds without a heartbeat update from the assigned node, auto-requeue it as PENDING. This is a platform gap that adversarial testing should surface and log.

**Warning signs:**
- Job is stuck in ASSIGNED for more than 2x the node poll interval with no result appearing.
- `GET /api/executions?job_id=<guid>` returns no records for a job that should have a failure record.
- The orchestrator dashboard shows ASSIGNED with no progress, but node container is running.
- All three failure modes look identical from the orchestrator perspective.

**Phase to address:** Phase 4 (job failure mode testing) — pre-define the diagnostic steps for each failure mode before running tests. Establish the "check node container logs" step as mandatory for any ASSIGNED job with no result.

---

## Technical Debt Patterns

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| Using one enrollment token for all nodes | Simpler provisioning script | First node consumes token; nodes 2-4 get 403 silently | Never — always generate N tokens for N nodes |
| Testing air-gap without actual network isolation | Faster test setup | Test passes even with internet fallback; false confidence | Never for release validation |
| Testing EE key patching without a dev wheel rebuild | Skips Cython rebuild step | Patch approaches all fail on compiled `.so`; hours wasted | Never — rebuild is the only valid path |
| `docker compose down -v` for teardown between runs | Complete cleanup | Destroys Root CA; all LXC nodes break | Never without simultaneous node secrets cleanup |
| SQLite for concurrent node validation tests | No DB server needed | `database is locked` errors under 4-node polling load | Acceptable for single-node tests only |
| Skipping `/tmp` cleanup between Foundry builds | Faster iteration | Disk fills up; later builds fail with `No space left` | Never in a multi-build test run |
| Vague gap report entries ("improve X") | Faster to write | Actionable for nothing; no fix can be verified | Never — every gap must have a reproduction step and acceptance criterion |

---

## Integration Gotchas

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|------------------|
| LXC nodes + Compose stack | LXC container network cannot reach `puppeteer-agent-1` hostname | Use `host.docker.internal` or host IP as `AGENT_URL`; ensure LXC container has network access to the host port 8001 |
| LXC nodes + mTLS | LXC node presents cert signed by old Root CA after stack teardown + rebuild | Clear `secrets/` on each LXC node before re-enrolling; do not reuse node cert files across stack rebuilds |
| Foundry + local registry | Push to `localhost:5000` from inside the `agent` container fails | Use the container-internal registry hostname (`registry:5000`) not `localhost:5000` — Docker networking resolves `registry` via the compose network |
| Foundry + base image | `FROM localhost/master-of-puppets-node:latest` fails in Foundry build | Image must exist in the host Docker daemon registry, not just locally built with `docker build` in a previous session that was cleared |
| Air-gap mirror + pip | pip falls back to PyPI if mirror returns 404 | Block internet at the network level during air-gap tests; verify `pip.conf` was injected into the built image |
| EE dev wheel + CE install | Install dev wheel into the same venv as production CE | Use an isolated venv per EE build variant; never mix dev and prod EE wheels in the same Python environment |
| Concurrent polling + SQLite | 4 nodes poll simultaneously on SQLite dev DB | Use Postgres for any multi-node validation; enable WAL mode if SQLite is unavoidable |
| Job signing + node verification | Node verifies signature against the server-registered public key | Test keypair used for signing must be registered in `signatures` table on the orchestrator before submitting the signed job |

---

## Performance Traps

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|----------------|
| 4 LXC nodes at identical poll intervals | Synchronized polling storms; write lock queuing on SQLite | Stagger poll intervals by 1-2s per node | At 3+ nodes with < 5s poll interval on SQLite |
| Foundry builds leave `/tmp/puppet_build_*` dirs | Disk fills; later builds fail with `No space left on device` | Cleanup step after each build test; increase tmpfs size | After 5-10 builds of large images |
| APScheduler firing all cron jobs at same second | Multiple jobs dispatched simultaneously; node queue depth spikes | Stagger cron schedules by at least 30s between definitions in the test matrix | Any time 3+ cron definitions have the same minute expression |
| node stats history query on 60 rows × 4 nodes | Acceptable at 4 nodes; not a trap for this scale | No action needed at 4 nodes | Documented: breaks at 1000+ nodes |
| Concurrent Foundry builds (>2 simultaneous) | Docker daemon build queue; agent HTTP request timeout | Run Foundry builds sequentially in the test matrix | Immediately if builds exceed the agent HTTP timeout (~120s) |

---

## Security Mistakes

| Mistake | Risk | Prevention |
|---------|------|------------|
| Embedding the production EE licence public key in the dev/test wheel | Test fixture generates forged licences that pass validation on the production binary | Keep dev and prod wheel builds completely separate; dev key must never be embedded in the same binary as the prod key |
| Using a fixed, predictable test JOIN_TOKEN in LXC compose files | Token committed to git is usable by anyone who clones the repo | Regenerate tokens before each validation run; never commit live tokens to git |
| Testing mTLS revocation without verifying CRL is served | Revoked node may still receive work if the CRL is not reachable | After revoking a node, curl `GET /system/crl.pem` and verify the revoked cert's serial is present before testing work rejection |
| Running the validation stack with `ENCRYPTION_KEY` unset | Secrets stored as plaintext; encryption test results are meaningless | Set `ENCRYPTION_KEY` to a real Fernet key in `puppeteer/.env` before validation; verify with `docker exec puppeteer-agent-1 env | grep ENCRYPTION_KEY` |
| Signing test jobs with the operator's real production signing key | Test job scripts submitted and signed with real credentials; if test scripts are malicious, the node executes them | Generate a separate Ed25519 keypair specifically for test jobs; register it as a test signature entry; delete it after validation |

---

## UX Pitfalls

| Pitfall | User Impact | Better Approach |
|---------|-------------|-----------------|
| Gap report entries with no reproduction steps | Developers cannot reproduce or verify a fix | Every gap entry must include: observed behaviour, reproduction steps, expected behaviour, acceptance criterion |
| Gap report mixes critical bugs with cosmetic issues in a flat list | Critical fixes deprioritised; cosmetic fixes done first | Three-tier severity: CRITICAL (blocks jobs or breaks security) / MODERATE (degrades UX) / DEFERRED (known acceptable shortcut) |
| Gap report created only at the end | Findings from early phases are forgotten or underspecified | Log findings inline during each test phase; write the gap entry immediately after observing the issue |
| Vague gap entries like "node enrollment is fragile" | Actionable by nobody | Required fields: affected component, reproduction steps, severity, proposed fix |
| Marking a gap DEFERRED without a tracking note | Gap is silently forgotten | Every DEFERRED entry must reference the milestone where it will be addressed (e.g., "DEFERRED to v12.0 — EE-08") |

---

## "Looks Done But Isn't" Checklist

- [ ] **Stack teardown + fresh install:** Run `docker compose down -v` AND clear LXC node secrets simultaneously. Confirm fresh stack generates a new Root CA. Confirm all 4 LXC nodes re-enroll cleanly against the new CA.
- [ ] **EE dev wheel installed:** `pip show axiom-ee` inside the agent container must show the dev wheel (test public key). `GET /api/features` must return `ee_status: loaded`. A licence signed with the test private key must be accepted. A licence signed with a wrong key must be rejected.
- [ ] **All 4 LXC nodes enrolled:** `GET /nodes` must return exactly 4 nodes, all in ONLINE status. Verify each node has the correct `env_tag` (DEV/TEST/PROD/STAGING).
- [ ] **Concurrent job dispatch:** Dispatch 8 jobs simultaneously. Verify all 8 reach COMPLETED (or FAILED with a result) — none stuck in ASSIGNED.
- [ ] **Bad signature rejection:** Submit a job signed with an unregistered key. Confirm the node log shows rejection. Confirm no ExecutionRecord is created in the orchestrator for this job.
- [ ] **Foundry build completes cleanly:** After a Foundry build, verify `/tmp/puppet_build_*` has been cleaned. Verify the built image exists in the local registry. Verify a node can be enrolled using the Foundry-built image.
- [ ] **Air-gap test uses real isolation:** `curl https://pypi.org/simple/requests/` from inside the test container during the air-gap test must fail. Packages must install successfully from the local mirror only.
- [ ] **Gap report is actionable:** Every entry has: severity, component, reproduction steps, expected behaviour, proposed fix or DEFERRED milestone reference. No entry is a single sentence.
- [ ] **SQLite is not used for concurrent tests:** `DATABASE_URL` in the running stack must point to Postgres (`postgresql+asyncpg://...`), not SQLite. Verify: `docker exec puppeteer-agent-1 env | grep DATABASE_URL`.
- [ ] **CRL reflects revoked node:** After revoking a node, `GET /system/crl.pem` must contain the revoked cert serial. The revoked node must not receive work on the next poll.

---

## Recovery Strategies

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|----------------|
| Teardown destroyed Root CA, nodes broken | MEDIUM | Clear all LXC node `secrets/` directories; run hard teardown on stack; fresh install; re-enroll all nodes |
| EE dev wheel not buildable (Cython environment issue) | HIGH | Install Cython + build toolchain in the test environment; `pip install cython cibuildwheel`; rebuild dev wheel from EE source with test key |
| LXC nodes stuck at 403 after token race | LOW | Generate 4 new tokens; update each LXC node env with its dedicated token; restart node containers |
| SQLite locked under concurrent tests | LOW | Switch `DATABASE_URL` to Postgres in `puppeteer/.env`; restart the agent container; re-run concurrent tests |
| Foundry `/tmp` full | LOW | `docker exec puppeteer-agent-1 rm -rf /tmp/puppet_build_*`; free at least 2GB before re-running builds |
| Air-gap test false positive | LOW | Add `iptables` block for the test container; re-run; verify pip uses only local mirror |
| Vague gap report | MEDIUM | Re-run the test that produced the vague entry; observe and document precisely; rewrite the entry with reproduction steps |

---

## Pitfall-to-Phase Mapping

| Pitfall | Prevention Phase | Verification |
|---------|------------------|--------------|
| Teardown destroys Root CA (P1) | Phase 1 — define soft/hard teardown scripts before any test | Fresh stack after hard teardown + LXC secrets clear → all 4 nodes re-enroll cleanly |
| EE key immutable in compiled `.so` (P2) | Phase 2 — dev wheel build procedure defined before EE tests | `GET /api/features` shows `ee_status: loaded` with test-key-signed licence |
| Parallel enrollment token race (P3) | Phase 3 — per-node token generation in provisioning script | `GET /nodes` shows all 4 nodes ONLINE after parallel spinup |
| SQLite locking under concurrent polling (P4) | Phase 4 — Postgres confirmed before concurrent job test | No `database is locked` errors in server logs during 8-job concurrent dispatch |
| Foundry `/tmp` cleanup and base image (P5) | Phase 5 — pre-flight checklist + cleanup step in test script | Foundry builds succeed across a 5-build sequence; `/tmp` stays clean |
| Air-gap mirror without network isolation (P5) | Phase 5 — network isolation added to air-gap test procedure | `curl https://pypi.org/` fails during test; packages install from local mirror |
| Failure modes all look identical (P4) | Phase 4 — per-failure-mode diagnostic steps defined upfront | Correct node log message found for bad-sig, expired licence, and crash within 30s of job submission |
| Vague gap report entries | All phases — gap template enforced from Phase 1 | Every gap entry passes the checklist (severity, reproduction, acceptance criterion) |

---

## Sources

- Direct inspection: `puppeteer/compose.server.yaml` (named volumes: `certs-volume`, `pgdata`, `caddy_data`; Docker socket mount; `../puppets:/app/puppets:ro`)
- Direct inspection: `puppeteer/agent_service/db.py` line 12 — SQLite default with `aiosqlite`; no WAL mode configured; no `connect_args`
- Direct inspection: `puppeteer/agent_service/main.py` lines 1912-1919 — token marked `used=True` immediately on first request, before CSR is processed
- Direct inspection: `puppets/node-compose.yaml` — single JOIN_TOKEN in compose file; `./secrets:/app/secrets` volume mount; node ID persistence pattern
- Direct inspection: `puppets/secrets/` — contains `node-3d795c2c.crt`, `node-3d795c2c.key`, `root_ca.crt`, `verification.key` (confirms secrets persist in volume)
- PROJECT.md v11.1 milestone definition — confirms: EE test keypair, 4 LXC nodes (DEV/TEST/PROD/STAGING), concurrent job tests, Foundry/Smelter deep test, air-gap mirror fallback
- Existing PITFALLS.md (CE/EE split domain, 2026-03-19) — confirms EE public key is compiled into `.so`; confirms Cython compiled modules have read-only attribute restrictions
- `.agent/reports/core-pipeline-gaps.md` — MIN-7 (build dir cleanup deferred), MIN-6 (SQLite NodeStats pruning compat deferred), WARN-8 (non-deterministic node ID scan)
- SQLite documentation: WAL mode required for concurrent readers + single writer; `DEFERRED` default isolation — https://www.sqlite.org/wal.html
- Cython documentation: compiled module attributes are read-only at the C level — attribute assignment raises `AttributeError` — https://cython.readthedocs.io/en/latest/src/tutorial/cdef_classes.html
- Docker socket + Foundry DinD: build context is sent from the socket-client container's filesystem; `docker build` via mounted socket is the established pattern — https://jpetazzo.github.io/2015/09/03/do-not-use-docker-in-docker-for-ci/

---
*Pitfalls research for: Axiom v11.1 Stack Validation — adversarial testing, LXC nodes, EE binary patching, SQLite concurrency, Foundry DinD, air-gap mirror, gap report quality*
*Researched: 2026-03-20*
