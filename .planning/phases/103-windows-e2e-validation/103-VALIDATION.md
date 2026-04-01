---
phase: 103
slug: windows-e2e-validation
status: complete
nyquist_compliant: true
wave_0_complete: true
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
| **E2E orchestrator** | `python3 mop_validation/scripts/run_windows_e2e.py` |
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
| 103-01 | 01 | 0 | WIN-01, WIN-02 | scaffold | `ls mop_validation/scripts/run_windows_scenario.py` | ✅ | ✅ green |
| 103-02 | 01 | 0 | WIN-01 | scaffold | `ls mop_validation/scripts/run_windows_e2e.py` | ✅ | ✅ green |
| 103-03 | 01 | 0 | WIN-02 | scaffold | `ls mop_validation/scripts/windows_validation_prompt.md` | ✅ | ✅ green |
| 103-04 | 02 | 1 | WIN-01 | E2E live SSH | `python3 mop_validation/scripts/run_windows_e2e.py` | ✅ | ✅ green |
| 103-05 | 02 | 1 | WIN-02 | E2E subagent | subagent constrained to PWSH — verified by validation run | ✅ | ✅ green |
| 103-06 | 03 | 1 | WIN-03 | E2E live API | PATCH /auth/me forced-change flow verified in Run 3/4 | ✅ | ✅ green |
| 103-07 | 03 | 1 | WIN-04 | E2E live API | Run 8: node-26d9e8cd enrolled and ONLINE | ✅ | ✅ green |
| 103-08 | 03 | 1 | WIN-05 | E2E live API | Run 8: job f90aa388 completed exit_code 0 | ✅ | ✅ green |
| 103-09 | 04 | 2 | WIN-06 | report artifact | FRICTION-WIN-103.md: 8 BLOCKERs all fixed, Verdict: PASS | ✅ | ✅ green |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

> **Note:** WIN-01 through WIN-06 are validated by live E2E SSH runs to Dwight (Windows host), not by unit tests. The CRLF normalization code change from this phase has a dedicated unit test in `test_crlf_countersign.py` (Phase 105).

---

## Wave 0 Requirements

- [x] `mop_validation/scripts/run_windows_scenario.py` — paramiko helper library
- [x] `mop_validation/scripts/run_windows_e2e.py` — Phase 103 Windows orchestrator
- [x] `mop_validation/scripts/windows_validation_prompt.md` — Claude subagent persona + Windows golden path
- [x] `mop_validation/scripts/invoke_subagent.ps1` — PowerShell wrapper for Claude CLI
- [x] PowerShell tabs added to `enroll-node.md` and `first-job.md`
- [x] `synthesise_friction.py --files` patch applied (Phase 102)

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Windows Docker stack cold-start | WIN-01 | Requires live SSH to Dwight + Docker Desktop | Run `python3 mop_validation/scripts/run_windows_e2e.py`; check stack starts |
| All interactions use PowerShell | WIN-02 | Validation prompt enforces PWSH-only persona | Subagent uses only Invoke-RestMethod, pwsh syntax |
| Forced password change prompt | WIN-03 | Requires live API + browser UI on Windows | PATCH /auth/me verified in Run 3/4; bootstrap fix in Phase 105 |
| Node enrollment on Dwight | WIN-04 | mTLS + Docker networking on Windows | Run 8: node enrolled and ONLINE via GET /nodes |
| First job dispatches and completes | WIN-05 | Full signing pipeline on Windows host | Run 8: job completed with exit_code 0, sig verified |
| All friction catalogued and fixed | WIN-06 | Iterative SSH runs with fix-verify cycles | FRICTION-WIN-103.md: 8 BLOCKERs fixed; synthesis: READY |

---

## Validation Evidence

| Artifact | Location | Status |
|----------|----------|--------|
| FRICTION-WIN-103.md | `mop_validation/reports/FRICTION-WIN-103.md` | Verdict: PASS — 8 BLOCKERs all fixed across 8 runs |
| Synthesis report | `mop_validation/reports/windows_e2e_synthesis.md` | Verdict: READY — 0 open product BLOCKERs |
| E2E orchestrator | `mop_validation/scripts/run_windows_e2e.py` | Syntax OK, imports from run_windows_scenario |
| Validation prompt | `mop_validation/scripts/windows_validation_prompt.md` | 286 lines, 5-step golden path, PowerShell-only persona |
| Subagent wrapper | `mop_validation/scripts/invoke_subagent.ps1` | PowerShell wrapper using Get-Content |

---

## Validation Sign-Off

- [x] All tasks have E2E verify or Wave 0 dependencies
- [x] Sampling continuity: E2E orchestrator covers all requirements in single run
- [x] Wave 0 covers all infrastructure requirements
- [x] No watch-mode flags
- [x] Feedback latency < 60s (unit suite)
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** approved 2026-04-01

---

## Validation Audit 2026-04-01

| Metric | Count |
|--------|-------|
| Gaps found | 0 |
| Resolved | 0 |
| Escalated | 0 |

All 6 requirements are E2E/manual-only with clear justification. The validation infrastructure (orchestrator + FRICTION file + synthesis report) provides the verification evidence. No unit-testable gaps identified.
