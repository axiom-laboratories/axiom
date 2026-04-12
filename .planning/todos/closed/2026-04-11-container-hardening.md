---
created: 2026-04-11T12:00:00.000Z
title: Harden container security posture (non-root, cap_drop, no privileged)
area: ops
files:
  - puppeteer/compose.server.yaml
  - puppeteer/Containerfile.server
  - puppets/node-compose.yaml
  - puppets/Containerfile.node
  - puppets/environment_service/runtime.py
  - puppeteer/agent_service/services/foundry_service.py
---

## Problem

No container in the stack is hardened. Every service runs as root, no capabilities are dropped,
Postgres is reachable on 0.0.0.0:5432, and the puppet node runs fully privileged. This is the
default Docker posture — functional, but unnecessarily wide attack surface.

Current issues ranked by severity:

| Issue | File | Severity |
|-------|------|----------|
| `privileged: true` on node | `node-compose.yaml` | High — full host escape if container compromised |
| All services run as root | All Containerfiles | High |
| Postgres exposed on 0.0.0.0:5432 | `compose.server.yaml` | Medium — DB reachable from host network |
| No `cap_drop` on any service | `compose.server.yaml` | Medium |
| No `security_opt: no-new-privileges` | All compose files | Medium |
| No `read_only` root filesystem | All compose files | Low |
| No memory/CPU resource limits | `compose.server.yaml` | Low |
| Hardcoded `masterpassword` default in compose | `compose.server.yaml` | Low |

## Solution

### Change 1: Non-root USER in Containerfiles

Add a dedicated non-root user to each Containerfile:

**`Containerfile.server`** (agent + model services):
```dockerfile
# Near the end of the Dockerfile, before CMD/ENTRYPOINT
RUN addgroup --system --gid 1001 appgroup && \
    adduser --system --uid 1001 --ingroup appgroup --no-create-home appuser

# Fix ownership of app directory and secrets volume mount point
RUN chown -R appuser:appgroup /app

USER appuser
```

Note: The agent service mounts the Docker socket (`/var/run/docker.sock`). The appuser needs to
be in the `docker` group inside the container, or the socket needs gid=docker. Handle with:
```dockerfile
RUN addgroup --system --gid 999 docker && \
    adduser appuser docker
```

**`Containerfile.node`** (puppet node):
Similar pattern. The node service calls the container runtime (docker/podman) — user must be in
the appropriate group.

### Change 2: Remove `privileged: true` from node — use host socket mount instead

The node uses `privileged: true` because it installs Podman and runs containers inside the node
container. The correct alternative is mounting the **host's** container runtime socket, which
`runtime.py` already supports. This aligns with the intended deployment model: Docker hosts run
Docker nodes, Podman hosts run Podman nodes — not mixed.

**Docker host** (`node-compose.yaml`):
```yaml
# Remove:
privileged: true

# Add:
volumes:
  - /var/run/docker.sock:/var/run/docker.sock
environment:
  - EXECUTION_MODE=docker  # or auto
```

**Podman host** (ship as `node-compose.podman.yaml` variant):
```yaml
# Remove:
privileged: true

# Add:
volumes:
  - /run/podman/podman.sock:/run/podman/podman.sock
  # rootless Podman alternative:
  # - /run/user/1000/podman/podman.sock:/run/podman/podman.sock
environment:
  - EXECUTION_MODE=podman  # or auto
```

Podman's socket is Docker API-compatible — the same client code works against both.

**`runtime.py` update required:** The auto-detection logic must check for the Podman socket path
(`/run/podman/podman.sock`) in addition to the Docker socket (`/var/run/docker.sock`). Current
auto-detection likely only checks for Docker.

**`Containerfile.node` cleanup:** With socket mount, the node container no longer runs its own
daemon. Remove all packages that were only needed for Podman-in-Docker:
```dockerfile
# Remove from apt install:
# podman, iptables, krb5-user, docker-cli (if only there for Podman support)
```

The node container just needs Python + the node agent. Significantly smaller image.

**Job containers do NOT get the socket mounted.** The socket is used by `runtime.py` in the node
container to spawn ephemeral job containers. Once spawned, the job container has no socket access
— it runs the signed script in isolation with no path back to the host daemon. This is by design
and must not be changed.

### Change 3: Remove Postgres external port binding

```yaml
# compose.server.yaml — db service
# Remove or restrict:
ports:
  - "5432:5432"   # DELETE — internal services use service name 'db' directly

# If external access is needed for debugging, bind to loopback only:
ports:
  - "127.0.0.1:5432:5432"
```

