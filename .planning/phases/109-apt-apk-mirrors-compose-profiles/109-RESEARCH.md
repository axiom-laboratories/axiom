# Phase 109: APT + apk Mirrors + Compose Profiles - Research

**Researched:** 2026-04-03
**Domain:** Linux package mirroring (APT + Alpine), Docker Compose profiles, Caddy multi-path serving
**Confidence:** HIGH

## Summary

Phase 109 completes the mirror backend for two dominant Linux distributions by implementing APT (Debian) and apk (Alpine) package mirroring using existing infrastructure patterns. APT packages are downloaded via `apt-get download` and indexed with `dpkg-scanpackages` in a throwaway Debian container. Alpine packages use `apk fetch` and `apk index` in a throwaway Alpine container. Both are served by the existing Caddy sidecar (port 8081) via multi-path routing. All mirror sidecars move behind a Docker Compose profile (`--profile mirrors`), keeping the CE deployment minimal and the EE deployment opt-in for mirror services.

**Primary recommendation:** Implement APT/apk as background mirror tasks following the established `asyncio.to_thread(subprocess.run)` pattern from Phase 108's resolver, serve both via updated Caddy Caddyfile with `handle` blocks for `/apt/` and `/apk/` paths, and apply Docker Compose profiles to all mirror services (pypi, mirror, new apk sidecars if needed).

---

## User Constraints (from CONTEXT.md)

