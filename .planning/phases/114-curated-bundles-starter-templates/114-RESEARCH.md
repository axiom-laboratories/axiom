# Phase 114: Curated Bundles + Starter Templates - Research

**Researched:** 2026-04-05
**Domain:** Bundle management, starter templates, bulk ingredient approval, template gallery UI
**Confidence:** HIGH

## Summary

Phase 114 delivers non-developer operators a simplified path to building node images: instead of manually selecting individual packages, they select from pre-built curated bundles (Data Science, Web/API, Network Ops, File Processing, Windows Automation) or starter templates seeded on first deployment. The phase integrates tightly with Phase 107's `CuratedBundle`/`CuratedBundleItem` DB models (already in schema), Phase 108's transitive dependency resolution, and existing `smelter_service.add_ingredient()` workflow. The UI occupies the Foundry page (Templates tab), introducing a "Starter Templates" gallery at the top and an "Admin: Bundles" section for CRUD management.

**Primary recommendation:** Implement as three subsystems: (1) Bundle admin API (`/api/admin/bundles`) for CRUD with automatic seeding, (2) Bundle application endpoint (`/api/foundry/apply-bundle`) that bulk-approves ingredients with transitive resolution, (3) Starter template seeding with `is_starter` flag on `PuppetTemplate`, and (4) Templates.tsx gallery UI with two paths ("Build now" / "Customize first"). All bundle operations require `foundry:write` permission; immutability of starter templates is enforced client-side and via soft-delete on server. The flow leverages existing `SmelterService.add_ingredient()` (which auto-triggers resolver + mirroring), so no new services are needed.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **5 default bundles ship:** Data Science, Web/API, Network Ops, File Processing, Windows Automation
- **Mixed-ecosystem bundles:** A single bundle can include PyPI, APT, and other ecosystems (e.g., Data Science includes numpy + libopenblas)
- **CuratedBundleItem gets ecosystem column:** Each item has its own ecosystem (existing CuratedBundle.ecosystem becomes the primary ecosystem)
- **No version pins on bundle items:** Package names only; transitive resolver picks latest compatible versions at approval time
- **Admin-curated only:** Admins can add/edit/delete bundles; operators consume bundles only
- **One-click bulk-approve:** Applying a bundle approves all packages immediately (skips review queue)
- **Already-approved packages silently skipped:** No errors, no duplicate approvals
- **Transitive dependency resolution auto-triggers:** For each newly approved package (existing Phase 108 flow)
- **Applying bundle DOES NOT auto-create blueprint:** Operator uses ingredients in wizard or via starter templates
- **Requires `foundry:write` permission:** Consistent with individual ingredient approval
- **Feedback: immediate toast + mirror status on ingredients:** "Applying Data Science bundle (12 packages)..." then packages appear in ingredient list as they're approved
- **5 starter templates seeded on first EE startup:** One per bundle: Python Data Science, Web/API, Network Tools, File Processing, Windows Automation
- **Each starter pre-configured:** With bundle's packages + appropriate base OS
- **Gallery cards show:** Name, description, package count, "Use This Template" button
- **Starter badges + immutability:** "Starter" badge; cannot be deleted (hidden only)
- **"Use This Template" dialog:** Two options: "Build now" (3-click path) or "Customize first" (clone + wizard)
- **"Build now" auto-approves + mirrors:** If starter's packages aren't yet approved/mirrored, auto-approve + mirror + build in single flow (requires foundry:write)
- **"Build now" confirmation shows summary:** Template name, base OS, package count by ecosystem (e.g., "8 Python, 3 APT"), estimated build time
- **Bundles and starters live in Foundry page only:** No Dashboard shortcuts for now

### Claude's Discretion
- Exact package lists for each of the 5 bundles
- Base OS choices per starter template (Debian vs Alpine)
- Bundle admin CRUD UI layout (table vs cards)
- Gallery card styling and icons
- "Estimated build time" calculation/display
- Bundle seeding mechanism (SQL migration vs startup code)
- Whether starters are stored as regular `PuppetTemplate` rows with `is_starter` flag or separate table (RECOMMENDATION: single table with flag)

