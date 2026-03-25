# Stack Research

**Domain:** Axiom v14.1 — First-User Readiness patches (code + docs fixes)
**Researched:** 2026-03-25
**Confidence:** HIGH (all four fix areas verified against live source + official docs)

---

## Scope

This addendum covers ONLY the net-new tooling questions for v14.1 First-User Readiness.
The existing validated stack (FastAPI CE+EE, React dashboard, MkDocs Material, Caddy,
Containerfile.node, axiom-push CLI, Gemini CLI cold-start harness) is NOT re-researched.
See the v14.0 STACK.md entry for the validation harness additions.

The four fix areas are:
1. Docker CLI in Containerfile.node (approach verification)
2. DinD `/tmp` volume mount in compose.cold-start.yaml (mechanism explanation)
3. FastAPI CE stub route for `/api/executions` (pattern + implementation)
4. MkDocs Material tooling for CLI code blocks and curl examples

---

## Pre-Assessment: Current Source State

| Fix Area | Status in Current Source |
|----------|--------------------------|
| `COPY --from=docker:cli` in Containerfile.node | **Already committed** — cold-start run patched it |
| `/tmp:/tmp` and docker socket in compose.cold-start.yaml | **Already committed** — cold-start run patched it |
| `/api/executions` CE-gating | **Not implemented** — routes are in `main.py` and return 200 in CE mode |
| MkDocs `pymdownx.tabbed` extension | **Not configured** — `pymdownx.tabbed` absent from `docs/mkdocs.yml` |
| Getting-started docs content | **Outdated** — multiple BLOCKERs in install.md, enroll-node.md, first-job.md |

The milestone's code work is therefore:
- **Zero changes** to Containerfile.node and compose.cold-start.yaml (already patched)
- **One new file** + two file edits for the CE stub (`ee/interfaces/executions.py`, `ee/__init__.py`, `main.py`)
- **One config line** in `docs/mkdocs.yml` for tabbed support
- **Content edits** to `docs/docs/getting-started/*.md`

---

## Fix Area 1: Docker CLI in Containerfile.node

### Status: Already Resolved in Source

`puppets/Containerfile.node` currently reads:

```dockerfile
COPY --from=docker:cli /usr/local/bin/docker /usr/local/bin/docker
```

This is the correct approach. No further code change required.

### Why `COPY --from=docker:cli` Is Correct

| Approach | Verdict | Reason |
|----------|---------|--------|
| `COPY --from=docker:cli /usr/local/bin/docker /usr/local/bin/docker` | **Correct — in use** | Single statically-linked binary; no apt repo setup; no GPG key chain; no version skew risk between apt and docker daemon |
| `apt-get install docker.io` (Debian package) | **Wrong for Debian 13** | On Debian 13 (Trixie), `docker.io` installs only `docker-init`, not the `docker` CLI binary — confirmed as the root cause in the cold-start friction report |
| Docker official apt repo: `apt-get install docker-ce-cli` | Technically correct but heavyweight | Requires 5-step GPG key + DEB822 sources setup in the Dockerfile; adds apt repo surface to the image; installs unnecessary dependencies (`containerd.io`, etc.) for a CLI-only need |

### docker:cli Version Pinning (Documentation Recommendation)

The current `docker:cli` is a floating tag resolving to the latest stable Docker CLI at build time.
For reproducible builds, pin to a major version:

```dockerfile
COPY --from=docker:27-cli /usr/local/bin/docker /usr/local/bin/docker
```

Docker CLI 27.x is current stable (2025/2026). The floating `docker:cli` tag is acceptable for the
cold-start evaluation compose where exact Docker version is not a correctness concern.

**Milestone action:** No code change. Optionally add a comment noting the pinning option.

---

## Fix Area 2: DinD `/tmp` Volume Mount

### Status: Already Resolved in Source

`puppeteer/compose.cold-start.yaml` already has for both puppet-node services:

```yaml
volumes:
  - /var/run/docker.sock:/var/run/docker.sock
  - /tmp:/tmp
```

No further code change required.

### Root Cause Explanation (for PITFALLS.md and doc comments)

The node execution path in `node.py` (verified via source read):

