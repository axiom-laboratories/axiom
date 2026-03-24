---
phase: 50-guided-job-form
verified: 2026-03-23T13:10:00Z
status: human_needed
score: 9/9 must-haves verified
re_verification: false
human_verification:
  - test: "Open Jobs view in the running dashboard, confirm the raw-JSON dispatch card is gone and the guided form is shown"
    expected: "Form shows Name, Runtime selector, Script textarea, Targeting section (node dropdown + tag chips + capability chips), Sign section (Key ID dropdown + signature textarea), Generated Payload accordion, Dispatch Payload button"
    why_human: "DOM rendering and visual layout cannot be confirmed via unit tests alone; needs the full Docker stack"
  - test: "Add a target tag and fill both signing fields; verify Dispatch button enables"
    expected: "Button transitions from disabled to enabled state only when targeting is set AND both signatureId and signature are non-empty"
    why_human: "Radix Select value-setting via JSDOM is unreliable; the test confirms the guard logic but Key ID selection via UI was not exercisable in JSDOM"
  - test: "Click [ADV], cancel, then click [ADV] again and confirm; verify the JSON textarea is pre-populated with the guided form values"
    expected: "Cancel leaves guided form unchanged; confirm switches to JSON editor showing the serialised payload"
    why_human: "End-to-end Radix Dialog dismiss animation and state preservation need visual confirmation"
  - test: "In Advanced mode, enter invalid JSON; verify inline error message and disabled Dispatch button with tooltip on hover"
    expected: "Red error text below textarea; button disabled; hovering shows error text in tooltip"
    why_human: "Radix Tooltip hover behaviour requires pointer events not available in JSDOM"
  - test: "In Advanced mode, click '← Guided', confirm Reset; verify form returns to blank state"
    expected: "Guided form fields show blank/default values; ADV button visible again; JSON textarea gone"
    why_human: "Full reset flow needs visual verification in running app"
---

# Phase 50: Guided Job Form — Verification Report

**Phase Goal:** Replace the raw-JSON dispatch card with a guided, field-by-field job form so operators can dispatch jobs without manually constructing JSON. The form must include a read-only live JSON preview and an escape-hatch Advanced mode that exposes the raw JSON editor with schema validation.
**Verified:** 2026-03-23T13:10:00Z
**Status:** human_needed
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Operator sees a guided form (Name, Runtime, Script, Targeting, Sign, Dispatch button) replacing the raw-JSON card | VERIFIED | `GuidedDispatchCard.tsx` renders all sections; `Jobs.tsx` mounts it in place of old card; old dispatch state vars (`newTaskPayload`, etc.) not present in `Jobs.tsx` |
| 2 | Dispatch button is disabled until targeting AND signature fields are set | VERIFIED | `canDispatch` condition verified; test "Dispatch button is disabled when no targeting field is provided" passes; "enabled when target tag + signature" test confirms guard logic |
| 3 | Script change after signature is entered clears signature fields and shows amber warning | VERIFIED | `prevScriptRef` + `useEffect` on `scriptContent`; test "shows amber warning and clears signature fields" passes (11/11 green) |
| 4 | JSON preview accordion is collapsed by default and updates live | VERIFIED | `previewOpen` state initialised `false`; `generatedPayload` useMemo; tests for JOB-02 both pass |
| 5 | Node dropdown is populated from the `nodes` prop (no duplicate API call) | VERIFIED | Props: `nodes: NodeItem[]`; no `GET /nodes` inside component; `fetchNodes` in `Jobs.tsx` provides the prop |
| 6 | Key ID dropdown is populated from GET /signatures | VERIFIED | `useEffect` on mount calls `authenticatedFetch('/signatures')`; sets `signatures` state; mapped into Select items |
| 7 | Target tag and capability chips support Enter/comma-to-add and × to remove | VERIFIED | `onKeyDown` handler checks `e.key === 'Enter' || e.key === ','`; `removeTargetTag` / `removeCapReq` callbacks present |
| 8 | ADV button shows confirmation dialog; confirming serialises form to JSON editor; reset returns to blank guided form | VERIFIED | `pendingAdvSwitch` / `pendingAdvReset` Dialog pattern; `handleSwitchToAdvanced` / `handleResetToGuided`; all 4 JOB-03 tests pass |
| 9 | Advanced mode dispatch button is disabled when JSON is invalid; schema checks task_type/payload/runtime | VERIFIED | `advancedJsonError` useMemo implements exact schema from plan; `canDispatch` branches on `advancedMode`; Radix Tooltip wraps disabled button |

**Score:** 9/9 truths verified

---

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `puppeteer/dashboard/src/views/__tests__/Jobs.test.tsx` | Wave 0 TDD scaffold + full test implementations | VERIFIED | 319 lines; 11 tests all pass; imports `GuidedDispatchCard` directly |
| `puppeteer/dashboard/src/components/GuidedDispatchCard.tsx` | Self-contained guided form component | VERIFIED | 608 lines; exports `GuidedDispatchCard`; all form sections, dialogs, tooltip present |
| `puppeteer/dashboard/src/views/Jobs.tsx` | Updated Jobs view mounting GuidedDispatchCard | VERIFIED | Imports and mounts `<GuidedDispatchCard nodes={nodes} onJobCreated=...>`; no old dispatch state remains |

