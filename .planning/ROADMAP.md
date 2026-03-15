# Roadmap: Master of Puppets

## Milestones

- ✅ **v1.0–v6.0** — Milestones 1–6 (Production Reliability → Remote Validation) — shipped 2026-03-06/09
- ✅ **v8.0 — mop-push CLI & Job Staging** — Phases 17–19 (shipped 2026-03-15)
- 🚧 **v7.0 — Advanced Foundry & Smelter** — Phases 11–16 (in progress — Phase 11 complete)

## Phases

<details>
<summary>✅ v8.0 — mop-push CLI & Job Staging (Phases 17–19) — SHIPPED 2026-03-15</summary>

- [x] **Phase 17: Backend — OAuth Device Flow & Job Staging** — RFC 8628 device flow, ScheduledJob status field, /api/jobs/push with dual-token verification, REVOKED enforcement at dispatch (completed 2026-03-12)
- [x] **Phase 18: mop-push CLI** — mop-push login/push/create commands, Ed25519 signing locally, installable SDK package (completed 2026-03-12)
- [x] **Phase 19: Dashboard Staging View & Governance Doc** — Staging tab, script inspection, one-click Publish, status badges, OIDC v2 architecture doc (completed 2026-03-15)

Archive: `.planning/milestones/v8.0-ROADMAP.md`

</details>

### 🚧 v7.0 — Advanced Foundry & Smelter (In Progress)

- [x] **Phase 11: Compatibility Engine** — OS family tagging, runtime deps, API/UI enforcement (completed 2026-03-11)
- [x] **Phase 12: Smelter Registry** — Vetted ingredient catalog, CVE scanning, STRICT/WARNING enforcement (completed 2026-03-15)
- [ ] **Phase 13: Package Management & Custom Repos** — Local PyPI + APT mirror sidecars, auto-sync on ingredient add, air-gapped manual upload, pip.conf/sources.list build injection, sync log capture, mirror health UI
- [ ] **Phase 14: Foundry Wizard UI** — 5-step guided composition wizard with real-time OS filtering
- [ ] **Phase 15: Smelt-Check, BOM & Lifecycle** — Post-build ephemeral validation, JSON BOM, image ACTIVE/DEPRECATED/REVOKED states
- [ ] **Phase 16: Security & Governance** — SLSA provenance, Ed25519-signed build provenance, resource limits, --secret credentials

## Phase Details

### Phase 12: Smelter Registry
**Goal**: Admin can curate a vetted ingredient catalog; builds fail or warn when unapproved packages are used
**Depends on**: Phase 11
**Requirements**: SMLT-01, SMLT-02, SMLT-03, SMLT-04, SMLT-05
**Plans**: 9 plans
Plans:
- [x] 12-01-PLAN.md — Wave 0 test stubs
- [x] 12-02-PLAN.md — DB model + CRUD API
- [x] 12-03-PLAN.md — SmelterService implementation
- [x] 12-04-PLAN.md — pip-audit CVE scan integration
- [x] 12-05-PLAN.md — Foundry enforcement (STRICT/WARNING)
- [x] 12-06-PLAN.md — Template compliance badging (backend)
- [x] 12-07-PLAN.md — Dashboard compliance badges (frontend)
- [x] 12-08-PLAN.md — Phase verification
- [x] 12-09-PLAN.md — Bookkeeping wrap-up

