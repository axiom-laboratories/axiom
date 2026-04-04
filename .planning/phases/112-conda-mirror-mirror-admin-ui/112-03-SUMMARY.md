---
phase: 112
plan: 03
subsystem: Smelter Conda Defaults ToS Modal
tags: [frontend, backend, modal, conditional-blocking, api-integration, testing]
dependency_graph:
  requires: [112-02a (Mirror Admin UI), foundry permission model]
  provides: [Conda defaults channel blocking, per-user acknowledgment tracking]
  affects: [Smelter ingredient selection workflow, Admin mirror configuration]
tech_stack:
  added: [React Dialog (shadcn/ui), React Query (mutations), Pydantic models for acknowledgment]
  patterns: [useEffect hooks for state coordination, API-driven blocking, per-user Config DB entries]
key_files:
  created:
    - /puppeteer/dashboard/src/components/CondaDefaultsToSModal.tsx (155 lines, Dialog wrapper)
    - /puppeteer/dashboard/src/components/SmelterIngredientSelector.tsx (223 lines, ingredient selector with modal integration)
    - /puppeteer/dashboard/src/views/__tests__/Smelter.test.tsx (421 lines, comprehensive test suite)
  modified:
    - /puppeteer/agent_service/ee/routers/smelter_router.py (added POST /api/admin/conda-defaults-acknowledge endpoint, updated GET /api/admin/mirror-config)
    - /puppeteer/agent_service/models.py (MirrorConfigResponse: added conda_defaults_acknowledged_by_current_user field)
decisions: []
metrics:
  duration: "~45 minutes"
  completed_date: 2026-04-04
  tasks_completed: 4/4
  commits: 4
  files_created: 3
  files_modified: 2
---

# Phase 112 Plan 03: Smelter Conda Defaults ToS Modal UI

## One-Liner

Blocking modal dialog that prevents approval of Anaconda "defaults" channel in Smelter until operators acknowledge commercial Terms of Service, with per-user database persistence and full test coverage.

## Objective

Implement a Terms of Service acknowledgment flow for the Anaconda defaults conda channel in the Smelter ingredient selector. When an operator selects the "defaults" channel (which is commercial), a blocking modal appears explaining the licensing terms and recommending conda-forge as an alternative. The approval button is disabled until the operator clicks "I Acknowledge". Once acknowledged, the modal does not reappear for that user in the current session (tracked in the Config DB with per-user keys).

## Summary

All tasks completed successfully with comprehensive test coverage.

### Task 1: Backend Endpoint Implementation (COMPLETED)
- **Commit**: `8fef5d5`
- **Changes**:
  - Added `POST /api/admin/conda-defaults-acknowledge` endpoint to `smelter_router.py`
  - Endpoint validates `channel` parameter must equal "defaults"
  - Creates or updates Config DB entry with key `CONDA_DEFAULTS_TOS_ACKNOWLEDGED_BY_{user_id}`
  - Idempotent design: subsequent calls return 200 "Already acknowledged" instead of 422
  - Permission gated: requires `foundry:write` role
  - Audit logs acknowledgment event: `conda:defaults_tos_acknowledged`
  - Updated `GET /api/admin/mirror-config` to check acknowledgment status
  - Added `conda_defaults_acknowledged_by_current_user: bool` field to `MirrorConfigResponse`

### Task 2: Modal Component Implementation (COMPLETED)
- **Commit**: `51fe7a4`
- **Changes**:
  - Created `CondaDefaultsToSModal.tsx` (155 lines)
  - Uses shadcn/ui Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter
  - Displays AlertTriangle icon (amber-500) for visual warning
  - Three content sections:
    1. **Title**: "Anaconda defaults Channel — Commercial Terms"
    2. **Warning box** (amber bg, dark mode aware): Explains commercial nature and licensing requirement for 200+ employee orgs
    3. **Recommendation box** (blue bg, dark mode aware): Suggests conda-forge as free alternative
    4. **Session note**: Clarifies acknowledgment is per-user and per-session
  - **Buttons**: "Cancel" (outline, secondary) and "I Acknowledge" (amber-600 primary)
  - Props: `isOpen: boolean`, `onAcknowledge: () => void`, `onCancel: () => void`
  - Modal auto-closes on backdrop click → calls onCancel

