# Pitfalls Research

**Domain:** Adding transitive dependency resolution, multi-ecosystem mirror backends, Foundry CRUD completeness, script analysis (AST), curated bundles, and operator UX to an existing Docker-image-building orchestration platform (Axiom v19.0)
**Researched:** 2026-04-01
**Confidence:** HIGH for pip/dep-resolution and Docker-socket pitfalls (official docs + confirmed issue trackers); MEDIUM for AST mapping and compose sprawl (community sources + direct code inspection); HIGH for Conda licensing (Anaconda's own legal pages)

---

## Critical Pitfalls

### Pitfall 1: `--no-deps` Mirror Leaves Full Dep-Tree Incomplete — STRICT Mode Fails at Install Time

**What goes wrong:**
The current `mirror_service.py` runs `pip download --no-deps` for each `ApprovedIngredient`. When a node's Foundry-built image runs `pip install` from the local mirror with `--no-index`, it fails for packages that have their own transitive dependencies (e.g. `requests` needs `certifi`, `urllib3`, `charset-normalizer`, `idna`). In STRICT mode the node has no internet fallback, so the entire install aborts and the Foundry-built image is silently broken — it builds fine (Dockerfile `pip install` can reach the mirror at image-build time if fall-through is still allowed), but the resulting image is missing packages at runtime if the Dockerfile itself adds `--no-index`.

The worst case: the image builds successfully, passes BOM validation, and ships to nodes. The error only surfaces when a job tries to `import requests` inside the container.

**Why it happens:**
`--no-deps` is correct for single-ingredient audit (CVE scan the exact wheel without noise), but wrong for mirror population. Developers conflate "we have the wheel" with "we have everything needed to install it." The gap is invisible until the full air-gap scenario is tested end-to-end.

**How to avoid:**
- Add a separate `mirror_ingredient_with_deps()` path that drops `--no-deps` and adds `--find-links` pointing to the already-mirrored directory so pip resolves transitively:
  ```python
  cmd = [
      "pip", "download",
      "--dest", MirrorService.PYPI_PATH,
      "--find-links", MirrorService.PYPI_PATH,
      "--platform", target_platform,
      "--only-binary=:all:",
      req
  ]
  ```
- Store the full resolved dep-tree in `ApprovedIngredient.transitive_deps` (JSON list) so the UI can show the complete tree before mirroring starts.
- Add a post-mirror smoke test: spin up a throwaway container from the target base image with `--network none`, run `pip install <pkg> --no-index --find-links /mirror`, and assert exit code 0. Fail the mirror job if the smoke test fails.

**Warning signs:**
- BOM reports only the top-level package, not its deps.
- MIRRORED status set on an ingredient that has unresolved `Requires-Dist` entries in its wheel metadata.
- Air-gap test with `iptables` isolation shows `pip install` failures despite "MIRRORED" status.

**Phase to address:** Phase 1 (Transitive Dependency Resolution) — must be the first thing solved because every downstream feature (multi-ecosystem mirrors, STRICT mode, CVE scanning transitive deps) depends on the dep-tree being correct and complete.

---

### Pitfall 2: Platform Tag Mismatch Breaks Alpine/musl Images Silently

**What goes wrong:**
`pip download --platform manylinux2014_x86_64` downloads glibc wheels. Alpine Linux uses musl libc. A glibc wheel installed into an Alpine container will import-fail with "ELF file OS ABI invalid" or just segfault — no helpful Python error. The image builds successfully; the runtime failure is silent until a job actually imports the package.

**Why it happens:**
`manylinux` and `musllinux` are separate platform tag families (PEP 656). The `pip download --platform` flag only downloads for the requested tag. Developers assume "linux wheel = any linux." A single mirror path for all OS families makes it worse — the same wheel directory is used for both Debian and Alpine images.

**How to avoid:**
- Mirror each package in **two separate paths**: `pypi/manylinux/` (for DEBIAN/FEDORA os_family) and `pypi/musllinux/` (for ALPINE os_family). Use `--platform manylinux2014_x86_64` for the former, `--platform musllinux_1_1_x86_64` for the latter.
- Store `target_platform` on each mirrored artifact row, not just on the ingredient.
- The pip.conf injected into Foundry-built images must point to the OS-family-specific sub-path.
- Validate: after downloading a wheel, parse its filename to confirm the platform tag matches the intended target before setting `mirror_status = "MIRRORED"`.

**Warning signs:**
- The PYPI_PATH directory contains `*-manylinux*` wheels but the image being built has `alpine` in its base OS.
- `pip install` in Alpine CI container succeeds (pip falls back to source dist) but the binary extension actually loaded is the wrong ABI.

**Phase to address:** Phase 1 (Transitive Dependency Resolution) — the multi-platform mirror layout must be established before any other mirror backend work, otherwise each ecosystem phase will need to retrofit the same split.

---

### Pitfall 3: Circular Dependency Explosion Hangs the Dep-Resolution Worker

**What goes wrong:**
Circular deps (A→B→A, or longer rings) exist in the wild PyPI ecosystem. When the dep-resolution worker attempts full transitive download without a visited-set guard, it loops indefinitely, consuming memory and blocking the `asyncio.Semaphore`. Pip itself raises `ResolutionTooDeepError` at depth 200+ which surfaces as an unhandled exception and sets `mirror_status = "FAILED"` — but not before the worker thread has blocked for several seconds. With `asyncio.to_thread`, a hung thread holds a semaphore slot, starving other mirror jobs.

**Why it happens:**
`pip download` without `--no-deps` may invoke pip's resolver repeatedly for deep dependency chains. The resolver can stack-overflow or time out on pathological dependency graphs. The current code has a single `subprocess.run` call with no timeout and no recursive visited-set.

**How to avoid:**
- Set `--timeout 60` and pass `--progress-bar off` in `pip download` subprocess calls. Add `timeout=90` to `subprocess.run`.
- Use `pip-compile` (pip-tools) to pre-resolve the full dep-tree before downloading — pip-compile detects cycles and raises a clean error. Store the compiled requirements lockfile per ingredient.
- Implement a visited-set in `mirror_ingredient_with_deps()` that short-circuits if a package+version is already in the PYPI_PATH directory.
- Cap `asyncio.Semaphore` for dep-resolution throwaway containers separate from Foundry build semaphore (current `_build_semaphore = asyncio.Semaphore(2)` covers builds; resolution needs its own gate).

**Warning signs:**
- Mirror jobs stuck in `PENDING` / never transitioning to `MIRRORED` or `FAILED`.
- Docker socket shows long-lived throwaway containers.
- `asyncio.to_thread` workers accumulating without completing.

**Phase to address:** Phase 1 (Transitive Dependency Resolution) — concurrent resolution must be designed safely from the start.

---

### Pitfall 4: Docker Socket Contention Between Foundry Builds and Dep-Resolution Containers

**What goes wrong:**
Foundry builds (`docker build`) and throwaway dep-resolution containers (`docker run --rm pip download ...`) both share the single `/var/run/docker.sock` mount. The Foundry build semaphore (`asyncio.Semaphore(2)`) only limits Foundry builds — it doesn't know about dep-resolution containers. Under load: two concurrent Foundry builds + multiple simultaneous mirror-trigger requests each spawning a container = Docker daemon OOM or "Error response from daemon: layer already being pulled" errors.

**Why it happens:**
The Docker daemon has a single write lock on layer operations. Concurrent `docker build` and `docker run` operations that pull shared base layers create lock contention. The agent container has no visibility into what the daemon is doing, and the two semaphore namespaces are independent.

**How to avoid:**
- Use a **single shared semaphore** for all Docker-socket operations: `_docker_semaphore = asyncio.Semaphore(3)`. Both `foundry_service.build_template()` and any dep-resolution container spawning must acquire it.
- Alternatively, **avoid Docker-in-Docker for dep resolution entirely**: run `pip download` directly inside the agent container (which already has pip) using a virtual environment per resolve job. This eliminates the Docker socket contention for the dep-resolution path and is simpler to implement correctly.
- If Docker is used for resolution, add a health check after each `docker run --rm` that confirms the container exited 0 before releasing the semaphore slot.

**Warning signs:**
- `docker build` taking 3-5x longer than baseline when mirror sync is also running.
- "context deadline exceeded" or "layer does not exist" Docker errors in agent logs.
- `docker ps` shows many `python-mirror-resolver` containers queued behind each other.

**Phase to address:** Phase 1 if dep-resolution uses throwaway containers; Phase 2 (Mirror Ecosystem Expansion) if the problem is amplified by 6 additional backends each spawning containers.

---

### Pitfall 5: Conda `defaults` Channel Triggers Commercial Licensing Violation

**What goes wrong:**
Anaconda's Terms of Service (updated again July 2025) require a paid commercial licence for any organization with 200+ employees using `defaults`-channel packages — this threshold now includes non-human agents, automated processes, and serverless systems, not just human users. If Axiom's Conda mirror backend defaults to pointing at `repo.anaconda.com/pkgs/main` or `repo.anaconda.com/pkgs/r`, every Axiom customer deploying the Conda backend into a commercial environment is silently exposed to a licence violation they may not notice.

**Why it happens:**
Conda's default channel configuration points to `defaults` (which is an alias for Anaconda's commercial repository) unless explicitly overridden. Developers testing locally with Miniconda/Miniforge assume all conda channels are free. The distinction between `defaults` and `conda-forge` is subtle and poorly documented in the conda documentation itself.

