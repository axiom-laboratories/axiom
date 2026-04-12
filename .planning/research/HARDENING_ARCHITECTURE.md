# Architecture: Container Security Hardening + EE Licence Protection

**Project:** Axiom (Master of Puppets)
**Phase:** 130+ — Dual hardening initiatives (container security + EE licence protection)
**Researched:** 2026-04-12
**Confidence:** MEDIUM-HIGH — codebase inspection + 2026 hardening best practices verified

---

## Executive Summary

Two security workstreams integrate with the existing Axiom architecture: **(1) container hardening** transitions control plane (puppeteer) and worker nodes (puppets) from root execution to non-root users, dropping Linux capabilities, and restricting privileged operations; **(2) EE licence protection** hardens wheel manifest verification, entry point whitelisting, and boot log integrity via HMAC-keyed timestamps.

**Three critical integration points exist:**

1. **Docker socket group membership** for non-root `appuser` to access `/var/run/docker.sock` in foundry_service.py
2. **Secrets volume ownership migration** from root:root to appuser:appuser during upgrade (boot.log, licence.key files)
3. **ENCRYPTION_KEY availability** for boot.log HMAC signing (existing env var, now required for EE)

Build order must respect dependencies: foundry non-root changes before CAP_DROP enforcement; boot.log HMAC before secrets migration; wheel signing infrastructure before EE wheel loading validates entry points. **All changes are implementation-safe independently for fresh Docker deployments** but require **coordinated database migrations + operator runbook steps** for PostgreSQL production upgrades.

---

## Current Baseline Architecture

### Puppeteer Control Plane (v21.0)

```
Containerfile.server
├── Base: python:3.12-alpine
├── User: root (implicit)
├── Capabilities: ALL
├── Volumes (compose.server.yaml):
│   ├── /var/run/docker.sock:/var/run/docker.sock (RW)
│   ├── /app/puppets:/app/puppets:ro (Foundry context)
│   └── secrets-data:/app/secrets (boot.log, licence.key)
├── Services:
│   ├── Agent (8001): FastAPI, foundry_service.py
│   └── Model (8000): uvicorn, no filesystem ops
└── Key Files:
    ├── agent_service/services/foundry_service.py → docker build via socket
    ├── agent_service/services/licence_service.py → reads AXIOM_LICENCE_KEY, detects clock rollback
    └── agent_service/ee/__init__.py → loads EE wheels, mounts stub routers
```

**Permission Model:** Root user → unrestricted socket access, unrestricted file writes, all Linux capabilities.

### Puppet Nodes (v21.0)

```
Containerfile.node
├── Base: python:3.12-slim
├── Deps: curl wget podman krb5-user iptables (+ docker CLI)
├── User: root (implicit)
├── Capabilities: ALL (usually, privileged:true in compose)
├── Volumes (node-compose.yaml):
│   ├── ./secrets:/app/secrets (enrollment keys, certificates)
│   └── /var/run/docker.sock:/var/run/docker.sock (DinD)
├── Services:
│   └── environment_service/node.py → polls /work/pull, executes jobs
└── Key Files:
    └── environment_service/runtime.py → auto-detects docker/podman, runs job containers
```

**Permission Model:** Root + privileged flag → can execute privileged operations, attach to host resources.

### Shared Secrets Volume

```
secrets-data/
├── boot.log          (hash-chained clock rollback log, current: root-owned)
├── licence.key       (EdDSA JWT, current: root-owned)
├── root_ca.crt       (mTLS Root CA, created at init)
└── [node certs]      (enrolled node client certs)
```

**Current Ownership:** Typically `root:root` with `0755` permissions (created by root container on first startup).

---

## Hardening Target Architecture

### Non-Root User Introduction

```
Containerfile.server (Hardened)
├── Base: python:3.12-alpine
├── User: appuser (UID 1000, GID 1000)
├── Docker Group: docker (GID 997, added to appuser supplementary groups)
├── Capabilities: CAP_NET_BIND_SERVICE (+ CAP_SYS_ADMIN for Podman if needed)
├── Dropped: ALL except above
├── File Ownership: appuser:appuser for /app/secrets, /app/*
└── Validation:
    ├── docker group membership allows socket access
    ├── secrets directory readable/writable
    └── Foundry builds succeed (docker build via socket)

Containerfile.node (Hardened)
├── Base: python:3.12-slim
├── User: nodeuser (UID 1001, GID 1001)
├── Capabilities: CAP_NET_BIND_SERVICE only
├── Dropped: CAP_SYS_ADMIN, CAP_SYS_PTRACE, etc. (jobs run in isolated containers)
├── Optional Changes:
│   └── Drop podman/krb5 if non-critical for your use cases
└── Job Isolation: Jobs still execute in ephemeral containers as root (boundary preserved)
```