### Deferred Ideas (OUT OF SCOPE)
None — discussion stayed within phase scope

</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| UX-02 | Operator can select from curated package bundles (Data Science, DevOps, Network Ops, etc.) to bulk-approve packages and create a blueprint | Bundle CRUD endpoints, bulk approval via `smelter_service.add_ingredient()` loop, auto-trigger of `ResolverService.resolve_ingredient_tree()` and `MirrorService.mirror_ingredient_and_dependencies()` per ingredient |
| UX-03 | Pre-built starter templates (Python General, Data Science, Network Tools, Windows Automation) are seeded on first EE startup | Seeding logic in startup/migration, `PuppetTemplate.is_starter` flag, gallery UI in Templates.tsx with starter filter, immutability enforcement |

</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| SQLAlchemy ORM | existing | CuratedBundle/CuratedBundleItem persistence | Already in stack; Phase 107 defined schema |
| FastAPI | 0.100+ (existing) | Bundle CRUD + apply endpoints | Consistent with all other EE routes |
| Pydantic | existing | Request/response models | Used throughout codebase |
| React Query | existing | Frontend bundle data fetching | Standard across dashboard |
| Tailwind CSS | existing | UI styling | Dashboard standard |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `uuid4()` | builtin Python | Generate bundle IDs | Consistent with existing Axiom models |
| Toast notifications (Sonner) | existing | User feedback during bundle apply | Existing pattern in dashboard |
| Dialog components (Radix) | existing | "Use This Template" dialog | Existing UI pattern |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Single `PuppetTemplate` table with `is_starter` flag | Separate `StarterTemplate` table | Single table simpler, matches CONTEXT decision; separate table adds query complexity with no benefit |
| Bulk approval via loop of `add_ingredient()` | Custom bulk SQL insert + resolver trigger | Loop is transparent, observable (each ingredient's resolver/mirror runs; feedback updates); bulk insert is opaque |
| Startup seeding (Python code) | SQL migration (`migration_v*.sql`) | Startup code is version-agnostic and testable; migrations are one-time; startup is idempotent — use both: migration creates tables, startup code seeds data |

## Architecture Patterns

### Recommended Project Structure
```
puppeteer/agent_service/
├── db.py
│   ├── CuratedBundle              # Phase 107 (existing)
│   ├── CuratedBundleItem          # Phase 107 (existing, add ecosystem column)
│   └── PuppetTemplate             # Add is_starter: bool column
├── models.py
│   ├── CuratedBundleCreate        # NEW
│   ├── CuratedBundleResponse      # NEW
│   ├── ApplyBundleRequest         # NEW
│   └── BundleApplicationResult    # NEW
├── ee/routers/
│   ├── bundles_router.py          # NEW: Bundle CRUD + apply
│   └── foundry_router.py          # MODIFY: Add starter template seeding
├── services/
│   └── (no new service file needed — reuse smelter_service.add_ingredient)
└── ee/
    └── interfaces/
        └── bundles.py             # NEW: Startup seeding helpers

puppeteer/dashboard/src/
├── views/
│   └── Templates.tsx              # MODIFY: Add gallery + bundle admin tabs
├── components/
│   ├── StarterGalleryCard.tsx     # NEW: Template card component
│   ├── UseTemplateDialog.tsx      # NEW: "Build now" vs "Customize first"
│   ├── BuildConfirmationDialog.tsx # NEW: Summary card + Build button
│   └── BundleAdminPanel.tsx       # NEW: Bundle CRUD table
```

### Pattern 1: Bulk Ingredient Approval via Loop + Auto-Resolution
**What:** Apply bundle = loop through bundle items, call `smelter_service.add_ingredient()` for each. Resolver + mirroring auto-trigger per item.
**When to use:** For all bundle applications
**Example:**
```python
# Backend: ee/routers/bundles_router.py (pseudocode)
@router.post("/api/foundry/apply-bundle/{bundle_id}")
async def apply_bundle(
    bundle_id: str,
    current_user: User = Depends(require_permission("foundry:write")),
    db: AsyncSession = Depends(get_db)
):
    """Bulk-approve all ingredients in a bundle. Auto-skip already-approved."""
    bundle_result = await db.execute(
        select(CuratedBundle).where(CuratedBundle.id == bundle_id)
    )
    bundle = bundle_result.scalar_one_or_none()
    if not bundle:
        raise HTTPException(status_code=404, detail="Bundle not found")

    items_result = await db.execute(
        select(CuratedBundleItem).where(CuratedBundleItem.bundle_id == bundle_id)
    )
    items = items_result.scalars().all()

    approved_count = 0
    skipped_count = 0

    for item in items:
        # Check if already approved
        existing = await db.execute(
            select(ApprovedIngredient).where(
                ApprovedIngredient.name == item.ingredient_name,
                ApprovedIngredient.ecosystem == item.ecosystem
            )
        )
        if existing.scalar_one_or_none():
            skipped_count += 1
            continue

        # Add ingredient (auto-triggers resolver + mirror)
        try:
            ingredient_in = ApprovedIngredientCreate(
                name=item.ingredient_name,
                version_constraint=item.version_constraint or "*",
                ecosystem=item.ecosystem,
                os_family=bundle.os_family,
                sha256=""  # Optional field for bundles
            )
            await SmelterService.add_ingredient(db, ingredient_in)
            approved_count += 1
        except Exception as e:
            logger.error(f"Failed to approve {item.ingredient_name}: {str(e)}")

    audit(db, current_user, "bundle:applied", f"{bundle.name} ({approved_count} new, {skipped_count} skipped)")
    await db.commit()

    return {
        "bundle_id": bundle.id,
        "bundle_name": bundle.name,
        "approved": approved_count,
        "skipped": skipped_count,
        "total": len(items)
    }
```

### Pattern 2: Starter Template Gallery with Dual Actions
**What:** Gallery shows starter cards. Clicking "Use This Template" opens dialog with "Build now" and "Customize first" options.
**When to use:** For non-technical operator onboarding
**Example:**
```typescript
// Frontend: components/UseTemplateDialog.tsx (pseudocode)
export function UseTemplateDialog({ template, isOpen, onClose }: Props) {
  const [action, setAction] = useState<'build' | 'customize' | null>(null);
  const buildMutation = useMutation({
    mutationFn: async () => {
      const res = await authenticatedFetch(`/api/templates/${template.id}/build`, {
        method: 'POST'
      });
      return res.json();
    },
    onSuccess: () => {
      toast.success(`Build started for ${template.friendly_name}`);
      onClose();
    }
  });

  const cloneMutation = useMutation({
    mutationFn: async () => {
      const res = await authenticatedFetch(`/api/templates/${template.id}/clone`, {
        method: 'POST',
        body: JSON.stringify({ friendly_name: `${template.friendly_name} (Custom)` })
      });
      return res.json();
    },
    onSuccess: (cloned) => {
      // Open blueprint wizard for cloned template
      setEditingTemplateId(cloned.id);
      onClose();
    }
  });

  if (action === 'build') {
    return <BuildConfirmationDialog template={template} onBuild={buildMutation.mutate} />;
  }

  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent>
        <DialogHeader>Use {template.friendly_name}?</DialogHeader>
        <div className="space-y-4">
          <Button onClick={() => setAction('build')}>Build now</Button>
          <Button variant="outline" onClick={() => cloneMutation.mutate()}>
            Customize first
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
}
```

### Pattern 3: Starter Template Immutability
**What:** Starters are flagged with `is_starter=true`. Client hides delete button. Server rejects delete for starters.
**When to use:** For all starter template management
**Example:**
```python
# Backend: ee/routers/foundry_router.py (pseudocode)
@router.delete("/api/templates/{id}")
async def delete_template(
    id: str,
    current_user: User = Depends(require_permission("foundry:write")),
    db: AsyncSession = Depends(get_db)
):
    """Delete a template (unless it's a starter)."""
    result = await db.execute(select(PuppetTemplate).where(PuppetTemplate.id == id))
    template = result.scalar_one_or_none()
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")

    if template.is_starter:
        raise HTTPException(
            status_code=403,
            detail="Starter templates cannot be deleted; they are read-only"
        )

    await db.delete(template)
    await db.commit()
    return {"status": "deleted", "id": id}
```

### Anti-Patterns to Avoid
- **Synchronous bulk approval:** Don't block the response waiting for all resolver/mirror tasks. Return immediately after triggering approvals; let async tasks run background. UI gets immediate toast + polling for mirror status.
- **Bundle duplication in starter templates:** Don't copy bundle items into starter blueprints as static JSON. Store reference to bundle ID; expand at build time. Allows bundle updates to flow to starters.
- **Manual version pinning in bundles:** Don't pin exact versions (e.g., `numpy==1.24.3`). Bundle item versions default to `*` (any). Operator sets constraints in blueprint wizard if needed.
- **Admin-only bundle visibility:** Don't hide bundles from operators. Operators see and apply bundles (CONTEXT decision: operators consume, don't create). Admins see CRUD UI.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Bulk package approval | Custom approval queue or multi-step workflow | Loop + `SmelterService.add_ingredient()` | add_ingredient already handles resolver + mirror integration; looping is transparent and observable |
| Transitive dependency resolution on new ingredients | Custom dependency walker | `ResolverService.resolve_ingredient_tree()` (Phase 108) | Already integrated into add_ingredient; auto-triggers on every new ingredient |
| Starter template cloning | Custom clone SQL | `/api/templates/{id}/clone` endpoint + PuppetTemplate copy | Simpler; avoids DB-level blueprint deep-copy complexity |
| Bundle package lookup | Custom SQL joins | Simple `select(CuratedBundleItem).where(bundle_id == x)` | Single table, no complex joins needed |
| Mirror status polling | WebSocket or long-polling | Existing `mirror_status` field + client-side React Query refetch | Ingredients already have mirror_status field (Phase 107); use standard polling pattern |

