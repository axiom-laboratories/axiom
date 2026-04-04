# Phase 112: Conda Mirror + Mirror Admin UI - Research

**Researched:** 2026-04-04
**Domain:** Conda package mirroring with licensing awareness, unified admin mirror configuration UI, Docker socket-based service provisioning
**Confidence:** HIGH

## Summary

Phase 112 implements three interconnected features:
1. **Conda mirror backend** — downloads packages from Anaconda and conda-forge channels using a throwaway miniconda container, stores in `/conda/` path with repodata.json indexes, and injects `.condarc` configuration into Foundry-built images. Includes blocking ToS modal when users select the Anaconda `defaults` channel (which requires commercial license for orgs 200+ employees), defaulting to free conda-forge instead.
2. **Unified mirror admin UI** — expands Admin.tsx with a new "Mirrors" tab containing 8 cards (one per ecosystem: PyPI, APT, apk, npm, NuGet, OCI Hub, OCI GHCR, Conda). Each card shows URL field, health status badge, and provisioning toggle.
3. **One-click provisioning** — operator can enable/disable mirror services via Docker Engine API (gated by `ALLOW_CONTAINER_MANAGEMENT` env var; defaults false for security). Reuses the existing Docker socket mount and Docker-py pattern established for Foundry builds.

This phase delivers MIRR-06 (Conda ToS), MIRR-08 (unified mirror config UI for all ecosystems), and MIRR-09 (Docker-based provisioning).

**Primary recommendation:** Use docker-py (installed via pip) for Docker Engine API access, matching the ecosystem socket pattern. For Conda downloads, use miniconda:latest from continuumio (143MB Alpine base available). Repodata regeneration: run `conda index` inside throwaway container post-download. ToS acknowledgment: store as Config DB key (simpler than User column) with per-user first-encounter dismissal in localStorage (current session only, re-appears on reload for other users).

---

<user_constraints>

## User Constraints (from CONTEXT.md)

### Locked Decisions

**Conda ToS handling:**
- Selecting Anaconda `defaults` channel shows blocking modal explaining commercial ToS; recommends conda-forge
- Dialog requires operator acknowledgment before proceeding
- Default channel for new Conda ingredients: conda-forge (pre-selected)
- ToS acknowledgment persisted per-user — once acknowledged by user, that user won't see it again; other users still see it
- Operators can enter custom channel URLs (free-text) beyond conda-forge and defaults

**Admin mirror config UI:**
- Lives as "Mirrors" tab in existing Admin.tsx
- One card per ecosystem (8 cards: PyPI, APT, apk, npm, NuGet, OCI Hub, OCI GHCR, Conda)
- Each card: URL field, live health badge (HTTP health check), service provisioning toggle
- Admin-only (requires admin role); operators can view but not edit mirror URLs
- Backend: expand `MirrorConfigUpdate` with all ecosystem URLs
- GET/PUT `/api/admin/mirror-config` endpoints

**One-click provisioning (MIRR-09):**
- Uses Docker Engine API via mounted Docker socket (same trust model as Portainer/Watchtower)
- Gated by `ALLOW_CONTAINER_MANAGEMENT` env var (default `false`, secure by default)
- When `true`: toggles per ecosystem, agent creates/starts/stop mirror sidecars, hardcoded container configs
- When `false`: toggles replaced with read-only badges + banner showing `docker compose -f compose.ee.yaml up -d <service>` command
- Auto-pulls images if not locally available
- UI per card: enable/disable toggle + running/stopped/error status indicator (no log streaming)

**Conda mirror approach:**
- Download: `conda create --download-only` in throwaway miniconda container (same pattern as APT/apk)
- Storage: `mirror-data/conda/{channel}/{subdir}/` with repodata.json
- Serving: Caddy static files via existing mirror sidecar, add `/conda/` path to Caddyfile
- Foundry injection: `.condarc` injected only when blueprint has CONDA ecosystem ingredients
- Conda ingredients require conda-capable base (miniconda); Foundry errors at build time if base doesn't have conda
- New env var: `CONDA_MIRROR_URL` (default: `http://mirror:8081/conda`)

**Security documentation:**
- Document Docker socket implications and `ALLOW_CONTAINER_MANAGEMENT` setting
- Recommend running Axiom in sandbox/VM
- Document scope: Foundry builds (always) vs container management (opt-in)

### Claude's Discretion

