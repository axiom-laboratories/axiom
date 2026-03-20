# Architecture Research: v11.1 Stack Validation

**Domain:** Adversarial end-to-end validation of the Axiom CE/EE stack — fresh install, LXC nodes, EE test keypair, job test matrix
**Researched:** 2026-03-20
**Confidence:** HIGH — all components derived from direct codebase inspection

---

## Context Note

This file supersedes the v11.0 architecture research (CE/EE plugin wiring) for the purposes of the v11.1 milestone. v11.0 implementation is complete and that architecture is now a fixed constraint. v11.1 adds a validation harness on top of it. Where the v11.0 plugin wiring is relevant context it is referenced, not re-documented.

---

## System Overview

### Full v11.1 Validation Stack

```
┌─────────────────────────────────────────────────────────────────────┐
│  HOST MACHINE (Linux, Docker daemon running)                        │
│                                                                     │
│  Control Plane (Docker Compose — puppeteer/compose.server.yaml)    │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌─────────┐  │
│  │ agent    │ │ db       │ │ cert-mgr │ │ docs     │ │ devpi   │  │
│  │ :8001    │ │ postgres │ │ caddy    │ │ nginx    │ │ :3141   │  │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘ └─────────┘  │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐              │
│  │ model    │ │ pypi     │ │ mirror   │ │ registry │              │
│  │ :8000    │ │ :8080    │ │ :8081    │ │ :5000    │              │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘              │
│                                                                     │
│  Local Docker Nodes (mop_validation/local_nodes/)                  │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐               │
│  │ puppet-alpha │ │ puppet-beta  │ │ puppet-gamma │               │
│  │ ENV=PROD     │ │ ENV=TEST     │ │ ENV=DEV      │               │
│  │ tags:hello,  │ │ tags:network,│ │ tags:foundry │               │
│  │   mounted    │ │   ping       │ │   mounted    │               │
│  └──────────────┘ └──────────────┘ └──────────────┘               │
│                                                                     │
│  Incus LXC Containers (4 new for v11.1)                            │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌───────────┐ │
│  │ lxc-dev      │ │ lxc-test     │ │ lxc-prod     │ │lxc-staging│ │
│  │ ENV=DEV      │ │ ENV=TEST     │ │ ENV=PROD     │ │ENV=STAGING│ │
│  │ Ubuntu 24.04 │ │ Ubuntu 24.04 │ │ Ubuntu 24.04 │ │Ubuntu 24  │ │
│  │ + Docker     │ │ + Docker     │ │ + Docker     │ │ + Docker  │ │
│  └──────────────┘ └──────────────┘ └──────────────┘ └───────────┘ │
│                                                                     │
│  mop_validation/ (test harness — separate repo)                    │
│  ├── scripts/test_local_stack.py   (existing CE regression suite)  │
│  ├── scripts/validate_v11_1.py     (NEW — v11.1 validation runner) │
│  ├── scripts/generate_licence_key.py  (NEW — test EE licence)      │
│  ├── scripts/teardown_fresh_install.py  (NEW — clean teardown)     │
│  └── local_nodes/lxc-{dev,test,prod,staging}/node-compose.yaml    │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Component Responsibilities

### Existing Components (fixed — do not modify)

| Component | Responsibility | Location |
|-----------|----------------|----------|
| `agent` service | FastAPI API, job dispatch, node enrollment, EE plugin host | `puppeteer/agent_service/` |
| `db` service | PostgreSQL 15 — all CE + EE tables | `compose.server.yaml` |
| `cert-manager` | Caddy TLS, Root CA, ACME, mTLS enforcement | `puppeteer/cert-manager/` |
| `devpi` | Internal PyPI for EE compiled wheel | `compose.server.yaml` |
| `registry` | Docker registry for Foundry-built node images | `compose.server.yaml` :5000 |
| `ee/plugin.py` | EE startup, licence validation, router mounting | `axiom-ee/` (private, compiled .so) |
| `node.py` | Puppet node agent — poll, execute, heartbeat | `puppets/environment_service/` |
| `manage_node.py` | Single Incus LXC lifecycle (launch/teardown) | `.agent/skills/manage-test-nodes/scripts/` |

### New Components for v11.1

| Component | Responsibility | Location | Status |
|-----------|----------------|----------|--------|
| `teardown_fresh_install.py` | Deterministic stack teardown preserving nothing (volumes, certs, PKI) | `mop_validation/scripts/` | CREATE |
| `provision_lxc_nodes.py` | Multi-node LXC provisioning (4 nodes, env-tagged) | `mop_validation/scripts/` | CREATE |
| `generate_licence_key.py` | Generate test Ed25519 keypair + signed test licence key | `mop_validation/scripts/` | CREATE |
| `validate_v11_1.py` | Orchestrate full v11.1 validation suite (CE pass, EE pass, job matrix) | `mop_validation/scripts/` | CREATE |
| `lxc-{dev,test,prod,staging}/node-compose.yaml` | Docker Compose for each env-tagged LXC node | `mop_validation/local_nodes/` | CREATE |
| `EE test keypair` | Ed25519 key in `~/Development/axiom-ee/test_keys/` — dev build only | `axiom-ee/` | CREATE |
| `ee_dev` Docker image | CE+EE image with test public key baked in — for validation only | local build | CREATE |

---

## Integration Points

### New vs Modified — Clear Distinction

| Component | New or Modified | Notes |
|-----------|----------------|-------|
| `compose.server.yaml` | Modified — CE variant | Add `AXIOM_LICENCE_KEY` env var on `agent` service for EE validation pass |
| `ee/plugin.py` build | Modified — dev build | Swap hardcoded public key bytes for test public key during validation |
| `manage_node.py` | Not modified | Existing single-node script; new `provision_lxc_nodes.py` wraps it |
| `test_local_stack.py` | Not modified | Existing CE regression suite runs unchanged |
| `local_nodes/node_alpha/` | Not modified | Existing local Docker nodes keep their compose files |
| All API routes | Not modified | Validation is black-box API testing only |

### Critical Integration: EE Test Keypair

The EE plugin has an Ed25519 **public key hardcoded as bytes** in the compiled `plugin.py`. In production this is the Axiom Labs key. For validation testing, the compiled `.so` must embed a **test public key** that the validation harness controls.

Two approaches — pick one per validation run:

**Approach A (preferred): dev build with test key**
Build a separate `axiom-ee` wheel with the test public key swapped in before compilation. This wheel is tagged `0.1.0.dev1` or `0.1.0+test` and never published. The validation compose file installs this dev wheel via devpi.

**Approach B: env var override (requires CE code change)**
Add `AXIOM_LICENCE_PUBLIC_KEY_OVERRIDE` env var support to `plugin.py`. If set, use that key instead of the hardcoded one. This is a development convenience escape hatch; only meaningful if the `.so` is built with this override path compiled in.

Approach A is recommended — it requires no changes to the production code path and keeps the test infrastructure fully isolated from the production EE build.

### Internal Boundaries

| Boundary | Communication | Notes |
|----------|---------------|-------|
| `teardown_fresh_install.py` → Docker | `subprocess` + `docker compose down -v` | Must remove named volumes (pgdata, certs-volume, etc.) to guarantee clean state |
| `provision_lxc_nodes.py` → Incus | `incus launch / exec / file push` (same pattern as `manage_node.py`) | 4 containers in parallel; each gets Docker installed (not Podman) for compatibility with existing node-compose pattern |
| LXC node → Control Plane | `AGENT_URL=https://<host-ip>:8001` using `extra_hosts` bridge pattern | LXC containers use Incus bridge IP, not 172.17.0.1; must discover host IP dynamically |
| `generate_licence_key.py` → `validate_v11_1.py` | File-based — writes `test_licence.key` to `mop_validation/secrets/` | Licence key is a `base64url(payload).base64url(sig)` dot-separated string passed as `AXIOM_LICENCE_KEY` |
| `validate_v11_1.py` → API | `requests` over HTTPS to `localhost:8001`, verify=False (self-signed dev cert) | Same pattern as existing `test_local_stack.py` |
| devpi → agent container | `pip install --index-url http://devpi:3141/...` in Containerfile | devpi is already in `compose.server.yaml`; EE dev wheel is pushed there before stack up |

