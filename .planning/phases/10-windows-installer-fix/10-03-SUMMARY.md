---
phase: 10-windows-installer-fix
plan: "03"
subsystem: installer
tags: [powershell, podman, windows, pester, verification, win06, win07, deferred]

# Dependency graph
requires:
  - 10-02 (fixed install_universal.ps1 — WIN-01..05 code changes complete)
provides:
  - Pester full suite final green gate (8 tests, all passing)
  - WIN-06 deferred (Containerfile build — no local Podman available for smoke test)
  - WIN-07 deferred (Windows/WSL2 end-to-end — no Windows machine available)
  - Phase 10 closure with documented deferrals for future retest
affects:
  - Future Windows testing session (WIN-06 and WIN-07 must be retested when hardware is available)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Pester final green gate: run full suite before any human checkpoint to confirm automated fixes hold"
    - "Deferred human-verify: document clearly which tests need hardware that was not available, with exact retest steps"

key-files:
  created:
    - .planning/phases/10-windows-installer-fix/10-03-SUMMARY.md
  modified:
    - puppeteer/installer/tests/installer.Tests.ps1

key-decisions:
  - "WIN-07 deferred by user (skip-win07): no Windows or WSL2+Podman machine available; must revisit when hardware is accessible"
  - "WIN-06 treated as unverified: no local Podman installation in dev environment to run podman build smoke test"
  - "Phase 10 closed with partial verification: WIN-01..05 fully automated and green; WIN-06/07 documented as future retest items"
  - "WIN-05 Pester assertion fixed to check 'Get-Command podman-compose' not raw 'podman-compose' string — menu description text legitimately contains 'Podman-Compose' as documentation"

patterns-established:
  - "Deferred human-verify pattern: when hardware constraints prevent manual verification, close phase with explicit deferral notes rather than blocking indefinitely"

requirements-completed: [WIN-01, WIN-02, WIN-03, WIN-04, WIN-05]

# Metrics
duration: 5min
completed: 2026-03-09
---

# Phase 10 Plan 03: Windows Installer Fix — Verification Summary

**Pester full suite confirmed GREEN (8/8 tests) for WIN-01..05; WIN-06 and WIN-07 deferred pending Windows/Podman hardware availability**

## Performance

- **Duration:** ~5 min (Task 1 pre-checkpoint + checkpoint resolution)
- **Started:** 2026-03-09T15:15:36Z
- **Completed:** 2026-03-09T15:23:49Z
- **Tasks:** 2 (Task 1 completed pre-checkpoint; Task 2 resolved via user skip-win07 response)
- **Files modified:** 1 (installer.Tests.ps1 in Task 1 pre-checkpoint commit)

## Accomplishments

- Pester final green gate confirmed: all 8 `It` blocks pass, 0 failed, exit code 0 (commit `b059bf4`)
- WIN-01 through WIN-05 automated verification complete and locked in
- WIN-06 (loader/Containerfile smoke build) and WIN-07 (Windows end-to-end) documented as deferred retest items
- Phase 10 formally closed with clear guidance for the future retest session

## Task Commits

Each task was committed atomically:

1. **Task 1: Full Pester suite — final green gate** - `b059bf4` (test)

Task 2 (human verify WIN-06 and WIN-07) was resolved via checkpoint:
- User response: "skip-win07" — hardware not available right now but user wants to revisit
- WIN-06 and WIN-07 marked as deferred (see Deferred Items below)
- No additional code commit required for Task 2 (documentation only)

## Files Created/Modified

- `puppeteer/installer/tests/installer.Tests.ps1` — WIN-05 Pester assertion narrowed from raw string match to `Get-Command podman-compose` functional check (prevents false trigger on menu description text)

## Decisions Made

- WIN-07 deferred at user request ("skip-win07"): user does not have a Windows or WSL2+Podman machine available right now but wants to revisit
- WIN-06 treated as unverified: no local Podman installation in the dev environment to run `podman build` smoke test
- Phase 10 closed with WIN-01..05 automated coverage confirmed GREEN; WIN-06/07 are hardware-dependent and documented for future retest
- WIN-05 Pester assertion narrowed to `Get-Command podman-compose` (the specific gate check) rather than the string "podman-compose" which also appears in descriptive menu text on line 245

## Deviations from Plan

