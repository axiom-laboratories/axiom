---
phase: 102-linux-e2e-validation
plan: "01"
subsystem: validation-infrastructure
tags: [e2e, linux, validation, lxc, friction, orchestrator, subagent]
dependency_graph:
  requires: []
  provides:
    - run_linux_e2e.py orchestrator for Phase 102 LXC-based E2E validation
    - linux_validation_prompt.md first-user persona with 7-step golden path
    - synthesise_friction.py --files flag for single-file processing
  affects:
    - mop_validation/scripts/run_linux_e2e.py
    - mop_validation/scripts/linux_validation_prompt.md
    - mop_validation/scripts/synthesise_friction.py
tech_stack:
  added: []
  patterns:
    - LXC reprovision via provision_coldstart_lxc.py --stop + reprovision
    - Claude subagent invoked via claude --dangerously-skip-permissions -p inside container
    - FRICTION file format (BLOCKER/NOTABLE/ROUGH EDGE/MINOR) for structured findings
key_files:
  created:
    - /home/thomas/Development/mop_validation/scripts/run_linux_e2e.py
    - /home/thomas/Development/mop_validation/scripts/linux_validation_prompt.md
  modified:
    - /home/thomas/Development/mop_validation/scripts/synthesise_friction.py
decisions:
  - Exit code 2 (not 1) used for pre-flight failures to distinguish image-unreachable from run-failure
  - Subagent non-zero exit is tolerated — fallback FRICTION file written if output absent
  - synthesise_friction.py _derive_edition() uses filename stem parsing for non-CE/EE run prefixes
metrics:
  duration: "4 min"
  completed: "2026-03-31"
  tasks_completed: 3
  files_created: 2
  files_modified: 1
---

# Phase 102 Plan 01: Validation Infrastructure Setup Summary

Wave 0 infrastructure for Linux E2E validation: LXC orchestrator, first-user persona prompt, and friction synthesiser patch for single-file use.

## Tasks Completed

| Task | Name | Commit | Key Files |
|------|------|--------|-----------|
| 1 | Create run_linux_e2e.py orchestrator | 8af19e0 (mop_validation) | scripts/run_linux_e2e.py |
| 2 | Create linux_validation_prompt.md subagent persona | d36e449 (mop_validation) | scripts/linux_validation_prompt.md |
| 3 | Patch synthesise_friction.py to accept --files argument | f78b0a1 (mop_validation) | scripts/synthesise_friction.py |

## Verification Results

All 4 post-execution checks passed:
1. `run_linux_e2e.py` parses without syntax errors
2. `synthesise_friction.py --help` shows `--files` flag
3. `linux_validation_prompt.md` is 228 lines (minimum 80)
4. `synthesise_friction.py --files FRICTION-CE-INSTALL.md` processes CE file without hardcoded-file error

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed typo in report_summary() string formatting**
- **Found during:** Task 1 (after initial write)
- **Issue:** `'YES' % ()` was invalid Python (old-style % formatting with no args on a string literal, not a variable)
- **Fix:** Replaced with `'YES' if has_blocker else 'NO'` in f-string
- **Files modified:** `scripts/run_linux_e2e.py`
- **Commit:** Inline fix before Task 1 commit

## Self-Check: PASSED

Files verified present:
- /home/thomas/Development/mop_validation/scripts/run_linux_e2e.py — FOUND
- /home/thomas/Development/mop_validation/scripts/linux_validation_prompt.md — FOUND
- /home/thomas/Development/mop_validation/scripts/synthesise_friction.py (modified) — FOUND

Commits verified (mop_validation repo):
- 8af19e0 — FOUND
- d36e449 — FOUND
- f78b0a1 — FOUND