---

## Build Order

Dependencies between phases enforce the following order. Each phase is a prerequisite for the next.

### Phase 38: Clean Teardown + Fresh CE Install

**Must come first.** All subsequent validation requires a known-clean stack state.

1. `teardown_fresh_install.py` — `docker compose down -v --remove-orphans`, wipe `secrets/`, reset `jobs.db` if present
2. Rebuild CE-only agent image with `docker compose -f compose.server.yaml build agent`
3. Start stack CE-only (no `AXIOM_LICENCE_KEY`)
4. Run `test_local_stack.py` — establishes CE regression baseline
5. Verify `GET /api/licence` → `{"edition": "community"}`
6. Verify `GET /api/blueprints` → 402

**Rationale:** Can't test EE over CE if there are residual EE artefacts from previous runs. Can't test nodes if control plane isn't healthy. Teardown must be destructive (volumes included) to catch PKI re-initialization bugs.

**Risk:** If `init_db()` or PKI init has bugs that only surface on first run (vs. restart-from-existing), a teardown-less validation misses them entirely.

### Phase 39: EE Test Keypair + Dev Build

**Depends on:** Nothing stack-related — can run in parallel with Phase 38, but output needed for Phase 40.

1. `generate_licence_key.py` — generates Ed25519 keypair, writes `test_keys/signing.key` + `test_keys/verification.key` to `axiom-ee/test_keys/` (git-ignored)
2. Patch `axiom-ee/ee/plugin.py` — replace production public key bytes constant with test public key bytes
3. Build EE dev wheel with cibuildwheel (or `pip install -e .` for a source build in dev): `axiom-ee-0.1.0.dev1`
4. Push dev wheel to devpi: `twine upload --repository devpi axiom_ee-0.1.0.dev1-*.whl`
5. `generate_licence_key.py --sign` — produce a valid test licence key signed by the test private key, valid 90 days, all features enabled

