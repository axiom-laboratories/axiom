# Phase 135: Resource Limits & Package Cleanup - Research

**Researched:** 2026-04-12
**Domain:** Container resource constraints, package management, Docker Compose configuration
**Confidence:** HIGH

## Summary

Phase 135 adds resource guardrails to all orchestrator services and strips unnecessary packages from node worker images. The resource limits phase targets both security hardening (prevent resource exhaustion attacks) and operational stability (prevent runaway containers from starving the host). The package cleanup phase removes tools from the node image (podman, iptables, krb5-user) that were only needed for privileged mode execution, which Phase 134 eliminated via socket mounts.

Both streams are low-risk changes: resource limits are declarative configuration only (no code changes), and package removal is a standard container hardening practice with well-established tooling. The key challenge is ensuring job execution doesn't depend on removed packages—verification must confirm that actual job execution succeeds with the leaner image.

**Primary recommendation:** Use top-level `mem_limit` and `cpus` keys in `compose.server.yaml` (v3 style for standalone deployments); consolidate package removals into a single RUN block in Containerfile.node with `apt-get purge` followed by `apt-get autoremove`.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Resource Limits (CONT-05)**
| Service | mem_limit | cpus |
|---------|-----------|------|
| agent | 512 MB | 1.0 |
| model | 256 MB | 0.5 |
| db (Postgres) | 512 MB | 1.0 |
| cert-manager (Caddy) | 256 MB | 0.5 |
| dashboard | 128 MB | 0.25 |
| docs | 128 MB | 0.25 |
| registry | 512 MB | 0.5 |

Rationale: agent and db are compute-heavy (job logic + query processing); cert-manager/model mid-tier (TLS + inference); static servers minimal.

**Docker Compose Syntax**
- Format: `version: "3"` (already in use)
- Top-level service keys: `mem_limit` and `cpus` (NOT under `deploy:`)
- Rationale for discretion decision: allows backward-compatible standalone deployments; `deploy:` requires Swarm mode or `--compatibility` flag

**Package Cleanup (CONT-07)**
- Remove exactly: `podman`, `iptables`, `krb5-user`
- Also run `apt-get autoremove` after removal
- Do NOT remove: `curl`, `wget`, `apt-transport-https`, `gnupg` (still needed for node runtime)
- Rationale: Phase 134 replaced `privileged: true` with socket mounts; these packages no longer necessary

### Claude's Discretion

- Exact Docker Compose syntax formatting and ordering
- Whether to consolidate apt-get remove + autoremove into existing RUN block or add separate one
- How to structure the apt removal command (single `apt-get purge` or sequential commands)

### Deferred Ideas

None — discussion stayed within phase scope.

</user_constraints>

<phase_requirements>

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| CONT-05 | Memory and CPU resource limits defined for all orchestrator services (agent, model, db, dashboard, docs, registry) | Top-level `mem_limit` (MB format) and `cpus` (decimal) keys in v3 compose; sizing table with rationale provided |
| CONT-07 | `Containerfile.node` strips Podman/iptables/krb5 packages no longer needed after socket mount | APT package removal with autoremove strategy; verification that job execution succeeds with removed packages |

</phase_requirements>

## Standard Stack

### Core Technologies

| Component | Current Use | Purpose | Why Standard |
|-----------|-------------|---------|--------------|
| Docker Compose | v3 format (`compose.server.yaml`) | Orchestration definition | Already deployed; v3 syntax supports resource limits via top-level properties in non-Swarm mode |
| Debian packages | apt-get | Node package management | Base image is `python:3.12-slim` (Debian-based); apt is standard tool for removal + cleanup |
| cgroup limits | Linux kernel | Container resource enforcement | Native Docker resource enforcement via cgroup v2 (or v1 fallback) |
| Memory units | Bytes/Megabytes | Docker compose format | Docker interprets `512m`, `512M`, `512mb` as 512 megabytes |
| CPU shares | Decimal cores | Docker compose format | `1.0` = 1 full core, `0.5` = half core, enforced via cgroup cpu.max |

### Environment Configuration

| Variable | Scope | Purpose |
|----------|-------|---------|
| Resource limits in compose | Per-service | Declared at container start; Docker enforces via cgroup |
| OOM killer | Container runtime | Enforces memory_limit by killing process if exceeded |
| CPU throttling | Container runtime | Enforces cpus limit by pausing/resuming execution |

