---
phase: 79
slug: install-docs-cleanup
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-27
---

# Phase 79 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | grep (shell — no test framework; pure file content validation) |
| **Config file** | none |
| **Quick run command** | `grep -c "puppet-node-1" puppeteer/compose.cold-start.yaml && echo "FAIL: node refs remain" || echo "PASS"` |
| **Full suite command** | `bash -c 'grep -q puppet-node-1 puppeteer/compose.cold-start.yaml && echo FAIL-INST01a || echo PASS-INST01a'; bash -c 'grep -q puppet-node-2 puppeteer/compose.cold-start.yaml && echo FAIL-INST01b || echo PASS-INST01b'; bash -c 'grep -q JOIN_TOKEN puppeteer/compose.cold-start.yaml && echo FAIL-INST01c || echo PASS-INST01c'; bash -c 'grep -qi "JOIN_TOKEN" docs/install.md && echo FAIL-INST02a || echo PASS-INST02a'; bash -c 'grep -qi "Cold-Start Install" docs/install.md && echo FAIL-INST02b || echo PASS-INST02b'` |
| **Estimated runtime** | ~1 second |

---

## Sampling Rate

- **After every task commit:** Run quick run command
- **After every plan wave:** Run full suite command
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 5 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 79-01-01 | 01 | 1 | INST-01 | grep | `grep -c "puppet-node-1\|puppet-node-2" puppeteer/compose.cold-start.yaml; echo exit:$?` | ✅ | ⬜ pending |
| 79-01-02 | 01 | 1 | INST-01 | grep | `grep -c "node1-secrets\|node2-secrets" puppeteer/compose.cold-start.yaml; echo exit:$?` | ✅ | ⬜ pending |
| 79-01-03 | 01 | 1 | INST-01 | grep | `grep -c "JOIN_TOKEN" puppeteer/compose.cold-start.yaml; echo exit:$?` | ✅ | ⬜ pending |
| 79-02-01 | 01 | 1 | INST-02 | grep | `grep -ci "JOIN_TOKEN" docs/install.md; echo exit:$?` | ✅ | ⬜ pending |
| 79-02-02 | 01 | 1 | INST-02 | grep | `grep -c "Cold-Start Install" docs/install.md; echo exit:$?` | ✅ | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

Existing infrastructure covers all phase requirements.

*No test files need to be created — validation is grep-based smoke tests on the edited files.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| `docker compose -f compose.cold-start.yaml up -d` starts no node services | INST-01 | Requires Docker runtime to confirm services started | Run `docker compose -f puppeteer/compose.cold-start.yaml up -d` and verify `docker ps` shows no puppet-node-* containers |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 5s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
