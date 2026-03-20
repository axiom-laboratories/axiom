# Phase 40: LXC Node Provisioning - Research

**Researched:** 2026-03-20
**Domain:** Incus LXC provisioning, Docker-in-LXC, mTLS node enrollment, revoke/re-enroll lifecycle
**Confidence:** HIGH

## Summary

Phase 40 provisions four Incus LXC containers as simulated remote machines, each running the node agent inside Docker with `EXECUTION_MODE=docker`. The goal is to exercise the actual deployment path an operator would use on a real remote server, not a shortcut. Each container gets its own unique JOIN_TOKEN (pre-generated before the provisioning loop), pulls the node image from the local registry at the `incusbr0` bridge IP, and enrolls via mTLS.

The existing codebase has all necessary building blocks: the `test_installer_lxc.py` script demonstrates the Incus lifecycle patterns (launch, IP discovery, Docker install, file push, exec), `verify_ce_install.py` establishes the `[PASS]`/`[FAIL]` output convention used by the verifier, and the `node_alpha/node-compose.yaml` establishes the correct bridge-mode Docker compose structure. The `mop_validation/secrets/ee/` directory pattern establishes how per-phase secrets are stored.

The one non-obvious complexity is NODE-05 (revoke/re-enroll): the `/api/enroll` endpoint explicitly blocks re-enrollment of REVOKED nodes (HTTP 403). Re-enrollment therefore requires calling `POST /nodes/{node_id}/reinstate` first (flips status to OFFLINE), then providing a fresh JOIN_TOKEN. The new cert serial will differ from the original, which is the proof of a clean PKI re-enrollment.

**Primary recommendation:** Build `provision_lxc_nodes.py` as an idempotent loop over a statically-declared node config table, reusing the `test_installer_lxc.py` Incus helper patterns at scale.

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Node agent runtime**
- LXC containers simulate real remote machines — the purpose is to test the actual deployment path
- Each LXC container runs Docker inside it (`security.nesting=true`)
- Node agent runs via `docker compose up` inside each LXC (not as a direct Python process)
- `EXECUTION_MODE=docker` — jobs run as Docker containers via the LXC's Docker socket (mounted into the node container). `direct` mode is NOT acceptable
- Node container runs `privileged: true` with the Docker socket mounted from the LXC host

**Node image delivery**
- Node image built on host, pushed to `registry:5000` in `compose.server.yaml`
- Inside each LXC, Docker pulls from the host's registry IP (the `incusbr0` bridge IP, dynamically discovered)
- Registry address injected into the compose file pushed to each LXC (not hardcoded)

**Compose file for LXC nodes**
- Dedicated `mop_validation/local_nodes/lxc-node-compose.yaml` (NOT `puppets/node-compose.yaml`)
- Network: bridge mode (no `puppeteer_default` external network)
- `extra_hosts: host.docker.internal:host-gateway`
- `EXECUTION_MODE=docker` pre-set
- Image references local registry: `<incusbr0-ip>:5000/puppet-node:latest`
- Per-node env vars via `.env` file pushed alongside compose

**Script structure**
- `provision_lxc_nodes.py` in `mop_validation/scripts/` — idempotent single orchestrator
  - Pre-generates all 4 JOIN_TOKENs at start (fails fast if stack not up)
  - Loops sequentially: launch LXC → wait for IP → install Docker → push compose + .env → pull image → `docker compose up`
  - Idempotent: if node already RUNNING, skip launch/install, only re-deploy compose stack
  - PASS/FAIL per step output
- `verify_lxc_nodes.py` in `mop_validation/scripts/` — separate verifier
  - NODE-01 through NODE-05 with `[PASS]`/`[FAIL]` per requirement ID
  - NODE-05 fully automated (no manual steps)

**Token generation and storage**
- All 4 tokens generated upfront via `POST /admin/generate-token`
- Tokens written to `mop_validation/secrets/nodes/` — one file per node: `axiom-node-dev.env`, `axiom-node-test.env`, `axiom-node-prod.env`, `axiom-node-staging.env`
- Each file: `JOIN_TOKEN=...`, `ENV_TAG=DEV/TEST/PROD/STAGING`, `AGENT_URL=https://<incusbr0-ip>:8001`
- `teardown_hard.sh` should clear `mop_validation/secrets/nodes/`