1. Job script is received via `/work/pull` API response
2. Node writes script to `/tmp/job_{guid}.{ext}` inside the node container's filesystem
3. Node calls `docker run -v /tmp/job_guid.py:/tmp/job_guid.py:ro <image> <cmd>`
4. The `docker run` command executes against the host Docker daemon via the mounted socket
5. The host Docker daemon resolves `/tmp/job_guid.py` against the HOST filesystem — not the
   node container's filesystem

Without `/tmp:/tmp`: the file written to the node container's `/tmp` does not exist on the host.
Docker's bind-mount source resolution against the HOST path creates an empty directory at
`/tmp/job_guid.py`, and the job container receives a directory mount where a file is expected.
The script does not execute.

With `/tmp:/tmp`: the node container's `/tmp` IS the host's `/tmp` (bind mount). Files written
inside the container appear on the host immediately. The host Docker daemon finds the file at the
expected path, and the job container receives the correct file mount.

### What NOT to Use

| Approach | Problem |
|----------|---------|
| `tmpfs: /tmp` in compose | Creates an in-container tmpfs; still isolated from host; DinD path resolution still fails |
| Named volume for `/tmp` | Docker-managed volume at an opaque path; host daemon cannot resolve the path |
| `EXECUTION_MODE=direct` | Removed from `node.py` — raises `RuntimeError` at startup |

### Multi-Node Consideration

All node containers on the same host share `/tmp` via this mount. The existing per-job UUID
filename (`job_{uuid4_hex}.py`) prevents collisions. This is acceptable for the cold-start
evaluation scenario and standard homelab deployments.

---

## Fix Area 3: FastAPI CE Stub for `/api/executions`

### Decision: Execution History Is EE-Gated

From the friction report finding: "Decide whether Execution History should be CE or EE-gated."

**Verdict: EE-gated.** Rationale:
- `ExecutionRecord` table was introduced in v10.0 Axiom Commercial Release (PROJECT.md)
- Attestation export (`/api/executions/{id}/attestation`) is explicitly commercial
- The dashboard History view is listed as a commercial differentiator
- Treating execution history as CE would weaken the EE value proposition with no user benefit

### Implementation Pattern

The existing CE stub architecture is the authoritative pattern. All stubs follow this exact structure
(verified across `audit.py`, `smelter.py`, and 4 other interface files):

**Step 1: New file `puppeteer/agent_service/ee/interfaces/executions.py`**

```python
from fastapi import APIRouter
from fastapi.responses import JSONResponse

executions_stub_router = APIRouter(tags=["Execution Records"])

_EE_RESPONSE = JSONResponse(
    status_code=402,
    content={"detail": "This feature requires Axiom Enterprise Edition. See https://axiom.run/enterprise"}
)


@executions_stub_router.get("/api/executions")
async def list_executions_stub(): return _EE_RESPONSE

@executions_stub_router.get("/api/executions/{id}")
async def get_execution_stub(id: int): return _EE_RESPONSE

@executions_stub_router.get("/api/executions/{id}/attestation")
async def get_execution_attestation_stub(id: int): return _EE_RESPONSE

@executions_stub_router.patch("/api/executions/{exec_id}/pin")
async def pin_execution_stub(exec_id: int): return _EE_RESPONSE

@executions_stub_router.patch("/api/executions/{exec_id}/unpin")
async def unpin_execution_stub(exec_id: int): return _EE_RESPONSE

@executions_stub_router.get("/api/jobs/{guid}/executions/export")
async def export_job_executions_stub(guid: str): return _EE_RESPONSE

@executions_stub_router.get("/jobs/{guid}/executions")
async def list_job_executions_stub(guid: str): return _EE_RESPONSE
```

**Step 2: Register in `_mount_ce_stubs()` in `ee/__init__.py`**

Add one import and one `app.include_router()` call:

```python
def _mount_ce_stubs(app: Any) -> None:
    from .interfaces.executions import executions_stub_router
    # ... existing imports unchanged ...
    app.include_router(executions_stub_router)
    # ... existing app.include_router() calls unchanged ...
```

**Step 3: Remove execution routes from `main.py`**

The routes currently in `main.py` (lines 231–294, 296–338, 339–..., 2274–2397, 1369–1395) must be
removed from `main.py`. FastAPI does NOT support route override — the first-registered route wins.
Since `main.py` routes are registered at module import time before the lifespan runs `_mount_ce_stubs`,
leaving them in `main.py` means CE stubs are never reached for these paths.

