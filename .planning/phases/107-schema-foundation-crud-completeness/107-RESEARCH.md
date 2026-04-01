# Phase 107: Schema Foundation + CRUD Completeness - Research

**Researched:** 2026-04-01
**Domain:** SQLAlchemy async schema changes, FastAPI PATCH endpoints, React CRUD patterns
**Confidence:** HIGH

## Summary

Phase 107 is a well-scoped internal phase with no new external dependencies. All work lives within the existing FastAPI+SQLAlchemy async backend and React+TanStack Query frontend. The main technical concerns are: (1) adding an ecosystem enum column to an existing table with a migration default, (2) implementing optimistic locking via version column comparison, and (3) extending the BlueprintWizard component to support edit mode while keeping create mode unchanged.

The codebase already has complete patterns for every operation needed: PATCH endpoints (CapabilityMatrix), pencil-edit flow (JobDefinitions), dialog-based forms (Add Tool in Templates.tsx), and migration SQL files (up to v45). No new libraries or architectural patterns are required. The only design decisions remaining are schema shape for three new tables and the Approved OS edit UX pattern, both marked as Claude's discretion.

**Primary recommendation:** Follow existing codebase patterns exactly. No new dependencies needed. Focus on correctness of optimistic locking and migration idempotency.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- Blueprint edit flow: Re-open existing BlueprintWizard in edit mode, pre-populated. Pencil icon on each blueprint card. Auto-increment version on save. Optimistic locking via version column + 409 on mismatch. New PATCH /api/blueprints/{id} endpoint.
- Approved OS management: New "Approved OS" tab in Foundry page. Full CRUD with PATCH endpoint. Block delete if any blueprint references the OS entry's image_uri as base_os. OS Family dropdown restricted to DEBIAN and ALPINE only (remove FEDORA).
- Dependency confirmation dialog: Show on 422 deps_required response. Simple list format. All-or-nothing acceptance. Single "Add and Save" button. Works in both create and edit flows.
- Ecosystem enum on ApprovedIngredient: PYPI, APT, APK, OCI, NPM, CONDA, NUGET. All 7 from day one. Migration defaults existing rows to PYPI. Non-nullable after migration.
- New schema tables: ingredient_dependencies, curated_bundles, curated_bundle_items. Empty after this phase; downstream phases populate them.

### Claude's Discretion
- Approved OS edit UX pattern (inline table rows vs modal form)
- Schema design for ingredient_dependencies, curated_bundles, curated_bundle_items tables
- Migration SQL file numbering and structure
- Whether to clean up FEDORA references in smelter_service.py and mirror_service.py filter lists

### Deferred Ideas (OUT OF SCOPE)
- Full Fedora build support (Dockerfile generation, dnf/yum injection)
- Dependency tree visualization (showing which tool requires which dep)
- Side-by-side diff on version conflicts
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| CRUD-01 | Operator can edit an existing Image Recipe (blueprint) via a pre-populated wizard modal, with optimistic locking (version column + 409 on conflict) | BlueprintWizard already exists with 5 steps. Needs edit mode prop + PATCH endpoint. Version column already on Blueprint model (default=1). Optimistic locking pattern documented below. |
| CRUD-02 | Operator can edit an existing Tool Recipe via an edit dialog using the existing PATCH endpoint | PATCH /api/capability-matrix/{id} already exists in foundry_router.py. Tool table in Templates.tsx needs pencil icon + pre-populated edit dialog. |
| CRUD-03 | Admin can list, add, edit, and remove Approved OS entries from a dedicated section | GET/POST/DELETE endpoints exist. Need PATCH endpoint + referential integrity check on delete + new tab in Templates.tsx. |
| CRUD-04 | Operator sees a confirmation dialog showing all runtime dependencies before a blueprint build commits | Backend already returns 422 with deps_required error on POST /api/blueprints. Frontend needs to catch this and show a confirmation dialog, then resubmit with confirmed_deps. Same logic needed for PATCH. |
| MIRR-10 | Smelter ingredient model has an explicit ecosystem enum (PYPI, APT, APK, OCI, NPM, CONDA, NUGET) alongside existing os_family | ApprovedIngredient in ee/smelter/models.py needs new column. Migration SQL required. New tables for downstream phases. |
</phase_requirements>

## Standard Stack

