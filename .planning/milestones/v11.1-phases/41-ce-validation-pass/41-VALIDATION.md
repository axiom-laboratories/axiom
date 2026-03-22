---
phase: 41
slug: ce-validation-pass
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-21
---

# Phase 41 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | Standalone Python validation scripts (no pytest) |
| **Config file** | `mop_validation/secrets.env` (credentials) |
| **Quick run command** | `python3 mop_validation/scripts/verify_ce_stubs.py` |
| **Full suite command** | `python3 mop_validation/scripts/verify_ce_stubs.py && python3 mop_validation/scripts/verify_ce_tables.py && python3 mop_validation/scripts/verify_ce_job.py` |
| **Estimated runtime** | ~30 seconds |

---

## Sampling Rate

- **After every task commit:** Run the specific script for that task's CEV requirement
- **After every plan wave:** Run full suite command above
- **Before `/gsd:verify-work`:** All 3 scripts must exit 0
- **Max feedback latency:** ~30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 41-01-01 | 01 | 1 | CEV-01 | integration/smoke | `python3 mop_validation/scripts/verify_ce_stubs.py` | ❌ Wave 0 | ⬜ pending |
| 41-02-01 | 02 | 1 | CEV-02 | integration/smoke | `python3 mop_validation/scripts/verify_ce_tables.py` | ❌ Wave 0 | ⬜ pending |
| 41-03-01 | 03 | 1 | CEV-03 | integration/e2e | `python3 mop_validation/scripts/verify_ce_job.py` | ❌ Wave 0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `mop_validation/scripts/verify_ce_stubs.py` — covers CEV-01 (7 EE routes return HTTP 402)
- [ ] `mop_validation/scripts/verify_ce_tables.py` — covers CEV-02 (exactly 13 CE tables after hard teardown)
- [ ] `mop_validation/scripts/verify_ce_job.py` — covers CEV-03 (signed job executes on DEV node; stdout captured)

*All three scripts ARE the deliverables of this phase — Wave 0 IS the implementation.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Hard teardown + CE reinstall sequence | CEV-02 | Requires stopping the live stack and dropping/recreating the database | Run `docker compose down -v` then `docker compose up -d`, wait for healthy, then run `verify_ce_tables.py` |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