---

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `Jobs.tsx` | `GuidedDispatchCard.tsx` | import + `<GuidedDispatchCard nodes={nodes} onJobCreated={...}>` | WIRED | Line 49 import; line 746 JSX mount |
| `GuidedDispatchCard.tsx` | `POST /api/jobs` | `authenticatedFetch('/jobs', { method: 'POST', ... })` in `handleDispatch` | WIRED | Line 222; dispatches `generatedPayload` or `JSON.parse(advancedJson)` depending on mode |
| `GuidedDispatchCard.tsx` | `GET /api/signatures` | `authenticatedFetch('/signatures')` on mount in `useEffect` | WIRED | Line 95; populates `signatures` state for Key ID dropdown |
| `GuidedDispatchCard.tsx` | Radix Dialog | `pendingAdvSwitch` / `pendingAdvReset` control `Dialog open` prop | WIRED | Lines 571, 587; two Dialog instances as specified |
| `GuidedDispatchCard.tsx` | `advancedJsonError` useMemo | `canDispatch` check uses `advancedJsonError === null` in advanced mode | WIRED | Lines 156–167, 171–173 |

---

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| JOB-01 | 50-01, 50-02 | Operator can submit a job using a structured guided form | SATISFIED | All 5 JOB-01 test stubs pass; component renders all required fields |
| JOB-02 | 50-01, 50-02 | Operator can view generated JSON payload in a read-only panel | SATISFIED | Both JOB-02 tests pass; `previewOpen` accordion with read-only `<pre>` block |
| JOB-03 | 50-01, 50-03 | Operator can switch to Advanced mode via one-way gate with confirmation; JSON schema validation before submission | SATISFIED | All 4 JOB-03 tests pass; two confirmation dialogs, `advancedJsonError` validation, Tooltip-guarded disabled button |

All 3 requirement IDs declared in plan frontmatter are accounted for. No orphaned requirements: REQUIREMENTS.md marks JOB-01, JOB-02, and JOB-03 as `[x]` (satisfied).

---

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `GuidedDispatchCard.tsx` | 124–125 | `void tagSuggestions` suppressor for an unused computed value | Info | `tagSuggestions` is computed but silenced with `void` — the computed value is never rendered. Not a goal blocker; comment says "used in future datalist". Low impact. |
| `GuidedDispatchCard.tsx` | 241 | `console.error(e)` in dispatch error catch | Info | Debugging aid in error path. Not a stub; error is also surfaced to user via `toast.error`. |

No blockers or warnings found. The `return null` hits at lines 157/163 are valid sentinel values in `advancedJsonError` useMemo, not stubs.

---

### TypeScript and Lint Status

- `npm run lint`: **ok (no errors)**
- `npx tsc --noEmit`: No errors in any phase-50 files. Pre-existing TS errors exist in unrelated files (`ExecutionLogModal.tsx`, `Dashboard.tsx`, `Account.tsx`, etc.) — all pre-date this phase and are not regressions.
- Full test suite: **39/39 passing** (8 test files)

---

### Human Verification Required

The automated checks are fully green. The following items need human verification in the running Docker stack because they involve visual rendering, Radix UI pointer behaviour, and end-to-end form interaction that JSDOM cannot reliably simulate.

#### 1. Guided form renders correctly in the running app

**Test:** Open the Jobs view in the dashboard. Confirm the old raw-JSON "Configure a manual orchestration payload" card is gone and the guided "Dispatch Job" form is in its place.
**Expected:** Form shows Name input, Runtime selector (python/bash/powershell), Script textarea, Targeting section (node dropdown + target tag chips + capability chips), Sign section (Key ID dropdown + signature textarea), "Generated Payload" collapsible accordion, Dispatch Payload button.
**Why human:** Visual layout and CSS classes cannot be confirmed by unit tests.

#### 2. Dispatch button enables after filling required fields

**Test:** Add a target tag (type a tag name, press Enter), select a Key ID from the dropdown, paste a signature value.
**Expected:** Dispatch Payload button transitions from disabled (greyed) to enabled.
**Why human:** Radix Select component value-setting in JSDOM is unreliable — the Key ID selection step was not exercisable in the unit tests.

#### 3. ADV dialog cancel and confirm flow

**Test:** Click `[ADV]`, then click Cancel. Confirm guided form state is unchanged. Click `[ADV]` again, fill a job name, then click "Switch to Advanced". Verify the JSON textarea shows the guided form values as serialised JSON.
**Expected:** Cancel closes dialog with no side effects; confirm pre-fills textarea with `task_type`, `runtime`, `payload`, and any set fields.
**Why human:** Radix Dialog animation and state transitions need visual confirmation.

#### 4. Advanced mode tooltip on disabled Dispatch button

**Test:** In Advanced mode, type invalid text (e.g. `{bad json`) in the JSON textarea. Hover over the disabled Dispatch Payload button.
**Expected:** A tooltip appears showing the error message (e.g. "Invalid JSON").
**Why human:** Radix Tooltip requires pointer events not available in JSDOM.

#### 5. Reset-to-guided full flow

**Test:** Switch to Advanced mode, then click "← Guided", then "Reset" in the confirmation dialog.
**Expected:** Guided form reappears with all fields blank; `[ADV]` button is visible again; JSON textarea is gone.
**Why human:** Full multi-dialog reset flow needs visual confirmation that state is fully cleared.

---

### Gaps Summary

None. All automated checks pass. The phase goal is achieved in the codebase. The items above are standard human-verification checkpoints for UI behaviour — they do not indicate missing implementation.

---

_Verified: 2026-03-23T13:10:00Z_
_Verifier: Claude (gsd-verifier)_
