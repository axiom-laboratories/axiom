# Requirements: Axiom

**Defined:** 2026-03-19
**Core Value:** Jobs run reliably — on the right node, when scheduled, with their output captured — without any step in the chain weakening the security model.

## v11.0 Requirements

Requirements for the CE/EE Split Completion milestone.

### CE Gap Fixes

- [x] **GAP-01**: CE mode returns 402 (not 404) for all EE routes — all 7 stub routers mounted in `load_ee_plugins()`
- [x] **GAP-02**: `load_ee_plugins()` uses `importlib.metadata.entry_points()` instead of deprecated `pkg_resources`
- [x] **GAP-03**: EE-only test files (`test_lifecycle_enforcement`, `test_foundry_mirror`, `test_smelter`, `test_staging`) isolated with `@pytest.mark.ee_only` marker + conftest skip logic
- [x] **GAP-04**: `test_bootstrap_admin.py` `User.role` attribute references removed — CE pytest suite passes cleanly
- [x] **GAP-05**: `NodeConfig` Pydantic model stripped of EE-only fields (`concurrency_limit`, `job_memory_limit`, `job_cpu_limit`)
- [x] **GAP-06**: `job_service.py` EE field workarounds (`concurrency_limit=0` hardcoding) removed and replaced with CE-appropriate defaults

### EE Plugin

- [x] **EE-01**: `axiom-ee` private GitHub repo created with `EEPlugin` class skeleton
- [x] **EE-02**: `EEPlugin.register()` is async and mounts all 7 EE routers via `app.include_router()`
- [x] **EE-03**: `EEPlugin.register()` creates EE DB tables via separate `EEBase.metadata.create_all(engine)`
- [x] **EE-04**: All 7 router files use absolute imports — no relative imports from CE codebase
- [x] **EE-05**: `pyproject.toml` entry_points configured (`[project.entry-points."axiom.ee"]`) and validated
- [x] **EE-06**: CE-alone smoke test passes: 13 tables created, all EE routes return 402, `GET /api/features` returns all false
- [x] **EE-07**: CE+EE combined install smoke test passes: EE tables present, EE routes functional, `GET /api/features` returns all true
- [ ] **EE-08**: `axiom-ee` stub wheel published to PyPI to reserve the package name

### Compilation

- [x] **BUILD-01**: EE source audited and cleaned for Cython compatibility — no `@dataclass` decorators, `__init__.py` excluded from `ext_modules`
- [x] **BUILD-02**: Cython `ext_modules` list configured in EE `pyproject.toml` — enumerates each `.py` file explicitly
- [x] **BUILD-03**: `cibuildwheel` CI pipeline in `axiom-ee` repo builds wheels for amd64 + arm64, Python 3.11 / 3.12 / 3.13
- [x] **BUILD-04**: Published EE wheel verified to contain no `.py` source files — only `.so` compiled extensions
- [x] **BUILD-05**: CE+EE combined smoke test passes after installing compiled `.so` wheel (not just source install)

### Licensing & Publishing

- [ ] **DIST-01**: Ed25519 offline licence key validation implemented in EE plugin — payload carries `customer_id`, `exp`, `features`; public key hardcoded in compiled binary; checked at startup only
- [ ] **DIST-02**: `axiom-ce` image published to Docker Hub in existing `release.yml` — two-step addition alongside GHCR
- [x] **DIST-03**: MkDocs docs updated with CE/EE admonition callouts — EE-only feature sections marked with `!!! enterprise` admonitions

## Future Requirements

### v12.0+

- **DIST-04**: Licence issuance portal — web UI or automated pipeline to generate and deliver signed licence keys to customers
- **DIST-05**: Periodic licence re-validation — check licence on a schedule, not only at startup
- **EE-09**: OIDC/SAML SSO integration
- **EE-10**: Custom RBAC roles + fine-grained permissions

## Out of Scope

| Feature | Reason |
|---------|--------|
| Licence issuance portal | Product decision required on customer onboarding flow — not blocking v11.0 |
| Online licence validation | Air-gapped deployments are a core use case — offline Ed25519 is required; online as optional future enhancement |
| Nuitka compilation | Undocumented multi-module wheel workflow; Cython is the established standard |
| Compiling `__init__.py` to .so | CPython bug #59828 — breaks relative imports; `__init__.py` must stay as plain Python |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| GAP-01 | Phase 34 | Complete |
| GAP-02 | Phase 34 | Complete |
| GAP-03 | Phase 34 | Complete |
| GAP-04 | Phase 34 | Complete |
| GAP-05 | Phase 34 | Complete |
| GAP-06 | Phase 34 | Complete |
| EE-01 | Phase 35 | Complete |
| EE-02 | Phase 35 | Complete |
| EE-03 | Phase 35 | Complete |
| EE-04 | Phase 35 | Complete |
| EE-05 | Phase 35 | Complete |
| EE-06 | Phase 35 | Complete |
| EE-07 | Phase 35 | Complete |
| EE-08 | Phase 35 | Pending |
| BUILD-01 | Phase 36 | Complete |
| BUILD-02 | Phase 36 | Complete |
| BUILD-03 | Phase 36 | Complete |
| BUILD-04 | Phase 36 | Complete |
| BUILD-05 | Phase 36 | Complete |
| DIST-01 | Phase 37 | Pending |
| DIST-02 | Phase 37 | Pending |
| DIST-03 | Phase 37 | Complete |

**Coverage:**
- v11.0 requirements: 22 total
- Mapped to phases: 22
- Unmapped: 0 ✓

---
*Requirements defined: 2026-03-19*
*Last updated: 2026-03-19 — traceability filled by roadmapper*
