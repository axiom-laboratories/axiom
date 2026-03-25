# Architecture Research

**Domain:** First-user readiness fixes for Axiom job orchestration platform (v14.1)
**Researched:** 2026-03-25
**Confidence:** HIGH — all findings verified directly from codebase source files

---

## Context: What Is Being Fixed

This research answers four precise integration questions for the v14.1 milestone. The existing architecture is not being redesigned — specific gaps found during the v14.0 CE/EE cold-start validation are being patched. Each section below covers one fix area: where the change lands, what surrounds it, and what constraints the fix must respect.

---

## System Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│  Operator Browser                                                    │
│  dashboard (React/Vite -> Caddy at :443/:8443)                      │
└──────────────────────────┬──────────────────────────────────────────┘
                           | HTTPS (Caddy TLS termination)
┌──────────────────────────▼──────────────────────────────────────────┐
│  Control Plane (puppeteer/)                                          │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │  FastAPI agent service (:8001)                                │   │
│  │  ┌────────────────────────────┐  ┌────────────────────────┐  │   │
│  │  │  main.py  (CE routes +     │  │  ee/__init__.py         │  │   │
│  │  │  lifespan licence gating)  │  │  _mount_ce_stubs() OR  │  │   │
│  │  │                            │  │  load_ee_plugins()      │  │   │
│  │  └────────────────────────────┘  └────────────────────────┘  │   │
│  │  ┌──────────────────────────────────────────────────────┐    │   │
│  │  │  deps.py  (get_current_user, require_permission,      │    │   │
│  │  │            require_auth, audit, _perm_cache)           │    │   │
│  │  └──────────────────────────────────────────────────────┘    │   │
│  └──────────────────────────────────────────────────────────────┘   │
│  PostgreSQL 15 (pgdata volume)                                       │
└──────────────────────────┬──────────────────────────────────────────┘
                           | mTLS (node-signed client cert)
┌──────────────────────────▼──────────────────────────────────────────┐
│  Puppet Nodes (puppets/)                                             │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │  node.py -- polls /work/pull, executes via runtime.py         │   │
│  │  runtime.py -- spawns `docker run` or `podman run`            │   │
│  │  /tmp/job_<guid>.<ext> -- temp script file (bind-mounted in)  │   │
│  └──────────────────────────────────────────────────────────────┘   │
│  Containerfile.node -- built image: localhost/axiom-node:cold-start │
└─────────────────────────────────────────────────────────────────────┘
                           | nginx at :80
┌──────────────────────────▼──────────────────────────────────────────┐
│  MkDocs docs site (docs/)                                            │
│  Two-stage Dockerfile: builder (mkdocs build) -> nginx:alpine       │
│  Content source: docs/docs/**/*.md + mkdocs.yml nav                 │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Fix Area 1: `/api/executions` CE-Gating

### How CE/EE Gating Works

The CE/EE split operates entirely at **startup** via `lifespan()` in `main.py`. The decision tree is:

1. Parse `AXIOM_LICENCE_KEY` from env. If valid and unexpired, set `app.state.licence = data` and `_licence_valid = True`.
2. If valid, call `load_ee_plugins(app, engine)` — discovers `axiom.ee` entry point, calls `plugin.register(ctx)`, mounts real EE routers.
3. If not valid, call `_mount_ce_stubs(app)` — mounts 6 stub routers from `ee/interfaces/`. Each stub router returns a hardcoded `JSONResponse(status_code=402, ...)`.

The stubs only cover routes they explicitly declare. There is no catch-all 402 gate; each EE route must be enumerated in an interface file.

### Where `/api/executions` Lives

`/api/executions` (GET list), `/api/executions/{id}` (GET single), and `/api/executions/{id}/attestation` are declared directly in `main.py` at lines 231, 296, and 339. They use `Depends(require_auth)` — standard CE auth — not EE gating. The stub router system has no interface file for executions; this path was never handed to EE.

Execution History (`ExecutionRecord` table, `GET /api/executions`) is a v10.0 feature documented as EE-only in the validated requirements. The routes are reachable on CE because they were placed in `main.py` rather than in an EE router.

### How to Add the Gate

There is no `require_ee_licence()` dependency in the codebase — this concept does not exist. Two patterns are available:

