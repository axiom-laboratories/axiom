---
phase: 19-dashboard-staging-view-and-governance-doc
verified: 2026-03-15T17:30:00Z
status: human_needed
score: 6/6 must-haves verified
re_verification:
  previous_status: gaps_found
  previous_score: 5/6
  gaps_closed:
    - "One-click Publish promotes a DRAFT job to ACTIVE in the database (DASH-04)"
  gaps_remaining: []
  regressions: []
human_verification:
  - test: "Staging tab visibility and filter"
    expected: "STAGING tab shows only DRAFT jobs; ACTIVE tab shows non-DRAFT jobs"
    why_human: "Tab filter logic is correct in code but visual rendering and interactive tab toggle cannot be confirmed programmatically."
  - test: "Script inspection expand/collapse"
    expected: "Clicking the chevron reveals script content in a monospaced panel; clicking again collapses it"
    why_human: "expandedRows toggle is implemented correctly but visual layout and scroll behaviour require live render."
  - test: "pushed_by attribution display"
    expected: "Jobs pushed via CLI show an italic 'by <username>' sub-label below the job name"
    why_human: "Conditional render guard is correct in code but requires a real DRAFT job in the DB to confirm."
  - test: "Publish end-to-end flow"
    expected: "Clicking Publish on a DRAFT job moves it to the Active tab with ACTIVE badge; DB row reflects status = ACTIVE"
    why_human: "Full PATCH chain is now wired (commit 0296e25) but end-to-end DB persistence requires a running stack."
---

# Phase 19: Dashboard Staging View & Governance Documentation — Verification Report

**Phase Goal:** Operators can see all DRAFT jobs in a dedicated Staging view, inspect script content, finalize scheduling, publish to ACTIVE in one click, and all jobs display their lifecycle status badge — with the OIDC v2 integration path documented.
**Verified:** 2026-03-15T17:30:00Z
**Status:** human_needed
**Re-verification:** Yes — after gap closure (DASH-04 status assignment fix at commit `0296e25`)

---

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Dashboard shows a Staging/Drafts tab listing all DRAFT jobs | VERIFIED | `JobDefinitions.tsx:194-200` — `filteredDefinitions` filters `def.status === 'DRAFT'` when `activeTab === 'staging'`; tab buttons at lines 218-229 |
| 2 | Operator can inspect a draft job's script content (read-only) | VERIFIED | `JobDefinitionList.tsx:224-237` — expandable sibling TableRow with `<pre><code>{def.script_content}</code></pre>`, triggered by chevron button |
| 3 | Operator can finalize scheduling (cron, target tags) on a draft from the dashboard | VERIFIED | `JobDefinitions.tsx:85-100` — `handleEdit` fetches the job by ID; modal pre-populates `schedule_cron` and `target_tags`; `handleUpdate` PATCHes the definition |
| 4 | One-click Publish promotes a DRAFT to ACTIVE in the database | VERIFIED | `scheduler_service.py:281-282` — `if update_req.status is not None: job.status = update_req.status` present after `timeout_minutes` block, before `job.updated_at`. Committed at `0296e25`. Frontend `handlePublish` at `JobDefinitions.tsx:163-181` sends `{status: 'ACTIVE'}` to the wired backend route. |
| 5 | Job list shows status badge (DRAFT / ACTIVE / DEPRECATED / REVOKED) on all jobs | VERIFIED | `JobDefinitionList.tsx:68-82` — `renderStatusBadge()` switch maps all four states to colour-coded Badges; called at line 147 for every table row |
| 6 | OIDC v2 integration is documented as a governance architecture document | VERIFIED | `docs/architecture/OIDC_INTEGRATION.md` exists (30 lines); covers current Device Flow contract, v2 OIDC integration path, and dual-factor integrity model |

**Score:** 6/6 truths verified

---

## Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `puppeteer/dashboard/src/views/JobDefinitions.tsx` | Tabbed view, handlePublish, filteredDefinitions | VERIFIED | `activeTab` state, `filteredDefinitions` derived filter, `handlePublish` PATCH call all present and substantive |
| `puppeteer/dashboard/src/components/job-definitions/JobDefinitionList.tsx` | Status badges, expandable rows, pushed_by, Publish button | VERIFIED | `renderStatusBadge()`, `expandedRows` state, `toggleRow()`, `pushed_by` sub-label, and conditional Publish button all implemented |
| `puppeteer/agent_service/services/scheduler_service.py` | `update_job_definition()` applies status field to `job.status` | VERIFIED | Lines 281-282: `if update_req.status is not None: job.status = update_req.status` — follows the same guard pattern as all other optional fields in the method |
| `docs/architecture/OIDC_INTEGRATION.md` | OIDC architecture doc | VERIFIED | File exists (30 lines) covering Device Flow contract, OIDC v2 roadmap, and dual-factor integrity model |
| `docs/UserGuide.md` Section 6 | Staging workflow documentation | VERIFIED | Section 6 "Job Staging & Lifecycle" covers all four lifecycle statuses, staging workflow steps, and governance rules |
| `puppeteer/agent_service/main.py` (import fix) | ImageBOMResponse, PackageIndexResponse imports | VERIFIED | Both present on line 41; used as `response_model` at lines 2051 and 2064 |

---

## Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `JobDefinitions.tsx handlePublish` | `PATCH /api/jobs/definitions/{id}` | `authenticatedFetch` + `/api` prefix | WIRED | `handlePublish` line 168 sends `{status: 'ACTIVE'}` body |
| `PATCH /api/jobs/definitions/{id}` | `job.status` in DB | `scheduler_service.update_job_definition()` lines 281-282 | WIRED | Fixed in commit `0296e25`; status assignment now persists to database |
| `JobDefinitions.tsx activeTab` | `filteredDefinitions` | Derived filter at lines 194-200 | WIRED | `filteredDefinitions` computed from `definitions` state and passed to `JobDefinitionList` |
| `JobDefinitionList onPublish prop` | `handlePublish` in parent | `onPublish` prop at `JobDefinitions.tsx:244` | WIRED | Parent passes `handlePublish` as `onPublish`; child guards render with `def.status === 'DRAFT' && onPublish` |
| `JobDefinitionList expandedRows` | `script_content` display | `toggleRow()` + conditional sibling TableRow | WIRED | `expandedRows[def.id]` gate at line 224 renders sibling row with `<pre><code>{def.script_content}</code></pre>` |
| `JobDefinitions.tsx handleEdit` | `JobDefinitionModal` pre-population | `editingJob` state + `useEffect` in modal | WIRED | `setEditingJob(data)` sets editing state; modal `useEffect` populates formData from `editingJob` |

---

## Requirements Coverage

| Requirement | Description | Status | Evidence |
|-------------|-------------|--------|----------|
| DASH-01 | Dashboard shows a Staging/Drafts view listing all DRAFT jobs | SATISFIED | `filteredDefinitions` filter + STAGING tab button in `JobDefinitions.tsx` |
| DASH-02 | Operator can inspect a draft job's script content (read-only) | SATISFIED | Expandable row with `<pre><code>` panel in `JobDefinitionList.tsx:224-237` |
| DASH-03 | Operator can finalize scheduling (cron, target tags) on a draft | SATISFIED | Edit button opens `JobDefinitionModal` pre-populated; PATCH update path functional |
| DASH-04 | One-click Publish promotes a DRAFT to ACTIVE | SATISFIED | Backend fix at `scheduler_service.py:281-282` closes the gap. Full path: `handlePublish` sends `{status: 'ACTIVE'}` → route validates REVOKED gate → `update_job_definition()` writes `update_req.status` to `job.status` → `db.commit()` persists. |
| DASH-05 | Job list shows status badge (DRAFT / ACTIVE / DEPRECATED / REVOKED) | SATISFIED | `renderStatusBadge()` in `JobDefinitionList.tsx:68-82` covers all four states |
| GOV-CLI-02 | External IdP (OIDC) documented as a v2 integration path | SATISFIED | `docs/architecture/OIDC_INTEGRATION.md` exists and covers the integration path |

**Orphaned requirements:** None. All 6 Phase 19 requirements appear in plan frontmatter and are satisfied.

---

## Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `puppeteer/dashboard/src/views/JobDefinitions.tsx` | 57-59 | Redundant await with `res.ok` boolean check | Info | Harmless; works correctly but is confusing |

No blocker anti-patterns. No TODO/FIXME/placeholder comments in phase files.

---

## Human Verification Required

### 1. Staging Tab Visual Rendering

**Test:** Navigate to the Scheduled Jobs page. Confirm two tab buttons (ACTIVE, STAGING) are visible next to the "Archive New Payload" button.
**Expected:** Active tab is highlighted by default; clicking STAGING filters the table to show only DRAFT jobs; clicking ACTIVE restores non-DRAFT jobs.
**Why human:** Tab filter logic is correct in code but visual rendering and interactive tab state transitions cannot be confirmed programmatically.

### 2. Script Inspection Panel

**Test:** On any job row, click the chevron icon on the left.
**Expected:** A full-width panel expands below the row showing the job's script content in a monospaced font with horizontal scroll for long lines. Clicking again collapses it.
**Why human:** `expandedRows` toggle is implemented correctly but visual layout, max-height scroll behaviour, and collapse animation require live render to confirm.

### 3. pushed_by Attribution

**Test:** Push a job via `mop-push job push` CLI. Find it in the Staging tab.
**Expected:** An italic "by <username>" sub-label appears below the job name in the table row.
**Why human:** The conditional render `{def.pushed_by && (...)}` is correct in code but requires a real DRAFT job in the database to confirm end-to-end appearance.

### 4. Publish End-to-End Flow

**Test:** With a DRAFT job visible in the Staging tab, click the Publish button on that row.
**Expected:** The job disappears from the Staging tab and reappears in the Active tab with an ACTIVE badge. The database row reflects `status = 'ACTIVE'`.
**Why human:** The full PATCH chain is now wired in code (fix at `0296e25`) but end-to-end confirmation of the UI refresh and DB persistence requires a running stack with a real DRAFT job.

---

## Re-verification Summary

**Gap closed:** DASH-04 — The missing status field assignment is confirmed present at `scheduler_service.py:281-282`:

```python
if update_req.status is not None:
    job.status = update_req.status
```

This follows the identical guard pattern used for all other optional fields in `update_job_definition()`. The fix was committed at `0296e25`.

**No regressions detected.** Quick regression checks confirmed:
- `filteredDefinitions` STAGING filter still present in `JobDefinitions.tsx`
- `renderStatusBadge()`, `expandedRows`, `script_content`, `pushed_by` still present in `JobDefinitionList.tsx`
- `handlePublish` still sends `{status: 'ACTIVE'}` to the correct endpoint
- `ImageBOMResponse`/`PackageIndexResponse` imports still present in `main.py`
- `docs/architecture/OIDC_INTEGRATION.md` still exists (30 lines)

All 6/6 automated truths verified. Status is `human_needed` pending live stack confirmation of visual and interactive behaviour.

---

_Verified: 2026-03-15T17:30:00Z_
_Verifier: Claude (gsd-verifier)_
_Re-verification after gap closure at commit 0296e25_