**How to avoid:**
- Axiom's Conda mirror backend must **default to `conda-forge` only**, never `defaults`. Ship with a hardcoded `.condarc`:
  ```yaml
  channels:
    - conda-forge
  channel_priority: strict
  ```
- Display a **prominent warning** in the Admin UI when a user adds a Conda source that includes `defaults`, `main`, `r`, or `msys2` (all Anaconda commercial channels).
- Document in `docs/foundry.md` the licensing distinction and recommend Miniforge/Micromamba as the conda distribution for Axiom nodes (both ship without `defaults`).
- Never hardcode `repo.anaconda.com` as a default in compose service environment variables.

**Warning signs:**
- Conda backend compose service uses `CONDA_CHANNELS=defaults` or no channel override.
- Users adding `defaults` to their channel list without a warning in the UI.

**Phase to address:** Phase 2 (Mirror Ecosystem Expansion — Conda backend) — must be addressed at the point of implementation, not after.

---

### Pitfall 6: Blueprint Edit Without Version Tracking Silently Breaks Built Images

**What goes wrong:**
When an operator edits a Blueprint (Image Recipe) after a Node Image has already been built from it, the built image's BOM no longer matches the current Blueprint definition. There's a `mark_base_updated` mechanism for the base OS layer, but no equivalent version counter on Blueprints themselves. An operator edits a runtime blueprint to add a package, saves, and forgets to rebuild. Nodes running the old image execute jobs successfully but without the new package. The operator assumes the deployment succeeded because the Node Image status is still `ACTIVE`.

