---
phase: 135
slug: resource-limits-package-cleanup
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-12
---

# Phase 135 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x + docker compose config |
| **Config file** | puppeteer/pytest.ini (existing) |
| **Quick run command** | `docker compose -f puppeteer/compose.server.yaml config --quiet && echo "compose valid"` |
| **Full suite command** | `cd puppeteer && pytest tests/ -x -q` |
| **Estimated runtime** | ~30 seconds |

---

## Sampling Rate

- **After every task commit:** Run `docker compose -f puppeteer/compose.server.yaml config --quiet && echo "compose valid"`
- **After every plan wave:** Run `cd puppeteer && pytest tests/ -x -q`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 135-01-01 | 01 | 1 | CONT-05 | compose-validate | `docker compose -f puppeteer/compose.server.yaml config --quiet` | ✅ | ⬜ pending |
| 135-01-02 | 01 | 1 | CONT-07 | container-build | `docker build -t mop-node-test -f puppets/Containerfile.node puppets/ && docker run --rm mop-node-test dpkg -l podman iptables krb5-user 2>&1 \| grep -v "^.i"` | ✅ | ⬜ pending |
| 135-01-03 | 01 | 2 | CONT-05+07 | integration | `cd puppeteer && pytest tests/ -x -q` | ✅ | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

Existing infrastructure covers all phase requirements. No new test stubs needed — validation is done via:
1. `docker compose config` for compose syntax
2. `docker build` + `dpkg -l` for package removal verification
3. Existing pytest suite for regression

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Resource limits enforced at runtime | CONT-05 | Requires running stack + `docker stats` | Start stack, run `docker stats --no-stream`, confirm each service stays within limits under load |
| autoremove didn't strip needed packages | CONT-07 | Requires job execution post-build | Build leaner image, run a sample job, verify output is correct |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
