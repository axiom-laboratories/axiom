# Phase 11: Compatibility Engine - Context

**Gathered:** 2026-03-09
**Status:** Ready for planning

<domain>
## Phase Boundary

Add OS-family metadata and runtime dependency tracking to CapabilityMatrix tool entries, enforce OS compatibility at blueprint creation API level, and filter the tool picker in the Foundry blueprint editor in real-time. Smelter Registry enforcement, wizard UI, and package management are later phases.

</domain>

<decisions>
## Implementation Decisions

### Tool admin UI placement
- New "Tools" tab in the Foundry page, alongside the existing Templates and Blueprints tabs
- Editable table with columns: tool_id, OS family, validation_cmd, runtime_dependencies, active status
- Full CRUD: add new tool entries, edit existing ones, delete (soft-delete — marks inactive, never destroys)
- Soft-delete: if a tool entry is referenced by any existing blueprint, it is marked inactive (hidden from new blueprints) rather than hard-deleted; API returns info about which blueprints reference it
- Only active tool entries appear in the blueprint editor tool picker

### OS family on blueprints
- Explicit DEBIAN/ALPINE dropdown in the blueprint creation form — admin declares OS family; not auto-derived from base_os string
- Only DEBIAN and ALPINE for v1 (matches existing CapabilityMatrix seed data)
- OS family badge displayed on blueprint cards in the Foundry list views
- Backfill existing NULL blueprints to DEBIAN via migration (safe default — all current builds are Debian-based), then make os_family required for new blueprint creation
- Template creation validates only the runtime blueprint's OS family against tools; network blueprints are OS-agnostic and are not validated

### Runtime dependency representation
- `runtime_dependencies` stored as a JSON list of tool_ids (e.g. `["python-3.11"]`) on each CapabilityMatrix entry
- Dependencies are scoped per OS family implicitly — each CapabilityMatrix row is already (base_os_family × tool_id), so dependency tool_ids reference other entries within the same OS family
- **Two-phase confirmation flow (API + UI):**
  - When admin selects a tool with unsatisfied dependencies in the blueprint editor, a dialog prompts to confirm each missing dep individually before submission
  - At the API level: `POST /api/blueprints` returns 422 with a `deps_to_confirm` list if any tool has runtime dependencies not included in the blueprint's tool list
  - Caller resubmits with `confirmed_deps: ["python-3.11"]` to acknowledge and proceed — confirmed deps are auto-added to the blueprint
  - This applies to both UI and programmatic/CI callers

### OS compatibility validation (COMP-03)
- Validation fires at blueprint creation time (`POST /api/blueprints`)
- Rejects if any selected tool_id has no active CapabilityMatrix entry for the blueprint's declared os_family
- Error response lists the offending tools explicitly: e.g. "Blueprint validation failed: tools [pwsh-7.4] have no CapabilityMatrix entry for ALPINE. Add ALPINE support for these tools or change the OS family."

### Foundry tool picker filtering (COMP-04)
- Tools are filtered in real-time immediately as admin selects OS family in the blueprint creation form
- Only tools with an active CapabilityMatrix entry for the selected OS family are shown — incompatible tools are hidden entirely (not greyed out)
- Before OS family is selected, tool list shows a placeholder ("Select an OS family to see available tools")

### Claude's Discretion
- Exact table styling / column order for the Tools tab
- Modal vs inline form for adding/editing tool entries
- How to handle tools with deep dependency chains (transitive deps — detect and surface in one confirmation dialog or chain)

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `CapabilityMatrix` DB model (db.py:274): has `base_os_family`, `tool_id`, `injection_recipe`, `validation_cmd`, `artifact_id` — needs `runtime_dependencies` (JSON text) and `is_active` (bool) columns added
- `Blueprint` DB model (db.py:233): already has `os_family: Mapped[str]` column — currently never populated at creation, needs to be set from the new dropdown
- `CreateBlueprintDialog.tsx`: already fetches `/api/capability-matrix` and renders tool_id chips — this is the component to add OS filtering and dep-confirmation logic
- `Templates.tsx`: already has a tab-based layout with Blueprints tab — add "Tools" as a third tab here

### Established Patterns
- `Blueprint.os_family` exists but is NULL for all existing blueprints — migration required before enforcement can be added
- `foundry_service.py` already derives `os_family = "ALPINE" if "alpine" in base_os.lower() else "DEBIAN"` from the runtime blueprint's `base_os` field — this logic can be replaced/removed once blueprints explicitly carry os_family
- Startup seeding in `main.py` (~line 94) seeds CapabilityMatrix entries — new `runtime_dependencies`/`is_active` fields need defaults in the seed
- `BlueprintCreate` / `BlueprintResponse` models in `models.py` need `os_family` field added

### Integration Points
- `POST /api/blueprints` — add OS family validation (tools vs os_family) and dep-confirmation flow
- `GET /api/capability-matrix` — needs to accept `?os_family=DEBIAN` query param for real-time filtering in UI
- New CRUD routes needed: `POST /api/capability-matrix`, `PATCH /api/capability-matrix/{id}`, `DELETE /api/capability-matrix/{id}`
- `migration_v25.sql` (or next available number) — add `runtime_dependencies TEXT`, `is_active BOOLEAN DEFAULT TRUE` to capability_matrix; backfill blueprints.os_family = 'DEBIAN' WHERE os_family IS NULL

</code_context>

<specifics>
## Specific Ideas

- Dep-confirmation dialog in blueprint editor: list each required dep with a checkbox "Add python-3.11 to this blueprint?" — admin must confirm each one before submitting
- API confirmation mechanism: `POST /api/blueprints` → 422 with `{ "detail": "deps_required", "deps_to_confirm": ["python-3.11"] }` → resubmit with `{ ..., "confirmed_deps": ["python-3.11"] }`
- Tool soft-delete: instead of a "delete" that destroys, clicking delete marks `is_active=false` and shows which blueprints reference it, letting admin clean those up first if desired

</specifics>

<deferred>
## Deferred Ideas

- None — discussion stayed within phase scope

</deferred>

---

*Phase: 11-compatibility-engine*
*Context gathered: 2026-03-09*
