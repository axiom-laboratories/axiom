# Phase 114: Curated Bundles + Starter Templates - Context

**Gathered:** 2026-04-05
**Status:** Ready for planning

<domain>
## Phase Boundary

Non-developer operators can build node images by picking from pre-built bundles and starter templates instead of manually selecting individual packages. Covers: curated bundle definitions, bundle application flow, starter template seeding, template gallery UI, and the 3-click operator path from gallery pick to built image. Script analysis is Phase 113. UX polish is deferred to v20.0.

</domain>

<decisions>
## Implementation Decisions

### Bundle content & categories
- 5 focused bundles ship by default: Data Science, Web/API, Network Ops, File Processing, Windows Automation
- Bundles are mixed-ecosystem: a single bundle can include PyPI, APT, and other ecosystem packages (e.g. Data Science includes numpy + libopenblas)
- CuratedBundleItem gets an ecosystem column per item (existing CuratedBundle.ecosystem column becomes the primary ecosystem)
- No version pins on bundle items — package names only, transitive resolver picks latest compatible versions at approval time
- Admin-curated only: admins can add/edit/delete bundles from admin UI. Operators consume bundles, they don't create them

### Bundle application flow
- One-click bulk-approve: applying a bundle approves all its packages as ingredients immediately (skips review queue)
- Already-approved packages are silently skipped
- Transitive dependency resolution auto-triggers for each newly approved package (existing Phase 108 flow)
- Applying a bundle only approves ingredients — does NOT auto-create a blueprint. Operator uses ingredients in wizard or via starter templates
- Requires `foundry:write` permission (consistent with individual ingredient approval)
- Feedback: immediate toast ("Applying Data Science bundle (12 packages)...") then packages appear in ingredient list as they're approved. Mirror status shown on each ingredient card (existing mirror_status field). No blocking modal

### Starter templates & gallery
- 5 starter templates seeded on first EE startup, one per curated bundle: Python Data Science, Web/API, Network Tools, File Processing, Windows Automation
- Each starter pre-configured with its bundle's packages + appropriate base OS
- Gallery cards displayed in a "Starter Templates" section at the top of the existing Node Images tab, above custom templates
- Each starter card shows: name, description, package count, and "Use This Template" button
- Starter cards have a "Starter" badge and cannot be deleted (only hidden)
- Custom/user-created templates listed in "Your Node Images" section below
- Clicking "Use This Template" shows a dialog with two options: "Build now" or "Customize first"
  - "Build now": triggers build with starter's exact config (3-click path)
  - "Customize first": clones starter into a new editable PuppetTemplate, opens in blueprint wizard for review/customization

### Non-developer operator path
- 3-click path: (1) Click "Use This Template" on starter card, (2) Dialog: "Build now" or "Customize", (3) Click "Build now"
- "Build now" confirmation dialog shows a summary card: template name, base OS, package count by ecosystem (e.g. "8 Python, 3 APT"), estimated build time. Single "Build" button
- If starter's packages aren't yet approved/mirrored: auto-approve + mirror + build in a single flow (requires foundry:write). No manual prerequisite steps
- Bundles and starter templates live in Foundry page only — no Dashboard shortcuts for now

### Claude's Discretion
- Exact package lists for each of the 5 bundles (research phase can determine optimal packages)
- Base OS choices per starter template (Debian vs Alpine)
- Bundle admin CRUD UI layout (table vs cards)
- Gallery card styling and icons
- How "estimated build time" is calculated or displayed
- Bundle seeding mechanism (SQL migration vs startup code)
- Whether starters are stored as regular PuppetTemplate rows with an is_starter flag or a separate table

</decisions>

<specifics>
## Specific Ideas

- The gallery should feel like an app store for node images: browse, pick, go. Non-technical operators should never need to know individual package names
- "Build now" path is the hero flow — it should be prominent and feel like the default action
- "Customize first" is the escape hatch for operators who want to tweak before building
- Mixed-ecosystem bundles are important because real-world node images always need system libraries alongside Python packages

</specifics>

<code_context>
## Existing Code Insights

### Reusable Assets
- `CuratedBundle` + `CuratedBundleItem` DB models (db.py:329-348): already exist with id, name, description, ecosystem, os_family, is_active. Items have bundle_id, ingredient_name, version_constraint
- `PuppetTemplate` model (db.py:258): existing template entity — starters can be flagged with is_starter column or similar
- `TemplateCard` component (Templates.tsx:100): existing card pattern for displaying templates — reuse for starter gallery
- `BlueprintWizard` component: existing wizard for blueprint customization — "Customize first" opens this
- `smelter_service.add_ingredient()`: existing ingredient approval + auto-mirror trigger — bundle application calls this per package
- `resolver_service.resolve_ingredient_tree()`: transitive resolution — auto-triggered on ingredient approval

### Established Patterns
- EE DB models in db.py extending Base, Pydantic models in models.py
- EE routers in `agent_service/ee/routers/` with `require_permission` decorators
- `audit()` helper for security-relevant mutations
- `tabs.tsx` component for tab navigation in Foundry page
- React Query `useQuery`/`useMutation` for data fetching
- Toast notifications for success/error feedback
- Existing TemplateCard pattern with build/delete actions and status badges

### Integration Points
- Node Images tab in Templates.tsx: add "Starter Templates" section above existing template cards
- `smelter_router.py` or new `bundles_router.py`: CRUD endpoints for bundles + apply endpoint
- `foundry_router.py`: starter template seeding at EE startup
- CuratedBundle/CuratedBundleItem tables: populate with seed data
- PuppetTemplate table: add is_starter flag or equivalent for starter identification

</code_context>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 114-curated-bundles-starter-templates*
*Context gathered: 2026-04-05*