The routes should move to the EE plugin's router inside the `axiom-ee` private package.

### Routes to Cover

Verified from `main.py` grep (confirmed paths and methods):

| Path | Method | Notes |
|------|--------|-------|
| `/api/executions` | GET | List with filters and pagination |
| `/api/executions/{id}` | GET | Single execution detail |
| `/api/executions/{id}/attestation` | GET | Attestation export (EE-specific by nature) |
| `/api/executions/{exec_id}/pin` | PATCH | Pin for retention exemption |
| `/api/executions/{exec_id}/unpin` | PATCH | Unpin |
| `/api/jobs/{guid}/executions/export` | GET | CSV export per job |
| `/jobs/{guid}/executions` | GET | Per-job execution list |

### FastAPI Route Override Behaviour (Important)

FastAPI uses Starlette's route matching which evaluates routes in registration order. There is no
built-in override mechanism. The CE stub approach works because:
- CE stubs are registered during the lifespan startup (`_mount_ce_stubs`)
- The corresponding EE routes are registered by the EE plugin (also during lifespan)
- Neither set of routes appears in `main.py`

The current `/api/executions` routes ARE in `main.py` (registered before lifespan). Moving them
out is the only correct approach. This is a small refactor, not an architectural change.

---

## Fix Area 4: MkDocs Material CLI Code Blocks and curl Examples

### Current Extension State

From `docs/mkdocs.yml` (verified via grep):

```yaml
markdown_extensions:
  - pymdownx.superfences:   # already configured
      custom_fences:
        - name: mermaid
          ...
  - admonition              # already configured
  - pymdownx.details        # already configured
  # pymdownx.tabbed         # NOT YET CONFIGURED
```

### Required Addition to `docs/mkdocs.yml`

```yaml
markdown_extensions:
  - pymdownx.tabbed:
      alternate_style: true
```

Add alongside the existing `pymdownx.superfences`, `admonition`, and `pymdownx.details` entries.

`alternate_style: true` is **required** — the legacy non-alternate style is deprecated and removed
in Material for MkDocs 9.x. Omitting it causes tabs to render incorrectly.

No package installation required. `pymdownx.tabbed` is part of PyMdown Extensions, already
installed as a transitive dependency of `mkdocs-material` (confirmed via existing superfences usage).

### Content Tabs Syntax: Dashboard / CLI Alternatives

Use content tabs where a doc step has both a dashboard GUI path and a CLI/API path. This is the
primary pattern needed for the open BLOCKERs (JOIN_TOKEN generation, job dispatch, etc.):

```markdown
=== "Dashboard"

    1. Go to **Nodes** in the sidebar.
    2. Click **Generate Token**.
    3. Copy the `JOIN_TOKEN` value shown.

=== "CLI (curl)"

    ```bash
    # Get a JWT first
    TOKEN=$(curl -sk -X POST https://localhost:8443/api/token \
      -d "username=admin&password=<your-password>" \
      | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")

    # Generate JOIN_TOKEN
    curl -sk -X POST https://localhost:8443/api/admin/generate-token \
      -H "Authorization: Bearer $TOKEN" \
      | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['enhanced_token'])"
    ```
```

Content inside each `=== "Label"` must be indented by 4 spaces. Code fences inside tabs work via
`pymdownx.superfences` (already configured) — no additional extension needed.

### Admonition Syntax: CLI Alternative Callouts

For pages where a full tab set is not warranted (e.g., single secondary CLI note), use an `info`
admonition. This uses only the existing `admonition` extension (already configured):

```markdown
!!! info "CLI Alternative"

    If you prefer the API over the dashboard, generate a token via:

    ```bash
    curl -sk -X POST https://localhost:8443/api/admin/generate-token \
      -H "Authorization: Bearer <jwt>"
    ```
```

Nested code fences inside admonitions require `pymdownx.superfences` (already configured).
The 4-space indent is mandatory for all admonition content.

### Warning Admonition for Removed Features

For the `EXECUTION_MODE=direct` removal BLOCKER, use a `warning` admonition:

```markdown
!!! warning "EXECUTION_MODE=direct removed"

    The `direct` execution mode was removed in v12.0. Setting `EXECUTION_MODE=direct`
    causes the node to fail at startup with a `RuntimeError`. Use `EXECUTION_MODE=docker`
    or `EXECUTION_MODE=podman` instead.
```

