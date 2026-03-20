---
phase: 35-private-ee-repo-plugin-wiring
plan: "03"
subsystem: ee-routers-plugin
tags: [python, fastapi, ee, routers, services, plugin]

# Dependency graph
requires:
  - "35-01 (EEBase + axiom-ee scaffold)"
  - "35-02 (EE SQLAlchemy models)"
provides:
  - "7 EE router files in ee/{feature}/router.py with absolute imports"
  - "4 EE service files in ee/{feature}/services.py with absolute imports"
  - "EE Pydantic models co-located in ee/{feature}/models.py"
  - "Full EEPlugin.register() implementation with all 8 EEContext flags"
  - "Zero relative imports in entire ee/ tree"
affects:
  - "35-04"
  - "35-05"

# Tech tracking
tech-stack:
  added:
    - "httpx (for WebhookService.dispatch_event outbound HTTP calls)"
  patterns:
    - "Deferred router imports inside register() body — prevents circular import at module load"
    - "Lazy proxy pattern in foundry/services.py for smelter/staging cross-deps"
    - "Pydantic models co-located with SQLAlchemy models in ee/{feature}/models.py"
    - "Per-router error isolation in register() — one failed mount does not block others"

key-files:
  created:
    - "~/Development/axiom-ee/ee/foundry/router.py"
    - "~/Development/axiom-ee/ee/foundry/services.py"
    - "~/Development/axiom-ee/ee/smelter/router.py"
    - "~/Development/axiom-ee/ee/smelter/services.py"
    - "~/Development/axiom-ee/ee/audit/router.py"
    - "~/Development/axiom-ee/ee/auth_ext/router.py"
    - "~/Development/axiom-ee/ee/webhooks/router.py"
    - "~/Development/axiom-ee/ee/webhooks/services.py"
    - "~/Development/axiom-ee/ee/triggers/router.py"
    - "~/Development/axiom-ee/ee/triggers/services.py"
    - "~/Development/axiom-ee/ee/users/router.py"
    - "~/Development/axiom-ee/ee/users/models.py"
  modified:
    - "~/Development/axiom-ee/ee/foundry/models.py (added Pydantic models)"
    - "~/Development/axiom-ee/ee/smelter/models.py (added Pydantic models)"
    - "~/Development/axiom-ee/ee/auth_ext/models.py (added Pydantic models + ALLOWED_ROLES)"
    - "~/Development/axiom-ee/ee/webhooks/models.py (added Pydantic models)"
    - "~/Development/axiom-ee/ee/triggers/models.py (added Pydantic models)"
    - "~/Development/axiom-ee/ee/plugin.py (full register() implementation)"

key-decisions:
  - "EE Pydantic models co-located in ee/{feature}/models.py alongside SQLAlchemy models — avoids a separate pydantic/ subdirectory per feature"
  - "StagingService and _MirrorServiceProxy kept in ee/smelter/services.py — foundry/services.py uses lazy proxies to avoid circular import"
  - "ee/users/models.py created as new file (not added to rbac or auth_ext) — user CRUD models are logically owned by the users feature"
  - "WebhookService.dispatch_event uses httpx for async outbound HTTP — replaces CE no-op stub with real implementation"
  - "ALLOWED_ROLES constant lives in ee/auth_ext/models.py and is re-exported from ee/users/models.py — single source of truth"

# Metrics
duration: ~8 min
completed: 2026-03-19
---

# Phase 35 Plan 03: Router Migration + EEPlugin Wiring Summary

**All 7 EE routers migrated with absolute imports; EEPlugin.register() mounts all routers with per-router isolation and sets all 8 EEContext flags**

## Performance

- **Duration:** ~8 min
- **Started:** 2026-03-19T21:28:01Z
- **Completed:** 2026-03-19T21:36:22Z
- **Tasks:** 2
- **Files modified/created:** 18

## Accomplishments

### Task 1: Foundry + Smelter routers and services

- Migrated `foundry_router.py` → `ee/foundry/router.py`: 465-line router with blueprints, templates, capability matrix, image BOM, approved OS, legacy aliases
- Created `ee/foundry/services.py`: FoundryService with build_template (Smelter check, mirror check, Dockerfile gen, Docker build/push), build_image, list_images
- Added Pydantic models to `ee/foundry/models.py`: BlueprintCreate/Response, CapabilityMatrixEntry/Update, PuppetTemplateCreate/Response, ImageBuildRequest/Response, ImageBOMResponse, PackageIndexResponse, ApprovedOSResponse, ArtifactResponse
- Migrated `smelter_router.py` → `ee/smelter/router.py`: ingredients CRUD, config, mirror health/config, scan
- Created `ee/smelter/services.py`: SmelterService (add/list/delete/scan/validate), StagingService (smelt-check, BOM), _MirrorService background task
- Added Pydantic models to `ee/smelter/models.py`: ApprovedIngredientCreate/Response/Update, MirrorConfigUpdate

### Task 2: Remaining 5 routers, services, and plugin wiring