### Core (already in project)
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| SQLAlchemy | 2.0+ (async) | ORM + schema | Already used throughout; EEBase for EE tables |
| FastAPI | 0.100+ | API endpoints | Existing PATCH pattern in capability-matrix |
| React | 18.x | Frontend | Existing component patterns |
| TanStack Query | 5.x | Data fetching + mutations | Used by BlueprintWizard and Templates.tsx |
| Sonner | latest | Toast notifications | Already imported in both wizard and page |
| Radix UI | latest | Dialog, AlertDialog, Select, Tabs | All already in use in Templates.tsx |

### Supporting (already in project)
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| Lucide React | latest | Icons (Pencil, Plus, etc.) | Edit button icons |
| Pydantic | 2.x | Request/response models | BlueprintUpdate, ApprovedOSUpdate models |

### Alternatives Considered
None needed. This phase uses only existing stack components.

## Architecture Patterns

### Existing Code Locations

```
axiom-ee/ee/
  foundry/models.py     # Blueprint, ApprovedOS, CapabilityMatrix, PuppetTemplate (SQLAlchemy)
  smelter/models.py     # ApprovedIngredient (SQLAlchemy)
  base.py               # EEBase (separate DeclarativeBase)

puppeteer/agent_service/ee/routers/
  foundry_router.py     # Blueprint, template, capability matrix, approved OS endpoints
  smelter_router.py     # Ingredient endpoints

puppeteer/dashboard/src/
  components/foundry/BlueprintWizard.tsx  # 5-step wizard (create only today)
  views/Templates.tsx                      # Foundry page with tabs
```

### Pattern 1: Optimistic Locking (PATCH with version check)

**What:** Client sends current `version` in PATCH body. Server compares against DB. If mismatch, return 409.
**When to use:** Blueprint edit (CRUD-01)
**Example:**

```python
# In foundry_router.py — PATCH /api/blueprints/{id}
@foundry_router.patch("/api/blueprints/{id}", response_model=BlueprintResponse)
async def update_blueprint(
    id: str,
    req: BlueprintUpdate,
    current_user: User = Depends(require_permission("foundry:write")),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(Blueprint).where(Blueprint.id == id))
    bp = result.scalar_one_or_none()
    if not bp:
        raise HTTPException(status_code=404, detail="Blueprint not found")
    if req.version != bp.version:
        raise HTTPException(status_code=409, detail="Blueprint was modified by another user")
    # Apply updates...
    bp.version += 1
    await db.commit()
```

**Frontend pattern (from JobDefinitions.tsx):**
```typescript
// Fetch current version before editing
const handleEdit = async (id: string) => {
    const res = await authenticatedFetch(`/api/blueprints/${id}`);
    const data = await res.json();
    setEditingBlueprint(data);  // includes version
    setWizardOpen(true);
};

// On save, include version in payload
const handleSave = async (payload) => {
    const res = await authenticatedFetch(`/api/blueprints/${id}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ ...payload, version: editingBlueprint.version })
    });
    if (res.status === 409) {
        toast.error("Blueprint was modified by another user. Your changes were not saved.");
        // Reload latest version
        handleEdit(id);
        return;
    }
};
```

### Pattern 2: Dependency Confirmation Dialog (422 catch + resubmit)

**What:** Backend returns 422 with `deps_required` error code. Frontend shows confirmation dialog. User accepts, resubmit with `confirmed_deps`.
**When to use:** Blueprint create and edit flows (CRUD-04)
**Example:**

```typescript
// In BlueprintWizard mutation handler
const res = await authenticatedFetch('/api/blueprints', { method: 'POST', body: JSON.stringify(payload) });
if (res.status === 422) {
    const err = await res.json();
    if (err.detail?.error === 'deps_required') {
        setPendingDeps(err.detail.deps_to_confirm);
        setShowDepDialog(true);
        return;  // Don't throw — user will confirm
    }
}
// On dialog confirm:
await authenticatedFetch('/api/blueprints', {
    method: 'POST',
    body: JSON.stringify({ ...payload, confirmed_deps: pendingDeps })
});
```

This pattern already exists on the backend (see `create_blueprint` in foundry_router.py lines 64-88). The frontend just needs to handle the 422 response.

### Pattern 3: Referential Integrity Check on Delete

**What:** Before deleting an ApprovedOS, check if any Blueprint references its `image_uri` as `base_os` in the definition JSON.
**When to use:** Approved OS delete (CRUD-03)
**Example:**

```python
# In foundry_router.py — enhanced DELETE /api/approved-os/{id}
all_bps = (await db.execute(select(Blueprint))).scalars().all()
for bp in all_bps:
    defn = json.loads(bp.definition)
    if defn.get("base_os") == os_entry.image_uri:
        raise HTTPException(
            status_code=409,
            detail=f"Cannot delete: referenced by blueprint '{bp.name}'"
        )
