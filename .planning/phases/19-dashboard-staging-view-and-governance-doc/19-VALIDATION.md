# Phase 19 Validation Strategy: Dashboard Staging View & Governance Doc

## Automated Tests
- **UI Components**: 
  - Verify `JobDefinitionList` correctly renders status badges based on the `status` field.
  - Verify `JobDefinitions` correctly filters jobs between "Active" and "Staging" tabs.
- **State Transitions**:
  - Mock the `/jobs/definitions/{id}` PATCH call to verify the "Publish" button triggers the correct status update.

## Manual E2E Verification
Requires a running `puppeteer` backend and dashboard.

### 1. Staging View (DASH-01)
- **Action**: Use `mop-push` to push a DRAFT job.
- **Verification**: Job appears in the "Staging" tab of the dashboard, but not in the "Active" tab.

### 2. Script Inspection (DASH-02)
- **Action**: Click "View Script" on a draft job.
- **Verification**: Modal opens showing the full, read-only script content.

### 3. Finalize Scheduling (DASH-03)
- **Action**: Edit a draft job to set a cron schedule and tags.
- **Verification**: Changes are saved and visible in the list.

### 4. Publish Transition (DASH-04)
- **Action**: Click "Publish" on a draft job.
- **Verification**: Job status transitions to `ACTIVE`, it moves to the "Active" tab, and it becomes eligible for node assignment.

### 5. Status Badges (DASH-05)
- **Action**: View the job list.
- **Verification**: Every job displays a badge (DRAFT, ACTIVE, DEPRECATED, or REVOKED).

### 6. Governance Doc (GOV-CLI-02)
- **Action**: Read `docs/architecture/OIDC_INTEGRATION.md`.
- **Verification**: Document clearly explains the OIDC v2 path and the OAuth device flow contract.

## Success Metrics
- 100% functional parity with PRD requirements.
- Dashboard feels responsive and correctly reflects backend state.
- Documentation is accurate and complete.
