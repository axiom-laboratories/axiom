# Phase 84: Package Repo Operator Docs - Research

**Researched:** 2026-03-29
**Domain:** Operator runbooks — devpi (PyPI mirror), apt-cacher-ng (APT proxy), BaGet (NuGet/PWSH mirror), signed pip-mirror validation job
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Doc placement:**
- New file: `docs/docs/runbooks/package-mirrors.md` — one combined page with H2 sections per mirror type (devpi, apt-cacher-ng, BaGet)
- Added to MkDocs nav under **Runbooks** in `docs/mkdocs.yml`
- `security/air-gap.md` keeps its existing shallow "Package Mirror Setup" section but adds a cross-link to the new runbook: "For a full from-scratch setup guide, see [Package Mirror Runbooks](../runbooks/package-mirrors.md)"
- Air-gap.md is NOT expanded in-place — it stays as a readiness-checklist context doc

**Runbook depth per mirror:**
- Each mirror section covers the full from-scratch setup:
  1. What the sidecar is and why to use it (one short paragraph)
  2. Compose snippet — the service block to add to `compose.server.yaml`
  3. Configuration steps — URL registration via API + any sidecar-specific config
  4. Initial seeding procedure — how to get packages into the mirror before going offline
  5. Verification step — confirm Foundry builds use the mirror (and for devpi: the PKG-04 validation job)
  6. Common issues — 2-4 inline bullet points covering likely failure modes
- Same depth for all three mirrors (devpi, apt-cacher-ng, BaGet)
- No verbose prose explanations — setup + verify format, theory skipped

**PKG-04 validation job:**
- Script: `tools/example-jobs/validation/verify_pypi_mirror.py`
- Behaviour: runs `pip install <package> -v` and captures stdout; searches for download URL in verbose output; PASSes if URL contains the expected mirror hostname, FAILs with clear message if URL is pypi.org or hostname not found
- Package used for the test install: `requests` (lightweight, universally available)
- Mirror hostname source: `PYPI_MIRROR_HOST` env var (e.g. `pypi-mirror:3141`) — operator sets this in the job dispatch payload; job fails clearly if env var is absent
- Added to `tools/example-jobs/manifest.yaml` with same metadata format as Phase 83 jobs
- Dispatch command and expected PASS/FAIL output documented inline in the runbook's devpi section as a "Verify the mirror works" subsection

**PWSH mirror (BaGet):**
- Primary implementation: BaGet — simplest self-hosted NuGet v3 server
- Enterprise note: one short paragraph after the BaGet setup mentioning Sonatype Nexus and Artifactory as alternatives
- PKG-03 verification is two-part:
  1. Blueprint config — runbook shows how to add a `Register-PSRepository` call in a Foundry Blueprint
  2. Test job — a PWSH job script that calls `Install-Module Pester -Repository AxiomInternal` and verifies import
- Example module: **Pester** (ubiquitous PWSH test framework, on PSGallery)
- Runbook shows: how to seed Pester into BaGet (download .nupkg from PSGallery, upload to BaGet admin), then the job script + dispatch command

### Claude's Discretion

- Exact compose snippet field values for BaGet and apt-cacher-ng (image versions, port mappings)
- Specific apt-cacher-ng config file structure (acng.conf content)
- Pester version to seed (use latest stable)
- Exact `pip install` verbose output format parsing in the validation script

### Deferred Ideas (OUT OF SCOPE)

- APT mirror validation job (equivalent to PKG-04 for apt-cacher-ng)
- BaGet/NuGet validation job as a signed script
- Docs for the `mop_validation/reports/deployment_recomendations.md` content
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| PKG-01 | Operator can follow a runbook to configure a devpi PyPI mirror sidecar and point a Blueprint at it via `pip.conf` injection | devpi already in compose.server.yaml at port 3141; MirrorService.get_pip_conf_content() generates the pip.conf; foundry_service.py already COPYs pip.conf into Dockerfile — runbook documents this end-to-end |
| PKG-02 | Operator can follow guidance to configure an apt-cacher-ng APT mirror and verify packages resolve from it | apt-cacher-ng is a transparent proxy on port 3142; Dockerfile adds APT proxy line via build arg; Foundry DEBIAN blueprint injects APT config — runbook documents compose snippet + Dockerfile pattern |
| PKG-03 | Operator can follow guidance to set up a BaGet/PSGallery mirror and install a PWSH module from it inside a job | BaGet runs on port 5555 with NuGet v3 feed at /v3/index.json; Register-PSRepository works against it; Blueprint can inject the registration command; job script uses Install-Module -Repository AxiomInternal |
| PKG-04 | A signed validation job confirms a pip install resolves from the internal mirror (not the public internet) | pip install -v outputs "Downloading http://..." lines; regex on stdout for PYPI_MIRROR_HOST; new script at tools/example-jobs/validation/verify_pypi_mirror.py; added to manifest.yaml |
</phase_requirements>