**Pattern A — Move routes to EE router (recommended):** Move the three execution routes from `main.py` into an EE router file (e.g., `ee/routers/execution_router.py`), and add stub routes in a new `ee/interfaces/executions.py`. The EE router file gets mounted by the EE plugin's `register(ctx)` method; the CE stub gets mounted by `_mount_ce_stubs()`. This mirrors exactly how audit, foundry, webhooks, and the other EE features are handled.

**Pattern B — Add a request-time dependency:** Create a `require_ee_licence` FastAPI dependency that checks `request.app.state.licence is not None` and raises `HTTPException(402)` if absent. This is simpler but diverges from the established architectural pattern — the stub-router approach is cleaner because it avoids mixing CE/EE logic in `main.py`.

Pattern A is the correct integration path because it keeps `main.py` as CE-only and all EE routes in `ee/`. It also ensures the 402 response format is consistent with all other EE stubs.

### Files Affected

| File | Change Type | What Changes |
|------|-------------|--------------|
| `puppeteer/agent_service/main.py` | Modified | Remove 3 execution routes (list, get, attestation) |
| `puppeteer/agent_service/ee/routers/execution_router.py` | New | Real execution routes (moved from main.py, with EE auth) |
| `puppeteer/agent_service/ee/interfaces/executions.py` | New | CE stub returning 402 for all 3 execution routes |
| `puppeteer/agent_service/ee/__init__.py` | Modified | Import executions stub; add to `_mount_ce_stubs()` |

Note: `/jobs/{guid}/executions` (per-job execution list, line 1369 in main.py) and the pin/unpin endpoints (lines 2274, 2291) and CSV export (line 2357) share the same scope problem and likely belong in EE scope as well, though the NOTABLE finding specifically calls out `GET /api/executions`.

### Constraint: No Breaking Change for EE Deployments

EE users currently rely on `GET /api/executions` returning 200. Moving the route to an EE router maintains that behaviour for licensed installs because `load_ee_plugins` mounts the real EE router. Route registration order matters: EE routers must be included before any possible 404 fallback, which the current plugin system already handles correctly.

---

## Fix Area 2: Containerfile.node — Docker CLI Install

### Current State

`puppets/Containerfile.node` already contains the correct Docker CE CLI install via multi-stage COPY:

```dockerfile
COPY --from=docker:cli /usr/local/bin/docker /usr/local/bin/docker
```

The comment in the file explains the rationale: on Debian 13 (Trixie), `docker.io` no longer ships the CLI binary — it requires `docker-cli` as a separate recommended package. Copying from `docker:cli` avoids adding the full Docker apt repo and delivers a statically linked binary.

This BLOCKER was fixed during the v14.0 run. The Containerfile already contains the correct fix.

### Why the `docker:cli` COPY Pattern Works

The `docker:cli` image (`docker.io/library/docker:cli`) is a minimal Alpine image containing the Docker CLI binary at `/usr/local/bin/docker`. The binary is statically linked — it carries no glibc/musl dependency and runs correctly on the `python:3.12-slim` (Debian bookworm) base. This is the Docker-official approach for DinD scenarios, avoiding the instability of Debian's `docker-ce-cli` apt package across Debian version transitions.

The current base image is `python:3.12-slim` (Debian 12 bookworm). The comment referencing "Debian 13 (Trixie)" is forward-looking documentation explaining why the apt approach was avoided. This distinction matters if the base image is ever bumped to a trixie-based image.

### Files Affected

| File | Change Type | What Changes |
|------|-------------|--------------|
| `puppets/Containerfile.node` | Already fixed in v14.0 | No further change needed for Docker CLI |

If any additional Containerfile changes are required (e.g., for PowerShell version or base image updates), rebuild:

```bash
docker build -t localhost/axiom-node:cold-start -f puppets/Containerfile.node puppets/
```

---

## Fix Area 3: `compose.cold-start.yaml` — `/tmp:/tmp` Bind Mount

### Why the Mount Is Required

`compose.cold-start.yaml` mounts `/tmp:/tmp` into `puppet-node-1` and `puppet-node-2` (lines 120 and 142). This is required by the DinD execution model in `node.py`.

`node.py` writes job scripts to a temp path inside the node container:

```python
tmp_path = f"/tmp/job_{guid}.{ext}"
with open(tmp_path, "w") as f:
    f.write(script)
mounts.append(f"{tmp_path}:{tmp_path}:ro")
```

