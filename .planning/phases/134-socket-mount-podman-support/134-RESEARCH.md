# Phase 134: Socket Mount & Podman Support - Research

**Researched:** 2026-04-12
**Domain:** Container security hardening, runtime detection, networking isolation
**Confidence:** HIGH

## Summary

Phase 134 removes the `privileged: true` security posture from node containers and replaces it with a targeted socket mount strategy. The node container will mount the host's Docker or Podman socket (depending on what's available), allowing job execution without requiring full privileged mode. This is a critical security hardening measure (CONT-02 requirement) that reduces the attack surface while maintaining full functionality.

The phase involves three parallel streams: (1) updating `node-compose.yaml` to remove `privileged: true`, mount the socket, and apply capability restrictions consistent with Phase 133 patterns; (2) enhancing `runtime.py`'s `detect_runtime()` function to probe for Podman socket in addition to Docker socket; (3) shipping `node-compose.podman.yaml` as a variant for Podman-only deployments using rootless Podman with `userns_mode: keep-id`.

Network isolation is a secondary hardening goal: replacing the hard-coded `--network=host` flag in job containers with a dedicated `jobs_network` bridge network. This prevents job containers from reaching the orchestrator network (`puppeteer_default`) or the host network, limiting blast radius if a job is compromised.

**Primary recommendation:** Implement socket detection in `detect_runtime()` with socket-first probing order, update both compose files in parallel, and wire the `jobs_network` parameter through `node.py` → `runtime.py` systematically.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

1. **Socket Access for appuser**
   - Use `group_add: [999]` in `node-compose.yaml` — GID 999 is the docker group default on most distros
   - Add inline comment: "GID 999 is the docker group default — verify on your host with: `getent group docker`"
   - Apply `cap_drop: ALL` + `security_opt: no-new-privileges` consistent with Phase 133 pattern
   - Set `DOCKER_HOST=unix:///var/run/docker.sock` explicitly in compose env vars

2. **Podman Socket Detection Order (runtime.py)**
   - Socket-first detection order in `detect_runtime()`:
     1. `/var/run/docker.sock` present → return `"docker"`
     2. `/run/podman/podman.sock` present → return `"podman"`
     3. `podman` binary in PATH → return `"podman"`
     4. `docker` binary in PATH → return `"docker"`
     5. Raise `RuntimeError`
   - When Podman socket detected, return `"podman"` (uses existing Podman code path in `run()`)

3. **Podman Compose Variant (node-compose.podman.yaml)**
   - Pure Docker Compose syntax — no Podman-specific labels
   - Key differences:
     - Mounts `${PODMAN_SOCK:-/run/user/1000/podman/podman.sock}` from host → `/run/podman/podman.sock` inside container (fixed internal path)
     - Sets `EXECUTION_MODE=podman` (overrides auto-detect)
     - Sets `userns_mode: keep-id` (UID 1000 inside container maps to host user running rootless Podman — socket ownership works without group_add)
     - No `group_add` needed (rootless Podman socket is owned by the host user)
   - Add comment: "Requires `systemctl --user enable podman.socket` on host"
   - Targets rootless Podman deployments

4. **Job Container Networking**
   - Replace hard-coded `--network=host` in `runtime.py` with `--network=jobs_network`
   - `jobs_network` is a Docker bridge network defined in compose and joined by the node container
   - Node container joins both `puppeteer_default` (orchestrator access) and `jobs_network` (job isolation)
   - Sidecar keeps `network_mode: service:node` — shares node's network namespace, reachable by job containers via node's IP on `jobs_network`
   - Job containers can reach: node + sidecar (via `jobs_network`)
   - Job containers cannot reach: puppeteer agent, host network, `puppeteer_default`
   - `network_ref` parameter in `runtime.py run()` should be wired up to pass `jobs_network` from `node.py`

### Claude's Discretion

- Exact `jobs_network` definition in compose (external vs compose-managed)
- Whether `node.py` passes the network name via env var or hardcodes `jobs_network`
- Any additional runtime.py cleanup around the old `--network=host` logic