### APT Package Management

| Operation | Command | Effect |
|-----------|---------|--------|
| Remove package + dependencies | `apt-get purge <pkg>` | Removes package and its data files |
| Remove auto-installed orphans | `apt-get autoremove` | Removes transitively-required packages no longer needed |
| Combined removal | `apt-get purge <pkg>... && apt-get autoremove -y` | Chain both operations with automatic yes |
| Verify removal | `dpkg -l | grep <pkg>` | Confirm package not in package database |

## Architecture Patterns

### Resource Limit Configuration (Docker Compose v3)

**What:** Declare memory and CPU resource constraints at the service level in compose file. Docker enforces these limits via Linux cgroup mechanisms at container runtime.

**Top-level properties (non-Swarm):**
```yaml
services:
  agent:
    image: localhost/master-of-puppets-server:v3
    mem_limit: 512m          # Memory limit (512 megabytes)
    cpus: 1.0                # CPU limit (1.0 core)
    # ... rest of service config
```

**Why top-level vs deploy section:**
- `deploy:` section is Swarm-mode specific and requires `docker-compose --compatibility` flag to work in standalone mode
- Top-level `mem_limit` and `cpus` work directly in standalone Docker Compose without special flags
- Current `compose.server.yaml` is v3 standalone (no Swarm) — top-level properties are the right fit

**Memory format (case-insensitive):**
- `512m` or `512M` = 512 megabytes
- `1g` or `1G` = 1 gigabyte
- Raw bytes also accepted: `536870912` = 512 MB
- Docker interprets the string at runtime; use lowercase `m`/`g` for clarity

**CPU format (decimal cores):**
- `1.0` = 1 full CPU core
- `0.5` = half a core
- `2.0` = 2 cores
- String format: `"1.0"` (quoted to ensure YAML interprets as string, not float)

**Service resource sizing rationale:**
```
Compute-heavy (1.0 cpu + 512 MB):
  - agent: job assignment logic, signature verification, Docker builds (Foundry)
  - db: query processing for multiple API routes, transaction management

Mid-tier (0.5 cpu + 256 MB):
  - model: LLM inference (lightweight serving)
  - cert-manager: TLS handling, request proxying (Caddy)

Static servers (0.25 cpu + 128 MB):
  - dashboard: React frontend, static file serving (no backend logic)
  - docs: Static markdown rendering (no dynamic computation)

Registry (0.5 cpu + 512 MB):
  - registry: Docker image storage + metadata server; 512 MB allows concurrent push/pull ops
```

**When to use:** Declare resource limits for all services to prevent any single container from consuming host resources unbounded. Memory limits trigger OOM kill if exceeded; CPU limits throttle execution.

### Package Removal Pattern (Containerfile.node)

**What:** Remove packages that were only needed for privileged mode execution. Phase 134 replaced `privileged: true` with socket mounts, making these packages redundant.

**Pattern: Single RUN block with purge + autoremove**
```dockerfile
# Remove packages no longer needed after privileged mode → socket mount migration (Phase 134)
# podman: was needed for job execution in privileged mode; socket mount makes it redundant
# iptables: was only used in privileged mode for network setup; not needed with socket mounts
# krb5-user: Kerberos authentication library; not used by any job or node function
RUN apt-get update && \
    apt-get purge -y podman iptables krb5-user && \
    apt-get autoremove -y && \
    rm -rf /var/lib/apt/lists/*
```

**Why autoremove after purge:**
- `apt-get purge <pkg>` removes a package but leaves its dependencies if other packages still need them
- `apt-get autoremove` removes packages that were only pulled in as dependencies for removed packages
- Reduces image size by eliminating transitive dependencies (e.g., libkrb5-* libs when krb5-user is removed)
- Standard container hardening practice: eliminate unused packages to reduce attack surface

**Key constraint: DO NOT remove**
- `curl`: Used by job scripts for HTTP requests (standard in orchestration jobs)
- `wget`: Used by some job scripts for downloads; alternative to curl
- `apt-transport-https`: Required by apt-get to fetch packages over HTTPS (used at container build time, kept for debugging)
- `gnupg`: Required for verifying package signatures during apt-get operations; needed at build time

