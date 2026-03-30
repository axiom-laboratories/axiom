---
phase: 92
slug: usp-signing-ux
status: approved
nyquist_compliant: true
wave_0_complete: true
created: 2026-03-30
---

# Phase 92 — Validation Strategy

> Retroactive validation record for Phase 92 (USP Signing UX). Phase complete.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x (asyncio) |
| **Config file** | puppeteer/pyproject.toml |
| **Quick run command** | `cd puppeteer && python -m pytest agent_service/tests/test_signing_ux.py -v` |
| **Full suite command** | `cd puppeteer && python -m pytest agent_service/tests/` |
| **Estimated runtime** | ~5 seconds (signing UX tests), ~60 seconds (full suite) |

---

## Sampling Rate

- **After every task commit:** Run `cd puppeteer && python -m pytest agent_service/tests/test_signing_ux.py -v`
- **After every plan wave:** Run `cd puppeteer && python -m pytest agent_service/tests/`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** ~5 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 92-signing-ux | 92 | 1 | USP-01 | integration | `pytest test_signing_ux.py` | ✅ | ✅ green |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

Existing infrastructure covers all phase requirements.
`test_signing_ux.py` was created as part of Phase 92 itself.

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Signatures page shows keygen banner with copy-paste command | USP-01 | UI render verification | Load the Signatures view in the dashboard; confirm the banner and KEYGEN_CMD block render correctly |
| SIGN_CMD block shows accurate signing script | USP-01 | UI render verification | Confirm YOUR_SCRIPT placeholder (not hello.py) and that the script signs encode("utf-8") |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references
- [x] No watch-mode flags
- [x] Feedback latency < 5s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** approved 2026-03-30 (retroactive)
