# Phase 26: Axiom Branding & Community Foundation - Research

**Researched:** 2026-03-17
**Domain:** Open-source community documentation, branding migration, GitHub community health files
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Naming conventions**
- Puppeteer → Axiom Orchestrator (short form: "orchestrator" after first use)
- Puppet → Axiom Node (short form: "node" after first use)
- MoP / Master of Puppets → Axiom or Axiom CE depending on context
- mop-push CLI → axiom-push: full rename — update `pyproject.toml` scripts entry (`mop-push = ...` → `axiom-push = ...`) and all documentation references
- Internal code stays unchanged: class names, FastAPI route paths, DB table names, function names keep Puppeteer/Puppet naming — this is a user-facing rebranding only

**Naming migration scope**
- Repo-level files: README.md, CONTRIBUTING.md, CHANGELOG.md, LEGAL.md, GitHub templates — all use Axiom naming
- MkDocs docs site: Full pass — grep for all variants of `MoP`, `Master of Puppets`, `Puppeteer`, `Puppet` (as component name) and update to Axiom equivalents in every file. This includes nav titles, headings, body text, and code annotations
- Introduce on first use, short form after: "Axiom Orchestrator (orchestrator)" on first mention, then "orchestrator". Same pattern for "Axiom Node (node)"

**README design**
- Primary job: Gateway — short README that answers "what is this" and "how do I get started", then links to the MkDocs docs site for everything else
- Tone: Open-source community — welcoming, technical, accessible
- CE/EE section: Explicit section explaining the Open Core model — what's free (CE, Apache 2.0: core orchestrator, nodes, job scheduling, mTLS, RBAC, Foundry, Smelter, CLI) vs what's enterprise (EE, proprietary: SSO, advanced RBAC, enterprise audit)
- Badges: Standard badge row — Apache 2.0 license badge, version badge (1.0.0-alpha), build status placeholder
- Structure: Badge row → What is Axiom → Key capabilities (bullet list) → CE vs EE → Quick start (3-4 commands to get running) → Link to full docs

**CLA model**
- Implicit clause: No CLA bot. CONTRIBUTING.md includes a paragraph certifying contributions are licensed under Apache 2.0
- EE boundary: Explicit section stating `/ee` directory is proprietary and community contributions to `/ee` are not accepted
- Content: CLA clause, EE boundary, code style (Black/Ruff/ESLint), testing requirements, PR workflow, issue reporting

**GitHub templates**
- Issue templates: Bug report + Feature request (two templates in `.github/ISSUE_TEMPLATE/`)
- PR template: Single PR template (`.github/pull_request_template.md`)
- Claude's Discretion: exact field structure of each template

**CHANGELOG format**
- Format: Keep a Changelog (keepachangelog.com) — Added / Changed / Deprecated / Removed / Fixed / Security
- Starting point: Retroactive milestone summaries — v7.0 (Foundry + Smelter), v8.0 (mop-push + OAuth + Job Staging), v9.0 (MkDocs docs), then v1.0.0-alpha as the Axiom launch entry
- v1.0.0-alpha entry: Feature summary of CE capabilities at launch

### Claude's Discretion
- Exact wording of issue/PR template fields and prompts
- Number and ordering of FAQ-style sections in CONTRIBUTING.md
- Exact badge URLs and shield styles (colour, shape)
- Whether to include a CODE_OF_CONDUCT.md (standard Contributor Covenant) alongside CONTRIBUTING.md
- Exact wording of retroactive milestone summaries in CHANGELOG

### Deferred Ideas (OUT OF SCOPE)
None — discussion stayed within phase scope.
</user_constraints>

---

## Summary

This phase is a documentation and configuration migration, not a code feature. The work falls into four buckets: (1) repo-level community health files created from scratch (CONTRIBUTING.md, CHANGELOG.md, GitHub templates), (2) README rewrite, (3) a mechanical naming pass across 24 MkDocs docs files plus mkdocs.yml, and (4) a single pyproject.toml scripts entry rename (`mop-push` → `axiom-push`).

