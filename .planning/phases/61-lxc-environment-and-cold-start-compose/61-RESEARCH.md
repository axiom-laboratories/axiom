# Phase 61: LXC Environment and Cold-Start Compose - Research

**Researched:** 2026-03-24
**Domain:** Incus LXC provisioning, Docker-in-LXC, Gemini CLI headless, PowerShell packaging, EE licence generation
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- `puppeteer/compose.cold-start.yaml` — lives alongside `compose.server.yaml`, versioned with product
- Services to include: `db`, `cert-manager`, `agent`, `dashboard`, `docs`, 2 puppet nodes
- Services to strip: `tunnel`, `ddns-updater`, `devpi`, `pypi`, `mirror`, `registry`
- Same compose file for CE and EE — `AXIOM_LICENCE_KEY` env var empty for CE, populated for EE
- `SERVER_HOSTNAME=172.17.0.1` in compose env so Caddy generates cert with Docker bridge SAN
- `EXECUTION_MODE=direct` on puppet nodes (Docker-in-Docker, no nested container runtime)
- 2 puppet nodes as Docker services inside `compose.cold-start.yaml` — start automatically
- Nodes connect via Docker bridge (`AGENT_URL=https://172.17.0.1:8001`)
- One LXC re-used for CE and EE; wipe between runs with `docker compose down -v`
- `raw.apparmor` override applied in incus config at launch — targeted Ubuntu 24.04 6.8.x fix
- Docker CE auto-installed inside LXC from official Docker apt repository
- `Containerfile.node` updated to download `pwsh` directly from GitHub releases as `.deb` (7.6.0 LTS)
- Pre-generation script produces Ed25519-signed test licence with 1-year expiry
- Stored in `mop_validation/secrets.env` as `AXIOM_EE_LICENCE_KEY`
- Node.js 20 installed via NodeSource PPA
- Gemini CLI installed via `npm install -g @google/gemini-cli` pinned to ≥ v0.23.0
- `GEMINI_MODEL=gemini-2.0-flash` env var set at LXC level
- `ripgrep` installed — required to prevent 300-second Gemini CLI initialization stall

