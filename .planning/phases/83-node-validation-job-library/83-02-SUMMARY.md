---
phase: 83-node-validation-job-library
plan: "02"
subsystem: testing
tags: [bash, python, yaml, node-validation, example-jobs, job-corpus]

requires:
  - phase: 83-node-validation-job-library-plan-01
    provides: "test scaffold (test_example_jobs.py) and hello-world reference scripts"

provides:
  - "validation/volume-mapping.sh: JOB-04 volume mount read/write validation"
  - "validation/network-filter.py: JOB-05 network isolation validation (Docker --network=none)"
  - "validation/memory-hog.py: JOB-06 OOM validation with capability guard"
  - "validation/cpu-spin.py: JOB-07 CPU throttle measurement with capability guard"
  - "tools/example-jobs/manifest.yaml: machine-readable metadata for all 7 corpus members"

affects:
  - 83-node-validation-job-library-plan-03
  - phase-84-package-repo-operator-docs

tech-stack:
  added: []
  patterns:
    - "Capability guard pattern: check AXIOM_CAPABILITIES env var before executing resource-intensive operations; exit 1 with 'resource_limits_supported capability missing' message"
    - "Page-touching pattern: bytearray[0::4096] = b'\\x00' * (len // 4096) forces RSS commitment to prevent Linux overcommit from deferring memory allocation"
    - "manifest.yaml version: '1' schema: jobs list with name/description/script/runtime/required_capabilities"
    - "required_capabilities values must be quoted strings ('1.0') not YAML floats — job_service.py uses packaging.version.Version"

key-files:
  created:
    - tools/example-jobs/validation/volume-mapping.sh
    - tools/example-jobs/validation/network-filter.py
    - tools/example-jobs/validation/memory-hog.py
    - tools/example-jobs/validation/cpu-spin.py
    - tools/example-jobs/manifest.yaml
  modified: []

key-decisions:
  - "resource_limits_supported capability guard: scripts exit 1 (not error) when capability absent — safe abort, not a crash"
  - "network-filter.py validates isolation only, never manipulates iptables — avoids residual node-global state (locked CONTEXT.md decision)"
  - "memory-hog.py exit codes: 1=capability missing, 2=sentinel (should never reach), OOM-kill=expected success"
  - "manifest.yaml required_capabilities values quoted as strings ('1.0') because job_service.py compares via packaging.version.Version"

patterns-established:
  - "Capability guard: check AXIOM_CAPABILITIES before executing resource-intensive jobs"
  - "Validation exit codes: 0=pass, 1=capability/isolation failure, 2=error sentinel"

requirements-completed: [JOB-04, JOB-05, JOB-06, JOB-07]

duration: 3min
completed: 2026-03-28
---

# Phase 83 Plan 02: Node Validation Job Library — Validation Scripts and Manifest Summary

**Four capability-gated validation scripts (volume mapping, network isolation, OOM, CPU throttle) plus a manifest.yaml covering all 7 corpus members with dispatch parameters**

## Performance

- **Duration:** 3 min
- **Started:** 2026-03-28T20:59:27Z
- **Completed:** 2026-03-28T21:02:20Z
- **Tasks:** 2
- **Files modified:** 5

## Accomplishments

- Four validation scripts implementing JOB-04 through JOB-07 with correct capability guards, exit codes, and output format
- manifest.yaml covering all 7 corpus members with name, description, script path, runtime, and required_capabilities in machine-readable format
- All 8 tests in test_example_jobs.py pass (combined Plan 01 hello-world + Plan 02 validation tests)

## Task Commits

Each task was committed atomically:

1. **Task 1: Write the four validation scripts** - `0594b4a` (feat)
2. **Task 2: Write manifest.yaml with metadata for all 7 corpus members** - `29281fd` (feat)

## Files Created/Modified

- `tools/example-jobs/validation/volume-mapping.sh` - JOB-04: writes PID-unique sentinel at AXIOM_VOLUME_PATH, reads back, cleans up, exits 0 on success
- `tools/example-jobs/validation/network-filter.py` - JOB-05: verifies AXIOM_BLOCKED_HOST is unreachable; exits 0 if isolated, exits 1 if reachable
- `tools/example-jobs/validation/memory-hog.py` - JOB-06: capability-gated 256 MB page-touching hold; exits 1 if capability missing, expects OOM kill
- `tools/example-jobs/validation/cpu-spin.py` - JOB-07: capability-gated 5s CPU spin with wall/CPU ratio reporting; exits 1 if capability missing
- `tools/example-jobs/manifest.yaml` - 7-entry job manifest with dispatch parameters for all corpus members

## Decisions Made

- Capability guard exits with code 1 and a descriptive "resource_limits_supported capability missing" message — safe abort rather than crash, matches the test assertions
- network-filter.py uses `socket.create_connection` only and never touches iptables, per the locked CONTEXT.md decision on Docker-native `--network=none` isolation
- memory-hog.py uses `exit(2)` as a sentinel after the 30s sleep — if the process reaches that line it means resource limits were not enforced on the node
- manifest.yaml wraps `required_capabilities` values in quotes ("1.0") because YAML unquoted `1.0` is a float; job_service.py expects strings for `packaging.version.Version` comparison

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- All 7 corpus scripts are now in place with passing tests
- manifest.yaml is ready for use by operators as dispatch reference
- Plan 03 (sign_corpus.py and README) can proceed — it depends on all 7 scripts existing

## Self-Check: PASSED

All created files verified present. All task commits verified in git log.

---
*Phase: 83-node-validation-job-library*
*Completed: 2026-03-28*
