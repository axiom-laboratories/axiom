---
phase: 39
slug: ee-test-keypair-dev-install
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-20
---

# Phase 39 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (puppeteer/), Python scripts (mop_validation/) |
| **Config file** | `puppeteer/pytest.ini` or default |
| **Quick run command** | `python3 -c "import ee.plugin; print(ee.plugin._LICENCE_PUBLIC_KEY_BYTES[:4])"` |
| **Full suite command** | `cd puppeteer && pytest tests/test_licence.py -x` |
| **Estimated runtime** | ~10 seconds |

---

## Sampling Rate

- **After every task commit:** Run `python3 -c "import ee.plugin; print(ee.plugin._LICENCE_PUBLIC_KEY_BYTES[:4])"`
- **After every plan wave:** Run `cd puppeteer && pytest tests/test_licence.py -x`
- **Before `/gsd:verify-work`:** All 5 `verify_ee_install.py` PASS lines must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 39-01-01 | 01 | 0 | EEDEV-01 | smoke | `python3 mop_validation/scripts/generate_ee_keypair.py && ls mop_validation/secrets/ee/` | ❌ W0 | ⬜ pending |
| 39-01-02 | 01 | 0 | EEDEV-02 | smoke | `python3 mop_validation/scripts/patch_ee_source.py && python3 -c "import ee.plugin; assert ee.plugin._LICENCE_PUBLIC_KEY_BYTES != b'\x00'*32"` | ❌ W0 | ⬜ pending |
| 39-02-01 | 02 | 0 | EEDEV-03 | integration | `python3 mop_validation/scripts/verify_ee_install.py --case valid` | ❌ W0 | ⬜ pending |
| 39-02-02 | 02 | 1 | EEDEV-04 | integration | `python3 mop_validation/scripts/verify_ee_install.py --case expired` | ❌ W0 | ⬜ pending |
| 39-02-03 | 02 | 1 | EEDEV-05 | integration | `python3 mop_validation/scripts/verify_ee_install.py --case absent` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `mop_validation/scripts/generate_ee_keypair.py` — generates test Ed25519 keypair to `mop_validation/secrets/ee/`; covers EEDEV-01
- [ ] `mop_validation/scripts/patch_ee_source.py` — editable install + patch `_LICENCE_PUBLIC_KEY_BYTES`; covers EEDEV-02
- [ ] `mop_validation/scripts/generate_ee_licence.py` — generate signed test licence JWTs; covers EEDEV-03 prerequisite
- [ ] `mop_validation/scripts/verify_ee_install.py` — API-level verification for `--case valid`, `--case expired`, `--case absent`; covers EEDEV-03/04/05
- [ ] `mop_validation/secrets/ee/` directory — created at runtime by `generate_ee_keypair.py`

*All Wave 0 items are new scripts; existing test infrastructure is unaffected.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Stack restart with `AXIOM_LICENCE_KEY` injected | EEDEV-03, EEDEV-04 | Requires `docker compose down && docker compose up -d` between cases | Run `verify_ee_install.py --case valid`, restart stack with expired key env, run `--case expired` |
| Stack restart with no `AXIOM_LICENCE_KEY` | EEDEV-05 | Requires env var absent at compose startup | Unset `AXIOM_LICENCE_KEY` and restart, then run `--case absent` |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