---

## Summary

Phase 84 is a documentation and tooling phase — no new backend API routes. The deliverables are: one new runbook page, a cross-link in the air-gap doc, and one new signed validation job script.

All three mirror sidecars already exist in `compose.server.yaml`. The devpi service (`muccg/devpi:latest`, port 3141) and a pypiserver sidecar (port 8080) are both defined. The `MirrorService.get_pip_conf_content()` in `mirror_service.py` already generates a `pip.conf` pointing to `PYPI_MIRROR_URL` (defaulting to `http://pypi:8080/simple`). The `foundry_service.py` already injects this `pip.conf` into every Foundry Docker build via `COPY pip.conf /etc/pip.conf`. There is no apt-cacher-ng sidecar yet — the Caddy-based APT file server is there but that is not a transparent proxy. BaGet is not yet in the compose file.

The PKG-04 validation job script needs to be written from scratch following the established pattern: read `PYPI_MIRROR_HOST` from env, run `pip install requests -v --dry-run` (or an install into a temp venv), capture stdout, check whether the download URL matches the mirror hostname, and exit 0 (PASS) or 1 (FAIL) accordingly.

**Primary recommendation:** Write the runbook as a single `package-mirrors.md` file with three H2 sections; write `verify_pypi_mirror.py` mirroring the `network-filter.py` pattern; add one manifest entry; add nav entry and cross-link. No backend changes needed.

---

## Standard Stack

### Core

| Component | Version / Image | Purpose | Authority |
|-----------|----------------|---------|-----------|
| devpi | `muccg/devpi:latest` | Full PyPI caching proxy with private index support | Already in `compose.server.yaml` |
| pypiserver | `pypiserver/pypiserver:latest` | Simpler static PyPI server (fallback) | Already in `compose.server.yaml` |
| apt-cacher-ng | `sameersbn/apt-cacher-ng:latest` or `modem7/apt-cacher-ng` | Transparent APT caching proxy, port 3142 | Widely used; sameersbn image has 10M+ pulls |
| BaGet | `loicsharma/baget:latest` | NuGet v3 server; PWSH Register-PSRepository compatible | Official BaGet docs (HIGH confidence) |
| Caddy (mirror) | `caddy:latest` | Static APT file server (already in stack, separate from apt-cacher-ng) | Already in `compose.server.yaml` |

### Established Project Patterns

| Pattern | Location | How Phase 84 Uses It |
|---------|----------|---------------------|
| Runbook format | `docs/docs/runbooks/node-validation.md` | package-mirrors.md must follow identical structure |
| manifest.yaml format | `tools/example-jobs/manifest.yaml` | PKG-04 entry uses identical field names |
| Validation script pattern | `tools/example-jobs/validation/network-filter.py` | verify_pypi_mirror.py follows same header/exit-code/print pattern |
| MkDocs nav entry | `docs/mkdocs.yml` line 66 | Add `Package Mirror Setup: runbooks/package-mirrors.md` after line 66 |

**Installation:** No new packages. All images are pulled at `docker compose up` time.

---

## Architecture Patterns

### Recommended File Structure

```
docs/docs/runbooks/
├── package-mirrors.md       # NEW — PKG-01, PKG-02, PKG-03
├── node-validation.md       # existing
└── ...

tools/example-jobs/
├── manifest.yaml            # ADD PKG-04 entry
└── validation/
    ├── verify_pypi_mirror.py  # NEW — PKG-04
    └── ...                    # existing

docs/docs/security/
└── air-gap.md               # ADD cross-link to package-mirrors.md
```

### Pattern 1: devpi pip.conf Injection (PKG-01)

