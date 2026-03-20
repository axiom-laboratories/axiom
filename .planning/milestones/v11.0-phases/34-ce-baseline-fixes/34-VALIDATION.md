---
phase: 34
slug: ce-baseline-fixes
status: draft
nyquist_compliant: true
wave_0_complete: false
created: 2026-03-19
---

# Phase 34 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Wave Structure

| Wave | Plans | Note |
|------|-------|------|
| 1 | Plan 02 | Creates placeholder test files; must run first |
| 2 | Plan 01, Plan 03 | Depend on Plan 02 (placeholder files must exist) |

Plan 02 is Wave 1 and has no dependencies. Plans 01 and 03 are Wave 2 (`depends_on: ["02"]`) — their `pytest -m "not ee_only"` verify commands require the placeholder files and conftest hook that Plan 02 produces.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.0.2 |
| **Config file** | `.worktrees/axiom-split/puppeteer/pyproject.toml` |
| **Quick run command** | `cd .worktrees/axiom-split && pytest puppeteer/agent_service/tests/ -m "not ee_only" -x -q` |
| **Full suite command** | `cd .worktrees/axiom-split && pytest -m "not ee_only" -q` |
| **Estimated runtime** | ~30 seconds |

---

## Sampling Rate

- **After every task commit:** Run `cd .worktrees/axiom-split && pytest puppeteer/agent_service/tests/ -m "not ee_only" -x -q`
- **After every plan wave:** Run `cd .worktrees/axiom-split && pytest -m "not ee_only" -q`
- **Before `/gsd:verify-work`:** Full suite must be green (zero failures, zero EE-attribute errors)
- **Max feedback latency:** ~30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 34-02-01 | 02 | 1 | GAP-03 | unit (marker) | `cd .worktrees/axiom-split && python -m pytest puppeteer/agent_service/tests/test_lifecycle_enforcement.py puppeteer/agent_service/tests/test_foundry_mirror.py puppeteer/agent_service/tests/test_smelter.py puppeteer/agent_service/tests/test_staging.py -v 2>&1 \| tail -15` | ❌ created by task | ⬜ pending |
| 34-02-02 | 02 | 1 | GAP-04 | suite gate | `cd .worktrees/axiom-split && python -m pytest puppeteer/agent_service/tests/ puppeteer/tests/ -m "not ee_only" -x -q 2>&1 \| tail -20` | ✅ | ⬜ pending |
| 34-01-01 | 01 | 2 | GAP-01 | grep check | `grep -n "reset-password\|force-password-change" .worktrees/axiom-split/puppeteer/agent_service/ee/interfaces/auth_ext.py` | ✅ | ⬜ pending |
| 34-01-02 | 01 | 2 | GAP-02 | import check | `cd .worktrees/axiom-split && python -c "import sys; sys.path.insert(0, 'puppeteer'); from agent_service.ee import load_ee_plugins, _mount_ce_stubs; print('OK')"` | ✅ | ⬜ pending |
| 34-03-01 | 03 | 2 | GAP-05 | unit | `cd .worktrees/axiom-split && grep -rn "NodeConfig" puppeteer/ 2>&1 && python -c "import sys; sys.path.insert(0,'puppeteer'); from agent_service.models import PollResponse; r = PollResponse(job=None, env_tag='PROD'); print(r.env_tag)"` | ✅ | ⬜ pending |
| 34-03-02 | 03 | 2 | GAP-06 | unit | `cd .worktrees/axiom-split && grep -n "env_tag" puppeteer/agent_service/services/job_service.py && python -m pytest puppeteer/agent_service/tests/test_job_service.py -x -q 2>&1 \| tail -15` | ✅ | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

Wave 0 is Plan 02 (Wave 1). The following files are created by Plan 02 Task 1 and must exist before Plans 01 and 03 can run their `pytest -m "not ee_only"` verify commands:

- [ ] `puppeteer/agent_service/tests/test_lifecycle_enforcement.py` — ee_only placeholder stub for GAP-03
- [ ] `puppeteer/agent_service/tests/test_foundry_mirror.py` — ee_only placeholder stub for GAP-03
- [ ] `puppeteer/agent_service/tests/test_smelter.py` — ee_only placeholder stub for GAP-03
- [ ] `puppeteer/agent_service/tests/test_staging.py` — ee_only placeholder stub for GAP-03

Note: GAP-02 verification (task 34-01-02) uses a direct Python import check rather than a pytest test — the import check directly validates that `importlib.metadata` replaced `pkg_resources` and that `_mount_ce_stubs` is importable. No `test_ee_plugin_loader` test file is required.

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| `GET /api/features` returns all flags as `false` on CE install | GAP-01 | Requires live CE server | Start server with `EDITION=ce`, `curl https://localhost:8001/api/features` — verify all values are `false` |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references (Plan 02 runs first — placeholder files created before Plans 01/03 execute)
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
