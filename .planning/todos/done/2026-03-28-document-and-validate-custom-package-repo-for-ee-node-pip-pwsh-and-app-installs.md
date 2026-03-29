---
created: 2026-03-28T17:26:51.990Z
title: Document and validate custom package repo for EE node pip, PWSH, and app installs
area: docs
files:
  - docs/docs/
  - puppeteer/agent_service/services/foundry_service.py
  - puppets/environment_service/
---

## Problem

The platform supports a custom package repository (local PyPI mirror, APT mirror, PWSH module feed) for air-gapped and controlled EE deployments. This feature exists in the code (Phase 13: Package Management & Custom Repos) but:

1. **No operator-facing docs** — there is no clear guide explaining how to: set up the mirror sidecars, upload packages, configure nodes to use the internal feed instead of the public internet
2. **No validation** — we have no automated check that a pip install, a pandas import, a PWSH `Install-Module`, or a custom app install actually resolves from the internal repo rather than the internet
3. **Operator friction** — the current flow requires understanding Docker sidecar config, pip.conf injection, and sources.list patching; this needs a guided wizard or at minimum a step-by-step operator runbook

## Solution

**Documentation:**
- Write an operator guide: "Custom Package Repositories" under the EE docs section
  - How to start the PyPI mirror sidecar (devpi or bandersnatch)
  - How to upload packages (pip download → devpi upload)
  - How to configure a Blueprint to use the internal feed (`pip.conf` injection recipe)
  - How to start the APT mirror sidecar and add a sources.list override
  - How to add a PWSH module feed (PSRepository registration)
  - Air-gap checklist: verify no outbound traffic during a job

**Validation jobs (linked to node-validation-jobs todo):**
- `validate_pip_internal_repo.py` — installs a known package, verifies it came from the internal mirror (check pip debug output for index URL)
- `validate_pwsh_module.ps1` — installs a PWSH module from the internal feed, verifies `Get-Module` shows it
- `validate_apt_package.sh` — apt-get installs a package, verifies sources.list was used

**Foundry UX improvements (if needed):**
- Blueprint editor should surface the internal repo config fields explicitly rather than requiring raw JSON
- Consider a "Use internal repo" toggle in the Foundry wizard that auto-injects the pip.conf/sources.list recipe
