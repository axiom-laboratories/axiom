---
phase: 30
slug: runtime-attestation
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-18
---

# Phase 30 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (existing) |
| **Config file** | `puppeteer/` — run from that directory |
| **Quick run command** | `cd puppeteer && pytest tests/test_attestation.py -x` |
| **Full suite command** | `cd puppeteer && pytest` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `cd puppeteer && pytest tests/test_attestation.py -x`
- **After every plan wave:** Run `cd puppeteer && pytest`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 30-W0-01 | W0 | 0 | OUTPUT-05 | unit | `cd puppeteer && pytest tests/test_attestation.py -x` | ❌ W0 | ⬜ pending |
| 30-01-01 | 01 | 1 | OUTPUT-05 | unit | `cd puppeteer && pytest tests/test_attestation.py::test_attestation_rsa_roundtrip -x` | ❌ W0 | ⬜ pending |
| 30-01-02 | 01 | 1 | OUTPUT-05 | unit | `cd puppeteer && pytest tests/test_attestation.py::test_bundle_deterministic -x` | ❌ W0 | ⬜ pending |
| 30-01-03 | 01 | 1 | OUTPUT-05 | unit | `cd puppeteer && pytest tests/test_attestation.py::test_cert_serial_matches -x` | ❌ W0 | ⬜ pending |
| 30-02-01 | 02 | 2 | OUTPUT-06 | unit | `cd puppeteer && pytest tests/test_attestation.py::test_attestation_mutation_fails -x` | ❌ W0 | ⬜ pending |
| 30-02-02 | 02 | 2 | OUTPUT-06 | source inspection | `cd puppeteer && pytest tests/test_attestation.py::test_execution_record_has_attestation_columns -x` | ❌ W0 | ⬜ pending |
| 30-02-03 | 02 | 2 | OUTPUT-06 | unit | `cd puppeteer && pytest tests/test_attestation.py::test_revoked_cert_stores_failed -x` | ❌ W0 | ⬜ pending |
| 30-03-01 | 03 | 2 | OUTPUT-07 | unit | `cd puppeteer && pytest tests/test_attestation.py::test_attestation_export_endpoint -x` | ❌ W0 | ⬜ pending |
| 30-03-02 | 03 | 2 | OUTPUT-07 | unit | `cd puppeteer && pytest tests/test_attestation.py::test_attestation_export_missing -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `puppeteer/tests/test_attestation.py` — stubs for OUTPUT-05, OUTPUT-06, OUTPUT-07 (full new file covering all attestation behaviors)

*Existing pytest infrastructure covers the framework requirement — only the test file is new.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Node actually submits attestation bundle on a live job run | OUTPUT-05 | Requires live node + job execution | Run a signed job via mop_validation, inspect the execution record in DB or via GET /api/executions/{id}/attestation |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