### Deferred Ideas

None — discussion stayed within phase scope.

</user_constraints>

<phase_requirements>

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| CONT-02 | Node removes `privileged: true` and uses host Docker/Podman socket mount instead | Socket mount strategy with group_add approach, capability restrictions from Phase 133 pattern, explicit DOCKER_HOST env var |
| CONT-09 | `node-compose.podman.yaml` variant ships alongside `node-compose.yaml` for Podman host deployments | Podman compose variant design with rootless Podman support, userns_mode: keep-id, PODMAN_SOCK env var override |
| CONT-10 | `runtime.py` auto-detects Podman socket path (`/run/podman/podman.sock`) in addition to Docker | Socket-first detection order in detect_runtime(), follows existing Podman code path in run() |

</phase_requirements>

## Standard Stack

### Core Libraries & Tools

| Component | Current Version/Path | Purpose | Why Standard |
|-----------|--------|---------|--------------|
| Python | 3.12 (slim base) | Node runtime | Already deployed in Containerfile.node; async/subprocess handling in runtime.py |
| Docker CLI | Latest from `docker:cli` multi-stage | Job execution | Statically linked binary, avoids apt repo issues on Debian 13+ |
| Podman | System package (apt) | Alternative runtime | Already installed in Containerfile.node; enables rootless Podman support |
| Python asyncio | stdlib | Async subprocess execution | Used in `runtime.py` for job container spawning |
| Python pathlib | stdlib | Path operations | Preferred for socket path checks in detect_runtime() |

### Environment Variables & Configuration

| Variable | Default | Purpose | Scope |
|----------|---------|---------|-------|
| `EXECUTION_MODE` | `auto` | Runtime detection mode override | Node container |
| `DOCKER_HOST` | `unix:///var/run/docker.sock` | Docker socket path (explicit) | Node container env |
| `PODMAN_SOCK` | `/run/user/1000/podman/podman.sock` | Podman socket override (node-compose.podman.yaml only) | Node container volume mount source |
| `JOB_MEMORY_LIMIT` | (from env) | Memory limit for jobs | Node container (passed to runtime.py) |
| `JOB_CPU_LIMIT` | (from env) | CPU limit for jobs | Node container (passed to runtime.py) |

### Installation / Deployment

**Node Compose (Docker):**
```yaml
# node-compose.yaml
services:
  node:
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock:rw  # Docker socket mount
    group_add:
      - "999"  # docker group GID — verify with: getent group docker
    cap_drop:
      - ALL
    cap_add:
      - NET_BIND_SERVICE  # (if needed for sidecar; otherwise cap_drop: ALL only)
    security_opt:
      - no-new-privileges:true
    environment:
      - DOCKER_HOST=unix:///var/run/docker.sock
      - EXECUTION_MODE=auto  # (or omit for auto-detect)
networks:
  jobs_network:
    driver: bridge
```

**Node Compose (Podman):**
```yaml
# node-compose.podman.yaml
services:
  node:
    volumes:
      - ${PODMAN_SOCK:-/run/user/1000/podman/podman.sock}:/run/podman/podman.sock:rw
    userns_mode: keep-id
    security_opt:
      - no-new-privileges:true
    cap_drop:
      - ALL
    environment:
      - EXECUTION_MODE=podman
networks:
  jobs_network:
    driver: bridge
```

**Installation note:** Both files use Docker Compose v3 syntax and are drop-in replacements for the current `node-compose.yaml`. No additional dependencies beyond what's already in Containerfile.node.

## Architecture Patterns

### Socket Detection Pattern (detect_runtime in runtime.py)

**What:** Probe for socket files first (privileged check via `os.path.exists()`), then fall back to binary detection in PATH. Socket presence is more reliable than binary presence in container environments.