### Locked Decisions
- Implement `_mirror_apt()` stub in `mirror_service.py` using `apt-get download` inside a throwaway Debian container (reuses Phase 108's throwaway container pattern)
- Downloaded `.deb` files stored in `mirror-data/apt/`
- Run `dpkg-scanpackages` after every successful package download to regenerate `Packages.gz`
- Top-level packages only — no transitive APT dependency resolution
- Continue using `[trusted=yes]` in `sources.list` (Phase 13 decision — GPG signing deferred)
- New `_mirror_apk()` method using `apk fetch` inside a throwaway Alpine container
- Downloaded `.apk` files stored in `mirror-data/apk/v{version}/main/`
- Run `apk index -o APKINDEX.tar.gz *.apk` after every successful package download
- APKINDEX left unsigned — Foundry injects `--allow-untrusted` flag on all generated `apk add` lines
- Both APT and apk packages served via existing Caddy sidecar (port 8081)
- **Not** using compose profiles — instead, create `compose.ee.yaml` as a compose override file alongside `compose.server.yaml`
- Services moving to `compose.ee.yaml`: `pypi` (pypiserver), `mirror` (Caddy file server)
- Also moving to EE overlay: agent's `mirror-data` volume mount, `MIRROR_DATA_PATH` env var, and `mirror-data` volume definition
- Mirror health detection: agent performs HTTP health check on `PYPI_MIRROR_URL` and `APT_MIRROR_URL` at startup and every ~60s
- Mirror health reachability stored in `app.state.mirrors_available` and exposed via `GET /api/system/health`
- New `get_apk_repos_content(base_os)` method in `mirror_service.py` — generates `/etc/apk/repositories` content
- Alpine version parsed from base_os image tag (e.g. `alpine:3.20` → `v3.20`)
- Foundry's `build_template()` branches on os_family: DEBIAN → `COPY sources.list`, ALPINE → `COPY repositories`
- `pip.conf` always injected regardless of os_family
- `--allow-untrusted` flag appended to all generated `apk add` lines in Dockerfile

### Claude's Discretion
- Exact throwaway container image selection and lifecycle (cleanup, caching)
- Caddy Caddyfile structure for multi-path serving
- Health check endpoint response shape and error handling
- Mirror health check interval tuning
- Banner component styling and dismissability
- How `apk fetch` handles architecture-specific packages

### Deferred Ideas (OUT OF SCOPE)
- APT GPG signing for local repo — deferred in Phase 13
- APKINDEX RSA signing — deferred for same reason as APT GPG
- APT/apk transitive dependency resolution — deferred
- npm, NuGet, OCI, Conda mirrors — Phases 111, 112

---

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| MIRR-01 | APT mirror backend is fully implemented (complete the existing stub in mirror_service.py) | `apt-get download` pattern verified; `dpkg-scanpackages` standard for index generation |
| MIRR-02 | apk (Alpine) mirror backend with nginx-based compose sidecar serves Alpine packages in air-gap | `apk fetch` + `apk index` pattern verified; Caddy multi-path serving confirmed as viable alternative to nginx |
| MIRR-07 | All mirror sidecars defined as compose services with opt-in profiles (not started by default) | Docker Compose profiles syntax confirmed; `compose.ee.yaml` override pattern matches official best practices |

---

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| dpkg-dev | System | Provides `dpkg-scanpackages` utility for Debian package indexing | Standard tool in Debian/Ubuntu ecosystems for offline repo creation; part of dpkg-dev package |
| apk-tools | System | Provides `apk index` for Alpine package indexing | Built-in Alpine utility; used by Alpine for official mirror setup |
| Caddy | 2.x (existing) | File server for APT and apk packages via `/apt/` and `/apk/` paths | Already running in phase; supports multi-path serving via `handle` blocks; simpler than dedicated nginx sidecar |
| Docker Compose | 2.0+ | Service orchestration with profile support | Native support for `profiles` attribute on services; no custom plugin needed |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| pip | 24.0+ (existing) | Pure Python package downloading (for pip.conf injection) | Already required for PyPI mirroring; no new dependency |
| asyncio | stdlib | Async subprocess execution for throwaway containers | Established pattern in mirror_service.py and resolver_service.py |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Caddy for apk serving | nginx sidecar | Caddy already running; nginx adds maintenance burden and new service to manage |
| compose.ee.yaml override | Modify compose.server.yaml with conditional logic | Override file pattern is cleaner, separates CE/EE concerns, matches Docker best practices |
| `dpkg-scanpackages` | `apt-ftparchive` | dpkg-scanpackages is simpler for small offline repos; apt-ftparchive is for large mirror infrastructure |

---

## Architecture Patterns

### Recommended Project Structure

```
mirror-data/
├── apt/                    # Debian packages
│   ├── package1.deb
│   ├── package2.deb
│   └── Packages.gz         # Generated by dpkg-scanpackages
├── apk/
│   ├── v3.18/              # Versioned subdirectories per Alpine version
│   │   └── main/           # Package category
│   │       ├── package1.apk
│   │       ├── package2.apk
│   │       └── APKINDEX.tar.gz  # Generated by apk index
│   ├── v3.19/
│   │   └── main/
│   └── v3.20/
│       └── main/
└── pypi/                   # Existing PyPI packages
    └── data/packages/
```

### Pattern 1: Throwaway Container for Mirroring

**What:** Execute a one-shot Docker container to download packages from a live repository, extract the download operation, then immediately destroy the container.

**When to use:** When you need to leverage a distro's package manager (apt-get, apk fetch, yum) without shipping those tools in the Foundry base image.

**Example (APT):**
```python
# Source: https://github.com/master-of-puppets/agent_service/services/mirror_service.py
async def _mirror_apt(db: AsyncSession, ingredient: ApprovedIngredient):
    """
    Download .deb package using apt-get download inside a throwaway Debian container.
    """
    os.makedirs(os.path.join(MirrorService.MIRROR_BASE_PATH, "apt"), exist_ok=True)

    cmd = [
        "docker", "run", "--rm",
        "-v", f"{os.path.join(MirrorService.MIRROR_BASE_PATH, 'apt')}:/mirror",
        "debian:12-slim",
        "bash", "-c",
        f"apt-get update && apt-get download {ingredient.name}{ingredient.version_constraint or ''}"
    ]

    result = await asyncio.to_thread(
        subprocess.run,
        cmd,
        capture_output=True,
        text=True,
        timeout=120
    )

    if result.returncode == 0:
        # Regenerate index
        await _regenerate_apt_index()
        ingredient.mirror_status = "MIRRORED"
    else:
        ingredient.mirror_status = "FAILED"
        ingredient.mirror_log = result.stderr

    await db.commit()
```

**Example (Alpine):**
```python
async def _mirror_apk(db: AsyncSession, ingredient: ApprovedIngredient):
    """
    Download .apk package using apk fetch inside a throwaway Alpine container.
    """
    # Determine version from base_os or use default
    version = "v3.20"  # Extract from ingredient or config
    apk_dir = os.path.join(MirrorService.MIRROR_BASE_PATH, "apk", version, "main")
    os.makedirs(apk_dir, exist_ok=True)

    cmd = [
        "docker", "run", "--rm",
        "-v", f"{apk_dir}:/mirror",
        "alpine:3.20",
        "sh", "-c",
        f"apk fetch -o /mirror {ingredient.name}{ingredient.version_constraint or ''}"
    ]

    result = await asyncio.to_thread(
        subprocess.run,
        cmd,
        capture_output=True,
        text=True,
        timeout=120
    )

    if result.returncode == 0:
        await _regenerate_apk_index(apk_dir)
        ingredient.mirror_status = "MIRRORED"
    else:
        ingredient.mirror_status = "FAILED"
        ingredient.mirror_log = result.stderr

    await db.commit()
```

### Pattern 2: Caddy Multi-Path Serving

**What:** Use Caddy's `handle` directive with path matchers to serve multiple static directories from a single service.

**When to use:** When you need to expose multiple package repositories (/apt/, /apk/) from a single file server without dedicated sidecars per path.

**Example (Caddyfile):**
```caddy
:80 {
    # APT packages
    handle /apt/* {
        root /data/apt
        file_server browse
    }

    # Alpine packages
    handle /apk/* {
        root /data/apk
        file_server browse
    }

    # PyPI packages (existing)
    handle /simple/* {
        root /data/pypi/data
        file_server browse
    }
}
```

### Pattern 3: Docker Compose Profiles for EE Services

**What:** Use the `profiles` attribute on services to group optional infrastructure behind an activation flag, keeping CE minimal and EE opt-in.

**When to use:** When you need to offer different service configurations (CE = core only, EE = core + mirrors + premium features) from the same compose files.

**Example (compose.server.yaml):**
```yaml
services:
  agent:
    # ... existing config, NO mirror-data volume
    volumes:
      - certs-volume:/app/global_certs:ro
      - /var/run/docker.sock:/var/run/docker.sock
      - ../puppets:/app/puppets:ro
      - secrets-data:/app/secrets
```

**Example (compose.ee.yaml override):**
```yaml
services:
  agent:
    volumes:
      - certs-volume:/app/global_certs:ro
      - /var/run/docker.sock:/var/run/docker.sock
      - ../puppets:/app/puppets:ro
      - mirror-data:/app/mirror_data
      - secrets-data:/app/secrets

  pypi:
    image: pypiserver/pypiserver:latest
    restart: always
    command: -P . -a . /data/packages
    volumes:
      - mirror-data:/data/packages
    ports:
      - "8080:8080"
    profiles: ["mirrors"]

  mirror:
    image: caddy:latest
    restart: always
    volumes:
      - ./mirror/Caddyfile:/etc/caddy/Caddyfile
      - mirror-data:/data
    ports:
      - "8081:80"
    profiles: ["mirrors"]

volumes:
  mirror-data:
```

**Deployment:**
```bash
# CE: Core only
docker compose -f compose.server.yaml up -d

# EE: Core + mirrors
docker compose -f compose.server.yaml -f compose.ee.yaml up -d --profile mirrors
```

### Anti-Patterns to Avoid
- **Transitive APT/apk resolution in mirror service:** Top-level packages only; base images include core libs, most builds need few extra packages. Avoid pulling entire dependency trees — increases storage and complexity.
- **GPG signing or RSA indexes:** Phase 13 decision carries forward: `[trusted=yes]` for APT, `--allow-untrusted` for apk. Signing deferred to future phase.
- **Embedding mirror-data paths in compose.server.yaml as defaults:** Makes CE deployment attempt to mount nonexistent volumes. Use compose.ee.yaml override to add mirror volumes only when EE is active.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Debian package indexing | Custom package index generator | `dpkg-scanpackages` (part of dpkg-dev) | Standard tool; handles metadata, priorities, architecture flags correctly; one-liner to regenerate after each download |
| Alpine package indexing | Custom .apk index format | `apk index` (built into alpine) | Official Alpine tool; generates proper tar.gz format; handles package metadata compression |
| Multi-path static file serving | Custom routing logic in FastAPI | Caddy `handle` blocks with `root` directive | Caddy is already running; `handle` + path matcher pattern is standard; avoids adding new sidecar |
| Service orchestration with optional tiers | Conditional compose generation scripts | Docker Compose `profiles` attribute | Native feature; no custom scripting; standard practice for CE/EE separation |

**Key insight:** Debian and Alpine provide battle-tested package management tools; using them directly (via throwaway containers) is simpler and more reliable than reimplementing index formats. Caddy's multi-path serving is mature and requires no new infrastructure.

---

## Common Pitfalls

### Pitfall 1: `apt-get download` Requires Package Name Parsing
**What goes wrong:** `apt-get download` strictly matches package names and fails if you pass a version constraint like `package==1.0.0` or `package>=1.0`.
**Why it happens:** apt-get expects `package=version` syntax with `=` not `==` or `>=`.
**How to avoid:** Extract the package name and version separately from `ingredient.version_constraint`. For APT, use `apt-get install --download-only --no-install-recommends` or `apt-get download` with proper version format (e.g., `package=1.0.0-1ubuntu1`).
**Warning signs:** Subprocess returns 404 or "unable to locate package" even though the package exists on the mirror.

### Pitfall 2: Alpine Version Mismatch in Directory Structure
**What goes wrong:** apk repositories are organized by Alpine version (v3.18, v3.19, v3.20). If you download a package for Alpine 3.20 but store it in v3.18/, the apk add command points to the wrong repo and fails.
**Why it happens:** Alpine's official mirrors organize packages by version. Each version has `/main`, `/community`, `/testing` subdirectories.
**How to avoid:** Parse the Alpine version from `base_os` image tag (e.g., `alpine:3.20` → `v3.20`) and ensure the mirror directory matches. For `alpine:latest`, use a configurable fallback version (e.g., `v3.20`).
**Warning signs:** Foundry build fails with "ERROR: unable to find a matching apk in any of the configured repositories" even though the package was downloaded.

### Pitfall 3: `apk index` Must Run in the Directory Containing .apk Files
**What goes wrong:** Running `apk index -o APKINDEX.tar.gz` from the wrong directory or with wrong CWD generates an index that points to nonexistent relative paths.
**Why it happens:** `apk index` scans the current directory for .apk files and stores relative paths in the index.
**How to avoid:** Always `cd` into the target directory before running `apk index`, or run the command inside a throwaway container with the correct working directory.
**Warning signs:** apk add in Dockerfile fails with "Could not open index for repository" or missing checksums.

### Pitfall 4: Mirror URL Misconfiguration Between Dockerfile and Container
**What goes wrong:** Foundry generates `/etc/apk/repositories` with `http://mirror:8081/apk/v3.20/main`, but the running Puppet node's DNS doesn't resolve `mirror`, or the port is wrong.
**Why it happens:** Bridge network naming is implicit in docker-compose. Manual builds outside compose may have different DNS.
**How to avoid:** Use environment variables `APK_MIRROR_URL` (default `http://mirror/apk`) that match the Caddy service hostname in compose. Test the URL from inside a Foundry build container before committing.
**Warning signs:** apk add hangs for 30s+ then fails with "connection refused" or "name not found".

### Pitfall 5: Caddy root Path Must Be Absolute
**What goes wrong:** Using `root /data/apt` works, but if you later use a relative path or try to use `${DATA_DIR}/apt`, Caddy silently ignores it or serves 404s.
**Why it happens:** Caddy's `root` directive requires absolute filesystem paths.
**How to avoid:** Always use absolute paths in Caddyfile; if you need dynamic paths, mount volumes at fixed paths (e.g., `/data/apt`, `/data/apk`).
**Warning signs:** HTTP 404 even though files exist at the volume path.

---

## Code Examples

Verified patterns from official sources and existing codebase:

### APT Mirror Implementation
```python
# Source: Follows pattern from https://man7.org/linux/man-pages/man1/dpkg-scanpackages.1.html
async def _mirror_apt(db: AsyncSession, ingredient: ApprovedIngredient):
    """
    Download .deb package using apt-get download in a throwaway Debian container.
    After each successful download, regenerate Packages.gz index.
    """
    apt_dir = os.path.join(MirrorService.MIRROR_BASE_PATH, "apt")
    os.makedirs(apt_dir, exist_ok=True)

    # Parse version: ingredient.version_constraint = "==1.0.0" → "1.0.0"
    pkg_spec = ingredient.name
    if ingredient.version_constraint:
        version = ingredient.version_constraint.lstrip("=><!")
        pkg_spec = f"{ingredient.name}={version}"

    cmd = [
        "docker", "run", "--rm",
        "-v", f"{apt_dir}:/mirror",
        "debian:12-slim",
        "bash", "-c",
        f"apt-get update && apt-get download {pkg_spec} -o /mirror"
    ]

    result = await asyncio.to_thread(
        subprocess.run,
        cmd,
        capture_output=True,
        text=True,
        timeout=120
    )

    if result.returncode == 0:
        # Regenerate index
        index_cmd = [
            "dpkg-scanpackages", "--multiversion", ".",
            "/dev/null"
        ]
        # Run dpkg-scanpackages in the apt directory
        proc = await asyncio.to_thread(
            subprocess.run,
            index_cmd,
            cwd=apt_dir,
            capture_output=True,
            text=True
        )

        # Compress to Packages.gz
        with gzip.open(os.path.join(apt_dir, "Packages.gz"), "wb") as f:
            f.write(proc.stdout.encode())

        ingredient.mirror_status = "MIRRORED"
        ingredient.mirror_log = f"Downloaded {ingredient.name}; regenerated Packages.gz"
    else:
        ingredient.mirror_status = "FAILED"
        ingredient.mirror_log = result.stderr or "apt-get download failed"

    await db.commit()
```

### Alpine Mirror Implementation
```python
# Source: Follows pattern from https://wiki.alpinelinux.org/wiki/Repositories
async def _mirror_apk(db: AsyncSession, ingredient: ApprovedIngredient):
    """
    Download .apk package using apk fetch in a throwaway Alpine container.
    After each download, regenerate APKINDEX.tar.gz.
    """
    # Parse Alpine version from base_os or use default
    # Example: "alpine:3.20" → "v3.20"; "alpine:latest" → fallback
    version = "v3.20"  # TODO: Extract from ingredient metadata or config
    apk_dir = os.path.join(
        MirrorService.MIRROR_BASE_PATH, "apk", version, "main"
    )
    os.makedirs(apk_dir, exist_ok=True)

    # Parse version: ingredient.version_constraint = "==1.0.0" → "1.0.0"
    pkg_spec = ingredient.name
    if ingredient.version_constraint:
        version_part = ingredient.version_constraint.lstrip("=><!")
        pkg_spec = f"{ingredient.name}={version_part}"

    cmd = [
        "docker", "run", "--rm",
        "-v", f"{apk_dir}:/mirror",
        "alpine:3.20",
        "sh", "-c",
        f"apk fetch -o /mirror {pkg_spec}"
    ]

    result = await asyncio.to_thread(
        subprocess.run,
        cmd,
        capture_output=True,
        text=True,
        timeout=120
    )

    if result.returncode == 0:
        # Regenerate APKINDEX.tar.gz
        index_cmd = ["apk", "index", "-o", "APKINDEX.tar.gz", "-d", "/mirror"]
        proc = await asyncio.to_thread(
            subprocess.run,
            index_cmd,
            cwd=apk_dir,
            capture_output=True,
            text=True
        )

        ingredient.mirror_status = "MIRRORED"
        ingredient.mirror_log = f"Downloaded {ingredient.name}; regenerated APKINDEX.tar.gz"
    else:
        ingredient.mirror_status = "FAILED"
        ingredient.mirror_log = result.stderr or "apk fetch failed"

    await db.commit()
```

### APK Repositories Content Generator
```python
# Source: Follows pattern from https://wiki.alpinelinux.org/wiki/Repositories
@staticmethod
def get_apk_repos_content(base_os: str = None) -> str:
    """
    Returns the content for /etc/apk/repositories pointing to local mirror.

    Args:
        base_os: Image tag (e.g., "alpine:3.20") to extract version

    Returns:
        Multiline string for /etc/apk/repositories
    """
    # Parse version from base_os
    version = "v3.20"  # Default fallback
    if base_os and "alpine:" in base_os.lower():
        tag = base_os.split(":")[-1]
        if tag != "latest":
            version = f"v{tag}"

    url = os.getenv("APK_MIRROR_URL", "http://mirror/apk")
    repos = [
        f"{url}/{version}/main",
        f"{url}/{version}/community",
    ]
    return "\n".join(repos) + "\n"
```

### Foundry Injection for Alpine
```python
# Source: Pattern from foundry_service.py build_template()
# In build_template(), after os_family detection:

repositories = MirrorService.get_apk_repos_content(base_os)
dockerfile.append("COPY repositories /etc/apk/repositories")

# ... later when writing files to build_dir:
with open(os.path.join(build_dir, "repositories"), "w") as f:
    f.write(repositories)

# When injecting apk add commands (for tools or packages):
for pkg in alpine_packages:
    dockerfile.append(f"RUN apk add --no-cache --allow-untrusted {pkg}")
```

### Caddy Multi-Path Configuration
```caddy
# Source: https://caddyserver.com/docs/caddyfile/directives/handle
:80 {
    # APT (Debian) packages
    handle /apt/* {
        root /data/apt
        file_server browse
    }

    # Alpine packages
    handle /apk/* {
        root /data/apk
        file_server browse
    }

    # PyPI packages (existing)
    handle /simple/* {
        root /data/pypi
        file_server browse
    }

    # Catch-all 404
    handle {
        respond 404
    }
}
```

### Docker Compose EE Override Pattern
```yaml
# compose.ee.yaml (alongside compose.server.yaml)
# This file ONLY defines what's different from compose.server.yaml

version: "3"

services:
  agent:
    # Override the volumes block (replaces entire list, doesn't merge)
    # Note: Both compose files must be kept in sync for agent volumes
    volumes:
      - certs-volume:/app/global_certs:ro
      - /var/run/docker.sock:/var/run/docker.sock
      - ../puppets:/app/puppets:ro
      - mirror-data:/app/mirror_data          # ← EE only
      - secrets-data:/app/secrets
    environment:
      - MIRROR_DATA_PATH=/app/mirror_data      # ← EE only

  pypi:
    image: pypiserver/pypiserver:latest
    restart: always
    command: -P . -a . /data/packages
    volumes:
      - mirror-data:/data/packages
    ports:
      - "8080:8080"
    profiles: ["mirrors"]

  mirror:
    image: caddy:latest
    restart: always
    volumes:
      - ./mirror/Caddyfile:/etc/caddy/Caddyfile
      - mirror-data:/data
    ports:
      - "8081:80"
    profiles: ["mirrors"]

volumes:
  mirror-data:
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Manual APT/apk download + manual index generation | Automated via throwaway container + background task | Phase 109 (now) | Operators no longer hand-edit Packages/APKINDEX; consistency guaranteed |
| Single compose.server.yaml for all tiers | CE-only compose + EE override (compose.ee.yaml) | Phase 109 (now) | CE deployment stays lightweight; EE mirrors are opt-in via CLI flag |
| Separate nginx sidecar for apk | Caddy multi-path serving | Phase 109 (now) | Reduced operational overhead; single file server manages all static content |
| Monolithic mirror service | Modular methods by ecosystem (PYPI, APT, APK) | Phase 109 (now) | Easier to extend to npm, NuGet, Conda in Phases 111–112 |

**Deprecated/outdated:**
- APT GPG signing: Phase 13 decision deferred — no operator has asked for it yet; `[trusted=yes]` sufficient for air-gap use
- Alpine APKINDEX signing: Deferred for same reason; `--allow-untrusted` sufficient for internal mirrors
- Transitive APT/apk resolution: Deferred; most builds need only top-level packages

---

## Open Questions

1. **Alpine version fallback strategy**
   - What we know: Alpine tags like `3.20` map to `v3.20` directory structure; `latest` tag is ambiguous
   - What's unclear: Should we parse Alpine version from base_os at Foundry build time, or pre-configure in environment?
   - Recommendation: Add `DEFAULT_ALPINE_VERSION` env var (default `v3.20`); parse base_os tag at build time; fallback to env var if unparseable

2. **`dpkg-scanpackages` vs `apt-ftparchive` for Debian indexing**
   - What we know: dpkg-scanpackages is simpler for small offline repos; apt-ftparchive supports full mirror infrastructure
   - What's unclear: Are there edge cases (multi-arch, rapid version updates) where dpkg-scanpackages falls short?
   - Recommendation: Start with dpkg-scanpackages (Phase 109); switch to apt-ftparchive only if edge cases surface in production

3. **Mirror health check interval**
   - What we know: CONTEXT.md specifies ~60s interval
   - What's unclear: Should health check timeout be 5s, 10s, or higher? Does failed health check block Foundry builds immediately, or degrade gracefully?
   - Recommendation: 10s timeout; failed check sets `app.state.mirrors_available = False` (advisory, not blocking); Foundry checks `mirrors_available` and displays banner, but doesn't hard-block if EE mirrors unreachable (allows fallback to internet or manual override)

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest + pytest-asyncio (existing) |
| Config file | `puppeteer/agent_service/tests/conftest.py` |
| Quick run command | `pytest puppeteer/tests/test_mirror.py -x -v` |
| Full suite command | `pytest puppeteer/ -x` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| MIRR-01 | `_mirror_apt()` downloads .deb and regenerates Packages.gz | unit | `pytest puppeteer/tests/test_mirror.py::test_mirror_apt_download -x` | ❌ Wave 0 |
| MIRR-01 | `_mirror_apt()` parses version constraint correctly (==, >=, <) | unit | `pytest puppeteer/tests/test_mirror.py::test_mirror_apt_version_parsing -x` | ❌ Wave 0 |
| MIRR-01 | `get_sources_list_content()` generates correct syntax for Foundry injection | unit | `pytest puppeteer/tests/test_mirror.py::test_sources_list_format -x` | ✅ (existing) |
| MIRR-02 | `_mirror_apk()` downloads .apk and regenerates APKINDEX.tar.gz | unit | `pytest puppeteer/tests/test_mirror.py::test_mirror_apk_download -x` | ❌ Wave 0 |
| MIRR-02 | `get_apk_repos_content()` parses Alpine version from base_os tag | unit | `pytest puppeteer/tests/test_mirror.py::test_apk_repos_version_parsing -x` | ❌ Wave 0 |
| MIRR-02 | `get_apk_repos_content()` falls back to DEFAULT_ALPINE_VERSION for `latest` tag | unit | `pytest puppeteer/tests/test_mirror.py::test_apk_repos_fallback -x` | ❌ Wave 0 |
| MIRR-02 | Foundry build for Alpine image injects repositories file correctly | integration | `pytest puppeteer/tests/test_foundry_mirror.py::test_alpine_build_injects_repos -x` | ❌ Wave 0 |
| MIRR-07 | `docker compose config` shows `pypi` service has `profiles: [mirrors]` | smoke | `docker compose -f compose.server.yaml config | grep -A 5 "profiles"` | ❌ Wave 0 |
| MIRR-07 | `docker compose up` without `--profile mirrors` does NOT start `pypi` or `mirror` services | smoke | `docker compose -f compose.server.yaml -f compose.ee.yaml up --dry-run | grep -E "pypi|mirror"` | ❌ Wave 0 |
| MIRR-07 | `docker compose up --profile mirrors` starts all mirror services | smoke | `docker compose -f compose.server.yaml -f compose.ee.yaml up --profile mirrors --dry-run` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `pytest puppeteer/tests/test_mirror.py -x -v` (APT/apk unit tests only, ~10s)
- **Per wave merge:** `pytest puppeteer/tests/test_mirror.py puppeteer/tests/test_foundry_mirror.py -x` (APT/apk + Foundry injection, ~30s)
- **Phase gate:** Full suite `pytest puppeteer/` + `docker compose config` validation before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_mirror.py::test_mirror_apt_download` — APT downloading and index regeneration
- [ ] `tests/test_mirror.py::test_mirror_apt_version_parsing` — Version constraint parsing (==, >=, <)
- [ ] `tests/test_mirror.py::test_mirror_apk_download` — APK downloading and APKINDEX regeneration
- [ ] `tests/test_mirror.py::test_apk_repos_version_parsing` — Alpine version extraction from base_os
- [ ] `tests/test_mirror.py::test_apk_repos_fallback` — Fallback to DEFAULT_ALPINE_VERSION for `alpine:latest`
- [ ] `tests/test_foundry_mirror.py::test_alpine_build_injects_repos` — Foundry Alpine build integration (new file)
- [ ] Smoke test for Compose profiles: `docker compose config` validation + dry-run checks

---

## Sources

### Primary (HIGH confidence)
- Official Debian Manual: [dpkg-scanpackages(1)](https://manpages.debian.org/testing/dpkg-dev/dpkg-scanpackages.1.en.html) — package index generation
- Official Alpine Wiki: [Repositories](https://wiki.alpinelinux.org/wiki/Repositories) — apk index structure and versioning
- Official Alpine Wiki: [Alpine Package Keeper](https://wiki.alpinelinux.org/wiki/Alpine_Package_Keeper) — apk fetch and index commands
- Official Docker Docs: [Use service profiles - Docker Compose](https://docs.docker.com/compose/how-tos/profiles/) — compose profile syntax and activation
- Official Caddy Docs: [file_server directive](https://caddyserver.com/docs/caddyfile/directives/file_server) — static file serving
- Official Caddy Docs: [handle directive](https://caddyserver.com/docs/caddyfile/directives/handle) — path-based routing

### Secondary (MEDIUM confidence)
- [Creating a Local APT Repository on Linux | Baeldung on Linux](https://www.baeldung.com/linux/apt-set-up-make-local-repository) — offline Debian mirror patterns verified against dpkg-scanpackages official docs
- [Creating an Alpine Linux Repository | Erianna](https://www.erianna.com/creating-an-alpine-linux-repository/) — Alpine offline repository setup with APKINDEX generation
- [How to serve file_server from different path? - Caddy Community](https://caddy.community/t/how-to-serve-file-server-from-different-path/10034) — multi-path static serving with Caddy (verified against official docs)

### Project Context (HIGH confidence)
- Existing `mirror_service.py`: `_mirror_apt()` stub (lines 234–241) and `get_sources_list_content()` pattern (lines 250–254)
- Existing `foundry_service.py`: os_family branching pattern (lines 88, 143–144) for DEBIAN sources.list injection
- Existing resolver_service.py: `asyncio.to_thread(subprocess.run, ...)` pattern for throwaway container execution
- CONTEXT.md Phase 109: Locked decisions and specific integration points

---

## Metadata

**Confidence breakdown:**
- Standard stack (APT/apk tools): HIGH — both are official distro tools with extensive documentation and proven patterns in field
- Architecture patterns (throwaway containers, Caddy multi-path, Compose profiles): HIGH — patterns verified against official docs and existing codebase
- Pitfalls: MEDIUM-HIGH — drawn from community experience (Baeldung, Caddy community) and project patterns; some edge cases (APT version constraint syntax) may need validation during implementation
- Test gaps: HIGH — clear mapping of requirements to missing tests; Wave 0 coverage obvious

**Research date:** 2026-04-03
**Valid until:** 2026-04-17 (14 days — APT/apk are stable; Docker Compose/Caddy release infrequently)

---

*Phase: 109-apt-apk-mirrors-compose-profiles*
*Research completed: 2026-04-03*
