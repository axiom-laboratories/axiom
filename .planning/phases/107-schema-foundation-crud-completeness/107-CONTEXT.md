# Phase 107: Schema Foundation + CRUD Completeness - Context

**Gathered:** 2026-04-01
**Status:** Ready for planning

<domain>
## Phase Boundary

Operators can fully manage all Foundry entities (blueprints, tools, approved OS) through the dashboard, with the DB schema ready for all v19.0 features. This phase adds missing CRUD operations, optimistic locking for blueprints, and creates the schema foundation (ecosystem enum, new tables) that Phases 108-115 depend on.

</domain>

<decisions>
## Implementation Decisions

### Blueprint edit flow
- Re-open the existing BlueprintWizard in edit mode, pre-populated with current blueprint values
- Pencil icon on each blueprint card triggers the edit (consistent with JobDefinitions pattern)
- Every save auto-increments the version column (integer, currently default=1)
- Optimistic locking: PUT/PATCH sends current version; backend returns 409 if version mismatch
- On 409 conflict: toast "Blueprint was modified by another user. Your changes were not saved." then reload latest version into the wizard
- Backend needs a new PATCH /api/blueprints/{id} endpoint (does not exist today)

### Approved OS management
- New "Approved OS" tab in the Foundry page (Templates.tsx) alongside Image Recipes / Templates / Tools
- Full CRUD: list, add, edit, delete (currently missing: edit and PATCH endpoint)
- Block delete if any blueprint references the OS entry's image_uri as base_os
- OS Family field: fixed dropdown with DEBIAN and ALPINE only (remove non-functional FEDORA option from BlueprintWizard and Admin page)
- Edit UX approach (inline table vs modal): Claude's discretion

### Dependency confirmation dialog
- When the backend returns 422 with deps_required, show a confirmation dialog listing all required dependencies
- Simple list format: "These tools are required by your selected tools" + checklist of dep names
- All-or-nothing: operator accepts all deps or cancels (no individual deselection)
- Single button: "Add and Save" — resubmits with confirmed_deps containing all listed deps
- Dialog appears in both blueprint creation and edit flows (backend already enforces on POST)

### Ecosystem enum on ApprovedIngredient
- Add explicit ecosystem column to ApprovedIngredient: PYPI, APT, APK, OCI, NPM, CONDA, NUGET
- All 7 values from day one (matches MIRR-10 requirement)
- Migration: default all existing rows to PYPI (all current ingredients are Python packages)
- Column is non-nullable after migration (new rows must specify ecosystem)

### New schema tables
- ingredient_dependencies, curated_bundles, curated_bundle_items: schema design at Claude's discretion
- These are plumbing for Phases 108 (transitive deps) and 114 (curated bundles)
- Tables should exist and be empty after this phase; downstream phases populate them

### Claude's Discretion
- Approved OS edit UX pattern (inline table rows vs modal form)
- Schema design for ingredient_dependencies, curated_bundles, curated_bundle_items tables
- Migration SQL file numbering and structure
- Whether to clean up FEDORA references in smelter_service.py and mirror_service.py filter lists (or leave for a future phase)

</decisions>

<specifics>
## Specific Ideas

- Pencil icon pattern already used in JobDefinitions — reuse the same visual treatment
- Fedora is non-functional today: appears in dropdowns and filter lists but no Foundry build support exists. Dropdown should show only DEBIAN and ALPINE.
- The existing CapabilityMatrix already has full CRUD (GET/POST/PATCH/DELETE) — no changes needed there, just the tool recipe edit UI (already exists in Templates.tsx)

</specifics>

<code_context>
## Existing Code Insights

### Reusable Assets
- `BlueprintWizard` component (`dashboard/src/components/foundry/BlueprintWizard.tsx`): existing 5-step wizard for blueprint creation — needs edit mode prop
- `CapabilityMatrix` CRUD endpoints: already complete in `foundry_router.py` (PATCH endpoint exists)
- `ApprovedOS` model + list/create/delete endpoints: exist in `foundry_router.py`, need PATCH + referential integrity check
- `tabs.tsx` component: already used in Templates.tsx for tab navigation

### Established Patterns
- EE DB models live in `~/Development/axiom-ee/ee/foundry/models.py` and `ee/smelter/models.py`, extending `EEBase`
- Pydantic request/response models co-located in the same model files
- EE routers in `puppeteer/agent_service/ee/routers/foundry_router.py` import from `...db` (models re-exported by EE plugin loader)
- Migration SQL files: `puppeteer/migration_v{N}.sql` pattern, currently up to v45
- `audit()` helper used for all security-relevant mutations

### Integration Points
- `foundry_router.py`: add PATCH /api/blueprints/{id} and PATCH /api/approved-os/{id} endpoints
- `ee/foundry/models.py`: add version-based optimistic locking logic
- `ee/smelter/models.py`: add ecosystem column to ApprovedIngredient + new tables
- `Templates.tsx`: add Approved OS tab, blueprint edit trigger, dep confirmation dialog
- `BlueprintWizard.tsx`: add edit mode (pre-populate from existing blueprint data)

</code_context>

<deferred>
## Deferred Ideas

- Full Fedora build support (Dockerfile generation, dnf/yum injection) — future milestone
- Dependency tree visualization (showing which tool requires which dep) — could enhance Phase 110's tree viewer
- Side-by-side diff on version conflicts — overkill for current use case, reconsider if multi-operator editing becomes common

</deferred>

---

*Phase: 107-schema-foundation-crud-completeness*
*Context gathered: 2026-04-01*
