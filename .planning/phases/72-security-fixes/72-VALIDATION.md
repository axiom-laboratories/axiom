---
phase: 72
slug: security-fixes
status: complete
nyquist_compliant: true
wave_0_complete: true
created: 2026-03-26
validated: 2026-03-27
---

# Phase 72 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest + anyio (async) |
| **Config file** | `puppeteer/pyproject.toml` |
| **Quick run command** | `cd puppeteer && pytest agent_service/tests/test_security.py agent_service/tests/test_pii.py -x` |
| **Full suite command** | `cd puppeteer && pytest` |
| **Estimated runtime** | ~30 seconds |

---

## Sampling Rate

- **After every task commit:** Run `cd puppeteer && pytest agent_service/tests/test_security.py agent_service/tests/test_pii.py -x`
- **After every plan wave:** Run `cd puppeteer && pytest`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 72-01-01 | 01 | 0 | SEC-01 | unit | `cd puppeteer && pytest agent_service/tests/test_device_xss.py -x` | ✅ | ✅ green |
| 72-01-02 | 01 | 0 | SEC-02 | unit | `cd puppeteer && pytest agent_service/tests/test_vault_traversal.py -x` | ✅ | ✅ green |
| 72-01-03 | 01 | 0 | SEC-03 | unit | `cd puppeteer && pytest agent_service/tests/test_docs_traversal.py -x` | ✅ | ✅ green |
| 72-01-04 | 01 | 0 | SEC-04 | unit | `cd puppeteer && pytest agent_service/tests/test_pii.py -x` | ✅ | ✅ green |
| 72-01-05 | 01 | 0 | SEC-05 | unit | `cd puppeteer && pytest agent_service/tests/test_security.py -x` | ✅ | ✅ green |
| 72-01-06 | 01 | 0 | SEC-06 | unit | `cd puppeteer && pytest agent_service/tests/test_csv_nosniff.py -x` | ✅ | ✅ green |
| 72-01-07 | 01 | 1 | SEC-01 | unit | `cd puppeteer && pytest agent_service/tests/test_device_xss.py -x` | ✅ | ✅ green |
| 72-01-08 | 01 | 1 | SEC-02,03 | unit | `cd puppeteer && pytest agent_service/tests/test_vault_traversal.py agent_service/tests/test_docs_traversal.py -x` | ✅ | ✅ green |
| 72-01-09 | 01 | 1 | SEC-04 | unit (timing) | `cd puppeteer && pytest agent_service/tests/test_pii.py -x` | ✅ | ✅ green |
| 72-01-10 | 01 | 1 | SEC-05 | unit | `cd puppeteer && pytest agent_service/tests/test_security.py -x` | ✅ | ✅ green |
| 72-01-11 | 01 | 1 | SEC-06 | unit | `cd puppeteer && pytest agent_service/tests/test_csv_nosniff.py -x` | ✅ | ✅ green |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [x] `puppeteer/agent_service/tests/test_device_xss.py` — stubs for SEC-01 (HTML escaping in GET /auth/device/approve)
- [x] `puppeteer/agent_service/tests/test_vault_traversal.py` — stubs for SEC-02 (vault path traversal guard)
- [x] `puppeteer/agent_service/tests/test_docs_traversal.py` — stubs for SEC-03 (docs route path traversal guard)
- [x] `puppeteer/agent_service/tests/test_csv_nosniff.py` — stubs for SEC-06 (X-Content-Type-Options: nosniff header)
- [x] Add ReDoS timing test stub to `puppeteer/agent_service/tests/test_pii.py` — SEC-04
- [x] Update `puppeteer/agent_service/tests/test_security.py` — remove `API_KEY` import/assertion stubs — SEC-05

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| GitHub Security tab shows all 6 alerts resolved | SEC-01–06 | Requires GitHub UI + CI run | After merging fixes to main, navigate to Security → Code scanning → confirm 0 open alerts |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references
- [x] No watch-mode flags
- [x] Feedback latency < 30s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** 2026-03-27 — 19/19 tests passing, all 6 SEC requirements covered by automated tests

---

## Validation Audit 2026-03-27

| Metric | Count |
|--------|-------|
| Gaps found | 0 |
| Resolved | 0 |
| Escalated | 0 |
| Total tests passing | 19 |
