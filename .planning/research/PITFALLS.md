# Pitfalls Research

**Domain:** First-user readiness fixes for a self-hosted job orchestration platform — docker-ce-cli in Debian containers, /tmp DinD volume mounts, FastAPI CE-gating stubs, and MkDocs getting-started doc rewrites
**Researched:** 2026-03-25
**Confidence:** HIGH (based on direct codebase inspection of `puppets/Containerfile.node`, `puppeteer/compose.cold-start.yaml`, `puppeteer/agent_service/main.py`, `puppeteer/agent_service/ee/__init__.py`, `docs/mkdocs.yml`, and v14.0 cold-start friction report findings; supplemented by Docker official docs, FastAPI lifecycle documentation, and MkDocs issue tracker)

---

## Critical Pitfalls

### Pitfall 1: PowerShell .deb Uses a Hard-Coded amd64 URL — Silently Broken on arm64

**What goes wrong:**
`Containerfile.node` downloads PowerShell 7.6.0 via a direct GitHub releases URL ending in `_amd64.deb`. On an arm64 build host (Apple Silicon Mac, AWS Graviton, Raspberry Pi), `docker build` or `docker compose build` completes without error because `apt-get install /tmp/powershell.deb` silently accepts the wrong-architecture package on some Debian versions, but PowerShell will then fail at runtime with `Exec format error`. On other Debian versions, apt errors out during the build. Either way, multi-arch CI or developer machines running arm64 hit this.

**Why it happens:**
Direct `.deb` URLs must be architecture-specific. The current URL hardcodes `amd64.deb`. Multi-arch builds are not guarded by a `--platform linux/amd64` in the Containerfile.

**How to avoid:**
Add `--platform linux/amd64` as the first line of `Containerfile.node` (after `FROM`) if only amd64 is supported, or use a `RUN ARCH=$(dpkg --print-architecture)` conditional to select the correct `.deb` URL at build time. At minimum, document the amd64-only constraint clearly in the Containerfile comment.

**Warning signs:**
- `docker buildx build` fails with `dpkg: error processing archive ... wrong architecture`
- PowerShell shows `Exec format error` on first run inside a built container
- CI pipeline builds pass on amd64 runners but fail on arm64 runners

**Phase to address:**
Containerfile.node fixes phase (whichever phase patches the node image). Add a build-time platform guard alongside the PowerShell install change.

---

### Pitfall 2: Docker CE CLI COPY --from=docker:cli Breaks in Air-Gapped / Registry-Mirror Environments

**What goes wrong:**
The Containerfile uses `COPY --from=docker:cli /usr/local/bin/docker /usr/local/bin/docker` to pull the Docker binary from Docker Hub's official `docker:cli` image without a digest pin. In air-gapped environments (the platform's stated use case), this reference resolves to Docker Hub at build time. If the build host has no internet access or only a partial mirror, the build fails silently at layer fetch. In online environments, the `docker:cli` tag is a floating tag — it can change to a new Docker CLI version without warning, potentially introducing API incompatibilities.

**Why it happens:**
`COPY --from=docker:cli` requires the builder to pull `docker:cli` from a registry. It is not pinned to a digest. Air-gap documentation says nodes deploy from the Containerfile, but the Containerfile has an implicit Docker Hub dependency that the docs do not call out.

**How to avoid:**
- For air-gapped deployments: pre-pull `docker:cli` and push to the local registry mirror, or change to `COPY --from=localhost:5000/docker:cli ...`. Document this step explicitly in the air-gap operation guide.
- For reproducibility: pin the image to a digest (`docker:cli@sha256:...`) rather than floating tag.
- Include a note in `Containerfile.node` comments that air-gapped builds must mirror this image.

**Warning signs:**
- `docker compose build` fails with `pull access denied for docker` or `network timeout` on nodes without internet
- Different Docker CLI versions appear across builds in the same environment
- The air-gap doc section says "mirror PyPI and APT" but does not mention mirroring `docker:cli`

**Phase to address:**
Containerfile.node fixes phase. Should be addressed in the same phase as other node image changes to keep the air-gap story consistent.