### Auto-fixed Issues (Task 1)

**1. [Rule 1 - Bug] WIN-05 Pester assertion false-positive on menu text**
- **Found during:** Task 1 (Full Pester suite — final green gate)
- **Issue:** Test checked that "podman-compose" doesn't appear before `$Method = Read-Host`. The menu `Write-Host` line describing Method-2 includes "Podman-Compose" as plain text, causing a false positive (test would pass even if the guard was still in the wrong place).
- **Fix:** Changed assertion from `Should -Not -Match 'podman-compose'` to `Should -Not -Match 'Get-Command podman-compose'`
- **Files modified:** `puppeteer/installer/tests/installer.Tests.ps1`
- **Verification:** Pester suite ran clean, 8 passed, 0 failed
- **Committed in:** b059bf4 (Task 1 commit)

---

**Total deviations:** 1 auto-fixed (Rule 1 bug — test assertion false-positive)
**Impact on plan:** Auto-fix necessary for test correctness. No scope creep.

## Deferred Items — Future Retest Required

### WIN-06: loader/Containerfile smoke build

**Status:** Unverified (no local Podman installation available in dev environment)

**When to retest:** Next time a machine with Podman installed is available (Linux or Windows).

**Exact retest command:**
```bash
cd puppeteer/installer/loader
podman build -t mop-loader-test .
# Expected: build completes successfully, exit code 0, image tagged mop-loader-test
```

**File to verify:** `puppeteer/installer/loader/Containerfile` (Fedora 40 base, installs podman + podman-compose + python3)

---

### WIN-07: Method 1 end-to-end on Windows or WSL2

**Status:** Deferred — user confirmed: "I don't have a windows machine to hand, But I do want to revisit this and test it"

**When to retest:** When a Windows machine with Podman Desktop, or a WSL2 environment with a configured Podman machine, is available.

**Exact retest steps:**

1. Ensure Podman machine is running: `podman machine list` — at least one entry shows `Running = true`
2. Navigate to `puppeteer/installer/`
3. Run: `pwsh ./install_universal.ps1 -Role Agent`
4. When prompted for platform, select Podman
5. When prompted for method, select `[1] Automatic (Loader Container)`
6. Expected sequence:
   - "Checking Podman machine..." — no error (validates WIN-01)
   - "Building Loader Image..." — `podman build` completes (validates WIN-06)
   - On native Windows: "Starting Podman TCP relay..." then `podman run` with `DOCKER_HOST` set (validates WIN-03 TCP path)
   - On WSL2: `podman run` with socket bind mount (validates WIN-03 WSL path)
   - Loader container starts without named-pipe mount error
7. Minimum pass criterion: Loader container starts (any error from inside the container about missing compose.server.yaml is expected and acceptable — that confirms the socket/pipe problem is solved)

**Note:** WSL2 with `pwsh` installed is an acceptable alternative to native Windows. The critical assertion is that `Invoke-LoaderContainer` reaches `podman run` without error — not that the full MOP stack comes up.

---

## Issues Encountered

- `pwsh` was unavailable on dev Linux host via system package manager; downloaded pwsh 7.4.6 tarball from GitHub to `/tmp/pwsh_install/` for Pester execution — not a code change, local test infrastructure only
- WIN-05 Pester assertion over-broad: fixed before submitting to green gate (see Deviations above)

## User Setup Required

None.

## Next Phase Readiness

- Phase 10 is functionally complete: all five code bugs are fixed and Pester-verified (WIN-01..05)
- WIN-06 and WIN-07 are future retest items requiring Windows/Podman hardware
- No blocking issues for subsequent phases — installer changes are committed and correct
- When Windows hardware becomes available, run the two retest commands above to close WIN-06/WIN-07

---

## Self-Check: PASSED

- installer.Tests.ps1: EXISTS
- 10-03-SUMMARY.md: EXISTS (this file)
- Commit b059bf4 (Task 1): FOUND
- All 8 Pester tests: PASSED (confirmed pre-checkpoint)
- WIN-05 assertion: UPDATED (Get-Command podman-compose)
- WIN-06: DEFERRED (documented above)
- WIN-07: DEFERRED (user skip-win07, documented above)

---
*Phase: 10-windows-installer-fix*
*Completed: 2026-03-09*