**Output:** `mop_validation/secrets/test_licence.key` — the `AXIOM_LICENCE_KEY` value for EE validation runs.

**Rationale:** EE licence validation is startup-only. The key must be in the environment when the agent container starts. If the public key in the `.so` doesn't match the signing key, EE features silently stay disabled — making it look like CE mode. This phase establishes the trusted keypair that the rest of v11.1 depends on.

### Phase 40: LXC Node Provisioning

**Depends on:** Phase 38 (stack healthy and JOIN_TOKEN available).

1. `provision_lxc_nodes.py` — launch 4 Incus containers: `axiom-lxc-dev`, `axiom-lxc-test`, `axiom-lxc-prod`, `axiom-lxc-staging`
2. Each container gets: Docker (not Podman), Python 3, SSH key injection, passwordless sudo
3. `GET /api/nodes/join-token` for each env tag → store in `mop_validation/secrets.env`
4. Push `node-compose.yaml` to each LXC via `incus file push`, setting `ENV_TAG`, `JOIN_TOKEN`, `AGENT_URL`
5. Start node agents on each LXC: `incus exec <name> -- docker compose up -d`
6. Wait for each node to appear in `GET /api/nodes` with `status=online`

**Key difference from existing nodes:** LXC nodes use Docker inside the container (not Podman). The existing local Docker nodes (`node_alpha/beta/gamma`) mount `/var/run/docker.sock` from the host. LXC nodes run Docker **inside** the LXC container — this is enabled by `security.nesting=true` on the Incus launch (already in `manage_node.py`). The `EXECUTION_MODE=direct` is used (Python subprocess) to avoid nested Docker-in-Docker cgroup issues, consistent with the existing test node pattern.

**LXC node compose template:**
```
ENV_TAG={DEV|TEST|PROD|STAGING}
AGENT_URL=https://<incus-bridge-host-ip>:8001
VERIFY_SSL=false
JOIN_TOKEN=<per-node token>
EXECUTION_MODE=direct
NODE_TAGS=lxc,<env-tag-lower>
```

**Rationale:** 4 nodes covering all 4 env tags enables testing of `env_tag` targeting, DEV→TEST→PROD promotion dispatch, and concurrent multi-env job runs. The STAGING env tag is not covered by existing local nodes.

### Phase 41: CE Validation Pass

**Depends on:** Phase 38 (clean CE stack), Phase 40 (LXC nodes enrolled).

Run existing `test_local_stack.py` plus:

1. Job dispatch targeting each env tag — verify only the matching node picks up the job
2. Concurrent dispatch to all 4 env tags simultaneously
3. Failure modes: bad signature, crash exit, memory limit exceeded (if EE resource limits not yet needed, skip memory test to Phase 42)
4. Cron job definition firing, verifying execution record created

**Rationale:** CE regression baseline before EE layer goes on top. Any failures here are CE bugs.

### Phase 42: EE Validation Pass

