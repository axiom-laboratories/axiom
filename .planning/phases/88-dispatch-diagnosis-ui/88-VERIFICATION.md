---
phase: 88-dispatch-diagnosis-ui
verified: 2026-03-29T21:30:00Z
status: human_needed
score: 11/11 must-haves verified
re_verification: false
human_verification:
  - test: "Open the Jobs view with at least one PENDING job and observe the status cell"
    expected: "A sub-line of amber text appears beneath the PENDING badge showing a diagnosis message (e.g. 'No nodes online' or 'Capability mismatch'); an amber left border appears on that row"
    why_human: "CSS class application and rendered text require a live browser — cannot verify visual rendering from grep"
  - test: "Leave the Jobs view open for 15 seconds with a PENDING job and watch the diagnosis text"
    expected: "Diagnosis text updates without any page reload (auto-poll every 10s)"
    why_human: "Timer-based UI polling requires live browser observation"
  - test: "Click the RefreshCw button in the Queue Monitor card header"
    expected: "Diagnosis sub-text refreshes immediately on click"
    why_human: "Button interactivity requires live browser"
  - test: "Open the detail drawer for a PENDING or ASSIGNED job; wait 15 seconds"
    expected: "Dispatch Diagnosis callout in the drawer shows the reason and updates while drawer stays open"
    why_human: "Drawer interval behaviour requires live browser observation"
---

# Phase 88: Dispatch Diagnosis UI Verification Report

**Phase Goal:** Surface dispatch diagnosis information in the UI so operators can understand why a job is stuck without leaving the dashboard.
**Verified:** 2026-03-29T21:30:00Z
**Status:** human_needed (all automated checks pass; 4 visual/behavioural items need live browser)
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| #  | Truth | Status | Evidence |
|----|-------|--------|----------|
| 1  | POST /jobs/dispatch-diagnosis/bulk accepts a list of GUIDs and returns a results dict keyed by GUID | VERIFIED | Route registered in FastAPI at `/jobs/dispatch-diagnosis/bulk`; confirmed via app.routes introspection; iterates guids and returns `{"results": {guid: diagnosis}}` |
| 2  | An ASSIGNED job whose started_at + (timeout_minutes * 1.2) is in the past returns reason=stuck_assigned | VERIFIED | `get_dispatch_diagnosis` contains branch at line 1237–1245 with threshold/elapsed calculation; `stuck_assigned` string confirmed present; branch precedes `not_pending` guard |
| 3  | An ASSIGNED job within its timeout threshold falls through to not_pending (unchanged) | VERIFIED | Branch only returns `stuck_assigned` when `elapsed_minutes > threshold_minutes`; otherwise falls through to existing guard at line 1246 |
| 4  | The bulk endpoint calls get_dispatch_diagnosis for each GUID and aggregates results | VERIFIED | Route body confirmed: `for guid in req.guids: results[guid] = await JobService.get_dispatch_diagnosis(guid, db)` |
| 5  | A PENDING job row in the job list shows diagnosis text under its status badge | VERIFIED (automated) / ? (visual) | `diagnosisCache` state wired; status cell renders diagnosis sub-line in a `flex-col` div beneath the badge; amber text class confirmed at line 1477 |
| 6  | A stuck-ASSIGNED job row shows diagnosis text under its assigned badge | VERIFIED (automated) / ? (visual) | Sub-line condition covers `job.status === 'ASSIGNED'` with cache lookup; `stuck_assigned` reason not filtered out by the `not_pending`/`pending_dispatch` suppression |
| 7  | Amber left-border accent appears on PENDING rows (and stuck-ASSIGNED rows) | VERIFIED (automated) / ? (visual) | `border-l-2 border-amber-500/60 pl-[10px]` applied conditionally at line 1458–1462 |
| 8  | Diagnosis text includes queue position info when queue_position >= 2 | VERIFIED | `toOrdinal` helper present; `queue_position >= 2` guard at line 1479–1481 appends ` · Nth in queue` suffix |
| 9  | A manual refresh button in the Queue Monitor header triggers an immediate bulk fetch | VERIFIED (automated) / ? (interactive) | `<Button onClick={fetchDiagnoses}>` with `<RefreshCw>` icon confirmed at lines 1246–1254 in Queue Monitor header |
| 10 | Diagnosis auto-updates every 10 seconds while Jobs view is mounted | VERIFIED (automated) / ? (behavioural) | `setInterval(fetchDiagnoses, 10_000)` with `clearInterval` cleanup confirmed at lines 890–891; dependency is stringified GUID join to prevent infinite re-render |
| 11 | When no PENDING/ASSIGNED jobs exist, no polling occurs | VERIFIED | `if (pendingGuids.length === 0) return;` guard at line 888 in the poll useEffect |