**Why it happens:**
PUT/PATCH on a Blueprint changes its `definition` JSON in-place. There's no `version` column, no `updated_at` comparison against `PuppetTemplate.last_built_at`, and no signal to downstream Node Images. The existing stale-warning mechanism only fires when `POST /admin/mark-base-updated` is called manually.

**How to avoid:**
- Add `version` (integer, default 1, incremented on every PUT/PATCH) and `updated_at` to the `Blueprint` model.
- When a Blueprint is updated, set `is_stale = True` on all `PuppetTemplate` rows that reference it (via `runtime_blueprint_id` or `network_blueprint_id`).
- The Templates.tsx view already shows a stale-warning badge for base OS changes — extend the same badge logic to fire when `blueprint.updated_at > template.last_built_at`.
- Add a migration: `ALTER TABLE blueprints ADD COLUMN version INTEGER DEFAULT 1; ALTER TABLE blueprints ADD COLUMN updated_at TIMESTAMP;`

**Warning signs:**
- Operator reports "I added a package to the recipe but the node doesn't have it" after a successful rebuild.
- `last_built_at` is newer than `blueprint.updated_at` on a template, but the template's definition was changed post-build without a migration having updated `updated_at`.

**Phase to address:** Phase 3 (Foundry CRUD Completeness — Blueprint Edit).