All files are well-understood from direct inspection. The existing docs/developer/contributing.md (in the MkDocs site) is a detailed contributor technical guide — the new root-level CONTRIBUTING.md serves a different audience (community contributors, not internal developers) and should be shorter and gatekeeping-focused. The naming pass covers approximately 115 Puppeteer/Puppet occurrences, 35 mop-push occurrences, and 33 Master-of-Puppets/MoP occurrences across 24 docs files. The `mop-push.md` guide file must be renamed to `axiom-push.md` and the MkDocs nav entry updated to match.

The Keep a Changelog format is well-established and stable. GitHub community health file conventions are stable. No third-party services, APIs, or package installs are required for this phase.

**Primary recommendation:** Organise work into four sequential waves: (1) pyproject.toml rename + GitHub directory scaffold, (2) root-level files (README, CONTRIBUTING, CHANGELOG), (3) MkDocs docs naming pass + nav update, (4) docs/developer/contributing.md naming pass (this file already uses correct technical content but old branding).

---

## Standard Stack

### Core

| File/Tool | Version | Purpose | Why Standard |
|-----------|---------|---------|--------------|
| Keep a Changelog | keepachangelog.com | CHANGELOG format | Industry standard for human-readable changelogs; explicitly chosen by user |
| shields.io | current | Badge generation | De facto standard for GitHub README badges; no account/API key required |
| GitHub ISSUE_TEMPLATE | GitHub convention | Issue triage | GitHub natively renders YAML or Markdown templates from `.github/ISSUE_TEMPLATE/` |
| GitHub pull_request_template.md | GitHub convention | PR quality gate | GitHub renders this automatically on all new PRs |
| Contributor Covenant | v2.1 | CODE_OF_CONDUCT.md | Most common CoC for open-source projects; single-file drop-in |

### No Installs Required

All deliverables in this phase are Markdown files, YAML nav changes, and a single `pyproject.toml` edit. No new dependencies are needed.

---

## Architecture Patterns

### File Inventory — What Gets Created vs Modified

**Created from scratch:**
```
.github/
  ISSUE_TEMPLATE/
    bug_report.md         # GitHub issue template
    feature_request.md    # GitHub issue template
  pull_request_template.md
CONTRIBUTING.md           # Community contributor guide (NOT the docs site guide)
CHANGELOG.md              # Keep a Changelog format
CODE_OF_CONDUCT.md        # Optional — Contributor Covenant v2.1
```

**Modified in place:**
```
README.md                                          # Full rewrite
pyproject.toml                                     # scripts: mop-push → axiom-push
docs/mkdocs.yml                                    # site_name + nav entry rename
docs/docs/index.md                                 # naming pass
docs/docs/feature-guides/mop-push.md              # rename to axiom-push.md + content pass
docs/docs/feature-guides/foundry.md               # naming pass
docs/docs/feature-guides/job-scheduling.md        # naming pass
docs/docs/feature-guides/rbac.md                  # naming pass
docs/docs/feature-guides/rbac-reference.md        # naming pass
docs/docs/feature-guides/oauth.md                 # naming pass
docs/docs/getting-started/prerequisites.md        # naming pass
docs/docs/getting-started/install.md              # naming pass
docs/docs/getting-started/enroll-node.md          # naming pass
docs/docs/getting-started/first-job.md            # naming pass
docs/docs/security/index.md                       # naming pass
docs/docs/security/mtls.md                        # naming pass
docs/docs/security/rbac-hardening.md              # naming pass
docs/docs/security/audit-log.md                   # naming pass
docs/docs/security/air-gap.md                     # naming pass
docs/docs/runbooks/faq.md                         # naming pass
docs/docs/runbooks/foundry.md                     # naming pass
docs/docs/runbooks/jobs.md                        # naming pass
docs/docs/runbooks/nodes.md                       # naming pass (0 old terms found — verify)
docs/docs/developer/architecture.md              # naming pass (heaviest — 17 Puppeteer hits)
docs/docs/developer/setup-deployment.md          # naming pass
docs/docs/developer/contributing.md              # naming pass
docs/docs/api-reference/index.md                 # naming pass
```

### Pattern 1: README Structure

Locked structure from CONTEXT.md decisions:

```markdown
# Axiom

[badge row]

[1-2 sentence "what is this"]

## Key Capabilities
[bullet list]

## Community Edition vs Enterprise Edition
[two-column table or short lists]

## Quick Start
[3-4 commands]

## Documentation
[link to MkDocs site]
```

