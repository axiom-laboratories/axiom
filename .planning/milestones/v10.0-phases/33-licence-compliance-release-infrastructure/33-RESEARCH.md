# Phase 33: Licence Compliance + Release Infrastructure - Research

**Researched:** 2026-03-18
**Domain:** Licence compliance documentation, PEP 639 metadata, PyPI Trusted Publisher (OIDC), GHCR multi-arch publishing
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**paramiko (LICENCE-04)**
- Remove paramiko from `puppeteer/requirements.txt`, `puppets/requirements.txt`, and `requirements.txt` — zero imports exist in application code
- Add a brief removal note in LEGAL-COMPLIANCE.md: paramiko was removed in v10.0 — not used in application code; LGPL-2.1 concern eliminated
- This satisfies LICENCE-04 via removal rather than linkage documentation

**LEGAL.md / compliance documentation (LICENCE-01, LICENCE-04)**
- Create a new `LEGAL-COMPLIANCE.md` at repo root — do NOT modify the existing `LEGAL.md` (that is the CE/EE policy/marketing doc)
- Audience: internal team and enterprise buyers — technical compliance language suitable for legal team review
- LEGAL-COMPLIANCE.md cites `python_licence_audit.md` and `node_licence_audit.md` as the evidence base; do not duplicate the 81-package table inline
- Must cover: certifi MPL-2.0 (read-only CA bundle, no source modification), paramiko removal note

**pyproject.toml / PEP 639 (LICENCE-02)**
- Root `pyproject.toml` is the single SDK package (`axiom-sdk`) — update in-place
- Root package: `license = "Apache-2.0"` (CE only), bump `setuptools>=77.0`
- `puppeteer/pyproject.toml` has only tool config sections — add `[project]` section with `license = "Apache-2.0"`
- EE components in `ee/` are handled separately; do not add `LicenseRef-Proprietary` to CE files

**NOTICE file (LICENCE-03)**
- Create `NOTICE` at repo root
- Must include: caniuse-lite CC-BY-4.0 attribution (only attribution-required package in the node audit)
- Include any other packages from the audit with attribution requirements
- Claude's discretion: exact format (Apache-style, plain text, or structured)

**Docs access decision (RELEASE-03)**
- Explicit deferral — `/docs/` stays behind CF Access
- Rationale: security guide contains mTLS/token architecture details; premature public exposure creates risk before CE community is established
- Document in a new `DECISIONS.md` at repo root (lightweight ADR format: decision, rationale, CF Access policy reference, date, review trigger)

**Release workflow activation (RELEASE-01, RELEASE-02)**
- `release.yml` is fully scaffolded — no code changes needed
- What's missing: `axiom-laboratories` GitHub org creation, `axiom-sdk` PyPI project, Trusted Publisher (pending publisher) on PyPI, `testpypi` + `pypi` GitHub Environments on repo
- Phase 33 documents the setup steps and confirms the dry-run against test.pypi.org passes

### Claude's Discretion
- Exact NOTICE file format (Apache-style vs plain text)
- DECISIONS.md ADR format details (MADR template vs lightweight freeform)
- Order of external service setup steps (org creation → repo transfer → PyPI publisher)
- Whether to add a `[project]` section stub or minimal one with name/version/licence to puppeteer/pyproject.toml

### Deferred Ideas (OUT OF SCOPE)
- None — discussion stayed within phase scope
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| LICENCE-01 | `LEGAL-COMPLIANCE.md` documents certifi MPL-2.0 usage decision — read-only CA bundle, no source modification | certifi usage confirmed as standard CA bundle import only; MPL-2.0 file-level copyleft not triggered by read-only use |
| LICENCE-02 | `pyproject.toml` files include PEP 639 `license` string field (`Apache-2.0`), `setuptools>=77.0` | PEP 639 string format is `license = "Apache-2.0"` in `[project]` table; setuptools >= 77.0 required for full support |
| LICENCE-03 | `NOTICE` file at repo root with caniuse-lite CC-BY-4.0 attribution and any other required attributions | Node audit identifies caniuse-lite CC-BY-4.0 as only attribution-required package; Python audit has no attribution-only packages |
| LICENCE-04 | paramiko LGPL-2.1 concern resolved — confirmed zero imports; remove from all three requirements.txt files | Grep confirms no `import paramiko` anywhere in application code; removal is clean |
| RELEASE-01 | `axiom-sdk` publishes to PyPI via GitHub Actions OIDC (Trusted Publisher) when version tag is pushed | Pending publisher flow documented; requires `axiom-laboratories` org + PyPI pending publisher + GitHub Environments |
| RELEASE-02 | Multi-arch GHCR images (`ghcr.io/axiom-laboratories/axiom`) publish automatically on version tag | `release.yml` docker-release job already wired; requires `axiom-laboratories` org to own the repo |
| RELEASE-03 | Documented decision on public `/docs/` access | Decision: explicit deferral with written rationale; captured in `DECISIONS.md` ADR |
</phase_requirements>

