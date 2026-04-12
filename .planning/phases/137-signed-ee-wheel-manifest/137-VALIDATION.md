---
phase: 137
slug: signed-ee-wheel-manifest
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-12
---

# Phase 137 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x |
| **Config file** | `puppeteer/pytest.ini` (or `pyproject.toml`) |
| **Quick run command** | `cd puppeteer && pytest tests/test_ee_manifest.py -x -q` |
| **Full suite command** | `cd puppeteer && pytest -x -q` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `cd puppeteer && pytest tests/test_ee_manifest.py -x -q`
- **After every plan wave:** Run `cd puppeteer && pytest -x -q`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 137-01-01 | 01 | 1 | EE-01 | unit | `cd puppeteer && pytest tests/test_ee_manifest.py::test_missing_manifest -x -q` | ❌ W0 | ⬜ pending |
| 137-01-02 | 01 | 1 | EE-01 | unit | `cd puppeteer && pytest tests/test_ee_manifest.py::test_malformed_json -x -q` | ❌ W0 | ⬜ pending |
| 137-01-03 | 01 | 1 | EE-01 | unit | `cd puppeteer && pytest tests/test_ee_manifest.py::test_missing_fields -x -q` | ❌ W0 | ⬜ pending |
| 137-01-04 | 01 | 1 | EE-01 | unit | `cd puppeteer && pytest tests/test_ee_manifest.py::test_sha256_mismatch -x -q` | ❌ W0 | ⬜ pending |
| 137-01-05 | 01 | 1 | EE-01 | unit | `cd puppeteer && pytest tests/test_ee_manifest.py::test_invalid_signature -x -q` | ❌ W0 | ⬜ pending |
| 137-01-06 | 01 | 1 | EE-01 | unit | `cd puppeteer && pytest tests/test_ee_manifest.py::test_valid_manifest_installs -x -q` | ❌ W0 | ⬜ pending |
| 137-01-07 | 01 | 1 | EE-01 | unit | `cd puppeteer && pytest tests/test_ee_manifest.py::test_activation_error_field -x -q` | ❌ W0 | ⬜ pending |
| 137-01-08 | 01 | 1 | EE-01 | unit | `cd puppeteer && pytest tests/test_ee_manifest.py -x -q` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `puppeteer/tests/test_ee_manifest.py` — stubs for all EE-01 verification behaviors (missing manifest, malformed JSON, missing fields, SHA256 mismatch, invalid signature, valid install, ee_activation_error field)
- [ ] Inline test keypair generation fixture (no file dependencies) — generate fresh Ed25519 keypair inside conftest/test file

*Existing infrastructure (pytest, cryptography) covers all phase requirements — no new packages needed.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| `/admin/licence` response includes `ee_activation_error: null` on successful EE activation | EE-01 | Requires full Docker stack with valid EE wheel + manifest | Start stack, upload signed wheel + manifest, `GET /admin/licence`, confirm `ee_activation_error` is null |
| `/admin/licence` response includes `ee_activation_error` string on failed activation | EE-01 | Requires Docker stack with tampered/missing manifest | Start stack, deploy wheel without manifest, `GET /admin/licence`, confirm error message appears |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