**Score:** 11/11 truths verified (4 require human confirmation for visual/behavioural correctness)

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `puppeteer/agent_service/services/job_service.py` | Stuck-ASSIGNED branch in get_dispatch_diagnosis | VERIFIED | `stuck_assigned` branch at lines 1237–1245; threshold = timeout * 1.2; ordering confirmed before `not_pending` guard |
| `puppeteer/agent_service/models.py` | BulkDiagnosisRequest model | VERIFIED | Model at line 82–84; `guids: List[str]`; importable and instantiable |
| `puppeteer/agent_service/main.py` | POST /jobs/dispatch-diagnosis/bulk route | VERIFIED | Route at lines 1052–1062; uses `require_auth`; calls `JobService.get_dispatch_diagnosis` per guid |
| `puppeteer/dashboard/src/views/Jobs.tsx` | Inline diagnosis display + bulk poll + manual refresh | VERIFIED | 1584 lines (min_lines 1350 met); all three UX changes present |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|----|--------|---------|
| `main.py` | `job_service.py` | bulk endpoint calls `JobService.get_dispatch_diagnosis` | VERIFIED | `JobService.get_dispatch_diagnosis` called inside `bulk_dispatch_diagnosis` at line 1061 |
| `Jobs.tsx` | `/jobs/dispatch-diagnosis/bulk` | `authenticatedFetch` POST in `fetchDiagnoses` callback | VERIFIED | `authenticatedFetch('/jobs/dispatch-diagnosis/bulk', { method: 'POST', ...})` at line 873; response merged into `diagnosisCache` via spread at line 880 |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| DIAG-01 | 88-02 | Operator can see why a PENDING job hasn't dispatched — inline in the job list or detail view | SATISFIED | Inline diagnosis sub-line rendered beneath status badge in job table rows; drawer callout also present |
| DIAG-02 | 88-01 | Diagnosis surfaces the specific reason (no capable nodes, mismatch, resource limit exceeded, etc.) | SATISFIED | `stuck_assigned`, `no_nodes_online`, `capability_mismatch`, `all_nodes_busy`, `target_node_unavailable` all returned from `get_dispatch_diagnosis`; message field contains human-readable explanation |
| DIAG-03 | 88-02 | Diagnosis updates without a full page reload (on-demand refresh or auto-poll) | SATISFIED | 10s `setInterval` poll present with immediate fetch on mount; manual RefreshCw button also present; drawer 10s interval for open PENDING/ASSIGNED jobs |

No orphaned requirements: all three DIAG IDs claimed in plan frontmatter match the REQUIREMENTS.md Phase 88 entries.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `Jobs.tsx` | 892 | `// eslint-disable-next-line react-hooks/exhaustive-deps` | Info | Intentional per plan spec — stringified dependency avoids array identity instability; not a real lint suppression concern |

No TODOs, FIXMEs, placeholder returns, or empty handler stubs found in phase-modified files.

### Human Verification Required

#### 1. Inline diagnosis sub-text renders in the job list

**Test:** Open the Jobs view in a browser with at least one PENDING job in the queue.
**Expected:** The status cell for that row shows the status badge on one line and a short amber text message beneath it (e.g. "No nodes online", "Capability mismatch — requires python3"). An amber left border appears on the row.
**Why human:** CSS class application and text rendering require a live browser session.

#### 2. Diagnosis auto-polls without page reload

**Test:** Leave the Jobs view open for 15+ seconds with a PENDING job. Observe the diagnosis sub-text.
**Expected:** The text updates in-place at ~10s intervals as node state changes (or remains consistent). No page reload occurs.
**Why human:** Timer-based UI polling behaviour cannot be verified from static code inspection alone.

#### 3. Manual refresh button works

**Test:** Click the circular-arrow RefreshCw icon in the top-right of the Queue Monitor card header.
**Expected:** The diagnosis sub-text immediately refreshes (network request visible in browser DevTools to `/api/jobs/dispatch-diagnosis/bulk`).
**Why human:** Button interactivity requires live browser.

#### 4. Drawer auto-refreshes for ASSIGNED stuck jobs

**Test:** Open the detail drawer for a job that is ASSIGNED and has been running longer than its timeout (or PENDING). Wait 15 seconds with the drawer open.
**Expected:** The "Dispatch Diagnosis" callout in the drawer shows the reason and updates every ~10s while open. Closing the drawer stops the interval.
**Why human:** Drawer interval lifecycle requires live browser observation.

### Gaps Summary

No gaps found. All artifacts exist, are substantive, and are wired. The phase goal is achieved: dispatch diagnosis information is surfaced inline in the job list and the detail drawer, with automatic polling and a manual refresh control, so operators can understand why a job is stuck without leaving the dashboard.

The 4 items above are observational/behavioural validations requiring a live browser — they are not blockers to declaring the phase complete, but should be spot-checked in the Docker stack before the branch is merged.

---

_Verified: 2026-03-29T21:30:00Z_
_Verifier: Claude (gsd-verifier)_