**What:** devpi runs at `http://devpi:3141`. The `root/pypi` index mirrors PyPI. pip.conf points to `http://devpi:3141/root/pypi/+simple/`. The `MirrorService.get_pip_conf_content()` already generates this content from `PYPI_MIRROR_URL` env var. Foundry automatically injects it.

**Operator action to enable:** Set `PYPI_MIRROR_URL=http://devpi:3141/root/pypi/+simple/` in the agent container environment (or via `PATCH /admin/mirror-config` which sets the `PYPI_MIRROR_URL` Config key). Then rebuild Foundry templates — the next build picks up the updated pip.conf automatically.

**devpi URL path:** `http://devpi:3141/root/pypi/+simple/` — the `root` user's `pypi` index which is a caching mirror of pypi.org.

**pip.conf format:**
```ini
[global]
index-url = http://devpi:3141/root/pypi/+simple/
trusted-host = devpi
```

Source: `puppeteer/agent_service/services/mirror_service.py:get_pip_conf_content()` (verified in codebase).

### Pattern 2: apt-cacher-ng Transparent APT Proxy (PKG-02)

**What:** apt-cacher-ng is a caching proxy for APT packages. It runs on port 3142. Dockerfiles that build Debian-based images proxy through it using a one-line APT config injection.

**Docker Compose snippet (discretion area — recommended values):**
```yaml
apt-mirror:
  image: sameersbn/apt-cacher-ng:latest
  restart: unless-stopped
  ports:
    - "3142:3142"
  volumes:
    - apt-cache-data:/var/cache/apt-cacher-ng
  environment:
    - DISABLE_IPFORWARD_CHECK=1
```

**Foundry Dockerfile injection pattern:**
```dockerfile
RUN echo 'Acquire::http::Proxy "http://apt-mirror:3142";' > /etc/apt/apt.conf.d/01proxy \
    && apt-get update \
    && apt-get install -y <packages> \
    && rm /etc/apt/apt.conf.d/01proxy
```

The proxy line is added then removed so the final image does not hardcode the internal proxy URL. Verification: trigger a Foundry build and inspect build logs — cache hits appear as `200 (ca)` in apt-cacher-ng logs.

### Pattern 3: BaGet NuGet v3 Server for PWSH Modules (PKG-03)

**What:** BaGet exposes a NuGet v3 feed. PowerShell's `Install-Module` (via `PowerShellGet`) can install from any NuGet v3 source registered as a PSRepository.

**Docker Compose snippet (discretion area — recommended values):**
```yaml
baget:
  image: loicsharma/baget:latest
  restart: unless-stopped
  ports:
    - "5555:80"
  volumes:
    - baget-data:/var/baget
  environment:
    - ApiKey=AXIOM-INTERNAL-NUGET-KEY
    - Storage__Type=FileSystem
    - Storage__Path=/var/baget
    - Database__Type=Sqlite
    - Database__ConnectionString=Data Source=/var/baget/db/baget.db
    - Search__Type=Database
```

**NuGet v3 index URL:** `http://baget:5555/v3/index.json`

**PowerShell registration (in Blueprint or job script):**
```powershell
Register-PSRepository `
  -Name "AxiomInternal" `
  -SourceLocation "http://baget:5555/v3/index.json" `
  -PublishLocation "http://baget:5555/v3/index.json" `
  -InstallationPolicy Trusted
```

**Seeding Pester into BaGet:**
```bash
# Download Pester nupkg from PSGallery
curl -L "https://www.powershellgallery.com/api/v2/package/Pester" -o Pester.nupkg

# Upload to BaGet
curl -X PUT "http://localhost:5555/api/v2/package" \
  -H "X-NuGet-ApiKey: AXIOM-INTERNAL-NUGET-KEY" \
  -F "package=@Pester.nupkg"
```

Source: BaGet official Docker docs + `Register-PSRepository` Microsoft Learn documentation (HIGH confidence).

### Pattern 4: PKG-04 Validation Job Script

**What:** A Python script that verifies pip resolves packages from the internal mirror. Follows identical code style to `network-filter.py`.

**Key design decisions:**
- Use `pip install requests --dry-run -v` OR `pip download requests -d /tmp/pip-test-$$` — both show the download URL in verbose output
- Parse stdout for lines starting with `Downloading` — the URL in this line reveals where pip fetched from
- `PYPI_MIRROR_HOST` env var (e.g., `devpi:3141` or `pypi-mirror:8080`) — job fails if absent
- Exit 0 = PASS (URL contains mirror host), Exit 1 = FAIL (URL contains pypi.org or env var missing)