### Secrets Volume Ownership Migration

```
Before Upgrade:
└── secrets-data/ owned by root:root

During Upgrade:
├── Step 1: Detect ownership mismatch in main.py lifespan
├── Step 2: chown -R 1000:1000 /app/secrets (auto via init container or startup script)
└── Step 3: Validate new entries (boot.log) written by appuser

After Upgrade:
└── secrets-data/ owned by appuser:appuser
    ├── boot.log continues to accept SHA256 legacy + new HMAC entries
    ├── licence.key read by appuser
    └── All new writes by appuser
```

### Boot Log Integrity Enhancement

```
Current (v21.0):
├── Format: <SHA256_hex> <ISO8601_timestamp>
├── Signing: None (hash-chain only, SHA256 vulnerable to precomputation)
└── Rollback Detection: Lexicographic timestamp comparison

Hardened:
├── Format: <HMAC-SHA256_hex> <ISO8601_timestamp>
├── Signing: HMAC-SHA256 with ENCRYPTION_KEY (same key as Fernet secrets encryption)
├── Rollback Detection: Strict timestamp verification (millisecond precision optional)
├── Backward Compatibility: Existing SHA256 entries validate, new entries use HMAC
└── Enforcement: Strict (raises RuntimeError) for EE licences; warning only for CE
```

---

## Integration Point 1: Docker Socket Group Membership

### Problem Statement

After switching Containerfile.server to non-root `appuser`, the user cannot directly read/write `/var/run/docker.sock` (owned by `root:docker` with mode `0660` on the host). foundry_service.py calls:

```python
docker.DockerClient(base_url="unix:///var/run/docker.sock")
```

This fails with **Permission denied** unless `appuser` is in the `docker` group.

### Current Implementation

```bash
# In Containerfile.server (v21.0)
USER root  # Default; can access anything
# (socket mounted in compose.server.yaml as-is)
```

### Hardening Implementation

**Containerfile.server changes:**

```dockerfile
# After installing base packages, before copying app code:
RUN apk add --no-cache shadow  # groupadd, useradd in Alpine

# Create appuser with docker group membership
RUN groupadd -g 997 docker || true  # May already exist from host
RUN useradd -u 1000 -g 1000 -G docker -s /sbin/nologin appuser

# Fix secrets directory ownership
RUN mkdir -p /app/secrets && chown -R appuser:appuser /app/secrets

# Verify docker group membership
RUN id appuser | grep -q docker || (echo "WARNING: docker group not added"; exit 1)

# Switch to non-root user
USER appuser
```

**Validation Steps:**

1. **Fresh deployment** → automatic (appuser created with docker group)
2. **Existing deployment** → requires manual `docker exec -u root agent gpasswd -a appuser docker` OR rely on docker group GID consistency (997 standard)

**foundry_service.py diagnostic logging** (no logic change):

```python
import stat, grp, os

def log_docker_socket_access():
    sock_path = "/var/run/docker.sock"
    if os.path.exists(sock_path):
        stat_info = os.stat(sock_path)
        gid = stat_info.st_gid
        try:
            group_name = grp.getgrgid(gid).gr_name
            logger.info(f"Docker socket at {sock_path}: owner={stat_info.st_uid}, group={group_name}({gid}), mode={oct(stat.S_IMODE(stat_info.st_mode))}")
        except KeyError:
            logger.warning(f"Docker socket group GID {gid} not in system groups")
    else:
        logger.error(f"Docker socket not found at {sock_path}")

# Call during init_logging or main startup
log_docker_socket_access()
```

**Risk Assessment:**
- **Severity:** HIGH — if appuser not in docker group, foundry_service.py hangs on first build attempt
- **Detection:** Immediate (first Foundry build fails)
- **Mitigation:** Test `docker exec agent docker ps` immediately after Containerfile deploy; document diagnostic in runbook