**Socket-first order:**
```python
# 1. Check for Docker socket (most common in Docker-in-Docker setups)
if os.path.exists("/var/run/docker.sock"):
    return "docker"

# 2. Check for Podman socket (rootless Podman or Podman daemon)
if os.path.exists("/run/podman/podman.sock"):
    return "podman"

# 3. Fallback to binary detection
if shutil.which("podman"):
    return "podman"
if shutil.which("docker"):
    return "docker"

# 4. Error if nothing found
raise RuntimeError("No container runtime detected...")
```

**Why this order:** Docker socket is most common (Docker daemon is default on many Linux hosts). Podman socket is the preferred method for Podman. Binaries alone don't guarantee you have a running daemon or socket access, so they're fallbacks only.

**When to use:** Called once at `ContainerRuntime.__init__()` in `runtime.py` module init. Honors explicit `EXECUTION_MODE` env var as an override.

### Job Container Networking Pattern

**What:** Job containers execute on an isolated bridge network (`jobs_network`), not `host` or `default`. This prevents jobs from reaching the orchestrator network or making direct host connections.

**Network topology:**
```
puppeteer_default (orchestrator network)
  ├── agent
  ├── model
  ├── db
  └── node (also joined to jobs_network)

jobs_network (job isolation)
  ├── node (shared namespace with sidecar)
  └── [ephemeral job containers spawned here]
```

**Job container execution:**
```python
# In runtime.py run()
cmd = [self.runtime, "run", "--rm"]
# OLD: cmd.extend(["--network=host"])
# NEW: cmd.extend([f"--network={network_ref}"])  # network_ref = "jobs_network"
```

**Sidecar access:** Sidecar uses `network_mode: service:node`, so it shares the node's network namespace and is reachable by job containers as `localhost` or the sidecar's hostname within `jobs_network`.

**When to use:** All job execution invocations in `runtime.py`. The `network_ref` parameter (already present in the signature) is wired from `node.py` with the value `jobs_network`.

### Capability Restrictions Pattern (from Phase 133)

**What:** Node container applies uniform capability restrictions: `cap_drop: ALL` + `security_opt: no-new-privileges:true`. Only add specific capabilities if the node requires them for a specific operation (e.g., if sidecar needs `NET_BIND_SERVICE`).

**Applied in:**
- `node-compose.yaml`: socket mount doesn't require extra capabilities (socket is accessed via file descriptor, not via syscall privilege checks)
- `node-compose.podman.yaml`: same restrictions apply

**Why:** Follows Phase 133 hardening strategy for all services. Prevents privilege escalation via setuid/setgid binaries if the container is compromised.

### appuser Socket Access Pattern

**For Docker (node-compose.yaml):**
```yaml
group_add:
  - "999"  # GID 999 is docker group (verify: getent group docker)
volumes:
  - /var/run/docker.sock:/var/run/docker.sock:rw
```
appuser (UID 1000) inherits GID 999 via `group_add`, grants read/write access to the socket file.

**For Podman rootless (node-compose.podman.yaml):**
```yaml
userns_mode: keep-id
volumes:
  - ${PODMAN_SOCK:-/run/user/1000/podman/podman.sock}:/run/podman/podman.sock:rw
```
`keep-id` mode means appuser (UID 1000 inside container) maps to the host user running Podman (typically UID 1000), so socket file ownership works without explicit group manipulation.

**Why this works:** Docker group membership allows non-root access to the Docker daemon. Podman rootless socket is owned by the host user, not a special group.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Container runtime detection | Custom shell script to find `docker`/`podman` binaries | `shutil.which()` + socket file checks in Python | Reliable across Alpine/Debian, handles both binaries and sockets, no shell dependency |
| Docker daemon communication | Direct TCP sockets or raw Docker API calls | Docker CLI or Docker Python SDK (python-docker) | Docker API is versioned and changes; CLI is stable. SDK is available but Docker CLI binary is already in image. |
| Podman socket detection | Hardcoding `/run/podman/podman.sock` without checking existence | `os.path.exists()` check in detect_runtime() | Podman socket path varies by installation; check existence, don't assume |
| Job network isolation | Custom iptables rules or manual bridge setup | Compose-managed bridge network + `--network=<name>` at job spawn | Docker Compose handles bridge creation and lifecycle; Docker/Podman `--network` flag is stable and doesn't require manual setup |
| Group membership for socket access | Manual `setgroup()` at runtime | Docker Compose `group_add` directive (Docker) or `userns_mode: keep-id` (Podman) | Compose handles group membership at container start; runtime manipulation is error-prone and doesn't persist |

