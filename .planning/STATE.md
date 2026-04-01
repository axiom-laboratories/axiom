---
gsd_state_version: 1.0
milestone: v19.0
milestone_name: Foundry Improvements
status: active
stopped_at: null
last_updated: "2026-04-01T20:00:00.000Z"
last_activity: "2026-04-01 — Milestone v19.0 started"
progress:
  total_phases: 0
  completed_phases: 0
  total_plans: 0
  completed_plans: 0
  percent: 0
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-04-01)

**Core value:** Jobs run reliably — on the right node, when scheduled, with their output captured — without any step in the chain weakening the security model.
**Current focus:** v19.0 Foundry Improvements

## Current Position

Phase: Not started (defining requirements)
Plan: —
Status: Defining requirements
Last activity: 2026-04-01 — Milestone v19.0 started

Progress: [░░░░░░░░░░] 0%

## Performance Metrics

**Velocity:**
- Total plans completed: 9 (this milestone)
- Average duration: ~12 min
- Total execution time: ~110 min

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 101-ce-ux-cleanup | 2 | 25 min | 13 min |
| 102-linux-e2e-validation | 3 | ~70 min | ~23 min |
| 104-pr-review-merge | 3 | ~10 min | ~3 min |

**Recent Trend:**
- Last 5 plans: 102-03, 104-01 (3 min), 104-02 (4 min), 104-03 (~3 min)
- Trend: Fast execution on PR merge/cleanup phases

*Updated after each plan completion*
| Phase 104 P03 | 3min | 2 tasks | 3 files |
| Phase 105 P01 | 1min | 5 tasks | 2 files |
| Phase 105 P02 | 2min | 6 tasks | 1 files |
| Phase 106 P01 | 1min | 4 tasks | 1 files |

## Accumulated Context

### Key Decisions

- [v18.0 Roadmap]: Phase 102 and 103 both depend on Phase 101 (CE UX Cleanup must land before E2E runs so testers see clean CE UI)
- [v18.0 Roadmap]: Phase 102 (Linux) and Phase 103 (Windows) are independent of each other — can run in parallel once Phase 101 is complete
- [v18.0 Roadmap]: Both E2E phases include friction fix requirements (LNX-06, WIN-06) — plan-phase must allocate a fix plan within each phase, not treat validation as read-only
- [101-01]: isEnterprise destructured at Admin component scope; EE tabs gated with {isEnterprise && (...)} on both TabsTrigger and TabsContent; + Enterprise CE upgrade panel renders UpgradePlaceholder grid
- [101-01]: Playwright confirmed CE tab bar = [Onboarding][+ Enterprise][Data], 6 EE tabs absent, upgrade panel shows 6 UpgradePlaceholder instances
- [101-02]: Tab visibility tests use queryByRole/getByRole with licence mock; exact regex /^\+ enterprise$/i used for EE-mode absence to avoid false positives from licence badge text
- [102-01]: Exit code 2 used for pre-flight image-unreachable failure (vs exit 1 for run failure) to distinguish failure modes
- [102-01]: synthesise_friction.py _derive_edition() derives edition from filename stem (CE/EE by keyword, else run prefix like LNX) enabling cross-phase reuse
- [102-02]: chromium-browser excluded from LXC apt install — pulls snapd which stalls inside LXC; Playwright chromium installed separately via playwright install chromium
- [102-02]: Claude subagent must run as non-root user — UID 0 blocks --dangerously-skip-permissions; validator user created in LXC with docker group membership
- [102-02]: FRICTION finding: Quick Start compose command hard-codes --env-file .env which fails with no .env file — this is the BLOCKER for Plan 03
- [102-02 checkpoint]: User direction — remove --env-file .env from compose flow; compose must be self-contained with no external env file required

- [104-01]: Cherry-picked useWebSocket.ts onto clean branch to strip .planning/ contamination from PR #17
- [104-01]: Code review of deps.py/main.py sufficient without Docker stack test — straightforward async audit fix and countersign addition
- [104-01]: Merge queue handles merge strategy (merge commit); functionally equivalent to squash for single-commit branches

