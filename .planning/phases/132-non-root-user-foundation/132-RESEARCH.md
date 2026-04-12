# Phase 132: Non-Root User Foundation - Research

**Researched:** 2026-04-12  
**Domain:** Container security — non-root user implementation and volume ownership  
**Confidence:** HIGH

## Summary

Phase 132 adds non-root user support to all application containers by creating a dedicated `appuser` (UID 1000) in Containerfile.server (Alpine) and Containerfile.node (Debian), setting proper directory ownership with `chown -R appuser:appuser /app`, and switching execution context with `USER appuser`. The phase handles the critical pattern where Docker named volumes mount over image directories: to ensure non-root write access, we must pre-set ownership in the image at build time before the USER directive.

Volume migration from root-based existing containers is not required for Phase 132 (breaking changes accepted per CONTEXT.md). The secrets-data volume will be recreated during validation, inheriting correct ownership from the rebuilt image.

**Primary recommendation:** Implement user creation and directory ownership in both Containerfiles using Alpine's `adduser` (server) and Debian's `useradd` (node), place `chown -R appuser:appuser /app` immediately before `USER appuser` to ensure mounted volumes inherit correct permissions.

---

## Standard Stack

### Core Changes
| File | Action | Purpose | Why Standard |
|------|--------|---------|--------------|
| Containerfile.server | Add `adduser appuser` + `chown /app` + `USER appuser` | Create non-root user in Alpine, set ownership, drop privileges | Container security baseline; aligns with Docker/Kubernetes best practices |
| Containerfile.node | Add `useradd appuser` + `chown /app` + `USER appuser` | Create non-root user in Debian slim, set ownership, drop privileges | Consistent user handling across all orchestrator services |
| compose.server.yaml | No changes required | compose `user:` directive not used; USER in Containerfile is portable | Baked-in USER is more robust than runtime override |

### Installation Patterns

**Alpine (Containerfile.server):**
```bash
RUN adduser appuser
```
Alpine's `adduser` is a shell script wrapper. Without explicit `--uid`, it assigns the next available UID (1000 for the first non-system user). No shell or home directory is created by default, which is appropriate for container workloads.

**Debian (Containerfile.node):**
```bash
RUN useradd -m appuser
```
Debian's `useradd` creates user and home directory (`-m` flag). Without explicit `--uid`, it assigns 1000 as the first non-system user. The home directory (`/home/appuser`) is created but not used by the application.

**Directory Ownership (both):**
```bash
RUN chown -R appuser:appuser /app
```
This ensures the /app directory (and all subdirectories) are owned by appuser:appuser. Critical for mounted volumes: Docker copies the directory tree structure and permissions from the image to new named volumes.

**USER Directive (both):**
```bash
USER appuser
```
Switches the container's execution context. All subsequent RUN commands (if any) and the final CMD execute as appuser. This directive is read into the image, making the user context portable across compose files (no need for runtime `user:` override).

---

## Architecture Patterns

### Recommended Build Order

```dockerfile
# 1. Install system packages as root
RUN apt-get update && apt-get install -y [packages] && rm -rf /var/lib/apt/lists/*

# 2. Copy application code as root
COPY app_code /app/
COPY config /app/config/

# 3. Create user and set ownership before USER directive
RUN useradd appuser
RUN chown -R appuser:appuser /app

# 4. Switch to non-root user (all subsequent operations as appuser)
USER appuser

# 5. Run application (executes as appuser)
CMD ["python", "-u", "app.py"]
```

**Why this order matters:**
- Packages must be installed as root (sudo required for apt/apk)
- Code copy as root (minimal privilege creep)
- User creation and ownership change as root (last privilege-escalated operations)
- USER directive BEFORE any remaining RUN commands (unlikely in these images, but follows best practice)
- CMD runs as appuser (verified in ps output)

### Volume Ownership Resolution

**The challenge:** Docker initializes named volumes with root ownership. If the image's /app directory is also root-owned, the volume inherits root ownership. When the container runs as appuser, write operations fail (permission denied).

**The solution:** Set /app ownership to appuser in the Dockerfile BEFORE the USER directive. When Docker creates a new named volume, it copies the image's directory permissions to the volume. Since /app is already owned by appuser, the volume inherits that ownership.

**Lifecycle:**
1. Build Containerfile → /app owned by appuser:appuser in image layers
2. Container starts → Docker mounts named volume over /app
3. New volume created → Docker copies /app permissions from image → volume is owned by appuser:appuser
4. appuser process writes to /app → succeeds (user owns the volume)