**AGENT_URL — incusbr0 bridge IP**
- Discovered dynamically: `ip -json addr show incusbr0` or `incus network info incusbr0`
- Not hardcoded as `172.17.0.1` (that is the Docker bridge, not the Incus bridge)
- Current value: `10.200.105.1` (but must be discovered at runtime, not hardcoded)

**Revoke/re-enroll test (NODE-05)**
- Fully automated in `verify_lxc_nodes.py`
- Uses `axiom-node-dev`
- Flow: record original cert serial → `POST /nodes/{id}/revoke` → poll `/work/pull` to confirm 403 → call `POST /nodes/{id}/reinstate` → `POST /admin/generate-token` for fresh token → restart node container with new JOIN_TOKEN → poll until HEALTHY → assert new cert serial differs

### Claude's Discretion
- Docker installation commands inside LXC (apt-get vs convenience script)
- Retry/backoff logic for LXC IP acquisition and Docker readiness
- `incus file push` vs `incus exec` for file transfer
- Whether to use `docker compose` v2 (plugin) or `docker-compose` v1 inside LXC — prefer v2 if available

### Deferred Ideas (OUT OF SCOPE)

None — discussion stayed within phase scope.
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| NODE-01 | 4 Incus LXC containers provisioned (`axiom-node-dev`, `axiom-node-test`, `axiom-node-prod`, `axiom-node-staging`), each with correct `OPERATOR_TAGS=env:DEV/TEST/PROD/STAGING` | Node.py reads `NODE_TAGS` env var; tags sent in heartbeat payload; `OPERATOR_TAGS` env var maps to `NODE_TAGS` in compose |
| NODE-02 | Each node enrolled using unique per-node JOIN_TOKEN — all 4 complete mTLS enrollment | `POST /admin/generate-token` returns base64 `{"t": token, "ca": pem}`; token is immediately marked `used=True` at enrollment; one token per node prevents collision |
| NODE-03 | All 4 nodes heartbeating; `GET /api/nodes` shows 4 nodes with correct `env_tag` and `HEALTHY` status | `ENV_TAG` env var read by node.py at heartbeat; `GET /nodes` returns `env_tag` field from DB; status becomes HEALTHY after successful heartbeats |
| NODE-04 | LXC nodes use `incusbr0` bridge IP for `AGENT_URL` — dynamically discovered, not hardcoded | `ip -json addr show incusbr0` returns `10.200.105.1` (current); same IP used for registry address; both injected via `.env` file at provision time |
| NODE-05 | Node revoke → re-enroll cycle: revoke node, confirm 403 on `/work/pull`, re-enroll with fresh token, confirm HEALTHY heartbeat | `POST /nodes/{id}/revoke` sets status=REVOKED + adds to CRL; `/work/pull` checks status and raises 403; `POST /nodes/{id}/reinstate` required before re-enroll (enroll endpoint blocks REVOKED nodes); new cert serial verifies PKI path |
</phase_requirements>

---

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| incus | system | LXC container orchestration | Established in project, used by manage_node.py and teardown_hard.sh |
| docker (inside LXC) | latest stable via apt | Container runtime inside LXC for running node agent | Matches production deployment model; `docker compose` v2 plugin |
| requests | project dep | HTTP calls to orchestrator API | Already used by all mop_validation scripts |
| subprocess | stdlib | Incus command execution | Established pattern from test_installer_lxc.py |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| json | stdlib | Incus `--format json` parsing | IP discovery, container status checks |
| time | stdlib | Retry loops with sleep | LXC IP acquisition, Docker readiness, heartbeat polling |
| pathlib | stdlib | Secrets file I/O | Writing node `.env` files to `secrets/nodes/` |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `ip -json addr show incusbr0` | `incus network info incusbr0` | Both valid; json addr is simpler Python parsing, incus network info is more explicit |
| `incus file push` | temp file + `incus exec bash -c 'cat > file'` | `incus file push` is cleaner for binary-safe transfers; exec cat works for small text files |
| Docker apt convenience script | `apt-get install docker.io` | Convenience script installs newer Docker CE; `docker.io` installs older stable version from Ubuntu repos. Prefer convenience script for v2 compose plugin. |

