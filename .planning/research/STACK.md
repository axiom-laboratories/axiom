# Stack Research

**Domain:** Axiom v11.1 Stack Validation — adversarial end-to-end testing infrastructure
**Researched:** 2026-03-20
**Confidence:** HIGH (all tools verified against live system; Incus 6.22 on host confirmed; cryptography 46.0.5 confirmed; Docker 29.2.1 confirmed)

---

## Scope

This addendum covers ONLY the net-new tooling and patterns needed for v11.1 Stack Validation.
The existing validated stack (FastAPI, SQLAlchemy, React/Vite, Docker Compose, cryptography,
APScheduler, Caddy, Postgres, MkDocs Material, devpi, Cython EE plugin) is not re-researched.

The previous STACK.md entries cover v10.0 and v11.0 additions. Those remain valid.

---

## Pre-Assessment: What Already Exists

| Requirement | Current State |
|-------------|---------------|
| Incus CLI | `incus` 6.22 installed at `/usr/bin/incus`; user is in `incus-admin` group; `incus list` returns successfully |
| Single LXC node provisioning | `.agent/skills/manage-test-nodes/scripts/manage_node.py` — launches one Ubuntu 24.04 node, configures SSH + Podman + Python, injects SSH key. Functional. |
| Ed25519 key generation | `cryptography` 46.0.5 on host; `Ed25519PrivateKey.generate()` confirmed working. Pattern fully documented in phase 37 research. |
| Test signing script | `~/Development/toms_home/.agents/tools/admin_signer.py --generate` generates a signing keypair |
| Licence key generation | Pattern documented in phase 37 research: `base64url(json_payload).base64url(ed25519_sig)` wire format |
| EE public key location | `_LICENCE_PUBLIC_KEY_BYTES` module-level bytes literal in `axiom-ee/ee/plugin.py` — currently a 32-zero placeholder |
| Job concurrent test | `mop_validation/scripts/test_concurrent_job.py` — submits one job; does not cover the full matrix |
| Stack teardown | Partial — `mop_validation/scripts/test_teardown.py` targets remote Docker nodes via SSH; no clean local compose teardown script |
| Validation test runner | `mop_validation/scripts/test_local_stack.py` — linear Phase 0–7 script; not parameterised for job matrix |

**Conclusion:** All base tools are present. v11.1 work is:
1. Extend single-node Incus provisioner to 4 nodes with env tags
2. Write clean local stack teardown + fresh install script
3. Write a licence keypair generator + EE binary patcher (no Cython rebuild — monkeypatch via env or inject bytes into plugin before rebuild)
4. Write a parameterised job test matrix runner

---

## Recommended Stack — New Additions for v11.1

### Core Technologies

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| Incus CLI | 6.22 (on host) | Provision and manage LXC containers for the 4 test nodes | Already installed and working; `incus exec` / `incus file push` / `incus list --format json` are the correct CLI verbs for scripted provisioning; no new installation needed |
| `cryptography` | 46.0.5 (on host) | Generate Ed25519 test licence keypair; sign test licence payloads | Already the EE plugin's verification library; same key format; no new dependency |
| `requests` | already in `mop_validation/` | HTTP client for the job matrix runner calling the Axiom REST API | Already used by all existing test scripts |
| `python-dotenv` | already in `mop_validation/` | Load `secrets.env` in test scripts | Already used by `test_concurrent_job.py` and others |

### Supporting Libraries

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `subprocess` (stdlib) | Python stdlib | Shell out to `docker compose` and `incus` CLI from test scripts | All teardown, rebuild, and node provisioning logic; avoid `os.system()` — use `subprocess.run(..., check=True)` for error propagation |
| `time` / `datetime` (stdlib) | Python stdlib | Job timing assertions in the test matrix (fast job < 5s, slow job > 10s) | Duration validation in the job matrix runner |
| `concurrent.futures.ThreadPoolExecutor` (stdlib) | Python stdlib | Submit N concurrent jobs simultaneously in the concurrency test cases | The REST API is synchronous from the caller's perspective; threads let N jobs be submitted in parallel without async overhead |
| `json` (stdlib) | Python stdlib | Build job payloads and parse API responses | Already used throughout test scripts |
| `base64` (stdlib) | Python stdlib | Encode licence key wire format and Ed25519 signatures | Same pattern as phase 37 key generation script |