---

### Pitfall 3: /tmp:/tmp Bind Mount Creates a Directory on the Host When /tmp Does Not Exist as a File

**What goes wrong:**
`compose.cold-start.yaml` mounts `/tmp:/tmp` as a bind mount for both puppet nodes. This is correct and necessary for DinD job execution — the node writes temp scripts to `/tmp` and the Docker socket passes that path to the daemon, which must resolve it on the host filesystem. However, if the host's `/tmp` is a `tmpfs` mount (which it is by default on modern systemd Linux hosts — `tmpfs on /tmp type tmpfs`), the bind mount works correctly in most cases. The documented BLOCKER from v14.0 was the opposite problem: when the wrong path was configured as a file instead of a directory, Docker Compose created a directory where a file was expected.

The real current risk is different: on some container runtimes and hosts, `/tmp` permissions differ. The node container runs as root, but the host `/tmp` is typically `1777` (sticky bit). Jobs that write temp files with restrictive umasks, then try to read them from the outer Docker daemon context, can fail with permission denied if the outer daemon runs as a different UID.

Additionally, `/tmp:/tmp` exposes the host's full `/tmp` to every node container. If a job writes sensitive data to `/tmp` before cleanup (the normal pattern in `runtime.py`), that data is visible to any other process on the host reading `/tmp`. This is acceptable in a single-tenant homelab but is a security concern in shared-host deployments.

**Why it happens:**
DinD requires the `/tmp` path to be resolvable by the host Docker daemon, so a bind mount (not a named volume) is required. The simplest fix is to use the host's `/tmp` directly. The risk is accepted implicitly without documentation.

**How to avoid:**
- Use a bind mount to a dedicated subdirectory: `/tmp/axiom-node-1:/tmp` rather than the root `/tmp`. Create the host directory in the compose file using `init: true` or a pre-up script. This scopes exposure.
- Document in the getting-started guide that `/tmp:/tmp` is a DinD requirement and what it implies for single-node vs. multi-tenant deployments.
- For the permission issue: ensure the node container runs with the same UID as the Docker daemon (root in most deployments) and that `/tmp` has at least `1777`.

**Warning signs:**
- Jobs fail with `permission denied` when writing or reading `/tmp` temp files
- `docker compose up` creates a `/tmp` directory inside the project directory instead of using the host's `/tmp`
- Security reviews flag the broad `/tmp` mount surface area

**Phase to address:**
compose.cold-start.yaml fixes phase. The security implication should be documented in the same phase that rewrites the getting-started guide.

---

### Pitfall 4: FastAPI Route Registration Order — CE Stubs Registered After Main Routes Cause Duplicate-Route Shadows

**What goes wrong:**
In `main.py`, CE stub routers are mounted via `_mount_ce_stubs(app)` inside the `lifespan` async context manager (startup event). FastAPI builds its route table when `include_router` is called. Routes registered via `include_router` in the lifespan are added after all routes defined at module level with `@app.get(...)`. This means if a stub route path exactly matches a route already defined in `main.py`, the stub is registered but never reached — the earlier route wins. Conversely, if a new EE route is added to a stub router that collides with a prefix used by an existing CE route in `main.py`, the CE route may shadow the stub for `GET` but not `POST`, creating inconsistent behaviour.

The specific known case: `/api/executions` is defined directly in `main.py` (line 231) and returns HTTP 200 in CE mode — it is not gated. An execution stub router has not been added yet. When the new stub router is added, it must be registered at startup (in lifespan) like the others — but the `@app.get("/api/executions")` declaration in `main.py` will shadow it. The fix requires removing the direct route definition and moving it into the EE router, but that changes the CE/EE boundary contract.

**Why it happens:**
FastAPI does not deduplicate routes — it uses first-match from the route list. Module-level `@app.get(...)` decorators run at import time, before `lifespan`. Stub routers registered in `lifespan` arrive later in the route list and are therefore shadowed by any identically-pathed module-level route.