**Verbose output format (pip 23+):**
```
Downloading http://devpi:3141/root/pypi/+f/abc/requests-2.31.0-py3-none-any.whl (62 kB)
```
The `Downloading` line is stable across pip versions; parse with `if line.startswith("Downloading") and mirror_host in line`.

**Note on pip --dry-run:** `pip install --dry-run` resolves and reports what would be downloaded but does not actually install — ideal for this validation. Available since pip 22.1.

**Script location:** `tools/example-jobs/validation/verify_pypi_mirror.py`

**manifest.yaml entry pattern:**
```yaml
- name: validation-pypi-mirror
  description: >-
    Confirms pip resolves packages from the configured internal mirror, not pypi.org.
    Reads PYPI_MIRROR_HOST env var (e.g. devpi:3141) and runs a dry-run pip install
    of requests; PASSes if the download URL contains the mirror hostname.
  script: validation/verify_pypi_mirror.py
  runtime: python
  required_capabilities: {}
  env:
    PYPI_MIRROR_HOST: ""
```

### Anti-Patterns to Avoid

- **Documenting the `pypi` (pypiserver) sidecar for PKG-01** — devpi is the primary mirror, pypiserver is a secondary/legacy sidecar. PKG-01 is explicitly about devpi. Use the `devpi:3141/root/pypi/+simple/` URL throughout.
- **Hardcoding the proxy URL in the final Docker image** — for apt-cacher-ng, always remove `/etc/apt/apt.conf.d/01proxy` after the install step.
- **Using `pip install -v` without `--dry-run`** — this actually installs the package into the system Python. Use `--dry-run` or install into a throwaway temp dir to avoid side effects.
- **Forgetting `trusted-host` in pip.conf** — internal mirrors typically use HTTP. Without `trusted-host`, pip refuses to connect.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| PyPI caching proxy | Custom nginx + filesystem serving | devpi (already in compose) | devpi handles cache invalidation, upstream mirroring, index merging |
| APT package proxy | Custom apt repo | apt-cacher-ng | apt-cacher-ng handles package caching transparently with no Dockerfile changes to the client |
| NuGet/PWSH package server | Custom file server | BaGet | BaGet implements NuGet v3 API correctly; Register-PSRepository requires strict protocol compliance |
| pip.conf generation | String templating in runbook prose | `MirrorService.get_pip_conf_content()` | Already exists; references `PYPI_MIRROR_URL` Config key |

---

## Common Pitfalls

### Pitfall 1: Wrong devpi Index URL
**What goes wrong:** Operator uses `http://devpi:3141/+simple/` (root index) instead of `http://devpi:3141/root/pypi/+simple/` (caching mirror index). Root index is empty; pip gets 404 for all packages.
**Why it happens:** devpi has multiple index layers. The root/pypi index is the upstream mirror — it proxies pypi.org and caches packages.
**How to avoid:** Always specify the full path including username and index name: `http://devpi:3141/root/pypi/+simple/`.
**Warning signs:** `pip install` fails with `No matching distribution found`.

### Pitfall 2: apt-cacher-ng Proxy Not Removed from Final Image
**What goes wrong:** Foundry builds a node image with `Acquire::http::Proxy "http://apt-mirror:3142"` baked in. On deployment, the node cannot install APT packages because `apt-mirror` does not resolve outside the compose network.
**Why it happens:** Proxy config added for build-time caching is left in the final image.
**How to avoid:** Always `rm /etc/apt/apt.conf.d/01proxy` in the same `RUN` layer as the `apt-get install`.
**Warning signs:** Node `apt-get update` fails with `Could not connect to apt-mirror:3142`.

### Pitfall 3: BaGet and PowerShellGet v2 vs v3 Incompatibility
**What goes wrong:** `Install-Module` from `PowerShellGet` v2 may fail against NuGet v3 feeds in some edge cases. The error manifests as "Unable to find module" even though the package exists in BaGet.
**Why it happens:** `PowerShellGet` v2 has partial NuGet v3 support. Fully resolved in `PowerShellGet` v3 (PSResourceGet).
**How to avoid:** Use `Install-PSResource` (PSResourceGet/PowerShellGet v3) if available. For v2, verify BaGet returns the package at the v2-compatible `/v2/` endpoint: `http://baget:5555/v2/FindPackagesById()?id='Pester'`.
**Warning signs:** `Install-Module` returns empty results despite the package being visible in BaGet web UI.