### Development Tools

| Tool | Purpose | Notes |
|------|---------|-------|
| `incus exec <node> -- <cmd>` | Run commands inside a provisioned LXC node | The correct verb for post-launch configuration; prefer over SSH for provisioning steps |
| `incus file push <local> <node>/<remote>` | Copy files into an LXC container | Use to inject node compose files, secrets, and JOIN_TOKEN |
| `incus list --format json` | Poll container state and extract IP addresses | Same pattern as existing `manage_node.py`; parse with `json.loads()` |
| `docker compose -f compose.server.yaml down -v` | Full stack teardown including volumes | `-v` removes named volumes (pgdata, certs-volume, etc.) — required for a true fresh install |
| `docker compose -f compose.server.yaml up -d --build` | Fresh stack bring-up with image rebuild | `--build` forces image rebuild so code changes are picked up |
| `docker compose -f compose.server.yaml ps` | Verify all services are healthy before running tests | Check `State: running` and health status on `db` service |

---

## Installation

No new packages need to be added to `puppeteer/requirements.txt` or `mop_validation/`.

All tooling is either:
- Already installed on the host (`incus`, `cryptography`, `docker`)
- Python stdlib (`subprocess`, `concurrent.futures`, `base64`, `json`, `time`)
- Already in `mop_validation/` (`requests`, `python-dotenv`)

```bash
# Verify prerequisites are in place (run once):
incus --version          # expect: 6.22
docker --version         # expect: 29.x
python3 -c "from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey; print('ok')"
python3 -c "import requests; print('ok')"
```

---

## Area 1: Clean Stack Teardown + Fresh Install

### What to Build

A single script at `mop_validation/scripts/fresh_install.py` (or `teardown_and_reinstall.sh`).
Use Python (not bash) for consistency with existing test scripts and to share the `load_env()` helper.

### Pattern

```
Phase 0: Teardown
  - docker compose -f compose.server.yaml down -v   # stops all containers + wipes volumes
  - docker compose -f compose.server.yaml rm -f     # remove stopped containers
  - docker volume prune -f                          # catch any orphan volumes
  - rm -f puppeteer/pki/root_ca.*                   # wipe CA so enrollment re-runs cleanly
  - rm -f puppeteer/jobs.db                         # wipe SQLite if dev mode
  - (optional) docker image rm <built images>       # force full image rebuild

Phase 1: CE-only fresh bring-up
  - docker compose -f compose.server.yaml up -d --build
  - poll /api/health until 200 (with 60s timeout)
  - assert admin login works

Phase 2: CE+EE fresh bring-up (separate run)
  - add axiom-ee wheel to agent's pip install step (or mount devpi wheel)
  - set AXIOM_LICENCE_KEY=<test licence key> in compose .env
  - docker compose -f compose.server.yaml up -d --build
  - poll /api/licence → assert edition == "enterprise"
```

### Why `-v` on `down` Matters

`docker compose down` without `-v` leaves named volumes intact (pgdata, certs-volume, mirror-data).
The next `up` reuses the old DB and old CA — this is not a fresh install. `-v` is mandatory for
true clean-slate validation.

### Pitfall: PKI Directory Permissions

The `certs-volume` mount at `/app/global_certs` in the agent container is read-only. The CA
files live in `puppeteer/pki/` on the host. After `down -v`, the Caddy cert-manager container
regenerates its own TLS certs on next start, but the Axiom Root CA is re-generated by the agent
on first startup (in `pki.py`). No manual CA cleanup is needed unless testing the case where
the CA is intentionally corrupted.

---

## Area 2: 4 LXC Nodes with Different Env Tags

### What to Build

Extend `.agent/skills/manage-test-nodes/scripts/manage_node.py` OR create a new script at
`mop_validation/scripts/provision_test_nodes.py` that provisions 4 named containers in parallel.

The existing skill creates one node (`mop-test-node`). The v11.1 requirement is 4 nodes with
distinct names and env tags:

| Container Name | Env Tag | JOIN_TOKEN Source | EXECUTION_MODE |
|---------------|---------|-------------------|----------------|
| `axiom-node-dev` | `DEV` | from `GET /api/join-token` | `direct` |
| `axiom-node-test` | `TEST` | from `GET /api/join-token` | `direct` |
| `axiom-node-prod` | `PROD` | from `GET /api/join-token` | `direct` |
| `axiom-node-staging` | `STAGING` | from `GET /api/join-token` | `direct` |

### Pattern

```python
NODES = [
    {"name": "axiom-node-dev",     "env_tag": "DEV"},
    {"name": "axiom-node-test",    "env_tag": "TEST"},
    {"name": "axiom-node-prod",    "env_tag": "PROD"},
    {"name": "axiom-node-staging", "env_tag": "STAGING"},
]
IMAGE = "images:ubuntu/24.04"
INCUS_FLAGS = "-c security.nesting=true"

# Launch all 4 in sequence (Incus launch is fast; parallel launches can race on the bridge):
for node in NODES:
    run(f"incus launch {IMAGE} {node['name']} {INCUS_FLAGS}")

# Configure each node (parallel via threads is safe for exec steps):
for node in NODES:
    configure_node(node)   # apt install, SSH key, Python deps

# Inject node compose file into each container with the correct AGENT_URL,
# ENV_TAG, and JOIN_TOKEN, then start the puppet node.py directly (or via a
# minimal node-compose.yaml inside the container).
```

### Env Tag Injection

The Axiom node declares its env tag via `OPERATOR_TAGS` env var (format: `env:DEV`).
The node.py sends this in the heartbeat; job_service.py enforces isolation.

Each container's node startup command must set:
```bash
OPERATOR_TAGS=env:DEV EXECUTION_MODE=direct python3 -m environment_service.node
```

Or pass via a minimal compose file injected with `incus file push`.

### Incus Networking to Axiom

The Axiom control plane runs in Docker on the host. Incus containers are on the default
`incusbr0` bridge (typically 10.x.x.x). The host is reachable from Incus containers at
the bridge's host-side IP.

Get the host-side Incus bridge IP:
```bash
ip addr show incusbr0 | grep 'inet ' | awk '{print $2}' | cut -d/ -f1
```

Set `AGENT_URL=https://<incusbr0_host_ip>:8001` in each node's environment.
The Axiom TLS cert must include this IP as a SAN. If Caddy was configured with
`SERVER_HOSTNAME=<host_lan_ip>`, the cert may not cover the Incus bridge IP — this
is the primary networking pitfall.

**Mitigation:** Use `--no-verify` (disable TLS verification) in the puppet node's connection
OR configure Caddy with `SERVER_HOSTNAME=` set to the Incus bridge host IP in addition to
the LAN IP. The simpler path for test nodes is to pass the Root CA PEM via `JOIN_TOKEN`
(the existing enrollment mechanism) — nodes already extract and trust the Root CA from the token.
The mTLS root CA trust is separate from the Caddy HTTPS cert trust.