---

### Pitfall 7: Concurrent Blueprint Edit Corrupts JSON Definition

**What goes wrong:**
Two operator browser sessions both load a Blueprint, make different edits, and PUT concurrently. The second PUT overwrites the first silently — no conflict detection, no version check. This is a last-writer-wins race, and the losing operator has no indication their change was lost. The BOM for all downstream images is now based on a partially merged (or fully overwritten) definition.

**Why it happens:**
The current architecture has no optimistic locking (`version_id_col` or ETag-based comparison) on Blueprint PUT. FastAPI + async SQLAlchemy doesn't add this automatically.

**How to avoid:**
- Add `version` to `BlueprintCreate` / `BlueprintUpdate` models. On PUT, include a `WHERE version = <submitted_version>` guard in the UPDATE:
  ```python
  if blueprint.version != req.version:
      raise HTTPException(status_code=409, detail="Blueprint was modified by another user")
  blueprint.version += 1
  ```
- Return the new `version` in every GET/PUT response so the frontend always works with the current value.
- The frontend edit modal must read and submit the `version` field — treat 409 as "reload and re-apply changes."

**Warning signs:**
- No `version` column on `blueprints` table.
- Blueprint PUT does not check the incoming version against the DB row.

**Phase to address:** Phase 3 (Foundry CRUD Completeness) — must be built in from the first Blueprint edit implementation, not patched after.

---

### Pitfall 8: AST Import Extraction Misclassifies Stdlib Modules as Missing Dependencies

**What goes wrong:**
The Script Analyzer walks Python AST `Import` and `ImportFrom` nodes to extract package requirements. It compares import names against a known third-party list. `os`, `sys`, `json`, `re`, `datetime`, `pathlib`, `typing` are all standard library but have names that could be confused with similarly-named third-party packages (e.g. `email`, `statistics`, `calendar`, `decimal` exist on PyPI as third-party packages too). The analyzer recommends installing them, causing noise. More critically, packages like `PIL` (import name) map to `Pillow` (PyPI name), `cv2` → `opencv-python`, `sklearn` → `scikit-learn` — the import name is not the PyPI package name. The analyzer misses these entirely unless it has an explicit alias map.

**Why it happens:**
Python's import namespace is flat and there is no machine-readable stdlib list. `sys.stdlib_module_names` (Python 3.10+) gives the authoritative list, but it's version-specific. Import-name-to-PyPI-name mapping is maintained manually by tools like `pipreqs` and `importlib-metadata` — there is no authoritative canonical source.

**How to avoid:**
- Use `sys.stdlib_module_names` (available Python 3.10+) as the authoritative stdlib exclusion list inside the analyzer. Fall back to a hardcoded set for older runtimes.
- Ship a bundled `import_to_pypi_mapping.json` covering the most common mismatches: `PIL→Pillow`, `cv2→opencv-python`, `sklearn→scikit-learn`, `bs4→beautifulsoup4`, `yaml→PyYAML`, `dateutil→python-dateutil`, `dotenv→python-dotenv`, `Crypto→pycryptodome`, `serial→pyserial`, `wx→wxPython`. Acknowledge this map is **incomplete** — surface the raw import name alongside any mapped name so the operator can verify.
- Frame the Script Analyzer output as **suggestions, not requirements**. Mark unmapped third-party imports as "unrecognized — verify manually" rather than silently omitting them or confidently recommending installation.
- Never block job submission based on script analyzer output alone — it's advisory, not authoritative.

**Warning signs:**
- Analyzer output recommends installing `typing`, `os`, or `json`.
- Analyzer output misses `PIL`, `cv2`, or `yaml` imports entirely.
- Operator feedback: "It says I need X but I already have it / It didn't catch Y."

**Phase to address:** Phase 4 (Script Analyzer) — the import mapper must be built with explicit handling of stdlib exclusion and alias mapping from day one, not added after complaints.

