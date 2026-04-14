---
phase: 138
slug: hmac-keyed-boot-log
status: complete
nyquist_compliant: true
wave_0_complete: true
created: 2026-04-12
---

# Phase 138 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x |
| **Config file** | `puppeteer/pytest.ini` (or pyproject.toml) |
| **Quick run command** | `cd puppeteer && pytest tests/test_licence_service.py -x -q` |
| **Full suite command** | `cd puppeteer && pytest -x -q` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `cd puppeteer && pytest tests/test_licence_service.py -x -q`
- **After every plan wave:** Run `cd puppeteer && pytest -x -q`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 138-01-01 | 01 | 0 | HMAC write | unit | `cd puppeteer && pytest tests/test_licence_service.py -k "hmac" -x -q` | ❌ W0 | ⬜ pending |
| 138-01-02 | 01 | 0 | HMAC verify on read | unit | `cd puppeteer && pytest tests/test_licence_service.py -k "hmac_verify" -x -q` | ❌ W0 | ⬜ pending |
| 138-01-03 | 01 | 0 | Mixed legacy+HMAC coexistence | unit | `cd puppeteer && pytest tests/test_licence_service.py -k "mixed" -x -q` | ❌ W0 | ⬜ pending |
| 138-01-04 | 01 | 0 | HMAC mismatch strict (EE) | unit | `cd puppeteer && pytest tests/test_licence_service.py -k "mismatch_strict" -x -q` | ❌ W0 | ⬜ pending |
| 138-01-05 | 01 | 0 | HMAC mismatch lax (CE) | unit | `cd puppeteer && pytest tests/test_licence_service.py -k "mismatch_lax" -x -q` | ❌ W0 | ⬜ pending |
| 138-01-06 | 01 | 0 | Legacy warning on last entry | unit | `cd puppeteer && pytest tests/test_licence_service.py -k "legacy_warning" -x -q` | ❌ W0 | ⬜ pending |
| 138-01-07 | 01 | 1 | _compute_hmac implementation | unit | `cd puppeteer && pytest tests/test_licence_service.py -x -q` | ✅ | ⬜ pending |
| 138-01-08 | 01 | 1 | check_and_record_boot HMAC path | unit | `cd puppeteer && pytest tests/test_licence_service.py -x -q` | ✅ | ⬜ pending |
| 138-01-09 | 01 | 1 | Full regression (existing tests pass) | regression | `cd puppeteer && pytest tests/test_licence_service.py -x -q` | ✅ | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_licence_service.py` — add 6 HMAC-specific test stubs (hmac_write, hmac_verify, mixed_format, mismatch_strict, mismatch_lax, legacy_warning)
- [ ] Verify `ENCRYPTION_KEY` fixture is available in test scope (mock env var `ENCRYPTION_KEY=test_key_32_bytes_padded_00000000`)

*Existing pytest infrastructure covers everything else — no new conftest.py needed.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Boot log upgrade on running stack | Phase 138 migration | Requires live Docker stack with existing SHA256 boot.log | Start stack, check first new entry has `hmac:` prefix, verify old entries still present and accepted |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