Confirm: nodes talk to `https://AGENT_URL:8001` using the Root CA from JOIN_TOKEN. If Caddy
is the TLS terminator and its cert is from a different CA (ACME/Let's Encrypt), nodes will
reject it. **Use `verify=False` on the node's `requests` session for the enroll step**, or
expose port 8001 (the FastAPI agent directly) rather than routing through Caddy port 443.

The compose.server.yaml exposes `8001:8001` directly on the agent — point nodes to
`https://<host_ip>:8001` (the FastAPI self-signed cert), not to the Caddy proxy.

---

## Area 3: EE Test Keypair + Binary Patcher

### What to Build

A script at `mop_validation/scripts/generate_test_licence.py` that:
1. Generates a fresh Ed25519 keypair
2. Prints the raw 32-byte public key as a Python bytes literal (for patching `plugin.py`)
3. Signs a test licence payload and prints the `AXIOM_LICENCE_KEY` env var value

This pattern is already fully documented in phase 37 research — see `37-RESEARCH.md` code
examples. The script is a direct implementation of that pattern.

### Pattern (already verified in phase 37)

```python
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding, PrivateFormat, NoEncryption, PublicFormat
import base64, json, time

priv = Ed25519PrivateKey.generate()
pub = priv.public_key()

# 32-byte raw public key — paste into ee/plugin.py as _LICENCE_PUBLIC_KEY_BYTES
raw_pub = pub.public_bytes(Encoding.Raw, PublicFormat.Raw)
print(f"_LICENCE_PUBLIC_KEY_BYTES = {raw_pub!r}")

# Build 1-year test licence
payload = {
    "customer_id": "axiom-test",
    "exp": int(time.time()) + 365 * 86400,
    "features": ["foundry", "rbac", "webhooks", "triggers", "audit"],
}
payload_bytes = json.dumps(payload, separators=(',', ':')).encode()
sig = priv.sign(payload_bytes)

p_b64 = base64.urlsafe_b64encode(payload_bytes).rstrip(b'=').decode()
s_b64 = base64.urlsafe_b64encode(sig).rstrip(b'=').decode()
print(f"AXIOM_LICENCE_KEY={p_b64}.{s_b64}")
```

### Patching the EE Binary

The `_LICENCE_PUBLIC_KEY_BYTES` is a bytes literal in `axiom-ee/ee/plugin.py` — currently
32 zero bytes (placeholder). To test EE validation:

1. Run `generate_test_licence.py` → get the raw bytes literal + `AXIOM_LICENCE_KEY` value
2. Edit `axiom-ee/ee/plugin.py`: replace the `_LICENCE_PUBLIC_KEY_BYTES` placeholder
3. Rebuild the Cython `.so`: `pip install build && python -m build --wheel --no-sdist`
   (or use cibuildwheel for the full pipeline)
4. Re-install the wheel into the devpi index or directly: `pip install dist/axiom_ee-*.whl --force-reinstall`
5. Rebuild the Docker agent image: `docker compose -f compose.server.yaml build agent`
6. Set `AXIOM_LICENCE_KEY=<value>` in `puppeteer/.env`
7. `docker compose -f compose.server.yaml up -d --no-build agent`
8. `GET /api/licence` should return `edition: enterprise`

**Simpler path for development testing (no Cython rebuild):** Run the EE plugin in pure Python
mode (skip the `.so`) by modifying the agent's `PYTHONPATH` to point to the raw `axiom-ee/` source
directory. The `_LICENCE_PUBLIC_KEY_BYTES` can then be patched directly in the `.py` file with
no compilation step. This is valid for v11.1 validation testing — the `.so` compilation is the
production path, not required for adversarial functional testing.

---

## Area 4: Job Test Matrix Runner

### What to Build

A script at `mop_validation/scripts/job_matrix_runner.py` that submits a parameterised set
of jobs and asserts outcomes.

### Job Script Templates

Each job is a small Python script signed with the existing signing key before submission.
The test matrix covers:

| Case | Script Behaviour | Expected Outcome | Env Tag Target |
|------|-----------------|-----------------|----------------|
| fast-success | `time.sleep(1); sys.exit(0)` | COMPLETED in < 5s | DEV |
| slow-success | `time.sleep(30); sys.exit(0)` | COMPLETED in 30–45s | TEST |
| light-memory | Allocate 10MB; exit 0 | COMPLETED; memory < limit | PROD |
| heavy-memory | Allocate 400MB; exit 0 (or OOM) | COMPLETED or FAILED (memory limit enforced) | STAGING |
| concurrent-N | Submit 4 identical fast jobs simultaneously | All 4 COMPLETED; confirm on correct env | DEV |
| crash | `raise RuntimeError("deliberate crash")` | FAILED; exit code != 0 | DEV |
| bad-exit | `sys.exit(99)` | FAILED; exit code == 99 | DEV |
| bad-sig | Submit job with corrupted signature | Rejected at submission (422) or at node (refused) | any |
| expired-sig | Submit job signed with revoked/old key | Rejected at node (signature mismatch) | any |

### Signing in the Matrix Runner

All valid jobs must be signed with the operator's Ed25519 signing key (registered via
`POST /api/signatures`). The matrix runner loads `puppeteer/secrets/signing.key` (PEM),
signs `script_content.encode('utf-8')`, base64-encodes the signature, and includes it in
the job payload. This is the same pattern as `mop_validation/scripts/run_signed_job.py`.

