---
phase: 103-windows-e2e-validation
plan: "02"
subsystem: testing
tags: [paramiko, ssh, windows, powershell, e2e-validation, claude-subagent]

requires:
  - phase: 103-windows-e2e-validation/103-01
    provides: Windows docs pre-audit (PowerShell tabs added to enroll-node.md, first-job.md)

provides:
  - run_windows_scenario.py — paramiko SSH helper library for Dwight interactions
  - run_windows_e2e.py — Phase 103 orchestrator (preflight, push, subagent, FRICTION pull)
  - invoke_subagent.ps1 — PowerShell wrapper that reads prompt from disk (avoids quoting failures)
  - windows_validation_prompt.md — Claude subagent persona + 5-step PowerShell golden path
  - Dwight credential placeholders in mop_validation/secrets.env

affects:
  - 103-windows-e2e-validation/103-03 (live execution run — uses all 4 files from this plan)

tech-stack:
  added: [paramiko (SSH client), requests (stack health polling)]
  patterns:
    - Fresh SSH connection per dwight_exec call (no persistent state — same as test_ssh.py)
    - ps1 wrapper pattern for multi-line CLI invocation (avoids pwsh -Command quoting failures)
    - SFTP mkdir -p equivalent via recursive _sftp_makedirs
    - Key-based SSH auth with password fallback
    - Dashboard polled directly from Linux host (requests.get, verify=False)

key-files:
  created:
    - /home/thomas/Development/mop_validation/scripts/run_windows_scenario.py
    - /home/thomas/Development/mop_validation/scripts/run_windows_e2e.py
    - /home/thomas/Development/mop_validation/scripts/invoke_subagent.ps1
    - /home/thomas/Development/mop_validation/scripts/windows_validation_prompt.md
  modified:
    - /home/thomas/Development/mop_validation/secrets.env (Dwight credential placeholders added)

key-decisions:
  - "invoke_subagent.ps1 reads prompt via Get-Content from disk rather than inline -Command — avoids PowerShell multi-line quoting failures documented in 103-RESEARCH.md"
  - "dwight_exec wraps every command in pwsh -NoProfile -NonInteractive -Command — Windows OpenSSH defaults to cmd.exe, not PowerShell"
  - "invoke_subagent called via raw exec_command with pwsh -NoProfile -File (not through dwight_exec wrapper) to avoid double-wrapping the -File invocation"
  - "windows_validation_prompt.md uses pre-placed keys (skip generation, not registration) — reduces subagent steps while still exercising the full signing flow"
  - "dwight_password=FILL_ME_IN placeholder added to secrets.env — user must supply real value before Plan 103-03"

patterns-established:
  - "ps1 wrapper pattern: push a .ps1 file to Dwight then invoke via pwsh -File to avoid quoting issues with multi-line strings"
  - "Paramiko fresh-connection-per-call: same pattern as test_ssh.py — no persistent connection state, simpler error handling"
  - "SFTP makedirs: recursive _sftp_makedirs handles Windows drive letter prefix (C:) correctly"

requirements-completed:
  - WIN-01
  - WIN-02

duration: 5min
completed: "2026-03-31"
---

# Phase 103 Plan 02: Windows E2E Scaffold Summary

**Paramiko SSH helper library + Phase 103 orchestrator + PowerShell subagent wrapper + first-user persona prompt for Dwight Windows validation**

## Performance

- **Duration:** 5 min
- **Started:** 2026-03-31T21:09:14Z
- **Completed:** 2026-03-31T21:13:57Z
- **Tasks:** 3 (Task 0 credential check, Task 1 scenario helpers, Task 2 three-file scaffold)
- **Files modified:** 5

