# Feature Research

**Domain:** Package management / image-building platform (Foundry/Smelter pipeline, air-gapped orchestration)
**Researched:** 2026-04-01
**Confidence:** MEDIUM-HIGH
**Milestone:** v19.0 Foundry Improvements

---

## Context

Axiom's Foundry pipeline already ships:
- 5-step wizard: compose Node Images from Image Recipes (runtime + network blueprints)
- Smelter Registry: vetted ingredient catalog, CVE scanning (pip-audit), STRICT/WARNING enforcement
- PyPI mirror (devpi) + APT mirror (apt-cacher-ng) as compose sidecars, air-gapped upload
- Blueprint/Tool create + delete (no edit)
- Approved OS list: create + delete (no edit)
- Smelt-Check post-build validation, JSON BOM, image lifecycle (ACTIVE/DEPRECATED/REVOKED)
- `PATCH /api/capability-matrix/{id}` already exists (Tool Recipe edit backend exists)

This research covers only NEW v19.0 features.

---

## Feature Landscape

### Table Stakes (Users Expect These)

Features users of image-building / package-management platforms expect. Missing these = product feels incomplete or untrustworthy.

| Feature | Why Expected | Complexity | Dependencies on Existing Infrastructure |
|---------|--------------|------------|-----------------------------------------|
| Edit Image Recipe (blueprint) | Any CRUD surface is broken without edit; create+delete only creates orphaned configs | LOW | `POST /api/blueprints` exists; need `PATCH /api/blueprints/{id}` backend + wizard-style modal frontend |
| Edit Tool Recipe (capability-matrix entry) | PATCH endpoint already exists in `foundry_router.py`; UI has no edit button | LOW | Backend done; frontend gap only — add edit modal matching create flow |
| Edit Approved OS entry | Name/family/version of an OS entry must be correctable without delete+recreate | LOW | `POST /api/approved-os` + `DELETE` exist; need `PATCH /api/approved-os/{id}` + inline form |
| Runtime dependency confirmation dialog | Users must confirm which packages get pulled before a build commits; prevents surprise failures mid-build | MEDIUM | Requires calling `validate_blueprint()` in `smelter_service.py` before build; modal shows validated package list |
| Package list for transitive deps visible pre-build | pip's resolver pulls far more than what's listed — operators need to see what will actually be installed | MEDIUM | Depends on transitive resolution backend (see Differentiators) |

**Rationale:** The first three are pure CRUD completeness gaps — the backend patterns exist and all three are LOW complexity. The last two become table stakes once operators have been burned by silent dep surprises or audit failures.

---

### Differentiators (Competitive Advantage)

Features that make Axiom's Foundry pipeline stand apart from "bring your own Dockerfile."