### Integration Dependencies

- **Blocks:** All subsequent container hardening (CAP_DROP, read-only filesystems)
- **Blocked by:** None
- **Parallel:** Can develop alongside licence protection (orthogonal)

---

## Integration Point 2: Secrets Volume Ownership Migration

### Problem Statement

Existing deployments created `secrets-data` volume with root ownership (root container runs as UID 0). When switching to non-root `appuser` (UID 1000), the agent can no longer write `boot.log` or read `licence.key`.

```bash
# Before upgrade (existing deployment)
docker exec agent ls -ld /app/secrets
# drwxr-xr-x root root /app/secrets

# After switching to appuser in Containerfile
docker compose up -d agent
docker logs agent
# PermissionError: [Errno 13] Permission denied: '/app/secrets/boot.log'
```

### Migration Strategy

**Three approaches:**

#### Approach A: Init Container (Recommended for compose.server.yaml)

```yaml
services:
  init:
    image: alpine:latest
    user: root
    command: ["sh", "-c", "[ -d /app/secrets ] && chown -R 1000:1000 /app/secrets; exit 0"]
    volumes:
      - secrets-data:/app/secrets
    depends_on:
      - agent  # Ensure volume is created by agent first
```

**Pros:** Clean, explicit, runs before agent starts.
**Cons:** Extra container in compose file; requires ordering logic.

#### Approach B: Startup Script in main.py (Recommended for robustness)

```python
# In puppeteer/agent_service/main.py lifespan startup

async def lifespan(app: FastAPI):
    # ... existing startup code ...
    
    # Fix secrets volume ownership if needed (upgrade from root to appuser)
    secrets_dir = Path("secrets")
    if secrets_dir.exists():
        try:
            stat_info = secrets_dir.stat()
            appuser_uid = 1000
            appuser_gid = 1000
            
            if stat_info.st_uid != appuser_uid or stat_info.st_gid != appuser_gid:
                logger.warning(f"Secrets directory owned by UID {stat_info.st_uid}, GID {stat_info.st_gid} — upgrading to appuser ({appuser_uid}:{appuser_gid})")
                
                # Attempt automatic chown (only works if container has CAP_CHOWN or runs as root)
                try:
                    os.chown(secrets_dir, appuser_uid, appuser_gid)
                    for item in secrets_dir.rglob("*"):
                        os.chown(item, appuser_uid, appuser_gid)
                    logger.info("Secrets directory ownership fixed successfully")
                except (PermissionError, OSError) as e:
                    logger.error(f"Automatic chown failed: {e}")
                    logger.error("MANUAL FIX REQUIRED: docker exec -u root agent chown -R 1000:1000 /app/secrets")
                    # Continue anyway; app may fail on boot.log write, which is more obvious than startup hang
        except OSError as e:
            logger.warning(f"Could not stat secrets directory: {e}")
    
    # ... rest of startup ...
```

**Pros:** Single point of truth; retries on failure; clear logging.
**Cons:** Relies on CAP_CHOWN or root execution (works during upgrade phase when root still running).

#### Approach C: Operator Manual Step (Runbook)

```bash
# Before upgrading agent image:
docker exec -u root $(docker compose ps -q agent) chown -R 1000:1000 /app/secrets
docker compose build agent
docker compose up -d agent
```

**Pros:** Explicit, operator control.
**Cons:** Easy to forget; not automated.

### Recommended Approach: B + C (Startup Script + Runbook)

- **Automatic:** Startup script attempts chown during upgrade (covers most cases)
- **Documented:** Runbook provides manual step if automatic fails (CAP_CHOWN dropped)
- **Logging:** Clear error messages guide operator action
- **Validation:** `docker logs agent | grep -i secrets` shows migration status

### Backward Compatibility: Boot Log Format

Boot.log entries created before upgrade will use SHA256 hashing. New entries (post-upgrade) will use HMAC. The `check_and_record_boot()` function must accept both:

