# Requirements: Axiom v19.0 Foundry Improvements

**Defined:** 2026-04-01
**Core Value:** Jobs run reliably — on the right node, when scheduled, with their output captured — without any step in the chain weakening the security model.

## v19.0 Requirements

Requirements for this milestone. Each maps to roadmap phases.

### Foundry CRUD Completeness

- [ ] **CRUD-01**: Operator can edit an existing Image Recipe (blueprint) via a pre-populated wizard modal, with optimistic locking (version column + 409 on conflict)
- [ ] **CRUD-02**: Operator can edit an existing Tool Recipe via an edit dialog using the existing PATCH endpoint
- [ ] **CRUD-03**: Admin can list, add, edit, and remove Approved OS entries from a dedicated section in the Foundry or Admin page
- [ ] **CRUD-04**: Operator sees a confirmation dialog showing all runtime dependencies before a blueprint build commits

### Dependency Resolution

- [ ] **DEP-01**: Mirror service resolves and downloads full transitive dependency trees (not just top-level packages), with separate paths for manylinux and musllinux wheels
- [ ] **DEP-02**: Operator can view the transitive dependency tree for any ingredient in a visual tree component showing provenance chains
- [ ] **DEP-03**: CVE scanning covers the full transitive dependency tree, not just directly approved ingredients
- [ ] **DEP-04**: Operator can trigger dependency discovery for any ingredient via an endpoint that returns the full tree with one-click "Approve All"

### Mirror Ecosystem Expansion

- [ ] **MIRR-01**: APT mirror backend is fully implemented (complete the existing stub in mirror_service.py)
- [ ] **MIRR-02**: apk (Alpine) mirror backend with nginx-based compose sidecar serves Alpine packages in air-gap
- [ ] **MIRR-03**: npm mirror backend using Verdaccio pull-through proxy with compose sidecar
- [ ] **MIRR-04**: NuGet mirror backend using BaGetter with compose sidecar for PowerShell/NuGet packages
- [ ] **MIRR-05**: OCI pull-through cache using registry:2 so Foundry base image pulls work in air-gap
- [ ] **MIRR-06**: Conda mirror backend with Anaconda ToS warning when operator selects the defaults channel
- [ ] **MIRR-07**: All mirror sidecars defined as compose services with opt-in profiles (not started by default)
- [ ] **MIRR-08**: Admin mirror configuration UI includes URL fields for all new ecosystems (apk, OCI, Verdaccio, Conda, BaGetter)
- [ ] **MIRR-09**: Operator can enable/disable mirror services from the Admin dashboard (one-click provisioning via Docker socket)
- [ ] **MIRR-10**: Smelter ingredient model has an explicit ecosystem enum (PYPI, APT, APK, OCI, NPM, CONDA, NUGET) alongside existing os_family

### Operator UX

- [ ] **UX-01**: Operator can paste a script and receive auto-detected package suggestions based on AST analysis (Python imports, Bash apt-get/yum, PowerShell Import-Module)
- [ ] **UX-02**: Operator can select from curated package bundles (Data Science, DevOps, Network Ops, etc.) to bulk-approve packages and create a blueprint
- [ ] **UX-03**: Pre-built starter templates (Python General, Data Science, Network Tools, Windows Automation) are seeded on first EE startup
- [ ] **UX-04**: User-facing UI labels are simplified: Ingredient → Package, Smelter Registry → Package Registry, Capability Matrix/Tool → Add-on Tool, etc.
- [ ] **UX-05**: Operator can search packages by description (plain-language) not just exact package name
- [ ] **UX-06**: User can toggle between standard (full UI) and simplified mode (Template Gallery + Upload Script + My Images)
- [ ] **UX-07**: Template catalog shows usage stats (created_by, nodes using it, last_used_at) so proven templates surface first

## v20.0+ Requirements

Deferred to future release. Tracked but not in current roadmap.

### Advanced Ecosystems

- **ADV-01**: Extend transitive dependency resolution to all ecosystems (npm, Conda, APT, apk)
- **ADV-02**: Conda channel selector (conda-forge vs defaults) stored per ingredient
- **ADV-03**: NuGet packageSourceMapping for multi-feed resolution

### Advanced UX

- **ADV-04**: Per-user ui_mode preference persisted in User model (currently localStorage only)
- **ADV-05**: Template catalog with full usage analytics (build history, failure rates)

## Out of Scope

| Feature | Reason |
|---------|--------|
| Automatic dependency pinning (lock-file generation) | Server-side lock files without target platform context produce false confidence; show resolved tree instead |
| Full conda channel sync (all platforms/versions) | 500 GB+ storage; use filtered sync only |
| Real-time dep resolution during wizard typing | pip resolver is 2-10s per call; would create load spikes; use explicit "Resolve" button |
| Auto-suggest CVE fixes (auto-upgrade transitive deps) | No context about operator's version constraints; show CVE + recommendation, let operator decide |
| Script Analyzer as hard gate | Bash/PowerShell static analysis is inherently imprecise; soft suggestions only |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| CRUD-01 | Phase 107 | Pending |
| CRUD-02 | Phase 107 | Pending |
| CRUD-03 | Phase 107 | Pending |
| CRUD-04 | Phase 107 | Pending |
| DEP-01 | Phase 108 | Pending |
| DEP-02 | Phase 110 | Pending |
| DEP-03 | Phase 110 | Pending |
| DEP-04 | Phase 110 | Pending |
| MIRR-01 | Phase 109 | Pending |
| MIRR-02 | Phase 109 | Pending |
| MIRR-03 | Phase 111 | Pending |
| MIRR-04 | Phase 111 | Pending |
| MIRR-05 | Phase 111 | Pending |
| MIRR-06 | Phase 112 | Pending |
| MIRR-07 | Phase 109 | Pending |
| MIRR-08 | Phase 112 | Pending |
| MIRR-09 | Phase 112 | Pending |
| MIRR-10 | Phase 107 | Pending |
| UX-01 | Phase 113 | Pending |
| UX-02 | Phase 114 | Pending |
| UX-03 | Phase 114 | Pending |
| UX-04 | Phase 115 | Pending |
| UX-05 | Phase 115 | Pending |
| UX-06 | Phase 115 | Pending |
| UX-07 | Phase 115 | Pending |

**Coverage:**
- v19.0 requirements: 25 total
- Mapped to phases: 25
- Unmapped: 0

---
*Requirements defined: 2026-04-01*
*Last updated: 2026-04-01 after roadmap creation*