### Pitfall 4: PYPI_MIRROR_HOST vs Full URL in PKG-04 Job
**What goes wrong:** Operator sets `PYPI_MIRROR_HOST=http://devpi:3141/root/pypi/+simple/` (full URL) instead of just the hostname+port `devpi:3141`. The substring match fails because `pip install -v` output shows `http://devpi:3141/...` and the check for `http://devpi:3141/root/pypi/+simple/` as a substring is fragile.
**Why it happens:** Env var name says "HOST" but operators may assume full URL.
**How to avoid:** Document clearly that `PYPI_MIRROR_HOST` is `hostname:port` only (e.g., `devpi:3141`). The script checks `if mirror_host in download_url`.
**Warning signs:** Job reports FAIL with "download URL not matching expected mirror host" even when mirror is running.

### Pitfall 5: devpi Caddy Proxy URL in STATE.md Warning
**Why it matters:** STATE.md records a research flag: "Verify live devpi Caddy-proxied URL, index name, and auth config before writing runbook." The compose stack has both a `devpi` service (direct port 3141) and a `mirror` Caddy service (port 8081). The Caddy `mirror/Caddyfile` serves `/data/apt` as a static file server — it does NOT proxy devpi. The runbook must point to the devpi service directly (`http://devpi:3141`), not through Caddy.
**Confirmed finding:** Caddy mirror service is for APT files only. devpi is accessed at `http://devpi:3141` directly. (HIGH confidence — verified in `compose.server.yaml` and `mirror/Caddyfile`.)

---

## Code Examples

Verified patterns from existing codebase:

### PKG-04 Validation Script Structure (follows network-filter.py pattern)
```python
#!/usr/bin/env python3
# validation/verify_pypi_mirror.py
# PKG-04 — PyPI Mirror Validation
#
# Required env:
#   PYPI_MIRROR_HOST   Hostname:port of internal mirror (e.g. devpi:3141)
#
# Exit codes:
#   0  PASS — pip resolved from internal mirror
#   1  FAIL — pip resolved from pypi.org, mirror unreachable, or env var absent

import os
import subprocess
import sys

MIRROR_HOST = os.environ.get("PYPI_MIRROR_HOST", "")
TEST_PACKAGE = "requests"

print("=== Axiom PyPI Mirror Validation ===")

if not MIRROR_HOST:
    print("FAIL: PYPI_MIRROR_HOST env var is not set.")
    print("      Set it to the mirror hostname:port (e.g. devpi:3141).")
    sys.exit(1)

print(f"Testing mirror: {MIRROR_HOST}")

result = subprocess.run(
    [sys.executable, "-m", "pip", "install", TEST_PACKAGE, "--dry-run", "-v"],
    capture_output=True,
    text=True,
)

combined = result.stdout + result.stderr
download_lines = [l for l in combined.splitlines() if "Downloading" in l or "downloading" in l]

for line in download_lines:
    if MIRROR_HOST in line:
        print(f"PASS: pip resolved {TEST_PACKAGE!r} from internal mirror ({MIRROR_HOST}).")
        print(f"      {line.strip()}")
        sys.exit(0)
    if "pypi.org" in line:
        print(f"FAIL: pip is resolving from pypi.org, not the internal mirror.")
        print(f"      {line.strip()}")
        print(f"      Check PYPI_MIRROR_URL in agent config and that devpi is seeded.")
        sys.exit(1)

# No download line found — package may be cached or pip version differences
print("WARN: Could not determine download source from pip output.")
print("      Pip may have used the cache. Rerun with --no-cache-dir.")
print(combined[-500:])
sys.exit(1)
```

Source: pattern derived from `tools/example-jobs/validation/network-filter.py` (verified in codebase).