**Depends on:** Phase 39 (test keypair + dev wheel ready), Phase 41 (CE baseline clean).

1. Stop agent container
2. Rebuild CE+EE agent image: install `axiom-ee-0.1.0.dev1` from devpi, set `AXIOM_LICENCE_KEY=<test_licence.key contents>` in env
3. Start stack (EE mode)
4. Verify `GET /api/licence` → `{"edition": "enterprise", "customer_id": "test", "features": [...]}`
5. Verify `GET /api/features` → all true
6. Verify EE routes respond (not 402): `/api/blueprints`, `/admin/audit-log`, `/api/webhooks`
7. Foundry: create blueprint, create template, build image
8. Smelter: register ingredient, run CVE scan
9. RBAC: create operator user, verify permission enforcement
10. Audit log: check events from steps above are recorded
11. Resource limits: dispatch job with memory limit, verify admission check

**Rationale:** Validates that the compiled `.so` functions correctly end-to-end, not just that it loads.

### Phase 43: Job Test Matrix

**Depends on:** Phase 42 (full EE stack with 4 LXC nodes).

| Test | Profile | Expected |
|------|---------|----------|
| Fast job | 1s sleep, 10MB | COMPLETED, execution record captured |
| Slow job | 60s sleep | RUNNING during poll, COMPLETED after |
| Light memory | 50MB alloc | COMPLETED |
| Heavy memory | 500MB alloc (if limit 256MB) | FAILED with OOM |
| Concurrent | 5 jobs same node | All COMPLETED, no deadlock |
| Crash exit | `sys.exit(1)` | FAILED, stderr captured |
| Bad signature | script modified post-sign | REJECTED at node (not dispatched) |
| Bad sig bypass attempt | unsigned script via API | 422 validation error at API |
| Multi-env dispatch | 4 jobs, 4 env tags | Each lands on correct env |
| Retry | fail 2× then succeed | 3 ExecutionRecords, final COMPLETED |

**Rationale:** These are the categories most likely to expose timing bugs, race conditions in job_service.py, and resource accounting errors. They must be in a fixed matrix so the gap report is reproducible.

### Phase 44: Foundry + Smelter Deep Pass

**Depends on:** Phase 42 (EE stack, Foundry available).

1. Foundry wizard: 5-step blueprint → template → build via Foundry wizard UI
2. CVE enforcement: STRICT mode, ingredient with known CVE → verify build blocked
3. Air-gap mirror: disable external network access, verify pypi mirror serves packages
4. Image lifecycle: mark image DEPRECATED → verify dispatch rejects it
5. Smelt-Check BOM: verify JSON BOM generated, package index entries created

**Rationale:** Foundry and Smelter have the most complex internal state machine. Edge cases here are likely.

### Phase 45: Gap Report Synthesis

**Depends on:** All previous phases complete.

1. Collect all FAIL/SKIP outcomes from phases 41–44
2. Categorise: critical (blocks v12.0), moderate (should fix), minor (deferred)
3. Patch critical bugs inline
4. Write `.agent/reports/v11_1_validation_report.md`

---

## Data Flow

### Test Job End-to-End Flow

```
Operator machine
    ↓ (1) axiom-push sign job_script.py --key test_keys/signing.key
    ↓     → produces signature (base64-encoded Ed25519 sig)
    ↓
    ↓ (2) POST /api/signatures  {name, public_key}
    ↓     → signature_id stored in DB
    ↓
    ↓ (3) POST /api/jobs  {script, signature, signature_id, env_tag="DEV", ...}
    ↓     → job_service validates sig against registered public key
    ↓     → Job record created, status=PENDING
    ↓
Control Plane (agent_service)
    ↓ (4) job_service.assign_job()
    ↓     → SELECT node WHERE env_tag="DEV" AND status=online AND capabilities match
    ↓     → Job.node_id set, status=ASSIGNED
    ↓
LXC node (axiom-lxc-dev)
    ↓ (5) node.py polls GET /work/pull  (every N seconds)
    ↓     → server returns WorkResponse {script, signature, ...}
    ↓     → node verifies Ed25519 sig locally (cryptography lib)
    ↓     → if invalid: job rejected, error reported back
    ↓
    ↓ (6) runtime.py execute()  (EXECUTION_MODE=direct)
    ↓     → Python subprocess, captures stdout/stderr
    ↓     → exit code captured
    ↓
    ↓ (7) POST /work/complete  {job_id, status, stdout, stderr, exit_code}
    ↓
Control Plane
    ↓ (8) ExecutionRecord created  {job_id, node_id, output, status, duration}
    ↓
Dashboard / API consumer
    (9) GET /api/executions?job_id=X  → execution history visible
```