## Accomplishments
- Created `run_windows_scenario.py` with 5 public helpers: `dwight_exec`, `dwight_push`, `dwight_pull`, `wait_for_stack_dwight`, `ensure_workspace_dwight`
- Created `invoke_subagent.ps1` — PowerShell wrapper that reads prompt from disk via `Get-Content`, eliminating the quoting failures that occur when passing multi-line content inline in `pwsh -Command`
- Created `run_windows_e2e.py` — 8-step Phase 103 orchestrator that mirrors `run_linux_e2e.py` structure but drives Dwight via paramiko SSH instead of incus exec
- Created `windows_validation_prompt.md` — 255-line PowerShell-only first-user persona with 5 golden path steps, FRICTION format spec, and pre-placed key instructions
- Added Dwight credential placeholders to `mop_validation/secrets.env` (real password must be filled in before Plan 103-03)

## Task Commits

Each task was committed atomically (in mop_validation repo):

1. **Task 0: Assert Dwight credentials** — secrets.env updated (gitignored, not committed)
2. **Task 1: run_windows_scenario.py** — `1cb04c6` (feat)
3. **Task 2: invoke_subagent.ps1 + run_windows_e2e.py + windows_validation_prompt.md** — `4f02293` (feat)

## Files Created/Modified

- `/home/thomas/Development/mop_validation/scripts/run_windows_scenario.py` — Paramiko helper library: `_connect_dwight`, `dwight_exec`, `dwight_push`, `dwight_pull`, `wait_for_stack_dwight`, `ensure_workspace_dwight`
- `/home/thomas/Development/mop_validation/scripts/run_windows_e2e.py` — Phase 103 orchestrator (7 functions + main)
- `/home/thomas/Development/mop_validation/scripts/invoke_subagent.ps1` — PowerShell wrapper for claude CLI invocation
- `/home/thomas/Development/mop_validation/scripts/windows_validation_prompt.md` — Subagent persona + golden path (255 lines)
- `/home/thomas/Development/mop_validation/secrets.env` — Dwight credential placeholders added (gitignored)

## Decisions Made

- **ps1 wrapper for subagent**: The research file explicitly warned that passing multi-line content inline in `pwsh -Command` fails due to quoting. The `invoke_subagent.ps1` wrapper reads the prompt via `Get-Content` from disk and is invoked via `pwsh -NoProfile -File` — no quoting issues.
- **pwsh prefix in dwight_exec**: Windows OpenSSH server defaults to `cmd.exe`, not PowerShell. Every command is automatically wrapped in `pwsh -NoProfile -NonInteractive -Command "..."` in `dwight_exec`.
- **Raw exec_command for subagent invocation**: `invoke_subagent` in `run_windows_e2e.py` bypasses `dwight_exec` and uses a raw paramiko `exec_command` with `pwsh -NoProfile -File`. This prevents the double-wrapping that would occur if `-File` were passed through the `-Command` wrapper.
- **Pre-placed signing keys**: The validation prompt instructs the subagent to skip key generation but still perform key registration. This exercises the full signing flow while reducing subagent friction.

## Deviations from Plan

None — plan executed exactly as written.

The only minor note: `secrets.env` is gitignored in `mop_validation` (expected for a credentials file), so the Task 0 credential addition was not committed to git. The file was updated on disk as required.

## Issues Encountered

None. All three Python files parsed without syntax errors on first write. All 7 verification checks passed.

## User Setup Required

**Before running Plan 103-03**, the user must fill in the real Dwight password in:
`/home/thomas/Development/mop_validation/secrets.env`

Change `dwight_password=FILL_ME_IN` to the actual password. The `dwight_ip=192.168.50.149` and `dwight_ssh_key=external_client_ed25519` values are pre-set.

## Next Phase Readiness

- Plan 103-03 (live execution run) can now proceed: all 4 Wave 1 infrastructure files exist
- Pre-condition: `dwight_password` must be set in `secrets.env` before running `run_windows_e2e.py`
- Optional: verify `external_client_ed25519` key file exists at `/home/thomas/Development/mop_validation/external_client_ed25519` for key-based auth

---
*Phase: 103-windows-e2e-validation*
*Completed: 2026-03-31*