---

### Pitfall 9: Multi-Ecosystem Compose Service Sprawl Breaks Cold-Start

**What goes wrong:**
Adding 6 new sidecar services (APT mirror, apk mirror, npm Verdaccio, Conda mirror, NuGet BaGet, OCI registry passthrough) to `compose.server.yaml` increases cold-start time and creates port collision risks. More critically: the existing cold-start validation script (`provision_coldstart_lxc.py`) will fail because none of the new services have health checks defined, and the cold-start stack's dependency chain is broken. Operators who were deploying a 6-service compose stack now have a 12-service stack where any one failing service blocks the whole bring-up.

**Why it happens:**
New backends are added one-by-one per phase without a compose topology review. Each developer adds their service independently without checking existing port allocations or cold-start dependency ordering. The cold-start compose file is a copy of the server compose file — it inherits all new services by default.

**How to avoid:**
- Define a **mirror services profile** in compose.server.yaml: `profiles: [mirrors]`. Operators who don't need a full mirror stack opt in explicitly rather than getting all services by default.
- Before each new backend is added, run `docker compose config` and validate port assignments in code review.
- Each new mirror sidecar must have a `healthcheck` and be listed as a soft dependency (`condition: service_healthy`) of the agent only if the agent actually calls it on startup (which it doesn't — mirrors are lazy).
- The cold-start compose file should reference only core services; mirror services should require a separate `--profile mirrors` flag.
- Document the port allocation table in `ARCHITECTURE.md` and treat port collisions as a blocking review issue.

**Warning signs:**
- `compose.server.yaml` grows beyond 15 services without a profile separation.
- Port 5000 (OCI registry) conflicts with existing registry service.
- New services added without `healthcheck` blocks.
- Cold-start provisioner script times out waiting for services that aren't needed for the baseline test.

**Phase to address:** Phase 2 (Mirror Ecosystem Expansion) — establish the compose profile pattern before the first new backend is added.

---

### Pitfall 10: NuGet Mirror Silently Falls Back to nuget.org When Offline

**What goes wrong:**
NuGet's `nuget.config` supports multiple `packageSources`. When the local mirror source doesn't have a package, NuGet falls back to any other listed source — including `nuget.org` — silently. In an air-gapped environment, this fallback produces a timeout rather than a clean "package not found in mirror" error. The dotnet layer of a Foundry build hangs for 30-120 seconds before failing, with an error that looks like a network issue rather than a mirror completeness issue.

**Why it happens:**
NuGet's offline behaviour was historically unreliable (documented in GitHub issue NuGet/Home#2623). NuGet doesn't distinguish "mirror is intentionally the only source" from "mirror is one of many sources." Unless `PackageSourceMapping` is explicitly configured to pin packages to the local source, it probes all sources.

**How to avoid:**
- Inject a `nuget.config` into NuGet-targeting Foundry builds that uses `packageSourceMapping` to route all packages to the local BaGet mirror:
  ```xml
  <packageSourceMapping>
    <packageSource key="local-baget">
      <package pattern="*" />
    </packageSource>
  </packageSourceMapping>
  ```
- Set `<add key="nuget.org" value="https://api.nuget.org/v3/index.json" protocolVersion="3" />` to disabled unless the operator explicitly enables online fallback.
- Add a smoke test: attempt `dotnet restore` with `--no-cache --source http://baget:5555/v3/index.json` and confirm it either succeeds or fails with "package not found" (not a timeout).

**Warning signs:**
- NuGet build layer timing out rather than failing fast.
- `nuget.config` in the generated Dockerfile does not include `packageSourceMapping`.
- BaGet sidecar has zero request logs but the build still reports success (means it fell through to nuget.org).

**Phase to address:** Phase 2 (Mirror Ecosystem Expansion — NuGet backend).

---

## Technical Debt Patterns

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| Single PYPI_PATH for all OS families | Simple implementation | manylinux wheels served to Alpine nodes cause silent runtime failures | Never — split the path at Phase 1 start |
| Reuse Foundry build semaphore for dep-resolution | No new semaphore to manage | Dep-resolution starves Foundry builds and vice versa | Never — they're independent workloads |
| `--no-deps` with transitive-resolution flag deferred | BOM looks complete | Full dep-tree missing from mirror; STRICT mode breaks | Never — transitive is the core feature |
| Skip `version` column on Blueprint at first | Faster implementation | Lost edits, stale images, no diff capability | Never — version is required for safe edit UX |
| Conda backend ships with `defaults` channel as option | Users can access full conda ecosystem | Commercial licence liability for every enterprise customer | Never — default must be `conda-forge` |
| Add all mirror services unconditionally to compose | Simple topology | Cold-start time doubles; port collisions; operators who don't need mirrors pay the cost | Acceptable only behind `--profile mirrors` |
| AST analyzer recommends based on raw import names only | Fast to implement | False positives on stdlib; missed aliased packages; operator trust eroded | Acceptable for v1 if clearly labelled "advisory suggestions" |

---

## Integration Gotchas

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|------------------|
| `pip download` + mirror pypiserver | Using `--no-deps` everywhere | Drop `--no-deps` for mirror population; keep `--no-deps` only for CVE scanning of a specific wheel |
| `pip download --platform` | Using only `manylinux2014_x86_64` | Use platform-appropriate tag per OS family: `manylinux2014_x86_64` for glibc, `musllinux_1_1_x86_64` for Alpine |
| Conda channel configuration | Pointing at `defaults` / `repo.anaconda.com` | Always default to `conda-forge`; warn explicitly when user configures `defaults` |
| NuGet BaGet sidecar | Omitting `packageSourceMapping` in injected nuget.config | Pin all packages to local source with `pattern="*"` mapping |
| Docker socket sharing | Assuming Foundry semaphore covers all Docker operations | Single shared semaphore or run dep-resolution in-process (no container) |
| Blueprint PUT endpoint | No version check in UPDATE | `WHERE version = :submitted_version` with HTTP 409 on mismatch |
| npm Verdaccio in air-gap | Expecting Verdaccio to pre-mirror everything at startup | Verdaccio is a proxy — populate by running `npm pack <pkg>` and pushing to the registry before entering air-gap mode |
| APT `apt-mirror` vs `apt-cacher-ng` | Using `apt-mirror` (full mirror = 250+ GB) | Use `apt-cacher-ng` for selective caching; or `aptly` for curated subset mirrors |

---

## Performance Traps

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|----------------|
| Resolving full dep-tree synchronously in the request handler | `/api/smelter/ingredients` POST takes 30-90s | Always background transitive resolution; return `PENDING` status immediately | First package with a deep dep-tree |
| No visited-set in recursive dep download | Worker spins indefinitely on circular deps | Maintain `set()` of resolved `name==version` pairs per resolution job | First circular dep encountered (e.g. `pytest` ecosystem) |
| All mirror backends writing to the same Docker volume | I/O contention; writes serialise at filesystem level | Separate named volumes per ecosystem: `mirror-pypi`, `mirror-apt`, `mirror-npm`, etc. | When more than 2 backends sync concurrently |
| Script Analyzer running full AST parse synchronously on large scripts | UI blocks on submit | Run analyzer in `asyncio.to_thread`; cache results keyed by script content hash | Scripts > ~5000 lines |
| Dep-tree viewer fetching all transitive nodes in one DB query | Nodes page loads slowly when a package has 50+ transitive deps | Lazy-load sub-trees on expand; limit initial tree depth to 2 | Any package in scipy/numpy ecosystem |

---

## Security Mistakes

| Mistake | Risk | Prevention |
|---------|------|------------|
| Injecting arbitrary user-supplied package names into `pip download` subprocess args | Command injection (e.g. `name = "requests; rm -rf /"`) | Validate package name against `^[a-zA-Z0-9_\-\.]+$` before using in subprocess args; use `shlex.quote` |
| Serving mirrored packages over plain HTTP without checksum verification | MITM package substitution inside the LAN | pypiserver serves its own index — add `--hash-algo sha256` to the pypiserver command; verify hash in post-mirror smoke test |
| Conda backend accepting `file://` channel URLs | Path traversal to arbitrary host filesystem | Validate Conda channel URLs against an allowlist of protocols (`https://`, `http://localhost`) |
| Script Analyzer results cached without HMAC integrity | Cached "safe" result swapped for "missing deps" result | Apply the same `HMAC-SHA256 integrity on signature_payload` pattern already used for sig payloads (from v12.0 SEC-02) |
| NuGet BaGet sidecar exposed on host port without auth | Any LAN host can push malicious packages | Either bind BaGet to `127.0.0.1` only in compose, or enable BaGet's API key auth and store the key in `secrets.env` |

---

## UX Pitfalls

| Pitfall | User Impact | Better Approach |
|---------|-------------|-----------------|
| Showing mirror status as binary MIRRORED/FAILED | Operator can't tell if transitive deps are also mirrored or just the root package | Add `deps_resolved: bool` and `dep_count: int` fields; show "Fully mirrored (12 deps)" vs "Root only" in the badge |
| Script Analyzer showing raw PyPI package names for aliased imports | Operator doesn't recognise `Pillow` as the package for `import PIL` | Show both the import name and the PyPI name: "PIL → Pillow (verify)" |
| Blueprint edit modal with no diff view | Operator can't see what changed since the last build | Show a diff of the JSON definition against `last_built_definition` snapshot stored at build time |
| Curated Bundle apply silently overwriting existing blueprint packages | Operator loses custom packages they added | Merge bundles additively by default; show a conflict list before applying; offer "replace" only as explicit secondary action |
| Dep-tree viewer rendering flat list for deep trees | Operator can't trace which root package pulled in a vulnerable transitive dep | Tree view with expand/collapse per node; highlight nodes with CVE findings in amber/red |

---

## "Looks Done But Isn't" Checklist

- [ ] **Transitive dep resolution:** Verify MIRRORED status means the full dep-tree is available, not just the root wheel. Check `pip install --no-index --find-links /mirror <pkg>` in a network-isolated container succeeds.
- [ ] **Alpine mirror:** Verify the mirrored wheels use `musllinux` tags, not `manylinux`. Run `pip install` inside an Alpine container against the mirror.
- [ ] **STRICT mode air-gap:** Verify a Foundry build with `iptables -I OUTPUT -j DROP` on the agent host still completes successfully for a mirrored blueprint. A "passing" STRICT mode test that can still reach PyPI is not an air-gap test.
- [ ] **Conda backend:** Verify no requests reach `repo.anaconda.com` during normal Conda mirror operation. Confirm `.condarc` defaults to `conda-forge` only.
- [ ] **Blueprint edit:** Verify editing a Blueprint marks all downstream Node Images as stale. Verify concurrent PUT with same version returns 409.
- [ ] **Script Analyzer:** Verify `import os`, `import sys`, `import json` do not appear in the suggested packages list. Verify `import PIL` is correctly mapped to `Pillow`.
- [ ] **Compose sprawl:** Verify `docker compose up` without `--profile mirrors` starts the same number of services as v18.0 (no new mandatory services).
- [ ] **NuGet offline:** Verify `dotnet restore` from the BaGet mirror fails fast (not timeout) when a package is absent from the mirror.

---

## Recovery Strategies

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|----------------|
| Mirror has `--no-deps` roots only; STRICT mode breaks in production | HIGH | Re-trigger mirror for all ingredients with full dep resolution; rebuild all Node Images; validate in air-gap before re-enabling STRICT |
| manylinux wheels served to Alpine nodes | HIGH | Populate musllinux path; rebuild all Alpine Node Images; nodes will pick up rebuilt images on next pull |
| Conda `defaults` channel in production | MEDIUM | Reconfigure to `conda-forge`; flush Conda mirror cache; rebuild affected images; legal review if commercial customer was using defaults channel in violation |
| Blueprint edits lost to last-writer-wins | MEDIUM | Retrieve previous blueprint from audit log (if audit covers foundry:write) or Git history if blueprints are exported; re-apply lost changes |
| Compose sprawl causes cold-start failure | LOW-MEDIUM | Add `profiles: [mirrors]` to new services; cold-start returns to baseline; no data loss |
| Script Analyzer false positives erode trust | LOW | Add explicit stdlib exclusion list and alias map; clear analyzer cache; no data migration needed |

---

## Pitfall-to-Phase Mapping

| Pitfall | Prevention Phase | Verification |
|---------|------------------|--------------|
| `--no-deps` leaves dep-tree incomplete | Phase 1: Transitive Dep Resolution | Air-gap smoke test: `pip install --no-index` succeeds for all MIRRORED ingredients |
| Platform tag mismatch (manylinux vs musllinux) | Phase 1: Transitive Dep Resolution | Confirm Alpine container `pip install` from mirror uses musllinux wheels |
| Circular dep hangs resolution worker | Phase 1: Transitive Dep Resolution | Inject a circular dep test package; verify worker returns FAILED within 120s |
| Docker socket contention | Phase 1 (if containers used) or Phase 2 (scale) | Run 2 concurrent Foundry builds + 3 mirror syncs; confirm no timeouts |
| Conda `defaults` licensing | Phase 2: Mirror Ecosystem Expansion (Conda backend) | Confirm `.condarc` default has only `conda-forge`; confirm UI warning fires for `defaults` |
| Compose service sprawl | Phase 2: Mirror Ecosystem Expansion (first new backend) | `docker compose up` without `--profile mirrors` shows same service count as baseline |
| Blueprint edit without version tracking | Phase 3: Foundry CRUD Completeness | PUT blueprint with stale `version` returns 409; downstream templates show stale badge |
| Concurrent Blueprint edit lost write | Phase 3: Foundry CRUD Completeness | Two concurrent PUTs with same version: only one succeeds, other gets 409 |
| AST stdlib misclassification | Phase 4: Script Analyzer | `import os` / `import sys` absent from analyzer output; `import PIL` maps to `Pillow` |
| NuGet silent fallback to nuget.org | Phase 2: Mirror Ecosystem Expansion (NuGet backend) | BaGet-only `dotnet restore` with `--no-cache` fails fast on missing package (no timeout) |

---

## Sources

- pip documentation: dependency resolution and `--no-deps` behaviour — https://pip.pypa.io/en/stable/topics/dependency-resolution/
- pip documentation: `pip download` command reference — https://pip.pypa.io/en/stable/cli/pip_download/
- PEP 656: musllinux platform tag — https://peps.python.org/pep-0656/
- Python platform compatibility tags — https://packaging.python.org/en/latest/specifications/platform-compatibility-tags/
- Anaconda Terms of Service (2025 update) — https://www.anaconda.com/legal
- Anaconda licensing analysis — https://eracent.com/anaconda-licensing-pitfalls-what-you-need-to-know/
- Miniforge (conda-forge default) — https://www.fabriziomusacchio.com/blog/2025-07-03-miniforge/
- SQLAlchemy optimistic locking (`version_id_col`) — https://docs.sqlalchemy.org/en/20/orm/versioning.html
- NuGet offline behaviour and packageSourceMapping — https://learn.microsoft.com/en-us/nuget/reference/nuget-config-file
- NuGet offline issue tracker (Home#2623) — https://github.com/NuGet/Home/issues/2623
- Docker concurrent builds resource exhaustion — https://github.com/docker/buildx/issues/3006
- pip `resolution-too-deep` issue — https://github.com/pypa/pip/issues/12210
- Deploying Python to air-gapped systems — https://dev.to/borisuu/deploying-python-projects-to-air-gapped-systems-2agm
- Axiom `mirror_service.py` — direct code inspection (current `--no-deps` implementation)
- Axiom `compose.server.yaml` — direct code inspection (current service topology and port allocation)
- Axiom `foundry_service.py` — direct code inspection (build semaphore, template/blueprint fetch pattern)

---
*Pitfalls research for: Axiom v19.0 Foundry Improvements — transitive dep resolution, multi-ecosystem mirrors, script analyzer, Foundry CRUD*
*Researched: 2026-04-01*