### Fresh Install Teardown + Spinup Sequence

```
teardown_fresh_install.py:
    (1) docker compose -f puppeteer/compose.server.yaml down -v --remove-orphans
        → removes: pgdata, certs-volume, caddy_data, caddy_config, registry-data, mirror-data
    (2) rm -rf puppeteer/secrets/ puppets/secrets/   (local cert artefacts)
    (3) rm -f puppeteer/jobs.db                      (SQLite if present)
    (4) PASS → "Stack fully torn down. No residual state."

fresh_install_ce.py (or manual):
    (1) docker compose build agent                    (CE image, no EE wheel)
    (2) docker compose up -d                          (stack cold start)
    (3) wait_for https://localhost:8001/health
    (4) init_db() runs: 13 CE tables created
    (5) Root CA generated (new PKI — different CA from previous runs)
    (6) Admin user seeded (from ADMIN_PASSWORD env var)
    (7) GET /api/features → all false
    (8) PASS → CE install clean

fresh_install_ee.py:
    (1) Push EE dev wheel to devpi (already done in Phase 39)
    (2) Rebuild agent image: COPY axiom-ee-0.1.0.dev1 from devpi, pip install
    (3) Set AXIOM_LICENCE_KEY in compose env
    (4) docker compose up -d
    (5) wait_for https://localhost:8001/health
    (6) init_db() + EEPlugin.register() → 28 tables total
    (7) GET /api/licence → {"edition": "enterprise"}
    (8) PASS → EE install clean
```

### EE Keypair Patching Flow

```
generate_licence_key.py:
    (1) Ed25519PrivateKey.generate()
    (2) Write signing.key (PEM) → axiom-ee/test_keys/signing.key
    (3) Write verification.key (PEM) → axiom-ee/test_keys/verification.key

patch_ee_plugin.py (or manual step in build script):
    (4) Read verification.key → extract raw public key bytes (32 bytes)
    (5) In axiom-ee/ee/plugin.py, replace:
            _LICENCE_PUBLIC_KEY = b"\x<prod bytes>"
        with:
            _LICENCE_PUBLIC_KEY = b"\x<test bytes>"
    (6) cibuildwheel (or pip install -e .) → builds dev wheel
    (7) twine upload --repository devpi axiom_ee-0.1.0.dev1-*.whl

generate_licence_key.py --sign:
    (8) Construct payload: {"customer_id": "test", "exp": <now+90days>, "features": ["foundry", "webhooks", "triggers", "rbac", "smelter", "resource_limits", "service_principals", "api_keys"]}
    (9) base64url(json.dumps(payload)) → payload_b64
    (10) Ed25519PrivateKey.sign(payload_b64.encode()) → sig_bytes
    (11) base64url(sig_bytes) → sig_b64
    (12) Write: payload_b64 + "." + sig_b64 → mop_validation/secrets/test_licence.key
```

---

## Recommended Project Structure

### New Files for v11.1 Validation

```
mop_validation/
├── scripts/
│   ├── teardown_fresh_install.py    # Stack teardown (new)
│   ├── provision_lxc_nodes.py       # 4-node LXC provisioning (new)
│   ├── generate_licence_key.py      # Ed25519 keypair + licence signing (new)
│   ├── validate_v11_1.py            # Orchestration runner (new)
│   └── test_local_stack.py          # Existing — unchanged
└── local_nodes/
    ├── node_alpha/                  # Existing — unchanged
    ├── node_beta/                   # Existing — unchanged
    ├── node_gamma/                  # Existing — unchanged
    ├── lxc-dev/
    │   └── node-compose.yaml        # New — ENV_TAG=DEV, EXECUTION_MODE=direct
    ├── lxc-test/
    │   └── node-compose.yaml        # New — ENV_TAG=TEST, EXECUTION_MODE=direct
    ├── lxc-prod/
    │   └── node-compose.yaml        # New — ENV_TAG=PROD, EXECUTION_MODE=direct
    └── lxc-staging/
        └── node-compose.yaml        # New — ENV_TAG=STAGING, EXECUTION_MODE=direct

axiom-ee/
└── test_keys/                       # Git-ignored, generated by generate_licence_key.py
    ├── signing.key                  # Ed25519 private key (PEM)
    └── verification.key             # Ed25519 public key (PEM)
```