```python
def _verify_boot_entry(line: str) -> bool:
    """Accept SHA256 hash (pre-v22.0) or HMAC (post-v22.0)."""
    parts = line.split(" ", 1)
    hash_or_hmac = parts[0]
    ts = parts[1] if len(parts) > 1 else ""
    
    # Try HMAC verification if key available
    if BOOT_LOG_HMAC_KEY and len(hash_or_hmac) == 64:
        try:
            expected_hmac = _compute_hmac_for_entry(ts)
            return hash_or_hmac == expected_hmac
        except Exception:
            pass
    
    # Fall back to SHA256 (legacy)
    try:
        expected_sha256 = _compute_hash_for_entry(ts)
        return hash_or_hmac == expected_sha256
    except Exception:
        pass
    
    return False
```

### Risk Assessment

- **Severity:** MEDIUM — if chown fails and CAP_CHOWN is dropped, agent cannot write boot.log → licence validation fails → startup hangs
- **Detection:** Clear in startup logs; operator must run manual chown
- **Mitigation:** Startup script + runbook; validation test suite

### Integration Dependencies

- **Blocks:** CAP_DROP enforcement (must verify secrets ownership before dropping CAP_CHOWN)
- **Blocked by:** Containerfile.server appuser introduction (requires chown target)
- **Parallel:** Can test separately; requires coordination with main.py changes

---

## Integration Point 3: ENCRYPTION_KEY for Boot Log HMAC

### Problem Statement

Boot log integrity enhancement uses HMAC-SHA256 with a symmetric key. The existing `ENCRYPTION_KEY` env var (used for Fernet DB secrets) is reused here. If ENCRYPTION_KEY is absent in production EE deployment, boot.log entries fall back to plain SHA256 (weaker security posture).

### Current Boot Log Implementation (v21.0)

```python
# licence_service.py
def _compute_hash(prev_hash_hex: str, iso_ts: str) -> str:
    """SHA256 chain (no HMAC)."""
    return hashlib.sha256(f"{prev_hash_hex}{iso_ts}".encode()).hexdigest()

def check_and_record_boot(licence_status: LicenceStatus = LicenceStatus.CE) -> bool:
    # ... read last hash from boot.log ...
    new_hash = _compute_hash(last_hash, now_ts)
    # ... append to boot.log ...
```

**Limitation:** SHA256 chain is vulnerable to precomputation attacks if an attacker observes two entries and can compute a collision.

### Hardening Implementation

```python
# licence_service.py (post-v22.0)

import hmac
import os

# Module-level HMAC key (loaded from ENCRYPTION_KEY env var)
BOOT_LOG_HMAC_KEY: Optional[bytes] = None

def _init_hmac_key():
    """Initialize HMAC key from ENCRYPTION_KEY env var."""
    global BOOT_LOG_HMAC_KEY
    key_str = os.getenv("ENCRYPTION_KEY", "").strip()
    if key_str:
        # Assume ENCRYPTION_KEY is a base64-encoded Fernet key (44 chars)
        # or raw 32-byte symmetric key
        try:
            BOOT_LOG_HMAC_KEY = key_str.encode()
            logger.info("Boot log HMAC enabled (ENCRYPTION_KEY found)")
        except Exception as e:
            logger.warning(f"Failed to parse ENCRYPTION_KEY for HMAC: {e}")
    else:
        logger.warning("ENCRYPTION_KEY not set — boot log HMAC disabled (CE mode acceptable)")

def _compute_hmac_for_entry(prev_hmac_hex: str, iso_ts: str) -> str:
    """HMAC-SHA256 with ENCRYPTION_KEY."""
    if not BOOT_LOG_HMAC_KEY:
        return _compute_hash(prev_hmac_hex, iso_ts)  # Fallback to SHA256
    msg = f"{prev_hmac_hex}{iso_ts}".encode()
    return hmac.new(BOOT_LOG_HMAC_KEY, msg, hashlib.sha256).hexdigest()

def check_and_record_boot(licence_status: LicenceStatus = LicenceStatus.CE) -> bool:
    """Updated to use HMAC if key available; fallback to SHA256 for legacy entries."""
    strict_clock = licence_status != LicenceStatus.CE
    now_ts = datetime.now(timezone.utc).isoformat()
    
    BOOT_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    
    # Genesis case
    if not BOOT_LOG_PATH.exists() or BOOT_LOG_PATH.stat().st_size == 0:
        new_hash = _compute_hmac_for_entry("", now_ts)
        BOOT_LOG_PATH.write_text(f"{new_hash} {now_ts}\n")
        logger.info(f"Boot log initialized with {'HMAC' if BOOT_LOG_HMAC_KEY else 'SHA256'} entry")
        return True
    
    # ... existing clock rollback detection, but now verifying HMAC or SHA256 ...
    lines = BOOT_LOG_PATH.read_text().strip().splitlines()
    last_line = lines[-1]
    parts = last_line.split(" ", 1)
    last_hash = parts[0]
    last_ts = parts[1] if len(parts) > 1 else ""
    
    rollback_detected = last_ts > now_ts
    
    # Compute new entry (may be HMAC if key available)
    new_hash = _compute_hmac_for_entry(last_hash, now_ts)
    lines.append(f"{new_hash} {now_ts}")
    
    # Truncate to last 1000 lines
    if len(lines) > 1000:
        lines = lines[-1000:]
    
    BOOT_LOG_PATH.write_text("\n".join(lines) + "\n")
    
    if rollback_detected:
        msg = f"Clock rollback detected — last boot at {last_ts}, now {now_ts}"
        if strict_clock:
            raise RuntimeError(msg)
        logger.warning(msg)
        return False
    
    return True
```