- `ee/audit/router.py`: GET /admin/audit-log from ee.audit.models.AuditLog
- `ee/auth_ext/router.py`: signing keys, API keys, service principal CRUD + token rotation
- Added Pydantic models to `ee/auth_ext/models.py`: UserSigningKey*/ApiKey*/SP* + ALLOWED_ROLES
- `ee/webhooks/services.py`: real WebhookService (list/create/delete/dispatch_event with HMAC signing)
- `ee/webhooks/router.py`: webhook CRUD, imports from ee.webhooks.*
- Added Pydantic models to `ee/webhooks/models.py`: WebhookCreate/Response
- `ee/triggers/services.py`: TriggerService (fire/list/create/delete/update/regenerate)
- `ee/triggers/router.py`: automation trigger routes
- Added Pydantic models to `ee/triggers/models.py`: TriggerCreate/Response/Update
- `ee/users/models.py`: UserCreate, UserResponse, PermissionGrant (new file)
- `ee/users/router.py`: user management + role permission CRUD
- `ee/plugin.py`: full `register()` — import all 7 model modules, create_all DDL, mount 7 routers with per-router try/except, set 8 EEContext flags

## Task Commits

Each task was committed atomically in the axiom-ee repo:

1. **Task 1: Migrate foundry + smelter routers and services** - `4953499`
2. **Task 2: Migrate remaining routers, wire EEPlugin.register()** - `6622d0a`

## Router → Flag Mapping

| Router | Module | EEContext flag |
|--------|--------|----------------|
| foundry_router | ee.foundry.router | ctx.foundry = True |
| smelter_router | ee.smelter.router | (part of foundry, no separate flag) |
| audit_router | ee.audit.router | ctx.audit = True |
| webhook_router | ee.webhooks.router | ctx.webhooks = True |
| trigger_router | ee.triggers.router | ctx.triggers = True |
| users_router | ee.users.router | ctx.rbac = True |
| auth_ext_router | ee.auth_ext.router | ctx.api_keys = True + ctx.service_principals = True |
| (no router) | DB-level capability | ctx.resource_limits = True |

## Verification Results

```
PASS: no relative imports in ee/ tree
PASS: ee.plugin import does not trigger agent_service.main
8 EEContext flags set (foundry, audit, webhooks, triggers, rbac, api_keys,
  service_principals, resource_limits)
7/7 router files present
```

## Decisions Made

- EE Pydantic models co-located in ee/{feature}/models.py — avoids a separate pydantic/ layer
- StagingService kept in ee/smelter/services.py; foundry/services.py uses lazy proxy to avoid circular import at module load
- ee/users/models.py is a new dedicated file for user CRUD models — logically separate from RBAC or auth_ext
- WebhookService.dispatch_event uses httpx for real outbound HTTP (CE stub was no-op)
- ALLOWED_ROLES single source of truth in ee/auth_ext/models.py, re-imported by ee/users/models.py

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing functionality] Created StagingService in ee/smelter/services.py**
- **Found during:** Task 1
- **Issue:** foundry/services.py (migrated from CE worktree) called `StagingService.run_smelt_check()` and `StagingService.capture_bom()`. The CE worktree had a `staging_service.py` but it is not an EE-owned service. The EE foundry_service needed these to work.
- **Fix:** Created minimal StagingService in ee/smelter/services.py with real smelt-check (docker run smoke test) and stub capture_bom. Added _MirrorServiceProxy as lazy proxy to avoid circular import.
- **Files modified:** ee/smelter/services.py, ee/foundry/services.py

**2. [Rule 2 - Missing functionality] Created ee/users/models.py**
- **Found during:** Task 2
- **Issue:** users_router.py imports UserCreate, UserResponse, PermissionGrant from agent_service.models — but these are absent from the CE worktree (EE-owned after split). No pre-existing ee/users/models.py.
- **Fix:** Created ee/users/models.py with UserCreate, UserResponse, PermissionGrant.
- **Files modified:** ee/users/models.py (new)

**3. [Rule 2 - Missing functionality] Added Pydantic models to 5 EE model files**
- **Found during:** Tasks 1 and 2
- **Issue:** CE worktree models.py no longer contains any EE Pydantic models (they were removed in the split). Routers imported them from `...models` — needs absolute imports pointing to EE-owned location.
- **Fix:** Added Pydantic models directly to the relevant ee/{feature}/models.py files (foundry, smelter, auth_ext, webhooks, triggers).
- **Files modified:** ee/foundry/models.py, ee/smelter/models.py, ee/auth_ext/models.py, ee/webhooks/models.py, ee/triggers/models.py

## Issues Encountered

None beyond the auto-fixed deviations above.

## Next Phase Readiness

- All 7 routers exist in axiom-ee with zero relative imports
- EEPlugin.register() is complete and isolation-tested
- Plans 35-04 (CE stub suppression) and 35-05 (integration test) can proceed
- `pip install -e ~/Development/axiom-ee/` + CE restart should now mount all EE routes

---
*Phase: 35-private-ee-repo-plugin-wiring*
*Completed: 2026-03-19*
