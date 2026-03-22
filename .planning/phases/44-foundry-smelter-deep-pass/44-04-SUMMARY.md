---
phase: 44-foundry-smelter-deep-pass
plan: "04"
subsystem: mop_validation/foundry-tests
tags: [foundry, smelter, airgap, iptables, mirror, verification]
dependency_graph:
  requires: []
  provides: [FOUNDRY-05 air-gap mirror verification script]
  affects: [mop_validation/scripts/]
tech_stack:
  added: []
  patterns: [iptables host isolation, try/finally cleanup, graceful SKIP on missing prerequisites]
key_files:
  created:
    - mop_validation/scripts/verify_foundry_05_airgap.py
  modified: []
decisions:
  - "FOUNDRY-05 skip conditions checked in priority order: Foundry feature inactive → no sudo iptables → no MIRRORED ingredients. Each path exits 0 with remediation instructions."
  - "_rules_added boolean guards finally block cleanup — partial rule insertion failure still triggers removal of any successfully-added rules."
  - "image URI lookup uses list+filter pattern (GET /api/templates then filter by id) — consistent with FOUNDRY-06 decision that no GET /api/templates/{id} endpoint exists."
metrics:
  duration: "3m"
  completed: "2026-03-22"
  tasks_completed: 1
  files_created: 1
---

# Phase 44 Plan 04: FOUNDRY-05 Air-gap Mirror Verification Summary

FOUNDRY-05 air-gap test script with iptables network isolation and finally-block cleanup guarantee.

## What Was Built

`mop_validation/scripts/verify_foundry_05_airgap.py` — verifies that a Foundry build using a locally MIRRORED ingredient succeeds when outbound access to pypi.org and files.pythonhosted.org is blocked at the host level via iptables.

### Script Flow

**Pre-flights (all exit 0 on failure — graceful SKIP):**
1. Foundry feature active check (`GET /api/features`) — [SKIP] on CE build
2. Passwordless sudo iptables check (`sudo -n iptables --version`) — [SKIP] if not configured
3. MIRRORED ingredient discovery (`GET /api/smelter/ingredients`) — [SKIP] if none found

**Main test block (inside try/finally):**
4. Insert iptables OUTPUT DROP rules for pypi.org + files.pythonhosted.org
5. Confirm rules active via `iptables -L OUTPUT -n`
6. Create runtime blueprint with the MIRRORED package
7. Create network blueprint
8. Create template combining both blueprints
9. Trigger build (`POST /api/templates/{id}/build`, 180s timeout) — succeeds via local mirror
10. Confirm image URI is non-empty after build

**Finally block (unconditional):** `remove_iptables_rules()` using `check=False` on each deletion — host network state is always restored before exit.

### Safety Design

The `_rules_added` boolean ensures the finally block only attempts cleanup if at least one rule insertion was attempted. `remove_iptables_rules()` uses `check=False` on every `-D` call so a partial insertion failure (first rule added, second fails) still results in complete cleanup.

## Verification Run

Script ran against local CE stack and exited [SKIP] FOUNDRY-05 (Foundry feature not active) with exit code 0. iptables OUTPUT chain was clean after exit — confirmed via `sudo iptables -L OUTPUT -n | grep pypi` returning empty.

## Deviations from Plan

None — plan executed exactly as written.

## Self-Check

- [x] `mop_validation/scripts/verify_foundry_05_airgap.py` created and committed (ba420e6)
- [x] Script exits 0 on SKIP outcome (verified)
- [x] iptables rules absent after script exit (verified)
- [x] finally block present and uses check=False on removal commands