**Critical constraint:** README is a gateway, not a reference. Architecture diagrams and deep explanations stay in the MkDocs site.

### Pattern 2: CONTRIBUTING.md Structure

Root CONTRIBUTING.md serves external community contributors — it is distinct from the MkDocs docs site's `developer/contributing.md` (which serves internal developers). The root file should be shorter and community-facing:

```markdown
# Contributing to Axiom

[Welcome paragraph]

## Contributor License Agreement
[Implicit CLA paragraph — certify Apache 2.0]

## Enterprise Edition Boundary
[/ee is off-limits for community contributions]

## Code Style
[Black/Ruff for Python, ESLint for TypeScript — brief, links to docs]

## Testing
[pytest + vitest requirement — brief]

## Pull Request Workflow
[Branch naming, PR title format, review expectations]

## Reporting Issues
[Link to GitHub issue templates]
```

The MkDocs docs/developer/contributing.md already has the detailed technical content. CONTRIBUTING.md at root should cross-link to it for depth, not duplicate it.

### Pattern 3: Keep a Changelog Format

```markdown
# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [1.0.0-alpha] - 2026-03-17

### Added
- [capabilities list]

## [0.9.0] - 2026-03-16 (MkDocs Documentation)
### Added
- [3-5 bullets]

## [0.8.0] — ...
## [0.7.0] — ...
```

**Note on retroactive versions:** keepachangelog.com encourages retroactive entries. The user chose v7.0/v8.0/v9.0 as meaningful milestones for showing development arc; these are labelled as pre-release milestones to make the arc clear to new contributors.

### Pattern 4: GitHub Issue Templates

GitHub supports two formats for issue templates:
- **Markdown templates** (`.github/ISSUE_TEMPLATE/*.md`) — simple, rendered as a pre-filled text editor
- **YAML form templates** (`.github/ISSUE_TEMPLATE/*.yml`) — structured fields, required fields, dropdowns

For an early-stage project, **Markdown templates are preferable** — lower friction, no enforced structure that new contributors might find annoying. Use YAML forms only when triage volume warrants it.

**Bug report template skeleton:**
```markdown
---
name: Bug Report
about: Report a reproducible bug
labels: bug
---
**Describe the bug**
...
**Steps to reproduce**
...
**Expected behaviour / Actual behaviour**
...
**Environment**
...
**Logs / screenshots**
...
```

**Feature request template skeleton:**
```markdown
---
name: Feature Request
about: Suggest a new feature or improvement
labels: enhancement
---
**Problem this solves**
...
**Proposed solution**
...
**Alternatives considered**
...
```

### Pattern 5: PR Template

```markdown
## Summary
[What does this PR do?]

## Type of change
- [ ] Bug fix
- [ ] New feature
- [ ] Documentation update
- [ ] Refactor

## Checklist
- [ ] Tests pass (`cd puppeteer && pytest` and `npm run test`)
- [ ] Linting passes (`npm run lint`)
- [ ] New DB columns include a migration file
- [ ] No changes to `/ee` directory
```

The `/ee` boundary check is important to include here — it reinforces the CONTRIBUTING.md rule at the point of PR submission.

### Pattern 6: Naming Substitution Map

The planner can use this exact substitution table for all docs files:

| Find | Replace with | Context |
|------|-------------|---------|
| `Master of Puppets` | `Axiom` | Brand name |
| `\bMoP\b` | `Axiom` | Acronym |
| `Puppeteer` (as component) | `Axiom Orchestrator` (first use) / `orchestrator` (subsequent) | Component name |
| `Puppet Node` | `Axiom Node` (first use) / `node` (subsequent) | Component name |
| `Puppet node` | `Axiom Node` (first use) / `node` (subsequent) | Component name |
| `mop-push` | `axiom-push` | CLI name |
| `mop_push` | `axiom_push` | CLI name variants |
| `mop-push.md` | `axiom-push.md` | Filename |
| `feature-guides/mop-push` | `feature-guides/axiom-push` | Nav reference |

**Caution — do not replace:**
- Internal code terms: class names (`JobService`, `FoundryService`), route paths (`/api/enroll`, `/work/pull`), DB table names
- The word "puppet" when used as English noun (not as component name) — e.g., "puppet master" in non-technical prose

