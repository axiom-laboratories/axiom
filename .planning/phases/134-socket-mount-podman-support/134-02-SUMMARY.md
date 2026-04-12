---
phase: 134
plan: 02
type: execute
title: "Socket Mount & Podman Support – Compose & Network Wiring"
subsystem: container-hardening
status: complete
date_completed: "2026-04-12"
duration_minutes: 25
tasks_completed: 5
test_results: "19/19 passing"
requirements_satisfied: [CONT-02, CONT-09]
key_decisions:
  - "network_ref switched from hostname-based to explicit jobs_network bridge"
  - "Sidecar reachability maintained via network_mode: service:node"
  - "Jobs_network defined in both compose variants (Docker + Podman)"
tech_stack:
  added: []
  patterns: ["Socket mount strategy", "Network isolation bridge", "Capability restrictions"]
key_files:
  created:
    - puppets/node-compose.podman.yaml
    - puppeteer/tests/test_node_compose.py
  modified:
    - puppets/node-compose.yaml
    - puppets/environment_service/node.py
dependency_graph:
  requires: [134-01]
  provides: [CONT-02, CONT-09]
  affects: [135-resource-limits]
---

# Phase 134 Plan 02: Socket Mount & Podman Support – Compose & Network Wiring

## Summary

Completed Phase 134 Plan 02: Updated both Docker and Podman node compose files to remove `privileged: true`, mount sockets, apply capability restrictions, and define isolated job network. Wired `jobs_network` from compose files through `node.py` to `runtime.py`. All 19 validation tests passing.

**Duration:** 25 minutes (4 tasks executed sequentially with per-task commits)

## Tasks Completed

| # | Task | Commit | Status |
|----|------|--------|--------|
| 0 | Create compose validation test stubs (19 tests) | 295d800 | ✓ Complete |
| 1 | Update node-compose.yaml (Docker variant) | ab5f22f | ✓ Complete |
| 2 | Create node-compose.podman.yaml (Podman variant) | 31df475 | ✓ Complete |
| 3 | Wire jobs_network to runtime.py in node.py | 1ae80f8 | ✓ Complete |
| 4 | Validate all tests and compose files | b784002 | ✓ Complete |

## Key Changes

### Task 0: Compose Validation Test Suite

Created `/puppeteer/tests/test_node_compose.py` with 19 validation tests:

**Docker Variant Tests (9):**
- Valid YAML + docker compose config validation
- No privileged mode present
- Docker socket mount (`/var/run/docker.sock:/var/run/docker.sock:rw`)
- Capability restrictions (`cap_drop: ALL`, `security_opt: no-new-privileges:true`)
- Jobs network defined as bridge
- Node joins both `puppeteer_default` and `jobs_network`
- Group membership for socket access (`group_add: [999]`)
- `DOCKER_HOST` environment variable set to `unix:///var/run/docker.sock`

**Podman Variant Tests (6):**
- Valid YAML + docker compose config validation
- Rootless Podman UID mapping (`userns_mode: keep-id`)
- Podman socket mount with env var override (`${PODMAN_SOCK:-/run/user/1000/podman/podman.sock}`)
- Execution mode set to `EXECUTION_MODE=podman` (explicit)
- No group_add present (userns_mode handles it)
- Jobs network defined as bridge

**Capability Restrictions Tests (4):**
- Both variants have `cap_drop: ALL`
- Both variants have `security_opt: no-new-privileges:true`

### Task 1: Updated node-compose.yaml (Docker Variant)

Changed from `privileged: true` to socket-based access:

```yaml
# REMOVED: privileged: true

# ADDED: Capability restrictions
cap_drop:
  - ALL
security_opt:
  - no-new-privileges:true

# ADDED: Group membership for socket access
group_add:
  - "999"  # GID 999 is the docker group default

# UPDATED: Added socket mount volume
volumes:
  - ./secrets:/app/secrets
  - /var/run/docker.sock:/var/run/docker.sock:rw

# UPDATED: Added jobs_network bridge
networks:
  puppeteer_default:
    external: true
  jobs_network:
    driver: bridge

# UPDATED: Node joins both networks
networks:
  - puppeteer_default
  - jobs_network

# ADDED: Explicit DOCKER_HOST environment variable
- DOCKER_HOST=unix:///var/run/docker.sock
```

**Files modified:** `puppets/node-compose.yaml` (35 lines, ~50 lines total)

**Test results:** 9/9 Docker variant tests passing

### Task 2: Created node-compose.podman.yaml (Podman Variant)

New file for rootless Podman deployments with key differences from Docker variant:

```yaml
# ADDED: Rootless Podman UID mapping (no group_add needed)
userns_mode: keep-id

# DIFFERENT SOCKET: Podman socket with env var override
volumes:
  - ./secrets:/app/secrets
  - ${PODMAN_SOCK:-/run/user/1000/podman/podman.sock}:/run/podman/podman.sock:rw

# DIFFERENT EXECUTION MODE: Explicit Podman override
environment:
  - EXECUTION_MODE=podman

# SAME: Capability restrictions
cap_drop:
  - ALL
security_opt:
  - no-new-privileges:true

# SAME: Jobs network bridge
networks:
  puppeteer_default:
    external: true
  jobs_network:
    driver: bridge

# SAME: Node joins both networks
networks:
  - puppeteer_default
  - jobs_network
```

**Files created:** `puppets/node-compose.podman.yaml` (49 lines)

**Test results:** 6/6 Podman variant tests passing

### Task 3: Wired jobs_network Through node.py

Updated job execution in `node.py` to use `jobs_network` instead of hostname:

**Before:**
```python
hostname = socket.gethostname()
# ... later ...
result = await self.runtime_engine.run(
    ...,
    network_ref=hostname,
    ...
)
```

**After:**
```python
network_ref = "jobs_network"
# ... later (both paths) ...
result = await self.runtime_engine.run(
    ...,
    network_ref=network_ref,
    ...
)
```

