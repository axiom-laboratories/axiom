# Phase 101: CE UX Cleanup - Context

**Gathered:** 2026-03-31
**Status:** Ready for planning

<domain>
## Phase Boundary

Clean up the Admin settings page for CE users: remove EE-only tabs from the tab bar, replace them with a single "Enterprise" tab showing an upgrade panel, and verify no dashboard route renders blank in CE mode. No new features, no backend changes.

</domain>

<decisions>
## Implementation Decisions

### Tab visibility
- Remove the 6 EE-only tabs entirely from the Admin TabsList in CE mode: Smelter Registry, BOM Explorer, Tools, Artifact Vault, Rollouts, Automation
- CE user sees a clean tab bar: `[ Onboarding ] [ Data ] [ + Enterprise ]`
- Detection signal: `useLicence().isEnterprise` — already imported in Admin.tsx, no new flags needed

### Upgrade tab
- Add a single `+ Enterprise` tab at the right end of the TabsList (CE only)
- Clicking it shows a shared upgrade panel listing the 6 features unlocked by EE: Smelter Registry, BOM Explorer, Tools, Artifact Vault, Rollouts, Automation
- Use the existing `UpgradePlaceholder` component styled to list the 6 features — consistent with how Templates, AuditLog, and Users gate EE content

### Black page coverage (CEUX-03)
- Webhooks, ServicePrincipals, and History routes already gate via `useFeatures()` + `UpgradePlaceholder` — no gaps found
- The only CE black-page risk was the Admin EE tabs, which this phase resolves
- No changes needed to AppRoutes.tsx or any other view

### Tests
- Update `Admin.test.tsx` to assert CE behaviour: EE tabs absent, `+ Enterprise` tab present
- Existing mock setup (`mockUseLicence`) already supports adding a CE test case

### Claude's Discretion
- Exact label/icon for the `+ Enterprise` tab trigger
- Whether the Enterprise tab content uses `UpgradePlaceholder` directly or a bespoke inline panel
- Ordering and visual grouping of the 6 EE features listed in the upgrade panel

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `useLicence()` (hooks/useLicence.ts): `isEnterprise` boolean — already imported in Admin.tsx, use to gate tab rendering
- `UpgradePlaceholder` (components/UpgradePlaceholder.tsx): lock icon + "Enterprise Edition Required" + feature name + description + "Learn More" link — reuse for the Enterprise tab panel
- `Admin.test.tsx`: already mocks `useLicence` with `mockUseLicence` — extend with a CE test case

### Established Patterns
- Tab gating in CE mode: conditional rendering of `TabsTrigger` + `TabsContent` based on `isEnterprise`
- Route-level gating: `XxxWithFeatureCheck` wrapper — already used in Templates, AuditLog, Users, Webhooks, ServicePrincipals, History
- Radix Tabs: `defaultValue="onboarding"` — no URL-based tab routing, so removed tabs can't be deep-linked to

### Integration Points
- `Admin.tsx` TabsList (line ~1450): add `isEnterprise` conditional around the 6 EE `TabsTrigger` elements; add `+ Enterprise` trigger + TabsContent after them
- `Admin.test.tsx`: add CE licence mock scenario asserting tab visibility

</code_context>

<specifics>
## Specific Ideas

- Tab bar in CE: `[ Onboarding ] [ Data ] [ + Enterprise ]` — the Enterprise tab sits at the right end, visually distinct
- The Enterprise panel should list what each of the 6 removed tabs unlocks (not just a generic message)

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 101-ce-ux-cleanup*
*Context gathered: 2026-03-31*