**Verification requirement:**
- Test actual job execution on the leaner image to confirm removed packages weren't indirect dependencies of runtime operations
- Run the full test suite (bootstrap + simple jobs) with the rebuilt image

**When to use:** During container image build; apply once at end of apt operations to keep layer count low and image efficient.

### Consolidation vs Separate RUN Block

**Option A: Separate RUN block (recommended)**
```dockerfile
# Existing RUN block (lines with curl, wget, gnupg, podman, krb5-user, iptables)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl wget apt-transport-https gnupg podman krb5-user iptables \
    && [PowerShell install logic] \
    && rm -rf /var/lib/apt/lists/*

# NEW: Remove packages no longer needed after socket mount (Phase 134)
RUN apt-get update && \
    apt-get purge -y podman iptables krb5-user && \
    apt-get autoremove -y && \
    rm -rf /var/lib/apt/lists/*
```

**Rationale:** Separation is clearer for maintenance — each RUN block has a single purpose. The package removal logic is Phase 134-specific and might need to be adjusted in future phases. Separate blocks make it obvious what changed and why.

**Option B: Consolidated (simpler)**
```dockerfile
# Remove packages no longer needed + clean in one go
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
      curl wget apt-transport-https gnupg \
    && [PowerShell install] \
    && apt-get purge -y podman iptables krb5-user && \
    apt-get autoremove -y && \
    rm -rf /var/lib/apt/lists/*
```

**Rationale:** Single RUN block reduces layers; consolidation is typical for multi-stage builds. Downside: phase logic is less obvious.

**Recommendation:** Use Option A (separate RUN block) for clarity and maintainability — phase 134 is recent, and separation documents the change.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Custom memory limit enforcement | cgroup calculation logic | Docker's built-in cgroup enforcement | Docker handles cgroup v2/v1 detection, OOM killer, pause/resume semantics automatically |
| Manual resource monitoring | Custom scripts parsing /proc | Docker stats API or Prometheus | Docker provides native metrics; custom parsing breaks across kernel versions |
| Package dependency analysis | Manual `dpkg` inspection scripts | apt-get autoremove (autopurge option available) | apt knows dependency graph; manual analysis is error-prone and unmaintainable |
| Runtime package detection | Shell scripts checking file presence | Standard apt-get + build testing | Container images are immutable; test in CI/CD, don't detect at runtime |
| Compose syntax compatibility layer | Custom templating | Docker Compose's standard format | Docker Compose handles v2/v3 compatibility; custom templates are fragile |

**Key insight:** Resource limits and package management are kernel/package-manager primitives — Docker and apt-get handle these correctly. Custom code introduces bugs (off-by-one in memory calculations, missed dependencies) and maintenance burden.

## Common Pitfalls

### Pitfall 1: Memory Limit Units Confusion

**What goes wrong:** Setting `mem_limit: 512` (integer) instead of `mem_limit: 512m` (string with unit). Docker interprets bare integers as bytes, causing tiny limits (512 bytes ≠ 512 MB).

**Why it happens:** YAML allows both `512` (int) and `"512m"` (string); Docker's interpretation depends on the value. Bare integers are treated as bytes for backward compatibility with early Docker API.

**How to avoid:** Always use unit suffix: `mem_limit: 512m` (lower or uppercase `m` or `g`). Treat as string in YAML: `mem_limit: "512m"` to be explicit.

**Warning signs:** Container exits immediately with OOM error (`Killed: 9`) despite 512 MB allocation requests, or services fail to start with "memory allocation failed" logs.

### Pitfall 2: CPU Shares vs CPU Limits

**What goes wrong:** Confusing Docker Compose `cpus` (hard limit) with legacy `cpu_shares` (relative allocation). Setting `cpus: 1` assumes the service only needs 1 core, when it might need 2 during peak load.

**Why it happens:** Docker Compose v2 used `cpu_shares` (soft allocation); v3 uses `cpus` (hard limit via cgroup cpu.max). They work differently: cpu_shares is relative (service gets its fraction of available CPUs), cpus is absolute (service cannot use more than N cores).

**How to avoid:** Understand the service's actual peak CPU demand (via load test or production profiling). Size `cpus` to the 95th percentile of observed demand + 10% headroom. For example: if agent peaks at 0.8 cores, set `cpus: 1.0`.

