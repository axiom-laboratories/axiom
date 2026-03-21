---
created: 2026-03-21T21:50:41.075Z
title: Update documentation after runtime expansion and user story alignment milestones
area: docs
files:
  - docs/
  - mop_validation/reports/node_job_runtime_expansion.md
  - mop_validation/reports/user_story_friction.md
  - mop_validation/reports/apt_package_management.md
---

## Problem

Two milestones will introduce significant changes to MoP's operator-facing behaviour and UI. Documentation must be updated after both are complete to reflect the new reality. Shipping features without updated docs creates operator confusion and support overhead — especially for a product positioning itself as enterprise-grade.

**Changes introduced by Runtime Expansion milestone:**
- New `script` task type with `runtime` field (`python`, `bash`, `powershell`)
- `python_script` retained as alias — document the migration path
- Bash and PowerShell capability reporting on nodes
- Updated `Containerfile.node` — document what tools ship in the standard CE image
- New validation test scripts in `mop_validation/scripts/`

**Changes introduced by User Story Alignment milestone:**
- Guided job form (two-mode: guided vs advanced) — operators need to know both modes exist
- Job detail drawer — document the resubmit and edit-and-resubmit flows
- Scheduled job DRAFT state — operators need to understand the new signing lifecycle
- TOTP 2FA setup and recovery — must be documented clearly, especially the air-gap/NTP requirement
- Inline keypair generation (CE) — document the workflow end to end
- Key approval workflow (EE) — document separation of duties model
- UI label renames (Blueprint → Image Recipe, PuppetTemplate → Node Image, etc.) — all existing docs that reference old names need updating

## Solution

1. **Do not action this todo until both milestones are marked complete.** Documenting features before they are built risks docs diverging from implementation.
2. Run `/write-documentation` skill against both milestones' completed phases to generate first-draft docs
3. Priority areas to cover:
   - Getting started / first job guide — must reflect guided form and inline signing
   - Multi-runtime job submission — bash and pwsh examples with signing walkthrough
   - Scheduled jobs — include DRAFT state lifecycle and notification behaviour
   - Security model — TOTP setup, key approval, separation of duties
   - Node deployment (CE) — updated standard image tool inventory
   - EE Foundry / Image Recipes — updated terminology throughout
4. Cross-reference with the docs branding todo (`update-docs-wiki-branding-to-match-dashboard-identity`) — do both in the same pass if possible to avoid touching docs twice
5. Check all existing docs for references to old UI labels (Blueprint, PuppetTemplate) and update to new display names
