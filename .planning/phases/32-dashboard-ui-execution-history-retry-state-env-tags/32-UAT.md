---
status: complete
phase: 32-dashboard-ui-execution-history-retry-state-env-tags
source: [32-01-SUMMARY.md, 32-03-SUMMARY.md, 32-04-SUMMARY.md, 32-05-SUMMARY.md]
started: 2026-03-18T21:45:00Z
updated: 2026-03-18T23:10:00Z
---

## Current Test

[testing complete]

## Tests

### 1. Cold Start Smoke Test
expected: Kill any running dashboard dev server (or docker stack). Start fresh. The backend boots without errors, and the dashboard loads in the browser with a working login screen. After logging in, the main nav appears with no console errors in the browser developer tools.
result: pass

### 2. Attestation Badge in Execution Log
expected: Open any past job execution log (click the log icon on a job run in Jobs, History, or the new history panel). In the modal header area, there should be an attestation badge. If the node produced a signed attestation and it verified correctly, the badge shows "VERIFIED" in green. If verification failed, it shows "ATTEST FAILED" in red. If no attestation was produced (older runs), it shows "NO ATTESTATION" in a neutral/zinc colour.
result: issue
reported: "No attestation badge visible at all. Modal header shows Execution Log / COMPLETED status badge, exit code, duration, node — but no attestation badge (not VERIFIED, not ATTEST FAILED, not NO ATTESTATION). Tested on jobs run today after Phase 30 deployment."
severity: major

### 3. Attempt Tabs in Log Modal (Retry Run)
expected: For a job that has been retried (multiple attempts), open the execution log via the history panel. The modal header area should contain tabs labelled "Attempt 1", "Attempt 2", etc., sorted oldest-first. The final (most recent) attempt tab should be labelled "Attempt N (final)". Clicking each tab switches the stdout/stderr log displayed below.
result: skipped
reason: No retry runs present in test environment to verify against

### 4. Execution History Panel in Job Definitions
expected: Navigate to the Job Definitions view. Click on any job definition name (it should be clickable — cursor changes, and the row highlights with a left blue border). A history panel appears below the definitions list showing past execution runs for that definition — each row shows timestamp, node, exit code, and duration. Clicking the same definition again collapses the panel.
result: pass

### 5. Open Log from History Panel
expected: In the Job Definitions history panel (after selecting a definition), click on any execution run row. The ExecutionLogModal should open showing the stdout/stderr output for that run, the attestation badge in the header, and (if a retry run) attempt tabs.
result: pass

### 6. Retry Badge in History Panel
expected: If any job definition has runs that involved retries (max_retries > 1 and at least one failure that triggered a retry), the history panel should show an amber "Attempt N of M" badge on that run group. Failed runs that exhausted all retries should show "Failed N/M". Runs with a single attempt should show no retry badge.
result: skipped
reason: No retry runs present in test environment to verify against

### 7. Definition Filter in History View
expected: Navigate to the History view. There should be a 4th filter column in the filter bar labelled "Scheduled Job" (or similar). The dropdown lists all available job definitions. Selecting one filters the execution list to show only runs for that definition. Selecting "All" or clearing the filter returns all executions.
result: pass

### 8. Node Env Tag Badge
expected: Navigate to the Nodes view. Any node that was started with an ENV_TAG environment variable set should display a small colour-coded badge on its node card next to the node name. PROD nodes show a rose/red badge, TEST nodes show amber/yellow, DEV nodes show blue, and any custom tag shows zinc/grey. Nodes with no env_tag set show no badge.
result: pass

### 9. Node Env Tag Filter
expected: On the Nodes view, if any nodes have an env_tag set, a filter dropdown should appear above the node grid. It lists each unique env tag present in the fleet. Selecting a tag filters the node grid to show only nodes with that tag. Selecting "All Environments" returns all nodes. If no nodes have env_tag set, no filter dropdown appears.
result: pass

## Summary

total: 9
passed: 6
issues: 1
pending: 0
skipped: 2

## Gaps

- truth: "ExecutionLogModal shows an attestation badge in the header (VERIFIED / ATTEST FAILED / NO ATTESTATION)"
  status: failed
  reason: "User reported: No attestation badge visible at all. Modal header shows Execution Log / COMPLETED status badge, exit code, duration, node — but no attestation badge (not VERIFIED, not ATTEST FAILED, not NO ATTESTATION). Tested on jobs run today after Phase 30 deployment."
  severity: major
  test: 2
  root_cause: ""
  artifacts: []
  missing: []
  debug_session: ""
