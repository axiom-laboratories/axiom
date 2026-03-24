---
status: complete
phase: 56-integration-bug-fixes
source: 56-01-SUMMARY.md
started: 2026-03-24T00:00:00Z
updated: 2026-03-24T14:45:00Z
---

## Current Test

[testing complete]

## Tests

### 1. Python Job Executes on Node
expected: Submit a signed Python job via the Jobs page (or API). The job should be picked up by a connected node, execute, and reach COMPLETED status. Job detail should show output from the Python script.
result: pass

### 2. Bash Job Executes on Node
expected: Submit a signed Bash job. It should be accepted, dispatched to a node, and reach COMPLETED status. Job detail shows Bash script output.
result: pass

### 3. Queue View Renders Live Data
expected: Open the Jobs page / Queue view. It should display the current job list with statuses — no blank state, no errors, no spinner that never resolves.
result: pass

### 4. CSV Export Works
expected: On the Jobs page, trigger the CSV export. A CSV file should download containing job records (id, status, timestamps, etc.). The file should be valid CSV — no errors, no empty file.
result: pass

### 5. Job Retry State in Drawer
expected: Find a job that has been retried (or resubmit one and let it complete). Open the job detail drawer. It should show the retry count / retry state correctly — not blank, not showing stale data.
result: pass

### 6. Provenance Link in Drawer
expected: After resubmitting a job, open the new job's detail drawer. It should show a provenance link back to the original parent job. Clicking the link navigates to the original job.
result: pass

### 7. Node Survives Restart Without Re-enrolling
expected: Restart a node container. The node should reconnect to the server using its existing identity — same node ID visible in the Nodes page, no duplicate node entry, no new enrollment error in logs.
result: pass

## Summary

total: 7
passed: 7
issues: 0
pending: 0
skipped: 0

## Gaps

[none]