### Phase 13: Package Management & Custom Repos
**Goal**: Operators can pre-bake native and PIP packages into images and consume packages from local mirrors with full air-gapped support
**Depends on**: Phase 12
**Requirements**:
- PKG-01: Auto-sync — mirror a package to local storage automatically when it is added to the Smelter Catalog
- PKG-02: Status tracking — approved_ingredients.mirror_status tracks PENDING / MIRRORED / FAILED per ingredient
- PKG-03: Air-gapped manual upload — admins can upload .whl / .deb files directly to the mirror for environments without internet access
- REPO-01: Mirror sidecars — pypiserver + Caddy APT sidecar run as Docker Compose services sharing a mirror-data volume; health endpoint returns sidecar uptime and disk usage
- REPO-02: Fail-fast enforcement — Foundry build raises HTTP 403 if any blueprint package is approved but not yet mirrored; no emergency external fetching
- REPO-03: pip redirect — Foundry build injects pip.conf into the Docker build context so pip uses the local pypiserver instead of the public PyPI index
- REPO-04: APT redirect — Foundry build injects sources.list into the Docker build context (DEBIAN builds only) so apt uses the local Caddy-hosted APT repo
**Plans**: 8 plans (5 original + 3 gap-closure)
Plans:
- [x] 13-01-PLAN.md — Infrastructure + DB schema (sidecars, mirror-data volume, migration, mirror_log column)
- [x] 13-02-PLAN.md — MirrorService + auto-sync hook in SmelterService (captures subprocess output to mirror_log)
- [x] 13-03-PLAN.md — Foundry fail-fast enforcement + pip.conf/sources.list injection
- [x] 13-04-PLAN.md — Admin UI (MirrorStatusBadge, sync log viewer, upload, health card + file browser link) + API endpoints
- [x] 13-05-PLAN.md — Phase verification + human checkpoint
- [x] 13-06-PLAN.md — Backend gap closure: mirror_log, is_active, migration rewrite, unconditional fail-fast, soft-purge delete, upload routing, mirror-config GET/PUT
- [ ] 13-07-PLAN.md — Gap closure (UI/frontend fixes)
- [ ] 13-08-PLAN.md — Gap closure (remaining)

### Phase 14: Foundry Wizard UI
**Goal**: A guided multi-step wizard replaces raw JSON blueprint editing for composing node images
**Depends on**: Phase 13
**Requirements**: WIZ-01, WIZ-02, WIZ-03
**Plans**: TBD

### Phase 15: Smelt-Check, BOM & Lifecycle
**Goal**: Every built image is validated by a smoke test, receives a JSON bill of materials, and carries a lifecycle status
**Depends on**: Phase 14
**Requirements**: SMCK-01, SMCK-02, BOM-01, BOM-02, BOM-03, LCY-01, LCY-02, LCY-03
**Plans**: TBD

### Phase 16: Security & Governance
**Goal**: Build provenance is signed, resource limits are enforced, and secrets never appear in image history
**Depends on**: Phase 15
**Requirements**: SEC-01, SEC-02, SEC-03, SEC-04
**Plans**: TBD

## Progress

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|----------------|--------|-----------|
| 17. Backend — OAuth Device Flow & Job Staging | v8.0 | 5/5 | Complete | 2026-03-12 |
| 18. mop-push CLI | v8.0 | 4/4 | Complete | 2026-03-12 |
| 19. Dashboard Staging View & Governance Doc | v8.0 | 5/5 | Complete | 2026-03-15 |
| 11. Compatibility Engine | v7.0 | 6/6 | Complete | 2026-03-11 |
| 12. Smelter Registry | 10/10 | Complete    | 2026-03-15 | 2026-03-15 |
| 13. Package Management & Custom Repos | 7/8 | In Progress|  | - |
| 14. Foundry Wizard UI | v7.0 | 0/TBD | Not started | - |
| 15. Smelt-Check, BOM & Lifecycle | v7.0 | 0/TBD | Not started | - |
| 16. Security & Governance | v7.0 | 0/TBD | Not started | - |

---

## Archived

- ✅ **v6.0 — Remote Environment Validation** (Phases 6–10) — shipped 2026-03-06/09 → `.planning/milestones/v6.0-phases/`
- ✅ **v5.0 — Notifications & Webhooks** (Phases 1–3) — shipped 2026-03-06 → `.planning/milestones/v5.0-phases/`
- ✅ **v4.0 — Automation & Integration** (Phases 1–3) — shipped 2026-03-06 → `.planning/milestones/v4.0-phases/`
- ✅ **v3.0 — Advanced Foundry & Hot-Upgrades** (Phases 1–4) — shipped 2026-03-05 → `.planning/milestones/v3.0-phases/`
- ✅ **v2.0 — Foundry & Node Lifecycle** (Phases 1–4) — shipped 2026-03-05 → `.planning/milestones/v2.0-phases/`
- ✅ **v1.0 — Production Reliability** (Phases 1–6) — shipped 2026-03-05 → `.planning/milestones/v1.0-phases/`