### When to Use Each Pattern

| Scenario | Pattern |
|----------|---------|
| Step with equal-weight GUI and CLI paths | `=== "Dashboard"` / `=== "CLI (curl)"` content tabs |
| Primary GUI path with API as secondary option | `!!! info "CLI Alternative"` admonition |
| Warning about a removed or changed feature | `!!! warning` admonition |
| Single curl command as primary example | Plain fenced code block — no admonition needed |
| Enterprise-only feature note | `!!! enterprise` (already used in existing docs) |

---

## Recommended Stack

### Core Technologies (Unchanged)

| Technology | Version | Purpose | Status |
|------------|---------|---------|--------|
| FastAPI | Existing | REST API + CE stub routing | No version change |
| SQLAlchemy | Existing | ORM | No version change |
| MkDocs Material | 9.x | Documentation site | Add `pymdownx.tabbed` config only |
| docker:cli image | `cli` (latest ~27.x) | Docker CLI binary in node image | Already in Containerfile.node |
| PyMdown Extensions | 9.0+ (already installed) | MkDocs content tabs + admonitions | Add tabbed config only |

### New Files Required

| File | Type | Purpose |
|------|------|---------|
| `puppeteer/agent_service/ee/interfaces/executions.py` | Python | CE stub router for execution history routes |

### Files to Edit

| File | Change |
|------|--------|
| `puppeteer/agent_service/ee/__init__.py` | Import + register `executions_stub_router` in `_mount_ce_stubs()` |
| `puppeteer/agent_service/main.py` | Remove 7 execution-related route handlers (move to EE plugin) |
| `docs/mkdocs.yml` | Add `pymdownx.tabbed: alternate_style: true` |
| `docs/docs/getting-started/install.md` | Fix admin password setup, docs path, GitHub clone assumption, EE section |
| `docs/docs/getting-started/enroll-node.md` | Fix node image, EXECUTION_MODE, AGENT_URL, add CLI token path |
| `docs/docs/getting-started/first-job.md` | Add CLI dispatch path, Ed25519 signing workflow |
| `docs/docs/getting-started/ee-install.md` | Fix `/api/admin/features` → `/api/features` reference |

### Zero New Dependencies

All four fix areas require **zero new Python packages, npm packages, or system packages**. The
`pymdownx.tabbed` extension is already installed; it only requires a configuration entry.

---

## Alternatives Considered

| Recommended | Alternative | Why Not |
|-------------|-------------|---------|
| `COPY --from=docker:cli` for Docker CLI | Docker apt repo `docker-ce-cli` | 5-step GPG+DEB822 setup for a single binary; adds apt repo surface to node image; overkill |
| `COPY --from=docker:cli` | `apt-get install docker.io` | Broken on Debian 13 — only installs `docker-init`, not the CLI binary |
| `/tmp:/tmp` bind mount | `tmpfs` mount for `/tmp` | In-container tmpfs; host Docker daemon cannot see files; DinD path resolution fails |
| CE stub router in `ee/interfaces/` | Middleware interceptor for 402 | Middleware would intercept even EE requests; inconsistent with existing CE architecture |
| CE stub router | `require_ee_licence()` dependency injection | The execution routes are in `main.py`, not an EE plugin; dependency injection would partially gate them but not move them to EE correctly |
| `pymdownx.tabbed` content tabs | Custom HTML tabs in markdown | Not portable across MkDocs build; breaks in CDN-free/offline mode; harder to maintain |
| `!!! info` admonitions for secondary CLI notes | Blockquotes | Admonitions render with proper Material theme styling and visible type badge |

---

## What NOT to Use