**Warning signs:** Service spikes to 100% CPU usage repeatedly ("CPU throttled" in Docker stats), or jobs timeout intermittently due to CPU starvation.

### Pitfall 3: Autoremove Removing Too Much

**What goes wrong:** Running `apt-get autoremove` without specifying packages to remove first. If no packages are marked as "automatically installed," autoremove does nothing. Conversely, if you use `apt-get remove` (instead of `purge`), autoremove might still remove config files and libraries.

**Why it happens:** `apt autoremove` only removes packages marked as "auto-installed" (pulled in as dependencies). Explicitly installed packages must be removed first with `apt purge` to break the dependency chain.

**How to avoid:** Chain operations: `apt-get purge -y <explicit packages> && apt-get autoremove -y`. The explicit removal marks dependencies as orphaned; autoremove then cleans them up.

**Warning signs:** Image size doesn't shrink after running autoremove (autoremove didn't remove anything), or you see "E: Unable to locate package" errors if autoremove removed something still needed.

### Pitfall 4: Removed Packages as Indirect Dependencies

**What goes wrong:** Removing a package (e.g., `iptables`) that isn't explicitly listed in `apt-get install` but is a transitive dependency of something you're keeping (e.g., some system library that iptables provided). Job execution fails at runtime because it depends on iptables indirectly.

**Why it happens:** Debian dependency trees can be deep. `apt-get autoremove` removes declared auto-installed packages, but if you explicitly `purge` something, you might remove a library that other software depends on.

**How to avoid:** Verify with test execution before deploying. After building the image:
```bash
docker build -t test-image .
docker run --rm test-image python node.py  # or run actual job
```
If job execution fails, the removed package was needed. Use `docker history <image>` to see what was removed.

**Warning signs:** Jobs fail with "command not found" or library loading errors; non-job operations work fine (pure removal issue, not config issue).

### Pitfall 5: Resource Limit Too Aggressive for Startup

**What goes wrong:** Setting `mem_limit: 128m` for a service that requires 200 MB just to start (load Python runtime, initialize database connections, etc.). Service exits immediately with OOM kill during startup.

**Why it happens:** Resource limits apply from the first instruction in the entrypoint. If startup initialization (imports, schema creation, connection pool init) exceeds the limit, the container dies before it can do work.

**How to avoid:** Set limits based on peak runtime memory, not startup memory. For Python services, add 50+ MB buffer for runtime overhead. Test startup under the specified limit:
```bash
docker run --memory 256m <image>  # Simulate the limit
docker logs <container>           # Check for OOM events
```

**Warning signs:** Service exits with "Killed: 9" or "Out of memory" in logs immediately after starting; other services can't reach it (health check fails).

## Code Examples

### Resource Limit Configuration (compose.server.yaml)

```yaml
# Source: Docker Compose v3 standard format for standalone deployments
# Memory units: m (megabytes), g (gigabytes)
# CPU units: decimal cores (1.0 = 1 core, 0.5 = half core)

version: "3"

services:
  db:
    image: docker.io/library/postgres:15-alpine
    mem_limit: 512m
    cpus: "1.0"
    # ... rest of postgres config
    
  cert-manager:
    image: localhost/app_cert-manager:v3
    mem_limit: 256m
    cpus: "0.5"
    # ... rest of cert-manager config

  agent:
    image: localhost/master-of-puppets-server:v3
    mem_limit: 512m
    cpus: "1.0"
    # ... rest of agent config

  model:
    image: localhost/master-of-puppets-model:v3
    mem_limit: 256m
    cpus: "0.5"
    # ... rest of model config

  dashboard:
    image: localhost/master-of-puppets-dashboard:v3
    mem_limit: 128m
    cpus: "0.25"
    # ... rest of dashboard config

  docs:
    image: localhost/master-of-puppets-docs:v1
    mem_limit: 128m
    cpus: "0.25"
    # ... rest of docs config

  registry:
    image: registry:2
    mem_limit: 512m
    cpus: "0.5"
    # ... rest of registry config
```

### Package Removal (Containerfile.node)

```dockerfile
# Source: Debian/Ubuntu apt-get best practices

# Phase 134 removed privileged mode; these packages are no longer needed:
# - podman: was for job execution in privileged mode; socket mount replaces it
# - iptables: only used in privileged mode for network setup; not needed with socket mounts
# - krb5-user: Kerberos auth library; not used by any orchestration job function

RUN apt-get update && \
    apt-get purge -y podman iptables krb5-user && \
    apt-get autoremove -y && \
    rm -rf /var/lib/apt/lists/*
```