### Structure Rationale

- **`provision_lxc_nodes.py` wraps `manage_node.py` logic** rather than modifying it. The existing skill manages one node; the new script orchestrates 4 in parallel with env-tag-specific config.
- **`generate_licence_key.py` lives in `mop_validation/scripts/`** not in the main repo. Test key generation is validation infrastructure, not product code.
- **`test_keys/` is git-ignored** in `axiom-ee`. Test private keys must never be committed. The verification key can be committed if needed for CI, but the private key cannot.
- **LXC node compose files use `EXECUTION_MODE=direct`** — same as existing scale-test nodes. Avoids Docker-in-Docker cgroup v2 issues that occur when nesting Docker inside Incus containers.

---

## Architectural Patterns

### Pattern 1: Parameterised Teardown

**What:** `teardown_fresh_install.py` accepts a `--scope` flag: `volumes-only`, `full` (default), or `certs-only`. Full scope destroys everything. Volumes-only preserves the image cache (faster for iterative testing).

**When to use:** Always run `full` before the first validation pass. Use `volumes-only` for iterative job testing where you want to preserve the built Docker images.

**Trade-offs:** Full teardown adds ~2 minutes to the setup cycle (stack rebuild + PKI re-init). Acceptable for adversarial validation — the point is to test cold-start.

### Pattern 2: Parallel LXC Provisioning

**What:** `provision_lxc_nodes.py` launches all 4 containers simultaneously using Python `concurrent.futures.ThreadPoolExecutor`. Each thread runs the Incus launch + configuration sequence for one node.

**When to use:** Always — sequential provisioning would be ~4× slower (each container takes ~30s to configure).

**Trade-offs:** Incus can handle parallel launches without issue. The only shared resource is the Incus bridge network, which is not a bottleneck for 4 containers.

### Pattern 3: Licence Key in Environment, Not File

**What:** The test licence key is passed to the agent container via `AXIOM_LICENCE_KEY` environment variable in the compose file, not mounted as a file.

**When to use:** Always — matches the production deployment pattern. The EE plugin reads the env var at startup; no file I/O needed.

**Trade-offs:** The key appears in `docker inspect` output. Acceptable for test keys — production keys should use Docker secrets. Document this explicitly.

### Pattern 4: CE-First, EE-Second Validation Order

**What:** Always validate CE completely before enabling EE. The CE pass must pass clean before the EE wheel is installed.

**When to use:** Always — this is the critical discipline. Running CE+EE tests first could mask CE bugs that are papered over by EE code.

**Trade-offs:** Requires two stack restarts (CE → teardown → EE). Acceptable overhead.

---

## Anti-Patterns

### Anti-Pattern 1: Validating Without Full Volume Teardown

**What people do:** `docker compose restart` or `docker compose down` (without `-v`) between validation runs.

**Why it's wrong:** Postgres data volume survives. The database retains previous-run state: enrolled nodes, signed jobs, EE tables from a previous EE install. CE-only validation then has EE tables present in the DB, masking the CE isolation guarantee. PKI state survives too — the Root CA is reused, so cert re-enrollment bugs are invisible.

**Do this instead:** Always `docker compose down -v` before a CE validation pass. The explicit teardown script enforces this.

### Anti-Pattern 2: Reusing the Same JOIN_TOKEN for LXC Nodes

**What people do:** Generate one JOIN_TOKEN and use it for all 4 LXC nodes.

**Why it's wrong:** JOIN_TOKEN embeds the Root CA PEM. This is safe to share. The actual uniqueness comes from the node ID (derived from the client cert CN). If the same token is used but each node generates a unique cert, enrollment works — but the PKI is not properly tested. Each node should get its own token from `GET /api/nodes/join-token` to verify the enrollment endpoint is functional per-request.

**Do this instead:** Call the enrollment token endpoint once per node. Validate the returned token is parseable and contains the current CA.

### Anti-Pattern 3: Using a Production EE Wheel for Validation

**What people do:** Install the published `axiom-ee` wheel (with the Axiom Labs public key) and generate a licence key with the Axiom Labs signing key.