### Pattern 7: mkdocs.yml Changes

Two changes needed:
1. `site_name: Master of Puppets` → `site_name: Axiom`
2. Nav entry `- mop-push CLI: feature-guides/mop-push.md` → `- axiom-push CLI: feature-guides/axiom-push.md`

The file rename (`mop-push.md` → `axiom-push.md`) must happen in the same commit/wave as the nav update, or the Docker build will fail strict mode (broken nav reference).

### Pattern 8: shields.io Badge URLs

```markdown
[![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](LICENSE)
[![Version](https://img.shields.io/badge/version-1.0.0--alpha-orange.svg)](#)
[![Build Status](https://img.shields.io/badge/build-passing-brightgreen.svg)](#)
```

- License badge links to the `LICENSE` file in the repo
- Version badge is static (no PyPI lookup — package not published yet)
- Build status is a placeholder static badge until CI is wired in Phase 27

### Anti-Patterns to Avoid

- **Duplication between README and MkDocs:** README must not reproduce architecture diagrams, detailed setup steps, or feature guides — these live in the docs site. README links to the docs site.
- **Alembic references in CONTRIBUTING.md:** The root CONTRIBUTING.md must not say to use Alembic for DB changes — the project explicitly does not use it. The correct process is migration_vN.sql files.
- **CLA bot mention:** The decision is implicit CLA via PR submission, no bot. Do not reference CLA bot tooling.
- **Renaming internal code identifiers:** The naming pass must not touch class names (`Puppeteer`, `PuppetNode` if they exist), FastAPI route paths, or DB table names. This is enforced in scope.
- **Renaming mop_sdk package:** The Python package directory is `mop_sdk/` — this is an internal module name and is NOT renamed in this phase. Only the CLI entry point (`pyproject.toml [project.scripts]`) and documentation references change.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| CHANGELOG format | Custom versioning scheme | Keep a Changelog standard | Well-understood by contributors, tooling support |
| CoC | Custom code of conduct | Contributor Covenant v2.1 | Recognised, comprehensive, single-file drop-in |
| Issue template structure | Freeform markdown with no front matter | GitHub ISSUE_TEMPLATE front matter (`name`, `about`, `labels`) | GitHub uses front matter to display template picker correctly |
| Badge generation | Inline HTML images | shields.io static badges | Works in all GitHub markdown renderers, no CDN dependency |

---

## Common Pitfalls

### Pitfall 1: File Rename Without Nav Update (Breaks mkdocs --strict)

**What goes wrong:** `mop-push.md` renamed to `axiom-push.md` but `mkdocs.yml` nav still references `feature-guides/mop-push.md`. Docker build fails strict mode immediately.

**Why it happens:** The file rename and nav update are done in different tasks or waves without coordinating the change.

**How to avoid:** Rename the file and update the mkdocs.yml nav entry in the same task. Never let them diverge mid-wave.

**Warning signs:** Any Docker `mkdocs build --strict` failure with "page not found" or "nav references non-existent file".

### Pitfall 2: Replacing Internal Code Identifiers

**What goes wrong:** A grep-replace on "Puppeteer" hits class names or function names in code files included in documentation via code fences, or hits actual Python source files.

**Why it happens:** `grep -r "Puppeteer"` finds matches in both prose and code.

**How to avoid:** The naming pass is scoped to `docs/docs/` markdown prose and headings only. Any occurrence of "Puppeteer" inside a code block that reflects actual internal API behaviour should be annotated with a comment like `# Axiom Orchestrator internally` but the code identifier itself is left unchanged.

**Warning signs:** Any change to a `.py` file, any route path change, any DB table name change.

### Pitfall 3: README Scope Creep

**What goes wrong:** README grows to include detailed architecture explanation, environment variable tables, or troubleshooting — all content that already exists in the MkDocs site.

**Why it happens:** Writing a README naturally pulls in "helpful" context.

**How to avoid:** README must be readable in 2 minutes. Test: if a section would be at home in the MkDocs docs site, remove it from README and link instead.

### Pitfall 4: CONTRIBUTING.md Duplicates MkDocs developer/contributing.md

