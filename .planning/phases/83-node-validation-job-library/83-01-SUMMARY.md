---
phase: 83-node-validation-job-library
plan: "01"
subsystem: testing
tags: [pytest, bash, python, powershell, example-jobs, tdd]

requires: []
provides:
  - Wave 0 pytest test scaffold covering all 7 JOB-0x example jobs plus manifest
  - bash/hello.sh reference job (JOB-01): hostname, OS, Bash version, timestamp
  - python/hello.py reference job (JOB-02): hostname, OS, Python version, timestamp
  - pwsh/hello.ps1 reference job (JOB-03): hostname, OS, PS version, timestamp
  - tools/example-jobs/ directory structure with bash/, python/, pwsh/, validation/ subdirs
affects:
  - 83-02 (validation jobs — 5 remaining tests become green)
  - 83-03 (sign_corpus.py — signs scripts from this corpus)

tech-stack:
  added: []
  patterns:
    - "Test scaffold committed before scripts exist (TDD Wave 0): tests fail cleanly with pytest.fail() + helpful message when file missing"
    - "REPO_ROOT discovery via pathlib walk-up to tools/ dir; git fallback for edge cases"
    - "Example jobs use shebang + set -euo pipefail (bash) or plain print statements (Python) — no external deps"

key-files:
  created:
    - puppeteer/tests/test_example_jobs.py
    - tools/example-jobs/bash/hello.sh
    - tools/example-jobs/python/hello.py
    - tools/example-jobs/pwsh/hello.ps1
  modified: []

key-decisions:
  - "Scripts committed unsigned per plan locked decision — no .sig companion files at this stage"
  - "test_volume_mapping passes immediately due to pre-existing tools/example-jobs/validation/volume-mapping.sh — treated as expected bonus, not a deviation"

patterns-established:
  - "Wave 0 TDD: write all 8 tests first (all fail), then commit scripts to turn them green one by one"
  - "pytest.fail() with path + hint message on missing file — gives operators a clear signal when corpus is incomplete"

requirements-completed: [JOB-01, JOB-02, JOB-03]

duration: 2min
completed: 2026-03-28
---

# Phase 83 Plan 01: Node Validation Job Library — Wave 0 Scaffold + Hello-World Jobs Summary

**Wave 0 pytest scaffold (8 tests) covering all 7 JOB-0x corpus members plus manifest, with bash/python/PowerShell hello-world reference jobs printing hostname, OS, runtime version, timestamp, and === PASS ===**

## Performance

- **Duration:** ~2 min
- **Started:** 2026-03-28T20:59:02Z
- **Completed:** 2026-03-28T21:01:01Z
- **Tasks:** 2
- **Files modified:** 4 created

## Accomplishments

- Created `puppeteer/tests/test_example_jobs.py` with 8 tests — Wave 0 scaffold committed before scripts existed (TDD RED phase)
- Wrote three hello-world reference jobs (Bash JOB-01, Python JOB-02, PowerShell JOB-03) passing their respective tests
- Established `tools/example-jobs/{bash,python,pwsh,validation}/` directory layout for the full corpus

## Task Commits

Each task was committed atomically:

1. **Task 1 RED: Wave 0 test scaffold** - `b17cbcf` (test)
2. **Task 2 GREEN: Hello-world reference jobs** - `11355f6` (feat)

**Plan metadata:** (docs commit follows)

_Note: TDD task has RED commit (test scaffold) followed by GREEN commit (implementation)_

## Files Created/Modified

- `puppeteer/tests/test_example_jobs.py` — 8 pytest tests; covers bash/python/pwsh hello-world, 4 validation script stubs (Plan 02), and manifest.yaml validation; uses pathlib repo-root discovery
- `tools/example-jobs/bash/hello.sh` — JOB-01; prints hostname (hostname), OS (uname -sr), BASH_VERSION, UTC timestamp; exits 0; `=== PASS ===` marker
- `tools/example-jobs/python/hello.py` — JOB-02; prints hostname (socket.gethostname()), OS (platform.system/release), Python version (platform.python_version()), UTC timestamp; exits 0; `=== PASS ===` marker
- `tools/example-jobs/pwsh/hello.ps1` — JOB-03; Write-Host lines for hostname (COMPUTERNAME ?? hostname fallback), OS (RuntimeInformation.OSDescription), PSVersionTable.PSVersion, UTC timestamp; `=== PASS ===` marker

## Decisions Made

- Scripts committed unsigned per plan locked decision — no `.sig` companion files; signing is handled by Plan 03 (`sign_corpus.py`)
- `test_volume_mapping` passes immediately because `tools/example-jobs/validation/volume-mapping.sh` pre-existed in the filesystem (untracked) — treated as a bonus rather than an issue

## Deviations from Plan

None - plan executed exactly as written. The pre-existing `volume-mapping.sh` means 4 tests pass (not 3) but all success criteria are met:
- test_hello_bash, test_hello_python, test_hello_pwsh all pass
- remaining 4 tests fail with clear pytest.fail() messages (expected)
- 8 tests collected, 0 import errors

## Issues Encountered

None.

## Next Phase Readiness

- Plan 02 can now write the 4 remaining validation scripts (volume-mapping, network-filter, memory-hog, cpu-spin) plus manifest.yaml, turning 4 failing tests green
- The pre-existing volume-mapping.sh in validation/ is a head start for Plan 02

---
*Phase: 83-node-validation-job-library*
*Completed: 2026-03-28*