**Key insight:** Phases 107-108 provided the infrastructure (resolver, mirroring, ingredient model). Phase 114 is pure orchestration — calling existing services in bulk. Avoid building new logic; compose existing pieces.

## Common Pitfalls

### Pitfall 1: Confusing "Apply Bundle" with "Build Template"
**What goes wrong:** Operators think applying a bundle creates a ready-to-build template. It doesn't — it only approves ingredients. They must still use the wizard to create a blueprint + template.
**Why it happens:** Bundle and template names sound similar; both are in Foundry page.
**How to avoid:** Make UI flow explicit: (1) Apply bundle → toast "X packages approved" → ingredient list updates. (2) Separate "Create Blueprint" action from bundle application. Starter templates are the exception: "Use This Template" → build/customize.
**Warning signs:** Operators asking "Why is my bundle not building?" — they skipped blueprint creation.

### Pitfall 2: Duplicate Approval Silently Failing
**What goes wrong:** Operator applies same bundle twice. Second time, all items are skipped (already approved). Operator doesn't know if it succeeded.
**Why it happens:** No feedback for skipped items; toast only shows new approvals.
**How to avoid:** Toast message format: "Applied Data Science bundle: 5 new approved, 7 already approved, 12 total". Both counts visible.
**Warning signs:** Operator applies bundle, sees no change in ingredient list, assumes failure.

