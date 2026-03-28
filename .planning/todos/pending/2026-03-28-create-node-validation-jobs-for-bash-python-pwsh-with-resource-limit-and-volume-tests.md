---
created: 2026-03-28T17:26:51.990Z
title: Create node validation jobs for bash, Python, PWSH with resource limit and volume tests
area: testing
files:
  - mop_validation/scripts/
  - puppets/environment_service/runtime.py
---

## Problem

There is no standard job library that exercises the full capability surface of the three runtimes (bash, Python, PowerShell) and validates that EE-specific features (volume/dir mapping, network filtering, resource limits) are actually enforced at the container level.

Current gap: we assert that jobs run, but do not verify:
1. That volume mounts reach the expected paths inside the container
2. That network filtering (allowlist/denylist) actually blocks/permits traffic
3. That memory and CPU limits are enforced — a job exceeding its limit should be killed, not just reported

## Solution

Create a set of signed reference jobs (stored in `mop_validation/scripts/jobs/` or similar) covering:

**Runtime coverage (3 node types):**
- `bash_hello.sh` — basic bash job: echo, date, env dump
- `python_hello.py` — basic Python job: sys.version, platform info, write a temp file
- `pwsh_hello.ps1` — basic PowerShell job: Get-Date, $PSVersionTable

**EE feature validation jobs:**
- `validate_volume_mapping.py` — writes a file to the mapped volume path; verifies it persists and is readable from the expected host-side mount
- `validate_network_filter.py` — attempts HTTP requests to an allowed and a blocked host; asserts expected pass/fail
- `validate_dir_mapping.sh` — lists a mapped directory; verifies expected files are present

**Resource limit enforcement jobs:**
- `memory_hog.py` — allocates memory progressively until killed; job should fail with OOM, not succeed
- `cpu_spin.py` — spins CPU at 100% for longer than the CPU limit allows; verify throttling or kill behaviour
- `disk_fill.py` — writes until hitting disk quota (if applicable)

**Acceptance criteria:**
- All jobs are signed with the test keypair before upload
- Each job has an expected exit code and stdout pattern documented
- Pass/fail is asserted in an automated test script (extend `test_local_stack.py` or create `test_job_library.py`)
- Resource limit jobs: verify the job is terminated, not that it completes
