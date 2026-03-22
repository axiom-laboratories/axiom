---
phase: 44-foundry-smelter-deep-pass
plan: "03"
subsystem: validation-scripts
tags: [foundry, playwright, api-test, wizard-flow, FOUNDRY-01]
dependency_graph:
  requires: [44-02]
  provides: [verify_foundry_01_wizard.py]
  affects: [mop_validation/scripts/]
tech_stack:
  added: []
  patterns: [verify_job_01_fast canonical pattern, React native value setter login, Playwright wizard navigation]
key_files:
  created:
    - mop_validation/scripts/verify_foundry_01_wizard.py
  modified: []
decisions:
  - "Approved OS seed is non-destructive: script checks existing entries before POST /api/approved-os — idempotent on re-run"
  - "GET /api/templates/{id} used for image_uri confirmation with list-fallback — avoids list_images() stub that always returns []"
  - "Playwright login uses React native value setter pattern (MEMORY.md) — fill() alone does not update React controlled state"
  - "Both [SKIP] outcomes (EE not active, playwright not installed) exit 0 — consistent with pre-flight skip pattern from Phase 43"
metrics:
  duration: "2m"
  completed: "2026-03-22T09:16:50Z"
  tasks: 1
  files: 1
---

# Phase 44 Plan 03: Foundry Wizard Flow Verification (FOUNDRY-01) Summary

Single-script dual-coverage validation for FOUNDRY-01: verifies the full Foundry wizard pipeline at both the API layer (blueprints → template → build → image tag) and the Playwright browser layer (5-step BlueprintWizard UI flow).

## What Was Built

`mop_validation/scripts/verify_foundry_01_wizard.py` — a 300-line validation script with two sequential sections:

**API Section (Steps 1-7):**
1. EE feature pre-flight — [SKIP] if `foundry` not in `/api/features` (CE stack)
2. Approved OS seed — non-destructive POST of `DEBIAN/debian:12-slim` if absent
3. Runtime blueprint creation — `POST /api/blueprints` type=RUNTIME, packages={"python": []}
4. Network blueprint creation — `POST /api/blueprints` type=NETWORK, policy=deny-all
5. Template creation — `POST /api/templates` combining both blueprint IDs
6. Build trigger — `POST /api/templates/{id}/build` with 180s timeout (synchronous Docker build)
7. Image tag confirmation — `GET /api/templates/{id}` → asserts `current_image_uri` is non-empty, with list fallback

**Playwright Section (Steps 8-13):**
8. Login via React native value setter (not fill() — per MEMORY.md pattern)
9. Navigate to `/templates`, open wizard via "New Blueprint" button
10. Step 1: Fill friendly name, select DEBIAN OS family
11. Step 2: Select `debian:12-slim` from approved OS list
12. Steps 3-4: Skip ingredients and tools
13. Step 5: Click Build, wait up to 180s for success text in build log

Screenshot on failure: `/tmp/foundry_wizard_failure.png`

## Verification Result

Script ran against the live stack (CE mode — EE licence not loaded):
```
=== FOUNDRY-01: Full Foundry Wizard Flow (API + Playwright) ===
Waiting for stack at https://localhost:8001
[OK] Stack is up
[SKIP] FOUNDRY-01: EE foundry feature not active — is EE licence loaded?
       Check: GET /api/features; ensure AXIOM_LICENCE_KEY is set in compose.server.yaml
EXIT CODE: 0
```

[SKIP] + exit 0 is the correct outcome for CE stack — consistent with done criteria. Full [PASS] requires EE stack with `AXIOM_LICENCE_KEY` set.

## Deviations from Plan

None — plan executed exactly as written.

## Key Design Decisions

**Approved OS seed strategy:** Pre-flight checks existing entries via GET /api/approved-os before seeding — avoids duplicate entries on re-run. Uses DEBIAN family matching (not exact string) for robustness.

**Image tag confirmation fallback:** Primary assertion uses `GET /api/templates/{id}`, with a fallback to `GET /api/templates` list + filter. This handles any edge case where the single-item endpoint is unavailable.

**Playwright selector strategy (role-based first):** `get_by_role("button", name="Next")` as primary for all wizard progression, with CSS/text fallbacks. Combobox click uses Radix select pattern (click to open, then click option) before falling back to native `<select>`.

**Wizard "New Blueprint" entry point:** Three-tier fallback: `get_by_role("button", name="New Blueprint")` → `:has-text('New Blueprint')` → `:has-text('New')`.first — handles minor UI label variations.

## Self-Check: PASSED

- File exists: `mop_validation/scripts/verify_foundry_01_wizard.py` — FOUND
- Commit 55f4fc4 exists — FOUND