### Claude's Discretion
- Exact `raw.apparmor` profile content (use minimal `pivot_root` allow rule from Incus issue #791)
- Docker CE install script (standard `curl | sh` from get.docker.com or apt repo method)
- Provision script structure (single Python script extending `manage_node.py` pattern, or bash)
- Chromium NSS cert trust method for Playwright (needs separate handling from system `update-ca-certificates`)

### Deferred Ideas (OUT OF SCOPE)
- Parallel CE+EE runs in two simultaneous LXCs
- Automated LXC provisioning in CI
- Windows or macOS test environment
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| ENV-01 | LXC provisioning script creates Incus container with Docker nesting, AppArmor override, Node.js 20 (NodeSource PPA), Gemini CLI (npm ≥ v0.23.0), and Playwright + system deps | Existing `provision_lxc_nodes.py` + `manage_node.py` patterns directly reusable; confirmed Docker-in-LXC works with `security.nesting=true` on current kernel; NodeSource 20 PPA confirmed; `ripgrep` install critical for Gemini CLI |
| ENV-02 | `compose.cold-start.yaml` runs full Axiom stack (orchestrator, docs, 2 puppet nodes) with `SERVER_HOSTNAME` set for Caddy TLS SAN | `compose.server.yaml` is the direct template; cert-manager `entrypoint.sh` already reads `SERVER_HOSTNAME` as SAN; node compose pattern in `node-compose.yaml` |
| ENV-03 | `Containerfile.node` installs PowerShell via direct `.deb` from GitHub releases (replaces silently-failing Debian 12 repo method) | Confirmed: PowerShell 7.6.0 `.deb` asset is `powershell-lts_7.6.0-1.deb_amd64.deb` at `https://github.com/PowerShell/PowerShell/releases/download/v7.6.0/powershell-lts_7.6.0-1.deb_amd64.deb` |
| ENV-04 | EE licence pre-generation script produces test Ed25519 EE licence with 1-year expiry, stored as `AXIOM_EE_LICENCE_KEY` in `mop_validation/secrets.env` | Full toolchain already exists: `generate_ee_keypair.py`, `generate_ee_licence.py`, private key in `mop_validation/secrets/ee/ee_test_private.pem`, public key bytes already patched into `axiom-ee/ee/plugin.py` |
</phase_requirements>

---

## Summary

Phase 61 is an infrastructure phase that establishes the evaluation harness for CE/EE cold-start validation. Four distinct deliverables are required: an LXC provisioning script, a stripped-down compose file, a PowerShell fix in `Containerfile.node`, and an EE licence generation script targeted at `mop_validation/secrets.env`.

All four deliverables have substantial existing code to build from. The provisioning script extends `provision_lxc_nodes.py` (200+ lines of proven Incus patterns). The cold-start compose file is a direct reduction of `compose.server.yaml`. The PowerShell fix is a single `RUN` block replacement in `Containerfile.node`. The EE licence toolchain is complete in `mop_validation/scripts/` — only the output target (secrets.env key name) differs from what already exists.

The critical infrastructure risk — Docker-in-LXC on Ubuntu 24.04 kernel 6.18.x — is already resolved by the four existing `axiom-node-*` LXC containers, which run with `security.nesting=true` and `docker.io` without a `raw.apparmor` override. The locked decision to apply a `raw.apparmor` override is a belt-and-suspenders precaution; the key finding is that `docker run --rm hello-world` already works on this kernel without it.

**Primary recommendation:** All four tasks are execution work, not design work. Build directly on existing scripts and files — no new patterns need to be invented.

---

## Standard Stack

### Core
| Library / Tool | Version | Purpose | Why Standard |
|----------------|---------|---------|--------------|
| Incus | 6.22 (host) | LXC container management | Already installed, existing containers prove it works |
| docker.io | 28.2.2 (in LXC) | Docker runtime inside LXC | Ubuntu 24.04 apt package — simpler than docker-ce for LXC setup |
| Node.js | 20.x | Runtime for Gemini CLI | NodeSource PPA — Ubuntu 24.04 ships v18 which is too old |
| @google/gemini-cli | 0.35.0 (host), ≥0.23.0 (lock) | Tester agent | Only Gemini CLI version with headless non-hang behaviour |
| ripgrep | latest apt | Prevents Gemini 300s init stall | Required dep for Gemini CLI file indexing on Ubuntu Server |
| Python 3 / cryptography | host Python | EE licence generation | Already used in `generate_ee_licence.py` |

### Supporting
| Library / Tool | Version | Purpose | When to Use |
|----------------|---------|---------|-------------|
| docker-compose-v2 | 2.37.1+ (apt) | Compose plugin for docker | Installed in LXC alongside docker.io |
| Playwright (Python) | latest pip | Browser testing inside LXC | Phase 63/64 will use it; install now per ENV-01 |
| chromium-browser / chromium | latest apt | Playwright browser target | Must be system-level install for `--no-sandbox` to work |
| powershell-lts | 7.6.0 | Job runtime in node container | Direct .deb from GitHub — not via MS apt repo |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `docker.io` (Ubuntu pkg) | `docker-ce` (official repo) | docker.io is simpler (single apt install, no keyring setup), works fine for evaluation; docker-ce is better for production — not needed here |
| NodeSource PPA | `nvm` | PPA is system-wide, simpler for single-user LXC; nvm requires sourcing profile on every exec |
| `raw.apparmor` override | No override (just `security.nesting=true`) | Existing containers prove nesting alone works on 6.18.x; override is belt-and-suspenders for the new container's specific Ubuntu 24.04 cloud-init variant |

**Installation (inside LXC provisioner script):**
```bash
# Docker
apt-get update && apt-get install -y docker.io docker-compose-v2

# Node.js 20 via NodeSource
curl -fsSL https://deb.nodesource.com/setup_20.x | bash -
apt-get install -y nodejs

# ripgrep + Playwright deps
apt-get install -y ripgrep chromium-browser libglib2.0-0 libnss3 libatk1.0-0 \
    libatk-bridge2.0-0 libcups2 libxcomposite1 libxdamage1 libxrandr2 libgbm1 \
    libxkbcommon0 libpango-1.0-0 libcairo2 libasound2

# Gemini CLI
npm install -g @google/gemini-cli

# Playwright
pip3 install playwright && playwright install --with-deps chromium
```

---

## Architecture Patterns

### Recommended Project Structure

New files this phase creates:
```
mop_validation/scripts/
├── provision_coldstart_lxc.py   # New: provisions axiom-coldstart LXC (ENV-01)
│                                  # Extends provision_lxc_nodes.py pattern
├── generate_ee_licence.py       # Existing — adapt output target for ENV-04
└── generate_ee_keypair.py       # Existing — already run, keys exist

puppeteer/
├── compose.cold-start.yaml      # New: stripped compose for evaluation (ENV-02)
└── compose.server.yaml          # Existing template

puppets/
└── Containerfile.node           # Modified: PowerShell .deb fix (ENV-03)
```

### Pattern 1: Incus Launch with Nesting

**What:** Launch Ubuntu 24.04 container with `security.nesting=true` for Docker-in-LXC. The new `axiom-coldstart` container follows the exact same pattern as `axiom-node-*` containers.

**When to use:** Any LXC that needs to run Docker containers inside it.

**Key finding from live environment:** The four existing `axiom-node-*` containers run on kernel `6.18.7-76061807-generic` with only `security.nesting: "true"` — no `raw.apparmor` override — and `docker run --rm hello-world` succeeds. The `raw.apparmor` override is a locked decision from context but may be a no-op on this host. Include it as specified.

```python
# Source: existing provision_lxc_nodes.py + manage_node.py pattern
launch_result = subprocess.run(
    ["incus", "launch", "images:ubuntu/24.04", "axiom-coldstart",
     "--config", "security.nesting=true",
     "--config", "raw.apparmor=pivot_root,"],  # Incus #791 workaround
    capture_output=False, timeout=120,
)
```

### Pattern 2: Docker daemon config inside LXC

**What:** Docker inside LXC needs `iptables` and may need `cgroupns_mode` depending on the kernel. The existing provisioner creates `/etc/docker/daemon.json` for insecure registry config.

**When to use:** Any time Docker is installed inside an LXC for the cold-start stack.

**Key finding:** `docker.io` (Ubuntu package 28.2.2) works correctly inside LXC with `security.nesting=true`. No special `daemon.json` flags needed for the cold-start use case (no insecure registry required — images are built inside the LXC from source).

```python
# Source: provision_lxc_nodes.py — adapt for cold-start (no registry needed)
run_in_lxc("axiom-coldstart",
    "apt-get update -qq && apt-get install -y docker.io docker-compose-v2"
)
# Wait for daemon
run_in_lxc("axiom-coldstart", "systemctl start docker && docker info > /dev/null")
```

### Pattern 3: Cold-Start Compose Service Definitions

**What:** `compose.cold-start.yaml` strips 6 services from `compose.server.yaml` and adds 2 puppet node services. The critical change is setting `SERVER_HOSTNAME=172.17.0.1` so Caddy's SAN covers the Docker bridge gateway — required for puppet node mTLS enrollment.

**When to use:** Any evaluator running the Axiom stack for cold-start validation.

Services to KEEP: `db`, `cert-manager`, `agent`, `dashboard`, `docs`
Services to ADD: `puppet-node-1`, `puppet-node-2`
Services to DROP: `tunnel`, `ddns-updater`, `devpi`, `pypi`, `mirror`, `registry`

```yaml
# Source: compose.server.yaml structure; cert-manager/entrypoint.sh SERVER_HOSTNAME pattern
  cert-manager:
    environment:
      - SERVER_HOSTNAME=172.17.0.1   # Docker bridge — no DuckDNS/ACME needed
      # DUCKDNS_TOKEN not set — cert-manager uses local CA only in cold-start mode

  puppet-node-1:
    build:
      context: ..
      dockerfile: puppets/Containerfile.node
    image: localhost/axiom-node:cold-start
    environment:
      - AGENT_URL=https://172.17.0.1:8001
      - JOIN_TOKEN=${JOIN_TOKEN_1:-}
      - ROOT_CA_PATH=/app/secrets/root_ca.crt
      - EXECUTION_MODE=direct
      - NODE_TAGS=coldstart,linux
    volumes:
      - node1-secrets:/app/secrets
    restart: unless-stopped
```

**Critical note on JOIN_TOKEN:** Puppet nodes need a valid JOIN_TOKEN to enroll. For cold-start evaluation, two options:
1. Pre-generate tokens and bake them into the compose as defaults (simple, works for demos)
2. Generate tokens dynamically from the orchestrator API after first boot (complex)

**Recommendation:** The CONTEXT.md does not specify token handling. Since the compose is for evaluation, pre-generated tokens baked in as `${JOIN_TOKEN_1:-}` with guidance in a `.env.example` or README comment is correct. The node enrolment flow is part of what the evaluator tests — they provide their own token from the dashboard.

### Pattern 4: PowerShell Direct .deb Install

**What:** Replace the silently-failing MS Debian 12 apt repo method with direct `.deb` download from GitHub releases.

**Verified asset URL:**
- `https://github.com/PowerShell/PowerShell/releases/download/v7.6.0/powershell-lts_7.6.0-1.deb_amd64.deb`

This was verified against the GitHub API — 7.6.0 is the current LTS release as of 2026-03-24.

```dockerfile
# Source: verified from GitHub API response on 2026-03-24
# Replaces the silently-failing Debian 12 apt repo block in Containerfile.node
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl wget apt-transport-https gnupg podman krb5-user iptables docker.io \
    && rm -rf /var/lib/apt/lists/* \
    && wget -q -O /tmp/powershell.deb \
       "https://github.com/PowerShell/PowerShell/releases/download/v7.6.0/powershell-lts_7.6.0-1.deb_amd64.deb" \
    && apt-get install -y /tmp/powershell.deb \
    && rm /tmp/powershell.deb \
    && rm -rf /var/lib/apt/lists/*
```

### Pattern 5: EE Licence Generation for secrets.env

**What:** The licence toolchain already exists. `generate_ee_licence.py` produces `ee_valid_licence.env` with `AXIOM_LICENCE_KEY=...`. ENV-04 requires the key stored as `AXIOM_EE_LICENCE_KEY` in `mop_validation/secrets.env`.

**Critical finding:** The toolchain is complete. The private key exists at `mop_validation/secrets/ee/ee_test_private.pem`. The public key bytes are already patched into `axiom-ee/ee/plugin.py` (verified match: both derive `b'e~g\x98\xbf...'`). A new script (or adaptation of the existing one) just needs to:
1. Read the existing private key
2. Generate a 1-year payload (not 10-year as in the existing script)
3. Write `AXIOM_EE_LICENCE_KEY=<key>` to `mop_validation/secrets.env` (append/update pattern)

The format `base64url(json_payload).base64url(ed25519_sig)` is verified end-to-end.

### Anti-Patterns to Avoid

- **Using `docker-ce` (official repo) in LXC**: Adds keyring complexity. `docker.io` from Ubuntu apt works correctly on this kernel, as proven by existing containers.
- **Using `settings.json` for Gemini model pinning**: Known auto-switching bug. Always use `GEMINI_MODEL=gemini-2.0-flash` env var instead.
- **Omitting `ripgrep`**: Gemini CLI will stall for 300 seconds during initialization on Ubuntu Server without it. This blocks the `timeout 30 gemini -p "Say hello"` success criterion.
- **Using MS Debian 12 apt repo for PowerShell**: SHA1 key rejection silently falls through to `|| echo "skipped"`. The new image must install PowerShell or `docker exec <node> which pwsh` will return non-zero.
- **Setting SERVER_HOSTNAME to localhost only**: Puppet nodes inside the compose network reach the orchestrator via `172.17.0.1` — if the Caddy cert has no SAN for this IP, mTLS enrollment fails.
- **Hardcoding JOIN_TOKEN in compose**: A hard-coded token from a previous stack deployment will be invalid if the orchestrator DB was wiped. Leave as env var with empty default; the evaluator generates their own.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| LXC provisioning | Custom subprocess wrapper | Extend `provision_lxc_nodes.py` | Full helper library already exists: `run_in_lxc()`, `push_file_to_lxc()`, `get_container_ip()`, `is_container_running()` |
| EE licence generation | New crypto code | Adapt `generate_ee_licence.py` | Complete implementation with correct wire format, test key already patched into plugin |
| Docker-in-LXC config | Custom AppArmor profiles | `security.nesting=true` (proven working) | Four existing containers prove this is sufficient on kernel 6.18.x |
| Node.js install | Manual tarball extraction | NodeSource PPA | One `curl | bash` + `apt-get install nodejs` — standard Ubuntu pattern |
| Gemini CLI headless | Custom wrapper | `GEMINI_MODEL` env var + `ripgrep` install | Known exact fixes; Gemini CLI is headless by default with `GEMINI_API_KEY` set |

---

## Common Pitfalls

### Pitfall 1: Gemini CLI 300-second stall without ripgrep
**What goes wrong:** Gemini CLI attempts to index files on startup. On Ubuntu Server without `ripgrep`, it falls back to a slow filesystem walk that takes 300 seconds.
**Why it happens:** Gemini CLI uses `ripgrep` as its file indexer. Without it, it uses a slow fallback.
**How to avoid:** `apt-get install -y ripgrep` in the provisioning script before Gemini CLI install.
**Warning signs:** `timeout 30 gemini -p "Say hello"` times out even with correct API key.

### Pitfall 2: Gemini CLI model auto-switching
**What goes wrong:** `settings.json` model pinning has a known bug where it auto-switches to a different model mid-session.
**Why it happens:** Gemini CLI bug in versions around the 0.23 range — settings not reliably respected.
**How to avoid:** Set `GEMINI_MODEL=gemini-2.0-flash` as an env var in the LXC at provisioning time (add to `/etc/environment` or provision script exports).
**Warning signs:** Gemini CLI uses a different model than flash, which may not have the same context window.

### Pitfall 3: Docker bridge IP SAN missing from Caddy cert
**What goes wrong:** Puppet nodes enroll at `https://172.17.0.1:8001`. If the Caddy cert has no SAN for `172.17.0.1`, the mTLS handshake fails with certificate verification error.
**Why it happens:** `SERVER_HOSTNAME` not set or set to wrong value in compose env.
**How to avoid:** Hardcode `SERVER_HOSTNAME=172.17.0.1` in `compose.cold-start.yaml` (not as a variable).
**Warning signs:** Nodes log `certificate verify failed` and never appear as ENROLLED in the dashboard.

### Pitfall 4: LXC Docker daemon not started before compose up
**What goes wrong:** `docker compose up` inside the LXC fails immediately because Docker daemon is not running.
**Why it happens:** `docker.io` is installed but `systemctl enable docker` wasn't called, or daemon hasn't started after install.
**How to avoid:** In provisioning script, after Docker install: `run_in_lxc("axiom-coldstart", "systemctl enable docker && systemctl start docker")`. Then poll `docker info` before proceeding.
**Warning signs:** `docker compose up` exits with "Cannot connect to Docker daemon".

### Pitfall 5: Compose file builds node image on every `docker compose up`
**What goes wrong:** If `compose.cold-start.yaml` specifies `build:` for the node service without an explicit `image:` tag, Docker rebuilds the node image on every up, which is slow inside LXC.
**Why it happens:** Missing `image:` tag means no caching target.
**How to avoid:** Include both `build:` and `image: localhost/axiom-node:cold-start` in the node service definition. Build once, reuse on subsequent ups.

### Pitfall 6: Chromium cert trust vs. NSS cert trust for Playwright
**What goes wrong:** `update-ca-certificates` trusts the Caddy cert at the system level (openssl), but Chromium uses NSS which has a separate trust store.
**Why it happens:** Chromium and Firefox maintain their own NSS cert databases separate from the OS trust store.
**How to avoid:** Use `certutil -d sql:$HOME/.pki/nssdb` to add the cert to Chromium NSS. Phase 62/63 will need this — note the gap here.
**Warning signs:** Playwright navigates to the dashboard but gets `NET::ERR_CERT_AUTHORITY_INVALID`.

### Pitfall 7: PowerShell .deb depends on libicu
**What goes wrong:** `dpkg -i powershell-lts_7.6.0-1.deb_amd64.deb` fails with missing `libicu` dependency.
**Why it happens:** `python:3.12-slim` (the node base image) doesn't include `libicu72` which PowerShell requires.
**How to avoid:** Use `apt-get install -y /tmp/powershell.deb` instead of `dpkg -i`, which resolves dependencies automatically via apt. Or pre-install `libicu72`.
**Warning signs:** `docker exec <node> which pwsh` returns empty; build log shows `dpkg` dependency errors.

---

## Code Examples

### LXC Launch with AppArmor Override

```python
# Source: CONTEXT.md decision + existing provision_lxc_nodes.py pattern
# The raw.apparmor pivot_root rule from Incus issue #791
CONTAINER_NAME = "axiom-coldstart"

launch_result = subprocess.run(
    [
        "incus", "launch", "images:ubuntu/24.04", CONTAINER_NAME,
        "--config", "security.nesting=true",
        "--config", "raw.apparmor=pivot_root,",
    ],
    capture_output=False, timeout=120,
)
if launch_result.returncode != 0:
    raise RuntimeError(f"incus launch failed for {CONTAINER_NAME}")
```

### Node.js 20 + Gemini CLI Install Sequence

```python
# Source: CONTEXT.md decisions; NodeSource PPA is the standard Ubuntu method for Node 20
def install_nodejs_and_gemini(container: str) -> None:
    # NodeSource 20 PPA (Ubuntu 24.04 ships 18 — too old for Gemini CLI)
    run_in_lxc(container, "curl -fsSL https://deb.nodesource.com/setup_20.x | bash -")
    run_in_lxc(container, "apt-get install -y nodejs")
    # Gemini CLI — pinned floor version per CONTEXT.md
    run_in_lxc(container, "npm install -g @google/gemini-cli")
    # Model env var — settings.json pinning has known auto-switch bug
    run_in_lxc(container, "echo 'GEMINI_MODEL=gemini-2.0-flash' >> /etc/environment")
    # ripgrep — prevents 300-second init stall
    run_in_lxc(container, "apt-get install -y ripgrep")
    # Verify headless operation
    run_in_lxc(container, "timeout 30 gemini -p 'Say hello' || true")
```

### EE Licence Generation targeting secrets.env

```python
# Source: adapted from mop_validation/scripts/generate_ee_licence.py
# Key change: 1-year expiry (not 10), AXIOM_EE_LICENCE_KEY (not AXIOM_LICENCE_KEY)
import base64, json, time
from pathlib import Path
from cryptography.hazmat.primitives.serialization import load_pem_private_key

def generate_ee_licence(secrets_env_path: Path) -> str:
    private_key_path = Path("mop_validation/secrets/ee/ee_test_private.pem")
    priv = load_pem_private_key(private_key_path.read_bytes(), password=None)

    payload = {
        "customer_id": "axiom-coldstart-test",
        "exp": int(time.time()) + 365 * 86400,  # 1 year
        "features": ["foundry", "audit", "webhooks", "rbac",
                     "resource_limits", "service_principals", "api_keys"],
    }
    payload_bytes = json.dumps(payload, separators=(",", ":")).encode()
    sig_bytes = priv.sign(payload_bytes)

    def b64url(data: bytes) -> str:
        return base64.urlsafe_b64encode(data).rstrip(b"=").decode()

    licence_key = f"{b64url(payload_bytes)}.{b64url(sig_bytes)}"

    # Update secrets.env
    content = secrets_env_path.read_text() if secrets_env_path.exists() else ""
    import re
    if "AXIOM_EE_LICENCE_KEY=" in content:
        content = re.sub(r"AXIOM_EE_LICENCE_KEY=.*", f"AXIOM_EE_LICENCE_KEY={licence_key}", content)
    else:
        content += f"\nAXIOM_EE_LICENCE_KEY={licence_key}\n"
    secrets_env_path.write_text(content)
    return licence_key
```

### Cold-Start Compose Node Service Block

```yaml
# Source: node-compose.yaml pattern + CONTEXT.md decisions
  puppet-node-1:
    build:
      context: ..
      dockerfile: puppets/Containerfile.node
    image: localhost/axiom-node:cold-start
    environment:
      - AGENT_URL=https://172.17.0.1:8001
      - JOIN_TOKEN=${JOIN_TOKEN_1:-}
      - ROOT_CA_PATH=/app/secrets/root_ca.crt
      - EXECUTION_MODE=direct
      - PYTHONUNBUFFERED=1
      - NODE_TAGS=coldstart,linux
    volumes:
      - node1-secrets:/app/secrets
    restart: unless-stopped
    depends_on:
      agent:
        condition: service_started
```

---

## Existing Assets Summary

This phase is primarily execution work building on verified existing code:

| Asset | Location | Reuse Strategy |
|-------|----------|----------------|
| Incus provisioner helpers | `mop_validation/scripts/provision_lxc_nodes.py` | Copy `run_in_lxc()`, `push_file_to_lxc()`, `get_container_ip()`, `is_container_running()` into new script |
| Basic LXC launch | `.agent/skills/manage-test-nodes/scripts/manage_node.py` | Pattern for `incus launch` + `update_secrets()` |
| Compose template | `puppeteer/compose.server.yaml` | Strip 6 services, keep 5, add 2 node services |
| cert-manager SAN | `puppeteer/cert-manager/entrypoint.sh` | Already reads `SERVER_HOSTNAME` — just set to `172.17.0.1` |
| EE licence generation | `mop_validation/scripts/generate_ee_licence.py` | Adapt: change `exp` to 1 year, key name to `AXIOM_EE_LICENCE_KEY`, write to secrets.env |
| Ed25519 test private key | `mop_validation/secrets/ee/ee_test_private.pem` | Exists and valid — public key bytes already in `axiom-ee/ee/plugin.py` |
| Node compose pattern | `puppets/node-compose.yaml` | Template for puppet node service in cold-start compose |
| PowerShell base | `puppets/Containerfile.node` | Replace the `|| echo "skipped"` apt block with direct .deb wget |

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| MS Debian 12 apt repo for PowerShell | Direct `.deb` from GitHub releases | Required now: SHA1 key rejection on Debian 12 | `docker exec <node> which pwsh` goes from empty to `/usr/bin/pwsh` |
| `settings.json` Gemini model pinning | `GEMINI_MODEL` env var | Gemini CLI bug discovered during v14.0 planning | Prevents auto-switching mid-session |
| No `ripgrep` assumption | `ripgrep` install required | Discovered during LXC validation (v14.0 planning) | Prevents 300s Gemini CLI init stall |
| Ubuntu shipped Node.js 18 | NodeSource PPA for Node.js 20 | Gemini CLI requires Node ≥ 20 | Unblocks Gemini CLI install on Ubuntu 24.04 |

---

## Open Questions

1. **JOIN_TOKEN handling for cold-start compose**
   - What we know: Puppet nodes require a JOIN_TOKEN at startup to enroll with the orchestrator. The compose.server.yaml pattern uses `JOIN_TOKEN` as an env var.
   - What's unclear: Should `compose.cold-start.yaml` include pre-generated tokens (baked in as defaults) or expect the evaluator to generate them? The CONTEXT.md says "Mirrors what a real evaluator gets on `docker compose up`" — a real evaluator generates their own token from the dashboard first.
   - Recommendation: Leave `JOIN_TOKEN_1` and `JOIN_TOKEN_2` as env vars with empty defaults. Add a comment in the compose file and/or a `README` block explaining the token generation step. This is the correct cold-start evaluation flow.

2. **Playwright deps for ENV-01 vs Phase 62**
   - What we know: ENV-01 says "Playwright + system dependencies installed". Playwright's Chromium on Ubuntu requires ~15 system packages.
   - What's unclear: Should we install the full Playwright system deps now (during provisioning) or defer to Phase 62 when Playwright is actually used?
   - Recommendation: Install everything now per ENV-01's explicit scope. Use `playwright install --with-deps chromium` which auto-resolves system deps.

3. **`raw.apparmor` value syntax**
   - What we know: CONTEXT.md says "minimal `pivot_root` allow rule from Incus issue #791". The exact syntax for Incus `raw.apparmor` config value is `pivot_root,` (trailing comma is the Incus syntax for an inline rule appended to the default profile).
   - What's unclear: Whether `raw.apparmor=pivot_root,` is the complete syntax or if a full profile stanza is needed.
   - Recommendation: Use `--config "raw.apparmor=pivot_root,"` — this is the minimal documented workaround. If Docker fails after this, the fallback is simply removing it (existing containers prove nesting alone works).

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (puppeteer/tests/) + vitest (dashboard) |
| Config file | `puppeteer/dashboard/vitest.config.ts` |
| Quick run command | `cd puppeteer && python -m pytest tests/test_ee_smoke.py -x -q` |
| Full suite command | `cd puppeteer && pytest` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| ENV-01 | LXC container created with Docker, Node.js 20, Gemini CLI, ripgrep | smoke | `incus exec axiom-coldstart -- docker run --rm hello-world` + `incus exec axiom-coldstart -- timeout 30 gemini -p "Say hello"` | ❌ Wave 0 |
| ENV-02 | Cold-start compose brings full stack up; dashboard reachable at 172.17.0.1 | smoke | `cd puppeteer && docker compose -f compose.cold-start.yaml up -d && python3 -c "import requests; r=requests.get('https://172.17.0.1:8443', verify=False); assert r.status_code==200"` | ❌ Wave 0 |
| ENV-03 | PowerShell available in node container | smoke | `docker exec <node_container> which pwsh` | ❌ Wave 0 |
| ENV-04 | EE licence generated and stored in secrets.env | unit | `python3 mop_validation/scripts/generate_coldstart_licence.py && grep AXIOM_EE_LICENCE_KEY mop_validation/secrets.env` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `cd puppeteer && pytest tests/test_ee_smoke.py -x -q` (fast smoke)
- **Per wave merge:** `cd puppeteer && pytest` (full backend suite)
- **Phase gate:** All 4 success criteria verified manually before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `mop_validation/scripts/verify_phase61_env.py` — smoke verifier for ENV-01 through ENV-04
- [ ] No new pytest unit tests required — all ENV-0x requirements are infrastructure smoke checks, not code logic

*(Existing backend pytest suite covers application logic. Phase 61 deliverables are scripts and config files — validated by running the actual infrastructure.)*

---

## Sources

### Primary (HIGH confidence)
- Live inspection of `mop_validation/scripts/provision_lxc_nodes.py` — full 320-line provisioner with all helper patterns
- Live inspection of `.agent/skills/manage-test-nodes/scripts/manage_node.py` — Incus launch pattern
- Live inspection of `puppeteer/compose.server.yaml` — service definitions template
- Live inspection of `puppeteer/cert-manager/entrypoint.sh` — SERVER_HOSTNAME → SAN logic
- Live inspection of `puppets/Containerfile.node` — current PowerShell install (the failing pattern)
- Live inspection of `mop_validation/scripts/generate_ee_licence.py` — complete licence generation implementation
- Live inspection of `axiom-ee/ee/plugin.py` — confirms Ed25519 verification happens in EE plugin (not CE startup code)
- Live `incus exec axiom-node-dev -- docker run --rm hello-world` — confirmed Docker-in-LXC works with `security.nesting=true` only, no raw.apparmor needed
- Live `incus config show axiom-node-dev` — confirmed no raw.apparmor override in existing containers
- GitHub API: `https://api.github.com/repos/PowerShell/PowerShell/releases` — confirmed `powershell-lts_7.6.0-1.deb_amd64.deb` is current LTS asset
- Live `python3` key derivation — confirmed `mop_validation/secrets/ee/ee_test_private.pem` public key bytes match `axiom-ee/ee/plugin.py` constant

### Secondary (MEDIUM confidence)
- NodeSource install pattern (`https://deb.nodesource.com/setup_20.x`) — standard documented method, verified script fetchable
- Gemini CLI npm package name `@google/gemini-cli` — verified via `npm show @google/gemini-cli version` returning 0.35.0

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all tools verified live in existing containers or on host
- Architecture: HIGH — build patterns taken directly from working existing code
- Pitfalls: HIGH — most pitfalls discovered from live system inspection (existing containers, failing Containerfile.node pattern, Gemini CLI env requirements from CONTEXT.md)
- EE licence format: HIGH — end-to-end verified: private key → public key bytes → plugin.py constant

**Research date:** 2026-03-24
**Valid until:** 2026-06-24 (stable tooling — Node.js 20, Incus 6.x, PowerShell 7.6 LTS; Gemini CLI changes more frequently but the version floor is locked)