### Pitfall 3: Starter Template Edit Confusion
**What goes wrong:** Operator clicks "Customize first", clones starter, edits blueprint, but original starter is now orphaned and confused about whether they're editing the starter or a copy.
**Why it happens:** If clone UI doesn't clearly label the new template as custom.
**How to avoid:** Cloned template gets name like "{original} (Custom)" automatically. Gallery still shows original starter. Edit screen shows parent template reference.
**Warning signs:** Operator reporting "I saved my changes but the template didn't update" — they edited a clone, not the original.

### Pitfall 4: Bundle Ecosystem Mismatch
**What goes wrong:** Bundle is marked `os_family=DEBIAN` but includes Alpine-only packages (e.g., `musl-dev`). Approval succeeds but build fails later.
**Why it happens:** Bundle editor didn't validate ecosystem compatibility per item.
**How to avoid:** Bundle CRUD form validates: for each item, check that the ecosystem is applicable to the bundle's OS family. APT packages only for DEBIAN; apk only for ALPINE.
**Warning signs:** Build fails on package not found, but it was in the approved ingredients list.

### Pitfall 5: Mirror Status Not Propagating to UI
**What goes wrong:** Operator applies bundle, sees toast, but ingredient list doesn't update with mirror_status in real-time. Operator thinks nothing happened.
**Why it happens:** No polling or WebSocket update; frontend doesn't refetch ingredients after bundle apply.
**How to avoid:** After bundle apply toast, invalidate React Query `['smelter:ingredients']` cache. Ingredients list auto-refetches with latest mirror_status.
**Warning signs:** Operator applies bundle, ingredient list stays empty; toast says success, but UI doesn't show new ingredients.