The `docker run` command spawned by `runtime.py` runs against the **host Docker daemon** via the mounted `/var/run/docker.sock`. Host Docker resolves volume paths relative to the **host filesystem**, not the container filesystem. Without `/tmp:/tmp`, the script file written inside the node container is invisible to the host daemon when it tries to bind-mount it into the job container.

This BLOCKER was fixed during the v14.0 run. The mount is already present in `compose.cold-start.yaml`.

### Volume Conflict Analysis

`compose.cold-start.yaml` defines named volumes: `pgdata`, `certs-volume`, `caddy_data`, `caddy_config`, `node1-secrets`, `node2-secrets`. The `/tmp:/tmp` bind mount is a host bind mount, not a named volume. There is no conflict — Docker treats host bind mounts and named volumes as separate constructs at different levels.

### Security Note for Production Operators

The cold-start `/tmp:/tmp` mount is appropriate for local evaluation. For production nodes (the standalone `node-compose.yaml` pattern), the `/tmp:/tmp` mount is not required when the node container has direct filesystem visibility to the host paths it uses. In production, operators typically use a dedicated named volume or bind mount for script staging rather than sharing the entire `/tmp`. The docs should clarify this distinction.

### Files Affected

| File | Change Type | What Changes |
|------|-------------|--------------|
| `puppeteer/compose.cold-start.yaml` | Already fixed in v14.0 | `/tmp:/tmp` present for both node services |

No further code changes are needed. A documentation note in `enroll-node.md` explaining why `/tmp:/tmp` is required in DinD setups may be worthwhile.

---

## Fix Area 4: MkDocs Docs — Content Structure and CLI Alternatives

### MkDocs Content Structure

All content files live under `docs/docs/`. The nav is declared in `docs/mkdocs.yml`. The build pipeline is:

1. Builder stage: `mkdocs build --strict` (runs inside `python:3.12-slim`). The `--strict` flag means any broken link or undefined reference fails the build.
2. Runtime stage: `nginx:alpine` serves the compiled `site/` directory.

**Current nav for Getting Started** (from `docs/mkdocs.yml`):
```yaml
- Getting Started:
  - Prerequisites: getting-started/prerequisites.md
  - Install: getting-started/install.md
  - Running with Docker: getting-started/docker-deployment.md
  - Enroll a Node: getting-started/enroll-node.md
  - First Job: getting-started/first-job.md
```

For v14.1 all fixes are content edits to existing files, with one exception: if a new `ee-install.md` page is created (BLOCKER: "BLOCKER: `/api/admin/features` endpoint does not exist — `docs/getting-started/ee-install.md`"), both the file and a nav entry in `mkdocs.yml` must be added, otherwise `--strict` will fail or the file will be unreachable.

### Current Getting-Started File Status

| File | Current State | Open Gaps |
|------|--------------|-----------|
| `getting-started/install.md` | Has Steps 1-4 (clone, secrets.env, start, verify) and an EE section | Admin password discovery step missing; GitHub clone assumption; cold-start path not separated |
| `getting-started/enroll-node.md` | Has dashboard + CLI alternative, AGENT_URL table, Option A/B install | Partially patched during v14.0; verify image tag accuracy and socket mount documentation |
| `getting-started/first-job.md` | Has keygen, dashboard registration, manual signing, dispatch | Missing CLI/API dispatch path; `axiom-push` mentioned as a tip only, no full example |
| `getting-started/ee-install.md` | May not exist | If it exists: wrong endpoint (`/api/admin/features` vs `/api/features`); if not: entire file needed |

### Adding curl/API CLI Alternatives

`first-job.md` currently documents dashboard-only dispatch. The friction report BLOCKER is: "Guided form requires browser — no CLI/API dispatch path documented."

The architecture supports two CLI-facing paths:

**Path 1 — axiom-push CLI (simplest):**
```bash
pip install axiom-sdk
axiom-push login https://<orchestrator>:8001
axiom-push push hello.py --key dev-operator-key
```

This is already mentioned as a tip in `first-job.md` but without a full working example. The `axiom-push` package on PyPI handles signing and submission in one command. Adding a full example requires no backend changes.

**Path 2 — Raw curl (explicit, shows the API surface):**

