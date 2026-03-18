# Phase 33: Licence Compliance + Release Infrastructure - Context

**Gathered:** 2026-03-18
**Status:** Ready for planning

<domain>
## Phase Boundary

Satisfy dual-licence obligations through compliance documentation, update pyproject.toml files to PEP 639, create the NOTICE attribution file, and activate the release infrastructure so version tags trigger automated PyPI + GHCR publishing. No new features — this is documentation, configuration, and external service wiring.

</domain>

<decisions>
## Implementation Decisions

### paramiko (LICENCE-04)
- Remove paramiko from both `puppeteer/requirements.txt` and `puppets/requirements.txt` — it is in requirements.txt but has zero imports in any application code
- Add a brief removal note in LEGAL-COMPLIANCE.md: paramiko was removed in v10.0 — not used in application code; LGPL-2.1 concern eliminated
- This satisfies LICENCE-04 via removal rather than linkage documentation

### LEGAL.md / compliance documentation (LICENCE-01, LICENCE-04)
- Create a new `LEGAL-COMPLIANCE.md` at repo root — do NOT modify the existing `LEGAL.md` (that is the CE/EE policy/marketing doc, leave it as-is)
- Audience: internal team and enterprise buyers — technical compliance language, suitable for a legal team to review
- LEGAL-COMPLIANCE.md cites `python_licence_audit.md` and `node_licence_audit.md` as the evidence base (don't duplicate the full 81-package table inline)
- Must cover: certifi MPL-2.0 (read-only CA bundle, no source modification, LICENCE-01), paramiko removal note (LICENCE-04)

### pyproject.toml / PEP 639 (LICENCE-02)
- Root `pyproject.toml` is the single SDK package (`axiom-sdk`) — no `mop-sdk/` subdirectory needed; update in-place
- Root package: `License-Expression = "Apache-2.0"` (CE only), bump `setuptools>=62.3`
- `puppeteer/pyproject.toml` currently has only tool config (black/ruff, no [project] section) — add a [project] section with `License-Expression` appropriate to puppeteer's CE licence (`Apache-2.0`)
- EE components live in `ee/` — their licence (`LicenseRef-Proprietary`) is addressed separately; do not add it to the CE pyproject.toml files

### NOTICE file (LICENCE-03)
- Create `NOTICE` at repo root
- Must include: caniuse-lite CC-BY-4.0 attribution (identified in node_licence_audit.md as the only attribution-required package)
- Include any other packages from the audit with attribution requirements
- Claude's discretion: exact format of NOTICE (Apache-style, plain text, or structured)

### Docs access decision (RELEASE-03)
- Decision: explicit deferral — /docs/ stays behind CF Access for now
- Rationale to document: the security guide contains mTLS/token architecture details; premature public exposure creates operational risk before a CE community is established
- Document in a new `DECISIONS.md` at repo root (lightweight ADR format: decision, rationale, CF Access policy reference, date, review trigger)
- This satisfies RELEASE-03 as a written decision with rationale — the decision is deferral, not avoidance

### Release workflow activation (RELEASE-01, RELEASE-02)
- `release.yml` is already fully scaffolded: PyPI Trusted Publisher (OIDC, no API token), testpypi gate before real PyPI, GHCR multi-arch build
- What's missing: `axiom-laboratories` GitHub org creation, `axiom-sdk` PyPI project creation, Trusted Publisher (pending publisher) configuration on PyPI, `testpypi` + `pypi` GitHub Environments created on the repo
- Phase 33 must document the setup steps + confirm the dry-run against test.pypi.org passes
- Claude's discretion: exact order of org creation → repo transfer → publisher setup steps

### Claude's Discretion
- Exact NOTICE file format (Apache-style vs plain text)
- DECISIONS.md ADR format details (MADR template vs lightweight freeform)
- Order of external service setup steps (org creation → repo transfer → PyPI publisher)
- Whether to add a `[project]` section stub to puppeteer/pyproject.toml or a minimal one with only name/version/licence

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `release.yml` (`.github/workflows/release.yml`): fully scaffolded for OIDC PyPI publish + GHCR multi-arch — requires no changes, only external service config
- `python_licence_audit.md` + `node_licence_audit.md` at repo root: evidence base for LEGAL-COMPLIANCE.md; already generated
- Root `pyproject.toml`: has `[project]` section with `license = {text = "Apache-2.0"}` (old format) — needs `License-Expression` field + `setuptools>=62.3`
- `puppeteer/pyproject.toml`: has `[tool.black]` and `[tool.ruff]` sections only — needs `[project]` + `[build-system]` addition

### Established Patterns
- `LEGAL.md` at root is the CE/EE policy doc — leave untouched; LEGAL-COMPLIANCE.md is a new sibling file
- `CHANGELOG.md`, `CONTRIBUTING.md`, `CODE_OF_CONDUCT.md` already at repo root — DECISIONS.md and NOTICE fit that pattern
- Phase 27 explicitly deferred PyPI Trusted Publisher setup pending org creation — Phase 33 is where this unblocks

### Integration Points
- paramiko removal: delete line from `puppeteer/requirements.txt` and `puppets/requirements.txt`; no code changes (no imports exist)
- PyPI Trusted Publisher setup is external (PyPI web UI + GitHub Environments) — not automated; must be documented as a manual checklist
- GHCR multi-arch: already wired in `release.yml`; requires `axiom-laboratories` org to own the repo for `ghcr.io/axiom-laboratories/axiom` image path to resolve

</code_context>

<specifics>
## Specific Ideas

- LEGAL-COMPLIANCE.md should be usable by an enterprise buyer's legal team — technical but readable, not a wall of legalese
- DECISIONS.md: the docs deferral decision needs a "review trigger" (e.g., "revisit when CE community onboarding begins") so it doesn't silently rot
- PyPI pending publisher must be configured BEFORE the first version tag — dry-run against test.pypi.org to catch OIDC name mismatches (from STATE.md research flags)

</specifics>

<deferred>
## Deferred Ideas

- None — discussion stayed within phase scope

</deferred>

---

*Phase: 33-licence-compliance-release-infrastructure*
*Context gathered: 2026-03-18*
