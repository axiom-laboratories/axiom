# Phase 113: Script Analyzer - Context

**Gathered:** 2026-04-04
**Status:** Ready for planning

<domain>
## Phase Boundary

Operators can paste a script and get automatic package suggestions without knowing package names or ecosystems. Detected packages are cross-referenced against already-approved ingredients, and unapproved packages enter a review queue for admin/operator approval. This phase covers the analyzer service, the results UI, and the approval queue. Curated bundles and starter templates are Phase 114.

</domain>

<decisions>
## Implementation Decisions

### Suggestion presentation
- Grouped table by ecosystem (Python, APT, npm, etc.)
- Each row shows: package name, detected import/command, confidence indicator, and status badge (Approved/New/Pending)
- Fuzzy/mapped matches (e.g. `import cv2` -> `opencv-python`) get a subtle indicator or tooltip explaining the mapping
- Already-approved packages shown greyed out with green "Approved" badge, not selectable
- Approved packages also show which blueprint(s) include them (e.g. "Used in: Python-DataSci, Network-Tools")
- Approved packages show node availability as a count badge ("2 nodes ready") with click/hover to expand node names
- Stdlib modules silently excluded from results (never shown)
- Checkboxes for bulk selection of new packages, "Select all new" convenience toggle
- "Approve Selected" button for admin/operator; "Request Approval" button for users without foundry:write

### Analysis trigger & flow
- New "Analyzer" sub-section/card in the Smelter tab of Foundry (alongside Approved Ingredients)
- Dedicated textarea for pasting scripts
- Language auto-detected from shebang line, syntax patterns, or content heuristics
- Language dropdown shows detected result but allows operator override
- Analysis triggered by explicit "Analyze Script" button click (no auto-analyze on paste)
- Results table appears below the paste area after analysis completes

### Import-to-package mapping
- **Python**: AST-based parsing for imports. Static mapping dict (~200 entries) for import-name != package-name cases (cv2->opencv-python, PIL->Pillow, yaml->PyYAML, sklearn->scikit-learn, etc.). Fallback: check configured PyPI mirror URL (from Admin mirror config) for unresolved imports. If not found in mirror or approved list, flag as "Unknown -- request approval"
- **Bash**: Regex for package manager commands only: `apt-get install`, `apt install`, `yum install`, `dnf install`, `apk add`, `pip install`. No binary detection (kept simple, low false-positive)
- **PowerShell**: Regex for `Import-Module`, `Install-Module`, and `Install-Package`. Map to NuGet/PSGallery ecosystem

### Approval queue
- Non-admin operators can request approval for unapproved packages detected by the analyzer
- Pending requests stored with full traceability: requested_by (user ID), source_script (hash or snippet of originating script), requested_at (timestamp), detected_import (the original import/command line)
- Separate "Review Queue" tab/page for admins to review pending requests
- Admin/operator with `foundry:write` permission can approve or reject from the queue
- On approve: ingredient becomes active and transitive dependency resolution auto-triggers (existing resolver_service + mirror_service flow from Phase 108)
- On reject: request removed (or marked rejected) with optional reason

### Access control
- Script analysis endpoint: accessible to all authenticated users (viewer, operator, admin) -- analysis is read-only
- "Request Approval" action: requires operator+ permission
- "Approve/Reject" from review queue: requires `foundry:write` permission
- Direct "Approve Selected" (skip queue): requires `foundry:write` permission

### Claude's Discretion
- Exact Python stdlib module list (can be derived from `sys.stdlib_module_names`)
- Static import mapping dict contents and structure
- Language auto-detection heuristics implementation
- Review queue DB schema design (new table vs status column on ApprovedIngredient)
- Review queue page layout and filtering
- How to query node capabilities for the "nodes ready" badge
- Blueprint cross-reference query approach
- Error handling for malformed scripts

</decisions>

<specifics>
## Specific Ideas

- The analyzer should feel like a discovery surface: "paste your script, see what's available, what's missing, and where it already runs"
- For unresolved Python imports: check static mapping -> check local mirror -> check approved ingredients -> if still unknown, flag for approval request
- The review queue enables a separation of concerns: operators discover what they need, admins control what's allowed
- Node availability display gives operators immediate visibility into whether they can run their script NOW or need to build a new image

</specifics>

<code_context>
## Existing Code Insights

### Reusable Assets
- `SmelterIngredientSelector` component (`dashboard/src/components/SmelterIngredientSelector.tsx`): existing ingredient addition UI in Smelter tab -- new Analyzer panel sits alongside it
- `ApprovedIngredient` model (`agent_service/db.py`): has ecosystem column (PYPI, APT, APK, OCI, NPM, CONDA, NUGET), is_active flag, and existing CRUD endpoints
- `resolver_service.py`: transitive dependency resolution -- auto-triggers on ingredient approval
- `mirror_service.py`: mirrors packages for all ecosystems -- integrates with resolver on approval
- `smelter_service.add_ingredient()`: existing flow for adding ingredients with auto-mirror trigger
- Admin mirror config (`GET /api/admin/mirror-config`): provides PYPI_MIRROR_URL for fallback lookups

### Established Patterns
- EE routers in `agent_service/ee/routers/` with permission decorators (`require_permission`)
- `audit()` helper for security-relevant mutations
- `tabs.tsx` component for tab navigation within Foundry page
- `authenticatedFetch()` for all frontend API calls
- Toast notifications for success/error feedback
- Query/mutation pattern with React Query (`useQuery`, `useMutation`)

### Integration Points
- Smelter tab in Templates.tsx: new Analyzer sub-section added here
- `smelter_router.py` (EE): new POST endpoint for script analysis
- `approved_ingredients` table: cross-reference results against existing ingredients
- `puppet_templates` table: cross-reference for "used in blueprint" display
- Node heartbeat data (capabilities): query for "nodes ready" badge
- Existing RBAC: `foundry:write` for approval actions, `foundry:read` for analysis access

</code_context>

<deferred>
## Deferred Ideas

None -- discussion stayed within phase scope

</deferred>

---

*Phase: 113-script-analyzer*
*Context gathered: 2026-04-04*