| Feature | Value Proposition | Complexity | Dependencies | User Value | Impl Cost |
|---------|-------------------|------------|-------------|-----------|-----------|
| Transitive dependency resolution + tree viewer | Show the full resolved dep graph before a build, not just direct deps; CVE scan the full tree; operators can make informed approve/reject decisions | HIGH | New `pipdeptree`/`pip-compile` call in `foundry_service.py`; new `POST /api/blueprints/{id}/resolve` endpoint; new DepTree UI component | HIGH | HIGH |
| CVE scanning of transitive deps | pip-audit already scans BOM post-build; scanning transitive deps PRE-build lets operators block before committing image storage | MEDIUM | pip-audit already integrated in `smelter_service.scan_vulnerabilities()`; extend to accept a resolved dep list rather than an installed environment | HIGH | MEDIUM |
| Multi-ecosystem mirror expansion: apk (Alpine) | Alpine-based images cannot use apt-cacher-ng; apk needs a separate proxy (squid+ssl-bump or a custom apk-cacher) | HIGH | New compose sidecar; new `_mirror_apk()` in `mirror_service.py`; Admin mirror-config PATCH already exists | HIGH | HIGH |
| Multi-ecosystem mirror expansion: npm (Verdaccio) | Node.js tools in images (linters, runners) need npm packages; Verdaccio is a proven, Docker-native npm proxy | MEDIUM | New compose sidecar (Verdaccio); new `_mirror_npm()` in `mirror_service.py`; Admin UI mirror toggle | MEDIUM | MEDIUM |
| Multi-ecosystem mirror expansion: Conda | Data science node images require conda/mamba; `conda-mirror` is the standard tool for air-gap | HIGH | New compose sidecar; significant storage footprint; conda repodata is large | HIGH | HIGH |
| Multi-ecosystem mirror expansion: NuGet (BaGet) | PowerShell nodes using `Install-Package` need a NuGet proxy; BaGet is lightweight, Docker-first | MEDIUM | BaGet docker image available; new compose sidecar; `_mirror_nuget()` in `mirror_service.py` | MEDIUM | MEDIUM |
| Multi-ecosystem mirror expansion: OCI pull-through | Node images reference base images from Docker Hub/GHCR; an OCI pull-through cache (e.g., Zot, or Docker's registry:2) reduces external pulls and makes air-gap reliable | HIGH | New compose sidecar; `skopeo sync` for pre-seeding; Foundry needs to know local registry URL | HIGH | HIGH |
| Script Analyzer (auto-detect deps from script) | Operator pastes a script and Foundry detects `import requests`, `apt-get install curl` etc. and suggests needed packages | HIGH | New `POST /api/foundry/analyze-script` endpoint; AST-based parsing for Python (`ast` stdlib), regex for Bash/PowerShell; maps module names to PyPI/apt package names | HIGH | HIGH |
| Curated Bundles (pre-defined package sets) | "Data Science bundle" or "DevOps toolbox" reduces time-to-image for common personas; operators do not need to know package names | MEDIUM | New `Bundle` DB table; CRUD endpoint; Bundle selection step in wizard; seeded with 4-6 vetted bundles | HIGH | MEDIUM |
| Starter Templates (pre-built Node Images) | Seed a few complete templates (Python ML, Bash ops, PowerShell admin) so operators do not start from a blank wizard | LOW | Startup seeder or admin-importable JSON; no new tables needed; builds on existing wizard | HIGH | LOW |
| Plain-language search across recipes/ingredients | Operators search "machine learning" and get Python + numpy/pandas recipes, not a blank results page | MEDIUM | New full-text index or embedding on ingredient descriptions; `GET /api/foundry/search-packages` already exists but is package-name exact | MEDIUM | MEDIUM |
| Simplified naming (human-readable slugs) | Auto-generate display names from OS+packages rather than requiring operators to invent names | LOW | Server-side name suggestion on Blueprint create; pure UX addition, no schema change required | MEDIUM | LOW |
| Role-based Foundry view (operator vs developer) | Operators see Starter Templates + Bundle picker; developers see raw YAML/JSON editor mode | MEDIUM | Feature-flag per role; conditional UI rendering; no backend change | MEDIUM | MEDIUM |

---

### Anti-Features (Commonly Requested, Often Problematic)

| Feature | Why Requested | Why Problematic | Better Approach |
|---------|---------------|-----------------|-----------------|
| Automatic dependency pinning in the UI (lock-file generation) | Operators want "freeze my deps" without understanding implications | Lock files created by the server without context of target platform produce false confidence; pins break on next build when transitive deps conflict | Show the resolved dep list pre-build (tree viewer); let operators review it; do not auto-pin server-side |
| Full conda channel sync (all platforms/versions) | Completeness instinct | A single conda-forge channel sync is 500 GB+; destroys storage and sync time | Offer filtered sync (platform-specific, version-pinned, or allow-list driven) — same pattern used by EKS Anywhere curated packages |
| Real-time dep resolution during wizard typing | Responsive UX seems better | pip resolver is slow (2-10s per call); blocking UX on every keystroke; creates load spikes | Trigger resolution on explicit "Resolve" button click, not on every change |
| Auto-suggest CVE fixes (auto-upgrade transitive deps) | "Fix it for me" appeal | Server has no context about what version constraints the operator actually needs; an "auto-fix" can silently break compatibility | Show CVE + affected version range + recommended version; let operator decide; document why |
| Single unified mirror management UI for all ecosystems simultaneously | Seems simpler | Each ecosystem has fundamentally different sync models (PyPI=Simple API, APT=ftpsync, npm=REST, conda=repodata.json, OCI=content-addressable); forcing one UI creates leaky abstractions | Per-ecosystem tabs with ecosystem-specific controls and status; unified health summary card is fine |
| Script Analyzer as a hard gate (block build if unrecognized imports) | Security instinct | Static analysis for Bash is inherently imprecise; false positives block legitimate builds | Use as a soft suggestion ("these imports were detected — consider adding these packages"); never block |

---

## Feature Dependencies

```
Edit Image Recipe (frontend)
    └──requires──> PATCH /api/blueprints/{id} (backend — not yet built)

Edit Tool Recipe (frontend)
    └──uses──> PATCH /api/capability-matrix/{id} (backend — ALREADY EXISTS)

Edit Approved OS (frontend + backend)
    └──requires──> PATCH /api/approved-os/{id} (backend — not yet built)

Transitive Dependency Resolution (pre-build)
    └──requires──> new POST /api/blueprints/{id}/resolve endpoint
    └──enables──> CVE scan of transitive deps (pre-build)
    └──enables──> Dep Tree viewer in wizard
    └──enables──> Script Analyzer suggestions shown with resolved count

Script Analyzer
    └──requires──> POST /api/foundry/analyze-script (new endpoint)
    └──enhances──> Curated Bundles (can map detected imports to bundles)

Curated Bundles
    └──requires──> Bundle DB table + CRUD (new)
    └──enhances──> Starter Templates (templates can reference bundles)
    └──requires (to be useful)──> Plain-language search

Starter Templates
    └──requires──> Existing wizard + Image Recipe CRUD (already built)
    └──enhances──> Role-based Foundry view (operators land on starter templates)

apk mirror
    └──requires──> Alpine Approved OS entries (already have Approved OS table)
    └──requires──> New compose sidecar (alpine-pkg-cacher or squid)
    └──enables──> Alpine-based Node Images with reliable air-gap

OCI pull-through mirror
    └──requires──> Local OCI registry sidecar (Zot or registry:2)
    └──enables──> base image pulls air-gapped during foundry build

npm mirror (Verdaccio)
    └──requires──> Verdaccio compose sidecar
    └──enables──> Node.js tool installation in images

Conda mirror
    └──requires──> conda-mirror + large storage allocation
    └──conflicts──> storage budget (HIGH cost; defer unless data science is a priority)

NuGet mirror (BaGet)
    └──requires──> BaGet compose sidecar
    └──enables──> PowerShell package install in images
    └──enhances──> existing PowerShell node support

Role-based Foundry view
    └──requires──> Starter Templates (operator path needs something to show)
    └──requires──> Curated Bundles (developer vs operator distinction only useful with bundles)
```

### Dependency Notes

- **Transitive resolution enables CVE pre-build scanning:** The most impactful security improvement in this milestone builds on top of transitive resolution. Build transitive resolution first.
- **Script Analyzer is standalone:** It can be built without transitive resolution (it produces a suggested package list, not a resolved tree). But they compose well.
- **Edit CRUD gaps are independent:** No cross-dependencies between edit-blueprint, edit-tool-recipe, and edit-approved-os. All three can be built in parallel.
- **Mirror sidecars are independent of each other:** npm, apk, Conda, NuGet, OCI can be developed and shipped independently. Each is its own compose service + `_mirror_*()` method.
- **Curated Bundles + Starter Templates are a UX pair:** Bundles define package groups; Starter Templates compose bundles into ready-to-build recipes. Both together achieve the non-developer operator goal.

---

## MVP Definition

This is a subsequent milestone — "MVP" means the minimum slice needed to make this milestone useful to operators, not a product launch.

### Launch With (v19.0 Core)

- [ ] **Edit Image Recipe** — zero friction, existing pattern from create; unblocks operators stuck with wrong blueprint configs
- [ ] **Edit Tool Recipe (UI)** — backend already exists; purely frontend; quick win
- [ ] **Edit Approved OS** — rounds out Foundry CRUD completeness
- [ ] **Transitive dependency resolution + tree viewer** — headline feature; pre-build visibility into full dep graph; CVE scan the tree
- [ ] **Curated Bundles** — 4-6 seeded bundles (data-science, devops-bash, powershell-admin, network-ops); Bundle picker in wizard
- [ ] **npm mirror (Verdaccio)** — most broadly applicable new ecosystem; Node.js tools common in ops images; low storage footprint vs Conda/OCI

### Add After Validation (v19.x)

- [ ] **Script Analyzer** — high value but HIGH complexity for Bash/PowerShell parsing accuracy; add after core CRUD ships
- [ ] **OCI pull-through mirror** — high value for air-gap completeness; HIGH complexity; add when base pipeline is stable
- [ ] **NuGet mirror (BaGet)** — needed for PowerShell-heavy shops; MEDIUM complexity; add alongside OCI mirror work
- [ ] **Starter Templates (seeded)** — LOW complexity; add after bundles validated; operators need bundles first to make templates useful
- [ ] **apk mirror** — needed for Alpine images; HIGH complexity (ssl-bump or custom cacher); add when Alpine OS family adoption is confirmed
- [ ] **Role-based Foundry view** — low backend cost, MEDIUM frontend; add after bundles + starter templates are present

### Future Consideration (v20+)

- [ ] **Conda mirror** — HIGH storage/complexity; only if data science becomes an explicit ICP segment
- [ ] **Plain-language semantic search** — requires embedding infrastructure or search index; defer until package catalog grows large enough to need it
- [ ] **Simplified auto-naming** — minor UX polish; not urgent

---

## Feature Prioritization Matrix

| Feature | User Value | Implementation Cost | Priority | Existing Infrastructure |
|---------|------------|---------------------|----------|------------------------|
| Edit Image Recipe (blueprint) | HIGH | LOW | P1 | POST/DELETE exists; need PATCH backend + modal |
| Edit Tool Recipe (UI only) | HIGH | LOW | P1 | PATCH backend already exists |
| Edit Approved OS | MEDIUM | LOW | P1 | POST/DELETE exists; need PATCH + inline form |
| Transitive dep resolution + tree viewer | HIGH | HIGH | P1 | pip-audit + pipdeptree available; new endpoint needed |
| CVE scan transitive deps (pre-build) | HIGH | MEDIUM | P1 | pip-audit integration exists; extend to pre-build list |
| Runtime dep confirmation dialog | HIGH | MEDIUM | P1 | `validate_blueprint()` exists in smelter_service; wrap in modal |
| Curated Bundles | HIGH | MEDIUM | P1 | New Bundle table; no prior infrastructure |
| npm mirror (Verdaccio) | MEDIUM | MEDIUM | P2 | mirror_service + Admin UI pattern established |
| Script Analyzer | HIGH | HIGH | P2 | New endpoint; AST parsing stdlib available |
| NuGet mirror (BaGet) | MEDIUM | MEDIUM | P2 | Same pattern as npm mirror |
| Starter Templates (seeded) | HIGH | LOW | P2 | Wizard + template CRUD already built |
| OCI pull-through mirror | HIGH | HIGH | P2 | skopeo available; new registry sidecar needed |
| apk mirror | MEDIUM | HIGH | P3 | No prior infrastructure for Alpine pkg caching |
| Role-based Foundry view | MEDIUM | MEDIUM | P3 | Feature-flag pattern used elsewhere in app |
| Plain-language search | MEDIUM | HIGH | P3 | search-packages endpoint exists; needs semantic layer |
| Simplified auto-naming | LOW | LOW | P3 | Pure UX sugar |
| Conda mirror | MEDIUM | HIGH | P3 | High storage; LOW operator demand unless data science ICP |

**Priority key:**
- P1: Core of v19.0 — Foundry CRUD completeness + transitive resolution + bundles
- P2: High-value additions — new ecosystems + script analyzer + starter templates
- P3: Future enhancements — defer to v20+

---

## Competitor Feature Analysis

Reference platforms: Posit Package Manager, JFrog Artifactory, Nexus Repository, Pulp (Foreman/Katello).

| Feature | Posit Package Manager | JFrog Artifactory | Nexus Repository | Axiom Approach |
|---------|----------------------|-------------------|-----------------|----------------|
| Transitive dep resolution | YES — full tree view with CVE overlay | YES — Xray scans full dep graph | YES — via IQ Server | Build into pre-build wizard step; operator must confirm tree |
| Multi-ecosystem mirroring | PyPI + CRAN + Conda | All major ecosystems | All major ecosystems | Incremental: PyPI+APT today; add npm+NuGet+OCI+apk; skip Conda unless demanded |
| Curated repos / allow-lists | YES — "curated PyPI" feature | YES — include/exclude rules | YES — route rules | Curated Bundles as a simpler mental model; allow-list already in Smelter Registry |
| Script analysis / import detection | NO | NO | NO | Differentiator — no competitor does this in the image build flow |
| Air-gap first design | Partial (offline mode) | Complex setup | Complex setup | Native design constraint; mirrors + BUILD in same compose stack |
| RBAC on mirror management | YES | YES (complex) | YES (complex) | Already have role-gated Admin config; extend to mirror tabs |

**Key differentiation opportunity:** Script Analyzer (detect deps from script text) is not offered by any major competitor in the image-build workflow. If Axiom ships this well, it becomes a genuine differentiator for operators who are not packaging experts.

---

## Sources

- [pip dependency resolution — official pip docs](https://pip.pypa.io/en/stable/topics/dependency-resolution/)
- [pip-audit — PyPA official auditing tool](https://pypi.org/project/pip-audit/)
- [pipdeptree — dependency tree visualization](https://pypi.org/project/pipdeptree/)
- [Package Manager Mirroring landscape (2026)](https://nesbitt.io/2026/03/20/package-manager-mirroring.html)
- [The Package Management Landscape (2026)](https://nesbitt.io/2026/01/03/the-package-management-landscape.html)
- [Verdaccio — npm local registry proxy](https://www.verdaccio.org/)
- [conda-mirror — mirror upstream conda channels](https://pypi.org/project/conda-mirror/)
- [Skopeo — OCI image sync for air-gap](https://developers.redhat.com/articles/2025/09/24/skopeo-unsung-hero-linux-container-tools)
- [FawltyDeps — import/dep mismatch detection](https://github.com/tweag/FawltyDeps)
- [Posit Package Manager — curated PyPI repos](https://posit.co/blog/posit-package-manager-2023-04-0/)
- [EKS Anywhere Curated Packages pattern](https://anywhere.eks.amazonaws.com/docs/packages/)
- Existing codebase: `ee/routers/foundry_router.py`, `services/smelter_service.py`, `services/mirror_service.py`

---

*Feature research for: Axiom v19.0 Foundry Improvements*
*Researched: 2026-04-01*