```

### Pattern 4: BlueprintWizard Edit Mode

**What:** Add `editBlueprint` prop to BlueprintWizard. When set, pre-populate all fields from the existing blueprint and use PATCH instead of POST.
**When to use:** CRUD-01
**Example:**

```typescript
interface BlueprintWizardProps {
    open: boolean;
    onOpenChange: (open: boolean) => void;
    editBlueprint?: Blueprint | null;  // NEW: if set, wizard is in edit mode
}

// In useEffect when opening:
useEffect(() => {
    if (open && editBlueprint) {
        const def = editBlueprint.definition;  // already parsed by caller
        setComposition({
            name: editBlueprint.name,
            type: editBlueprint.type,
            os_family: editBlueprint.os_family || 'DEBIAN',
            base_os: def.base_os || 'debian-12-slim',
            packages: def.packages || { python: [], system: [] },
            tools: (def.tools || []).map((t: any) => t.id),
        });
        setStep(1);
    } else if (open) {
        setComposition(DEFAULT_COMPOSITION);
        setStep(1);
    }
}, [open, editBlueprint]);
```

Note: The existing `handleClone` method (line 91-107) already demonstrates the exact unpacking logic needed. Edit mode reuses this but skips the name suffix and uses PATCH instead of POST.

### Anti-Patterns to Avoid
- **Don't use SQLAlchemy `with_for_update()` for optimistic locking**: The version column approach is simpler and works across both SQLite and Postgres. `with_for_update()` is pessimistic locking and requires careful transaction management.
- **Don't make edit a separate component**: Reuse BlueprintWizard with a mode prop. Duplicating the 680-line wizard would create maintenance burden.
- **Don't use Alembic**: This project uses manual migration SQL files. Stick with `migration_v{N}.sql` pattern (currently at v45, so next is v46).

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Toast notifications | Custom notification system | `toast` from sonner (already imported) | Consistent with existing UX |
| Confirmation dialogs | Custom modal | `AlertDialog` from Radix (already imported in Templates.tsx) | Accessible, keyboard-navigable |
| Form validation | Manual checks | Pydantic validators on backend, conditional `disabled` on frontend buttons | Existing pattern throughout |
| Tab navigation | Custom tab component | `Tabs` from `@/components/ui/tabs` (already used) | Consistent with existing Foundry page |

## Common Pitfalls

### Pitfall 1: EEBase vs Base metadata
**What goes wrong:** Adding tables to the wrong declarative base. CE's `Base.metadata.create_all` runs separately from `EEBase.metadata.create_all`.
**Why it happens:** New tables for ingredient_dependencies, curated_bundles, curated_bundle_items are EE models and MUST extend `EEBase` (in axiom-ee), not `Base` (in agent_service/db.py).
**How to avoid:** All new SQLAlchemy models go in `axiom-ee/ee/smelter/models.py` or `axiom-ee/ee/foundry/models.py`, extending EEBase.
**Warning signs:** Tables not created on startup; test_ce_smoke.py failing.

### Pitfall 2: Migration idempotency with IF NOT EXISTS
**What goes wrong:** Migration fails on fresh DB (tables already created by `create_all`) or on re-run.
**Why it happens:** `create_all` handles fresh DBs. Migrations handle existing DBs. Both need to work.
**How to avoid:** Use `ALTER TABLE ... ADD COLUMN IF NOT EXISTS` for Postgres. SQLite doesn't support this natively, but the project only uses migrations on Postgres deployments (SQLite gets fresh schema from `create_all`).
**Warning signs:** Migration SQL that uses plain `ALTER TABLE ... ADD COLUMN` without IF NOT EXISTS.

### Pitfall 3: JSON definition parsing in Blueprint
**What goes wrong:** Blueprint.definition is stored as a JSON string in the DB. When editing, the frontend might double-serialize or fail to parse.
**Why it happens:** The `definition` field is `Text` in the DB but `Dict` in the Pydantic response model. The router manually does `json.loads(bp.definition)` before returning.
**How to avoid:** The PATCH endpoint must: (1) receive `definition` as a Dict from the client, (2) store it as `json.dumps(definition)` in the DB. The GET endpoint already returns it parsed. Frontend can use the parsed Dict directly.
**Warning signs:** `"definition": "{\"base_os\":..."` (double-quoted JSON string in response).

### Pitfall 4: BlueprintWizard mutation error handling
**What goes wrong:** The existing `createMutation` in BlueprintWizard throws on non-OK responses. A 422 for deps_required gets caught by the generic `onError` handler and shown as a toast.
**Why it happens:** The mutation's `mutationFn` (line 137-155) checks `!res.ok` and throws. The 422 with deps_required is a special case that should trigger the confirmation dialog, not an error toast.
**How to avoid:** Intercept the 422 response before the generic throw. Check `err.detail?.error === 'deps_required'`, set state for the dialog, and return without throwing.
**Warning signs:** User sees error toast "Failed to create blueprint" instead of the dependency confirmation dialog.

### Pitfall 5: OS Family dropdown still showing FEDORA
**What goes wrong:** Operator selects FEDORA from dropdown, but no Foundry build support exists, leading to silent failures.
**Why it happens:** FEDORA is in the BlueprintWizard Step1Identity select options (line 531) but has no implementation.
**How to avoid:** Remove FEDORA from all OS family dropdowns in BlueprintWizard and any Approved OS forms. Keep only DEBIAN and ALPINE.
**Warning signs:** FEDORA appearing in any dropdown or filter list.

### Pitfall 6: Approved OS delete without referential check
**What goes wrong:** Admin deletes an ApprovedOS entry that's referenced by a Blueprint's base_os field. Blueprint becomes unbuildable.
**Why it happens:** Current DELETE endpoint has no referential integrity check (see foundry_router.py line 452-465).
**How to avoid:** Before delete, scan all Blueprint definitions for `base_os` matching the ApprovedOS.image_uri. Return 409 if found.
**Warning signs:** Blueprint builds failing with "base image not found" after an OS entry was deleted.

## Code Examples

### New Pydantic Models Needed

```python
# In axiom-ee/ee/foundry/models.py — add after BlueprintCreate

