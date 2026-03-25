---
phase: 61
slug: lxc-environment-and-cold-start-compose
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-24
---

# Phase 61 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (puppeteer/tests/) + manual smoke |
| **Config file** | `puppeteer/pytest.ini` |
| **Quick run command** | `cd puppeteer && python -m pytest tests/test_ee_smoke.py -x -q` |
| **Full suite command** | `cd puppeteer && pytest` |
| **Estimated runtime** | ~60 seconds |

---

## Sampling Rate

- **After every task commit:** Run `cd puppeteer && python -m pytest tests/test_ee_smoke.py -x -q`
- **After every plan wave:** Run `cd puppeteer && pytest`
- **Before `/gsd:verify-work`:** Full suite must be green + all 4 manual smoke checks pass
- **Max feedback latency:** 60 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 61-01-01 | 01 | 1 | ENV-01 | smoke | `incus exec axiom-coldstart -- docker run --rm hello-world` | ❌ W0 | ⬜ pending |
| 61-01-02 | 01 | 1 | ENV-01 | smoke | `incus exec axiom-coldstart -- timeout 30 gemini -p "Say hello"` | ❌ W0 | ⬜ pending |
| 61-02-01 | 02 | 2 | ENV-02 | smoke | `cd puppeteer && docker compose -f compose.cold-start.yaml ps` | ❌ W0 | ⬜ pending |
| 61-02-02 | 02 | 2 | ENV-03 | smoke | `docker exec <node_container> which pwsh` | ❌ W0 | ⬜ pending |
| 61-03-01 | 03 | 3 | ENV-04 | unit | `grep AXIOM_EE_LICENCE_KEY mop_validation/secrets.env` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `mop_validation/scripts/verify_phase61_env.py` — smoke verifier for ENV-01 through ENV-04

*Existing backend pytest suite covers application logic. Phase 61 deliverables are scripts and config files — validated by running the actual infrastructure.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| LXC container with Docker nesting enabled | ENV-01 | Requires live Incus environment | `incus exec axiom-coldstart -- docker run --rm hello-world` |
| Dashboard reachable at 172.17.0.1 with valid TLS cert | ENV-02 | Requires running Docker stack | `curl -k https://172.17.0.1:8443` — expect 200 |
| PowerShell installed in node container | ENV-03 | Requires running node container | `docker exec <node> which pwsh` — expect a path |
| Gemini CLI responds headlessly in LXC | ENV-01 | Requires live LXC + Google auth | `incus exec axiom-coldstart -- timeout 30 gemini -p "Say hello"` |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 60s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
