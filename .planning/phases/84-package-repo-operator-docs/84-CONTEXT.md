# Phase 84: Package Repo Operator Docs - Context

**Gathered:** 2026-03-29
**Status:** Ready for planning

<domain>
## Phase Boundary

Operator runbooks for configuring devpi (PyPI), apt-cacher-ng (APT), and BaGet (PWSH/NuGet) package mirror sidecars from scratch, plus a signed pip-mirror validation job. Covers PKG-01 through PKG-04. Operators can follow the runbooks to point Foundry node image builds at internal mirrors and confirm packages resolve from those mirrors, not the public internet.

</domain>

<decisions>
## Implementation Decisions

### Doc placement
- New file: `docs/docs/runbooks/package-mirrors.md` — one combined page with H2 sections per mirror type (devpi, apt-cacher-ng, BaGet)
- Added to MkDocs nav under **Runbooks** in `docs/mkdocs.yml`
- `security/air-gap.md` keeps its existing shallow "Package Mirror Setup" section but adds a cross-link to the new runbook: "For a full from-scratch setup guide, see [Package Mirror Runbooks](../runbooks/package-mirrors.md)"
- Air-gap.md is NOT expanded in-place — it stays as a readiness-checklist context doc

### Runbook depth per mirror
- Each mirror section covers the full from-scratch setup:
  1. What the sidecar is and why to use it (one short paragraph)
  2. Compose snippet — the service block to add to `compose.server.yaml`
  3. Configuration steps — URL registration via API + any sidecar-specific config
  4. Initial seeding procedure — how to get packages into the mirror before going offline
  5. Verification step — confirm Foundry builds use the mirror (and for devpi: the PKG-04 validation job)
  6. Common issues — 2-4 inline bullet points covering likely failure modes
- Same depth for all three mirrors (devpi, apt-cacher-ng, BaGet)
- No verbose prose explanations — setup + verify format, theory skipped

### PKG-04 validation job
- Script: `tools/example-jobs/validation/verify_pypi_mirror.py`
- Behaviour: runs `pip install <package> -v` and captures stdout; searches for download URL in verbose output; PASSes if URL contains the expected mirror hostname, FAILs with clear message if URL is pypi.org or hostname not found
- Package used for the test install: `requests` (lightweight, universally available)
- Mirror hostname source: `PYPI_MIRROR_HOST` env var (e.g. `pypi-mirror:3141`) — operator sets this in the job dispatch payload; job fails clearly if env var is absent
- Added to `tools/example-jobs/manifest.yaml` with same metadata format as Phase 83 jobs
- Dispatch command and expected PASS/FAIL output documented inline in the runbook's devpi section as a "Verify the mirror works" subsection

### PWSH mirror (BaGet)
- Primary implementation: BaGet — simplest self-hosted NuGet v3 server, single Docker image, no auth required for internal use, compatible with PowerShell's `Register-PSRepository` and `Install-Module`
- Enterprise note: one short paragraph after the BaGet setup mentioning Sonatype Nexus and Artifactory as alternatives that expose NuGet v3 feeds (no full walkthrough — just a pointer)
- PKG-03 verification is two-part:
  1. **Blueprint config** — runbook shows how to add a `Register-PSRepository` call in a Foundry Blueprint so node images have the PSRepository pre-configured pointing at BaGet
  2. **Test job** — a PWSH job script that calls `Install-Module Pester -Repository AxiomInternal` and verifies import, confirming the module resolved from BaGet at runtime
- Example module: **Pester** (ubiquitous PWSH test framework, on PSGallery, familiar to all PWSH operators)
- Runbook shows: how to seed Pester into BaGet (download .nupkg from PSGallery, upload to BaGet admin), then the job script + dispatch command

### Claude's Discretion
- Exact compose snippet field values for BaGet and apt-cacher-ng (image versions, port mappings)
- Specific apt-cacher-ng config file structure (acng.conf content)
- Pester version to seed (use latest stable)
- Exact `pip install` verbose output format parsing in the validation script

</decisions>

<specifics>
## Specific Ideas

- Air-gap.md cross-link keeps the air-gap readiness checklist functional without duplicating setup instructions
- PKG-04 env var approach means the same job works for any custom mirror hostname, not just the default sidecar name
- Pester is the right example module — every PowerShell operator knows it, it's small, and it's available on PSGallery for seeding into BaGet

</specifics>

<code_context>
## Existing Code Insights

### Reusable Assets
- `docs/docs/runbooks/node-validation.md`: Established runbook format for this project — job-by-job sections with dispatch commands, expected PASS/FAIL output blocks. Package mirror runbook should follow the same structure for the verification sections.
- `tools/example-jobs/manifest.yaml`: Add PKG-04 job entry alongside existing Phase 83 validation jobs. Field format: `name`, `description`, `script`, `runtime`, `required_capabilities`, `env` (for PYPI_MIRROR_HOST).
- `docs/docs/security/air-gap.md`: Existing shallow mirror coverage at lines 27–70 — add cross-link here pointing to the new runbook.

### Established Patterns
- MkDocs nav in `docs/mkdocs.yml`: Runbooks section already has `node-validation.md` — add `package-mirrors.md` as the next entry in the same section.
- Job dispatch pattern: `axiom-push job push --script <path> --key signing.key --key-id <id>` — same pattern used in node-validation.md; PKG-04 dispatch command should match exactly.
- Runtime value for PWSH jobs: `powershell` (established in Phase 83 manifest).

### Integration Points
- `docs/mkdocs.yml` nav: Add `Package Mirror Setup: runbooks/package-mirrors.md` under the Runbooks section
- `docs/docs/security/air-gap.md`: Add cross-link sentence to the "Package Mirror Setup" section header
- `tools/example-jobs/manifest.yaml`: Add PKG-04 entry
- `tools/example-jobs/validation/`: New `verify_pypi_mirror.py` file

</code_context>

<deferred>
## Deferred Ideas

- APT mirror validation job (equivalent to PKG-04 for apt-cacher-ng) — the requirements only call for the PyPI validation job; APT and PWSH verification is documented in prose/command-line steps, not a signed job
- BaGet/NuGet validation job as a signed script — could mirror the PKG-04 pattern for PWSH; noted for a future phase
- Docs for the `mop_validation/reports/deployment_recomendations.md` content — captured as a separate todo

</deferred>

---

*Phase: 84-package-repo-operator-docs*
*Context gathered: 2026-03-29*