**Changes:** 
- Replaced hostname-based network reference with explicit bridge name
- Updated both stdin and file-based execution paths
- Sidecar remains accessible via `network_mode: service:node` (shares node's namespace)

**Files modified:** `puppets/environment_service/node.py` (5 lines changed)

### Task 4: Validation Summary

**Test Results:**

```
======================== 19 passed, 5 warnings in 0.21s ========================

Docker Compose Tests:     9/9 ✓
Podman Compose Tests:     6/6 ✓
Capability Tests:         4/4 ✓
```

**Compose File Validation:**

Both files pass `docker compose config --quiet`:
- `puppets/node-compose.yaml` → ✓ Valid
- `puppets/node-compose.podman.yaml` → ✓ Valid

## Requirements Satisfaction

### CONT-02: Node removes `privileged: true` and uses socket mount

✓ **Satisfied**
- `privileged: true` removed from node-compose.yaml
- Docker socket mounted at `/var/run/docker.sock:/var/run/docker.sock:rw` with group_add
- `cap_drop: ALL` + `security_opt: no-new-privileges:true` applied (Phase 133 pattern)
- Test verification: `test_docker_compose_no_privileged`, `test_docker_compose_docker_socket_mount`, `test_docker_compose_cap_drop_all`, `test_docker_compose_security_opt`

### CONT-09: `node-compose.podman.yaml` variant ships alongside `node-compose.yaml`

✓ **Satisfied**
- New file `puppets/node-compose.podman.yaml` created
- Uses `userns_mode: keep-id` for rootless Podman support
- Mounts Podman socket with env var override: `${PODMAN_SOCK:-/run/user/1000/podman/podman.sock}`
- Sets `EXECUTION_MODE=podman` explicitly
- Test verification: `test_podman_compose_config_valid`, `test_podman_compose_userns_mode_keep_id`, `test_podman_compose_podman_socket_mount`, `test_podman_compose_execution_mode_podman`

### CONT-10: `runtime.py` auto-detects Podman socket path

✓ **Already satisfied in Plan 01**
- Socket-first detection order implemented in `puppets/environment_service/runtime.py`
- Checks `/var/run/docker.sock` first, then `/run/podman/podman.sock`
- Falls back to binary detection if needed
- Respects explicit `EXECUTION_MODE` env var override

## Deviations from Plan

None. Plan executed exactly as specified.

All locked decisions from CONTEXT.md honored:
- Socket access via `group_add: [999]` with inline comment about GID verification
- Podman variant with `userns_mode: keep-id` + `${PODMAN_SOCK:-...}` env var
- Both files apply `cap_drop: ALL` + `security_opt: no-new-privileges` (Phase 133 pattern)
- `jobs_network` defined as bridge in both variants
- Node joins both `puppeteer_default` and `jobs_network`
- Sidecar unchanged: `network_mode: service:node`

## Network Topology

After Phase 134 Plan 02:

```
puppeteer_default (orchestrator network)
  ├── agent
  ├── model
  ├── db
  └── node (also joined to jobs_network)

jobs_network (job isolation bridge)
  ├── node (shared namespace with sidecar via network_mode: service:node)
  └── [ephemeral job containers spawned with --network=jobs_network]
```

**Job container isolation:**
- Job containers can reach: node + sidecar (via `jobs_network`)
- Job containers cannot reach: puppeteer agent, host network, `puppeteer_default`
- Sidecar reachable as `localhost` within the job container (shared network namespace)

## Deployment Instructions

### Docker Host Deployment

```bash
# Start node with Docker socket mount
docker compose -f puppets/node-compose.yaml up -d

# Verify GID 999 on your host (may differ by distro)
getent group docker

# If different, update group_add in node-compose.yaml to the correct GID
```

### Rootless Podman Deployment

```bash
# Enable Podman socket on host (if not already enabled)
systemctl --user enable podman.socket
systemctl --user start podman.socket

# Start node with Podman compose variant
docker compose -f puppets/node-compose.podman.yaml up -d

# Override Podman socket path if using non-standard location
export PODMAN_SOCK=/run/user/$(id -u)/podman/podman.sock
docker compose -f puppets/node-compose.podman.yaml up -d
```

## Phase 134 Progress

**Plan 01 (Socket-First Detection):** ✓ Complete
- Socket detection order implemented in `runtime.py`
- Podman socket support added (`/run/podman/podman.sock`)
- All 10 tests passing

**Plan 02 (Compose & Network Wiring):** ✓ Complete
- Docker variant compose file updated
- Podman variant compose file created
- Network wiring implemented in `node.py`
- All 19 tests passing

**Remaining for Phase 134:** Phase 135 (Resource Limits)

## Self-Check

**Files created:**
- `puppeteer/tests/test_node_compose.py` → ✓ Exists
- `puppets/node-compose.podman.yaml` → ✓ Exists

**Files modified:**
- `puppets/node-compose.yaml` → ✓ Modified
- `puppets/environment_service/node.py` → ✓ Modified

**Commits:**
- 295d800 test(134-02): add compose validation test stubs → ✓ Verified
- ab5f22f feat(134-02): update node-compose.yaml → ✓ Verified
- 31df475 feat(134-02): create node-compose.podman.yaml → ✓ Verified
- 1ae80f8 feat(134-02): wire jobs_network to runtime.py → ✓ Verified
- b784002 test(134-02): all 19 compose validation tests pass → ✓ Verified

**Tests:**
- 19/19 tests passing → ✓ Verified
- Both compose files valid YAML → ✓ Verified
- Both pass `docker compose config --quiet` → ✓ Verified

**Self-Check: PASSED**
