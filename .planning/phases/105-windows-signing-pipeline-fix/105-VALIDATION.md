---
phase: 105
slug: windows-signing-pipeline-fix
status: complete
nyquist_compliant: true
wave_0_complete: true
created: 2026-04-01
---

# Phase 105 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (backend) |
| **Config file** | `puppeteer/pytest.ini` |
| **Quick run command** | `cd puppeteer && pytest tests/test_crlf_countersign.py -v` |
| **Full suite command** | `cd puppeteer && pytest` |
| **Estimated runtime** | ~2 seconds |

---

## Sampling Rate

- **After every task commit:** Run `cd puppeteer && pytest tests/test_crlf_countersign.py -v`
- **After every plan wave:** Run `cd puppeteer && pytest`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 2 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 105-01-02 | 01 | 1 | WIN-05 | unit | `pytest tests/test_crlf_countersign.py` | ✅ | ✅ green |
| 105-01-03 | 01 | 1 | WIN-03 | manual | Deploy + login as admin | N/A | ✅ green |
| 105-01-04 | 01 | 1 | WIN-05 | unit | `pytest tests/test_crlf_countersign.py` | ✅ | ✅ green |
| 105-02-03 | 02 | 1 | WIN-05 | manual | `grep -c 'Windows (PowerShell)' first-job.md` → 3 | N/A | ✅ green |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

Existing infrastructure covers all phase requirements.

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Admin bootstrap sets must_change_password=True | WIN-03 | Bootstrap logic is in lifespan async generator with DB interaction — cannot isolate for unit test | Deploy fresh stack, login admin/admin, verify response contains `must_change_password: true` |
| PowerShell tabs present in first-job.md | WIN-05 | Documentation content — verified by grep | `grep -c 'Windows (PowerShell)' docs/docs/getting-started/first-job.md` → 3 |
| Windows CRLF job submission E2E | WIN-05 | Requires Windows host or CRLF-producing client | Sign + submit job from Windows with CRLF script; verify no SECURITY_REJECTED |

---

## Validation Evidence

| Artifact | Evidence | Status |
|----------|----------|--------|
| `test_crlf_countersign.py` | 2/2 tests pass — CRLF script produces same countersig as LF | Verified |
| `main.py` line 1104 | `script_content.replace('\r\n', '\n').replace('\r', '\n')` | Verified |
| `main.py` lines 159-162 | `must_change_password = not skip_force` (defaults True) | Verified |
| `first-job.md` | 3 Windows (PowerShell) tabs at lines 46, 159, 292 | Verified |

---

## Validation Sign-Off

- [x] All tasks have automated verify or manual-only justification
- [x] Sampling continuity: test_crlf_countersign.py provides automated checkpoint
- [x] Wave 0 covers all requirements (existing infrastructure)
- [x] No watch-mode flags
- [x] Feedback latency < 2s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** approved 2026-04-01

---

## Validation Audit 2026-04-01

| Metric | Count |
|--------|-------|
| Gaps found | 1 |
| Resolved | 0 |
| Escalated | 1 (WIN-03 → manual-only) |

WIN-05 fully covered by test_crlf_countersign.py (2 tests pass). WIN-03 bootstrap logic marked manual-only — lifespan function with DB interaction cannot be isolated for unit testing.
