---
phase: 43
slug: job-test-matrix
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-21
---

# Phase 43 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x (standalone scripts, not pytest suites) + Python stdlib |
| **Config file** | none — scripts are self-contained |
| **Quick run command** | `python mop_validation/scripts/verify_job_01_fast.py` |
| **Full suite command** | `python mop_validation/scripts/run_job_matrix.py` |
| **Estimated runtime** | ~180 seconds (dominated by JOB-02 90s sleep job) |

---

## Sampling Rate

- **After every task commit:** Run `python mop_validation/scripts/verify_job_01_fast.py` (smoke check)
- **After every plan wave:** Run `python mop_validation/scripts/run_job_matrix.py`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 180 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 43-01-01 | 01 | 0 | JOB-01 | integration | `python mop_validation/scripts/verify_job_01_fast.py` | ❌ W0 | ⬜ pending |
| 43-01-02 | 01 | 0 | JOB-02 | integration | `python mop_validation/scripts/verify_job_02_slow.py` | ❌ W0 | ⬜ pending |
| 43-01-03 | 01 | 0 | JOB-03 | integration | `python mop_validation/scripts/verify_job_03_concurrent.py` | ❌ W0 | ⬜ pending |
| 43-01-04 | 01 | 0 | JOB-04 | integration | `python mop_validation/scripts/verify_job_04_staging.py` | ❌ W0 | ⬜ pending |
| 43-01-05 | 01 | 0 | JOB-05 | integration | `python mop_validation/scripts/verify_job_05_env_tag.py` | ❌ W0 | ⬜ pending |
| 43-02-01 | 02 | 1 | JOB-05 | code-fix | manual review of `main.py` dispatch guard | n/a | ⬜ pending |
| 43-02-02 | 02 | 1 | JOB-09 | code-fix | manual review of `main.py` revoked guard | n/a | ⬜ pending |
| 43-03-01 | 03 | 1 | JOB-06 | integration | `python mop_validation/scripts/verify_job_06_retry.py` | ❌ W0 | ⬜ pending |
| 43-03-02 | 03 | 1 | JOB-07 | integration | `python mop_validation/scripts/verify_job_07_dead_letter.py` | ❌ W0 | ⬜ pending |
| 43-03-03 | 03 | 1 | JOB-08 | integration | `python mop_validation/scripts/verify_job_08_bad_sig.py` | ❌ W0 | ⬜ pending |
| 43-03-04 | 03 | 1 | JOB-09 | integration | `python mop_validation/scripts/verify_job_09_revoked.py` | ❌ W0 | ⬜ pending |
| 43-04-01 | 04 | 2 | all | integration | `python mop_validation/scripts/run_job_matrix.py` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `mop_validation/scripts/verify_job_01_fast.py` — JOB-01: fast job completes with stdout
- [ ] `mop_validation/scripts/verify_job_02_slow.py` — JOB-02: slow (90s) job, node live during execution
- [ ] `mop_validation/scripts/verify_job_03_concurrent.py` — JOB-03: 5 concurrent jobs, no duplicate execution
- [ ] `mop_validation/scripts/verify_job_04_staging.py` — JOB-04: STAGING-tagged routing
- [ ] `mop_validation/scripts/verify_job_05_env_tag.py` — JOB-05: env-tag routing, cross-tag rejection
- [ ] `mop_validation/scripts/verify_job_06_retry.py` — JOB-06: retry mechanics
- [ ] `mop_validation/scripts/verify_job_07_dead_letter.py` — JOB-07: DEAD_LETTER final status, 3 attempt records
- [ ] `mop_validation/scripts/verify_job_08_bad_sig.py` — JOB-08: bad signature → SECURITY_REJECTED
- [ ] `mop_validation/scripts/verify_job_09_revoked.py` — JOB-09: revoked definition → 4xx at orchestrator
- [ ] `mop_validation/scripts/run_job_matrix.py` — thin runner, sequential, aggregated summary table

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| DB corrupt for JOB-08 | JOB-08 | Requires `docker exec` PostgreSQL UPDATE to corrupt signature_payload | Run `docker exec puppeteer-postgres-1 psql -U ...` to corrupt signature, then run verify_job_08_bad_sig.py |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 180s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