| Avoid | Why | Use Instead |
|-------|-----|-------------|
| `apt-get install docker.io` in node Containerfile | Only installs `docker-init` on Debian 13, not the `docker` CLI binary | `COPY --from=docker:cli /usr/local/bin/docker /usr/local/bin/docker` |
| `EXECUTION_MODE=direct` in compose files or docs | Raises `RuntimeError` at `node.py` startup — removed in v12.0 | `EXECUTION_MODE=docker` for DinD scenarios |
| `docker restart` to reload env vars | Does not re-read `.env` file; container keeps old env | `docker compose up -d --force-recreate <service>` |
| `pymdownx.tabbed` without `alternate_style: true` | Deprecated legacy style; not rendered correctly in Material 9.x | `pymdownx.tabbed:` with `alternate_style: true` nested |
| Named volume or `tmpfs` for `/tmp` in DinD compose | Host Docker daemon cannot resolve paths inside; job scripts not visible | Bind mount `/tmp:/tmp` from host |
| Leaving execution routes in `main.py` and adding CE stubs | FastAPI first-registered-wins routing means `main.py` routes shadow the stubs | Remove routes from `main.py`; register exclusively in EE plugin and CE stub router |

---

## Stack Patterns by Variant

**For DinD job execution (cold-start compose):**
- Requires both `/var/run/docker.sock:/var/run/docker.sock` AND `/tmp:/tmp` mounts on node services
- `EXECUTION_MODE=docker` (not `auto` — auto may connect to wrong daemon in nested Docker)
- `JOB_IMAGE` must match an image tag present on the host Docker daemon (not a remote registry image)
- Both puppet-node services need identical mounts (already in current compose.cold-start.yaml)

**For CE stub routing (new EE-gated routes):**
- New stub file goes in `ee/interfaces/<feature>.py`
- Register in `_mount_ce_stubs()` in `ee/__init__.py`
- Remove the corresponding routes from `main.py` before the stub will take effect
- Use `JSONResponse(status_code=402, content={"detail": "..."})` — exact same pattern as all existing stubs

**For MkDocs content tabs (CLI alternatives in docs):**
- Add `pymdownx.tabbed: alternate_style: true` to `mkdocs.yml` once
- Use `=== "Label"` syntax in any page; content must be 4-space indented
- `pymdownx.superfences` (already configured) enables code fences inside tabs

---

## Version Compatibility

| Component | Version | Notes |
|-----------|---------|-------|
| `docker:cli` image tag | `cli` (latest) or `27-cli` | `27-cli` pins to major; `cli` is floating latest stable |
| `pymdownx.tabbed` with `alternate_style` | PyMdown Extensions ≥ 9.0 | Already installed via mkdocs-material |
| FastAPI `APIRouter` CE stub | Any FastAPI version in use | No new FastAPI features needed; standard `APIRouter` + `JSONResponse` |
| Docker Compose bind mount syntax | Compose v2 (any) | Short syntax `- /tmp:/tmp` works; `type: bind` long form not needed |

---

## Sources

- [Docker official Debian install docs](https://docs.docker.com/engine/install/debian/) — Confirmed docker-ce-cli apt procedure; verified `docker.io` vs `docker-ce-cli` distinction (MEDIUM confidence — CLI-only install not the main focus of the page)
- [Docker Hub docker:cli tags](https://hub.docker.com/_/docker/tags?name=cli) — Confirmed `cli` and `27-cli` tag existence (HIGH confidence)
- [MkDocs Material Content Tabs reference](https://squidfunk.github.io/mkdocs-material/reference/content-tabs/) — Confirmed `alternate_style: true` requirement, `=== "Tab"` syntax, superfences integration (HIGH confidence — official docs)
- [MkDocs Material Admonitions reference](https://squidfunk.github.io/mkdocs-material/reference/admonitions/) — Confirmed `!!! type "title"` + nested code block syntax (HIGH confidence — official docs)
- [Docker bind mounts — official docs](https://docs.docker.com/engine/storage/bind-mounts/) — Confirmed host-path bind mount resolution behaviour; DinD path resolution documented via community (MEDIUM confidence — DinD scenario not explicitly in official docs; behaviour confirmed from friction report cold-start run)
- Live source analysis: `puppets/Containerfile.node`, `puppeteer/compose.cold-start.yaml`, `puppeteer/agent_service/ee/interfaces/*.py`, `puppeteer/agent_service/main.py`, `puppeteer/agent_service/ee/__init__.py`, `docs/mkdocs.yml` — Direct read and grep of current committed state (HIGH confidence)
- `mop_validation/reports/cold_start_friction_report.md` — Root cause descriptions and fix targets from the live cold-start run (HIGH confidence)

---

*Stack research for: Axiom v14.1 — First-User Readiness patch milestone*
*Researched: 2026-03-25*