**Installation:** No new Python dependencies — `requests` already available in mop_validation environment.

---

## Architecture Patterns

### Recommended Project Structure

New files for this phase:
```
mop_validation/
├── scripts/
│   ├── provision_lxc_nodes.py      # Orchestrator (new)
│   └── verify_lxc_nodes.py         # Verifier (new)
├── local_nodes/
│   └── lxc-node-compose.yaml       # LXC-specific compose template (new)
└── secrets/
    └── nodes/                       # New subdirectory (parallels secrets/ee/)
        ├── axiom-node-dev.env
        ├── axiom-node-test.env
        ├── axiom-node-prod.env
        └── axiom-node-staging.env
```

Also modify:
```
mop_validation/scripts/teardown_hard.sh  # Add secrets/nodes/ cleanup
```

### Pattern 1: Node Configuration Table

**What:** Declare all 4 nodes as a static list of dicts at the top of `provision_lxc_nodes.py`. Loop over this table for all provisioning steps.

**When to use:** Eliminates per-node conditional logic; makes adding a 5th node trivial.

```python
# Source: derived from CONTEXT.md decisions
NODE_CONFIGS = [
    {"name": "axiom-node-dev",     "env_tag": "DEV",     "tags": "env:DEV"},
    {"name": "axiom-node-test",    "env_tag": "TEST",    "tags": "env:TEST"},
    {"name": "axiom-node-prod",    "env_tag": "PROD",    "tags": "env:PROD"},
    {"name": "axiom-node-staging", "env_tag": "STAGING", "tags": "env:STAGING"},
]
```

### Pattern 2: incusbr0 IP Discovery

**What:** Discover the Incus bridge IP dynamically at script start; use it for both `AGENT_URL` and registry address.

**When to use:** Always — never hardcode `172.17.0.1` (Docker bridge) or `10.200.105.1` (current Incus bridge, may change).

```python
# Source: verified with `ip -json addr show incusbr0` on this machine
import json, subprocess

def get_incusbr0_ip() -> str:
    result = subprocess.run(
        ["ip", "-json", "addr", "show", "incusbr0"],
        capture_output=True, text=True, check=True
    )
    data = json.loads(result.stdout)
    for addr_info in data[0]["addr_info"]:
        if addr_info["family"] == "inet":
            return addr_info["local"]
    raise RuntimeError("No IPv4 address on incusbr0")
```

### Pattern 3: Idempotent LXC Launch

**What:** Check `incus list --format json` before launching; if the node already exists and is RUNNING, skip launch and Docker install.

**When to use:** Provisioning 4 nodes with Docker install takes several minutes. Idempotency lets the operator re-run after a failure without starting over.

```python
# Source: derived from test_installer_lxc.py and teardown_hard.sh patterns
def is_container_running(name: str) -> bool:
    result = subprocess.run(
        ["incus", "list", name, "--format", "json"],
        capture_output=True, text=True
    )
    data = json.loads(result.stdout)
    return bool(data) and data[0]["status"] == "Running"
```

### Pattern 4: Docker Installation Inside LXC

**What:** Install Docker CE with the official convenience script; configure insecure registry for local pull.

**When to use:** Always for LXC nodes that need Docker v2 compose plugin.

```bash
# Inside LXC via incus exec <name> -- bash -c '...'
curl -fsSL https://get.docker.com | sh
# Configure insecure registry for local pull
mkdir -p /etc/docker
echo '{"insecure-registries":["<incusbr0-ip>:5000"]}' > /etc/docker/daemon.json
systemctl restart docker
```

Alternative (apt-get, faster but older Docker):
```bash
apt-get install -y docker.io docker-compose-plugin
```

**Recommendation:** Use `apt-get install docker.io docker-compose-plugin` for speed and reliability inside LXC. The convenience script fetches from the internet and takes longer; apt-get uses local Ubuntu mirrors. Either way, insecure registry config is required.

### Pattern 5: lxc-node-compose.yaml Structure

**What:** The compose file pushed to each LXC node. Key differences from `puppets/node-compose.yaml`: bridge network (no `puppeteer_default`), `extra_hosts: host.docker.internal:host-gateway`, `EXECUTION_MODE=docker`, image from local registry.

