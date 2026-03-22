---
phase: 42
slug: ee-validation-pass
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-21
---

# Phase 42 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x (integration) + direct script execution |
| **Config file** | none — scripts are standalone |
| **Quick run command** | `python mop_validation/scripts/verify_ee_pass.py` |
| **Full suite command** | `python mop_validation/scripts/verify_ee_pass.py` |
| **Estimated runtime** | ~120 seconds (includes docker compose restart cycle for EEV-02) |

---

## Sampling Rate

- **After every task commit:** Run `python mop_validation/scripts/verify_ee_pass.py` (or the relevant sub-section)
- **After every plan wave:** Run `python mop_validation/scripts/verify_ee_pass.py`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 120 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 42-01-01 | 01 | 1 | EEV-03 | integration | `curl -s https://localhost:8001/api/licence -H "Authorization: Bearer $OPERATOR_TOKEN"` → expect 403 | ✅ | ⬜ pending |
| 42-01-02 | 01 | 1 | EEV-03 | integration | `docker compose -f puppeteer/compose.server.yaml build agent && up -d --no-build agent` | ✅ | ⬜ pending |
| 42-02-01 | 02 | 2 | EEV-01 | integration | `python mop_validation/scripts/verify_ee_pass.py` (EEV-01 section) | ❌ W0 | ⬜ pending |
| 42-02-02 | 02 | 2 | EEV-02 | integration | `python mop_validation/scripts/verify_ee_pass.py` (EEV-02 section) | ❌ W0 | ⬜ pending |
| 42-02-03 | 02 | 2 | EEV-03 | integration | `python mop_validation/scripts/verify_ee_pass.py` (EEV-03 section) | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `mop_validation/scripts/verify_ee_pass.py` — stubs for EEV-01, EEV-02, EEV-03

*Wave 0 creates the validation script. The backend patch (Plan 01) is a prerequisite for Plan 02.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Docker compose restart cycle timing | EEV-02 | Requires live Docker stack; automated in verify_ee_pass.py | Script handles the restart cycle automatically |

*All phase behaviours have automated verification via verify_ee_pass.py.*

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 120s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