**What goes wrong:** Root CONTRIBUTING.md becomes a copy of the MkDocs contributing guide — 260+ lines of DB migration conventions, code structure guidelines, etc.

**Why it happens:** The MkDocs file is detailed and it's tempting to reuse.

**How to avoid:** Root CONTRIBUTING.md covers community contributor concerns (CLA, EE boundary, minimal workflow). Link to `developer/contributing.md` in the docs site for the detailed technical guide.

### Pitfall 5: CHANGELOG Retroactive Versioning Confusion

**What goes wrong:** Retroactive v7.0/v8.0/v9.0 entries don't match any git tags, causing confusion.

**Why it happens:** The project has no formal git tags yet.

**How to avoid:** Add a brief comment or note in the CHANGELOG header acknowledging that v7.0–v9.0 are historical milestone summaries predating the Axiom rename, and that semantic versioning from `[1.0.0-alpha]` forward is the canonical release line.

### Pitfall 6: Missing mop_sdk Package Rename

**What goes wrong:** `pyproject.toml` scripts entry is renamed to `axiom-push = "mop_sdk.cli:main"` but confusion arises about whether the package directory itself should also change.

**Why it happens:** "axiom-push" entry point and "mop_sdk" module name sound inconsistent.

**How to avoid:** This is explicitly in scope per CONTEXT.md — only the scripts entry changes in this phase. The `mop_sdk` package directory rename is NOT in scope for Phase 26. The entry `axiom-push = "mop_sdk.cli:main"` is correct — the entry point label is user-facing, the module path is internal.

---

## Code Examples

### pyproject.toml Scripts Entry Change

```toml
# Source: CONTEXT.md locked decision
# Before:
[project.scripts]
mop-push = "mop_sdk.cli:main"

# After:
[project.scripts]
axiom-push = "mop_sdk.cli:main"
```

Note: only one line changes. The package include (`include = ["mop_sdk*"]`) is NOT changed.

### mkdocs.yml Changes

```yaml
# Source: CONTEXT.md locked decision + direct file inspection
# site_name line 1:
site_name: Axiom

# nav entry (line 32):
      - axiom-push CLI: feature-guides/axiom-push.md
```

### shields.io Badge Row for README

```markdown
[![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](LICENSE)
[![Version](https://img.shields.io/badge/version-1.0.0--alpha-orange.svg)](#)
[![Build Status](https://img.shields.io/badge/build-passing-brightgreen.svg)](#)
```

### GitHub Template Front Matter Pattern

```markdown
---
name: Bug Report
about: Report a reproducible bug in Axiom
title: "[Bug]: "
labels: bug
assignees: ''
---
```

---

## Naming Pass: Term Count by File

From direct file inspection (confidence HIGH — grep verified):

| File | Puppeteer | Puppet/Node | mop-push | MoP/MoP |
|------|-----------|-------------|----------|---------|
| `developer/architecture.md` | 17 | ~12 | 0 | 4 |
| `feature-guides/mop-push.md` | 0 | 0 | 14 | 2 |
| `index.md` | 1 | 1 | 1 | 3 |
| `developer/contributing.md` | 1 | 2 | 0 | 3 |
| `developer/setup-deployment.md` | varies | varies | 0 | varies |
| All other files | low | low | varies | low |

**Total estimate:** ~115 Puppeteer/Puppet lines + 35 mop-push lines + 33 MoP/Master-of-Puppets lines across 24 files. `architecture.md` is the highest-density file and will take the most care to preserve code-block accuracy.

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest (backend), vitest (frontend) |
| Config file | `puppeteer/pyproject.toml` (pytest), `puppeteer/dashboard/vitest.config.*` |
| Quick run command | `cd puppeteer && pytest -x -q` |
| Full suite command | `cd puppeteer && pytest && cd dashboard && npm run test -- --run` |

### Phase Requirements → Test Map

This phase has no formal requirement IDs. The deliverables are all documentation and configuration files. Testing is verification-style (grep/inspect), not automated unit tests.