**Key insight:** Socket access and network isolation are well-solved problems in container platforms. The platform provides these tools (socket mounts, group_add, userns_mode, bridge networks) — they're not tricks that need custom implementation.

## Common Pitfalls

### Pitfall 1: Group GID Mismatch (Docker socket access)

**What goes wrong:** Using a hardcoded GID (e.g., `group_add: [999]`) assumes the docker group on the host has GID 999. On some systems it might be 995 or 100. Node container crashes with "Permission denied" when trying to access `/var/run/docker.sock`.

**Why it happens:** GID assignment is OS/distro-dependent. Debian uses 999, RHEL uses 995, Alpine uses different defaults. Instructions that say "use GID 999" without verification cause failures in non-Debian environments.

**How to avoid:** Add inline documentation in compose file: "GID 999 is the docker group default — verify on your host with: `getent group docker`". Operators must run this check and update if needed.

**Warning signs:** 
- Node container exits with: `permission denied while trying to connect to Docker daemon socket at unix:///var/run/docker.sock`
- `docker exec node-container id` shows appuser in wrong groups

### Pitfall 2: Podman Socket Path Hardcoding

**What goes wrong:** Assuming Podman socket is always at `/run/podman/podman.sock`. For rootless Podman, the socket is at `/run/user/<UID>/podman/podman.sock`. Container fails to mount a non-existent socket, or detection fails because the socket path is wrong.

**Why it happens:** Podman has two modes (rootful daemon, rootless user daemon) with different socket paths. Code that hardcodes one path works only for one scenario.

**How to avoid:** 
- In `detect_runtime()`: check `/run/podman/podman.sock` first (rootful daemon), then check a user socket path via env var if needed
- In `node-compose.podman.yaml`: provide `PODMAN_SOCK` env var with a sensible default (`/run/user/1000/podman/podman.sock`) and allow override via `${PODMAN_SOCK:-default}`
- Document in comments that rootless Podman requires `systemctl --user enable podman.socket` on the host

**Warning signs:**
- `detect_runtime()` returns `"podman"` but Podman CLI works (socket not mounted correctly)
- Container logs: `Error: error creating runtime for 'job-container': error creating container runtime: mkdir /run/podman: permission denied`

### Pitfall 3: Forgetting to Replace --network=host in runtime.py

**What goes wrong:** Code to use `jobs_network` is merged in compose files and `node.py`, but `runtime.py` still has the hard-coded `cmd.extend(["--network=host"])` line. Job containers spawn on the host network, defeating the isolation goal of Phase 134.

**Why it happens:** The runtime.py change is in a different file from the compose changes, and the parameter `network_ref` was already present but unused. Easy to miss during code review.

**How to avoid:** 
- Test job execution against the new compose file: verify that a test job can reach the sidecar (via `jobs_network`) but cannot reach the orchestrator agent (no route to `puppeteer_default`)
- Add a comment at the old `--network=host` line: "DEPRECATED: replaced with jobs_network bridge isolation (Phase 134)"
- Commit `runtime.py` and network testing in the same PR so the change is visible

**Warning signs:**
- `docker inspect <job-container>` shows `"NetworkMode": "host"` instead of `"NetworkMode": "jobs_network"`
- Job script can reach `https://puppeteer-agent-1:8001` (should not be reachable)

### Pitfall 4: Sidecar Network Mode Misconception