---

## Summary

Phase 33 is a documentation, configuration, and external service activation phase — no new application features. The work falls into three areas: (1) licence compliance files (`LEGAL-COMPLIANCE.md`, `NOTICE`, `DECISIONS.md`) and pyproject.toml PEP 639 updates, (2) paramiko removal from three requirements files, and (3) PyPI + GHCR release infrastructure wiring.

All the hard technical decisions were made in the context session. The release workflow (`release.yml`) is fully scaffolded — it uses `pypa/gh-action-pypi-publish@release/v1` with OIDC (`id-token: write`), testpypi gate before production PyPI, and `docker/build-push-action@v6` for multi-arch GHCR. What blocks the first version tag is entirely external configuration: the `axiom-laboratories` GitHub org does not yet exist, the `axiom-sdk` PyPI project has not been created, and no GitHub Environments (`testpypi`, `pypi`) have been configured on the repository.

The licence compliance work requires careful language for `LEGAL-COMPLIANCE.md` because the audience is enterprise buyers' legal teams. The core obligations are straightforward: certifi is used read-only (MPL-2.0 file-level copyleft is not triggered), paramiko has been removed (LGPL-2.1 concern eliminated), and caniuse-lite requires CC-BY-4.0 attribution in a NOTICE file.

**Primary recommendation:** Complete compliance files first (LEGAL-COMPLIANCE.md, NOTICE, DECISIONS.md, pyproject.toml), then execute the external service setup checklist in order (org → PyPI pending publisher → GitHub Environments → dry-run tag).

---

## Standard Stack

### Core
| Tool / Spec | Version / Ref | Purpose | Why Standard |
|-------------|---------------|---------|--------------|
| PEP 639 `license` string | setuptools >= 77.0 | SPDX expression in `pyproject.toml` [project] table | Adopted standard for Python packaging; replaces deprecated table format |
| `pypa/gh-action-pypi-publish` | `release/v1` | GitHub Actions PyPI publish via OIDC | Official PyPA action; already in release.yml |
| PyPI Trusted Publisher (pending publisher) | N/A | Create PyPI project + configure OIDC without an API token | Current best practice; eliminates long-lived secrets |
| `docker/build-push-action` | v6 | Multi-arch GHCR image build and push | Already in release.yml; standard Docker GitHub Action |
| SPDX identifier | `Apache-2.0` | CE licence expression | Canonical SPDX identifier for Apache 2.0 |

### Supporting
| Tool | Version | Purpose | When to Use |
|------|---------|---------|-------------|
| SPDX `LicenseRef-Proprietary` | — | Non-SPDX proprietary licence expression | EE components only — NOT added in this phase |
| Apache NOTICE format | — | Plain-text attribution file format | Standard for Apache-licensed projects distributing third-party CC/attribution-required content |

---

## Architecture Patterns

### Recommended File Structure (new files this phase)
```
repo root/
├── LEGAL-COMPLIANCE.md   # New: technical compliance doc for legal review
├── NOTICE                # New: third-party attribution (caniuse-lite CC-BY-4.0)
├── DECISIONS.md          # New: ADR for /docs/ access deferral
├── pyproject.toml        # Modified: license string format + setuptools>=77.0
└── puppeteer/
    └── pyproject.toml    # Modified: add [project] + [build-system] sections
```

### Pattern 1: PEP 639 License Field in pyproject.toml

**What:** Replace the deprecated TOML table format `license = {text = "Apache-2.0"}` with a plain string `license = "Apache-2.0"`.

**When to use:** Any `[project]` table in pyproject.toml that currently uses the old table syntax.

**Current state (root pyproject.toml — line 9):**
```toml
license = {text = "Apache-2.0"}
```

