---
phase: 33-licence-compliance-release-infrastructure
plan: 01
subsystem: infra
tags: [licence, pyproject, pep639, packaging, setuptools, apache2]

# Dependency graph
requires: []
provides:
  - paramiko (LGPL-2.1) removed from all three requirements files
  - Root pyproject.toml updated to PEP 639 string licence format with setuptools>=77.0
  - puppeteer/pyproject.toml gains [build-system] and [project] sections with PEP 639 licence
affects: [phase-33-release, pypi-packaging, ghcr-release]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "PEP 639 licence string format: license = \"Apache-2.0\" (NOT table format)"
    - "setuptools>=77.0 required for PEP 639 compliance in [build-system]"

key-files:
  created: []
  modified:
    - requirements.txt
    - puppeteer/requirements.txt
    - puppets/requirements.txt
    - pyproject.toml
    - puppeteer/pyproject.toml

key-decisions:
  - "paramiko removed without replacement — no application code imports it; removal eliminates LGPL-2.1 concern entirely"
  - "puppeteer/pyproject.toml given minimal compliance stub [project] section — not a distributable package, stub exists solely to carry License-Expression metadata"
  - "setuptools>=61.0 bumped to >=77.0 — required for PEP 639 string licence field support"

patterns-established:
  - "PEP 639: use plain string license = \"Apache-2.0\", never table format license = {text = ...}"

requirements-completed: [LICENCE-02, LICENCE-04]

# Metrics
duration: 3min
completed: 2026-03-18
---

# Phase 33 Plan 01: Licence Compliance — Paramiko Removal + PEP 639 Metadata Summary

**Eliminated LGPL-2.1 concern by removing unused paramiko from all three requirements files and updated both pyproject.toml files to PEP 639 string licence format with setuptools>=77.0**

## Performance

- **Duration:** ~3 min
- **Started:** 2026-03-18T13:09:25Z
- **Completed:** 2026-03-18T13:11:53Z
- **Tasks:** 2
- **Files modified:** 5

## Accomplishments
- Removed paramiko (LGPL-2.1) from requirements.txt, puppeteer/requirements.txt, and puppets/requirements.txt — confirmed zero application imports
- Updated root pyproject.toml: setuptools>=61.0 -> >=77.0 and deprecated `license = {text = "Apache-2.0"}` -> PEP 639 `license = "Apache-2.0"`
- Added [build-system] and [project] sections to puppeteer/pyproject.toml as minimal compliance stub with PEP 639 licence field

## Task Commits

Each task was committed atomically:

1. **Task 1: Remove paramiko from all three requirements files** - `5399101` (chore)
2. **Task 2: Update pyproject.toml files to PEP 639 licence format** - `0b6b2c3` (chore)

**Plan metadata:** (final commit — docs)

## Files Created/Modified
- `requirements.txt` - paramiko line removed
- `puppeteer/requirements.txt` - paramiko line removed
- `puppets/requirements.txt` - paramiko line removed
- `pyproject.toml` - setuptools>=77.0, license string format (PEP 639)
- `puppeteer/pyproject.toml` - [build-system] + [project] sections prepended with PEP 639 licence

## Decisions Made
- **paramiko removed without replacement:** grep confirms zero imports in application code (`agent_service/`, `model_service/`, `puppets/environment_service/`). Removal is safe and fully eliminates the LGPL-2.1 concern.
- **puppeteer/pyproject.toml stub:** puppeteer is not a distributable package. The [project] section is a minimal compliance stub — name, version, licence, requires-python only. The existing [tool.black] and [tool.ruff] sections follow unchanged.
- **setuptools version bump:** PEP 639 string licence field requires setuptools>=77.0 for correct wheel metadata generation. Root updated; puppeteer stub uses same minimum.

## Deviations from Plan

None — plan executed exactly as written.

## Issues Encountered
- pytest invocation required venv path (`/.venv/bin/pytest`) — system PATH does not include project venv
- 15 pre-existing test failures in `test_job_staging.py` confirmed identical before and after changes (git stash check); no regressions introduced

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- LICENCE-02 and LICENCE-04 requirements satisfied
- Remaining Phase 33 plans: LEGAL.md/NOTICE file creation, PyPI Trusted Publisher setup, GHCR image publishing
- PyPI Trusted Publisher still blocked on `axiom-laboratories` GitHub org creation (deferred from Phase 27-03)

---
*Phase: 33-licence-compliance-release-infrastructure*
*Completed: 2026-03-18*