First, get a JWT:
```bash
TOKEN=$(curl -sk -X POST https://<host>:8001/auth/login \
  -H 'Content-Type: application/x-www-form-urlencoded' \
  -d 'username=admin&password=<pass>' \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")
```

Register a public key (requires a key to already be generated):
```bash
curl -sk -X POST https://<host>:8001/api/signatures \
  -H "Authorization: Bearer $TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{"name": "dev-key", "public_key_pem": "'"$(cat verification.key)"'"}'
```

Dispatch a job via `POST /jobs`:
```bash
curl -sk -X POST https://<host>:8001/jobs \
  -H "Authorization: Bearer $TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{"task_type": "script", "runtime": "python", "script_content": "print(\"hello\")", "signature": "<b64-sig>", "signature_id": "<key-id>", "target_tags": ["general"]}'
```

The `POST /jobs` endpoint accepts `JobCreate` which includes `script_content`, `signature`, `signature_id`, and `target_tags`. This endpoint is in `main.py` (CE-accessible). No backend changes are required to add these docs.

### Correct Features Endpoint

The friction report BLOCKER documents that `GET /api/admin/features` does not exist. The correct endpoint is `GET /api/features` (unauthenticated, line 903 in `main.py`). Any docs referencing `/api/admin/features` must be updated to `/api/features`.

### Impact of Adding curl Alternatives

All doc changes are content-only. The underlying API supports all described operations. No backend code changes are required for the CLI documentation additions.

### Files Affected for Docs Fixes

| File | Change Type | What Changes |
|------|-------------|--------------|
| `docs/docs/getting-started/install.md` | Modified | Admin password discovery step, cold-start vs full-stack separation |
| `docs/docs/getting-started/enroll-node.md` | Modified | Verify image tag accuracy, Docker socket mount documentation |
| `docs/docs/getting-started/first-job.md` | Modified | Add curl/API dispatch path, add full axiom-push example |
| `docs/docs/getting-started/ee-install.md` | New or Modified | Fix `/api/features` endpoint; create if absent |
| `docs/mkdocs.yml` | Modified (conditional) | Add nav entry for `ee-install.md` if file is new |
| `docs/docs/licensing.md` | Modified | Fix `AXIOM_EE_LICENCE_KEY` vs `AXIOM_LICENCE_KEY` naming inconsistency |

---

## Build Order for Applying Fixes

The fix areas have no hard dependencies on each other, but a recommended order exists:

**Step 1 — Backend code patches**

Apply the `/api/executions` CE-gating fix first. Reason: if docs are published before the gate is added, CE users following the docs will see 200 responses from `/api/executions`, contradicting the EE-only framing in the docs.

```bash
docker compose -f puppeteer/compose.cold-start.yaml build agent
docker compose -f puppeteer/compose.cold-start.yaml up -d --no-build agent
```

**Step 2 — Containerfile.node (if any changes needed)**

If additional Containerfile changes are made, rebuild:
```bash
docker build -t localhost/axiom-node:cold-start -f puppets/Containerfile.node puppets/
```

**Step 3 — Docs changes**

Edit content files, then rebuild the docs image:
```bash
docker compose -f puppeteer/compose.cold-start.yaml build docs
docker compose -f puppeteer/compose.cold-start.yaml up -d --no-build docs
```

The `--strict` MkDocs flag catches broken links and undefined nav references immediately at build time.

**Step 4 — compose.cold-start.yaml (if any changes needed)**

Compose file changes require a stack restart:
```bash
docker compose -f puppeteer/compose.cold-start.yaml down
docker compose -f puppeteer/compose.cold-start.yaml --env-file .env up -d
```

---

## Existing Deployment Impact

### Fresh Deployments (no existing DB)

No migration concerns. All fixes are:
- Backend code changes with no new DB tables and no schema changes
- Docs content changes with no code impact
- Containerfile and compose changes that take effect on image rebuild

### Existing CE Deployments

Moving `/api/executions` to an EE stub changes observable behaviour: requests that previously returned 200 will return 402. This is intentional and correct. The change is not backward-compatible for CE users who were accessing execution history — they will need to upgrade to EE to continue using this feature.

**Data note:** Existing CE deployments may have accumulated `ExecutionRecord` rows in the database. These rows remain in the DB after the fix but are inaccessible from CE via the API. The data is not deleted; it is only gated at the API layer. This is acceptable since the feature was always intended as EE-only.