**Target state:**
```toml
[build-system]
requires = ["setuptools>=77.0"]
build-backend = "setuptools.build_meta"

[project]
name = "axiom-sdk"
version = "1.0.0-alpha"
license = "Apache-2.0"
```

**Note:** The field name in TOML is `license` (lowercase string value). The metadata field name published to PyPI is `License-Expression`. These are different names for the same thing — `license` in pyproject.toml maps to `License-Expression` in the wheel metadata when using setuptools >= 77.0.

### Pattern 2: puppeteer/pyproject.toml — Minimal [project] Addition

**What:** Add a `[project]` and `[build-system]` section to a pyproject.toml that currently has only `[tool.*]` sections.

**Target state:**
```toml
[build-system]
requires = ["setuptools>=77.0"]
build-backend = "setuptools.build_meta"

[project]
name = "axiom-orchestrator"
version = "10.0.0-alpha"
license = "Apache-2.0"

[tool.black]
# ... existing tool config unchanged
```

**Note:** This is a stub-minimal addition — name, version, licence. No dependencies listed (puppeteer is not a distributable package; the `[project]` section exists solely to carry the `License-Expression` metadata field for compliance purposes).

### Pattern 3: PyPI Trusted Publisher (Pending Publisher) Setup

**What:** Configure PyPI to accept OIDC tokens from GitHub Actions without a pre-existing PyPI project or API token.

**Sequence (ordered — each step depends on previous):**

1. Create `axiom-laboratories` GitHub organisation
2. Transfer or fork this repo under `axiom-laboratories` (or create new repo `axiom` there)
3. On PyPI (test.pypi.org first): Account → Publishing → "Add a new pending publisher"
   - PyPI project name: `axiom-sdk`
   - Owner: `axiom-laboratories`
   - Repository: `axiom` (the repo name under the org)
   - Workflow filename: `release.yml`
   - Environment name: `testpypi` (optional but strongly recommended)
4. In GitHub repo Settings → Environments: create `testpypi` environment
5. Create GitHub release with a `v*` tag to trigger the workflow
6. Confirm testpypi publish succeeds — pending publisher converts to normal publisher on first use
7. Repeat steps 3-4 for production PyPI with environment `pypi`

**Critical flag from STATE.md:** Configure and dry-run against test.pypi.org BEFORE pushing a real version tag to production PyPI. OIDC name mismatches (org name, repo name, workflow filename mismatch) cause silent failures that are hard to diagnose after the fact.

### Pattern 4: NOTICE File Format (Apache-style)

**What:** Plain-text file listing required third-party attributions.

**Recommended format (Apache-style, suitable for Apache-licensed project):**
```
Axiom Orchestrator
Copyright 2024-2026 Axiom Laboratories

This product includes software developed by third parties under the following licences:

-----------------------------------------------------------------------
caniuse-lite (CC-BY-4.0)
-----------------------------------------------------------------------
caniuse-lite is copyright (c) Alexis Deveria and contributors.
Licensed under the Creative Commons Attribution 4.0 International License.
https://creativecommons.org/licenses/by/4.0/
Source: https://github.com/browserslist/caniuse-lite
```

**Why Apache-style:** The project is Apache-2.0 licensed. Apache-style NOTICE files are the industry pattern for Apache-licensed projects that bundle third-party content requiring attribution. The format is plain text, legally unambiguous, and readable by automated compliance tools.

### Pattern 5: DECISIONS.md ADR Format

**What:** Lightweight Architecture Decision Record for the /docs/ access deferral.

**Recommended format (lightweight freeform, not full MADR):**
```markdown
# ADR-001: /docs/ Public Access Deferred

**Date:** 2026-03-18
**Status:** Accepted
**Decided by:** Thomas (Phase 33 context session)

## Decision
/docs/ remains behind Cloudflare Access policy. No public-facing path is activated for v10.0.

## Rationale
- The security guide documents mTLS/token architecture details that create operational risk if exposed before the CE community is established
- CF Access policy (`dev.master-of-puppets.work` → cert-manager) is already in place and functional
- Public docs access is a growth-stage concern; v10.0 is a commercial launch milestone

## Review Trigger
Revisit when CE community onboarding begins or when the first external contributor PR is received.

## CF Access Reference
Tunnel ID: 27bf990f-4380-41ea-9495-6a1cda5fe2d7
Policy: dev.master-of-puppets.work enforces CF Access service token
```

