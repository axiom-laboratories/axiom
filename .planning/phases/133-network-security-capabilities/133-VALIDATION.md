---
phase: 133
slug: network-security-capabilities
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-12
---

# Phase 133 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x (backend) + shell/bash inspect commands |
| **Config file** | `puppeteer/pytest.ini` |
| **Quick run command** | `cd puppeteer && pytest tests/ -x -q` |
| **Full suite command** | `cd puppeteer && pytest tests/` |
| **Estimated runtime** | ~30 seconds |

---

## Sampling Rate

- **After every task commit:** Run `cd puppeteer && pytest tests/ -x -q`
- **After every plan wave:** Run `cd puppeteer && pytest tests/`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 60 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 133-01-01 | 01 | 1 | CONT-03 | inspect | `docker inspect puppeteer-agent-1 \| python3 -c "import sys,json; d=json.load(sys.stdin); print(d[0]['HostConfig']['CapDrop'])"` | ✅ | ⬜ pending |
| 133-01-02 | 01 | 1 | CONT-03 | inspect | `docker inspect puppeteer-cert-manager-1 \| python3 -c "import sys,json; d=json.load(sys.stdin); print(d[0]['HostConfig']['CapAdd'])"` | ✅ | ⬜ pending |
| 133-01-03 | 01 | 1 | CONT-04 | inspect | `docker inspect puppeteer-db-1 \| python3 -c "import sys,json; d=json.load(sys.stdin); print(d[0]['HostConfig']['PortBindings'])"` | ✅ | ⬜ pending |
| 133-01-04 | 01 | 1 | CONT-03 | diff | `diff <(grep -c 'cap_drop' puppeteer/compose.server.yaml) <(echo 9)` — count services with cap_drop | ✅ | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

Existing infrastructure covers all phase requirements. This phase is compose.server.yaml configuration only — no new test files needed. Verification is via `docker inspect` after stack rebuild.

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Stack starts without errors after compose changes | CONT-03/04 | Requires full docker compose up | `cd puppeteer && docker compose -f compose.server.yaml up -d` — verify all services reach healthy state |
| Postgres still reachable from agent service | CONT-04 | Requires live DB connection test | Check agent service logs for successful DB connection on startup |
| Registry still reachable for remote Foundry pulls | CONT-03 | Requires network connectivity from external host | Verify `docker pull localhost:5000/puppet:<tag>` works from agent container perspective |
| Dead services removed | — | Config-only check | `grep -c 'tunnel:\|ddns-updater:' puppeteer/compose.server.yaml` should return 0 |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 60s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