**How to avoid:**
- When adding a CE stub for a route that currently exists in `main.py`, the original `@app.get(...)` definition in `main.py` must be removed (or replaced with a CE-mode conditional) before the stub router will work.
- Write a test that starts the app in CE mode (no `AXIOM_LICENCE_KEY`) and asserts that every stub path returns 402. This test will catch shadowed stubs immediately.
- Review the stub router registration in `ee/__init__.py` — stub routers should be registered early (ideally also in lifespan, but before any conflicting routes are reachable). Consider moving stub registration to a decorator-time hook rather than lifespan if ordering becomes a recurring problem.

**Warning signs:**
- A stub route returns 200 (not 402) in CE mode
- The test suite passes for stub routes that were never actually reached
- A new stub router is added but `/api/executions` still returns 200 in CE mode

**Phase to address:**
FastAPI CE-gating fixes phase. Write the CE smoke test (`test_ce_smoke.py` already exists — extend it) before making the change so the test fails first, then make the fix, then verify 402.

---

### Pitfall 5: Getting-Started Doc Rewrites Break Deep Links in the Existing mkdocs.yml Navigation

**What goes wrong:**
When heading text is renamed during a doc rewrite — for example changing "## Step 3: Enroll your first node" to "## Enroll a Node" — MkDocs auto-generates anchor IDs from the heading text by slugifying it. Any link pointing to `#step-3-enroll-your-first-node` (from another doc, from the sidebar `nav:` section, or from external references) silently returns a 404 anchor. MkDocs does not warn about broken anchor links by default. The build succeeds, the doc site appears correct, and the broken links are only discovered by users following old bookmarks or cross-doc references.

Additionally, if a page is renamed or moved (e.g. `getting-started/enroll-node.md` split into two files), the `nav:` section in `mkdocs.yml` must be updated or the page disappears from the site map entirely. MkDocs will warn about unreferenced pages during `mkdocs build --strict` but not about broken cross-page links.

**Why it happens:**
MkDocs slugifies anchors from heading text at build time. There is no redirect mechanism for changed anchors. Developers rewriting docs for clarity routinely rename headings without checking whether those headings are referenced elsewhere.

**How to avoid:**
- Before rewriting: run `grep -r "getting-started/enroll-node\|getting-started/first-job\|getting-started/install" docs/docs/` to find all internal cross-references to the files being changed.
- After rewriting: update `mkdocs.yml` `nav:` section to reflect any file additions or path changes.
- Use `mkdocs build --strict` after every doc change — this fails on warnings, catching orphaned pages before they ship.
- Keep heading anchor IDs stable by adding explicit HTML anchors (`<a id="enroll-node"></a>`) on critical sections if the heading text needs to change.
- Check the existing `nav:` structure: `docs/mkdocs.yml` has a Getting Started section with exact file paths — any file rename without updating `nav:` removes the page from the sidebar.

**Warning signs:**
- `mkdocs build` outputs `WARNING - ... is not found in the documentation files`
- Cross-references in `runbooks/nodes.md` or `security/mtls.md` point to renamed sections
- The sidebar in the built docs site no longer shows a renamed page

**Phase to address:**
Documentation fixes phase. Run `mkdocs build --strict` as the final step of every doc change phase to catch issues before the roadmapper considers the phase complete.

---

## Technical Debt Patterns

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| Floating `docker:cli` tag in Containerfile | Simple, always gets latest Docker CLI | Unreproducible builds; air-gap friction | Never for a release image — pin to digest |
| `/tmp:/tmp` full host bind mount | Simplest DinD setup, zero config | Exposes all of host `/tmp` to node containers; multi-tenant security risk | Acceptable for single-tenant homelab only; document the trade-off |
| Direct `@app.get("/api/executions")` in main.py without CE gate | Faster to write, no EE machinery required | Every new route that should be EE-only must be manually audited; easy to miss | Never — the CE/EE boundary must be enforced systematically |
| Rewriting doc pages without running `--strict` | Saves 30 seconds | Broken links in production docs; hard to discover post-deploy | Never — `mkdocs build --strict` is a 10-second check |
| Hard-coded `amd64.deb` in Containerfile with no platform guard | Works on developer's machine | Silent failures on arm64 CI runners and user machines | Never for a published image — add the platform guard before v14.1 ships |