## Code Examples

Verified patterns from official sources:

### Bundle Admin CRUD (Create)
```python
# Source: Phase 107 + Axiom EE patterns (main.py and existing routers)
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from agent_service.db import get_db, AsyncSession, CuratedBundle
from agent_service.models import CuratedBundleCreate, CuratedBundleResponse
from agent_service.deps import require_permission, audit
from agent_service.db import User
from uuid import uuid4

bundles_router = APIRouter()

@bundles_router.post("/api/admin/bundles", response_model=CuratedBundleResponse, tags=["Bundles"])
async def create_bundle(
    bundle: CuratedBundleCreate,
    current_user: User = Depends(require_permission("foundry:write")),
    db: AsyncSession = Depends(get_db)
):
    """Create a new curated bundle (Admin only)."""
    new_bundle = CuratedBundle(
        id=str(uuid4()),
        name=bundle.name,
        description=bundle.description,
        ecosystem=bundle.ecosystem,
        os_family=bundle.os_family,
        is_active=True
    )
    db.add(new_bundle)
    await db.commit()
    await db.refresh(new_bundle)

    audit(db, current_user, "bundle:created", bundle.name)
    await db.commit()

    return new_bundle
```

### Apply Bundle (Bulk Approval)
```python
# Source: Phase 107-108 integration (smelter_service + resolver)
@bundles_router.post("/api/foundry/apply-bundle/{bundle_id}")
async def apply_bundle(
    bundle_id: str,
    current_user: User = Depends(require_permission("foundry:write")),
    db: AsyncSession = Depends(get_db)
):
    """Apply a curated bundle: bulk-approve all items with auto-resolve."""
    from agent_service.services.smelter_service import SmelterService
    from agent_service.models import ApprovedIngredientCreate

    bundle_result = await db.execute(
        select(CuratedBundle).where(CuratedBundle.id == bundle_id)
    )
    bundle = bundle_result.scalar_one_or_none()
    if not bundle:
        raise HTTPException(status_code=404, detail="Bundle not found")

    items_result = await db.execute(
        select(CuratedBundleItem).where(CuratedBundleItem.bundle_id == bundle_id)
    )
    items = items_result.scalars().all()

    approved_count = 0
    skipped_count = 0

    for item in items:
        existing = await db.execute(
            select(ApprovedIngredient).where(
                ApprovedIngredient.name == item.ingredient_name,
                ApprovedIngredient.ecosystem == item.ecosystem
            )
        )
        if existing.scalar_one_or_none():
            skipped_count += 1
            continue

        try:
            ingredient_in = ApprovedIngredientCreate(
                name=item.ingredient_name,
                version_constraint=item.version_constraint or "*",
                ecosystem=item.ecosystem,
                os_family=bundle.os_family,
                sha256=""
            )
            await SmelterService.add_ingredient(db, ingredient_in)
            approved_count += 1
        except Exception as e:
            logger.error(f"Failed to approve {item.ingredient_name}: {str(e)}")

    audit(db, current_user, "bundle:applied", f"{bundle.name} ({approved_count} new)")
    await db.commit()

    return {
        "bundle_id": bundle.id,
        "bundle_name": bundle.name,
        "approved": approved_count,
        "skipped": skipped_count,
        "total": len(items)
    }
```

