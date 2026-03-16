# Phase 19 Context: Dashboard Staging View & Governance Doc

## Phase Goal
Provide UI visibility for staged jobs (DRAFTs), allow script inspection, finalize scheduling, and publish to ACTIVE. Additionally, document the OIDC v2 integration path and specify the OAuth device flow contract.

## Requirements (from ROADMAP.md)
- **DASH-01**: Dashboard Staging/Drafts view listing all DRAFT job definitions.
- **DASH-02**: Read-only script inspection view for draft jobs.
- **DASH-03**: Finalize cron and tags for draft jobs from dashboard.
- **DASH-04**: "Publish" button to transition DRAFT -> ACTIVE.
- **DASH-05**: Status badges (DRAFT/ACTIVE/DEPRECATED/REVOKED) on all jobs.
- **GOV-CLI-02**: Architecture doc for OIDC v2 integration path.

## Research Findings
- `JobDefinitions.tsx` manages the main job list.
- `JobDefinitionList.tsx` handles the rendering of the table.
- Backend `JobDefinitionResponse` already includes `status` and `pushed_by`.
- Need to implement a tabbed interface or separate section for Staging.
- Script content is available in the job definition but not currently displayed in the list.

## Implementation Waves
1. **Wave 1: UI Foundation**: Update `JobDefinition` interface, add status badges to `JobDefinitionList`, and implement tabbed view in `JobDefinitions.tsx`.
2. **Wave 2: Staging Features**: Implement script inspection modal/view and "Publish" logic (transition DRAFT -> ACTIVE).
3. **Wave 3: Governance Documentation**: Create the OIDC v2 integration architecture document.
4. **Wave 4: Verification**: Verify UI interactions and document completeness.
