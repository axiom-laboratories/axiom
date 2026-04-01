---
phase: 106
slug: fix-docs-signing-pipeline
status: draft
nyquist_compliant: true
wave_0_complete: true
created: 2026-04-01
---

# Phase 106 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | grep / diff (documentation-only changes) |
| **Config file** | none |
| **Quick run command** | `grep -n 'signature_id\|signature_key_id\|SkipCertificateCheck\|TrustAll' docs/docs/getting-started/first-job.md` |
| **Full suite command** | `grep -n 'signature_id\|signature_key_id\|SkipCertificateCheck\|TrustAll' docs/docs/getting-started/first-job.md` |
| **Estimated runtime** | <1 second |

---

## Sampling Rate

- **After every task commit:** Run quick run command
- **After every plan wave:** Run full suite command
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 1 second

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 106-01-02 | 01 | 1 | LNX-04, WIN-05 | grep | `grep -c 'signature_key_id' docs/docs/getting-started/first-job.md` → 0 | N/A | ⬜ pending |
| 106-01-03 | 01 | 1 | WIN-05 | grep | `grep -c 'TrustAll' docs/docs/getting-started/first-job.md` → 0 | N/A | ⬜ pending |
| 106-01-03 | 01 | 1 | WIN-05 | grep | `grep -c 'SkipCertificateCheck' docs/docs/getting-started/first-job.md` → >0 | N/A | ⬜ pending |
| 106-01-04 | 01 | 1 | WIN-05 | grep | `grep -c 'signature_id' docs/docs/getting-started/first-job.md` → 2 | N/A | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

Existing infrastructure covers all phase requirements.

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Linux signing pipeline E2E | LNX-04 | Requires live stack + enrolled node | Follow first-job.md Linux curl snippet end-to-end; verify job completes |
| Windows signing pipeline E2E | WIN-05 | Requires Windows host with live stack | Follow first-job.md PowerShell snippet end-to-end; verify job completes |

*Both manual verifications confirm the docs-following path works after the field name and TrustAll fixes.*

---

## Validation Sign-Off

- [x] All tasks have automated verify or manual-only justification
- [x] Sampling continuity: grep checks after each task
- [x] Wave 0 covers all requirements (existing infrastructure)
- [x] No watch-mode flags
- [x] Feedback latency < 1s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
