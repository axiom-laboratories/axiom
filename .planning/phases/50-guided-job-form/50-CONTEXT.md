# Phase 50: Guided Job Form - Context

**Gathered:** 2026-03-23
**Status:** Ready for planning

<domain>
## Phase Boundary

Replace the current raw-JSON dispatch card in Jobs.tsx with a structured guided form that builds the job payload from discrete fields. Operators can switch to Advanced (raw JSON) mode via a one-way confirmation gate. No new job capabilities — this is a submission UX improvement over the existing dispatch form.

</domain>

<decisions>
## Implementation Decisions

### Form layout & structure
- Guided form **replaces the existing dispatch card in-place** — no modal or sheet; the current "Configure a manual orchestration payload" card becomes the guided form
- **Single-page layout**: all fields visible at once — Name, Runtime, Script content, Targeting section, Sign section, Dispatch button
- An `[ADV]` button in the card header provides access to Advanced mode
- **JSON preview**: collapsible `[▼ Generated Payload]` accordion below the form fields; closed by default; updates live as fields are filled

### Signing UX
- Signature fields are **inline in the guided form** (same as current raw form) — no separate signing step or dialog
- **Key ID field is a dropdown** populated from `GET /signatures` — operator selects a registered key; `signature_id` is set automatically
- **Signature field**: freeform text input for the Ed25519 signature string
- **Dispatch button is disabled** until both `signature_id` and `signature` are non-empty
- If the **script content changes after a signature has been pasted**: signature fields are cleared and an amber inline warning appears — "Script changed — re-sign required." Prevents dispatch with a stale signature.

### Target & routing fields
- A unified **"Targeting" section** contains three fields:
  1. **Node dropdown** (optional): populated from live node list; operator can target a specific node
  2. **Target tag chips** (chip input): autocomplete suggestions fetched from distinct `target_tags` on registered nodes; freeform typing also allowed
  3. **Capability tag chips** (chip input): freeform type-and-add; no server-side autocomplete
- **At least one targeting field is required** before the Dispatch button is enabled — operator must select a node or add at least one tag or capability chip before dispatch is permitted
- Chip interaction: type value → press Enter or comma to add; click chip `×` to remove

### Advanced mode gate
- **Trigger**: `[ADV]` button in the top-right of the card header
- **Confirmation dialog** text: "Switch to Advanced mode? Your current form values will be converted to JSON. You won't be able to switch back without clearing the form." Buttons: **Cancel** | **Switch to Advanced**
- **Pre-fill behaviour**: on switching, current guided form values are serialised into the JSON editor — operator sees the JSON they were about to submit
- **Return to guided mode**: a "Reset form" (or "← Guided") button appears in Advanced mode; clicking shows: "Clear the JSON editor and return to guided mode?" Buttons: Cancel | Reset. Resets to a blank guided form.
- **Advanced mode JSON validation** (client-side, required fields only before Dispatch is enabled):
  - JSON must parse without errors
  - Must contain `task_type: "script"`, a `payload` object, and a `runtime` field
  - Dispatch button shows "Fix JSON errors" tooltip if validation fails

### Claude's Discretion
- Exact chip component implementation (reuse Phase 49 filter chip pattern vs standalone)
- Whether the collapsible JSON preview uses a Radix Collapsible or a simple toggle state
- Exact layout/spacing of the Targeting section and Sign section within the single-page form
- Autocomplete dropdown behaviour (debounce, min-chars, empty state)
- Whether targeting requirement validation shows inline field error or disables the Dispatch button with a tooltip

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `Jobs.tsx` existing dispatch state: `capabilityReqs`, `dispatchTargetTags`, `newTaskPayload`, `payloadError` — these map directly to the new guided form fields; guided form replaces and extends them
- `Jobs.tsx` node selector: already fetches node list and renders a node dropdown for the dispatch form — reuse for the targeting node dropdown
- Phase 49 filter chip pattern in `Jobs.tsx`: chip add/remove interaction for filter bar already implemented — reuse the same chip component for target tag and capability chips
- `GET /signatures` (Signatures view): already fetched in `Signatures.tsx`; add the same fetch to the guided form for the Key ID dropdown
- Radix `Select` component (from Phase 46 via `select.tsx`): used for runtime selector in Phase 47 — reuse for node dropdown and Key ID dropdown
- `JobDefinitionModal.tsx`: has existing `signature_id` + `signature` inline fields pattern — reference for signing section layout

### Established Patterns
- Chip input: tag chips with `×` remove and Enter/comma add — already built for Phase 49 filter bar
- Amber inline warning: amber text below a field with icon — used in Phase 48 DRAFT warning and Foundry stale badge
- Disabled button with tooltip: Dispatch button disabled until preconditions met — consistent with "Re-sign" button gating in Phase 48
- Collapsible/accordion: Radix Collapsible already available in the component library
- `authenticatedFetch()` in `src/auth.ts`: all API calls go through this

### Integration Points
- `Jobs.tsx` dispatch card: replace the raw `<textarea>` JSON block and current tag/capability text inputs with the new guided form fields
- `GET /nodes` (already called in Jobs.tsx): reuse for node dropdown in Targeting section
- `GET /signatures`: add fetch to Jobs.tsx for Key ID dropdown
- `POST /jobs` (existing dispatch endpoint): no backend changes needed — guided form constructs the same `JobCreate` payload as the raw form; Advanced mode sends the edited JSON directly
- Phase 47 runtime selector (already in Jobs.tsx): the guided form supersedes the stopgap runtime dropdown added in Phase 47 — remove the Phase 47 control and integrate runtime into the guided form's Runtime field

</code_context>

<specifics>
## Specific Ideas

- The `[ADV]` button should be visually subtle (small, muted) so it's not the first thing operators reach for — the guided form is the intended default path
- "At least one targeting field required" — the job should never silently broadcast to all nodes without the operator making an explicit choice; this is a safety guardrail given the production nature of the platform
- Pre-filling Advanced mode with the guided form's JSON removes the "blank editor" friction — operators who switch to Advanced usually do so to add a field not in the form, not to start from scratch

</specifics>

<deferred>
## Deferred Ideas

- None — discussion stayed within phase scope

</deferred>

---

*Phase: 50-guided-job-form*
*Context gathered: 2026-03-23*
