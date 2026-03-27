---
phase: 75
slug: secrets-volume-dead-code-cleanup
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-27
---

# Phase 75 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest |
| **Config file** | none — run from repo root with full import paths |
| **Quick run command** | `cd /home/thomas/Development/master_of_puppets && python -m pytest puppeteer/tests/test_licence_service.py -x -q` |
| **Full suite command** | `cd /home/thomas/Development/master_of_puppets && python -m pytest puppeteer/tests/ puppeteer/agent_service/tests/ -x -q` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `python -m pytest puppeteer/tests/test_licence_service.py -x -q`
- **After every plan wave:** Run `python -m pytest puppeteer/tests/ puppeteer/agent_service/tests/ -x -q`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 75-01-W0-01 | 01 | 0 | LIC-05 | unit | `python -m pytest puppeteer/tests/test_licence_service.py -x -q` | ✅ | ⬜ pending |
| 75-01-W0-02 | 01 | 0 | LIC-05 | unit | `python -m pytest puppeteer/tests/test_licence_service.py::test_check_and_record_boot_strict_ee -x` | ❌ W0 | ⬜ pending |
| 75-01-W0-03 | 01 | 0 | SEC-02 | unit | `python -m pytest puppeteer/agent_service/tests/test_vault_traversal.py -x` | ❌ W0 | ⬜ pending |
| 75-01-01 | 01 | 1 | LIC-05 | unit | `python -m pytest puppeteer/tests/test_licence_service.py -x -q` | ✅ | ⬜ pending |
| 75-01-02 | 01 | 1 | LIC-05 | unit | `python -m pytest puppeteer/tests/test_licence_service.py -x -q` | ✅ | ⬜ pending |
| 75-01-03 | 01 | 1 | SEC-02 | unit | `python -m pytest puppeteer/agent_service/tests/test_vault_traversal.py -x -q` | ✅ | ⬜ pending |
| 75-01-04 | 01 | 1 | SEC-02 | unit | `python -m pytest puppeteer/agent_service/tests/ -x -q` | ✅ | ⬜ pending |
| 75-01-05 | 01 | 1 | LIC-05 | manual | `docker compose down && docker compose up -d && docker exec agent cat /app/secrets/boot.log` | N/A | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `puppeteer/tests/test_licence_service.py` — update `test_clock_rollback_detection`: replace `AXIOM_STRICT_CLOCK` env var patch with `LicenceStatus.VALID` parameter call for strict-mode assertion
- [ ] `puppeteer/tests/test_licence_service.py` — add RED test `test_check_and_record_boot_strict_ee`: verifies `check_and_record_boot(LicenceStatus.VALID)` raises RuntimeError when rollback detected
- [ ] `puppeteer/agent_service/tests/test_vault_traversal.py` — add RED test `test_vault_service_deleted`: asserts `vault_service.py` does not exist OR that importing it fails (documents SEC-02 closure intent)

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| `secrets/boot.log` persists across `docker compose down && up` | LIC-05 | Docker E2E restart cycle not automatable in < 30s unit test | `docker compose down && docker compose up -d && sleep 5 && docker exec puppeteer-agent-1 cat /app/secrets/boot.log` — verify file exists and contains prior boot entry |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