**What goes wrong:** Thinking sidecar must also be updated to use `--network=jobs_network`, or removing `network_mode: service:node` from the sidecar service definition in compose.

**Why it happens:** "Job isolation" might seem to require sidecar isolation too, or copy-pasting network settings from node to sidecar without understanding that sidecar is not a job.

**How to avoid:** Sidecar remains as-is: `network_mode: service:node` in compose, so it shares the node's network namespace and is reachable by jobs. The sidecar is not isolated — it's a trusted control point. Do not change its network configuration.

**Warning signs:**
- Jobs can no longer reach the sidecar (heartbeat timeouts, execution failures)
- Error logs: `connect: no route to host` when job tries to reach sidecar

### Pitfall 5: Missing jobs_network in compose

**What goes wrong:** `runtime.py` is updated to use `--network=jobs_network`, but the `jobs_network` bridge is not defined in `node-compose.yaml` or `node-compose.podman.yaml`. Docker/Podman fails to spawn job containers: `Error response from daemon: network jobs_network not found`.

**Why it happens:** The network definition is added to `node-compose.yaml`, but a variant file (`node-compose.podman.yaml`) is created without copying the network definition, or the network is deleted during cleanup.

**How to avoid:** Define `jobs_network` in both `node-compose.yaml` and `node-compose.podman.yaml`:
```yaml
networks:
  puppeteer_default:
    external: true
  jobs_network:
    driver: bridge
```
Verify the network exists before restarting: `docker network ls | grep jobs_network`.

**Warning signs:**
- `docker compose up` succeeds, but first job fails with "network not found"
- `docker network ls` shows no `jobs_network` bridge

### Pitfall 6: Breaking Backwards Compatibility with EXECUTION_MODE

**What goes wrong:** Socket detection changes the behavior of `EXECUTION_MODE=auto`. An operator who has set `EXECUTION_MODE=podman` or `EXECUTION_MODE=docker` explicitly sees the behavior change if the socket detection order is wrong.

**Why it happens:** If the socket detection order probes for Docker first but the operator's host has Podman as the primary runtime, auto-detect will choose Docker (if the socket exists) even though the operator expects Podman.

**How to avoid:** Respect explicit `EXECUTION_MODE` env var — never override it in socket detection. Only perform socket detection when `EXECUTION_MODE == "auto"`. Verify in testing that explicit modes still work as before.

**Warning signs:**
- Operator sets `EXECUTION_MODE=podman` but node uses Docker socket
- Node logs: `Container Runtime Detected: docker` when Podman was expected

## Code Examples

### detect_runtime() with Socket-First Detection

**Source:** `puppets/environment_service/runtime.py` (Phase 134 modification)

```python
def detect_runtime(self) -> str:
    """
    Detect available container runtime.
    
    Order of detection:
    1. Explicit EXECUTION_MODE env var (always respected)
    2. Socket files: Docker → Podman
    3. Binary PATH: Podman → Docker
    4. Error if nothing found
    """
    mode = os.environ.get("EXECUTION_MODE", "auto").lower()
    if mode in ("docker", "podman"):
        logger.info(f"EXECUTION_MODE={mode} (explicit)")
        return mode
    
    # auto mode: socket-first detection
    if os.path.exists("/var/run/docker.sock") and shutil.which("docker"):
        logger.info("Container runtime: docker (socket detected)")
        return "docker"
    
    if os.path.exists("/run/podman/podman.sock"):
        logger.info("Container runtime: podman (socket detected)")
        return "podman"
    
    # Fallback: binary detection
    if shutil.which("podman"):
        logger.info("Container runtime: podman (binary in PATH)")
        return "podman"
    
    if shutil.which("docker"):
        logger.info("Container runtime: docker (binary in PATH)")
        return "docker"
    
    raise RuntimeError(
        "No container runtime detected. "
        "Ensure Docker or Podman is installed and accessible. "
        "For Docker-in-Docker, mount the host Docker socket at /var/run/docker.sock. "
        "For Podman, ensure /run/podman/podman.sock is mounted or podman binary is in PATH. "
        "See docs/runbooks/faq.md for guidance."
    )
```

