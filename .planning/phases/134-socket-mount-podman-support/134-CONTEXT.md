# Phase 134: Socket Mount & Podman Support - Context

**Gathered:** 2026-04-12
**Status:** Ready for planning

<domain>
## Phase Boundary

Remove `privileged: true` from node containers and replace with Docker/Podman socket mounts. Update `runtime.py` to auto-detect the Podman socket. Ship a `node-compose.podman.yaml` variant for Podman host deployments. Change job container networking from `--network=host` to a dedicated `jobs_network` bridge.

</domain>

<decisions>
## Implementation Decisions

### Socket Access for appuser
- Use `group_add: [999]` in `node-compose.yaml` — GID 999 is the docker group default on most distros
- Add inline comment on the `group_add` line: "GID 999 is the docker group default — verify on your host with: `getent group docker`"
- Apply `cap_drop: ALL` + `security_opt: no-new-privileges` to node container, consistent with Phase 133 pattern
- Set `DOCKER_HOST=unix:///var/run/docker.sock` explicitly in compose env vars

### Podman Socket Detection Order (runtime.py)
- Socket-first detection order in `detect_runtime()`:
  1. `/var/run/docker.sock` present → return `"docker"`
  2. `/run/podman/podman.sock` present → return `"podman"`
  3. `podman` binary in PATH → return `"podman"`
  4. `docker` binary in PATH → return `"docker"`
  5. Raise `RuntimeError`
- When Podman socket detected, return `"podman"` (uses existing Podman code path in `run()`)

### Podman Compose Variant (node-compose.podman.yaml)
- Pure Docker Compose syntax — no Podman-specific labels
- Key differences from `node-compose.yaml`:
  - Mounts `${PODMAN_SOCK:-/run/user/1000/podman/podman.sock}` from host → `/run/podman/podman.sock` inside container (fixed internal path)
  - Sets `EXECUTION_MODE=podman` (overrides auto-detect)
  - Sets `userns_mode: keep-id` (UID 1000 inside container maps to host user running rootless Podman — socket ownership works without group_add)
  - No `group_add` needed (rootless Podman socket is owned by the host user)
- Add comment: "Requires `systemctl --user enable podman.socket` on host"
- Targets rootless Podman deployments (host user running Podman, not root daemon)

### Job Container Networking
- Replace hard-coded `--network=host` in `runtime.py` with `--network=jobs_network`
- `jobs_network` is a Docker bridge network defined in compose and joined by the node container
- Node container joins both `puppeteer_default` (orchestrator access) and `jobs_network` (job isolation)
- Sidecar keeps `network_mode: service:node` — shares node's network namespace, reachable by job containers via node's IP on `jobs_network`
- Job containers can reach: node + sidecar (via `jobs_network`)
- Job containers cannot reach: puppeteer agent, host network, `puppeteer_default`
- `network_ref` parameter in `runtime.py run()` should be wired up to pass `jobs_network` from `node.py`
- Apply same pattern to `node-compose.podman.yaml`

### Claude's Discretion
- Exact `jobs_network` definition in compose (external vs compose-managed)
- Whether `node.py` passes the network name via env var or hardcodes `jobs_network`
- Any additional runtime.py cleanup around the old `--network=host` logic

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `runtime.py` `detect_runtime()`: already handles docker.sock + binary detection — extend with Podman socket check
- `runtime.py` `run()`: `network_ref` parameter already exists but is overridden by `--network=host` — wire it up properly
- `runtime.py` Podman code path: `--storage-driver=vfs`, `--cgroup-manager=cgroupfs`, `--events-backend=none` flags already there

### Established Patterns
- `compose.server.yaml` (Phase 133): `cap_drop: ALL` + `security_opt: no-new-privileges` — replicate in node compose
- `node-compose.yaml`: single compose file today — Phase 134 adds `node-compose.podman.yaml` sibling
- Sidecar uses `network_mode: service:node` — do not change this; it works via node's network namespace

### Integration Points
- `node.py` → `runtime.py`: need to pass `jobs_network` as the network name for job containers
- `node-compose.yaml`: remove `privileged: true`, add socket volume, `group_add`, `cap_drop`, `security_opt`, `DOCKER_HOST` env, `jobs_network`
- `node-compose.podman.yaml`: new file, mostly mirrors `node-compose.yaml` with Podman-specific overrides

</code_context>

<specifics>
## Specific Ideas

- "Job containers should only be able to reach mounts and network paths the node makes available to them" — `jobs_network` is the mechanism; node is the controlled gateway between orchestrator network and job network
- `PODMAN_SOCK` env var as override for the Podman socket host path (default `/run/user/1000/podman/podman.sock`)

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 134-socket-mount-podman-support*
*Context gathered: 2026-04-12*
