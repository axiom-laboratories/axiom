---
phase: 102
slug: linux-e2e-validation
status: complete
nyquist_compliant: true
wave_0_complete: true
created: 2026-03-31
---

# Phase 102 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (backend) + vitest (frontend) + live LXC E2E orchestrator |
| **Config file** | `puppeteer/pytest.ini` (backend), `puppeteer/dashboard/vite.config.ts` (frontend) |
| **Quick run command** | `cd puppeteer && pytest tests/ -x -q` |
| **Full suite command** | `cd puppeteer && pytest && cd dashboard && npm run test` |
| **E2E orchestrator** | `python3 mop_validation/scripts/run_linux_e2e.py` |
| **Estimated runtime** | ~5–10 min per LXC golden path iteration |

---

## Sampling Rate

- **After every task commit:** Run `cd puppeteer && pytest tests/ -x -q`
- **After every plan wave:** Run `cd puppeteer && pytest && cd dashboard && npm run test`
- **Per E2E iteration:** Full LXC golden path run (`python3 mop_validation/scripts/run_linux_e2e.py`)
- **Before `/gsd:verify-work`:** Full suite must be green + zero BLOCKER friction points in `FRICTION-LNX-102.md`
- **Max feedback latency:** ~600 seconds (E2E run)

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 102-01-01 | 01 | 0 | LNX-01 | E2E | `python3 mop_validation/scripts/run_linux_e2e.py` | ✅ | ✅ green |
| 102-01-02 | 01 | 0 | LNX-06 | artifact | FRICTION-LNX-102.md produced | ✅ | ✅ green |
| 102-02-01 | 02 | 1 | LNX-01 | E2E | subagent golden path run | ✅ | ✅ green |
| 102-02-02 | 02 | 1 | LNX-02 | E2E | subagent validation run | ✅ | ✅ green |
| 102-02-03 | 02 | 1 | LNX-03 | E2E | subagent validation run | ✅ | ✅ green |
| 102-02-04 | 02 | 1 | LNX-04 | E2E | subagent validation run | ✅ | ✅ green |
| 102-02-05 | 02 | 1 | LNX-05 | E2E | subagent validation run | ✅ | ✅ green |
| 102-03-01 | 03 | 2 | LNX-06 | report | FRICTION-LNX-102.md zero BLOCKERs | ✅ | ✅ green |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

> **Note:** LNX-01 through LNX-06 are validated by a live E2E run in the LXC environment, not by unit or component tests. The "test" for this phase is the validation orchestrator script and the resulting FRICTION file. The server-side countersign code change has a dedicated unit test in `test_crlf_countersign.py` (Phase 105).

---

## Wave 0 Requirements

- [x] `mop_validation/scripts/run_linux_e2e.py` — Phase 102 orchestrator script
- [x] `mop_validation/scripts/linux_validation_prompt.md` — Claude subagent persona + golden path instructions
- [x] `synthesise_friction.py` — patched with `--files` argument for single-file use

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Cold-start deploy via docs | LNX-01 | Requires live LXC container + network pull of GHCR images | Run `python3 mop_validation/scripts/run_linux_e2e.py` from host; check container reaches dashboard |
| admin/admin forced password change | LNX-02 | Browser interaction in LXC headless env; must_change_password flow requires live API | Subagent golden path checks ForceChangeModal trigger after first login |
| Node enrollment appears ONLINE | LNX-03 | mTLS cert exchange, live Docker networking, DinD environment | Subagent checks Nodes view after `docker compose up` on node |
| First job reaches COMPLETED | LNX-04 | Full job dispatch + worker execution loop, Ed25519 signing pipeline | Subagent dispatches signed Python job and polls status |
| All CE features accessible | LNX-05 | UI navigation across all views in live stack | Subagent navigates each documented CE route, reports 404s or blank panels |
| All friction catalogued and fixed | LNX-06 | Requires iterative LXC runs with fix-verify cycles | FRICTION-LNX-102.md Verdict: PASS + linux_e2e_synthesis.md Verdict: READY |

---

## Validation Evidence

| Artifact | Location | Status |
|----------|----------|--------|
| FRICTION-LNX-102.md | `mop_validation/reports/FRICTION-LNX-102.md` | Verdict: PASS — 7 findings, 4 BLOCKERs all fixed |
| Synthesis report | `mop_validation/reports/linux_e2e_synthesis.md` | Verdict: READY — 0 open product BLOCKERs |
| E2E orchestrator | `mop_validation/scripts/run_linux_e2e.py` | 400 lines, syntax OK |
| Validation prompt | `mop_validation/scripts/linux_validation_prompt.md` | 262 lines, 7-step golden path |

---

## Validation Sign-Off

- [x] All tasks have E2E verify or Wave 0 dependencies
- [x] Sampling continuity: E2E orchestrator covers all requirements in single run
- [x] Wave 0 covers all infrastructure requirements
- [x] No watch-mode flags
- [x] Feedback latency < 600s
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