### Validation in main.py Lifespan

```python
# puppeteer/agent_service/main.py

async def lifespan(app: FastAPI):
    # Initialize HMAC key from ENCRYPTION_KEY
    from .services import licence_service
    licence_service._init_hmac_key()
    
    # Load licence and check boot log
    licence = load_licence()
    
    if licence.is_ee_active and not licence_service.BOOT_LOG_HMAC_KEY:
        logger.warning("EE licence active but ENCRYPTION_KEY not set — boot log HMAC disabled")
        logger.warning("For production EE deployments, set ENCRYPTION_KEY env var")
    
    try:
        check_and_record_boot(licence.status)
    except RuntimeError as e:
        if licence.is_ee_active:
            logger.error(f"Boot log validation failed in EE mode: {e}")
            raise  # Strict for EE
        else:
            logger.warning(f"Boot log validation warning in CE mode: {e}")
            # Continue in CE
```

### Env Var Requirements

**compose.server.yaml:**
```yaml
agent:
  environment:
    - ENCRYPTION_KEY=${ENCRYPTION_KEY}  # Required for production EE
    - AXIOM_LICENCE_KEY=${AXIOM_LICENCE_KEY}
```

**Deployment guide:**
```bash
# Generate random ENCRYPTION_KEY if not present
export ENCRYPTION_KEY=$(python -c "import secrets; print(secrets.token_urlsafe(32))")
docker compose -f compose.server.yaml up -d agent
```

### Risk Assessment

- **Severity:** LOW (CE mode acceptable without ENCRYPTION_KEY; EE deployments must set it)
- **Detection:** Startup logs show "ENCRYPTION_KEY not set" warning
- **Mitigation:** Document as **required for EE**; CI gate validates it's set in production builds

### Integration Dependencies

- **Blocks:** None (orthogonal to container hardening)
- **Blocked by:** None
- **Parallel:** Develop independently; test with/without ENCRYPTION_KEY

---

## New vs. Modified Files

### Container Hardening

| File | Change | Type | Scope |
|------|--------|------|-------|
| `puppeteer/Containerfile.server` | Add appuser (UID 1000), docker group, chown secrets | Modified | Image build |
| `puppeteer/compose.server.yaml` | Add init container for chown, CAP_DROP/CAP_ADD, resource limits, Postgres port binding changes | Modified | Deployment |
| `puppeteer/agent_service/main.py` | Add secrets chown + ENCRYPTION_KEY validation in lifespan | Modified | Startup |
| `puppeteer/agent_service/services/foundry_service.py` | Add docker socket group diagnostic logging | Modified | Foundry |
| `puppets/Containerfile.node` | Add nodeuser (UID 1001), drop podman/krb5 (optional), CAP_DROP | Modified | Image build |
| `puppets/node-compose.yaml` | Remove privileged:true, add CAP_DROP, add socket mount read-only flag | Modified | Deployment |
| `puppets/environment_service/runtime.py` | Add `/run/podman/podman.sock` detection for Podman | Minor | Socket detection |

### EE Licence Protection

