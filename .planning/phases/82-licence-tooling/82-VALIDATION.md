---
phase: 82
slug: licence-tooling
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-28
---

# Phase 82 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x (existing project framework) |
| **Config file** | `puppeteer/pytest.ini` (existing) |
| **Quick run command** | `cd puppeteer && pytest tests/test_licence_service.py -x -q` |
| **Full suite command** | `cd puppeteer && pytest -x -q` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `cd puppeteer && pytest tests/test_licence_service.py -x -q`
- **After every plan wave:** Run `cd puppeteer && pytest -x -q`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 82-01-01 | 01 | 1 | LIC-01 | manual | `ls axiom-licenses/keys/licence.key` | ❌ W0 | ⬜ pending |
| 82-01-02 | 01 | 1 | LIC-01 | unit | `cd puppeteer && pytest tests/test_licence_service.py -k test_new_public_key -x -q` | ❌ W0 | ⬜ pending |
| 82-01-03 | 01 | 1 | LIC-03 | unit | `cd axiom-licenses && python -m pytest tests/test_issue_licence.py -k test_key_source -x -q` | ❌ W0 | ⬜ pending |
| 82-01-04 | 01 | 1 | LIC-03 | unit | `cd axiom-licenses && python -m pytest tests/test_issue_licence.py -k test_jwt_output -x -q` | ❌ W0 | ⬜ pending |
| 82-01-05 | 01 | 1 | LIC-04 | unit | `cd axiom-licenses && python -m pytest tests/test_issue_licence.py -k test_yaml_record -x -q` | ❌ W0 | ⬜ pending |
| 82-01-06 | 01 | 1 | LIC-05 | unit | `cd axiom-licenses && python -m pytest tests/test_issue_licence.py -k test_no_remote -x -q` | ❌ W0 | ⬜ pending |
| 82-02-01 | 02 | 2 | LIC-01 | manual | `grep -r "BEGIN PRIVATE KEY" puppeteer/ tools/ 2>/dev/null | wc -l` (expect 0) | ✅ | ⬜ pending |
| 82-02-02 | 02 | 2 | LIC-02 | manual | Push to branch and check CI gitleaks job passes | ✅ | ⬜ pending |
| 82-02-03 | 02 | 2 | LIC-02 | unit | `cat .gitleaks.toml` + verify allowlist entries | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `puppeteer/tests/test_licence_service.py` — add test for new public key round-trip
- [ ] `axiom-licenses/tests/test_issue_licence.py` — stubs for key resolution, JWT output, YAML record, `--no-remote` flag

*Note: The private `axiom-licenses` repo tests are created as part of Wave 1 scaffolding. The puppeteer test can run immediately.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| `issue_licence.py` without `--key` and without `AXIOM_LICENCE_SIGNING_KEY` exits with clear error | LIC-03 | Requires live CLI execution with missing env | Run `python issue_licence.py --customer test --tier EE --nodes 5 --expiry 2027-01-01` with no key env var; expect non-zero exit and error message |
| CI gitleaks job triggers and rejects a PEM key commit | LIC-02 | Requires a live GitHub Actions push | Create a test branch with dummy `-----BEGIN PRIVATE KEY-----` content; verify gitleaks CI job fails |
| `--no-remote` writes YAML to local file | LIC-05 | Requires filesystem inspection after CLI run | Run with `--no-remote`; verify a `.yml` file is created locally and JWT is printed to stdout |
| Private repo `axiom-licenses/keys/licence.key` exists and has correct permissions | LIC-01 | Filesystem state in private repo | `ls -la axiom-licenses/keys/licence.key` → expect `chmod 600` |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
