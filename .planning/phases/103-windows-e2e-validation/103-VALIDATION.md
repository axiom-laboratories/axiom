---
phase: 103
slug: windows-e2e-validation
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-31
---

# Phase 103 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (backend) + vitest (frontend) for regression; live E2E SSH run for phase validation |
| **Config file** | `puppeteer/pytest.ini` (backend), `puppeteer/dashboard/vite.config.ts` (frontend) |
| **Quick run command** | `cd puppeteer && pytest tests/ -x -q` |
| **Full suite command** | `cd puppeteer && pytest && cd puppeteer/dashboard && npm run test` |
| **Estimated runtime** | ~60 seconds (unit suite); ~20 min (full Windows E2E run) |

---

## Sampling Rate

- **After every task commit:** Run `cd puppeteer && pytest tests/ -x -q`
- **After every plan wave:** Run `cd puppeteer && pytest && cd puppeteer/dashboard && npm run test`
- **Before `/gsd:verify-work`:** Full suite must be green + Windows E2E golden path completes
- **Max feedback latency:** 60 seconds (unit suite)

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 103-01 | 01 | 0 | WIN-01, WIN-02 | scaffold | `ls mop_validation/scripts/run_windows_scenario.py` | ❌ W0 | ⬜ pending |
| 103-02 | 01 | 0 | WIN-01 | scaffold | `ls mop_validation/scripts/run_windows_e2e.py` | ❌ W0 | ⬜ pending |
| 103-03 | 01 | 0 | WIN-02 | scaffold | `ls mop_validation/scripts/windows_validation_prompt.md` | ❌ W0 | ⬜ pending |
| 103-04 | 01 | 1 | WIN-01 | E2E live SSH | `python3 mop_validation/scripts/run_windows_e2e.py` | ❌ W0 | ⬜ pending |
| 103-05 | 01 | 1 | WIN-02 | E2E subagent | subagent constrained to PWSH — verified by validation run | ❌ W0 | ⬜ pending |
| 103-06 | 01 | 1 | WIN-03 | E2E live API | `get_token_dwight("admin")` returns `must_change_password: true` | ❌ W0 | ⬜ pending |
| 103-07 | 01 | 1 | WIN-04 | E2E live API | `verify_node_online(token)` returns True | ❌ W0 | ⬜ pending |
| 103-08 | 01 | 1 | WIN-05 | E2E live API | `verify_job_completed(token, job_id)["status"] == "COMPLETED"` | ❌ W0 | ⬜ pending |
| 103-09 | 01 | 2 | WIN-06 | report artifact | `FRICTION-WIN-103.md` produced; zero BLOCKERs remain | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `mop_validation/scripts/run_windows_scenario.py` — paramiko helper library (dwight_exec, dwight_push, wait_for_stack_dwight)
- [ ] `mop_validation/scripts/run_windows_e2e.py` — Phase 103 Windows orchestrator
- [ ] `mop_validation/scripts/windows_validation_prompt.md` — Claude subagent persona + Windows golden path
- [ ] Add Dwight credentials to `mop_validation/secrets.env`: `dwight_ip=192.168.50.149`, `dwight_username`, `dwight_password`, `dwight_ssh_key`
- [ ] `pip install paramiko requests` — ensure available in mop_validation Python environment
- [ ] PowerShell tabs added to `enroll-node.md` (CLI tab + Option B notes)
- [ ] PowerShell tabs added to `first-job.md` (Step 0 + Manual Setup)
- [ ] `synthesise_friction.py --files` patch — if not already applied in Phase 102

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Windows Docker Desktop TLS cert SAN covers `host.docker.internal` | WIN-04 | Live Dwight network inspection required | SSH to Dwight; `openssl s_client -connect host.docker.internal:8001` and verify SAN |
| PowerShell forced password change prompt displays | WIN-03 | Browser UI on remote Windows host | Subagent captures screenshot or HTML evidence during validation run |
| Node appears ONLINE in Nodes view | WIN-04 | Live dashboard state | Subagent verifies via API `GET /nodes` + Playwright screenshot if available |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 60s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