### Anti-Patterns to Avoid

- **Modifying LEGAL.md:** LEGAL.md is the CE/EE policy/marketing doc. Do not add compliance language there — create LEGAL-COMPLIANCE.md as a sibling.
- **Using `license = {text = "..."}` in new code:** This is the deprecated PEP 621 table format. Use the PEP 639 string format `license = "Apache-2.0"`.
- **Requiring setuptools >= 62.3:** The CONTEXT.md originally referenced 62.3 (partial PEP 639 support). Full support requires >= 77.0 — use 77.0.
- **Configuring production PyPI before testpypi:** Always dry-run against test.pypi.org first. OIDC configuration mismatches are caught at first publish; catching them on testpypi avoids a failed real release.
- **Forgetting the root requirements.txt:** paramiko appears in three files: `requirements.txt`, `puppeteer/requirements.txt`, and `puppets/requirements.txt`. All three must be edited.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| PyPI publishing auth | Long-lived API tokens or custom auth | PyPI Trusted Publisher (OIDC) | Already wired in release.yml; OIDC is the current security best practice |
| Multi-arch Docker builds | Platform-specific Dockerfiles | `docker/build-push-action@v6` with `platforms: linux/amd64,linux/arm64` | Already wired in release.yml |
| SPDX licence validation | Custom licence string parser | Standard SPDX identifiers (Apache-2.0, LicenseRef-Proprietary) | PyPI and tooling validate SPDX expressions natively |

---

## Common Pitfalls

### Pitfall 1: setuptools Version — 62.3 vs 77.0

**What goes wrong:** Using `setuptools>=62.3` (the partial implementation) instead of `>=77.0` (full PEP 639 support). With 62.3, the `license` string field may not be correctly mapped to the `License-Expression` wheel metadata field — it might fall back to the `License` legacy field.

**Why it happens:** Early PEP 639 drafts were partially implemented from setuptools 62.3. Full conformant support arrived in 77.0.

**How to avoid:** Use `requires = ["setuptools>=77.0"]` in `[build-system]`.

**Warning signs:** Running `python -m build` and inspecting the wheel metadata shows `License: Apache-2.0` (legacy field) rather than `License-Expression: Apache-2.0` (PEP 639 field).

### Pitfall 2: PyPI Pending Publisher — Name Mismatch

**What goes wrong:** The OIDC token from GitHub Actions does not match the pending publisher configuration on PyPI. The workflow fails with an authentication error that does not clearly identify the mismatch.

**Why it happens:** PyPI pending publishers match on a combination of: org/owner name, repo name, workflow filename, and (optionally) environment name. Any mismatch in any field causes rejection.

**How to avoid:** Verify the pending publisher form fields match release.yml exactly:
- Owner: `axiom-laboratories` (exact case)
- Repository: the exact repo name under the org
- Workflow: `release.yml` (filename only, not path)
- Environment: `testpypi` for testpypi, `pypi` for production

**Warning signs:** GitHub Actions job fails at `Publish to TestPyPI` step with 403 or token exchange error.

### Pitfall 3: Pending Publisher Converts on First Use

**What goes wrong:** The pending publisher on test.pypi.org is configured. Then when the real PyPI production publisher is configured, the team forgets to configure GitHub Environments (`pypi`), causing the production job to lack the required environment context.

**Why it happens:** The pending publisher recommends (but does not require) a GitHub Environment name. If the environment is omitted on testpypi but required on pypi, the workflow structure differs.

**How to avoid:** Configure both `testpypi` and `pypi` GitHub Environments before pushing any version tag. The release.yml workflow already references `environment: name: testpypi` and `environment: name: pypi`.

### Pitfall 4: GHCR Image Path Requires Org Ownership

**What goes wrong:** The `docker-release` job in release.yml pushes to `ghcr.io/axiom-laboratories/axiom`. If the repo is still owned by the personal account (not the org), the `GITHUB_TOKEN` will not have write permission to `ghcr.io/axiom-laboratories/`.

**Why it happens:** GHCR package visibility is scoped to the org/user that owns the repository. `GITHUB_TOKEN` inherits permissions from the repository's owner context.

**How to avoid:** Transfer or create the repo under `axiom-laboratories` org before pushing the first version tag. The `packages: write` permission is already in release.yml.

### Pitfall 5: Three requirements.txt Files for paramiko

