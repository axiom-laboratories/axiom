# Phase 56: Integration Bug Fixes - Context

**Gathered:** 2026-03-24
**Status:** Ready for planning

<domain>
## Phase Boundary

Verify that the four INT-01–04 integration defects identified in the v12.0 milestone audit are working end-to-end in the live Docker stack, then close out the 7 requirements (JOB-01, RT-01, RT-02, VIS-02, SRCH-10, JOB-04, JOB-05) that are currently marked Pending.

**Important:** Phase 54 already applied all four code fixes to the codebase:
- INT-01: `GuidedDispatchCard.tsx` sends `script_content` key (not `script`) at both dispatch sites
- INT-02: `Queue.tsx` fetches `/jobs` and `/nodes` without `/api` double-prefix
- INT-03: `Jobs.tsx` CSV export uses `/api/jobs/${guid}/executions/export`
- INT-04: `list_jobs()` includes `retry_count`, `max_retries`, `retry_after`, `originating_guid`

Phase 56 is a **re-verification + close-out phase**. The code is fixed; the task is to confirm it works end-to-end and formally close the requirements.

</domain>

<decisions>
## Implementation Decisions

### Verification depth
- Full Docker stack E2E verification required (not code review only)
- Playwright tests against the live `compose.server.yaml` stack
- Produce a formal `56-VERIFICATION.md` as the canonical evidence document
- Test all 3 runtimes end-to-end: Python, Bash, and PowerShell (RT-01, RT-02 in scope)
- INT-04 retry state verified with a live retried job in the stack (not just unit test evidence)

### New test coverage
- Write persistent Playwright test file at `mop_validation/scripts/test_phase56_integration.py`
- Covers all 4 scenarios:
  1. Guided form → Python/Bash/PowerShell job COMPLETED (INT-01 / JOB-01 / RT-01 / RT-02)
  2. Queue view shows PENDING/RUNNING job live data (INT-02 / VIS-02)
  3. CSV export from job detail drawer returns 200 with CSV content (INT-03 / SRCH-10)
  4. Job drawer shows retry_count/retry_after for retried job; provenance link for resubmitted job (INT-04 / JOB-04 / JOB-05)

### Human verify checkpoint
- Blocking human checkpoint included in the plan
- Operator must manually confirm: (1) guided form execution in browser, (2) Queue live data, (3) CSV export
- REQUIREMENTS.md close-out is **gated on the human checkpoint** — requirements only update after sign-off

### Plan structure
- Single plan (56-01-PLAN.md): verification + Playwright tests + human checkpoint + REQUIREMENTS.md update
- REQUIREMENTS.md update is the final task after the checkpoint passes

### Requirements close-out
- Update 7 checkboxes from `[ ]` to `[x]`: JOB-01, RT-01, RT-02, VIS-02, SRCH-10, JOB-04, JOB-05
- Update traceability rows: Phase 56 → Phase 54, Status Pending → Complete
- Coverage count updated to reflect all 7 now resolved

### Claude's Discretion
- Exact Playwright test structure (session reuse, JWT injection pattern per CLAUDE.md)
- Whether retry state is verified by submitting a job with max_retries=1 or finding an existing failed job
- Exact VERIFICATION.md section layout and evidence formatting

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `mop_validation/scripts/test_local_stack.py`: pattern for API-level stack testing — reuse for setup/teardown pattern
- `mop_validation/scripts/test_playwright.py`: existing Playwright E2E patterns — JWT injection via localStorage, `--no-sandbox` launch, form-encoded login
- Phase 54 pytest: `puppeteer/tests/test_list_jobs_retry_fields.py` — confirms INT-04 backend fix is in place
- Phase 54 vitest: `puppeteer/dashboard/src/views/__tests__/Queue.test.tsx` — confirms INT-02 URL pattern

### Established Patterns
- Playwright auth: inject JWT via `localStorage.setItem('mop_auth_token', token)` — not form fill
- API login: `requests.post(url, data={...})` (form-encoded, not JSON)
- Browser launch: `p.chromium.launch(args=['--no-sandbox'], headless=True)`
- Never use `npm run dev` — always test against Docker stack (`compose.server.yaml`)
- `authenticatedFetch` URL contract: paths without `/api` prefix (auth.ts prepends it), except CSV export which uses the full `/api/jobs/{guid}/executions/export` path

### Integration Points
- `GuidedDispatchCard.tsx` → `POST /api/dispatch` → `node.py` — key is `script_content`
- `Queue.tsx` → `GET /jobs` and `GET /nodes` — no `/api` prefix in fetch calls
- `Jobs.tsx` → `GET /api/jobs/{guid}/executions/export` — full `/api/` prefix
- `job_service.py list_jobs()` → `JobDetailPanel` retry countdown (lines 494–504) and provenance link (lines 514–518)

</code_context>

<specifics>
## Specific Ideas

- Phase 54 verification reference: guided form job `ca07b93f-8357-4a8b-a22d-f43418d998f0` ran to COMPLETED in Docker stack — new verification should produce a fresh GUID
- INT-04 retry test: submit a Python job that intentionally fails (e.g., `raise SystemExit(1)`) with `max_retries: 1`, wait for FAILED+retries-exhausted, then check the drawer

</specifics>

<deferred>
## Deferred Ideas

- None — discussion stayed within phase scope

</deferred>

---

*Phase: 56-integration-bug-fixes*
*Context gathered: 2026-03-24*