**Existing volumes:** If a volume already exists (from a prior root-run container), the Dockerfile chown does NOT retroactively change the volume's existing ownership. For Phase 132, this is acceptable: existing `secrets-data` will be destroyed and recreated during validation.

### Anti-Patterns to Avoid

- **Runtime `user:` in compose:** Using `user: appuser` in docker-compose.yaml instead of `USER` in Dockerfile. This works for simple cases but is fragile: if the user ID is wrong or the user doesn't exist in the image, startup fails. Baking USER into the image is more portable and verifiable.

- **No chown in Dockerfile:** Creating a user but not setting directory ownership, then relying on runtime entrypoint chown. This is slower and adds complexity; the Dockerfile approach is cleaner and happens once at build time.

- **chown after USER directive:** Placing `chown` after `USER appuser` requires appuser to have sudo or explicit sudo in the RUN command. Unnecessary—chown as root before USER switch is simpler.

- **Not pre-creating /app in image:** If /app doesn't exist in the image and is only created by volume mount, Docker won't set up permissions correctly. Explicitly `WORKDIR /app` or `RUN mkdir -p /app && chown appuser:appuser /app` ensures the directory exists with correct ownership.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Non-root user creation | Custom shell script for user setup | `adduser` (Alpine) / `useradd` (Debian) | Built-in commands handle UID/GID management correctly; custom scripts are brittle and OS-dependent |
| Directory ownership | Manual chown in entrypoint script | Dockerfile `RUN chown` before USER | Declarative and verifiable; happens once at build time; no runtime overhead |
| Verifying file ownership | Parsing `ls -l` output in bash | `stat` command with field format | stat is POSIX and reliable; avoids locale/formatting issues |
| Multi-user or sudo access | Adding appuser to sudo group | Just use appuser (no sudo needed) | Containers should run a single process as a single user; sudo adds complexity and is a security anti-pattern in containers |

---

## Common Pitfalls

### Pitfall 1: Existing Volume Ownership Not Updated

**What goes wrong:** Running Phase 132 changes the Dockerfile to chown /app to appuser, but an existing `secrets-data` volume from a prior root-run container still has root ownership. Container starts, appuser tries to write boot.log, and gets "Permission denied".

**Why it happens:** Docker does NOT re-apply image directory permissions to existing named volumes. The volume is a separate object with its own ownership metadata that persists across container restarts.

**How to avoid:** Either (a) accept that existing volumes must be recreated (acceptable per CONTEXT.md for Phase 132), (b) use a temporary container to `docker run --rm --volume secrets-data:/data alpine chown -R 1000:1000 /data`, or (c) document this as a manual migration step in upgrade runbooks.

**Warning signs:** 
- Test validation fails: `docker exec <agent> stat /app/secrets` shows `uid=0` (root) instead of `uid=1000`
- Container logs show "Permission denied" when writing to /app/secrets
- Volume was created by a prior root-run image

### Pitfall 2: USER Directive Placement

**What goes wrong:** `USER appuser` is placed in the middle of the Dockerfile, before all package installs. Subsequent `RUN apt-get install` commands fail because appuser doesn't have sudo or root.

**Why it happens:** Copy-paste error or misunderstanding of build order.

**How to avoid:** Place `USER appuser` at the VERY END, after all root-privileged operations (package installs, file ownership changes).

**Warning signs:**
- Build fails with "apt-get: command not found" or "permission denied" in RUN steps after USER
- Error: "appuser is not in the sudoers file"

### Pitfall 3: Dockerfile chown Syntax Error

**What goes wrong:** `RUN chown appuser /app` (missing `-R` flag) only changes the directory itself, not its contents. Files inside /app are still owned by root, so appuser can't read/write them.

**Why it happens:** Forgetting `-R` (recursive) flag; testing locally with small /app and not noticing deep directory ownership issues.

**How to avoid:** Always use `chown -R` for application directories. Verify with: `docker exec <container> stat /app/secrets` to check subdirectory ownership.

**Warning signs:**
- `stat /app` shows uid=1000 (directory correct), but `stat /app/secrets/boot.log` shows uid=0 (file wrong)
- Runtime "permission denied" on specific files inside /app

### Pitfall 4: Missing appuser Creation

**What goes wrong:** `USER appuser` directive is added, but the user was never created with `adduser`/`useradd`. Container fails to start with error "unable to find user appuser: no matching entries in passwd file".