### Starter Template Seeding (Startup)
```python
# Source: Phase 107 startup patterns (init_db) + Phase 110 seed patterns
async def seed_starter_templates(db: AsyncSession):
    """Seed 5 starter templates on first EE startup."""
    bundles = [
        {
            "name": "Python Data Science",
            "ecosystem": "PYPI",
            "os_family": "DEBIAN",
            "base_image": "debian:12-slim",
            "description": "Data analysis: numpy, pandas, scikit-learn, matplotlib"
        },
        {
            "name": "Web/API",
            "ecosystem": "PYPI",
            "os_family": "DEBIAN",
            "base_image": "debian:12-slim",
            "description": "FastAPI, Flask, Django, requests, SQLAlchemy"
        },
        {
            "name": "Network Tools",
            "ecosystem": "APT",
            "os_family": "DEBIAN",
            "base_image": "debian:12-slim",
            "description": "curl, nmap, tcpdump, iperf, netcat"
        },
        {
            "name": "File Processing",
            "ecosystem": "PYPI",
            "os_family": "DEBIAN",
            "base_image": "debian:12-slim",
            "description": "Pillow, pdf2image, python-docx, openpyxl"
        },
        {
            "name": "Windows Automation",
            "ecosystem": "NUGET",
            "os_family": "WINDOWS",
            "base_image": "mcr.microsoft.com/windows/servercore:ltsc2022",
            "description": "PowerShell modules, WMI, Active Directory"
        }
    ]

    for starter_def in bundles:
        # Check if starter already exists
        existing = await db.execute(
            select(PuppetTemplate).where(
                PuppetTemplate.friendly_name == starter_def["name"],
                PuppetTemplate.is_starter == True
            )
        )
        if existing.scalar_one_or_none():
            continue

        # Create starter template
        starter = PuppetTemplate(
            id=str(uuid4()),
            friendly_name=starter_def["name"],
            is_starter=True,
            status="ACTIVE",
            created_at=datetime.utcnow()
        )
        db.add(starter)
        await db.flush()

        # Create runtime blueprint with starter's packages
        # (Blueprint definition populated from matching bundle items)

    await db.commit()
```