### MirrorService pip.conf Generation (existing code)
```python
# puppeteer/agent_service/services/mirror_service.py
@staticmethod
def get_pip_conf_content() -> str:
    url = os.getenv("PYPI_MIRROR_URL", "http://pypi:8080/simple")
    host = url.split("//")[-1].split(":")[0].split("/")[0]
    return f"[global]\nindex-url = {url}\ntrusted-host = {host}\n"
```
Source: `puppeteer/agent_service/services/mirror_service.py:98-102` (verified in codebase).

### MkDocs nav addition (exact location)
```yaml
  - Runbooks:
    - Overview: runbooks/index.md
    - Node Troubleshooting: runbooks/nodes.md
    - Job Execution: runbooks/jobs.md
    - Foundry: runbooks/foundry.md
    - FAQ: runbooks/faq.md
    - Node Validation: runbooks/node-validation.md
    - Package Mirror Setup: runbooks/package-mirrors.md   # ADD HERE
```
Source: `docs/mkdocs.yml:60-66` (verified in codebase).

### air-gap.md cross-link (exact insertion point)
```markdown
## Package Mirror Setup

> For a full from-scratch setup guide, see [Package Mirror Runbooks](../runbooks/package-mirrors.md).
```
Insert at line 26 of `docs/docs/security/air-gap.md` (before the existing "The mirror sidecars must be configured..." sentence).

### manifest.yaml PKG-04 entry (follows existing pattern)
```yaml
  - name: validation-pypi-mirror
    description: >-
      Confirms pip resolves packages from the internal mirror, not pypi.org.
      Reads PYPI_MIRROR_HOST env var (hostname:port, e.g. devpi:3141) and runs
      a dry-run pip install of requests; PASSes if download URL contains the
      mirror hostname, FAILs if it resolves from pypi.org or env var is absent.
    script: validation/verify_pypi_mirror.py
    runtime: python
    required_capabilities: {}
```
Note: `env` block is NOT a standard field in manifest.yaml — document `PYPI_MIRROR_HOST` in the runbook, not the manifest.

---

## State of the Art

| Old Approach | Current Approach | Notes |
|--------------|------------------|-------|
| pypiserver (simple static) | devpi (caching proxy) | devpi is already in compose; pypiserver remains as fallback |
| Manual apt sources.list swap | apt-cacher-ng transparent proxy | Proxy requires no changes to how packages are named |
| Full PSGallery sync | BaGet with individual seeded modules | Full PSGallery sync is multi-TB; BaGet selective seeding is practical |
| `pip install -v` then parse (fragile) | `pip install --dry-run -v` | `--dry-run` available since pip 22.1; avoids side effects |

---

## Open Questions

1. **pip --dry-run availability on node images**
   - What we know: `--dry-run` added in pip 22.1 (2022). Most modern Python images include pip >= 22.
   - What's unclear: Very old Foundry base images (e.g., python:3.8-alpine with pip 21.x) would fail.
   - Recommendation: Document that the job requires pip >= 22.1 in the runbook. Alternatively, use `pip download requests -d /tmp/pip-test --no-deps` which works on all pip versions and also shows the download URL. Use `pip download` as the safer fallback.

2. **PowerShellGet v2 vs v3 on PWSH nodes**
   - What we know: PSResourceGet (v3) ships with PowerShell 7.4+. v2 is pre-installed on older nodes.
   - What's unclear: BaGet v3 endpoint compatibility with PSGet v2 is inconsistent (noted GitHub issue #199 on loic-sharma/BaGet).
   - Recommendation: Document `Install-PSResource` as the preferred command if PSResourceGet is available, with `Install-Module` as a fallback. Note the v2 caveat.