**Why it happens:** Removing lines during refactoring, or forgetting to add the user creation step in the first place.

**How to avoid:** Verify each Containerfile has explicit user creation (adduser or useradd) before USER directive. Use `docker run --rm <image> id appuser` to verify the user exists.

**Warning signs:**
- Container fails to start immediately with "unable to find user" error
- `docker exec` commands fail with same error

---

## Code Examples

Verified patterns from Docker and Linux best practices documentation.

### Alpine User Creation + Ownership (Containerfile.server)

```dockerfile
# Containerfile.server — Alpine 3.x
FROM python:3.12-alpine

WORKDIR /app

# Install packages as root
RUN apk add --no-cache gcc musl-dev libffi-dev python3-dev postgresql-dev linux-headers curl tar docker-cli

# Copy code as root
COPY requirements.txt .
COPY agent_service/ agent_service/
COPY model_service/ model_service/

# Create non-root user
RUN adduser appuser

# Set directory ownership (before USER directive)
RUN chown -R appuser:appuser /app

# Switch to non-root user
USER appuser

# Entrypoint runs as appuser
CMD ["python", "-m", "agent_service.main"]
```

**Note:** Alpine's `adduser` is a shell script wrapper around `addgroup` and `adduser` built-ins. It creates a user with UID 1000 by default (first non-system user), no password, no shell. This is idiomatic for Alpine containers.

### Debian User Creation + Ownership (Containerfile.node)

```dockerfile
# Containerfile.node — Debian 13 slim
FROM python:3.12-slim

WORKDIR /app

# Install packages as root
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl wget apt-transport-https gnupg podman krb5-user iptables \
    && rm -rf /var/lib/apt/lists/*

# Copy code as root
COPY requirements.txt .
COPY environment_service/node.py .
COPY environment_service/runtime.py .

# Create non-root user
RUN useradd -m appuser

# Set directory ownership (before USER directive)
RUN chown -R appuser:appuser /app

# Switch to non-root user
USER appuser

# Entrypoint runs as appuser
CMD ["python", "-u", "node.py"]
```

**Note:** Debian's `useradd` is the standard POSIX utility. The `-m` flag creates a home directory (`/home/appuser`), which is harmless for containers though not typically used. Without explicit `--uid`, it assigns UID 1000 (first non-system user).

### Verification Script Pattern

```bash
#!/bin/bash
# Standalone verification — run after docker compose up

echo "=== Checking process UIDs ==="
docker exec puppeteer-agent-1 ps -o uid,comm | grep -E "(UID|python)"
docker exec puppeteer-model-1 ps -o uid,comm | grep -E "(UID|python)"
docker exec node ps -o uid,comm | grep -E "(UID|python)"

echo "=== Checking directory ownership ==="
docker exec puppeteer-agent-1 stat -c "%U:%G %n" /app
docker exec puppeteer-agent-1 stat -c "%U:%G %n" /app/secrets

echo "=== Checking file ownership in secrets volume ==="
docker exec puppeteer-agent-1 find /app/secrets -type f -exec stat -c "%U:%G %n" {} \;
```