For bad-sig and expired-sig cases, corrupt the base64 signature string or use a different
private key that is not registered.

### Concurrency Pattern

Use `concurrent.futures.ThreadPoolExecutor` to submit N jobs simultaneously:

```python
from concurrent.futures import ThreadPoolExecutor, as_completed

def submit_job(session, payload):
    resp = session.post(f"{AGENT_URL}/jobs", json=payload)
    return resp.json()

with ThreadPoolExecutor(max_workers=4) as executor:
    futures = [executor.submit(submit_job, session, payload) for _ in range(4)]
    job_ids = [f.result()["guid"] for f in as_completed(futures)]
```

### Outcome Polling

Poll `GET /jobs/{guid}` or `GET /api/executions?job_guid={guid}` until status is
`COMPLETED` or `FAILED`, with a configurable timeout (e.g. 120s for slow jobs).

### Memory Limit Testing

Submit jobs with `memory_limit` field in the payload (already supported by `JobCreate` model).
The node's `runtime.py` passes `--memory` to Docker. For `direct` mode (which LXC nodes use),
the memory limit is NOT enforced by the runtime — this is a known limitation. Verify this
behaviour explicitly in the matrix results: assert that heavy-memory jobs complete successfully
in `direct` mode (limit bypassed) versus `docker` mode (limit enforced, OOM kills).

---

## Alternatives Considered

