---
phase: 83
slug: node-validation-job-library
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-28
---

# Phase 83 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x |
| **Config file** | none — pytest discovered by convention |
| **Quick run command** | `cd puppeteer && pytest tests/test_example_jobs.py -x` |
| **Full suite command** | `cd puppeteer && pytest` |
| **Estimated runtime** | ~10 seconds |

---

## Sampling Rate

- **After every task commit:** Run `cd puppeteer && pytest tests/test_example_jobs.py -x`
- **After every plan wave:** Run `cd puppeteer && pytest`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 10 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 83-01-01 | 01 | 0 | JOB-01..07 | unit | `cd puppeteer && pytest tests/test_example_jobs.py -x` | ❌ W0 | ⬜ pending |
| 83-01-02 | 01 | 1 | JOB-01 | unit | `cd puppeteer && pytest tests/test_example_jobs.py::test_hello_bash -x` | ❌ W0 | ⬜ pending |
| 83-01-03 | 01 | 1 | JOB-02 | unit | `cd puppeteer && pytest tests/test_example_jobs.py::test_hello_python -x` | ❌ W0 | ⬜ pending |
| 83-01-04 | 01 | 1 | JOB-03 | unit | `cd puppeteer && pytest tests/test_example_jobs.py::test_hello_pwsh -x` | ❌ W0 | ⬜ pending |
| 83-01-05 | 01 | 1 | JOB-04 | unit | `cd puppeteer && pytest tests/test_example_jobs.py::test_volume_mapping -x` | ❌ W0 | ⬜ pending |
| 83-01-06 | 01 | 1 | JOB-05 | unit | `cd puppeteer && pytest tests/test_example_jobs.py::test_network_filter -x` | ❌ W0 | ⬜ pending |
| 83-01-07 | 01 | 1 | JOB-06 | unit | `cd puppeteer && pytest tests/test_example_jobs.py::test_memory_hog_no_cap -x` | ❌ W0 | ⬜ pending |
| 83-01-08 | 01 | 1 | JOB-07 | unit | `cd puppeteer && pytest tests/test_example_jobs.py::test_cpu_spin_no_cap -x` | ❌ W0 | ⬜ pending |
| 83-01-09 | 01 | 1 | JOB-01..07 | unit | `cd puppeteer && pytest tests/test_example_jobs.py::test_manifest_valid -x` | ❌ W0 | ⬜ pending |
| 83-02-01 | 02 | 2 | JOB-01..07 | manual | See Manual-Only Verifications | N/A | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `puppeteer/tests/test_example_jobs.py` — stubs for JOB-01 through JOB-07 script content checks + manifest validation

*No new framework install needed — pytest already present.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| bash/hello.sh executes successfully on a bash-capable node and reaches COMPLETED status | JOB-01 | Requires live Docker stack + capable node | Dispatch via dashboard or axiom-push; observe job status reaches COMPLETED; check stdout for `=== PASS ===` |
| python/hello.py executes successfully on a Python-capable node and reaches COMPLETED status | JOB-02 | Requires live Docker stack + capable node | Dispatch via dashboard; observe COMPLETED status; check stdout for `=== PASS ===` |
| pwsh/hello.ps1 executes successfully on a PowerShell-capable node and reaches COMPLETED status | JOB-03 | Requires live Docker stack + pwsh-capable node | Dispatch via dashboard; observe COMPLETED status |
| volume-mapping.sh confirms sentinel file written inside container is readable at host-side mount path | JOB-04 | Requires node with volume mount configured | Set `AXIOM_VOLUME_PATH` env var at dispatch; observe PASS output; verify file written and cleaned up |
| network-filter.py confirms allowed hosts reachable and blocked hosts time out | JOB-05 | Requires node with `--network=none` configured | Configure node network isolation; dispatch; observe PASS on blocked host timeout |
| memory-hog.py is killed (OOM/FAILED) rather than completing on a memory-limited node | JOB-06 | Requires node with memory_limit < 256m + containerised execution | Configure node with 128m memory limit; dispatch with `capability_requirements: {resource_limits_supported: "1.0"}`; observe FAILED/OOM status |
| cpu-spin.py reports throttle ratio < 0.8 on a CPU-limited node | JOB-07 | Requires node with cpu_limit < 1.0 configured | Configure node with 0.5 CPU limit; dispatch; observe ratio output in stdout |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 10s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