3. **devpi initialization — does muccg/devpi auto-create root/pypi index?**
   - What we know: The `muccg/devpi` image auto-creates the root user on first start. The `root/pypi` index (which mirrors pypi.org) must be created manually on first run OR is created automatically depending on image version.
   - What's unclear: Exact first-run init commands needed. Some devpi setups require `devpi use http://localhost:3141` then `devpi login root` then `devpi index -c root/pypi`.
   - Recommendation: Document the explicit init steps in the runbook using `docker exec` commands. Do not assume auto-creation. HIGH priority to get right before writing runbook prose.

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest |
| Config file | `puppeteer/` (run from that directory) |
| Quick run command | `cd puppeteer && pytest tests/test_example_jobs.py -x` |
| Full suite command | `cd puppeteer && pytest` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| PKG-04 | `verify_pypi_mirror.py` exists and has PYPI_MIRROR_HOST check + PASS/FAIL markers | unit | `cd puppeteer && pytest tests/test_example_jobs.py::test_pypi_mirror_script -x` | ❌ Wave 0 |
| PKG-04 | `verify_pypi_mirror.py` exits 1 when PYPI_MIRROR_HOST is absent | unit (subprocess) | `cd puppeteer && pytest tests/test_example_jobs.py::test_pypi_mirror_no_env -x` | ❌ Wave 0 |
| PKG-04 | manifest.yaml updated to 8 entries including validation-pypi-mirror | unit | `cd puppeteer && pytest tests/test_example_jobs.py::test_manifest_valid -x` | ✅ (needs count update) |
| PKG-01 | `package-mirrors.md` exists with devpi section | file existence | manual / `test -f docs/docs/runbooks/package-mirrors.md` | ❌ Wave 0 |
| PKG-02 | `package-mirrors.md` exists with apt-cacher-ng section | file existence | manual | ❌ Wave 0 |
| PKG-03 | `package-mirrors.md` exists with BaGet section | file existence | manual | ❌ Wave 0 |

### Sampling Rate

- **Per task commit:** `cd puppeteer && pytest tests/test_example_jobs.py -x`
- **Per wave merge:** `cd puppeteer && pytest`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps

- [ ] `puppeteer/tests/test_example_jobs.py` — add `test_pypi_mirror_script` and `test_pypi_mirror_no_env` test cases
- [ ] `puppeteer/tests/test_example_jobs.py` — update `test_manifest_valid` assertion from `len(jobs) == 7` to `len(jobs) == 8`
- [ ] `tools/example-jobs/validation/verify_pypi_mirror.py` — new file (PKG-04 script)

---

## Sources

### Primary (HIGH confidence)

- `puppeteer/compose.server.yaml` — devpi service confirmed at port 3141, pypiserver at 8080, Caddy mirror at 8081 for APT static files only
- `puppeteer/agent_service/services/mirror_service.py` — `get_pip_conf_content()` and `get_sources_list_content()` confirmed
- `puppeteer/agent_service/services/foundry_service.py` — `COPY pip.conf /etc/pip.conf` injection confirmed at lines 93-157
- `puppeteer/mirror/Caddyfile` — serves `/data/apt` static files only, does NOT proxy devpi
- `docs/mkdocs.yml` — nav structure confirmed, Runbooks section ends at line 66
- `docs/docs/security/air-gap.md` — "Package Mirror Setup" section confirmed at line 26
- `docs/docs/runbooks/node-validation.md` — established runbook format confirmed
- `tools/example-jobs/manifest.yaml` — manifest format confirmed, 7 existing entries
- `tools/example-jobs/validation/network-filter.py` — validation script pattern confirmed
- `puppeteer/tests/test_example_jobs.py` — test patterns confirmed; `test_manifest_valid` hardcodes count 7

### Secondary (MEDIUM confidence)

- [BaGet Docker Installation](https://loic-sharma.github.io/BaGet/installation/docker/) — port 5555, NuGet v3 index URL `/v3/index.json`, ApiKey env var
- [devpi Docker image muccg](https://github.com/muccg/docker-devpi) — root/pypi index URL pattern, DEVPI_PASSWORD env var
- [apt-cacher-ng Docker (sameersbn)](https://github.com/sameersbn/docker-apt-cacher-ng) — port 3142, DISABLE_IPFORWARD_CHECK env var
- [pip install documentation](https://pip.pypa.io/en/stable/cli/pip_install/) — `--dry-run` flag availability

### Tertiary (LOW confidence)

- BaGet + PowerShellGet v2 compatibility: [GitHub issue #199](https://github.com/loic-sharma/BaGet/issues/199) — may affect Install-Module on older nodes; v3 (PSResourceGet) resolves this

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all mirror components verified in codebase or official docs
- Architecture: HIGH — pip.conf injection and Foundry patterns verified directly in source code
- Pitfalls: MEDIUM-HIGH — devpi URL path and apt proxy removal from HIGH; BaGet/PSGet v2 compat from LOW (GitHub issue)
- PKG-04 script design: HIGH — pattern directly derived from existing validation scripts

**Research date:** 2026-03-29
**Valid until:** 2026-04-29 (docker images stable; devpi API stable)
