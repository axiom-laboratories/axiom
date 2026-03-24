---
phase: 48-scheduled-job-signing-safety
plan: "01"
subsystem: scheduler
tags: [tdd, security, draft-state, signing, scheduler]
dependency_graph:
  requires: []
  provides: [SCHED-01, SCHED-02, SCHED-04]
  affects: [scheduler_service, alert_service, audit_log]
tech_stack:
  added: []
  patterns: [soft-DRAFT-transition, AlertService.create_alert, raw-SQL-audit, TDD-red-green]
key_files:
  created: []
  modified:
    - puppeteer/agent_service/services/scheduler_service.py
    - puppeteer/agent_service/tests/test_scheduler_service.py
decisions:
  - "Raw SQL used for audit_log INSERT in execute_scheduled_job to preserve CE compatibility (ORM model is EE-only)"
  - "Re-sign path (case e) checked first before script_content block to handle signature+signature_id with no script change"
  - "Signature removal detection: signature_id changed + no signature payload -> DRAFT only when no_script_change and ACTIVE"
  - "test_draft_skip_log_message creates audit_log table manually via DDL (EE-only table, not in CE Base.metadata)"
metrics:
  duration: "4 minutes"
  completed: "2026-03-22"
  tasks_completed: 2
  files_changed: 2
---

# Phase 48 Plan 01: DRAFT Transition + Skip Log Compliance Summary

Replaced the hard HTTP 400 rejection in `update_job_definition()` with a soft DRAFT transition. Operators can now edit a scheduled job's script without immediately providing a new signature — the job moves to DRAFT status and cannot fire until re-signed. Added verbatim skip-log message compliance and Alert creation on ACTIVE→DRAFT transitions.

## Tasks Completed

| Task | Commit | Description |
|------|--------|-------------|
| RED — 7 failing tests | fce61f8 | Added 7 test functions to test_scheduler_service.py covering SCHED-01 (5 cases), SCHED-02, SCHED-04 |
| GREEN — implementation | 6f32955 | Updated scheduler_service.py: DRAFT transition logic, re-sign path, signature-removal detection, verbatim skip message |

## What Was Built

**scheduler_service.py — update_job_definition() restructured into 4 cases:**

- **Case (e) Re-sign**: `signature + signature_id + no script change` → verify signature against existing script → `status=ACTIVE`, audit reactivated
- **Case (a) Sig removal**: `signature_id changed + no signature payload + no script change` → `status=DRAFT`, Alert created (WARNING), audit drafted
- **Case (b/c) Script + sig**: new `script_content + signature + signature_id` → verify signature → update fields (existing path)
- **Case (d) Script no sig**: new `script_content` without signature → `status=DRAFT` (if ACTIVE), Alert created, audit drafted; if already DRAFT: update content only, no duplicate Alert

**scheduler_service.py — execute_scheduled_job() SKIP_STATUSES block:**
- Adds `reason` key to detail JSON with verbatim string `"Skipped: job in DRAFT state, pending re-signing"` for DRAFT jobs
- Uses raw SQL INSERT for audit_log (CE-safe — table absent silently ignored)

**test_scheduler_service.py — 7 new test functions:**
- All cover the plan's `<behavior>` section exactly
- `test_draft_skip_log_message` creates audit_log table via DDL before executing

## Test Results

```
7 new tests: ALL PASS
9 total scheduler tests: ALL PASS
Pre-existing suite failures: unchanged (11 pre-existing failures in ee_plugin, job_service, models, sec01, sec02)
```

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] ORM AuditLog import replaced with raw SQL in execute_scheduled_job**
- **Found during:** GREEN phase implementation
- **Issue:** `from ..db import AuditLog as _AuditLog` in `execute_scheduled_job()` would throw `ImportError` in CE mode — `AuditLog` ORM model is EE-only and not in `agent_service/db.py`. Adding it to `db.py` would break `test_ce_table_count` (enforces exactly 13 CE tables with `audit_log` explicitly listed as EE-only).
- **Fix:** Replaced ORM session.add with `await session.execute(text("INSERT INTO audit_log ..."))` wrapped in try/except — consistent with `audit()` in `deps.py`. In CE mode the table doesn't exist so the insert silently fails; in EE mode it succeeds.
- **Files modified:** `puppeteer/agent_service/services/scheduler_service.py`
- **Also:** Test `test_draft_skip_log_message` creates the `audit_log` table via DDL (`CREATE TABLE IF NOT EXISTS`) before executing to ensure verifiable behavior in the unit test context.
- **Commit:** 6f32955

## Self-Check: PASSED

- puppeteer/agent_service/services/scheduler_service.py: FOUND
- puppeteer/agent_service/tests/test_scheduler_service.py: FOUND
- .planning/phases/48-scheduled-job-signing-safety/48-01-SUMMARY.md: FOUND
- Commit fce61f8: FOUND
- Commit 6f32955: FOUND
