# Technology Stack: Container Hardening + EE Licence Protection

**Project:** Master of Puppets (Axiom)  
**Researched:** 2026-04-12  
**Research Mode:** Ecosystem (NEW features for existing stack)

## Overview

This research covers **stack requirements for two hardening workstreams**:
1. **Container Security Hardening** — non-root users, capability dropping, socket mounting, Postgres port restriction
2. **EE Licence Protection** — signed wheel manifest verification, HMAC-keyed boot logs, entry point validation

Both workstreams use **existing dependencies** (cryptography, PyJWT, importlib.metadata) and **Python stdlib** (hmac, hashlib, importlib.metadata). **No new third-party dependencies required.**

---

## Recommended Stack — NO NEW DEPENDENCIES

### Python Standard Library (Already Available)

| Module | Purpose | Current Code | New Use |
|--------|---------|--------------|---------|
| `hmac` | SHA256-based message authentication (constant-time comparison) | ✓ Existing: `compute_signature_hmac()`, `verify_signature_hmac()` in `security.py` | HMAC-keyed boot log for licence tamper detection |
| `hashlib` | SHA256, MD5 for hashing | ✓ Existing: licence boot log hash chain | Boot log append-only integrity |
| `importlib.metadata` | Entry point discovery and loading | ✓ Existing: `entry_points(group="axiom.ee")` in `ee/__init__.py` | Whitelist entry points by name; validate loaded modules |
| `json` | Serialization (already used everywhere) | ✓ Existing | Wheel manifest parsing (METADATA, RECORD) |
| `pathlib.Path` | File system operations | ✓ Existing | Wheel extraction path validation, secure path handling |
| `zipfile` | ZIP archive handling (wheels are ZIP) | Not currently used | Wheel signature extraction (RECORD.sig file) |

**Confidence:** HIGH — all modules are stable, standard, documented in Python 3.12 docs.

---

### Existing Third-Party Dependencies (NO VERSION CHANGES NEEDED)

#### cryptography (v46.0.5 minimum)

| Feature | Needed By | Version Requirement | Status |
|---------|-----------|-------------------|--------|
| Ed25519PublicKey + verify() | Wheel manifest verification | ≥ 40.0 | ✓ v46.0.5 supports all operations |
| PEM key loading + serialization | Licence JWT verification (existing) | ≥ 2.0 | ✓ Since v2.0 |

**Existing integration:** `cryptography.hazmat.primitives.asymmetric.ed25519.Ed25519PublicKey` used in `licence_service.py` for JWT verification.

**New integration:** Same library, same public key hardcoding pattern, used for wheel RECORD.sig verification:
```python
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

_wheel_sign_key = Ed25519PublicKey.from_public_bytes(hardcoded_public_key_bytes)
_wheel_sign_key.verify(signature_bytes, manifest_bytes)  # Raises InvalidSignature on mismatch
```

**Confidence:** HIGH — cryptography v46 is current (released 2025), maintains backward compatibility, Ed25519 is stable since v3.4.

#### PyJWT (≥2.7.0, existing requirement)

No new integration needed. Licence JWT verification already uses PyJWT's EdDSA support:
```python
import jwt
jwt.decode(licence_token, public_key_pem, algorithms=["EdDSA"], key=ed25519_key)
```

**Confidence:** HIGH — requirement already specified in requirements.txt; EdDSA (RFC 8037) since v2.7.0.

---

## Stack Additions by Feature

### Feature 1: Container Security Hardening

#### 1a. Dockerfile Enhancements — Alpine & Debian Base Images

| Base Image | Purpose | Requirements | Special Handling |
|------------|---------|--------------|------------------|
| `python:3.12-alpine` | Agent/Model (existing) | `addgroup --system`, `adduser --system` | Alpine uses BusyBox addgroup/adduser; IDs recommended: 1001 for appuser, 1001 for appgroup |
| `python:3.12-slim` | Node image (existing) | `useradd`, `groupadd` (Debian GNU tools) | Debian allows `-N` flag for `useradd` (no home); gid range 999 for docker group |
| Docker multi-stage COPY | Node builds (existing) | No new deps | COPY --from=docker:cli and docker:dind for socket/CLI access |

