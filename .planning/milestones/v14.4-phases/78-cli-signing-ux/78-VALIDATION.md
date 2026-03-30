---
phase: 78
slug: cli-signing-ux
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-27
---

# Phase 78 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest |
| **Config file** | none — existing `mop_sdk/tests/` directory |
| **Quick run command** | `cd /home/thomas/Development/master_of_puppets/mop_sdk && python -m pytest tests/test_cli.py tests/test_client.py -x -q` |
| **Full suite command** | `cd /home/thomas/Development/master_of_puppets/mop_sdk && python -m pytest tests/ -v` |
| **Estimated runtime** | ~5 seconds |

---

## Sampling Rate

- **After every task commit:** Run `cd /home/thomas/Development/master_of_puppets/mop_sdk && python -m pytest tests/test_cli.py tests/test_client.py -x -q`
- **After every plan wave:** Run `cd /home/thomas/Development/master_of_puppets/mop_sdk && python -m pytest tests/ -v`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 10 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 78-01-01 | 01 | 1 | CLI-01 | unit | `python -m pytest tests/test_cli.py -x -k "url"` | ❌ W0 | ⬜ pending |
| 78-01-02 | 01 | 1 | CLI-02 | unit | `python -m pytest tests/test_cli.py -x -k "key_generate"` | ❌ W0 | ⬜ pending |
| 78-01-03 | 01 | 1 | CLI-02 | unit | `python -m pytest tests/test_cli.py -x -k "key_generate_no_overwrite"` | ❌ W0 | ⬜ pending |
| 78-01-04 | 01 | 1 | CLI-02 | unit | `python -m pytest tests/test_cli.py -x -k "key_generate_force"` | ❌ W0 | ⬜ pending |
| 78-02-01 | 02 | 1 | CLI-03 | unit | `python -m pytest tests/test_cli.py -x -k "init_skip_login"` | ❌ W0 | ⬜ pending |
| 78-02-02 | 02 | 1 | CLI-03 | unit | `python -m pytest tests/test_cli.py -x -k "init_skip_keygen"` | ❌ W0 | ⬜ pending |
| 78-02-03 | 02 | 1 | CLI-03 | unit | `python -m pytest tests/test_cli.py -x -k "init_full_flow"` | ❌ W0 | ⬜ pending |
| 78-02-04 | 02 | 1 | CLI-03 | unit | `python -m pytest tests/test_client.py -x -k "register_signature"` | ❌ W0 | ⬜ pending |
| 78-03-01 | 03 | 2 | CLI-04 | manual | `grep "axiom-push init" docs/docs/getting-started/first-job.md` | N/A | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `mop_sdk/tests/test_cli.py` — add test cases for CLI-01 (AXIOM_URL), CLI-02 (key generate), CLI-03 (init flow)
- [ ] `mop_sdk/tests/test_client.py` — add `test_register_signature()` test case

*Existing test infrastructure covers the framework — only new test cases are needed, not new files.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| `first-job.md` presents `axiom-push init` as primary path | CLI-04 | Documentation content; no automated doc linting in place | `grep "axiom-push init" docs/docs/getting-started/first-job.md` returns a match; openssl is positioned as fallback/alternative, not Step 1 |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 10s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