### Existing EE Deployments

No impact. EE deployments load real EE routers via `load_ee_plugins()`. The CE stubs (including any new executions stub) are never mounted when a valid licence is present.

---

## Component Boundaries

| Component | Responsibility | What v14.1 Changes |
|-----------|---------------|-------------------|
| `main.py` | CE routes + lifespan EE gating | Remove 3 execution routes |
| `ee/__init__.py` | Stub mount orchestration | Add executions stub to `_mount_ce_stubs()` |
| `ee/interfaces/executions.py` | CE 402 stub for execution routes | New file |
| `ee/routers/execution_router.py` | Real EE execution routes | New file |
| `deps.py` | Auth dependencies (CE + EE) | No change |
| `puppets/Containerfile.node` | Node image build | No change (already fixed in v14.0) |
| `puppeteer/compose.cold-start.yaml` | Cold-start evaluation stack | No change (already fixed in v14.0) |
| `docs/docs/getting-started/*.md` | First-user docs | Content edits on 3-4 files |
| `docs/mkdocs.yml` | Doc nav | Add ee-install entry if file is new |

---

## Anti-Patterns to Avoid

### Anti-Pattern 1: Adding an Inline EE Licence Check to main.py

**What people might do:** Add `if not request.app.state.licence: raise HTTPException(402)` directly inside the existing execution route handlers in `main.py`.

**Why it's wrong:** It pollutes `main.py` with EE logic, diverges from the established stub-router pattern, and the check runs even in EE mode (inefficiently). It makes the CE/EE boundary invisible to code reviewers.

**Do this instead:** Move the routes to an EE router and add a CE stub file. This is the existing pattern for all 6 other EE feature areas.

### Anti-Pattern 2: Forgetting to Add the Nav Entry When Creating ee-install.md

**What people might do:** Create `docs/docs/getting-started/ee-install.md` without adding it to the `nav:` block in `mkdocs.yml`.

**Why it's wrong:** MkDocs with `--strict` will either fail the build (if the file is referenced from another page) or silently omit the page from navigation (if it is not). The `--strict` flag catches this at build time, but only if there is an inbound link.

**Do this instead:** Add the nav entry to `mkdocs.yml` at the same time as creating the file. The entry goes under `Getting Started:` after `First Job:`.

### Anti-Pattern 3: Using Raw Hex Token Instead of enhanced_token for Node Enrollment

**What people might do:** Use the token from `POST /api/enrollment-tokens` response for node enrollment.

**Why it's wrong:** The raw token is a hex string without the embedded Root CA PEM. Node enrollment requires the base64-encoded JSON enhanced token which includes the Root CA for mTLS bootstrap.

**Do this instead:** Use `POST /admin/generate-token` and extract the `enhanced_token` field from the response.

---

## Sources

- `puppeteer/agent_service/main.py` — lines 71-204 (lifespan), 229-340 (execution routes), 903-919 (`/api/features` endpoint)
- `puppeteer/agent_service/ee/__init__.py` — CE/EE dispatch mechanism (`_mount_ce_stubs`, `load_ee_plugins`)
- `puppeteer/agent_service/ee/interfaces/*.py` — stub router pattern (audit.py as reference implementation)
- `puppeteer/agent_service/deps.py` — auth dependency structure (`require_auth`, `require_permission`)
- `puppets/environment_service/runtime.py` — DinD execution model
- `puppets/environment_service/node.py` lines 551-704 — script temp file lifecycle (`/tmp/job_<guid>.<ext>`)
- `puppets/Containerfile.node` — `COPY --from=docker:cli` pattern with rationale comment
- `puppeteer/compose.cold-start.yaml` — `/tmp:/tmp` bind mounts (lines 120, 142), named volume definitions
- `docs/mkdocs.yml` — nav structure, plugin list
- `docs/docs/getting-started/*.md` — current content state of all 5 pages
- `docs/Dockerfile` — two-stage docs build, `--strict` mkdocs flag
- [Docker multi-stage builds](https://docs.docker.com/build/building/multi-stage/) — `COPY --from` pattern
- [Docker on Debian](https://docs.docker.com/engine/install/debian/) — Debian trixie moby-cli removal

---

*Architecture research for: Axiom v14.1 First-User Readiness fixes*
*Researched: 2026-03-25*