| File | Change | Type | Scope |
|------|--------|------|-------|
| `puppeteer/agent_service/services/licence_service.py` | Add HMAC boot.log signing, backward-compat with SHA256 | Modified | Licence validation |
| `puppeteer/agent_service/ee/__init__.py` | Add entry point whitelist validation on EE wheel load | Modified | EE plugin loading |
| `axiom-licenses/tools/sign_wheels.py` | **New:** Script to sign wheels, embed MANIFEST verification | New | Release tooling |
| `puppeteer/migration_v53.sql` | **New:** Placeholder migration (actual fix is runtime chown) | New | Upgrade marker |

**Summary:**
- **Container hardening:** 7 files modified, 0 new
- **EE licence protection:** 2 files modified, 2 new
- **Shared:** main.py (startup validation), compose.server.yaml (hardening infrastructure)

---

## Build Order & Dependency Chain

### Phase A: Foundation (Prerequisite for All)

**Goal:** Establish non-root execution + secrets ownership.

1. **Containerfile.server update** — Add appuser, docker group, mkdir/chown secrets
   - **Test:** `docker compose build agent && docker run --rm localhost/master-of-puppets-server:v3 id` → UID 1000
   - **Blocker for:** All subsequent changes

2. **main.py lifespan update** — Add secrets chown + ENCRYPTION_KEY validation
   - **Test:** Run fresh + upgrade scenario; logs show "Secrets directory ownership fixed"
   - **Blocker for:** CAP_DROP (must verify secrets ownership before dropping CAP_CHOWN)

3. **compose.server.yaml update** — Add init container, CAP_DROP, resource limits
   - **Test:** Fresh deployment creates secrets-data with appuser ownership; CAP_* in `docker exec agent grep Cap /proc/self/status`
   - **Blocker for:** Node hardening coordination

### Phase B: Node Hardening (Parallel to A, but Depends on A for Coordination)

**Goal:** Non-root execution on worker nodes.

4. **Containerfile.node update** — Add nodeuser, drop podman/krb5 (optional), CAP_DROP
   - **Test:** Node enrolls, shows HEALTHY status, can pull jobs
   - **Validation:** `docker logs node | grep -i cap` shows dropped capabilities

5. **node-compose.yaml update** — Remove privileged:true, add CAP_DROP
   - **Test:** Jobs execute successfully in ephemeral containers; no escalation warnings

6. **runtime.py update** (minor) — Add Podman socket path detection
   - **Test:** Mixed Docker/Podman deployments both work

### Phase C: Licence Protection (Parallel to A+B, Orthogonal)

**Goal:** EE wheel integrity + boot.log HMAC.

7. **licence_service.py update** — Add HMAC signing, backward-compat
   - **Test:** Fresh boot.log uses HMAC; legacy entries accept SHA256; rollback detection works
   - **Blocker for:** EE release workflow

8. **sign_wheels.py (new tool)** — Release tool for signing wheels
   - **Test:** Generated wheel passes manifest + entry point verification
   - **Blocker for:** EE release CI/CD

9. **ee/__init__.py update** — Entry point whitelist validation
   - **Test:** Valid EE wheel loads; invalid wheel logs error, stubs mount
   - **Dependency:** Requires sign_wheels.py for wheel generation

### Phase D: Integration Testing

**Goal:** All workstreams together.

10. **End-to-end validation:**
    - Fresh hardened control plane + nodes
    - EE licence validation + boot.log HMAC
    - Existing deployment upgrade: root → appuser migration
    - Job execution on hardened infrastructure
    - Audit log records all hardening events

---

## Sequencing Rationale

**Why Phase A before B?**
- Control plane must be hardened first (issues work to nodes)
- Secrets volume ownership fix required by both
- CAP_DROP on agent = prerequisite for consistent security posture

**Why Phase C parallel?**
- Orthogonal to container hardening (no shared resource access changes)
- Can test independently
- **Synchronization point:** Smoke tests before release

**Why init container + startup script (dual approach)?**
- Init container handles fresh deployments automatically
- Startup script catches manual chown failures, provides clear logging
- Operator has clear fallback if auto-chown fails

---

## Foundry-Built Image Inheritance

**Question:** How do images built by Foundry inherit hardening?

### Current Implementation