| Deliverable | Test Type | Verification Command |
|-------------|-----------|---------------------|
| `pyproject.toml` scripts entry | smoke | `pip install -e . && axiom-push --help` |
| `mop-push.md` renamed + nav updated | structural | `docker compose -f puppeteer/compose.server.yaml build docs` (mkdocs --strict) |
| No `mop-push` references remain in docs | structural | `grep -r "mop-push" docs/docs/` returns 0 results |
| No `Master of Puppets` in README | structural | `grep "Master of Puppets" README.md` returns 0 results |
| GitHub templates render | manual | Create draft PR/issue in GitHub UI |
| CHANGELOG parses | structural | `grep "^## \[" CHANGELOG.md` — each version entry present |

### Sampling Rate

- **Per task commit:** Grep verification for the specific term(s) that task addressed
- **Per wave merge:** `grep -r "mop-push\|Master of Puppets\|\bMoP\b\|Puppeteer" docs/docs/ --include="*.md"` confirms zero remaining hits for terms that wave addressed
- **Phase gate:** Docker docs build passing `mkdocs build --strict` before `/gsd:verify-work`

### Wave 0 Gaps

None — no test infrastructure changes are needed. This phase creates only markdown, YAML, and a single TOML line change. Existing test suites (pytest + vitest) are not affected.

---

## State of the Art

| Old Approach | Current Approach | Impact |
|--------------|------------------|--------|
| Markdown issue templates (`.github/ISSUE_TEMPLATE/*.md`) | YAML form templates also supported | Markdown templates remain appropriate for early-stage projects — lower friction |
| CLA bot (cla-assistant.io) | Implicit CLA in CONTRIBUTING.md | Simpler, no third-party service; explicitly chosen |
| `CHANGELOG.md` written by hand | Tools like `git-cliff` can auto-generate | Hand-written is correct here; CONTEXT.md chose Keep a Changelog explicitly |

**Deprecated/outdated:**
- MIT license badge in current README.md: README currently says MIT but the project is Apache 2.0. The new README badge must say Apache 2.0.

---

## Open Questions

1. **CODE_OF_CONDUCT.md inclusion**
   - What we know: User deferred this to Claude's Discretion
   - What's unclear: Whether to include it now or defer to Phase 27
   - Recommendation: Include it. Contributor Covenant v2.1 is a single-file drop-in (~50 lines). It's expected by the GitHub community health checker and signals seriousness to potential contributors. No downside to including it now.

2. **docs site URL in README**
   - What we know: The MkDocs site is at `https://dev.master-of-puppets.work/docs/` and is behind Cloudflare Access
   - What's unclear: Whether to link to it in README or note "available after deployment"
   - Recommendation: Link to it with a note in the Quick Start section that the docs site requires the stack to be running. For GitHub visitors who don't have a running instance, the README itself should contain enough to assess relevance.

3. **docs/docs/developer/contributing.md Axiom naming**
   - What we know: This file uses MoP/Puppeteer branding heavily (confirmed by grep)
   - What's unclear: Whether updating it is part of the docs naming pass wave or a separate task
   - Recommendation: Include it in the docs naming pass wave. It's already in the `docs/docs/` directory and is part of the full pass scope in CONTEXT.md.

---

## Sources

### Primary (HIGH confidence)
- Direct file inspection — `README.md`, `LEGAL.md`, `pyproject.toml`, `docs/mkdocs.yml`, `docs/docs/index.md`, `docs/docs/developer/contributing.md`, `docs/docs/developer/architecture.md`, `26-CONTEXT.md`
- grep verification — term counts per file from live filesystem
- `AXIOM_RELEASE_PLAN.md` — project transition context

### Secondary (MEDIUM confidence)
- keepachangelog.com format — well-known, stable standard (v1.1.0)
- GitHub `.github/ISSUE_TEMPLATE/` convention — documented GitHub feature, stable for 5+ years
- shields.io static badge pattern — stable, no API key required

### Tertiary (LOW confidence)
- None

---

## Metadata

**Confidence breakdown:**
- Deliverable inventory: HIGH — all files inspected directly, term counts verified by grep
- Naming substitution map: HIGH — derived from CONTEXT.md locked decisions + direct file review
- GitHub template conventions: HIGH — stable platform feature
- Keep a Changelog format: HIGH — stable, widely adopted

**Research date:** 2026-03-17
**Valid until:** 2026-06-17 (stable domain — 90-day validity)