| Recommended | Alternative | Why Not |
|-------------|-------------|---------|
| Incus LXC for 4 test nodes | 4 Docker-in-Docker containers | DinD has known cgroup v2 issues on Linux 6.x hosts (the project's own CLAUDE.md documents this for `direct` mode); Incus LXC provides a proper Linux namespace boundary without the cgroup nesting problem |
| Incus LXC for 4 test nodes | 4 separate Docker Compose node stacks on host | Pollutes the host Docker network; makes network isolation per env-tag harder to test; LXC is cleaner for node-level isolation |
| `concurrent.futures.ThreadPoolExecutor` for concurrent job submission | `asyncio.gather` | The test script is synchronous; threading is the right tool for parallel HTTP calls in a sync script; `asyncio` would require rewriting the entire test client as async |
| Cython `.so` rebuild + fresh devpi wheel for EE key swap | Monkeypatch `_LICENCE_PUBLIC_KEY_BYTES` in memory at test time | Monkeypatching the compiled `.so` is not possible at runtime; patching the `.py` source + re-running pure Python (skipping Cython) is the dev-testing path; full rebuild is the production-fidelity path |
| Python script for teardown + install | Bash script | Python scripts share the `load_env()` helper and `subprocess.run(check=True)` error handling with existing test scripts; bash scripts are harder to integrate with the assertion/reporting layer |

## What NOT to Use

| Avoid | Why | Use Instead |
|-------|-----|-------------|
| `incus launch` in parallel threads for 4 nodes | Incus bridge assignment can race when multiple containers request IPs simultaneously — launches fail silently | Launch sequentially with `for` loop; configure in parallel after all are running |
| `docker compose down` without `-v` for teardown | Named volumes (pgdata, certs-volume) survive; next bring-up is not a fresh install | `docker compose down -v` always |
| `EXECUTION_MODE=auto` or `EXECUTION_MODE=docker` for LXC nodes | LXC containers have nesting enabled but Podman/Docker-in-LXC has the same cgroup v2 issues as DinD; `direct` mode avoids the container runtime entirely | `EXECUTION_MODE=direct` on all LXC test nodes |
| Submitting jobs without signing for success-case tests | The signature verification is part of what is being validated; unsigned job submission will be rejected at the API layer | Always sign with the registered key for success cases; only corrupt signatures for negative-path tests |
| Hardcoding the Incus bridge IP | The bridge IP can differ between host configurations (`10.x.x.x` range varies) | Derive dynamically: `ip addr show incusbr0 \| grep 'inet ' \| awk '{print $2}' \| cut -d/ -f1` |
| Testing EE with the 32-zero placeholder key in `plugin.py` | `Ed25519PublicKey.from_public_bytes(b'\x00' * 32)` will construct successfully but all licence signatures will fail verify — the key is not a valid curve point | Always generate a real keypair with `Ed25519PrivateKey.generate()` before EE testing |

---

## Stack Patterns by Variant

**If testing CE-only (no EE wheel installed):**
- Bring up stack normally
- `GET /api/licence` returns `{"edition": "community"}`
- EE routes return 402 (CE stubs)
- No `AXIOM_LICENCE_KEY` env var needed

**If testing CE+EE (EE wheel installed, test key):**
- Run `generate_test_licence.py` → get `_LICENCE_PUBLIC_KEY_BYTES` and `AXIOM_LICENCE_KEY`
- Patch `axiom-ee/ee/plugin.py` with the new bytes literal
- Either rebuild `.so` (full fidelity) or run in pure Python mode (dev shortcut)
- Set `AXIOM_LICENCE_KEY=...` in `puppeteer/.env`
- Rebuild and restart agent container
- `GET /api/licence` returns `{"edition": "enterprise", ...}`

**If testing node env-tag isolation:**
- Submit a job with `env_tag: "PROD"` in the payload
- Assert it is only picked up by `axiom-node-prod` (not DEV/TEST/STAGING nodes)
- Verify via `GET /jobs/{guid}` → `node_id` matches the PROD node's registered ID

**If testing `direct` mode memory limits:**
- Set `memory_limit: "50m"` in the job payload
- In `direct` mode, the limit is not enforced — the job completes even with 400MB allocation
- This is expected behaviour; document it in the test results rather than treating as a failure
- Run the same test via a Docker node (separate node compose stack) to confirm limit IS enforced

---

## Version Compatibility

| Package | Version on Host | Notes for v11.1 |
|---------|-----------------|-----------------|
| Incus | 6.22 | `incus exec <node> -- env ...` runs commands as root inside the container; `security.nesting=true` required for running containered workloads inside LXC |
| cryptography | 46.0.5 | `Ed25519PrivateKey.generate()` + `.sign(bytes)` → 64-byte signature; `Ed25519PublicKey.from_public_bytes(32_bytes).verify(sig, data)` — 2-arg call, sig first |
| Docker | 29.2.1 | `docker compose down -v` behaviour confirmed; `--build` flag forces image rebuild |
| Python (host) | 3.x (host system) | `concurrent.futures.ThreadPoolExecutor` is stdlib; no additional install |

---

## Sources

- Local host verification: `incus --version` → 6.22; `incus list` → clean (HIGH confidence)
- Local host verification: `python3 -c "from cryptography...Ed25519PrivateKey..."` → confirmed working with v46.0.5 (HIGH confidence)
- Local host verification: `docker --version` → 29.2.1 (HIGH confidence)
- `.agent/skills/manage-test-nodes/scripts/manage_node.py` — reviewed directly; existing single-node provisioner pattern (HIGH confidence)
- `mop_validation/scripts/test_concurrent_job.py` — reviewed directly; signing pattern, job submission structure (HIGH confidence)
- `mop_validation/scripts/test_local_stack.py` — reviewed directly; stack bring-up structure, path conventions (HIGH confidence)
- `.planning/milestones/v11.0-phases/37-licence-validation-docs-docker-hub/37-RESEARCH.md` — Ed25519 licence key generation pattern, wire format, verify call order (HIGH confidence — locally verified in phase 37)
- `puppeteer/compose.server.yaml` — reviewed directly; service names, volume names, port exposures (HIGH confidence)
- CLAUDE.md `Known Deferred Issues` — `direct` mode is correct for DinD / LXC nodes; memory limits not enforced in direct mode (HIGH confidence — documented project constraint)

---

*Stack research for: Axiom v11.1 — Stack Validation (teardown, LXC nodes, EE test key, job matrix)*
*Researched: 2026-03-20*