foundry_service.py generates Dockerfile:
```dockerfile
FROM <base_os>
# ... Smelter configs, tool recipes, packages ...
COPY environment_service/ /app/
CMD ["python", "environment_service/node.py"]
# (No USER directive)
```

Built image runs as root by default.

### Hardening Update

**foundry_service.py change** (before CMD):
```python
# Around line 298 in foundry_service.py
# After all package installation and tool injection:

# Add non-root user and drop capabilities
if os_family == "ALPINE":
    dockerfile.append("RUN addgroup -g 1001 nodeuser && adduser -u 1001 -G nodeuser -s /sbin/nologin nodeuser")
else:  # DEBIAN
    dockerfile.append("RUN groupadd -g 1001 nodeuser && useradd -u 1001 -G nodeuser -s /usr/sbin/nologin nodeuser")

# Copy environment_service as nodeuser
dockerfile.append("COPY --chown=nodeuser:nodeuser environment_service/ /app/environment_service/")

# Drop capabilities (remove any setuid/setcap bits)
dockerfile.append("RUN setcap -r /usr/bin/python3 || true")

# Switch to non-root user
dockerfile.append("USER nodeuser")

# Existing: CMD ["python", "-u", "node.py"]
```

### Implications

1. **Backward Compatibility:** Existing blueprints now auto-inherit non-root (no operator changes needed)
2. **Custom Blueprints:** If operator adds explicit `USER root` after base setup, they override the Foundry default (acceptable; audit logs flag it)
3. **Job Isolation:** Jobs still run in ephemeral containers as root (isolation boundary preserved)
4. **Capability Dropping:** `setcap -r` removes any inherited capabilities from Python shebang

### Risk: Tool Requirements

If a tool or package requires specific capabilities (rare), the generated Dockerfile may fail. **Mitigation:** Enhance CapabilityMatrix to declare required capabilities; if present, generate `RUN setcap cap_...=+ep /path/to/tool` instead of dropping all.

---

## Existing Deployment Migration Scenarios

### Scenario 1: Fresh Deployment (v21.1+)

```bash
# Steps (automatic)
git pull origin main  # Pick up hardening changes
docker compose build agent
docker compose up -d  # init container + startup script handle secrets chown
docker exec agent docker ps  # Validate socket access
docker logs agent | grep -i secret  # Confirm no ownership warnings
```

**Result:** Hardened deployment, zero manual steps.

### Scenario 2: Upgrade Existing Deployment (v21.0 → v21.1+)

```bash
# Step 1: Optional pre-emptive chown (recommended)
docker exec -u root $(docker compose ps -q agent) chown -R 1000:1000 /app/secrets

# Step 2: Deploy hardened image
docker compose build agent
docker compose up -d agent

# Step 3: Verify
docker exec agent id  # Should show UID 1000
docker logs agent | grep -E 'secret|docker' | head -20  # Check for errors
docker exec agent docker ps  # Validate socket access
```

**Result:** Hardened, secrets ownership fixed, minimal downtime.

### Scenario 3: Hardened Environment (CAP_DROP, SELinux, AppArmor)

```bash
# Pre-check: verify docker socket group
stat -c '%a %U:%G' /var/run/docker.sock  # Should be 660 root:docker

# Deploy
docker compose build agent
docker compose up -d agent

# Verify hardening applied
docker exec agent grep Cap /proc/self/status | head -5  # Check dropped caps
docker exec agent docker ps  # Must succeed (group membership)

# If socket access fails:
docker exec -u root agent gpasswd -a appuser docker  # Add group membership
docker compose restart agent
```

**Result:** Hardened in restrictive environment.

---

## Testing & Validation

### Unit Tests (pytest)

```python
# tests/test_licence_hardening.py
def test_boot_log_hmac_signing():
    """HMAC boot.log entries with ENCRYPTION_KEY."""
    with patch.dict(os.environ, {"ENCRYPTION_KEY": "test-key"}):
        result = check_and_record_boot(LicenceStatus.VALID)
        lines = Path("secrets/boot.log").read_text().splitlines()
        last_line = lines[-1]
        hash_hex, ts = last_line.split(" ", 1)
        assert len(hash_hex) == 64, "HMAC-SHA256 should be 64 hex chars"

def test_boot_log_backward_compat():
    """Legacy SHA256 entries accepted."""
    # Seed boot.log with SHA256 entry
    Path("secrets").mkdir(exist_ok=True)
    legacy_hash = hashlib.sha256("".encode()).hexdigest()
    Path("secrets/boot.log").write_text(f"{legacy_hash} 2026-04-12T00:00:00.000Z\n")
    
    # New entry should compute HMAC and append
    check_and_record_boot(LicenceStatus.CE)
    lines = Path("secrets/boot.log").read_text().splitlines()
    # Verify old entry still there, new entry added
    assert len(lines) == 2
```