Services on the same Docker network reach Postgres via `db:5432` — no external binding needed.

### Change 4: cap_drop + security_opt on all services

Add to each service in `compose.server.yaml` and `node-compose.yaml`:
```yaml
cap_drop:
  - ALL
security_opt:
  - no-new-privileges:true
```

Selectively add back only what each service requires:
- **cert-manager (Caddy)**: `cap_add: [NET_BIND_SERVICE]` to bind ports 80/443
- **agent**: no extra caps needed (Docker socket access is via group, not capabilities)
- **model, dashboard, docs**: no extra caps needed
- **registry**: `cap_add: [NET_BIND_SERVICE]` if binding port 5000 < 1024 (it's 5000, fine without)
- **db (Postgres)**: runs as internal postgres user already — no extra caps needed
- **node**: no extra caps if using Docker socket mount

### Change 5: Resource limits

Add reasonable resource limits to prevent runaway containers from taking down the host:

```yaml
# compose.server.yaml
agent:
  deploy:
    resources:
      limits:
        memory: 1g
        cpus: '2.0'
      reservations:
        memory: 256m

model:
  deploy:
    resources:
      limits:
        memory: 512m
        cpus: '1.0'

db:
  deploy:
    resources:
      limits:
        memory: 512m
```

### Change 6: read_only root filesystem (optional, higher effort)

Mark root filesystems read-only and use tmpfs for writable paths:
```yaml
read_only: true
tmpfs:
  - /tmp
  - /run
```

This requires identifying all paths each service writes to and either volume-mounting or tmpfs-ing
them. Higher effort — treat as a follow-on change after the above.

### Change 7: Remove hardcoded default password

```yaml
# compose.server.yaml — db service
environment:
  POSTGRES_USER: puppet
  POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}   # Remove default masterpassword
  POSTGRES_DB: puppet_db
```

Require `POSTGRES_PASSWORD` to be explicitly set in the env file. Document this in setup docs.
Update `DATABASE_URL` in all services to use `${POSTGRES_PASSWORD}` consistently.

### Change 8: Foundry node image propagation

Foundry-built node images inherit from `localhost/master-of-puppets-node:latest`. Any hardening
applied to the base node image automatically propagates — but two things require explicit action
in `foundry_service.py`:

1. **Non-root USER in generated Dockerfiles**: The generated Dockerfile installs additional
   packages (needs `root` during build). `foundry_service.py` must append `USER appuser` as the
   final instruction after all package installs:
   ```python
   # In foundry_service.py, when generating the Dockerfile
   dockerfile_lines.append("USER appuser")
   ```

2. **Hardened node-compose template for Foundry nodes**: The compose file customers use to deploy
   Foundry-built nodes should ship as a hardened template — with `cap_drop`, `security_opt`,
   resource limits, and the socket mount already configured. Ship both:
   - `node-compose.yaml` — Docker socket variant
   - `node-compose.podman.yaml` — Podman socket variant

## Explicitly Out of Scope

- **seccomp profiles** — the node executes arbitrary Bash, Python, and PowerShell. A tight
  seccomp allowlist is impractical across three language runtimes; Docker's default seccomp
  profile is already applied and covers the meaningful kernel-level restrictions. Custom profiles
  would give marginal tightening at high maintenance cost.
- AppArmor/SELinux custom profiles (require host-level config — not in our control)
- Rootless Docker daemon (requires host config changes — not in our control)
- Hardware security modules
- gVisor / Kata Containers (infrastructure-level, not config-level)

## Implementation Order

1. Remove `privileged: true` from node — replace with socket mount + update `runtime.py` auto-detection
2. Strip Podman/iptables/krb5 from `Containerfile.node`
3. Remove Postgres external port binding
4. `cap_drop: ALL` + `security_opt: no-new-privileges` on all services
5. Non-root USER in all Containerfiles (test Docker socket group access, secrets volume ownership)
6. Update `foundry_service.py` to append `USER appuser` in generated Dockerfiles
7. Ship hardened `node-compose.yaml` + `node-compose.podman.yaml` templates
8. Resource limits
9. Remove hardcoded default password

## Tests to Verify

After each change, validate via `mop_validation/scripts/test_local_stack.py`:
- All API endpoints still return expected status codes
- Node enrolment still works (cert generation, heartbeat)
- Job dispatch and execution still complete
- Foundry builds still succeed (Docker socket access)
- EE licence load still works (secrets volume access)