- Exact miniconda throwaway container image and lifecycle
- repodata.json regeneration approach after downloads
- Docker Engine API client choice (docker-py vs raw HTTP to socket) — **RECOMMENDS docker-py**
- Exact container configs for provisioning (image tags, volume paths, network attachment)
- Health check endpoint response shape extensions
- How per-user ToS acknowledgment stored (User column vs Config DB key) — **RECOMMENDS Config DB key**
- Caddy path structure for conda channel/subdir layout

### Deferred Ideas (OUT OF SCOPE)

- Transitive Conda dependency resolution — v20.0 ADV-01
- Conda channel selector stored per ingredient (conda-forge vs defaults vs custom) — v20.0 ADV-02
- Full conda channel sync (all platforms/versions) — 500GB+, filtered sync only
- Container log streaming in provisioning UI — keep it simple
- Rootless builder (Buildah/Kaniko) — longer-term security improvement

</user_constraints>

<phase_requirements>

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| MIRR-06 | Conda mirror backend with Anaconda ToS warning when operator selects defaults channel | Conda defaults channel requires commercial license for orgs 200+ employees (per Anaconda Legal); `.condarc` YAML format supports channel lists; miniconda:latest available 143MB; `conda index` regenerates repodata.json |
| MIRR-08 | Admin mirror configuration UI includes URL fields for all new ecosystems (apk, OCI, Verdaccio, Conda, BaGetter) | MirrorConfigUpdate expanded to 8 fields; Tabs pattern in Admin.tsx proven; health check socket pattern established in smelter_router; POST /api/admin/mirror-config endpoint exists |
| MIRR-09 | Operator can enable/disable mirror services from Admin dashboard (one-click provisioning via Docker socket) | docker-py (version 7.1.0+) enables container create/start/stop via Docker socket; ALLOW_CONTAINER_MANAGEMENT env var gates feature; container configs hardcoded; compose.ee.yaml already defines mirror services with profiles |

</phase_requirements>

---

## Standard Stack

### Core Conda Libraries

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| miniconda | latest | Minimal Python + conda (143MB) | Official, lightweight, throwaway container pattern |
| conda-build | installed in container | `conda index` command for repodata.json regeneration | Official conda ecosystem standard |
| docker-py | 7.1.0+ | Docker Engine API access in Python | Matches existing Foundry pattern; asyncio-friendly via threading |

### Supporting Libraries

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| pyyaml | in Python stdlib | Parse/write `.condarc` YAML files | Standard conda config format |
| aiofiles | existing dependency | Non-blocking file I/O for config generation | Consistent with async mirror_service pattern |

### Existing Reusable Patterns

- **Throwaway container downloads**: `docker run --rm -v {dest}:/output {image} bash -c "cmd"` — same as APT/APK mirrors
- **asyncio.to_thread(subprocess.run(...))** — async subprocess execution, 120s timeout standard
- **Ecosystem-based dispatch**: `if ingredient.ecosystem == "CONDA": await _mirror_conda(...)` — pattern in mirror_service.py
- **Caddy static file serving**: `/apk/*`, `/apt/*` → static paths, `/conda/*` follows same pattern
- **Compose profiles**: `profiles: - mirrors` gates sidecar services in compose.ee.yaml

---

## Architecture Patterns

### Conda Mirror Backend Integration

**Storage structure:**
```
mirror-data/
└── conda/
    ├── conda-forge/
    │   ├── linux-64/
    │   │   ├── repodata.json
    │   │   ├── repodata.json.bz2
    │   │   └── [packages].tar.bz2
    │   ├── osx-64/
    │   └── win-64/
    └── defaults/
    └── [custom-channel]/
```

**Conda download approach (async):**
1. Create throwaway miniconda container with network access
2. Run: `conda create --name mirror --download-only -c {channel} {package}=={version}`
3. Extract from `/opt/conda/pkgs/` → `mirror-data/conda/{channel}/{subdir}/`
4. Run: `conda index {dir}` inside container to regenerate `repodata.json` + `repodata.json.bz2`
5. Mark `ingredient.mirror_status = "MIRRORED"`