### Job Container Network Isolation

**Source:** `puppets/environment_service/runtime.py` (Phase 134 modification)

```python
async def run(
    self,
    image: str,
    command: List[str],
    env: Dict[str, str] = {},
    mounts: List[str] = [],
    network_ref: str = "jobs_network",  # NEW: default to jobs_network
    input_data: str = None,
    memory_limit: Optional[str] = None,
    cpu_limit: Optional[str] = None,
    timeout: Optional[int] = 30,
) -> Dict:
    """
    Executes a containerized job with network isolation.
    
    network_ref: bridge network name for job containers (default: jobs_network).
                 Job containers cannot reach puppeteer_default or host network.
    """
    cmd = [self.runtime, "run", "--rm"]
    
    # ... other flags ...
    
    # Network Strategy: use bridge network for isolation
    if os.name != 'nt':
        cmd.extend([f"--network={network_ref}"])
    
    # ... rest of execution ...
```

### node-compose.yaml with Socket Mount

**Source:** `puppets/node-compose.yaml` (Phase 134 complete version)

```yaml
version: '3'

networks:
  puppeteer_default:
    external: true
  jobs_network:
    driver: bridge

services:
  node:
    build:
      context: .
      dockerfile: Containerfile.node
    image: localhost/master-of-puppets-node:latest
    restart: always
    
    # Security: remove privileged mode, use capability restrictions
    cap_drop:
      - ALL
    security_opt:
      - no-new-privileges:true
    
    # Socket access: group_add grants docker group membership
    group_add:
      - "999"  # GID 999 is the docker group default — verify on your host with: getent group docker
    
    # Volumes: secrets + docker socket
    volumes:
      - ./secrets:/app/secrets
      - /var/run/docker.sock:/var/run/docker.sock:rw
    
    networks:
      - puppeteer_default
      - jobs_network
    
    environment:
      - NODE_TAGS=general,linux,test-group
      - JOB_IMAGE=docker.io/library/python:3.12-alpine
      - AGENT_URL=https://puppeteer-agent-1:8001
      - JOIN_TOKEN=${JOIN_TOKEN}
      - ROOT_CA_PATH=/app/secrets/root_ca.crt
      - PYTHONUNBUFFERED=1
      - DOCKER_HOST=unix:///var/run/docker.sock
      - EXECUTION_MODE=auto

  sidecar:
    image: localhost/mop-sidecar-proxy:v1
    restart: always
    network_mode: service:node  # Shares node's network namespace
```

### node-compose.podman.yaml for Rootless Podman

**Source:** `puppets/node-compose.podman.yaml` (Phase 134 new file)

```yaml
version: '3'

networks:
  puppeteer_default:
    external: true
  jobs_network:
    driver: bridge

services:
  node:
    build:
      context: .
      dockerfile: Containerfile.node
    image: localhost/master-of-puppets-node:latest
    restart: always
    
    # Security: capability restrictions (socket access doesn't need extra privileges)
    cap_drop:
      - ALL
    security_opt:
      - no-new-privileges:true
    
    # Rootless Podman: keep-id maps UID 1000 inside to host user running Podman
    userns_mode: keep-id
    
    # Volumes: secrets + podman socket (rootless path)
    volumes:
      - ./secrets:/app/secrets
      - ${PODMAN_SOCK:-/run/user/1000/podman/podman.sock}:/run/podman/podman.sock:rw
    
    networks:
      - puppeteer_default
      - jobs_network
    
    environment:
      - NODE_TAGS=general,linux,test-group
      - JOB_IMAGE=docker.io/library/python:3.12-alpine
      - AGENT_URL=https://puppeteer-agent-1:8001
      - JOIN_TOKEN=${JOIN_TOKEN}
      - ROOT_CA_PATH=/app/secrets/root_ca.crt
      - PYTHONUNBUFFERED=1
      - EXECUTION_MODE=podman

  sidecar:
    image: localhost/mop-sidecar-proxy:v1
    restart: always
    network_mode: service:node  # Shares node's network namespace
```

