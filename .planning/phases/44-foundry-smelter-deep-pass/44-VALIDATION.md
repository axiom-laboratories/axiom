---
phase: 44
slug: foundry-smelter-deep-pass
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-21
---

# Phase 44 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (mop_validation) + playwright sync_api |
| **Config file** | none — scripts are standalone |
| **Quick run command** | `python mop_validation/scripts/verify_foundry_01_wizard.py` |
| **Full suite command** | `python mop_validation/scripts/run_foundry_matrix.py` |
| **Estimated runtime** | ~120–180 seconds (includes Docker build waits) |

---

## Sampling Rate

- **After every task commit:** Run the specific `verify_foundry_NN_*.py` script for that task
- **After every plan wave:** Run `python mop_validation/scripts/run_foundry_matrix.py`
- **Before `/gsd:verify-work`:** Full matrix must show 6/6 (or documented SKIP/PASS-GAP)
- **Max feedback latency:** 180 seconds (build-constrained)

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 44-01-01 | 01 | 1 | FOUNDRY-01 | integration + e2e | `python mop_validation/scripts/verify_foundry_01_wizard.py` | ❌ W0 | ⬜ pending |
| 44-01-02 | 01 | 1 | FOUNDRY-02 | integration | `python mop_validation/scripts/verify_foundry_02_strict_cve.py` | ❌ W0 | ⬜ pending |
| 44-01-03 | 01 | 1 | FOUNDRY-03 | integration | `python mop_validation/scripts/verify_foundry_03_build_failure.py` | ❌ W0 | ⬜ pending |
| 44-01-04 | 01 | 1 | FOUNDRY-04 | integration | `python mop_validation/scripts/verify_foundry_04_build_dir.py` | ❌ W0 | ⬜ pending |
| 44-01-05 | 01 | 1 | FOUNDRY-05 | integration | `python mop_validation/scripts/verify_foundry_05_airgap.py` | ❌ W0 | ⬜ pending |
| 44-01-06 | 01 | 1 | FOUNDRY-06 | integration | `python mop_validation/scripts/verify_foundry_06_warning.py` | ❌ W0 | ⬜ pending |
| 44-02-01 | 02 | 2 | all | integration | `python mop_validation/scripts/run_foundry_matrix.py` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `mop_validation/scripts/verify_foundry_01_wizard.py` — FOUNDRY-01 API + Playwright wizard
- [ ] `mop_validation/scripts/verify_foundry_02_strict_cve.py` — FOUNDRY-02 STRICT CVE block
- [ ] `mop_validation/scripts/verify_foundry_03_build_failure.py` — FOUNDRY-03 bad base image → 500
- [ ] `mop_validation/scripts/verify_foundry_04_build_dir.py` — FOUNDRY-04 MIN-7 gap documentation
- [ ] `mop_validation/scripts/verify_foundry_05_airgap.py` — FOUNDRY-05 iptables block + mirror
- [ ] `mop_validation/scripts/verify_foundry_06_warning.py` — FOUNDRY-06 WARNING mode + audit log
- [ ] `mop_validation/scripts/run_foundry_matrix.py` — orchestrator runner (6/6 summary)

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| iptables block confirms pypi.org unreachable | FOUNDRY-05 | Requires sudo on Docker host; curl inside container to verify | `docker exec puppeteer-agent-1 curl -sk https://pypi.org/ --max-time 5` should fail/timeout during test |
| Playwright wizard: build log visible in UI | FOUNDRY-01 | Browser state during live build | Script captures screenshot on failure; review `/tmp/foundry_wizard_*.png` |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 180s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