### Starter Gallery (Frontend)
```typescript
// Source: Templates.tsx existing patterns (TemplateCard, Dialog)
export function StarterGallerySection({ starters }: { starters: Template[] }) {
  const [selectedStarter, setSelectedStarter] = useState<Template | null>(null);

  return (
    <div className="space-y-6">
      <div>
        <h3 className="text-lg font-semibold mb-4">Starter Templates</h3>
        <p className="text-sm text-muted-foreground mb-4">
          Pick a template and build a node image in 3 clicks — no configuration needed.
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {starters.map(starter => (
          <Card key={starter.id} className="hover:shadow-md transition-shadow">
            <CardHeader>
              <div className="flex items-center justify-between">
                <CardTitle className="text-base">{starter.friendly_name}</CardTitle>
                <Badge className="bg-blue-500/10 text-blue-500">Starter</Badge>
              </div>
              <CardDescription className="text-xs">
                {starter.description}
              </CardDescription>
            </CardHeader>
            <CardFooter className="flex gap-2">
              <Button
                size="sm"
                onClick={() => setSelectedStarter(starter)}
                className="flex-1"
              >
                Use This Template
              </Button>
            </CardFooter>
          </Card>
        ))}
      </div>

      {selectedStarter && (
        <UseTemplateDialog
          template={selectedStarter}
          isOpen={!!selectedStarter}
          onClose={() => setSelectedStarter(null)}
        />
      )}
    </div>
  );
}
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Manual ingredient selection | Curated bundles (Phase 114) | 2026-04-05 | Non-technical operators no longer need to know package names; bundles are curated by admins |
| Per-package approval | Bulk bundle approval | 2026-04-05 | 1-click approves 10+ packages; mirrors auto-trigger; operator feedback via toast + ingredient list |
| Custom blueprint creation required | Starter templates + "Build now" | 2026-04-05 | 3-click path: pick template → confirm → build. "Customize first" for advanced users |
| Separate template + bundle UX | Unified Foundry page | 2026-04-05 | Gallery at top of Templates tab; bundles + starters coexist |

**Deprecated/outdated:**
- None — Phase 114 is additive to existing Smelter/Foundry architecture

## Open Questions

1. **Exact bundle package contents**
   - What we know: 5 bundles, one per category (Data Science, Web/API, Network Ops, File Processing, Windows Automation)
   - What's unclear: Exact package list per bundle (e.g., numpy + pandas + scikit-learn for Data Science vs numpy + scipy + statsmodels?)
   - Recommendation: Research standard data science stack (numpy, pandas, scikit-learn, matplotlib); web stack (FastAPI, Flask, Django, SQLAlchemy); network tools (curl, nmap, tcpdump); file processing (Pillow, pdf2image, openpyxl). Propose in planning phase; allow feedback before finalizing.

2. **Base OS per starter**
   - What we know: Bundles have os_family (DEBIAN, ALPINE, WINDOWS)
   - What's unclear: Should all starters use latest-stable base image (debian:12, alpine:3.20, mcr.microsoft.com/windows/servercore:ltsc2022) or allow choice?
   - Recommendation: Lock base OS per starter (chosen during seeding). No OS choice in gallery UI. Operator customizes base OS in wizard if needed.

3. **Bundle admin UI layout**
   - What we know: CRUD endpoints exist; admin can add/edit/delete
   - What's unclear: Table vs cards? Inline edit vs modal forms? Pagination needed?
   - Recommendation: Simple table (name, description, ecosystem, os_family, item count, actions). Inline edit for quick changes. Modal for create + edit to support items sub-form.

4. **Estimated build time display**
   - What we know: "Build now" confirmation shows estimated time
   - What's unclear: How is it calculated? (hardcoded per ecosystem? based on package count? past builds?)
   - Recommendation: Hardcoded estimates per ecosystem: PyPI ~60s, APT ~30s, APK ~20s. Sum per starter. Show as "Est. 2–3 minutes" range.

5. **Bundle seeding: SQL migration vs startup code**
   - What we know: Need to seed bundles + items on first EE start
   - What's unclear: Migration file (migration_v*.sql) vs Python startup code in foundry_router init?
   - Recommendation: Both: migration creates tables (if first EE run), startup code idempotent-checks and seeds bundles. Allows offline deployment (migration pre-run) + dynamic updates.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (backend) + vitest (frontend) |
| Config file | puppeteer/conftest.py (pytest); puppeteer/dashboard/vitest.config.ts (vitest) |
| Quick run command | `cd puppeteer && pytest tests/test_smelter.py -k bundle -x` |
| Full suite command | `cd puppeteer && pytest tests/test_smelter.py && cd dashboard && npm run test` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| UX-02 | Operator can apply bundle; ingredients approved + mirror auto-triggers | integration | `pytest tests/test_smelter.py::test_bundle_apply_bulk_approval -x` | ❌ Wave 0 |
| UX-02 | Bundle apply toast shows correct counts (approved + skipped) | unit | `pytest tests/test_smelter.py::test_bundle_apply_feedback_message -x` | ❌ Wave 0 |
| UX-02 | Already-approved packages silently skipped on duplicate apply | integration | `pytest tests/test_smelter.py::test_bundle_apply_duplicate_skip -x` | ❌ Wave 0 |
| UX-02 | Bundle with mixed ecosystems auto-resolves per ecosystem | integration | `pytest tests/test_smelter.py::test_bundle_mixed_ecosystem_resolve -x` | ❌ Wave 0 |
| UX-02 | Requires `foundry:write` permission; viewer/operator roles blocked | unit | `pytest tests/test_smelter.py::test_bundle_apply_permission_gate -x` | ❌ Wave 0 |
| UX-03 | 5 starter templates seeded on first EE startup | integration | `pytest tests/test_foundry.py::test_starter_templates_seeded -x` | ❌ Wave 0 |
| UX-03 | Starter template has `is_starter=true`; delete blocked client + server-side | unit | `pytest tests/test_foundry.py::test_starter_immutability -x` | ❌ Wave 0 |
| UX-03 | "Use This Template" → "Build now" triggers template build directly | integration | `vitest run src/views/__tests__/Templates.test.tsx -t "build now" -x` | ❌ Wave 0 |
| UX-03 | "Use This Template" → "Customize first" clones template + opens wizard | integration | `vitest run src/views/__tests__/Templates.test.tsx -t "customize first" -x` | ❌ Wave 0 |
| UX-03 | Build confirmation shows package count by ecosystem | unit | `vitest run src/components/__tests__/BuildConfirmationDialog.test.tsx -x` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `pytest tests/test_smelter.py::test_bundle_apply_bulk_approval -x` (quick validate)
- **Per wave merge:** `cd puppeteer && pytest tests/test_smelter.py && cd dashboard && npm run test` (full suite)
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_smelter.py` — bundle CRUD + apply tests (covers UX-02)
- [ ] `tests/test_foundry.py` — starter template seeding + immutability tests (covers UX-03)
- [ ] `dashboard/src/views/__tests__/Templates.test.tsx` — gallery UI + dialog interaction tests (covers UX-03)
- [ ] `dashboard/src/components/__tests__/UseTemplateDialog.test.tsx` — "Build now" vs "Customize first" logic (covers UX-03)
- [ ] `dashboard/src/components/__tests__/BuildConfirmationDialog.test.tsx` — package count display (covers UX-03)
- [ ] Framework install: already in place (pytest + vitest)