**Expected output:**
```
=== Checking process UIDs ===
UID COMM
1000 python
1000 python
1000 python

=== Checking directory ownership ===
appuser:appuser /app
appuser:appuser /app/secrets

=== Checking file ownership in secrets volume ===
appuser:appuser /app/secrets/boot.log
appuser:appuser /app/secrets/licence.key
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Containers running as root (UID 0) | Non-root appuser (UID 1000) by default | 2024–2025 industry standardization | Reduces blast radius of container escape; aligns with Kubernetes Pod Security Standards |
| Runtime `user:` override in compose | User baked into Dockerfile with USER directive | 2023+ Docker/Compose best practices | More portable; verifiable at build time; no runtime surprises |
| Manual entrypoint chown for volumes | Dockerfile chown before USER | Contemporary container patterns | Simpler; happens once at build; no runtime overhead |
| No documentation of user context | Explicit USER directive with clear rationale | 2025 security baseline | Operators can verify process UID at a glance |

**Deprecated/outdated:**
- Running containers with `--user=0` or `privileged: true` without explicit justification (Phase 134 addresses this)
- Assuming `chown` in entrypoint scripts handles volume ownership (it doesn't for existing volumes)

---

## Open Questions

1. **Non-system UID enforcement:** Phase 132 CONTEXT.md notes "no explicit --uid 1000... OS will assign 1000 by default." This is true for Alpine and Debian, but is this assumption validated across all base images used in the stack?
   - What we know: Alpine python:3.12-alpine and Debian python:3.12-slim both assign UID 1000 to the first non-system user
   - What's unclear: If base images change (e.g., if a future phase uses a different Python base), will the default UID still be 1000?
   - Recommendation: Document the UID 1000 assumption in CONTEXT.md or add explicit `adduser -u 1000` / `useradd -u 1000` if guaranteed UID is required. For Phase 132, accept the default and document it.

2. **Volume migration entrypoint for existing deployments:** The phase accepts breaking changes, but should upgrade docs mention a migration step for operators with existing containers?
   - What we know: Existing volumes won't automatically update ownership; this breaks existing root-run containers
   - What's unclear: Is there a documented upgrade path in docs/?
   - Recommendation: Add a note to upgrade.md: "Secrets volume will be recreated during upgrade; no manual migration needed for new deployments."

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (backend) + Docker compose (integration) |
| Config file | `pyproject.toml` at repo root (pytest.ini_options); `compose.server.yaml` + `node-compose.yaml` for Docker |
| Quick run command | `cd puppeteer && pytest agent_service/tests/ -v` (~5 seconds) |
| Full suite command | `cd puppeteer && pytest agent_service/tests/ && cd .. && docker compose -f puppeteer/compose.server.yaml up -d && docker compose -f puppets/node-compose.yaml up -d && bash verify_nonroot.sh` (Docker full stack + verification ~60 seconds) |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| CONT-01 | Process UID is 1000 (ps -o uid) | integration | `docker exec puppeteer-agent-1 ps -o uid=,comm= \| grep python \| awk '{print $1}'` → expect "1000" | ❌ Wave 0 |
| CONT-01 | Directory /app owned by uid 1000 (stat) | integration | `docker exec puppeteer-agent-1 stat -c %U /app` → expect "appuser" | ❌ Wave 0 |
| CONT-01 | Subdirectory /app/secrets owned by uid 1000 | integration | `docker exec puppeteer-agent-1 stat -c %U /app/secrets` → expect "appuser" | ❌ Wave 0 |
| CONT-06 | Secrets volume readable/writable by appuser | integration | `docker exec puppeteer-agent-1 touch /app/secrets/test.txt && rm /app/secrets/test.txt` → exit 0 | ❌ Wave 0 |
| CONT-01 | Node process UID is 1000 | integration | `docker exec node ps -o uid=,comm= \| grep python \| awk '{print $1}'` → expect "1000" | ❌ Wave 0 |
| CONT-01 | Model service process UID is 1000 | integration | `docker exec puppeteer-model-1 ps -o uid=,comm= \| awk '{print $1}'` → expect "1000" | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `pytest puppeteer/agent_service/tests/ -v` (fast unit tests; verifies no regressions in auth/user model logic)
- **Per wave merge:** Full Docker stack validation (see Wave 0 gaps below) with verification script
- **Phase gate:** All 6 integration checks green before `/gsd:verify-work`

### Wave 0 Gaps

- [ ] `verify_nonroot.sh` — standalone verification script; checks process UIDs + directory ownership + volume write access
  - Script command: `docker exec <container> ps -o uid,comm` (assert uid=1000 for python processes)
  - Script command: `docker exec <container> stat -c %U:%G /app` (assert appuser:appuser ownership)
  - Script command: `docker exec <container> stat -c %U:%G /app/secrets` (assert appuser:appuser ownership)
  - Must run after `docker compose up` on both compose.server.yaml and node-compose.yaml
- [ ] `puppeteer/agent_service/tests/test_nonroot_permissions.py` — unit test verifying /app directory ownership in built image
  - Test: `docker run --rm <image> stat -c %U:%G /app` → parse uid and expect 1000 or "appuser"
  - Test: `docker run --rm <image> find /app -type f -exec stat -c %U:%G {} \;` → expect all appuser:appuser (or spot-check key paths)
  - Rationale: Portable across Docker/Podman; verifies Dockerfile correctness independently of runtime

*(Gaps summary: Two new validation layers needed — integration (compose-based verification script) and unit (image-level verification). Existing pytest infrastructure is sufficient; no new framework setup required.)*

---

## Sources

### Primary (HIGH confidence)
- [Docker USER Instruction documentation](https://www.docker.com/blog/understanding-the-docker-user-instruction/) — official Docker guidance on USER directive and container user context
- [Nick Janetakis: Running Docker Containers as Non-Root with Custom UID/GID](https://nickjanetakis.com/blog/running-docker-containers-as-a-non-root-user-with-a-custom-uid-and-gid) — authoritative reference on UID/GID handling and volume permissions
- [VS Code Remote Containers: Add Non-Root User](https://code.visualstudio.com/remote/advancedcontainers/add-nonroot-user) — official Microsoft guidance on container user patterns
- [Alpine Linux Wiki: Setting Up a New User](https://wiki.alpinelinux.org/wiki/Setting_up_a_new_user) — official Alpine documentation for `adduser` / `addgroup`
- Project codebase: `puppeteer/Containerfile.server`, `puppets/Containerfile.node`, `puppeteer/compose.server.yaml` (current state confirmed via direct inspection)

### Secondary (MEDIUM confidence)
- [Pratik Chowdhury: Docker Compose Named Volumes as Non-Root](https://pratikpc.medium.com/use-docker-compose-named-volumes-as-non-root-within-your-containers-1911eb30f731) — detailed analysis of Docker volume initialization and ownership inheritance; verified against official Docker behavior documentation
- [Docker Community Forums: Volume Ownership Issues](https://forums.docker.com/t/how-to-mount-a-docker-volume-so-as-writeable-by-a-non-root-user-within-the-container/144321) — real-world scenarios and solutions; cross-verified with official Docker docs
- [Oneuptime Blog: Docker Container User Permissions (2026-01-25)](https://oneuptime.com/blog/post/2026-01-25-docker-container-user-permissions/view) — contemporary best practices for 2026

### Tertiary (LOW confidence, marked for validation)
- GitHub Issues (moby/moby #3124, #45919; docker/for-mac #6734) — community reports of volume ownership behavior; useful for understanding edge cases but not official specification

---

## Metadata

**Confidence breakdown:**
- Standard stack (user creation + chown + USER directive): **HIGH** — verified against official Docker docs and confirmed in codebase inspection
- Architecture patterns (volume ownership inheritance): **MEDIUM** — cross-verified across multiple authoritative sources; some edge cases (existing volumes) documented but not fully tested at validation time
- Pitfalls and common errors: **HIGH** — well-documented in Docker community and reflected in project structure (persistent secrets-data volume that must be migrated)
- Validation approach: **MEDIUM** — Docker integration tests are straightforward, but test coverage for non-root scenarios not yet in place (Wave 0 gap)

**Research date:** 2026-04-12  
**Valid until:** 2026-05-12 (30 days for stable container patterns; Docker USER directive and volume ownership behavior is mature and unlikely to change)

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **User creation approach:** Add `appuser` via `adduser appuser` (Alpine) / `useradd appuser` (Debian) in each Containerfile
- **No explicit UID assignment:** Do NOT use `--uid 1000`; OS will assign 1000 by default as the first non-system user
- **Directory ownership:** Use `RUN chown -R appuser:appuser /app` in each Containerfile before the `USER` directive
- **USER directive placement:** Bake `USER appuser` into Dockerfile, not in compose `user:` field
- **Container scope:** Modify `Containerfile.server` (both agent and model services) and `Containerfile.node`
- **Out of scope for Phase 132:** cert-manager (Caddy manages its own user), dashboard (nginx:alpine already non-root), Podman/iptables/krb5 package removal (Phase 135), socket-based execution (Phase 134)
- **Volume migration:** No migration script or entrypoint chown logic; accept breaking changes (single local deployment); secrets-data volume will be recreated during validation

### Claude's Discretion
- Exact `adduser` flags beyond the user name (shell, home dir, etc.)
- Order of RUN layers in the Dockerfile (as long as packages installed before USER, ownership set before USER)

### Deferred Ideas (OUT OF SCOPE)
- Host-path directories for ephemeral containers (Phase 134)
- Removing Podman/iptables/krb5 (Phase 135)
- Dropping capabilities and no-new-privileges (Phase 133)
- Removing `privileged: true` from node-compose (Phase 134)

</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| CONT-01 | All services run as non-root appuser (UID 1000) with correct ownership of app directories and mounted volumes | Containerfile patterns documented; USER directive + chown RUN precedent established; Docker volume ownership inheritance explained |
| CONT-06 | Secrets volume ownership migrates correctly when upgrading from root-based containers to non-root | Volume ownership lifecycle clarified; breaking change acceptable per CONTEXT; recreation strategy documented |

</phase_requirements>