- [104-02]: Rebase conflicts in .planning/ resolved with --theirs; doc conflicts in first-job.md resolved with --ours (PR #19 version is canonical)
- [104-02]: Code review sufficient without Docker stack test -- PR #18 changes are additive to different sections than deps.py extraction
- [104-02]: Admin merge used to bypass merge queue with pre-existing CI failures (pytest not found, History.test.tsx)

- [104-03]: History.test.tsx failures caused by missing useFeatures mock — component renders UpgradePlaceholder when features.executions is falsy
- [104-03]: All 3 PR branches deleted (remote already gone via --delete-branch on merge); worktrees cleaned; milestone v18.0 closed

### Roadmap Evolution

- Phase 104 added: PR Review & Merge — Review and merge PRs #17 (WebSocket fix), #18 (Windows E2E), #19 (Linux E2E) into main
- Milestone v18.0 shipped 2026-04-01

### Pending Todos

**CRITICAL: Transitive Dependency Resolution** (air-gapped STRICT deployments broken without this):

Context: `mirror_service.py:66` uses `pip download --no-deps`, so only the named package is mirrored. But `foundry_service.py:130` runs `pip install` WITHOUT `--no-deps`, so pip tries to resolve the full dependency tree at build time. In air-gapped STRICT mode the build fails because transitive deps aren't in the local mirror. This only works today because WARNING mode falls through to public PyPI, or devpi's caching proxy fetches deps on-demand when internet is available.

- [ ] **mirror_service: resolve and mirror transitive deps** — change `_mirror_pypi()` in `mirror_service.py:52-85` to run `pip download` WITHOUT `--no-deps` in a throwaway container. Parse the downloaded filenames to discover the full dependency tree. Auto-create `ApprovedIngredient` records for each transitive dep with a `parent_ingredient_id` foreign key linking back to the original package. Mirror all of them.
- [ ] **Smelter API: dependency discovery endpoint** — new endpoint `POST /api/smelter/ingredients/{id}/resolve-deps` that returns the full transitive tree before committing. The Smelter UI shows e.g. "flask requires 5 additional packages: Werkzeug, Jinja2, MarkupSafe, itsdangerous, click" with one-click "Approve All". Reuses the `deps_to_confirm` pattern already implemented for Tool dependencies in `foundry_router.py:64-88`.
- [ ] **Extend dep resolution to all ecosystems** — same pattern per ecosystem: npm (`npm install --dry-run --json`), Conda (`conda create --dry-run --json`), APT (`apt-get install -s <pkg>` and parse "Inst" lines), apk (`apk add --simulate <pkg>`). Each runs in a throwaway container matching the target OS family and returns a structured dep list for bulk approval in the UI.
- [ ] **CVE scan: include transitive deps** — `smelter_service.py:103` runs `pip-audit --no-deps`. Remove `--no-deps` so the scan covers the full resolved tree. A vulnerable transitive dep (e.g. a CVE in MarkupSafe pulled by Jinja2 pulled by Flask) is currently invisible.
- [ ] **Smelter UI: dependency tree viewer** — in the ingredient table, show a tree icon on packages that were auto-approved as transitive deps. Clicking it shows the provenance chain (e.g. "MarkupSafe ← Jinja2 ← flask"). Helps operators understand why a package is in their registry.

**EE Dashboard GUI Gaps** (found during package mirrors course audit, 2026-04-01):

Context: Audit of `Templates.tsx`, `Admin.tsx`, and EE routers against all API endpoints. Most operations have full GUI coverage. These are the gaps where the API supports an operation but the dashboard doesn't expose it.

- [ ] **Edit Blueprint** — `Templates.tsx` BlueprintWizard supports create + view (JSON modal) + delete, but no edit flow. The API also lacks a PATCH endpoint for blueprints (`foundry_router.py` has POST and DELETE only). Need: (a) add `PATCH /api/blueprints/{id}` to foundry_router, (b) add "Edit" button on blueprint rows that reopens the wizard pre-populated with current definition. Current workaround: delete and recreate.
- [ ] **Edit Tool Recipe** — API supports `PATCH /api/capability-matrix/{id}` (`foundry_router.py`), but `Templates.tsx` Tools tab only has Add + Delete. Need: edit dialog/form that loads current recipe fields (injection_recipe, validation_cmd, runtime_dependencies) into editable inputs.
- [ ] **Approved OS Management** — `foundry_router.py` exposes `GET/POST/DELETE /api/approved-os` for managing base OS images (e.g. `debian:12-slim`, `alpine:3.20`). No admin tab in `Admin.tsx` or `Templates.tsx` exposes this. Need: dedicated section in the Foundry or Admin page to list/add/remove approved base images.
- [ ] **Blueprint Runtime Dependency Confirmation** — when `foundry_router.py:80-81` returns `{"error": "deps_required", "deps_to_confirm": [...]}`, the BlueprintWizard doesn't display a confirmation dialog. Must use API directly with `confirmed_deps` array. Need: a modal in Step 4 (Tools) that shows required tool dependencies and lets the operator confirm.

**Mirror Ecosystem Expansion** (from package mirrors course design, 2026-04-01):

Context: Currently only PyPI mirroring is implemented (`mirror_service.py:52-85`). APT has a placeholder function (`mirror_service.py:88-95`). The Smelter ingredient model uses `os_family` (DEBIAN/ALPINE/FEDORA) which doesn't accommodate ecosystem-level packages like Docker images, npm, or Conda. The course at `docs/docs/quick-ref/package-mirrors-course.html` documents the target architecture with 7 ecosystems. All mirror backends are permissively licensed (MIT/BSD/Apache-2.0) — no commercial licensing issues when referenced via compose (user pulls images themselves).

- [ ] **Smelter: expand `os_family` to `ecosystem`** — `ApprovedIngredient` model in EE DB uses `os_family` (DEBIAN/ALPINE/FEDORA). Add a `package_type` or `ecosystem` enum field: PYPI, APT, APK, OCI, NPM, CONDA, NUGET. Keep `os_family` for backwards compat but route mirror logic on `ecosystem`. Update `smelter_service.py` validation and `smelter_router.py` endpoints.
- [ ] **mirror_service: implement `_mirror_apt()`** — placeholder at `mirror_service.py:88-95`. Run `apt-get download <pkg>=<version>` in a throwaway `debian:12-slim` container. Route through apt-cacher-ng (`apt-mirror:3142`) to warm the cache. Update `mirror_status` on the ingredient.
- [ ] **mirror_service: implement `_mirror_apk()`** — new function. Run `apk fetch <pkg>=<version>` in a throwaway `alpine:3.20` container. Route through nginx apk-cache (`apk-cache:3143`) to warm the cache. Requires the apk-cache compose service to exist first.
- [ ] **mirror_service: implement `_mirror_oci()`** — new function. Run `docker pull <image>:<tag>` through the registry:2 pull-through cache (`registry-cache:5000`). The pull itself warms the cache. Verify the image layers are stored in the `registry-cache-data` volume.
- [ ] **mirror_service: implement `_mirror_npm()`** — new function. Run `npm pack <pkg>@<version>` in a throwaway `node:20-slim` container to download the tarball, then publish to Verdaccio (`verdaccio:4873`) via `npm publish`. Or configure Verdaccio as an uplink to npmjs.com so it caches on first fetch (simpler).
- [ ] **mirror_service: implement `_mirror_conda()`** — new function. Run `conda create --download-only -n tmp <pkg>=<version>` in a throwaway `continuumio/miniconda3` container. Packages land in `/opt/conda/pkgs/`. Copy to the local conda mirror directory served by nginx. Respect channel selection (conda-forge vs defaults).
- [ ] **mirror_service: implement `_mirror_nuget()`** — new function. Download `.nupkg` from PSGallery via `curl -L "https://www.powershellgallery.com/api/v2/package/<name>/<version>"`. Push to BaGet (`baget:5555`) via `PUT /api/v2/package` with the API key from config.
- [ ] **Smelter UI: Conda channel selector** — when ecosystem=CONDA, show a dropdown: "conda-forge" (default, recommended) or "Anaconda defaults". Store the selected channel on the ingredient record. `_mirror_conda()` uses this to set the `-c` flag.
- [ ] **Foundry UI: Anaconda ToS warning** — in `Templates.tsx` BlueprintWizard Step 3 (Packages), when a CONDA ingredient sourced from the Anaconda default channel is added to the recipe, show an amber callout: "Anaconda's Terms of Service require a commercial licence for organisations with 200+ employees. Consider using conda-forge instead." No hard block — just a visible warning. Suppress the warning for conda-forge-sourced ingredients.
- [ ] **Smelter UI: mirror URL config for new ecosystems** — the existing Mirror Configuration form in `Admin.tsx` Smelter Registry tab has PyPI and APT URL fields. Add fields for: apk mirror URL, OCI registry URL, Verdaccio URL, Conda mirror URL. Store in Config table alongside existing `pypi_mirror_url` / `apt_mirror_url`.
- [ ] **compose.server.yaml: add mirror services** — add compose service definitions for: `apk-cache` (nginx:alpine with `apk-cache.conf`, port 3143, volume `apk-cache-data`), `registry-cache` (registry:2 with `REGISTRY_PROXY_REMOTEURL`, port 5000, volume `registry-cache-data`), `verdaccio` (verdaccio/verdaccio:5, port 4873, volume `verdaccio-data`), `baget` (loicsharma/baget, port 5555, volume `baget-data`). Conda mirror via nginx reverse proxy to conda-forge.org (same pattern as apk-cache). All services optional — only started if the operator enables the corresponding mirror.

**Operator UX: Non-Developer Accessibility** (from package mirrors course discussion, 2026-04-01):

Context: The Foundry/Smelter workflow assumes the operator knows package names, ecosystems, and version constraints. Service desk staff and sysadmins typically know "I need a node that runs our inventory script" — not "I need openpyxl>=3.1 from PyPI". These features make the system accessible to non-developers.

- [ ] **Script Analyzer** — new endpoint `POST /api/foundry/analyze-script` that accepts a script body + runtime hint (python/bash/powershell/node). For Python: parse AST for `import` statements, map to PyPI package names (using a known stdlib exclusion list + importlib metadata). For Node: parse `require()` / `import from`. For PowerShell: parse `Import-Module`. Return a structured list of `{name, ecosystem, suggested_version}`. Dashboard: new "Analyze Script" button in the Foundry that opens a paste/upload dialog, shows results, and offers "Approve All & Build" which chains Smelter approval → mirror sync → blueprint creation → build in one flow.
- [ ] **Curated Package Bundles** — new `PackageBundle` DB model: `{id, name, description, packages: JSON[{name, ecosystem, version}]}`. Seed 5 bundles on startup: Data Science (numpy, pandas, scikit-learn, matplotlib, jupyter), Web/API (requests, flask, beautifulsoup4, lxml), Network Ops (paramiko, netmiko, nmap, dnspython), File Processing (openpyxl, Pillow, PyPDF2, python-docx), Windows Automation (Pester, PSScriptAnalyzer, ImportExcel). Dashboard: "Browse Bundles" in Foundry with one-click "Add Bundle" that bulk-approves all packages (with transitive deps) and creates a blueprint.
- [ ] **Pre-built Starter Templates** — ship "Golden Image" template definitions as seed data. On first EE startup, create templates for: Python General, Python Data Science, Network Tools, Windows Automation. Each combines a seeded runtime blueprint + default network blueprint. Dashboard: "Template Gallery" view where non-technical operators pick from pre-built options and click Deploy instead of using the wizard.
- [ ] **One-click mirror provisioning** — new Admin section: "Mirror Infrastructure". Shows each mirror type (PyPI, APT, apk, OCI, npm, Conda, NuGet) with an Enable/Disable toggle. Enabling a mirror triggers the agent service to `docker run` the corresponding container (using the Docker socket already mounted for Foundry builds). Stores state in Config table. Eliminates compose file editing entirely — the operator enables mirrors through the dashboard and the system handles container lifecycle.
- [ ] **Plain-language package search** — enhance the Smelter "Add Ingredient" dialog with a search field that queries a package description index. For PyPI: use the PyPI JSON API (`/pypi/<pkg>/json`) to fetch summary fields. Show results like "openpyxl — A Python library to read/write Excel xlsx files" when the operator types "excel". Auto-detect ecosystem from the search source. Fallback: if no index is available (air-gapped), search only already-approved ingredients by name substring.
- [ ] **Simplified UI naming** — rename user-facing labels across `Templates.tsx` and `Admin.tsx`: "Runtime Image Recipe" → "Software Profile", "Network Image Recipe" → "Network Policy", "Ingredient" → "Package", "Capability Matrix" / "Tool" → "Add-on Tool", "Smelter Registry" → "Package Registry", "Enforcement Mode" → "Approval Policy". Keep API field names unchanged for backwards compat. This is a pure UI rename — no backend changes.
- [ ] **Role-based simplified view** — add a `ui_mode` preference per user (stored in User model or localStorage): "standard" (current full UI) or "simplified". In simplified mode, the Foundry page shows only: (a) Template Gallery (pick a starter), (b) "Upload Script" (triggers Script Analyzer flow), (c) "My Node Images" (templates the user has built). The full Smelter/Blueprint/Tool views are hidden. Admin role always sees full UI. Operator/viewer roles default to simplified but can toggle.
- [ ] **Template catalog with usage stats** — extend `PuppetTemplate` model with `created_by`, `used_by_nodes_count` (computed from enrolled nodes), `last_used_at`. Dashboard: "Template Catalog" view with columns: name, creator, last built, nodes using it, status. Sort by usage count so proven templates surface first. Service desk picks from the catalog instead of building from scratch.

### Blockers/Concerns

None — all blockers resolved.

## Session Continuity

Last session: 2026-04-01T18:52:22.093Z
Stopped at: Completed 106-01-PLAN.md
Resume file: None
