---
phase: 48
slug: scheduled-job-signing-safety
status: complete
nyquist_compliant: true
wave_0_complete: true
created: 2026-03-22
---

# Phase 48 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest + anyio (existing `test_scheduler_service.py`) |
| **Config file** | `puppeteer/pytest.ini` |
| **Quick run command** | `cd /home/thomas/Development/master_of_puppets/puppeteer && pytest agent_service/tests/test_scheduler_service.py -x` |
| **Full suite command** | `cd /home/thomas/Development/master_of_puppets/puppeteer && pytest` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `cd /home/thomas/Development/master_of_puppets/puppeteer && pytest agent_service/tests/test_scheduler_service.py -x`
- **After every plan wave:** Run `cd /home/thomas/Development/master_of_puppets/puppeteer && pytest`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 48-W0-01 | W0 | 0 | SCHED-01 | unit | `pytest agent_service/tests/test_scheduler_service.py::test_update_script_without_sig_transitions_to_draft -x` | ✅ | ✅ green |
| 48-W0-02 | W0 | 0 | SCHED-01 | unit | `pytest agent_service/tests/test_scheduler_service.py::test_update_script_with_sig_stays_active -x` | ✅ | ✅ green |
| 48-W0-03 | W0 | 0 | SCHED-01 | unit | `pytest agent_service/tests/test_scheduler_service.py::test_draft_reedits_no_duplicate_alert -x` | ✅ | ✅ green |
| 48-W0-04 | W0 | 0 | SCHED-01 | unit | `pytest agent_service/tests/test_scheduler_service.py::test_resign_without_script_change_reactivates -x` | ✅ | ✅ green |
| 48-W0-05 | W0 | 0 | SCHED-02 | unit | `pytest agent_service/tests/test_scheduler_service.py::test_draft_skip_log_message -x` | ✅ | ✅ green |
| 48-W0-06 | W0 | 0 | SCHED-04 | unit | `pytest agent_service/tests/test_scheduler_service.py::test_draft_transition_creates_alert -x` | ✅ | ✅ green |
| 48-02-01 | 02 | 1 | SCHED-03 | manual | Visual verification via Docker stack (Playwright) | N/A | ✅ green |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [x] `agent_service/tests/test_scheduler_service.py` — 6 new test functions covering SCHED-01 (4 cases), SCHED-02 (1 case), SCHED-04 (1 case)
- Existing `conftest.py` and `db_session` fixture are reusable — no new test infrastructure needed

*Existing infrastructure covers all phase requirements except new test stubs.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Confirmation modal appears before DRAFT save | SCHED-03 | React UI intercept logic; not unit-testable without browser | Edit a job script in the UI without providing a new signature → verify modal appears with correct copy; click Cancel → form preserved; click "Save & Go to DRAFT" → job transitions to DRAFT |
| Re-sign inline dialog on DRAFT rows | SCHED-03 | UI flow | Open JobDefinitionList → DRAFT row has amber badge + Re-sign button → clicking opens dialog → submitting valid signature activates job |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references
- [x] No watch-mode flags
- [x] Feedback latency < 15s
- [x] `nyquist_compliant: true` set in frontmatter

**Bug found during Playwright test:** `JobDefinitions.tsx` was sending the stale signature with the changed script on "Save & Go to DRAFT", causing a 422 from the backend. Fixed by stripping `signature`/`signature_id` from the PATCH payload in the DRAFT save path.

**Approval:** PASSED — 2026-03-22
