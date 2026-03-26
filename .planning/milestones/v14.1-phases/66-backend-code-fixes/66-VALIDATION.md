---
phase: 66
slug: backend-code-fixes
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-25
---

# Phase 66 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest with pytest-asyncio |
| **Config file** | `pyproject.toml` (`[tool.pytest.ini_options]`) |
| **Quick run command** | `cd /home/thomas/Development/master_of_puppets/puppeteer && /home/thomas/Development/master_of_puppets/.venv/bin/python -m pytest agent_service/tests/test_ce_smoke.py -v` |
| **Full suite command** | `cd /home/thomas/Development/master_of_puppets/puppeteer && /home/thomas/Development/master_of_puppets/.venv/bin/python -m pytest agent_service/tests/ -v` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run quick run command (test_ce_smoke.py)
- **After every plan wave:** Run full suite command
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** ~15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 66-01-01 | 01 | 1 | CODE-01 | smoke (manual docker build) | `docker build -f puppets/Containerfile.node puppets/ && docker run --rm <img> docker --version` | ❌ W0 manual step | ⬜ pending |
| 66-01-02 | 01 | 1 | CODE-02 | static grep | `grep -c '/tmp:/tmp' puppeteer/compose.cold-start.yaml` (expect 2) | ❌ W0 grep assertion | ⬜ pending |
| 66-01-03 | 01 | 1 | CODE-03 | smoke (manual docker build) | `docker build -f puppets/Containerfile.node puppets/ && docker run --rm <img> pwsh --version` | ❌ W0 manual step | ⬜ pending |
| 66-01-04 | 01 | 1 | CODE-04 | unit | `cd puppeteer && python -m pytest agent_service/tests/test_ce_smoke.py -v` | ✅ exists (needs update) | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `agent_service/tests/test_ce_smoke.py` — update `test_ce_features_all_false` (add `"executions"` to ee_flags list), update `test_ce_stub_routers_return_402` (import and assert all 7 execution stub handlers return 402), update `test_ce_table_count` (assertion from 13 → 15)

*Container build verification for CODE-01 and CODE-03 is manual (docker build + docker run). CODE-02 is a static file inspection. No new test infrastructure needed.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| `docker --version` runs inside built node image | CODE-01 | Requires actual Docker image build | `docker build -f puppets/Containerfile.node puppets/ -t mop-node-test && docker run --rm mop-node-test docker --version` |
| `pwsh --version` runs inside built node image | CODE-03 | Requires actual Docker image build | `docker build -f puppets/Containerfile.node puppets/ -t mop-node-test && docker run --rm mop-node-test pwsh --version` |
| `/tmp:/tmp` present for both nodes in compose | CODE-02 | Static file assertion | `grep -c '/tmp:/tmp' puppeteer/compose.cold-start.yaml` — must return 2 |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