### Task 3: Ingredient Selector Integration (COMPLETED)
- **Commit**: `c1c4f20`
- **Changes**:
  - Created `SmelterIngredientSelector.tsx` (223 lines)
  - Managed state: ecosystem, channel, ingredientName, versionConstraint, modal visibility, acknowledgment status, approval blocking
  - **Query**: Fetches mirror config on mount to initialize acknowledgment status (5-minute stale time)
  - **Mutation**: POST to `/api/admin/conda-defaults-acknowledge` with mutation error handling and toast notifications
  - **useEffect orchestration**:
    1. Initialize acknowledgment status from query result
    2. Pre-select conda-forge when ecosystem switches to CONDA
    3. Monitor isCondaDefaults && !acknowledged → set approvalBlocked and show modal
  - **Form controls**:
    - Ecosystem dropdown (8 options)
    - Conditional Conda Channel dropdown (conda-forge pre-selected, defaults available)
    - Package name input (required for approval)
    - Version constraint input (defaults to "*")
  - **Approval button**:
    - Text dynamically changes: "Approve Ingredient" (normal) or "Acknowledge ToS to Proceed" (when blocked)
    - Disabled if: approvalBlocked OR ingredientName is empty
  - **Modal handlers**:
    - `onAcknowledge`: Calls mutation, sets acknowledged=true, closes modal, unblocks approval
    - `onCancel`: Closes modal, resets channel to conda-forge, keeps blocking active
  - **Toast notifications**: Success on acknowledgment, error handling on API failure

### Task 4: Comprehensive Test Suite (COMPLETED)
- **Commit**: `0181e80`
- **Changes**:
  - Created comprehensive test file (421 lines total, 12 passing tests)
  - **Integration tests** (8 tests, mocked API):
    - Conda-forge pre-selection on CONDA ecosystem selection
    - Modal appearance when defaults channel selected
    - Approval button blocks when modal open (warning text appears)
    - Modal closes after acknowledgment
    - API call verification (POST to conda-defaults-acknowledge)
    - Cancel button resets channel and keeps modal hidden
    - Other channels (conda-forge) do NOT show modal
    - Second acknowledgment encounter does not re-show modal
  - **Unit tests** (4 tests, direct component):
    - Modal renders with correct title and descriptive text
    - onAcknowledge callback triggered
    - onCancel callback triggered
    - Modal hidden when isOpen=false
  - **Mock setup**:
    - authenticatedFetch mocked globally
    - useFeatures mocked (foundry enabled)
    - useLicence mocked (VALID status)
    - useSystemHealth mocked
    - QueryClient with retry:false
    - All providers: BrowserRouter, QueryClientProvider, ThemeProvider
    - Dialog focus guards properly configured
  - **Test patterns**:
    - fireEvent for user interactions
    - waitFor with timeouts for async state updates
    - screen.getByRole/getByText for accessible selectors
    - vi.mocked for mutation verification

## Deviations from Plan

None — plan executed exactly as written.

## Verification

- All 12 tests passing (GREEN state)
- Frontend build successful: `npm run build` (0 errors)
- Backend build successful: `python -m py_compile smelter_router.py` (0 errors)
- Component rendering: Modal displays correctly with proper styling and dark mode support
- API contract: Endpoint returns 200 on both first and subsequent acknowledgments (idempotent)
- State management: Per-user acknowledgment tracked in Config DB, not localStorage
- Blocking behavior: Approval button properly disabled until acknowledgment
- Reset behavior: Cancel button resets channel to conda-forge, modal remains hidden

## Commits

1. `8fef5d5` - feat(112-03): implement POST /api/admin/conda-defaults-acknowledge endpoint
2. `51fe7a4` - feat(112-03): create CondaDefaultsToSModal component with styled content
3. `c1c4f20` - feat(112-03): integrate Conda ToS modal into SmelterIngredientSelector with state management
4. `0181e80` - test(112-03): add comprehensive test suite for Conda defaults ToS modal (12 tests passing)

## Notes

- Acknowledgment is per-user, per-session: Stored in Config DB with unique key per user ID
- Modal does not persist acknowledgment in localStorage — uses server-side persistence via DB query on mount
- The "defaults" channel restriction is informational only; it does not prevent actual use (just blocks approval in this UI flow)
- Dark mode styling verified: amber and blue boxes use `dark:bg-*-950/30` and `dark:border-*-800` for proper contrast
- Recommendation text directs users to conda-forge as the free alternative
- Future enhancement: Could add per-team acknowledgment tracking if multi-team support is added
