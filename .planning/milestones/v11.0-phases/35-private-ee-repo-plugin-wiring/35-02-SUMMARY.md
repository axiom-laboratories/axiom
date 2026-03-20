---
phase: 35-private-ee-repo-plugin-wiring
plan: "02"
subsystem: ee-models
tags: [python, sqlalchemy, ee, models, orm]

# Dependency graph
requires:
  - "35-01 (EEBase + axiom-ee scaffold)"
provides:
  - "All 15 EE SQLAlchemy model classes defined in per-feature model files"
  - "EEBase.metadata contains exactly 15 tables after importing all model modules"
  - "Zero FK references from EE tables to CE tables (users, scheduled_jobs)"
affects:
  - "35-03"
  - "35-04"
  - "35-05"

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "EEBase subclassing — all EE models use `from ee.base import EEBase` never CE Base"
    - "FK removal pattern — cross-base FKs dropped, referencing columns kept as plain String"
    - "Comment-as-documentation — each dropped FK explained inline with reason"

key-files:
  created:
    - "~/Development/axiom-ee/ee/foundry/models.py"
    - "~/Development/axiom-ee/ee/smelter/models.py"
    - "~/Development/axiom-ee/ee/audit/models.py"
    - "~/Development/axiom-ee/ee/auth_ext/models.py"
    - "~/Development/axiom-ee/ee/rbac/models.py"
    - "~/Development/axiom-ee/ee/webhooks/models.py"
    - "~/Development/axiom-ee/ee/triggers/models.py"
  modified: []

key-decisions:
  - "All intra-EEBase FKs (ImageBOM.template_id, PackageIndex.template_id, CapabilityMatrix.artifact_id) dropped as plain String per plan spec — avoids DDL ordering dependencies and simplifies Cython compilation in Phase 36"
  - "Trigger.job_definition_id made nullable=True (was NOT NULL in CE) — no referential integrity without FK, so nullable is safer"
  - "UserSigningKey.username and UserApiKey.username kept as NOT NULL String — logical ownership preserved without DB-level FK constraint"

# Metrics
duration: 2min
completed: 2026-03-19
---

# Phase 35 Plan 02: EE SQLAlchemy Models Summary

**All 15 EE SQLAlchemy models defined across 7 per-feature files using EEBase, zero FK references to CE tables**

## Performance

- **Duration:** ~2 min
- **Started:** 2026-03-19T21:23:32Z
- **Completed:** 2026-03-19T21:25:30Z
- **Tasks:** 2
- **Files modified:** 7

## Accomplishments

- 7 Foundry models in `ee/foundry/models.py`: Blueprint, Artifact, ApprovedOS, CapabilityMatrix, PuppetTemplate, ImageBOM, PackageIndex
- 1 Smelter model in `ee/smelter/models.py`: ApprovedIngredient (full field set including vulnerability_report, mirror_status)
- 1 Audit model in `ee/audit/models.py`: AuditLog (exact CE field match)
- 3 Auth extension models in `ee/auth_ext/models.py`: UserSigningKey, UserApiKey, ServicePrincipal
- 1 RBAC model in `ee/rbac/models.py`: RolePermission with UniqueConstraint("role", "permission")
- 1 Webhook model in `ee/webhooks/models.py`: Webhook (exact CE field match)
- 1 Trigger model in `ee/triggers/models.py`: Trigger with job_definition_id as nullable String (FK dropped)
- All models importable from CE venv without touching agent_service
- EEBase.metadata verified to contain exactly 15 tables

## Task Commits

Each task was committed atomically in the axiom-ee repo:

1. **Task 1: Create foundry models (7 tables)** - `9c1ed8a`
2. **Task 2: Create remaining 8 EE models** - `aa5ec08`

## Files Created

| File | Tables | Notes |
|------|--------|-------|
| `ee/foundry/models.py` | Blueprint, Artifact, ApprovedOS, CapabilityMatrix, PuppetTemplate, ImageBOM, PackageIndex | CapabilityMatrix.artifact_id, ImageBOM.template_id, PackageIndex.template_id all plain String (FK dropped) |
| `ee/smelter/models.py` | ApprovedIngredient | Full field set from CE db.py lines 339-353 |
| `ee/audit/models.py` | AuditLog | Exact CE transcription |
| `ee/auth_ext/models.py` | UserSigningKey, UserApiKey, ServicePrincipal | username FK to users dropped; ServicePrincipal unchanged |
| `ee/rbac/models.py` | RolePermission | UniqueConstraint preserved |
| `ee/webhooks/models.py` | Webhook | Exact CE transcription |
| `ee/triggers/models.py` | Trigger | job_definition_id changed to nullable String (CE had NOT NULL FK) |

## Verification Results

```
PASS — 15 EE tables: ['approved_ingredients', 'approved_os', 'artifacts', 'audit_log',
'blueprints', 'capability_matrix', 'image_boms', 'package_index', 'puppet_templates',
'role_permissions', 'service_principals', 'triggers', 'user_api_keys', 'user_signing_keys', 'webhooks']
```

No actual `ForeignKey()` calls in any EE model file — all FK references exist only in comments documenting what was dropped and why.

## Decisions Made

- All intra-EEBase FKs dropped as plain String — avoids DDL ordering dependencies and simplifies Cython compilation in Phase 36
- `Trigger.job_definition_id` made `nullable=True` — logical: without FK constraint, NULL is valid (no orphan prevention)
- Username columns kept NOT NULL in UserSigningKey/UserApiKey — preserves logical ownership without DB-level enforcement

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## Next Phase Readiness

- All 15 EE tables defined and verified in EEBase.metadata
- Plans 35-03 (router implementations) and 35-04 (plugin wiring) can import these models directly
- No CE imports required — all 7 model files are CE-venv compatible without agent_service dependency

---
*Phase: 35-private-ee-repo-plugin-wiring*
*Completed: 2026-03-19*