**What goes wrong:** Only removing paramiko from `puppeteer/requirements.txt` and `puppets/requirements.txt`, forgetting the root `requirements.txt`.

**Why it happens:** The root `requirements.txt` appears to be a dev/meta file but also contains paramiko.

**How to avoid:** Edit all three files. Files confirmed to contain paramiko:
- `/requirements.txt` (line 15)
- `/puppeteer/requirements.txt` (line 15)
- `/puppets/requirements.txt` (line 15)

---

## Code Examples

### pyproject.toml Root — Before and After

**Before (current — deprecated table format):**
```toml
# Source: /pyproject.toml lines 1-4, 9
[build-system]
requires = ["setuptools>=61.0"]
build-backend = "setuptools.build_meta"

[project]
license = {text = "Apache-2.0"}
```

**After (PEP 639 compliant):**
```toml
[build-system]
requires = ["setuptools>=77.0"]
build-backend = "setuptools.build_meta"

[project]
license = "Apache-2.0"
```

### puppeteer/pyproject.toml — Sections to Add

```toml
# Add before existing [tool.*] sections
[build-system]
requires = ["setuptools>=77.0"]
build-backend = "setuptools.build_meta"

[project]
name = "axiom-orchestrator"
version = "10.0.0-alpha"
license = "Apache-2.0"
requires-python = ">=3.10"
```

### release.yml Environment Confirmation

The existing `release.yml` already references the correct environments:
```yaml
# publish-testpypi job (line 35-36)
environment:
  name: testpypi
  url: https://test.pypi.org/p/axiom-sdk

# publish-pypi job (line 55-56)
environment:
  name: pypi
  url: https://pypi.org/p/axiom-sdk
```

Both GitHub Environments must be created in repo Settings → Environments before the first version tag push.

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `license = {text = "Apache-2.0"}` (PEP 621 table) | `license = "Apache-2.0"` (PEP 639 string) | setuptools 77.0, deadline 2026-02-18 | Wheel metadata `License-Expression` field populated correctly |
| Long-lived PyPI API tokens | OIDC Trusted Publisher | ~2023, mainstream 2024-2025 | No secrets stored in GitHub; token is short-lived and scoped per workflow run |
| Single-arch Docker image push | Multi-arch `linux/amd64,linux/arm64` via QEMU + Buildx | Docker Buildx GA ~2022 | Runs natively on M-series Macs and ARM servers without emulation |

**Deprecated/outdated:**
- `license = {text = "..."}` (PEP 621 table format): deprecated as of setuptools 77.0, hard deadline 2026-02-18
- `license = {file = "LICENSE"}`: same deprecation timeline

---

## Open Questions

1. **Root `requirements.txt` purpose**
   - What we know: It contains the same packages as `puppeteer/requirements.txt` minus a few. Paramiko is on line 15.
   - What's unclear: Is this file used by any tooling or deployment step, or is it purely a dev convenience file?
   - Recommendation: Remove paramiko from all three files. If the root `requirements.txt` is redundant, that is a separate cleanup concern outside Phase 33 scope.

2. **puppeteer/pyproject.toml [project] name/version values**
   - What we know: The file has only `[tool.black]` and `[tool.ruff]` — no `[project]` section.
   - What's unclear: The planner must decide whether `name = "axiom-orchestrator"` and `version = "10.0.0-alpha"` are correct, or if different values are appropriate for a non-distributable package.
   - Recommendation: Use minimal stub values. The `[project]` section is added solely to carry the `License-Expression` field. The name/version do not need to be publishable.

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 9.x (Python); vitest 3.x (frontend) |
| Config file | `pyproject.toml` `[tool.pytest.ini_options]` |
| Quick run command | `cd puppeteer && pytest tests/ -x -q` |
| Full suite command | `cd puppeteer && pytest && cd dashboard && npx vitest run` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| LICENCE-01 | LEGAL-COMPLIANCE.md exists at repo root with correct sections | smoke/manual | `test -f LEGAL-COMPLIANCE.md` | ❌ Wave 0 (file created by phase) |
| LICENCE-02 | pyproject.toml contains `license = "Apache-2.0"` string (not table) and `setuptools>=77.0` | smoke | `grep -q 'license = "Apache-2.0"' pyproject.toml` | ❌ Wave 0 |
| LICENCE-03 | NOTICE file exists with caniuse-lite CC-BY-4.0 attribution | smoke/manual | `test -f NOTICE && grep -q "caniuse-lite" NOTICE` | ❌ Wave 0 (file created by phase) |
| LICENCE-04 | paramiko absent from all three requirements.txt files | smoke | `grep -r paramiko requirements.txt puppeteer/requirements.txt puppets/requirements.txt` returns no matches | ❌ Wave 0 |
| RELEASE-01 | testpypi dry-run passes (pending publisher configured, GitHub Environment exists) | manual-only | Manual: push `v10.0.0-alpha.1` tag to trigger release.yml, observe Actions run | N/A |
| RELEASE-02 | GHCR multi-arch image push succeeds on version tag | manual-only | Manual: confirm docker-release job completes; inspect `ghcr.io/axiom-laboratories/axiom` tags | N/A |
| RELEASE-03 | DECISIONS.md exists with /docs/ deferral ADR | smoke/manual | `test -f DECISIONS.md && grep -q "docs" DECISIONS.md` | ❌ Wave 0 (file created by phase) |

