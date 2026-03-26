# Requirements: Axiom

**Defined:** 2026-03-26
**Core Value:** Jobs run reliably — on the right node, when scheduled, with their output captured — without any step in the chain weakening the security model.

## v14.2 Requirements

### Deployment

- [x] **DEPLOY-01**: Docs site is automatically deployed to GH Pages on every push to `main` via a new `docs-deploy.yml` workflow
- [x] **DEPLOY-02**: Deploy workflow is a standalone file with its own trigger and permissions, separate from `ci.yml`

### Config

- [x] **CONFIG-01**: `site_url` in `mkdocs.yml` updated to `https://axiom-laboratories.github.io/axiom/`
- [x] **CONFIG-02**: `offline` plugin made conditional (`!ENV [OFFLINE_BUILD, false]`) — disabled for GH Pages builds, enabled when `OFFLINE_BUILD=true`
- [x] **CONFIG-03**: Dockerfile sets `OFFLINE_BUILD=true` in the `mkdocs build` step to preserve current air-gap container behaviour

### Housekeeping

- [x] **HOUSE-01**: `docs/site/` added to `.gitignore` and removed from git tracking
- [x] **HOUSE-02**: `.nojekyll` file added to `docs/docs/` to prevent Jekyll interference on GH Pages

### Maintenance

- [x] **MAINT-01**: Local script to regenerate `openapi.json` from the FastAPI app (run locally when API schema changes, commits the updated file)

## Future Requirements

(none identified for this milestone)

## Out of Scope

| Feature | Reason |
|---------|--------|
| Custom domain (CNAME) | github.io URL is sufficient for now |
| Versioned docs (mike) | Adds complexity without current use case; conflicts with plain gh-deploy |
| Zip distribution path for offline | Docker container is the sole air-gap distribution path |
| robots.txt | Not needed for initial launch |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| DEPLOY-01 | Phase 71 | Complete |
| DEPLOY-02 | Phase 71 | Complete |
| CONFIG-01 | Phase 71 | Complete |
| CONFIG-02 | Phase 71 | Complete |
| CONFIG-03 | Phase 71 | Complete |
| HOUSE-01 | Phase 71 | Complete |
| HOUSE-02 | Phase 71 | Complete |
| MAINT-01 | Phase 71 | Complete |

**Coverage:**
- v14.2 requirements: 8 total
- Mapped to phases: 8
- Unmapped: 0 ✓

---
*Requirements defined: 2026-03-26*
*Last updated: 2026-03-26 — traceability confirmed after roadmap creation*