---

## Integration Gotchas

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|------------------|
| Docker CE CLI in Containerfile via `COPY --from` | Assuming `docker:cli` floating tag is air-gap safe | Pre-pull and mirror `docker:cli` image; pin to digest; document in air-gap guide |
| PowerShell `.deb` install in Dockerfile | Not setting `DOTNET_SYSTEM_GLOBALIZATION_INVARIANT=1` for Debian 13 (libicu74 collation change) | Already done in current Containerfile — must not be removed when updating the PowerShell version |
| FastAPI CE stubs via `include_router` in lifespan | Adding a stub for a route that still has a module-level `@app.get(...)` definition | Remove or conditionalise the module-level route first; verify with `test_ce_smoke.py` |
| MkDocs `nav:` section | Adding a new page without updating `nav:` | Always update `nav:` in the same commit as the file creation |
| DinD `/tmp` bind mount | Using a named volume (`- tmp-data:/tmp`) instead of bind mount | DinD requires a real host path that the outer Docker daemon can resolve; named volumes are not visible to the outer daemon |

---

## Performance Traps

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|----------------|
| CE permission cache pre-warm skipped silently | Every API request hits the DB for permission lookup; not a correctness issue but a latency issue | The existing try/except in lifespan already handles this — do not change the error-swallowing behaviour | Relevant only when adding new CE-gated routes that call `require_permission` |

---

## Security Mistakes

| Mistake | Risk | Prevention |
|---------|------|------------|
| `/tmp:/tmp` bind mount with no documentation | A compromised job can read other jobs' temp artefacts if they overlap in execution time; host `/tmp` exposed | Document the trust boundary in getting-started; consider scoped `/tmp/axiom-node-N:/tmp` per node |
| `/api/executions` returning 200 in CE mode | CE users get EE Execution History data for free; breaks the CE/EE feature gate contract | Add the CE stub router and remove the direct route from `main.py` before v14.1 ships |
| PowerShell `.deb` downloaded from GitHub releases over plain `wget` in Dockerfile | No hash verification — MITM or GitHub release tampering would silently replace the binary | Add `sha256sum` verification after the `wget` download; pin the expected hash in the Containerfile comment |

---

## UX Pitfalls

| Pitfall | User Impact | Better Approach |
|---------|-------------|-----------------|
| Getting-started guide assumes Docker Hub image pull available | Air-gapped first users hit `pull access denied` on the first step | Add a prerequisites section stating which images need to be available; provide a mirror checklist |
| JOIN_TOKEN documented as GUI-only | CLI users (most advanced users doing scripted deployments) cannot automate node enrollment | The API endpoint already exists (`POST /admin/generate-token`) — document it alongside the GUI path |
| Admin password setup buried or missing | First user cannot log in; must inspect running container environment to recover the password | Move admin password setup to step 1 of the install guide, before any `docker compose up` command |
| EE licence injection method inconsistency across docs | Users inject `AXIOM_LICENCE_KEY` as an env var in compose but `AXIOM_EE_LICENCE_KEY` appears in `licensing.md` | Pick one name, use it everywhere, and add a `AXIOM_EE_LICENCE_KEY` → `AXIOM_LICENCE_KEY` migration note |

---

## "Looks Done But Isn't" Checklist

- [ ] **Docker CLI in node image:** Building the image succeeds — verify `docker --version` runs inside a running container before marking done
- [ ] **PowerShell in node image:** Image builds — verify `pwsh --version` inside a running container; also verify a PowerShell job dispatched via the platform actually completes with COMPLETED status
- [ ] **CE stub for `/api/executions`:** Stub router added — verify with `curl` against a running CE stack that the endpoint returns 402, not 200; check all three paths (`GET /api/executions`, `GET /api/executions/{id}`, `PATCH /api/executions/{id}/pin`)
- [ ] **MkDocs doc rewrite:** Page renders — run `mkdocs build --strict` and verify zero warnings; also verify `nav:` in `mkdocs.yml` references all new or renamed files
- [ ] **`/tmp:/tmp` fix:** Compose file updated — run a job end-to-end (not just node enrollment) to verify the DinD temp file path resolves correctly through the Docker socket