**New Dockerfile directives needed:**
```dockerfile
# Alpine (Containerfile.server)
RUN addgroup --system --gid 1001 appgroup && \
    adduser --system --uid 1001 --ingroup appgroup --no-create-home appuser && \
    addgroup appuser docker  # For socket access (gid 999 on Linux)
RUN chown -R appuser:appgroup /app
USER appuser

# Debian (Containerfile.node)
RUN groupadd --system --gid 1001 appgroup && \
    useradd --system --uid 1001 --gid appgroup --no-create-home appuser && \
    getent group docker >/dev/null || groupadd --gid 999 docker && \
    usermod -aG docker appuser
RUN chown -R appuser:appgroup /app
USER appuser
```

**Confidence:** HIGH — standard Linux userland tooling, no new packages.

#### 1b. Docker Compose v3+ Syntax — Hardening Directives

| Directive | Purpose | Syntax |
|-----------|---------|--------|
| `cap_drop` | Drop all Linux capabilities by default | `cap_drop: [ALL]` |
| `cap_add` | Selectively restore only needed caps | `cap_add: [NET_BIND_SERVICE]` (Caddy only) |
| `security_opt` | Disable privilege escalation | `security_opt: [no-new-privileges:true]` |
| `deploy.resources.limits` | Memory + CPU caps | `deploy: { resources: { limits: { memory: '1g', cpus: '2.0' } } }` |
| `deploy.resources.reservations` | Minimum guaranteed resources | `deploy: { resources: { reservations: { memory: '256m' } } }` |
| `volumes` (socket mounts) | Node → host Docker socket access | `- /var/run/docker.sock:/var/run/docker.sock` (Docker) or `/run/podman/podman.sock:/run/podman/podman.sock` (Podman) |

**Key decision:** Replace `privileged: true` on node with socket mount + `cap_drop: [ALL]`.

**Examples:**
```yaml
# Caddy (cert-manager) — needs NET_BIND_SERVICE for :80/:443
cert-manager:
  cap_drop: [ALL]
  cap_add: [NET_BIND_SERVICE]
  security_opt: [no-new-privileges:true]

# Node (Docker host variant)
node:
  cap_drop: [ALL]
  security_opt: [no-new-privileges:true]
  volumes:
    - /var/run/docker.sock:/var/run/docker.sock
  environment:
    EXECUTION_MODE: docker  # Explicit, not auto-detect
  deploy:
    resources:
      limits:
        memory: 2g
        cpus: '2.0'

# Node (Podman host variant)
node:
  cap_drop: [ALL]
  security_opt: [no-new-privileges:true]
  volumes:
    - /run/podman/podman.sock:/run/podman/podman.sock
  environment:
    EXECUTION_MODE: podman
```

**Postgres port restriction:**
```yaml
db:
  ports:
    - "127.0.0.1:5432:5432"  # Loopback only; internal: use db:5432
```

**Confidence:** HIGH — Docker Compose v3.7+ (2019) fully supports all directives; `deploy.resources` is standard since v3.2.

#### 1c. runtime.py Socket Mount Auto-Detection

**Current code:** Checks only `/var/run/docker.sock` in `detect_runtime()`.

**New requirement:** Also check `/run/podman/podman.sock` (Podman rootful) and `/run/user/1000/podman/podman.sock` (Podman rootless).

**No new dependencies.** Uses `shutil.which()` and `os.path.exists()` (already present).

```python
def detect_runtime(self) -> str:
    mode = os.environ.get("EXECUTION_MODE", "auto").lower()
    if mode in ("docker", "podman"):
        logger.info(f"EXECUTION_MODE={mode} (explicit)")
        return mode
    # auto: probe in order
    if os.path.exists("/var/run/docker.sock") and shutil.which("docker"):
        return "docker"
    if os.path.exists("/run/podman/podman.sock") and shutil.which("podman"):
        return "podman"
    if os.path.exists(f"/run/user/{os.getuid()}/podman/podman.sock") and shutil.which("podman"):
        return "podman"
    raise RuntimeError("...")
```

**Confidence:** HIGH — no new packages, uses stdlib `os`, `shutil`.

#### 1d. foundry_service.py — Generated Dockerfile User Directive

**New requirement:** Append `USER appuser` after all RUN commands that install packages.

```python
def _generate_dockerfile(...):
    lines = [...]
    # ... existing lines: FROM, RUN apt-get install, etc.
    lines.append("")
    lines.append("# Switch to non-root user")
    lines.append("USER appuser")
    return "\n".join(lines)
```

