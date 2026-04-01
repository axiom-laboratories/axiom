---
phase: 102
slug: linux-e2e-validation
status: draft
nyquist_compliant: false
wave_0_complete: false
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
| 102-01-01 | 01 | 0 | LNX-01 | integration | `python3 mop_validation/scripts/run_linux_e2e.py` | ❌ W0 | ⬜ pending |
| 102-01-02 | 01 | 0 | LNX-06 | artifact | `FRICTION-LNX-102.md` produced | ❌ W0 | ⬜ pending |
| 102-02-01 | 02 | 1 | LNX-01 | manual/E2E | subagent golden path run | ❌ W0 | ⬜ pending |
| 102-02-02 | 02 | 1 | LNX-02 | manual/E2E | subagent validation run | ❌ W0 | ⬜ pending |
| 102-02-03 | 02 | 1 | LNX-03 | manual/E2E | subagent validation run | ❌ W0 | ⬜ pending |
| 102-02-04 | 02 | 1 | LNX-04 | manual/E2E | subagent validation run | ❌ W0 | ⬜ pending |
| 102-02-05 | 02 | 1 | LNX-05 | manual/E2E | subagent validation run | ❌ W0 | ⬜ pending |
| 102-03-01 | 03 | 2 | LNX-06 | report | `FRICTION-LNX-102.md` zero BLOCKERs | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

> **Note:** LNX-01 through LNX-06 are validated by a live E2E run in the LXC environment, not by unit or component tests. The "test" for this phase is the validation orchestrator script and the resulting FRICTION file. No new backend unit tests are required — this phase is a live integration test.

---

## Wave 0 Requirements

- [ ] `mop_validation/scripts/run_linux_e2e.py` — Phase 102 orchestrator script (new)
- [ ] `mop_validation/scripts/linux_validation_prompt.md` — Claude subagent persona + golden path instructions (new)
- [ ] GHCR pre-flight check — verify `ghcr.io/axiom-laboratories/axiom:latest` and related images are published before first LXC run
- [ ] `synthesise_friction.py` patch — add `--files` argument to support single `FRICTION-LNX-102.md` (currently hardcoded for 4 CE/EE files)

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Cold-start deploy via docs | LNX-01 | Requires live LXC container + network pull of GHCR images | Run `python3 mop_validation/scripts/run_linux_e2e.py` from host; check container reaches dashboard |
| admin/admin forced password change | LNX-02 | Browser interaction in LXC headless env | Subagent golden path checks for `ForceChangeModal` trigger after first login |
| Node enrollment appears ONLINE | LNX-03 | mTLS cert exchange, live Docker networking | Subagent checks Nodes view after `docker compose up` on node |
| First job reaches COMPLETED | LNX-04 | Full job dispatch + worker execution loop | Subagent dispatches signed Python job and polls status |
| All CE features accessible | LNX-05 | UI navigation across all views | Subagent navigates each documented CE route, reports 404s or blank panels |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 600s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