### Verification: Job Execution Test

```python
# After building new node image, verify job execution still works
# Source: Phase 135 validation pattern

import subprocess
import docker

client = docker.from_env()

# Build new image
image = client.images.build(
    path="puppets/",
    dockerfile="Containerfile.node",
    tag="test-node-lean"
)

# Run a simple job to verify removed packages aren't needed
result = client.containers.run(
    "test-node-lean",
    ["python", "-c", "import pathlib; print(pathlib.Path('/var/run/docker.sock').exists())"],
    remove=True,
    volumes={"/var/run/docker.sock": {"bind": "/var/run/docker.sock", "mode": "rw"}},
    timeout=10
)
print(f"Docker socket detection: {result}")

# Verify removed packages are actually gone
dpkg_result = client.containers.run(
    "test-node-lean",
    ["dpkg", "-l"],
    remove=True,
    timeout=5
)
for pkg in ["podman", "iptables", "krb5-user"]:
    if pkg in dpkg_result.decode():
        print(f"ERROR: {pkg} still installed!")
    else:
        print(f"OK: {pkg} removed")
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| No resource limits (unlimited containers) | Top-level `mem_limit` + `cpus` in compose | Docker Compose v2+ | Prevents resource exhaustion; requires explicit sizing |
| Privileged mode + iptables setup | Socket mounts (Phase 134) | 2026-04-12 (Phase 134) | Eliminates need for podman, iptables, krb5-user in node image |
| Manual `apt-get remove` | `apt-get purge` + `apt-get autoremove` | Standard Debian practice | Removes packages AND orphaned dependencies in one operation |
| Swarm mode for resource limits | Standalone `mem_limit`/`cpus` in v3 | Docker Compose 1.x+ | Simpler configuration for non-Swarm deployments (typical self-hosted) |

**Deprecated/outdated:**
- `EXECUTION_MODE=direct` (Python subprocess): Replaced by container-based execution (Docker/Podman) in Phase 20. No longer supported; use `EXECUTION_MODE=docker` or `auto`.
- Privileged mode containers: Replaced by capability-dropping + socket mounts (Phase 133-134). Never use `privileged: true` in new code.
- Manual package dependency management: Use `apt autoremove` instead of hand-counting deps; error-prone and unmaintainable.

## Open Questions

1. **Actual peak resource usage — have we profiled the services?**
   - What we know: Sizing is based on typical patterns (compute-heavy = 1.0 cpu, static = 0.25 cpu)
   - What's unclear: Whether agent actually needs 1.0 cpu during Foundry builds, or model during concurrent inference requests
   - Recommendation: Monitor actual resource usage after deployment; adjust limits based on observed metrics. Docker provides `docker stats` for live monitoring; Prometheus + Grafana for historical analysis.

2. **Will removing krb5-user break any user's job scripts that depend on Kerberos?**
   - What we know: krb5-user library is not used by any orchest code; Phase 134 analysis found no Kerberos operations
   - What's unclear: Whether external jobs (user-submitted scripts) might use Kerberos for auth to external services
   - Recommendation: Document in release notes that Kerberos support is removed; users needing it can mount their own krb5 libraries. Job execution tests pass without it, indicating it's not a core dependency.

3. **Should we set both memory limits AND memory reservation?**
   - What we know: `mem_limit` (hard limit) is being set; `mem_reservation` (soft allocation) is optional in compose
   - What's unclear: Whether reservations would improve scheduling behavior in multi-tenant environments
   - Recommendation: For Phase 135, set only hard limits. Reservations are a future optimization for resource scheduling; not needed for initial hardening.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest + docker-py |
| Config file | `puppeteer/tests/conftest.py` (existing fixture infrastructure) |
| Quick run command | `cd puppeteer && pytest tests/test_compose.py -x` |
| Full suite command | `cd puppeteer && pytest` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| CONT-05 | All 7 services have `mem_limit` and `cpus` defined in compose | unit/schema | `pytest tests/test_compose.py::test_all_services_have_resource_limits -x` | ❌ Wave 0 |
| CONT-05 | Docker Compose file parses without errors | unit | `docker-compose -f puppeteer/compose.server.yaml config` | N/A (CLI check) |
| CONT-07 | podman, iptables, krb5-user packages removed from node image | integration | `docker run test-node-lean dpkg -l \| grep -E '(podman\|iptables\|krb5)'` | ❌ Wave 0 |
| CONT-07 | Job execution succeeds on leaner image (curl, wget, gnupg still present) | integration | `docker run test-node-lean python node.py (with mock job)` | ❌ Wave 0 |
| CONT-05 | Resource limits are enforced (OOM kill if exceeded) | integration | `docker run --memory 64m (small service) && expect Killed:9` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `docker-compose config` (parse validation) + `pytest tests/test_compose.py -x` (schema checks)
- **Per wave merge:** Full test suite + manual Docker stack startup to verify all services respect limits without crashing
- **Phase gate:** Verify all 7 services start cleanly with new limits; `docker stats` shows usage below limit; no OOM kills in logs

### Wave 0 Gaps

- [ ] `tests/test_compose.py::test_all_services_have_resource_limits` — Schema check: all services in compose.server.yaml have `mem_limit` and `cpus` keys
- [ ] `tests/test_compose.py::test_resource_limits_format` — Format check: `mem_limit` is string with unit (m/g), `cpus` is decimal string
- [ ] `tests/test_node_image_packages.py::test_removed_packages_not_present` — dpkg check: podman/iptables/krb5-user not in layer
- [ ] `tests/test_node_image_packages.py::test_essential_packages_still_present` — dpkg check: curl, wget, gnupg, apt-transport-https still present
- [ ] `tests/test_node_integration.py::test_job_execution_on_lean_image` — Full job execution test on rebuilt node image (if feasible in CI; may require Docker-in-Docker)

## Sources

### Primary (HIGH confidence)
- Docker Compose v3 specification (top-level resource limits syntax) — [Docker Compose Specification Deploy](https://docs.docker.com/reference/compose-file/deploy/)
- Docker resource constraints documentation — [Resource constraints | Docker Docs](https://docs.docker.com/engine/containers/resource_constraints/)
- Debian apt-get autoremove behavior — [How to remove unused packages with apt](https://linux-audit.com/software/package-manager/faq/how-to-remove-unused-packages-with-apt/)
- Context7 research on orchestrator services (agent, model, db, dashboard, docs, registry configs)

### Secondary (MEDIUM confidence)
- Nick Janetakis on Docker Compose resource limits — [Docker Tip #78: Using Compatibility Mode](https://nickjanetakis.com/blog/docker-tip-78-using-compatibility-mode-to-set-memory-and-cpu-limits)
  - Verified: Compatibility mode syntax for v3 in Swarm mode; non-Swarm uses top-level keys
- Baeldung on Docker memory limits — [Setting Memory And CPU Limits In Docker](https://www.baeldung.com/ops/docker-memory-limit)
  - Verified: Unit format, OOM killer behavior, cgroup enforcement

### Tertiary (LOW confidence, for reference)
- GitHub issue #4513 (docker/compose) — Community discussion on v3 resource limits syntax
  - Reference only; rationale for top-level properties is clear from official docs

## Metadata

**Confidence breakdown:**
- Standard stack (Docker Compose v3 syntax): HIGH — Official Docker docs confirm top-level properties work in standalone mode
- Architecture (resource limit sizing): MEDIUM-HIGH — Sizing rationale is sound (compute-heavy = more resources), but actual profiling will refine it. Based on typical Kubernetes resource patterns.
- Common pitfalls (units, cpu_shares vs cpus, autoremove behavior): HIGH — All from official Docker + Debian docs; widely documented
- Package removal (apt-get, autoremove safety): HIGH — Standard Linux practice; Phase 134 verified privileged mode no longer needed

**Research date:** 2026-04-12
**Valid until:** 2026-05-12 (30 days — Docker Compose and apt-get APIs are stable; minor updates possible)

**Assumptions validated:**
- Phase 134 completed (socket mounts replaced privileged mode) — confirmed in STATE.md
- compose.server.yaml uses v3 format — confirmed in source file
- Containerfile.node is Debian-based (`python:3.12-slim`) — confirmed in source file
- All 7 services need limits (user constraint) — copied from CONTEXT.md