class BlueprintUpdate(BaseModel):
    """Partial update for blueprint edit with optimistic locking."""
    name: Optional[str] = None
    definition: Optional[Dict] = None
    os_family: Optional[str] = None
    confirmed_deps: Optional[List[str]] = None
    version: int  # REQUIRED — for optimistic locking

    @field_validator('os_family', mode='before')
    @classmethod
    def normalize_os_family(cls, v):
        return v.upper() if isinstance(v, str) else v


class ApprovedOSCreate(BaseModel):
    """Explicit create model (currently using ApprovedOSResponse for both)."""
    name: str
    image_uri: str
    os_family: str


class ApprovedOSUpdate(BaseModel):
    """Partial update for approved OS edit."""
    name: Optional[str] = None
    image_uri: Optional[str] = None
    os_family: Optional[str] = None
```

### New Schema Tables (Claude's discretion recommendations)

```python
# In axiom-ee/ee/smelter/models.py — new tables

class IngredientDependency(EEBase):
    """Tracks transitive dependencies between approved ingredients.
    Used by Phase 108 (dependency resolution)."""
    __tablename__ = "ingredient_dependencies"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    parent_id: Mapped[str] = mapped_column(String(36), index=True)  # FK to approved_ingredients.id
    child_id: Mapped[str] = mapped_column(String(36), index=True)   # FK to approved_ingredients.id
    dependency_type: Mapped[str] = mapped_column(String(50))         # "install_requires", "extras_require", etc.
    version_constraint: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    ecosystem: Mapped[str] = mapped_column(String(20))               # PYPI, APT, etc.
    discovered_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint('parent_id', 'child_id', 'ecosystem', name='uq_ingredient_dep'),
    )