### Sampling Rate
- **Per task commit:** `grep -r "license = {" pyproject.toml puppeteer/pyproject.toml` (confirms no deprecated table format remains)
- **Per wave merge:** `cd puppeteer && pytest -x -q` (baseline — no regression from requirements.txt changes)
- **Phase gate:** All smoke checks pass + manual RELEASE-01/RELEASE-02 verification before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] No new test files required — all LICENCE-01..04 and RELEASE-03 checks are smoke-level file/grep assertions, not pytest test cases
- [ ] RELEASE-01 and RELEASE-02 are manual-only: they require external service configuration (GitHub org, PyPI) that cannot be automated in CI at this stage

*(No framework installation needed — existing pytest and vitest infrastructure covers any regression checks)*

---

## Sources

### Primary (HIGH confidence)
- PyPI Official Docs — `https://docs.pypi.org/trusted-publishers/creating-a-project-through-oidc/` — pending publisher creation steps and fields
- PyPI Official Docs — `https://docs.pypi.org/trusted-publishers/adding-a-publisher/` — GitHub Actions required fields (owner, repo, workflow filename, environment)
- PEP 639 — `https://peps.python.org/pep-0639/` — License-Expression field specification; `license = "string"` syntax
- Project audit files: `python_licence_audit.md`, `node_licence_audit.md` — evidence base for all compliance decisions
- `release.yml` — `.github/workflows/release.yml` — confirmed workflow structure, environment names, GHCR image path
- `pyproject.toml` — root — confirmed current `license = {text = "Apache-2.0"}` table format (deprecated)
- `puppeteer/pyproject.toml` — confirmed no `[project]` section exists

### Secondary (MEDIUM confidence)
- setuptools GitHub issue #4903 — confirms setuptools >= 77.0 required for full PEP 639 support; deprecation deadline 2026-02-18
- setuptools history — `https://setuptools.pypa.io/en/stable/history.html` — version timeline
- Creative Commons recommended attribution practices — `https://wiki.creativecommons.org/wiki/Recommended_practices_for_attribution` — CC-BY-4.0 NOTICE requirements
- Apache NOTICE format guidance — `https://infra.apache.org/licensing-howto.html` — assembling NOTICE and LICENSE files

### Tertiary (LOW confidence)
- None — all material claims verified against primary or secondary sources

---

## Metadata

**Confidence breakdown:**
- Compliance file content (LEGAL-COMPLIANCE.md, NOTICE, DECISIONS.md): HIGH — decisions locked in CONTEXT.md; content is documentation with clear specifications
- PEP 639 pyproject.toml syntax: HIGH — verified against PEP text and setuptools issue tracker
- PyPI Trusted Publisher setup: HIGH — verified against official PyPI docs
- setuptools version (77.0 vs 62.3): MEDIUM-HIGH — verified in setuptools issue tracker; original CONTEXT.md reference to 62.3 is outdated
- paramiko removal: HIGH — `grep` confirms zero imports; three files confirmed

**Research date:** 2026-03-18
**Valid until:** 2026-06-18 (stable specs — PEP 639 and PyPI Trusted Publisher are settled standards)

**Key correction vs CONTEXT.md:** CONTEXT.md referenced `setuptools>=62.3` (partial PEP 639 support). Research confirms full PEP 639 support requires `>=77.0`. Use `>=77.0` in both pyproject.toml files.