**Note:** Requires `systemctl --user enable podman.socket` on host before deployment. The socket path can be overridden via `PODMAN_SOCK` env var.

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `privileged: true` in node-compose | Socket mount + capability restrictions | Phase 134 | Reduces attack surface; node can still execute jobs without full privilege escalation capability |
| Hardcoded runtime binary detection (PATH only) | Socket-first detection (file exists) + PATH fallback | Phase 134 | More reliable in container-in-container scenarios; properly detects Podman daemon vs rootless socket |
| `--network=host` for all job containers | `--network=<bridge>` with dedicated `jobs_network` | Phase 134 | Isolates jobs from orchestrator network; prevents lateral movement if job is compromised |
| Single compose file (Docker only) | Docker + Podman variants shipped in parallel | Phase 134 | Supports rootless Podman deployments natively; operators can choose based on host runtime |

**Deprecated/Outdated:**
- `EXECUTION_MODE=direct` (Python subprocess execution): Removed in v20.0. All jobs execute in containers for security isolation. Use `docker` or `podman` mode instead.
- Mounting the entire host filesystem (not applicable here, but legacy concern): Phase 134 mounts only the specific socket file, not the whole host.

## Open Questions

1. **jobs_network lifecycle management**
   - What we know: The network is defined in compose with `driver: bridge`. Docker Compose creates it on `up` and cleans it on `down`.
   - What's unclear: Should the network be external (pre-created) or compose-managed? External requires manual `docker network create`, managed is automatic.
   - Recommendation: Keep it compose-managed (simpler for operators). Document that `docker compose down` removes the network; jobs in progress will be disconnected.

2. **Containerfile.node cleanup (Phase 135 deferred)**
   - What we know: Containerfile.node installs `krb5-user`, `iptables`, and `podman` packages. After socket mount, these are no longer needed.
   - What's unclear: Can we safely remove these packages, or do they have other uses? Should this be part of Phase 134 or deferred?
   - Recommendation: Defer to Phase 135 (CONT-07 "strip packages no longer needed"). Phase 134 focuses on socket mounting; package optimization is a separate concern.

3. **DOCKER_HOST env var necessity**
   - What we know: Docker CLI and Python docker SDK respect the `DOCKER_HOST` env var.
   - What's unclear: Is setting `DOCKER_HOST=unix:///var/run/docker.sock` in compose necessary, or does Docker auto-detect the socket at the standard path?
   - Recommendation: Set it explicitly in compose for clarity and to support custom socket paths via env override in the future. It's a low-cost documentation tool.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest + asyncio |
| Config file | `puppeteer/pyproject.toml` (pytest configuration) |
| Quick run command | `cd puppeteer && pytest tests/test_nonroot.py -x -v` |
| Full suite command | `cd puppeteer && pytest tests/ -x` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| CONT-02 | Node container removes `privileged: true` and uses socket mount | integration | `docker inspect puppeteer-node-1 \| grep -i privileged` (verify false) + socket volume mount check | ✅ manual inspection; unit test TBD |
| CONT-09 | `node-compose.podman.yaml` variant exists and validates with `docker-compose config` | integration | `docker-compose -f puppets/node-compose.podman.yaml config > /dev/null && echo "valid"` | ✅ Wave 0 |
| CONT-10 | `runtime.py` detects Podman socket at `/run/podman/podman.sock` when Docker socket absent | unit | `cd puppeteer && pytest tests/test_runtime_detection.py::test_podman_socket_detection -x` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `cd puppeteer && pytest tests/test_nonroot.py -x -v`
- **Per wave merge:** Full suite: `cd puppeteer && pytest tests/ -x`
- **Phase gate:** Validation script (`mop_validation/scripts/`) runs end-to-end on Docker stack with both compose files