**Confidence:** HIGH — no dependencies, string concatenation.

---

### Feature 2: EE Licence Protection — Signed Wheel Manifest Verification

#### 2a. Wheel Signature Verification (Python stdlib + existing cryptography)

**New module needed:** `puppeteer/agent_service/services/wheel_service.py` (single, focused module for wheel validation).

**Inputs:**
- Wheel file path (e.g., `/tmp/axiom_ee-0.1.0-cp312-cp312-musllinux_1_2_x86_64.whl`)
- Hardcoded Ed25519 public key (same pattern as licence key)

**Process:**
1. Extract wheel (ZIP archive)
2. Read `dist-info/WHEEL` metadata (JSON or RFC822 format)
3. Read `dist-info/RECORD` (manifest of all files + hashes)
4. Read `dist-info/RECORD.sig` (Ed25519 signature of RECORD)
5. Verify signature using `cryptography.hazmat.primitives.asymmetric.ed25519.Ed25519PublicKey`
6. Validate RECORD hashes match extracted files

**No new dependencies.** Uses:
- `zipfile` (stdlib)
- `hashlib.sha256()` (stdlib, existing)
- `cryptography.hazmat.primitives.asymmetric.ed25519.Ed25519PublicKey` (existing)

**Confidence:** HIGH — all components (zipfile, hashlib, cryptography) are stable; wheel format is standardized (PEP 427, 566).

#### 2b. Boot Log HMAC — Tamper Detection (Existing Pattern)

**Current:** `boot.log` is a plaintext file with SHA256 hash chain (per `licence_service.py`).

**Enhancement:** Add HMAC-SHA256 to detect tampering (e.g., clock rollback via manual `/app/secrets/boot.log` edit).

**No new dependencies.** Uses existing `hmac` + `hashlib`:

```python
import hmac
import hashlib

def append_to_boot_log_with_hmac(secret: bytes, entry: str) -> None:
    """Append entry with HMAC-SHA256 tag for tamper detection."""
    with open(Path("secrets/boot.log"), "a") as f:
        tag = hmac.new(secret, entry.encode('utf-8'), hashlib.sha256).hexdigest()
        f.write(f"{entry} HMAC:{tag}\n")

def verify_boot_log_integrity(secret: bytes) -> bool:
    """Verify all HMAC tags in boot.log. Returns True if all valid."""
    with open(Path("secrets/boot.log"), "r") as f:
        for line in f:
            line = line.rstrip()
            if not line or "HMAC:" not in line:
                continue
            entry, tag_part = line.rsplit(" HMAC:", 1)
            expected = hmac.new(secret, entry.encode('utf-8'), hashlib.sha256).hexdigest()
            if not hmac.compare_digest(tag_part, expected):
                return False
    return True
```

**Integration:** Call `verify_boot_log_integrity(ENCRYPTION_KEY)` in `load_licence()` as part of clock-rollback detection.

**Confidence:** HIGH — existing pattern in `compute_signature_hmac()` and `verify_signature_hmac()`.

#### 2c. Entry Point Whitelist Validation (importlib.metadata + stdlib)

**Current:** `ee/__init__.py` uses `importlib.metadata.entry_points(group="axiom.ee")` to discover plugins.

**New requirement:** Validate that:
1. Only one entry point exists in the `axiom.ee` group (no user-installed conflicting plugins)
2. The entry point name matches expected (e.g., `axiom_ee`)
3. The loaded module comes from the wheel (not a shadow import)

**No new dependencies.** Uses `importlib.metadata` (existing).

**Confidence:** HIGH — `importlib.metadata` is stdlib (since Python 3.8); entry point discovery is stable.

#### 2d. Wheel Installation Bootstrap Safety

**Current:** `ee/__init__.py` calls `pip install --no-deps` on the wheel.

**Enhancement:** Before installation, verify wheel signature (using Feature 2a).

**Confidence:** HIGH — integrates with existing `_install_ee_wheel()` pattern.

---

## Integration Points — How Features Connect

### Container Hardening → Foundry Propagation
- **Requirement:** Foundry-built node images inherit non-root USER
- **Implementation:** `foundry_service.py` appends `USER appuser` to generated Dockerfile
- **No new dependencies**

### Wheel Signature Verification → Licence Loading
- **Requirement:** Verify wheel integrity before entry point discovery
- **Implementation:** `ee/__init__.py` calls `wheel_service.verify_wheel_integrity()` before `pip install`
- **Entry points:** Already using `importlib.metadata.entry_points(group="axiom.ee")`
- **No new dependencies**