---

## Recovery Strategies

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|----------------|
| Wrong-arch PowerShell in built image | LOW | Rebuild the image with corrected URL or `--platform` guard; no data migration needed |
| Air-gapped build fails due to `docker:cli` pull | MEDIUM | Mirror `docker:cli` to local registry, update Containerfile reference, rebuild; requires registry access |
| CE stub shadowed by module-level route (still returns 200) | LOW | Remove module-level route, add to EE router, restart app; no DB migration needed |
| Broken anchor links in shipped docs | MEDIUM | Fix heading anchors, rebuild and redeploy the docs container; external bookmarks already broken cannot be recovered — add redirects if docs are hosted externally |
| `/tmp` permission failure in DinD node | LOW | Change compose volume to scoped `/tmp/axiom-node-N:/tmp`; `docker compose up -d` to apply; no data loss |

---

## Pitfall-to-Phase Mapping

| Pitfall | Prevention Phase | Verification |
|---------|------------------|--------------|
| amd64-only PowerShell `.deb` URL | Containerfile.node fixes phase | Run `docker build` on arm64 host or CI; `pwsh --version` in container |
| `docker:cli` air-gap fragility | Containerfile.node fixes phase + air-gap doc update | Attempt build with `--network=none` after mirroring |
| `/tmp:/tmp` DinD permission and exposure | compose.cold-start.yaml fixes phase | Run a job end-to-end; inspect host `/tmp` for residual artefacts |
| FastAPI route shadow blocking CE stub | FastAPI CE-gating fixes phase | `test_ce_smoke.py` — all EE routes return 402 in CE mode |
| Doc deep-link breakage from heading renames | Documentation fixes phase | `mkdocs build --strict`; manual audit of cross-doc `#anchor` references |
| MkDocs `nav:` not updated after page add/rename | Documentation fixes phase | `mkdocs build --strict` outputs warning for unreferenced pages |
| Admin password setup missing from install docs | Documentation fixes phase | End-to-end cold-start from docs only — first user can log in without consulting source code |
| JOIN_TOKEN CLI path undocumented | Documentation fixes phase | API-only cold-start (no browser) can enroll a node using only the docs |

---

## Sources

- Direct codebase inspection: `puppets/Containerfile.node` (current state with `COPY --from=docker:cli` and PowerShell `.deb` install)
- Direct codebase inspection: `puppeteer/compose.cold-start.yaml` (current `/tmp:/tmp` bind mounts)
- Direct codebase inspection: `puppeteer/agent_service/main.py` (lines 231+, `/api/executions` without CE gate)
- Direct codebase inspection: `puppeteer/agent_service/ee/__init__.py` (`_mount_ce_stubs` registration in lifespan)
- Direct codebase inspection: `docs/mkdocs.yml` (current `nav:` structure)
- Project v14.0 friction report: 6 BLOCKERs fixed mid-run including the `/tmp` directory creation issue and wrong node image tag
- [Docker CE CLI official install docs — Debian](https://docs.docker.com/engine/install/debian/)
- [Docker GPG key deprecated apt-key issue tracker](https://github.com/docker/docs/issues/22041)
- [FastAPI lifecycle guide — startup order and pitfalls](https://medium.com/@dynamicy/fastapi-starlette-lifecycle-guide-startup-order-pitfalls-best-practices-and-a-production-ready-53e29dcb9249)
- [Docker tmpfs mounts — official docs](https://docs.docker.com/engine/storage/tmpfs/)
- [tmpfs permissions reset issue — docker/for-linux#138](https://github.com/docker/for-linux/issues/138)
- [MkDocs anchor link breakage on heading rename — mkdocs/mkdocs#744](https://github.com/mkdocs/mkdocs/issues/744)
- [MkDocs anchor validation — mkdocs/mkdocs#658](https://github.com/mkdocs/mkdocs/issues/658)

---
*Pitfalls research for: v14.1 First-User Readiness — cold-start UX fixes*
*Researched: 2026-03-25*