**Why it's wrong:** If Axiom Labs does not provide a test signing key, the test licence cannot be verified against the production public key. More critically, the validation harness needs to control licence expiry and feature lists — which requires owning the signing key.

**Do this instead:** Always build a dev wheel with the test public key. Never use the production EE wheel in CI or local validation.

### Anti-Pattern 4: LXC Nodes Using Host Bridge IP Hardcoded as 172.17.0.1

**What people do:** Copy the `extra_hosts: host.docker.internal:172.17.0.1` pattern from the local Docker node compose files into the LXC node compose files.

**Why it's wrong:** LXC containers connect via the Incus bridge (typically `10.x.x.1` range, not `172.17.0.1`). The host's Docker bridge IP is unreachable from inside an Incus container.

**Do this instead:** Discover the host's Incus bridge IP dynamically in `provision_lxc_nodes.py` (`incus network info incusbr0 | grep inet`), or use the host's primary LAN IP. Pass it as `AGENT_URL=https://<bridge-host-ip>:8001`.

### Anti-Pattern 5: Testing EE Features Before Verifying Licence Is Loaded

**What people do:** Dispatch to EE routes immediately after stack start, before confirming `GET /api/licence` returns enterprise edition.

**Why it's wrong:** If the licence key is malformed, expired, or the public key mismatch is silent, the stack returns CE mode and all EE route tests return 402. The test suite then fails with confusing errors that look like EE router mounting failures rather than licence validation failures.

**Do this instead:** Always assert `GET /api/licence` → `{"edition": "enterprise"}` as the first check in the EE validation pass. Gate all subsequent EE tests on this assertion.

---

## Scaling Considerations

This is a validation milestone, not a scalability assessment. Relevant limits for the test environment:

| Concern | At 4 LXC Nodes | Notes |
|---------|----------------|-------|
| Incus bridge network | No issue | 4 containers trivial for bridge |
| Host memory | ~2GB for 4 LXC containers | Each Ubuntu 24.04 container ~512MB idle |
| Docker-in-LXC | Works with `security.nesting=true` | `EXECUTION_MODE=direct` avoids cgroup v2 issues |
| Concurrent jobs | 5 per node tested in matrix | `concurrency_limit` column must be set or unlimited assumed |
| Postgres connections | No issue at this scale | asyncpg pool default handles 4 nodes polling |

---

## Sources

- Direct inspection: `puppeteer/compose.server.yaml` — service topology, volume names (HIGH)
- Direct inspection: `mop_validation/local_nodes/node_alpha/node-compose.yaml` — local Docker node pattern, ENV_TAG, EXECUTION_MODE (HIGH)
- Direct inspection: `mop_validation/local_nodes/node_beta/node-compose.yaml` — ENV_TAG=TEST, confirms per-node env tag pattern (HIGH)
- Direct inspection: `mop_validation/local_nodes/node_gamma/node-compose.yaml` — Foundry-built image pattern (HIGH)
- Direct inspection: `.agent/skills/manage-test-nodes/scripts/manage_node.py` — Incus provisioning pattern: `security.nesting=true`, Ubuntu 24.04, podman/ssh/python install (HIGH)
- Direct inspection: `mop_validation/scripts/test_local_stack.py` — existing test harness structure, AGENT_URL, auth patterns (HIGH)
- Direct inspection: `.planning/milestones/v11.0-phases/37-licence-validation-docs-docker-hub/37-CONTEXT.md` — licence key wire format, `AXIOM_LICENCE_KEY`, hardcoded bytes in `.so` (HIGH)
- Direct inspection: `.planning/axiom-oss-ee-split.md` — CE/EE table split, 13 CE tables, 15 EE tables (HIGH)
- Direct inspection: `.planning/PROJECT.md` — v11.1 milestone goals, target features (HIGH)
- Direct inspection: `.planning/research/ARCHITECTURE.md` (prior version) — CE/EE plugin wiring, startup sequence, EEPlugin.register() contract (HIGH)
- Existing CLAUDE.md: node identity persistence fix (`_load_or_generate_node_id()`), EXECUTION_MODE=direct rationale (HIGH)
- CLAUDE.md: Node networking pattern: `extra_hosts: host.docker.internal:172.17.0.1`, LXC uses different bridge (HIGH — anti-pattern derived from this)

---

*Architecture research for: Axiom v11.1 Stack Validation — fresh install teardown, LXC node provisioning, EE test keypair integration, job test matrix*
*Researched: 2026-03-20*