### Integration Tests (Docker)

```bash
# Fresh deployment hardening
docker compose build agent
docker compose up -d agent
docker exec agent docker ps  # Docker socket access
docker exec agent stat /app/secrets | grep "Uid"  # appuser ownership
docker logs agent | grep -i "boot.log\|secret" | head -5  # Migration logs

# EE wheel loading with entry point validation
docker exec agent python -c "from ee import EEPlugin; print('EE loaded')"

# Foundry build produces hardened image
docker compose exec agent curl -X POST http://localhost:8001/api/foundry/build \
  -H "Content-Type: application/json" \
  -d '{"template_id": "test-template"}'
docker inspect localhost:5000/puppet:test-image | grep '"User"'  # Should show "nodeuser"
```

### Manual Smoke Tests

1. Dashboard login + API calls work post-hardening
2. Foundry template build succeeds, produces hardened image
3. Node enrolls, polls jobs, executes task on hardened infrastructure
4. Audit log records hardening events (CAP_DROP, USER changes)

---

## Risk Register

| Risk | Severity | Mitigation |
|------|----------|-----------|
| Docker socket access fails if appuser not in docker group | HIGH | Test `docker exec agent docker ps` immediately after Containerfile deploy; logs show group membership |
| Secrets chown fails, agent cannot write boot.log | MEDIUM | Startup script + runbook; clear error logging guides operator |
| ENCRYPTION_KEY missing in EE → boot.log falls back to SHA256 | MEDIUM | Document as required; CI gate validates in production |
| Podman socket path differs, runtime detection fails | LOW | Add `/run/podman/podman.sock` fallback check |
| Existing deployment chown missed during upgrade | MEDIUM | Startup script attempts fix; runbook provides manual step |
| Foundry-built images inherit nodeuser but operator adds `USER root` | LOW | Audit logs flag custom USER directives; acceptable operator choice |
| init container chown fails silently in some setups | LOW | Log chown result; startup script provides fallback |

---

## Summary

**Container hardening and EE licence protection integrate naturally with Axiom's existing architecture.** Three integration points require careful handling: Docker socket group membership (foundry access), secrets ownership migration (boot.log/licence.key), and ENCRYPTION_KEY availability (HMAC signing). **Build order enforces dependencies:** Containerfile.server → secrets chown → CAP_DROP, while EE protection develops in parallel. **Fresh deployments are automatic** (init container + startup script); **existing deployments need one manual chown step** documented in upgrade runbook. **All changes are backward-compatible** and can be validated independently before coordinated release.

---

## Sources

- [Linux post-installation steps for Docker Engine](https://docs.docker.com/engine/install/linux-postinstall/)
- [How To Run Docker As Non-root User In Linux](https://itsfoss.gitlab.io/post/how-to-run-docker-as-non-root-user-in-linux/)
- [Hardening Docker: Using Rootless Mode and User Namespaces for Security](https://dohost.us/index.php/2026/03/26/hardening-docker-using-rootless-mode-and-user-namespaces-for-security/)
- [Docker Container Security Best Practices in 2026](https://www.techsaas.cloud/blog/docker-container-security-best-practices-2026/)
- [How to Drop Linux Capabilities in Docker Containers](https://oneuptime.com/blog/post/2026-01-16-docker-drop-capabilities/view)
- [Securing Your APIs with HMAC Signature Validation](https://medium.com/@malindudilshan389/securing-your-apis-with-hmac-signature-validation-54af44d31197)
- [Entry points specification — Python Packaging User Guide](https://packaging.python.org/specifications/entry-points/)
- [Webhook Security Fundamentals: Complete Protection Guide 2026](https://www.hooklistener.com/learn/webhook-security-fundamentals)