### Boot Log HMAC → Licence State
- **Requirement:** Detect clock rollback via tampered boot.log
- **Implementation:** `licence_service.py` calls `verify_boot_log_integrity()` in `load_licence()`
- **Uses:** Existing `ENCRYPTION_KEY` (from `secrets.env`)
- **No new dependencies**

---

## Summary Table — Stack Changes by Feature

| Feature | New Modules | New Packages | Modified Files | Dependency Changes |
|---------|------------|--------------|-----------------|-------------------|
| **Container Hardening** | None | None | `Containerfile.server`, `Containerfile.node`, `compose.server.yaml`, `node-compose.yaml`, `runtime.py`, `foundry_service.py` | None |
| **Wheel Signature Verification** | `wheel_service.py` (new) | None | `ee/__init__.py` | None (uses existing cryptography) |
| **Boot Log HMAC** | None (extend existing) | None | `licence_service.py` | None (uses stdlib hmac) |
| **Entry Point Whitelist** | None (extend existing) | None | `ee/__init__.py` | None (uses stdlib importlib.metadata) |

---

## Versions Verified

| Library | Current Version | Minimum Required | Status |
|---------|-----------------|------------------|--------|
| cryptography | 46.0.5 | 40.0+ (Ed25519 stable since 3.4) | ✓ Sufficient |
| PyJWT | ≥2.7.0 (required) | 2.7.0+ (EdDSA support) | ✓ Sufficient |
| Python | 3.12 | 3.12+ | ✓ Current |
| Docker API (via docker SDK) | 7.0.0+ (existing) | 7.0.0 | ✓ Compatible |

---

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| **Stdlib modules (hmac, hashlib, importlib.metadata)** | HIGH | Stable since Python 3.8+; standard library |
| **cryptography v46 Ed25519 operations** | HIGH | Verified working for licence JWTs; wheel signature uses same APIs |
| **Docker Compose syntax (cap_drop, security_opt, deploy.resources)** | HIGH | Standard since v3.2–3.7 (2019–2021); widely used in production |
| **Dockerfile user/group management (Alpine + Debian)** | HIGH | Standard Linux userland; no surprises |
| **Wheel format (zipfile + RECORD + signature)** | HIGH | PEP 427, PEP 566 standardized; zipfile is stdlib |
| **importlib.metadata entry point discovery** | HIGH | Stdlib since Python 3.8; used in existing code |
| **Integration with existing codebase** | HIGH | All features extend existing patterns (HMAC, Ed25519, entry points, socket mounts) |

---

## What NOT to Add

❌ **Do not add:**
- `wheel` / `setuptools` packages (wheel format is ZIP; use stdlib `zipfile`)
- `cryptojwt` or `python-jose` (PyJWT already supports EdDSA)
- `pydantic-extra-types` or validation frameworks (use stdlib validators)
- Custom seccomp profiles (Docker default is sufficient; maintenance cost high)
- AppArmor/SELinux custom rules (host-level config outside our control)
- Container orchestration platforms (Docker Compose v3 is the target)

❌ **Do not change:**
- cryptography version (46.0.5 is current, backward compatible)
- PyJWT version (≥2.7.0 requirement is locked correctly)
- Base images (python:3.12-alpine and python:3.12-slim are standard)

---

## Sources

- [Python hmac documentation](https://docs.python.org/3/library/hmac.html)
- [Python hashlib documentation](https://docs.python.org/3/library/hashlib.html)
- [Python importlib.metadata documentation](https://docs.python.org/3/library/importlib.metadata.html)
- [Python zipfile documentation](https://docs.python.org/3/library/zipfile.html)
- [cryptography library Ed25519 API](https://cryptography.io/en/latest/hazmat/primitives/asymmetric/ed25519/)
- [PEP 427 — The Wheel Binary Package Format](https://www.python.org/dev/peps/pep-0427/)
- [PEP 566 — Metadata 2.2 for the JSON-based Serialisation](https://www.python.org/dev/peps/pep-0566/)
- [Docker Compose Specification — Services Security](https://github.com/compose-spec/compose-spec/blob/master/spec.md#security)
- Existing codebase: `licence_service.py`, `ee/__init__.py`, `security.py`, `runtime.py`
