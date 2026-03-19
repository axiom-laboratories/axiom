---
phase: 29
slug: backend-completeness-output-capture-retry-wiring
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-18
---

# Phase 29 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest + pytest-asyncio |
| **Config file** | `puppeteer/pyproject.toml` |
| **Quick run command** | `cd puppeteer && /home/thomas/Development/master_of_puppets/.venv/bin/pytest tests/test_execution_record.py tests/test_output_capture.py tests/test_retry_wiring.py -q` |
| **Full suite command** | `cd puppeteer && /home/thomas/Development/master_of_puppets/.venv/bin/pytest -q` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `cd puppeteer && /home/thomas/Development/master_of_puppets/.venv/bin/pytest tests/test_execution_record.py tests/test_output_capture.py tests/test_retry_wiring.py -q`
- **After every plan wave:** Run `cd puppeteer && /home/thomas/Development/master_of_puppets/.venv/bin/pytest -q`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 29-W0-stubs | Wave 0 | 0 | OUTPUT-01, OUTPUT-02, RETRY-01, RETRY-02 | setup | `pytest tests/test_output_capture.py tests/test_retry_wiring.py tests/test_direct_mode_removal.py -q` | ❌ W0 | ⬜ pending |
| 29-01 | schema | 1 | OUTPUT-02, RETRY-02 | unit | `pytest tests/test_execution_record.py tests/test_output_capture.py -q` | ❌ W0 | ⬜ pending |
| 29-02 | report_result | 1 | OUTPUT-01, OUTPUT-02, RETRY-02 | unit | `pytest tests/test_output_capture.py tests/test_retry_wiring.py -q` | ❌ W0 | ⬜ pending |
| 29-03 | pull_work | 1 | RETRY-01 | unit | `pytest tests/test_retry_wiring.py::test_work_response_has_retry_fields -x` | ❌ W0 | ⬜ pending |
| 29-04 | node changes | 1 | OUTPUT-01 | unit | `pytest tests/test_output_capture.py::test_node_computes_script_hash tests/test_direct_mode_removal.py -q` | ❌ W0 | ⬜ pending |
| 29-05 | migration | 1 | OUTPUT-02, RETRY-02 | manual | `cat puppeteer/migration_v32.sql` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `puppeteer/tests/test_output_capture.py` — stubs for OUTPUT-01, OUTPUT-02 (columns, extraction ordering, script_hash dual verification)
- [ ] `puppeteer/tests/test_retry_wiring.py` — stubs for RETRY-01, RETRY-02 (WorkResponse fields, attempt_number, job_run_id stability)
- [ ] `puppeteer/tests/test_direct_mode_removal.py` — stub for startup guard when EXECUTION_MODE=direct

*Existing infrastructure: `tests/test_execution_record.py` covers 10 passing tests — must remain green throughout.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| migration_v32.sql applies cleanly to existing DB | OUTPUT-02, RETRY-02 | Requires live DB with existing rows | Run `psql $DATABASE_URL < puppeteer/migration_v32.sql` and confirm no errors; check existing execution_records rows have NULL in new columns |
| mop_validation node compose files updated to docker mode | OUTPUT-01 | Runtime environment change, not unit-testable | Inspect `node_alpha/node-compose.yaml`, `node_beta/node-compose.yaml`, `node_gamma/node-compose.yaml` — confirm `EXECUTION_MODE=docker` in each |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
