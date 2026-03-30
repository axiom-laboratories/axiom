---
phase: 91
slug: output-validation
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-30
---

# Phase 91 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x (backend), vitest (frontend) |
| **Config file** | `puppeteer/pytest.ini` / `puppeteer/dashboard/vite.config.ts` |
| **Quick run command** | `cd puppeteer && pytest tests/test_output_validation.py -x -q` |
| **Full suite command** | `cd puppeteer && pytest -x -q && cd dashboard && npx vitest run` |
| **Estimated runtime** | ~30 seconds |

---

## Sampling Rate

- **After every task commit:** Run `cd puppeteer && pytest tests/test_output_validation.py -x -q`
- **After every plan wave:** Run `cd puppeteer && pytest -x -q && cd dashboard && npx vitest run`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 91-01-01 | 01 | 1 | VALD-01 | unit | `cd puppeteer && pytest tests/test_output_validation.py::test_validation_rules_schema -x -q` | ❌ W0 | ⬜ pending |
| 91-01-02 | 01 | 1 | VALD-02 | unit | `cd puppeteer && pytest tests/test_output_validation.py::test_exit_code_validation -x -q` | ❌ W0 | ⬜ pending |
| 91-01-03 | 01 | 1 | VALD-02 | unit | `cd puppeteer && pytest tests/test_output_validation.py::test_regex_validation -x -q` | ❌ W0 | ⬜ pending |
| 91-01-04 | 01 | 1 | VALD-02 | unit | `cd puppeteer && pytest tests/test_output_validation.py::test_json_field_validation -x -q` | ❌ W0 | ⬜ pending |
| 91-01-05 | 01 | 1 | VALD-02 | unit | `cd puppeteer && pytest tests/test_output_validation.py::test_no_retry_on_validation_failure -x -q` | ❌ W0 | ⬜ pending |
| 91-01-06 | 01 | 1 | VALD-01 | unit | `cd puppeteer && pytest tests/test_output_validation.py::test_null_rules_unchanged -x -q` | ❌ W0 | ⬜ pending |
| 91-02-01 | 02 | 2 | VALD-01 | component | `cd puppeteer/dashboard && npx vitest run src/views/__tests__/JobDefinitions.test.tsx` | ✅ | ⬜ pending |
| 91-02-02 | 02 | 2 | VALD-03 | component | `cd puppeteer/dashboard && npx vitest run src/views/__tests__/JobDefinitions.test.tsx` | ✅ | ⬜ pending |
| 91-02-03 | 02 | 2 | VALD-03 | component | `cd puppeteer/dashboard && npx vitest run src/views/__tests__/History.test.tsx` | ✅ | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `puppeteer/tests/test_output_validation.py` — test stubs for all VALD-01/02 backend logic (exit code, regex, JSON field, retry suppression, null-rules passthrough)

*Frontend test files already exist — only test cases need adding.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Validation section collapses when no rules set, auto-expands when rules exist | VALD-01 | Visual/UX interaction | Open job definition modal with no rules → section collapsed; open with rules → section expanded |
| Job detail sheet shows "Validation failed: ..." label distinctly from runtime errors | VALD-03 | Visual distinction | Trigger a validation failure; check Jobs.tsx detail sheet shows orange validation label, not generic error text |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