## Sources

### Primary (HIGH confidence)
- Phase 107 RESEARCH.md — CuratedBundle/CuratedBundleItem models, schema design
- Phase 108 RESEARCH.md — ResolverService.resolve_ingredient_tree() + MirrorService integration patterns
- Existing codebase: `puppeteer/agent_service/db.py` (CuratedBundle model at line 329), `smelter_service.py` (add_ingredient method at line 16), `foundry_router.py` (template creation pattern)
- CONTEXT.md decisions — locked implementation approach (5 bundles, bulk approval, starter seeding)

### Secondary (MEDIUM confidence)
- Phase 113 RESEARCH.md — analyzer_service patterns for reusable service architecture
- Existing test patterns: `puppeteer/tests/test_smelter.py` (mocking + integration test examples)
- React Query patterns: `puppeteer/dashboard/src/views/Templates.tsx` (useQuery/useMutation, toast feedback)

### Tertiary (LOW confidence)
- None — all findings verified against codebase or prior phase research

## Metadata

**Confidence breakdown:**
- Standard stack: **HIGH** — All dependencies (SQLAlchemy, FastAPI, Pydantic, React Query) already in codebase; no new packages needed
- Architecture: **HIGH** — Patterns verified in Phase 107-108 code; bundle application is straightforward smelter_service loop
- Pitfalls: **HIGH** — Identified from experience with bulk operations in Phase 108-109
- Bundle contents: **MEDIUM** — Package lists deferred to planning phase; recommendation provided but not finalized
- Estimated build time: **MEDIUM** — Calculation method deferred to planning; hardcoded estimates recommended

**Research date:** 2026-04-05
**Valid until:** 2026-05-05 (30 days — stable domain, no breaking changes expected in Smelter/Foundry stack)

---

*Phase: 114-curated-bundles-starter-templates*
*Research completed: 2026-04-05*
*Requirements addressed: UX-02, UX-03*