class CuratedBundle(EEBase):
    """Pre-built package bundles (Data Science, DevOps, etc.).
    Used by Phase 114 (curated bundles UX)."""
    __tablename__ = "curated_bundles"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    name: Mapped[str] = mapped_column(String(255), unique=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    ecosystem: Mapped[str] = mapped_column(String(20))  # PYPI, APT, etc.
    os_family: Mapped[str] = mapped_column(String(50))   # DEBIAN, ALPINE
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")


class CuratedBundleItem(EEBase):
    """Individual package in a curated bundle."""
    __tablename__ = "curated_bundle_items"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    bundle_id: Mapped[str] = mapped_column(String(36), index=True)  # FK to curated_bundles.id
    ingredient_name: Mapped[str] = mapped_column(String(255))
    version_constraint: Mapped[str] = mapped_column(String(255), default="*")
```

### Ecosystem Enum Column Addition

```python
# In axiom-ee/ee/smelter/models.py — add to ApprovedIngredient class
ecosystem: Mapped[str] = mapped_column(String(20), default="PYPI", server_default="'PYPI'")
```

### Migration SQL (migration_v46.sql)

```sql
-- migration_v46.sql — Phase 107: Schema Foundation + CRUD Completeness
-- Adds ecosystem enum to approved_ingredients, creates new tables for dep resolution + bundles.
-- Safe for existing deployments (IF NOT EXISTS / ADD COLUMN IF NOT EXISTS).

-- 1. Add ecosystem column to approved_ingredients
ALTER TABLE approved_ingredients ADD COLUMN IF NOT EXISTS ecosystem VARCHAR(20) NOT NULL DEFAULT 'PYPI';

-- 2. Create ingredient_dependencies table
CREATE TABLE IF NOT EXISTS ingredient_dependencies (
    id SERIAL PRIMARY KEY,
    parent_id VARCHAR(36) NOT NULL,
    child_id VARCHAR(36) NOT NULL,
    dependency_type VARCHAR(50) NOT NULL,
    version_constraint VARCHAR(255),
    ecosystem VARCHAR(20) NOT NULL,
    discovered_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(parent_id, child_id, ecosystem)
);
CREATE INDEX IF NOT EXISTS ix_ingredient_deps_parent ON ingredient_dependencies(parent_id);
CREATE INDEX IF NOT EXISTS ix_ingredient_deps_child ON ingredient_dependencies(child_id);

-- 3. Create curated_bundles table
CREATE TABLE IF NOT EXISTS curated_bundles (
    id VARCHAR(36) PRIMARY KEY,
    name VARCHAR(255) UNIQUE NOT NULL,
    description TEXT,
    ecosystem VARCHAR(20) NOT NULL,
    os_family VARCHAR(50) NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    is_active BOOLEAN NOT NULL DEFAULT TRUE
);

-- 4. Create curated_bundle_items table
CREATE TABLE IF NOT EXISTS curated_bundle_items (
    id SERIAL PRIMARY KEY,
    bundle_id VARCHAR(36) NOT NULL,
    ingredient_name VARCHAR(255) NOT NULL,
    version_constraint VARCHAR(255) DEFAULT '*'
);
CREATE INDEX IF NOT EXISTS ix_bundle_items_bundle ON curated_bundle_items(bundle_id);
```

### Approved OS Edit UX Recommendation (Claude's discretion)

**Recommendation: Inline table edit (not modal).** Rationale:
- ApprovedOS has only 3 fields (name, image_uri, os_family) -- too simple for a modal
- The tool recipe table already uses an inline-style interaction pattern in Templates.tsx
- Inline edit is faster for operators managing a small list (typically 2-6 OS entries)
- Pattern: pencil icon in Actions column toggles row into edit mode with Input fields, Save/Cancel buttons

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| No edit for blueprints | Edit via wizard re-open | This phase | Operators no longer need delete+recreate |
| No version tracking | Optimistic locking via version column | This phase | Safe concurrent editing |
| Implicit PYPI-only ecosystem | Explicit ecosystem enum | This phase | Enables multi-ecosystem mirrors in Phase 109+ |

**Deprecated/outdated:**
- FEDORA in OS family dropdowns: non-functional, being removed this phase

## Open Questions

1. **FEDORA cleanup scope**
   - What we know: FEDORA appears in BlueprintWizard dropdown (line 531) and possibly in smelter/mirror service filter lists
   - What's unclear: Whether to also clean up FEDORA references in smelter_service.py and mirror_service.py filter lists
   - Recommendation: Clean up all UI-facing references. Leave backend service references (they're benign and may be needed if Fedora support is added later)

2. **GET /api/blueprints/{id} endpoint**
   - What we know: The edit flow needs to fetch a single blueprint by ID. Currently only GET /api/blueprints (list) exists.
   - What's unclear: Whether to add a dedicated GET /api/blueprints/{id} endpoint or have the frontend filter from the list
   - Recommendation: Add a GET /api/blueprints/{id} endpoint. It's needed for the edit flow to get the latest version (important for optimistic locking) and is trivial to implement.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework (backend) | pytest + pytest-asyncio |
| Framework (frontend) | vitest + @testing-library/react |
| Config file (backend) | `puppeteer/pytest.ini` or pyproject.toml |
| Config file (frontend) | `puppeteer/dashboard/vitest.config.ts` |
| Quick run command (backend) | `cd puppeteer && pytest tests/test_smelter.py -x` |
| Quick run command (frontend) | `cd puppeteer/dashboard && npx vitest run src/views/__tests__/Templates.test.tsx` |
| Full suite command | `cd puppeteer && pytest && cd dashboard && npm run test` |

### Phase Requirements to Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| CRUD-01 | Blueprint PATCH with version check returns updated blueprint; 409 on stale version | unit | `cd puppeteer && pytest tests/test_blueprint_edit.py -x` | Wave 0 |
| CRUD-02 | Tool recipe edit via existing PATCH endpoint | unit | Already covered by existing capability matrix PATCH tests | Check existing |
| CRUD-03 | Approved OS PATCH + delete referential integrity | unit | `cd puppeteer && pytest tests/test_approved_os_crud.py -x` | Wave 0 |
| CRUD-04 | Blueprint create/edit returns 422 with deps_required when deps missing | unit | `cd puppeteer && pytest tests/test_blueprint_deps.py -x` | Partial (test_smelter.py has related) |
| MIRR-10 | ApprovedIngredient has ecosystem column, new tables exist | unit | `cd puppeteer && pytest tests/test_schema_v46.py -x` | Wave 0 |

### Sampling Rate
- **Per task commit:** `cd puppeteer && pytest tests/test_blueprint_edit.py tests/test_approved_os_crud.py -x`
- **Per wave merge:** `cd puppeteer && pytest && cd dashboard && npm run test`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `puppeteer/tests/test_blueprint_edit.py` -- covers CRUD-01 (PATCH + optimistic locking + 409)
- [ ] `puppeteer/tests/test_approved_os_crud.py` -- covers CRUD-03 (PATCH + referential integrity on DELETE)
- [ ] `puppeteer/tests/test_schema_v46.py` -- covers MIRR-10 (ecosystem column exists, new tables created)

*(CRUD-02 tool recipe edit is already testable via existing PATCH /api/capability-matrix/{id} endpoint. CRUD-04 backend logic already exists in create_blueprint; frontend dialog is the new work.)*

## Sources

### Primary (HIGH confidence)
- Direct codebase inspection: `axiom-ee/ee/foundry/models.py` -- Blueprint, ApprovedOS, CapabilityMatrix models
- Direct codebase inspection: `axiom-ee/ee/smelter/models.py` -- ApprovedIngredient model
- Direct codebase inspection: `puppeteer/agent_service/ee/routers/foundry_router.py` -- all existing CRUD endpoints
- Direct codebase inspection: `puppeteer/dashboard/src/components/foundry/BlueprintWizard.tsx` -- wizard component
- Direct codebase inspection: `puppeteer/dashboard/src/views/Templates.tsx` -- Foundry page with tabs
- Direct codebase inspection: `puppeteer/dashboard/src/views/JobDefinitions.tsx` -- edit pattern reference
- Direct codebase inspection: `axiom-ee/ee/plugin.py` -- EE table creation via EEBase.metadata.create_all
- Direct codebase inspection: `puppeteer/migration_v45.sql` -- latest migration file

### Secondary (MEDIUM confidence)
- SQLAlchemy 2.0 optimistic locking patterns (training data, verified against codebase usage)

### Tertiary (LOW confidence)
- None

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- all libraries already in project, no new dependencies
- Architecture: HIGH -- all patterns verified against existing codebase code
- Pitfalls: HIGH -- identified from direct code inspection of existing patterns and known issues
- Schema design (new tables): MEDIUM -- reasonable design for downstream phase needs, but Phase 108/114 may refine

**Research date:** 2026-04-01
**Valid until:** 2026-05-01 (stable internal codebase, no external dependency changes)
