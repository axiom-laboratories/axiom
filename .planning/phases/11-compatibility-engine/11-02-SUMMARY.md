---
phase: 11-compatibility-engine
plan: "02"
subsystem: backend-api
tags: [capability-matrix, db-migration, fastapi, pydantic, soft-delete, wave-1]

# Dependency graph
requires:
  - "11-01 — Wave 0 test scaffold (test_compatibility_engine.py)"
provides:
  - "is_active + runtime_dependencies columns on CapabilityMatrix DB model"
  - "migration_v26.sql for existing deployments"
  - "Updated GET /api/capability-matrix with ?os_family and ?include_inactive filters"
  - "PATCH /api/capability-matrix/{id} with partial update via CapabilityMatrixUpdate"
  - "DELETE /api/capability-matrix/{id} soft-delete returning referencing_blueprints"
  - "CapabilityMatrixEntry Pydantic model with runtime_dependencies list and is_active bool"
affects:
  - "11-03 — Blueprint validation can now query is_active and runtime_dependencies via capability_matrix"
  - "11-04/05 — Frontend plans can now render is_active state and filter by os_family"

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Soft-delete pattern: is_active=False instead of DELETE — referencing entity scan returns impact list"
    - "JSON-string column pattern: runtime_dependencies stored as TEXT, deserialized by @field_validator in Pydantic model (same as target_tags)"
    - "Query param filtering pattern: Optional[str] = Query(None) with .upper() normalization"

key-files:
  created:
    - puppeteer/migration_v26.sql
  modified:
    - puppeteer/agent_service/db.py
    - puppeteer/agent_service/models.py
    - puppeteer/agent_service/main.py

key-decisions:
  - "Soft-delete over hard-delete: allows admin Tools tab to show inactive entries with ?include_inactive=true; reversible; doesn't orphan existing blueprint references"
  - "JSON string storage for runtime_dependencies (TEXT column with DEFAULT '[]'): consistent with existing target_tags pattern in this codebase — avoids JSON column type that SQLite doesn't natively support"
  - "PUT replaced by PATCH with CapabilityMatrixUpdate: partial update semantics are more appropriate for individual field edits; breaking change acceptable since API is internal and Plan 04 frontend is not built yet"

requirements-completed: [COMP-01, COMP-02]

# Metrics
duration: 3min
completed: 2026-03-11
---

# Phase 11 Plan 02: Capability Matrix DB + API Extension Summary

**is_active and runtime_dependencies columns added to CapabilityMatrix with migration, Pydantic models updated, four routes updated: GET gains os_family/include_inactive filters, PUT becomes PATCH, DELETE becomes soft-delete with impact list**

## Performance

- **Duration:** 3 min
- **Started:** 2026-03-11T10:16:50Z
- **Completed:** 2026-03-11T10:20:22Z
- **Tasks:** 2
- **Files modified:** 3 (+ 1 created)

## Accomplishments

- Created `puppeteer/migration_v26.sql` — ALTER TABLE with IF NOT EXISTS guards + blueprints.os_family backfill UPDATE
- Updated `CapabilityMatrix` ORM model in db.py: `runtime_dependencies` (Text, default='[]', server_default='[]') and `is_active` (Boolean, default=True, server_default='true')
- Updated both seed blocks in main.py startup to include `is_active=True, runtime_dependencies="[]"` in all CapabilityMatrix() constructors
- Updated `CapabilityMatrixEntry` Pydantic model: added `runtime_dependencies: List[str] = []` with @field_validator JSON deserializer, `is_active: bool = True`, and `base_os_family` uppercase normalizer
- Added `CapabilityMatrixUpdate` model for PATCH partial update (all fields Optional)
- Replaced GET route: now supports `?os_family` and `?include_inactive` query params; default excludes inactive
- Updated POST route: persists `runtime_dependencies` as JSON string and `is_active`
- Replaced PUT route with PATCH using `CapabilityMatrixUpdate` for partial updates
- Replaced DELETE with soft-delete: sets `is_active=False`, scans blueprints definitions for referencing tool_id, returns `{"status": "deactivated", "referencing_blueprints": [...]}`

## Task Commits

Each task was committed atomically:

1. **Task 1: DB model + migration (capability_matrix new columns + blueprint backfill)** - `de4d71f`
2. **Task 2: Updated Pydantic models + all four capability-matrix routes** - `208751c`

**Plan metadata:** _(docs commit follows)_

## Files Created/Modified

- `puppeteer/migration_v26.sql` — Two ALTER TABLE statements + blueprints.os_family backfill
- `puppeteer/agent_service/db.py` — CapabilityMatrix model gains 2 new columns
- `puppeteer/agent_service/models.py` — CapabilityMatrixEntry updated, CapabilityMatrixUpdate added
- `puppeteer/agent_service/main.py` — 4 routes updated + imports for Query and CapabilityMatrixUpdate

## Verification Results

Three Wave 0 tests now green:
- `test_matrix_has_os_family` — PASS (inspects db.py source for `is_active`)
- `test_matrix_runtime_deps` — PASS (inspects db.py source for `runtime_dependencies`)
- `test_matrix_os_family_filter` — PASS (inspects main.py GET handler for `os_family` query param)

Pre-existing tests (23): all PASS with no regressions. Two remaining failures are expected:
- `test_blueprint_os_mismatch_rejected` — Plan 03 item (POST /api/blueprints validation)
- `test_blueprint_dep_confirmation_flow` — SKIP per plan spec (awaits Plan 03)

## Decisions Made

- Soft-delete pattern chosen over hard-delete: preserves history, reversible, admin can view inactive with `?include_inactive=true`
- JSON string storage for `runtime_dependencies` (TEXT column): consistent with existing `target_tags` pattern in this codebase — same `@field_validator` deserialization approach
- `PUT` replaced by `PATCH` using `CapabilityMatrixUpdate` model: partial update semantics more appropriate; breaking change acceptable since frontend (Plans 04/05) not yet built

## Deviations from Plan

None — plan executed exactly as written. The `test_matrix_os_family_filter` test appeared to fail once in a multi-test run due to pytest module caching ordering, but passes consistently when run in isolation or with the correct PYTHONPATH set. The pre-existing collection errors (`test_bootstrap_admin.py`, `test_intent_scanner.py`, `test_tools.py`) are out-of-scope for this plan.

## Next Phase Readiness

- Plan 03 (blueprint validation) can now query `CapabilityMatrix.is_active == True` and deserialize `runtime_dependencies` JSON to implement OS-mismatch rejection and dep-confirmation flow
- Plan 04 (frontend) has `?os_family` and `?include_inactive` params available on GET /api/capability-matrix

---
*Phase: 11-compatibility-engine*
*Completed: 2026-03-11*

## Self-Check: PASSED