**Conda repodata.json format (verified):**
- JSON file: maps conda package filename → metadata dict
- Contains: `repodata_version=1` header, per-package index with build string, dependencies, license, sha256
- Official schema: [conda/schemas/repodata-1.schema.json](https://github.com/conda/schemas/blob/main/repodata-1.schema.json)
- Sharded repodata available for large channels (CEP-16), but not required for mirroring

**Pattern 1: Conda Mirror Service Method**
```python
# In mirror_service.py alongside _mirror_pypi(), _mirror_apt(), etc.
@staticmethod
async def _mirror_conda(db: AsyncSession, ingredient: ApprovedIngredient):
    """
    Download conda package from specified channel using throwaway miniconda container.
    Regenerates repodata.json using conda index.
    """
    try:
        channel = ingredient.conda_channel or "conda-forge"  # Default to free channel
        subdir = "linux-64"  # Can expand to osx-64, win-64 per platform requirements
        conda_dir = os.path.join(MirrorService.CONDA_BASE_PATH, channel, subdir)
        os.makedirs(conda_dir, exist_ok=True)

        # Package spec: name==version
        pkg_spec = f"{ingredient.name}=={ingredient.version_constraint or '*'}"

        cmd = [
            "docker", "run", "--rm",
            "-v", f"{conda_dir}:/mirror",
            "continuumio/miniconda3:latest",
            "bash", "-c",
            f"conda create --prefix /tmp/env --download-only -c {channel} {pkg_spec} && "
            f"cp /tmp/env/pkgs/*.tar.bz2 /mirror/ && "
            f"conda index /mirror"
        ]

        process = await asyncio.to_thread(
            subprocess.run, cmd, capture_output=True, text=True, timeout=300
        )

        if process.returncode == 0:
            ingredient.mirror_status = "MIRRORED"
            ingredient.mirror_log = f"Downloaded {pkg_spec} from {channel}"
        else:
            ingredient.mirror_status = "FAILED"
            ingredient.mirror_log = process.stderr

        await db.commit()
    except Exception as e:
        ingredient.mirror_status = "FAILED"
        ingredient.mirror_log = str(e)
        await db.commit()
```

**Pattern 2: .condarc Generation (Foundry Injection)**
```python
# In mirror_service.py
@staticmethod
def get_condarc_content(conda_channels: list[str] = None) -> str:
    """
    Generate .condarc YAML for Foundry-built image.
    Default channels: conda-forge (free), with option to add custom/defaults.
    """
    channels = conda_channels or ["conda-forge"]
    return f"""channels:
  - {chr(10).join(f'  - {c}' for c in channels)}
show_channel_urls: true
channel_alias: https://conda.anaconda.org
ssl_verify: true
"""
```

Used in `foundry_service.py:build_template()`:
```python
if "CONDA" in [i.ecosystem for i in ingredients]:
    condarc = MirrorService.get_condarc_content([
        f"{CONDA_MIRROR_URL}/conda-forge",
        "conda-forge"  # Fallback to public
    ])
    # Write /root/.condarc in Dockerfile during build
```

### Mirror Admin UI Integration

**Pattern 3: Mirrors Tab in Admin.tsx**
```typescript
// In Admin.tsx, expand Tabs component:
<Tabs defaultValue="system">
  <TabsList>
    <TabsTrigger value="system">System</TabsTrigger>
    <TabsTrigger value="mirrors">Mirrors</TabsTrigger>  {/* NEW */}
    <TabsTrigger value="users">Users</TabsTrigger>
    {/* ... existing tabs ... */}
  </TabsList>

  <TabsContent value="mirrors">
    <MirrorCardsGrid /> {/* 8 cards, one per ecosystem */}
  </TabsContent>
</Tabs>
```

**Mirror Config Card Component:**
```typescript
// Mirror card structure (PyPI, APT, apk, npm, NuGet, OCI Hub, OCI GHCR, Conda)
<Card>
  <CardHeader>
    <CardTitle className="flex items-center gap-2">
      {icon}
      PyPI Mirror
    </CardTitle>
  </CardHeader>
  <CardContent className="space-y-4">
    <div>
      <Label>Mirror URL</Label>
      <Input
        value={config.pypi_mirror_url}
        onChange={(e) => updateUrl("pypi_mirror_url", e.target.value)}
        disabled={!isAdmin}
      />
    </div>

    <div className="flex items-center gap-2">
      <span>Health:</span>
      <HealthBadge status={health.pypi} />
    </div>

    {ALLOW_CONTAINER_MANAGEMENT ? (
      <ToggleSwitch
        enabled={runningServices.includes("pypi")}
        onChange={(enabled) => toggleService("pypi", enabled)}
      />
    ) : (
      <MirrorDisabledBanner>
        docker compose -f compose.ee.yaml up -d pypi
      </MirrorDisabledBanner>
    )}
  </CardContent>
</Card>
```

### Conda ToS Acknowledgment

**Pattern 4: Per-User ToS Modal (localStorage + Config DB)**
```typescript
// In Templates.tsx or Smelter UI when user selects "defaults" channel:
const [tosAcknowledged, setTosAcknowledged] = useState(false);

const handleSelectChannel = (channel: string) => {
  if (channel === "defaults" && !tosAcknowledged) {
    // Check Config DB for user's ToS acknowledgment (first encounter per user)
    const userKey = `conda_tos_${currentUser.username}`;
    const configValue = await authenticatedFetch(`/api/config/${userKey}`);

    if (!configValue.value) {
      // Show blocking modal
      setShowCondaToSModal(true);
    } else {
      setTosAcknowledged(true);
    }
  }
};

const handleAcceptTos = async () => {
  // Persist to Config DB so this user doesn't see it again
  await authenticatedFetch("/api/config", {
    method: "POST",
    body: JSON.stringify({
      key: `conda_tos_${currentUser.username}`,
      value: new Date().toISOString()
    })
  });

  // Set localStorage session-only flag for UI responsiveness
  localStorage.setItem("conda_tos_accepted_this_session", "true");
  setTosAcknowledged(true);
  proceed();
};
```

### Docker Socket Service Provisioning

**Pattern 5: Provisioning Service (docker-py)**
```python
# New module: agent_service/services/provisioning_service.py
import docker
from docker.types import Mount

class ProvisioningService:
    def __init__(self):
        self.client = docker.from_env()  # Uses /var/run/docker.sock

    async def start_mirror_service(self, service_name: str) -> dict:
        """
        Start a mirror service container (pypi, verdaccio, bagetter, etc).
        Returns {success, status, message}.
        """
        try:
            if service_name not in MIRROR_CONFIGS:
                return {"success": False, "message": f"Unknown service: {service_name}"}

            config = MIRROR_CONFIGS[service_name]

            # Check if already running
            try:
                container = self.client.containers.get(config["container_name"])
                if container.status == "running":
                    return {"success": True, "status": "running"}
                else:
                    container.start()
                    return {"success": True, "status": "running"}
            except docker.errors.NotFound:
                # Pull image if not available
                try:
                    self.client.images.get(config["image"])
                except docker.errors.ImageNotFound:
                    await asyncio.to_thread(
                        self.client.images.pull, config["image"]
                    )

                # Create and start container
                self.client.containers.run(
                    image=config["image"],
                    name=config["container_name"],
                    ports=config["ports"],
                    volumes=config["volumes"],
                    environment=config["environment"],
                    restart_policy={"Name": "always"},
                    detach=True
                )
                return {"success": True, "status": "created"}
        except Exception as e:
            return {"success": False, "message": str(e)}

    async def stop_mirror_service(self, service_name: str) -> dict:
        """Stop a mirror service container."""
        try:
            config = MIRROR_CONFIGS[service_name]
            container = self.client.containers.get(config["container_name"])
            container.stop()
            return {"success": True, "status": "stopped"}
        except docker.errors.NotFound:
            return {"success": True, "status": "not_running"}
        except Exception as e:
            return {"success": False, "message": str(e)}

# Hardcoded mirror configs
MIRROR_CONFIGS = {
    "pypi": {
        "image": "pypiserver/pypiserver:latest",
        "container_name": "axiom-mirror-pypi",
        "ports": {"8080/tcp": 8080},
        "volumes": {"/app/mirror_data/pypi": {"bind": "/data/packages", "mode": "rw"}},
        "environment": ["-P", ".", "-a", "."],
    },
    "verdaccio": {
        "image": "verdaccio/verdaccio:latest",
        "container_name": "axiom-mirror-verdaccio",
        "ports": {"4873/tcp": 4873},
        "volumes": {"/app/mirror_data/verdaccio": {"bind": "/verdaccio/storage", "mode": "rw"}},
        "environment": ["VERDACCIO_PORT=4873"],
    },
    # ... etc for bagetter, oci-cache-hub, oci-cache-ghcr, mirror (caddy), conda
}
```

**Pattern 6: Provisioning Route (FastAPI)**
```python
# In smelter_router.py
@smelter_router.post("/api/admin/mirror-services/{service}/start", tags=["Mirror Provisioning"])
async def start_mirror_service(
    service: str,
    current_user: User = Depends(require_permission("admin:write")),
    db: AsyncSession = Depends(get_db)
):
    """Start a mirror sidecar service (gated by ALLOW_CONTAINER_MANAGEMENT)."""
    if not os.getenv("ALLOW_CONTAINER_MANAGEMENT", "false").lower() == "true":
        raise HTTPException(
            status_code=403,
            detail="Container management disabled (ALLOW_CONTAINER_MANAGEMENT=false)"
        )

    result = await ProvisioningService().start_mirror_service(service)

    if result["success"]:
        await audit(db, "mirror_service_started", {"service": service})
        return {"status": "running"}
    else:
        raise HTTPException(status_code=500, detail=result["message"])

@smelter_router.post("/api/admin/mirror-services/{service}/stop", tags=["Mirror Provisioning"])
async def stop_mirror_service(
    service: str,
    current_user: User = Depends(require_permission("admin:write")),
    db: AsyncSession = Depends(get_db)
):
    """Stop a mirror sidecar service."""
    if not os.getenv("ALLOW_CONTAINER_MANAGEMENT", "false").lower() == "true":
        raise HTTPException(status_code=403, detail="Container management disabled")

    result = await ProvisioningService().stop_mirror_service(service)
    await audit(db, "mirror_service_stopped", {"service": service})
    return {"status": result["status"]}
```

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Conda package downloads | Custom channel parser, manual .tar.bz2 extraction | `conda create --download-only` in miniconda container | Official tool handles platform variants, dependency resolution, channel validation |
| repodata.json generation | Manual JSON construction, sqlite index parsing | `conda index` command (in container) | Official, handles checksums, dependency metadata, multiple architectures |
| Docker container management | Raw socket protocol, manual JSON API calls | docker-py (Python SDK) | Type-safe, event handling, error recovery, async-compatible via threading |
| .condarc YAML generation | String concatenation | pyyaml library (Python stdlib yaml) | Proper escaping, nested structures, prevents injection attacks |
| Conda channel verification | Manual HTTP GET to channel | Existing health check pattern (socket.create_connection) | Consistent with APT/APK health checks, reuses infrastructure |

**Key insight:** Conda ecosystem is battle-tested at scale; don't invent custom download/index logic. `conda` CLI is designed for this; running it in a container is the standard air-gap pattern.

---

## Common Pitfalls

### Pitfall 1: Alpine + Conda Glibc Mismatch
**What goes wrong:** Conda packages are built against glibc (Debian/RHEL standard). Alpine uses musl libc. Trying to run conda packages from defaults channel in Alpine container → missing libc symbols, crashes.

**Why it happens:** Phase context states "Conda ingredients require conda-capable base (miniconda)"; not all base images have miniconda. APK mirrors work in Alpine because apk ecosystem is Alpine-native. Conda's binary wheel ecosystem assumes glibc.

**How to avoid:** Foundry build validation (Phase 112 plan) must check: if blueprint includes CONDA ecosystem ingredients, base image must contain miniconda (e.g., `continuumio/miniconda3` or `conda/miniconda3`). Error at build time with clear message: `"Conda ingredients require miniconda base image; selected base doesn't include conda."` Same pattern as npm requiring Node.js, NuGet requiring dotnet SDK.

**Warning signs:** Build logs show `ImportError: libc.so.6 not found` or `cannot execute binary file: Exec format error` on conda packages in Alpine container.

### Pitfall 2: Anaconda Defaults Channel ToS Traps Operators
**What goes wrong:** Operator selects "defaults" channel in mirror config or ingredient approval, proceeds, realizes organization now owes license fees retroactively. Compliance team angry.

**Why it happens:** CONTEXT.md decision: "blocking modal recommends conda-forge" — but if dismissed or if modal implementation is weak, operator can miss the warning.

**How to avoid:**
- Modal is **non-bypassable** (not just a toast, not dismissible via X button, no "don't show again" at first encounter)
- Default to conda-forge (pre-selected) in all UI dropdowns; make defaults opt-in
- Persist acknowledgment per-user to Config DB (not just session)
- Admin docs must prominently call out: "Anaconda defaults channel requires commercial license for organizations 200+ employees. Use conda-forge (free) instead."

**Warning signs:** UI allows quick channel selection without confirmation; no Config DB persistence check; organization size not mentioned in onboarding.

### Pitfall 3: Docker Socket Provisioning Security Bypass
**What goes wrong:** `ALLOW_CONTAINER_MANAGEMENT` env var is "off" by default, but:
- Someone manually sets it to "true" without reviewing security implications
- Provisioning endpoints accidentally left unprotected (missing auth/permission check)
- Random user starts/stops services, crashes mirror infrastructure

**Why it happens:** Socket is powerful; root-equivalent access to container engine. Needs explicit operator intent + admin role.

**How to avoid:**
- `ALLOW_CONTAINER_MANAGEMENT` defaults to `false` in .env.example (secure by default)
- All provisioning routes require `require_permission("admin:write")` (not just "foundry:write")
- Banner shown when disabled: "Container management disabled. Enable in secrets.env if you trust this environment."
- Audit log every start/stop via `audit()` helper

**Warning signs:** Non-admin user can toggle mirrors; disabled banner not showing; env var always true in quick-start docs.

### Pitfall 4: repodata.json Not Regenerated After Download
**What goes wrong:** Mirror downloads package X, but repodata.json isn't updated. Later, `conda install X` from mirror fails — "package not found in index".

**Why it happens:** `conda index` needs to be run **inside the container or directory** with all packages present. If package extraction path or index command timing is off, index is stale.

**How to avoid:**
- After package download, **immediately** run `conda index /mirror_dir` in same container
- Verify index contains package name: `grep "package-name" repodata.json` in test
- Index regeneration is part of `_mirror_conda()` method, not a separate background task
- Test with actual `conda install` after mirroring to verify index is valid

**Warning signs:** Mirror page lists packages, but `conda install` from mirror fails; repodata.json has old timestamp; conda CLI returns "no packages found".

### Pitfall 5: Container Resource Limits Missing in Provisioning
**What goes wrong:** Provisioning starts mirror container without memory/CPU limits. Container eats all host resources, crashes node.

**Why it happens:** Hardcoded container configs in `MIRROR_CONFIGS` don't include resource limits; docker-py defaults to unlimited.

**How to avoid:**
- `MIRROR_CONFIGS` includes `mem_limit` (e.g., "512m") and `cpu_quota` per service
- Example: `pypi` (lightweight) = 256m, `bagetter` (heavier) = 512m
- Test locally: `docker stats` while mirror is mirroring to ensure no runaway memory
- Document in onboarding: "Mirror services consume ~1GB RAM total; ensure host has 2GB free"

**Warning signs:** Mirror container restarts frequently; OOMKilled in docker logs; single mirror start crashes multiple services.

---

## Code Examples

Verified patterns from existing codebase and official sources:

### Async Subprocess Pattern (Mirror Download)
```python
# Source: mirror_service.py _mirror_apt(), _mirror_apk() (ESTABLISHED PATTERN)
cmd = [
    "docker", "run", "--rm",
    "-v", f"{dest_path}:/output",
    "continuumio/miniconda3:latest",
    "bash", "-c",
    "conda create --download-only -c conda-forge scipy && cp /opt/conda/pkgs/*.tar.bz2 /output/"
]

process = await asyncio.to_thread(
    subprocess.run,
    cmd,
    capture_output=True,
    text=True,
    timeout=300  # 5min for larger packages
)
```

### Docker-py Container Creation
```python
# Source: Docker SDK for Python 7.1.0 documentation
# https://docker-py.readthedocs.io/en/stable/containers.html
import docker

client = docker.from_env()

# Pull image if missing
try:
    client.images.get("pypiserver/pypiserver:latest")
except docker.errors.ImageNotFound:
    client.images.pull("pypiserver/pypiserver:latest")

# Create and run
container = client.containers.run(
    image="pypiserver/pypiserver:latest",
    name="axiom-pypi",
    ports={"8080/tcp": 8080},
    volumes={"/app/mirror_data/pypi": {"bind": "/data/packages", "mode": "rw"}},
    command=["-P", ".", "-a", "."],
    restart_policy={"Name": "always"},
    detach=True  # Non-blocking
)

# Later, stop it
container.stop()
```

### .condarc YAML Generation
```python
# Source: https://docs.conda.io/projects/conda/en/latest/user-guide/configuration/use-condarc.html
# Example valid .condarc:
import yaml

config = {
    "channels": [
        f"http://mirror.local/conda/conda-forge",
        "conda-forge",  # Public fallback
    ],
    "show_channel_urls": True,
    "ssl_verify": True,
}

condarc_yaml = yaml.dump(config, default_flow_style=False)
# Output:
# channels:
# - http://mirror.local/conda/conda-forge
# - conda-forge
# show_channel_urls: true
# ssl_verify: true
```

### Caddy Config for Conda Path
```caddy
# Source: Caddyfile (existing pattern for /apt, /apk, /simple)
# Add to existing Caddyfile:
handle /conda/* {
    uri strip_prefix /conda
    root * /data/conda
    file_server browse
}

# Result: http://mirror:8081/conda/conda-forge/linux-64/repodata.json
#         → serves /data/conda/conda-forge/linux-64/repodata.json
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Manual conda package sync scripts (e.g., conda-mirror, mamba-repodata-patch) | Use container-isolated `conda create --download-only` in throwaway miniconda | 2023-2024 (industry shift to air-gap tooling) | Reproducible, no host dependencies, works in CI/CD |
| Hard-coded mirror URLs in image build | Injected .condarc at Foundry build time per blueprint | Phase 111+ (ecosystem-aware Foundry) | Per-ecosystem config, supports multiple channels |
| Operator CLI-only provisioning (`docker compose up -d <service>`) | Docker socket API with web UI toggles (ALLOW_CONTAINER_MANAGEMENT) | Phase 112 (this phase) | Non-technical operators can enable mirrors, audit trail |
| Single PyPI/APT mirror per deployment | 8-ecosystem mirror suite (PyPI, APT, apk, npm, NuGet, OCI Hub, OCI GHCR, Conda) | Phase 109-112 | Full air-gap support for DevOps/Data/Windows workloads |

**Deprecated/outdated:**
- **conda-mirror tool (inactive since 2020):** Use `conda index` instead; it's built-in
- **devpi for mirror (Phase 108 removed):** pypiserver is simpler, adequate for air-gap
- **Manual .condarc management in CI/CD scripts:** Foundry generates it at build time

---

## Open Questions

1. **Conda package size expectations?**
   - What we know: miniconda container ~143MB, scipy+deps ~200MB, large metapackages (pytorch, tensorflow) ~1GB+
   - What's unclear: Should we add progress indicators for long-running downloads? Operator expectations for sync time?
   - Recommendation: First implementation: no progress (async task), show mirror_status MIRRORING + last_log update in UI; Phase 113+ can add polling for progress

2. **Multi-platform conda sync (linux-64, osx-64, win-64)?**
   - What we know: repodata.json includes metadata per platform
   - What's unclear: Should Phase 112 download all platforms or just linux-64?
   - Recommendation: Phase 112 downloads linux-64 only (most common). Phase 113+ can extend to osx-64/win-64 if requested

3. **ALLOW_CONTAINER_MANAGEMENT security audit trail?**
   - What we know: audit() helper exists; feature needs admin role
   - What's unclear: Should we also log the env var value at startup? Rate-limit provisioning calls?
   - Recommendation: Add audit entry at startup: "Container management enabled" if ALLOW_CONTAINER_MANAGEMENT=true. No rate limiting (mirrors are infrastructure, not hotpath). Single audit entry per start/stop action.

4. **Conda-forge ToS vs Anaconda defaults?**
   - What we know: conda-forge is free (community-run); defaults requires license 200+ employees
   - What's unclear: Should we also warn on custom/bioconda channels?
   - Recommendation: Phase 112 blocks only `defaults`. Document custom channels as operator responsibility. Phase 113+ can add optional ToS checks via config

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (backend) + vitest (frontend) |
| Config file | `puppeteer/pytest.ini` + `puppeteer/dashboard/vitest.config.ts` |
| Quick run command | `cd puppeteer && pytest tests/test_mirror.py -k conda -x` |
| Full suite command | `cd puppeteer && pytest && cd dashboard && npm run test` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| MIRR-06 | Conda package downloaded from channel, repodata.json valid | unit | `pytest tests/test_mirror.py::test_mirror_conda_download -x` | ❌ Wave 0 |
| MIRR-06 | ToS modal blocks on defaults, allows conda-forge | integration | `pytest tests/test_smelter.py::test_conda_tos_warning -x` | ❌ Wave 0 |
| MIRR-08 | GET /api/admin/mirror-config returns all 8 ecosystem URLs | unit | `pytest tests/test_smelter.py::test_mirror_config_all_ecosystems -x` | ❌ Wave 0 |
| MIRR-08 | PUT /api/admin/mirror-config persists all fields | unit | `pytest tests/test_smelter.py::test_mirror_config_update -x` | ❌ Wave 0 |
| MIRR-09 | Docker socket provisioning starts pypi service when enabled | integration | `pytest tests/test_provisioning.py::test_start_mirror_service -x` | ❌ Wave 0 |
| MIRR-09 | Provisioning endpoints require admin role | unit | `pytest tests/test_smelter.py::test_provisioning_auth -x` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `cd puppeteer && pytest tests/test_mirror.py tests/test_smelter.py -x` (conda + mirror config tests)
- **Per wave merge:** Full backend + frontend suite + Playwright validation of Admin Mirrors tab
- **Phase gate:** Full suite green + Playwright verification that Mirrors tab renders, toggles work (when ALLOW_CONTAINER_MANAGEMENT=true)

### Wave 0 Gaps
- [ ] `puppeteer/agent_service/tests/test_mirror.py` — test `_mirror_conda()`, `get_condarc_content()`, repodata validation
- [ ] `puppeteer/agent_service/tests/test_provisioning.py` — test docker-py container start/stop, image pull, hardcoded configs
- [ ] `puppeteer/agent_service/tests/test_smelter.py` — expand existing with mirror config all-ecosystems, provisioning auth, conda ToS
- [ ] `puppeteer/dashboard/src/views/__tests__/Admin.test.tsx` — Mirrors tab rendering, card structure, health badge updates
- [ ] `mop_validation/scripts/test_playwright.py` — add Playwright test for Mirrors tab in light/dark theme, provisioning toggle (conditional on ALLOW_CONTAINER_MANAGEMENT)
- [ ] Framework install: `pip install docker` (docker-py for backend), `npm install` already covers vitest

---

## Sources

### Primary (HIGH confidence)
- Docker SDK for Python (docker-py) 7.1.0 documentation — Container creation, image pull, socket connection
  - [Docker SDK for Python — Docker SDK for Python 7.1.0 documentation](https://docker-py.readthedocs.io/)
  - [Containers — Docker SDK for Python 7.1.0 documentation](https://docker-py.readthedocs.io/en/stable/containers.html)

- Conda Official Documentation — .condarc format, channel configuration, repodata schema
  - [Using the .condarc conda configuration file — conda 26.3.1.dev6 documentation](https://docs.conda.io/projects/conda/en/latest/user-guide/configuration/use-condarc.html)
  - [schemas/repodata-1.schema.json at main · conda/schemas](https://github.com/conda/schemas/blob/main/repodata-1.schema.json)
  - [Channels — conda 26.1.2.dev71 documentation](https://docs.conda.io/projects/conda/en/latest/user-guide/concepts/channels.html)

- Anaconda Licensing — Defaults channel commercial license, conda-forge free
  - [Anaconda Legal](https://www.anaconda.com/legal)
  - [Is conda actually free?](https://pydevtools.com/handbook/explanation/is-conda-actually-free/)
  - [Navigating Anaconda Licensing Changes: What You Need to Know | DataCamp](https://datacamp.com/blog/navigating-anaconda-licensing)

- Miniconda Container Images — Official images, sizes, async docker pulls
  - [continuumio/miniconda3 - Docker Image](https://hub.docker.com/r/continuumio/miniconda3)
  - [conda/miniconda3 - Docker Image](https://hub.docker.com/r/conda/miniconda3/)

### Secondary (MEDIUM confidence)
- Conda Repodata Format and CEP-16 (sharded) — Optional for Phase 112 (standard repodata sufficient)
  - [CEP 16 - Sharded Repodata | conda.org](https://conda.org/learn/ceps/cep-0016/)
  - [Conda Repodata](https://jcristharif.com/msgspec/examples/conda-repodata.html)

- Docker-py GitHub and PyPI — Library status, active maintenance
  - [GitHub - docker/docker-py: A Python library for the Docker Engine API](https://github.com/docker/docker-py)
  - [docker · PyPI](https://pypi.org/project/docker/)

---

## Metadata

**Confidence breakdown:**
- Standard stack (miniconda, conda-py, docker-py): **HIGH** — official docs verified, versions confirmed current (2025-2026)
- Architecture (Conda mirror backend pattern): **HIGH** — mirrors APT/APK established patterns; `conda create --download-only` is official approach
- Docker provisioning (docker-py): **HIGH** — SDK 7.1.0+ active, widely used for container lifecycle
- ToS licensing (Anaconda defaults vs conda-forge): **HIGH** — Anaconda legal page explicit; conda-forge community documentation clear
- Pitfalls (Alpine glibc, ToS traps, socket security): **MEDIUM-HIGH** — derived from industry best practices + CONTEXT.md decisions; some edge cases (multi-platform sync) marked as future work

**Research date:** 2026-04-04
**Valid until:** 2026-05-04 (30 days for stable stack; conda and docker-py release cycles are slow)
**Next refresh needed if:** New conda-build release changes index format, or docker-py 8.0 incompatible API change