```yaml
# Source: node_alpha/node-compose.yaml adapted for LXC
services:
  node:
    image: <REGISTRY_IP>:5000/puppet-node:latest
    container_name: puppet-node
    restart: unless-stopped
    privileged: true
    extra_hosts:
      - "host.docker.internal:host-gateway"
    environment:
      - AGENT_URL=${AGENT_URL}
      - JOIN_TOKEN=${JOIN_TOKEN}
      - ENV_TAG=${ENV_TAG}
      - NODE_TAGS=${NODE_TAGS}
      - EXECUTION_MODE=docker
      - VERIFY_SSL=false
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock
      - node_secrets:/app/secrets
volumes:
  node_secrets:
```

Note: `<REGISTRY_IP>` is baked into the compose template (not an env var) because Docker's compose `image:` field does not support env var substitution for the registry prefix in all versions.

### Pattern 6: NODE-05 Revoke/Re-Enroll Flow

**What:** The re-enroll sequence requires `reinstate` before `enroll` because the `/api/enroll` endpoint explicitly rejects REVOKED nodes.

**Critical sequence:**
1. Record original cert serial via `GET /nodes` → find node → note `node_id`
2. `POST /nodes/{node_id}/revoke` → node status = REVOKED
3. Poll `POST /work/pull` (with node's mTLS cert) → confirm HTTP 403
4. `POST /nodes/{node_id}/reinstate` → node status = OFFLINE (re-enroll unblocked)
5. `POST /admin/generate-token` → fresh JOIN_TOKEN
6. Stop node Docker container on LXC; update `.env` with new JOIN_TOKEN; `docker compose up`
7. Poll `GET /api/nodes` until node appears with HEALTHY status
8. Assert new cert serial != original cert serial

```python
# Source: main.py line 1277-1278 (REVOKED re-enroll block) and line 1221-1232 (reinstate)
# POST /nodes/{node_id}/reinstate  — required before re-enroll
resp = requests.post(
    f"{AGENT_URL}/nodes/{node_id}/reinstate",
    headers={"Authorization": f"Bearer {jwt}"},
    verify=False,
)
assert resp.status_code == 200
```

### Anti-Patterns to Avoid

- **Shared JOIN_TOKEN across nodes:** Token is marked `used=True` immediately at first enrollment. Second node will get HTTP 403 "Invalid or Expired Enrollment Token".
- **Using `EXECUTION_MODE=direct`:** node.py raises `RuntimeError` at startup if `direct` is set. The check is at module level so the container will crash-loop.
- **Hardcoding `172.17.0.1` as `AGENT_URL`:** That is the Docker bridge IP. From inside an LXC container, it reaches the Docker host, not the orchestrator. Use the `incusbr0` IP (`10.200.105.1` currently, but always discover dynamically).
- **Using `puppeteer_default` network:** That network exists inside the puppeteer Docker compose stack. Inside LXC's independent Docker daemon, it does not exist. Use bridge mode + `extra_hosts`.
- **Attempting re-enroll without `reinstate`:** The `/api/enroll` endpoint at line 1277-1278 returns HTTP 403 for REVOKED nodes. Must call `reinstate` first.
- **Using `docker-compose` v1 (standalone binary):** Ubuntu 24.04 uses `docker compose` v2 plugin. Use `docker compose` (space, not hyphen).

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| LXC IP extraction | Custom regex over `incus list` text output | `incus list <name> --format json` + Python json.loads | JSON parsing is reliable; text format changes between Incus versions |
| Token generation | Generating tokens locally | `POST /admin/generate-token` | Token must be stored in DB; local generation bypasses the PKI CA embedding |
| Docker readiness check | Parsing docker version output | `docker info` exit code 0 = ready | Docker info fails until daemon is fully up; simpler than version string parsing |
| Cert serial extraction | Custom PEM parsing | `GET /api/nodes` returns node data (serial not directly exposed) or use Python cryptography lib | API is the right layer; local cert parsing is fragile |

**Key insight:** The orchestrator API (`/admin/generate-token`, `/nodes/{id}/revoke`, `/nodes/{id}/reinstate`) is the correct integration point for all token and node lifecycle operations. Never bypass it with direct DB manipulation.

---

## Common Pitfalls

### Pitfall 1: REVOKED Node Cannot Re-Enroll Without Reinstate

**What goes wrong:** `provision_lxc_nodes.py` restarts the node container with a fresh JOIN_TOKEN after revoke; the container calls `/api/enroll`; the server returns HTTP 403 "Node has been revoked and cannot re-enroll" because status is still REVOKED.

**Why it happens:** `main.py` line 1276-1278 checks `node.status == "REVOKED"` during enrollment and raises 403.

**How to avoid:** Call `POST /nodes/{node_id}/reinstate` before issuing the fresh token and restarting the container.

**Warning signs:** Node container logs show enrollment 403; node stays OFFLINE in dashboard after restart.

### Pitfall 2: LXC Docker Cannot Pull from localhost:5000

**What goes wrong:** Inside LXC, `docker pull localhost:5000/puppet-node:latest` fails because `localhost` inside LXC refers to the LXC's own loopback, not the host.

**Why it happens:** The local registry is on the host, accessible at the `incusbr0` bridge IP, not `localhost`.

**How to avoid:** Use `<incusbr0-ip>:5000/puppet-node:latest` as the image reference. Ensure `/etc/docker/daemon.json` inside LXC includes `{"insecure-registries":["<incusbr0-ip>:5000"]}` because the registry is HTTP-only.

**Warning signs:** `docker pull` inside LXC hangs or fails with "no such host" or TLS errors.

### Pitfall 3: EXECUTION_MODE=direct Causes Crash-Loop

**What goes wrong:** Node container exits immediately with RuntimeError; Docker restart policy causes endless crash-loop.

**Why it happens:** `node.py` line 52-59 calls `_check_execution_mode()` at module level, which raises RuntimeError if `EXECUTION_MODE=direct`.

**How to avoid:** Set `EXECUTION_MODE=docker` in the compose `.env` file. Never use `direct` in LXC.

**Warning signs:** `docker compose logs node` shows RuntimeError on startup; node never appears in `GET /api/nodes`.

### Pitfall 4: Token Race on Re-Run

**What goes wrong:** Re-running `provision_lxc_nodes.py` after partial failure re-generates tokens, but the `.env` files on disk are stale from the first run.

**Why it happens:** If the provisioner exits after generating tokens but before writing `.env` files, tokens are in the DB as `used=False` but will be consumed on the next container start with the wrong (old) `.env` file.

**How to avoid:** Write token `.env` files to `mop_validation/secrets/nodes/` before starting any container. On re-run, if a valid `.env` file already exists for a node, skip token generation and reuse the existing file.

**Warning signs:** Node enrollment fails with "Invalid or Expired Enrollment Token"; check if `.env` file token matches what was generated.

### Pitfall 5: Node Identity Reuse After Cert Volume Deletion

**What goes wrong:** Hard teardown deletes `/home/ubuntu/secrets/` inside each LXC. On re-provisioning, the node generates a new `node-<id>` identity, but the old identity remains in the orchestrator DB with REVOKED status. If the same hostname is reused, enrollment is blocked.

**Why it happens:** `node.py` derives `NODE_ID` from scanning `secrets/*.crt` files. After teardown, no cert exists, so a new random ID is generated. The new ID is not revoked, so enrollment succeeds. This is actually the correct behavior — no pitfall if teardown also clears the orchestrator DB (which hard teardown does via `docker compose down -v`).

**How to avoid:** Always run hard teardown (which removes the Postgres volume) before re-provisioning from scratch. Soft teardown + re-provision is the idempotent path and does not require node DB cleanup.

**Warning signs:** Enrollment 403 for a node that was previously revoked but not DB-cleared.

---

## Code Examples

### Incus IP Discovery (from existing node)
```python
# Source: manage_node.py pattern, adapted
import json, subprocess

def get_node_ip(container_name: str) -> str | None:
    result = subprocess.run(
        ["incus", "list", container_name, "--format", "json"],
        capture_output=True, text=True
    )
    data = json.loads(result.stdout)
    if not data:
        return None
    networks = data[0].get("state", {}).get("network", {})
    for net in networks.values():
        for addr in net.get("addresses", []):
            if addr.get("family") == "inet" and addr.get("scope") == "global":
                return addr.get("address")
    return None
```

### Token Generation
```python
# Source: main.py line 1315-1332; test_installer_lxc.py api_generate_token()
def api_generate_token(base_url: str, jwt: str) -> str:
    """POST /admin/generate-token → base64 JOIN_TOKEN string."""
    resp = requests.post(
        f"{base_url}/admin/generate-token",
        headers={"Authorization": f"Bearer {jwt}"},
        verify=False,
        timeout=15,
    )
    resp.raise_for_status()
    return resp.json()["token"]
```

### PASS/FAIL Check Pattern
```python
# Source: verify_ce_install.py check() function
def check(req_id: str, name: str, passed: bool, detail: str = "") -> bool:
    status = "[PASS]" if passed else "[FAIL]"
    detail_str = f" — {detail}" if detail else ""
    print(f"{status} {req_id}: {name}{detail_str}")
    return passed
```

### Revoke + Reinstate for NODE-05
```python
# Source: main.py lines 1183-1232
def revoke_node(base_url: str, jwt: str, node_id: str) -> None:
    resp = requests.post(
        f"{base_url}/nodes/{node_id}/revoke",
        headers={"Authorization": f"Bearer {jwt}"},
        verify=False, timeout=15,
    )
    resp.raise_for_status()

def reinstate_node(base_url: str, jwt: str, node_id: str) -> None:
    resp = requests.post(
        f"{base_url}/nodes/{node_id}/reinstate",
        headers={"Authorization": f"Bearer {jwt}"},
        verify=False, timeout=15,
    )
    resp.raise_for_status()
```

### Load env file helper (consistent with existing scripts)
```python
# Source: verify_ce_install.py load_env() pattern
from pathlib import Path

def load_env(path: Path) -> dict:
    env = {}
    if path.exists():
        for line in path.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, _, v = line.partition("=")
                env[k.strip()] = v.strip()
    return env
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `EXECUTION_MODE=direct` in LXC tests | `EXECUTION_MODE=docker` required | Sprint 10 (node.py raises RuntimeError for direct) | Compose files for LXC must specify `docker` explicitly |
| Shared JOIN_TOKEN across nodes | Unique JOIN_TOKEN per node | Phase 40 decision | Pre-generate all tokens before provisioning loop |
| Docker `172.17.0.1` for AGENT_URL | `incusbr0` IP (10.200.105.1) | Phase 40 decision | Must discover dynamically at script start |
| `node-compose.yaml` with `puppeteer_default` network | `lxc-node-compose.yaml` with bridge mode | Phase 40 decision | Separate compose template for LXC deployment |

**Deprecated/outdated:**
- `EXECUTION_MODE=direct`: Raises RuntimeError at node startup (node.py line 52-59). Never use in LXC.
- `puppeteer_default` network in LXC compose: Does not exist inside LXC's Docker daemon. Use bridge mode.
- `localhost/master-of-puppets-node:latest` as image in LXC: `localhost` is the LXC's loopback. Use `<incusbr0-ip>:5000/puppet-node:latest`.

---

## Open Questions

1. **Docker installation method inside LXC**
   - What we know: Both `apt-get install docker.io docker-compose-plugin` and the convenience script work in Ubuntu 24.04 LXC with `security.nesting=true`
   - What's unclear: Convenience script may take 60-90s (network fetch); apt-get is faster but may install an older Docker version without compose v2 plugin
   - Recommendation: Use `apt-get install -y docker.io docker-compose-plugin` — Docker v2 compose plugin is available in Ubuntu 24.04 repos and apt-get is faster and more reliable in CI-like environments

2. **Cert serial assertion in NODE-05**
   - What we know: `GET /api/nodes` returns node records but the cert serial is not directly exposed in `NodeResponse`
   - What's unclear: Whether the verifier can retrieve the cert serial from the API or must parse the PEM cert stored somewhere
   - Recommendation: Use the Python `cryptography` library to parse the cert PEM that node.py writes to `secrets/{NODE_ID}.crt` inside the container — accessible via `incus exec <name> -- cat /path/to/cert` — and extract the serial number from the X.509 cert. Alternatively, verify that enrollment produced a NEW node entry (different `node_id` if the container was fully reset) or compare the `client_cert_pem` content from a debug endpoint.

3. **Registry image name: `puppet-node` vs `master-of-puppets-node`**
   - What we know: Local registry at `localhost:5000` has tag `puppet-node:latest` (confirmed via registry catalog). Host Docker has `localhost/master-of-puppets-node:latest`.
   - What's unclear: Which image was last pushed to the registry and whether it is current
   - Recommendation: The provisioner must explicitly push the current host image to the registry before starting the provisioning loop: `docker tag localhost/master-of-puppets-node:latest localhost:5000/puppet-node:latest && docker push localhost:5000/puppet-node:latest`

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | verify_lxc_nodes.py (custom, matching verify_ce_install.py / verify_ee_install.py pattern) |
| Config file | none — standalone script |
| Quick run command | `python3 ~/Development/mop_validation/scripts/verify_lxc_nodes.py` |
| Full suite command | same — single script covers all 5 NODE-xx requirements |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| NODE-01 | 4 LXC containers running with correct OPERATOR_TAGS | integration | `python3 .../verify_lxc_nodes.py` | ❌ Wave 0 |
| NODE-02 | Each node enrolled with unique JOIN_TOKEN via mTLS | integration | `python3 .../verify_lxc_nodes.py` | ❌ Wave 0 |
| NODE-03 | All 4 nodes heartbeating, HEALTHY in `GET /api/nodes` | integration | `python3 .../verify_lxc_nodes.py` | ❌ Wave 0 |
| NODE-04 | `AGENT_URL` uses `incusbr0` IP, not `172.17.0.1` | integration | `python3 .../verify_lxc_nodes.py` | ❌ Wave 0 |
| NODE-05 | Revoke → 403 → reinstate → re-enroll → HEALTHY | integration | `python3 .../verify_lxc_nodes.py` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** Not applicable — no unit tests; integration tests require running stack
- **Per wave merge:** `python3 ~/Development/mop_validation/scripts/verify_lxc_nodes.py`
- **Phase gate:** All 5 `[PASS]` lines before marking phase complete

### Wave 0 Gaps
- [ ] `mop_validation/scripts/provision_lxc_nodes.py` — Wave 1 deliverable
- [ ] `mop_validation/scripts/verify_lxc_nodes.py` — Wave 1 deliverable (covers NODE-01 through NODE-05)
- [ ] `mop_validation/local_nodes/lxc-node-compose.yaml` — Wave 1 deliverable
- [ ] `mop_validation/secrets/nodes/` directory — created by provisioner at runtime
- [ ] `teardown_hard.sh` update — add `secrets/nodes/` cleanup

---

## Sources

### Primary (HIGH confidence)
- `puppeteer/agent_service/main.py` lines 1252-1332, 1071-1085, 1183-1232 — enrollment, work/pull, revoke/reinstate endpoints verified directly
- `puppets/environment_service/node.py` lines 52-62, 64-91, 295-320 — EXECUTION_MODE check, AGENT_URL, ENV_TAG/NODE_TAGS verified directly
- `mop_validation/scripts/test_installer_lxc.py` — Incus lifecycle patterns (launch, IP discovery, exec, file push) verified directly
- `mop_validation/scripts/verify_ce_install.py` — PASS/FAIL output convention verified directly
- `mop_validation/local_nodes/node_alpha/node-compose.yaml` — bridge-mode compose structure verified directly
- `puppeteer/compose.server.yaml` lines 153-159 — registry service at port 5000 verified directly

### Secondary (MEDIUM confidence)
- `ip -json addr show incusbr0` output — current `incusbr0` IP is `10.200.105.1`, `incus network info incusbr0` confirms same
- Docker registry catalog confirms `puppet-node:latest` tag exists at `localhost:5000`

### Tertiary (LOW confidence)
- Docker installation method (`apt-get` vs convenience script) — not verified against Ubuntu 24.04 LXC timing; recommendation based on common patterns

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all libraries are already in use in this project
- Architecture: HIGH — all patterns verified against existing code in test_installer_lxc.py, teardown_hard.sh, node_alpha/node-compose.yaml
- Pitfalls: HIGH — REVOKED re-enroll block verified in main.py source; EXECUTION_MODE=direct crash verified in node.py source; localhost registry issue verified by network topology

**Research date:** 2026-03-20
**Valid until:** 2026-04-20 (stable stack; unlikely to change within milestone)