### Wave 0 Gaps

- [ ] `tests/test_runtime_detection.py` — unit tests for socket-first detection logic (CONT-10)
  - Test: socket at `/var/run/docker.sock` → returns `"docker"`
  - Test: socket at `/run/podman/podman.sock` (no docker socket) → returns `"podman"`
  - Test: no sockets, `docker` binary in PATH → returns `"docker"`
  - Test: no sockets, no binaries → raises RuntimeError
  - Test: explicit `EXECUTION_MODE=podman` overrides socket detection
- [ ] `tests/test_network_isolation.py` — verify job containers use `jobs_network` (new behavior from Phase 134)
  - Test: job container spawned with `--network=jobs_network` (not `--network=host`)
  - Test: `docker inspect <job-container>` shows network as `jobs_network`
  - Test: job cannot reach `puppeteer_default` network addresses
  - Test: job can reach sidecar on `jobs_network`
- [ ] E2E validation in `mop_validation/scripts/` — run jobs on Docker stack with both compose files
  - Script: `test_phase134_socket_docker.py` — verify jobs execute via socket mount (no privileged mode)
  - Script: `test_phase134_socket_podman.py` — verify jobs execute with Podman socket (if Podman host available)
  - Script: `test_phase134_network_isolation.py` — verify job network isolation

*(If no gaps: "Existing test infrastructure in puppeteer/tests/ and mop_validation/scripts/ will be extended. Wave 0 involves writing the three new test modules above; full infrastructure exists.")*

## Sources

### Primary (HIGH confidence)

- **CONTEXT.md (Phase 134)** — User decisions on socket detection order, compose variant design, network isolation strategy (locked constraints used to drive research)
- **REQUIREMENTS.md** — v22.0 milestone requirements: CONT-02 (node socket mount), CONT-09 (Podman variant), CONT-10 (socket detection)
- **compose.server.yaml** — Existing Phase 133 hardening patterns: `cap_drop: ALL` + `security_opt: no-new-privileges` applied uniformly
- **puppets/node-compose.yaml** — Current Docker Compose for nodes; shows `privileged: true` baseline and network structure
- **puppets/Containerfile.node** — Confirms Docker CLI binary, Podman, and Python 3.12 already in image
- **puppets/environment_service/runtime.py** — Existing `detect_runtime()` and `run()` methods; shows current `--network=host` hard-coding and Podman flags (`--storage-driver=vfs`, `--cgroup-manager=cgroupfs`, etc.)
- **CLAUDE.md (Project Instructions)** — Documents non-root user (appuser, UID 1000), socket mount strategy, and Docker Compose patterns

### Secondary (MEDIUM confidence)

- **Docker documentation on socket mounts** — Standard practice; socket mounted as read-write volume grants access via file descriptor
- **Podman rootless socket location** — `/run/user/<UID>/podman/podman.sock` confirmed; `userns_mode: keep-id` is standard pattern for rootless Podman in Compose
- **Group membership for Docker socket access** — GID 999 is default on Debian/Ubuntu; varies by distro (verified via CONTEXT.md user decision)
- **docs/docs/runbooks/faq.md** — Existing socket mount documentation for Docker-in-Docker scenarios; confirms best practice approach

### Tertiary (LOW confidence)

- None — all findings are grounded in project code, official CLAUDE.md, and user-locked decisions.

## Metadata

**Confidence breakdown:**
- Standard stack (Python, Docker, Podman, socket mounts): **HIGH** — all tools are production-standard and already deployed in the codebase
- Architecture patterns (socket detection, network isolation, capability restrictions): **HIGH** — patterns are well-established in Docker/Podman ecosystem and directly supported by platform features
- Pitfalls (group GID, socket paths, network configuration): **HIGH** — derived from common container hardening mistakes documented in Docker/Podman best practices and project history (Phase 133)

**Research date:** 2026-04-12
**Valid until:** 2026-05-12 (stable container runtime APIs; refresh if Docker/Podman major version changes)
