---
phase: 84-package-repo-operator-docs
plan: 01
subsystem: testing
tags: [pip, pypi, devpi, validation, example-jobs, tdd]

requires:
  - phase: 83-node-validation-job-library
    provides: corpus manifest (manifest.yaml), test scaffold pattern (test_example_jobs.py), signing infrastructure

provides:
  - PKG-04 pip-mirror validation job script (verify_pypi_mirror.py)
  - 8-entry corpus manifest with validation-pypi-mirror entry
  - test_pypi_mirror_script and test_pypi_mirror_no_env test coverage

affects:
  - 84-02 runbook and signing docs (references verify_pypi_mirror.py)
  - corpus README (new entry to catalog)

tech-stack:
  added: []
  patterns:
    - "Wave 0 TDD: failing tests committed before script exists, pytest.fail() gives clear missing-file message"
    - "PKG-04 validation pattern: pip --dry-run -v, parse Downloading lines for mirror vs pypi.org hostname"
    - "Env-guard pattern: exit 1 immediately with descriptive message when required env var is empty"

key-files:
  created:
    - tools/example-jobs/validation/verify_pypi_mirror.py
  modified:
    - tools/example-jobs/manifest.yaml
    - puppeteer/tests/test_example_jobs.py

key-decisions:
  - "env block omitted from manifest.yaml entry — PYPI_MIRROR_HOST documented in runbook prose, not manifest (not a standard dispatch field)"
  - "Exit 1 on missing PYPI_MIRROR_HOST before running pip — avoids silent false negatives where pip falls back to pypi.org"
  - "Downloading-line parsing used for pip --dry-run -v output — more reliable than index URL headers across pip versions"

patterns-established:
  - "Pattern: pip mirror validation — use --dry-run -v and parse Downloading lines for hostname presence"
  - "Pattern: no-env guard — required env vars checked at top, sys.exit(1) with VARNAME in message (test_pypi_mirror_no_env asserts this)"

requirements-completed: [PKG-04]

duration: 8min
completed: 2026-03-29
---

# Phase 84 Plan 01: PKG-04 PyPI Mirror Validation Job Summary

**pip mirror validation job using --dry-run -v Downloading-line parsing with PYPI_MIRROR_HOST guard, corpus manifest updated to 8 entries, full TDD test coverage**

## Performance

- **Duration:** ~8 min
- **Started:** 2026-03-29T15:40:00Z
- **Completed:** 2026-03-29T15:48:00Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments

- Created `verify_pypi_mirror.py` following the established `network-filter.py` code pattern with env guard, pip subprocess call, Downloading-line parsing, and PASS/FAIL exit codes
- Updated `test_example_jobs.py` with two new tests (`test_pypi_mirror_script`, `test_pypi_mirror_no_env`) and corrected manifest count assertion to 8
- Added `validation-pypi-mirror` entry to `manifest.yaml` bringing the corpus to 8 jobs

## Task Commits

1. **Task 1: Script + test scaffold (TDD)** - `82ba3ad` (feat)
2. **Task 2: Add manifest entry** - `4ac3327` (feat)

## Files Created/Modified

- `tools/example-jobs/validation/verify_pypi_mirror.py` - PKG-04 validation script: checks PYPI_MIRROR_HOST, runs pip --dry-run -v, parses Downloading lines
- `tools/example-jobs/manifest.yaml` - Added 8th entry: validation-pypi-mirror
- `puppeteer/tests/test_example_jobs.py` - Added test_pypi_mirror_script, test_pypi_mirror_no_env; updated manifest count to 8

## Decisions Made

- `env` block omitted from manifest.yaml — PYPI_MIRROR_HOST is documented in runbook prose only (not a standard dispatch field)
- Script exits 1 immediately when PYPI_MIRROR_HOST is unset before spawning pip — prevents silent false negatives if pip falls back to pypi.org
- Downloading-line parsing approach used (not index URL headers) — more reliable across pip 22.1+ versions

## Deviations from Plan

None — plan executed exactly as written.

## Issues Encountered

None.

## Next Phase Readiness

- PKG-04 script is signed-and-dispatch-ready once the operator runs `sign_corpus.py` (Phase 83 infrastructure)
- Runbook prose (84-02) can now reference `verify_pypi_mirror.py` by confirmed path
- All 10 tests in `test_example_jobs.py` pass

---
*Phase: 84-package-repo-operator-docs*
*Completed: 2026-03-29*
