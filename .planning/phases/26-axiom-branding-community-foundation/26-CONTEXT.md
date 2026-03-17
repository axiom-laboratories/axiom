# Phase 26: Axiom Branding & Community Foundation - Context

**Gathered:** 2026-03-17
**Status:** Ready for planning

<domain>
## Phase Boundary

Transform the project's public-facing identity from "Master of Puppets / MoP" to "Axiom" — new README, CONTRIBUTING.md with CLA, GitHub issue/PR templates, CHANGELOG.md, and a naming pass across all user-facing surfaces (repo-level files + MkDocs docs site). Internal code identifiers (class names, API routes, DB table names) are NOT renamed in this phase.

</domain>

<decisions>
## Implementation Decisions

### Naming conventions

- **Puppeteer** → **Axiom Orchestrator** (short form: "orchestrator" after first use)
- **Puppet** → **Axiom Node** (short form: "node" after first use)
- **MoP / Master of Puppets** → **Axiom** or **Axiom CE** depending on context
- **mop-push CLI** → **axiom-push**: full rename — update `pyproject.toml` scripts entry (`mop-push = ...` → `axiom-push = ...`) and all documentation references
- Internal code stays unchanged: class names, FastAPI route paths, DB table names, function names keep Puppeteer/Puppet naming — this is a user-facing rebranding only

### Naming migration scope

- **Repo-level files**: README.md, CONTRIBUTING.md, CHANGELOG.md, LEGAL.md, GitHub templates — all use Axiom naming
- **MkDocs docs site**: Full pass — grep for all variants of `MoP`, `Master of Puppets`, `Puppeteer`, `Puppet` (as component name) and update to Axiom equivalents in every file. This includes nav titles, headings, body text, and code annotations
- **Introduce on first use, short form after**: "Axiom Orchestrator (orchestrator)" on first mention, then "orchestrator". Same pattern for "Axiom Node (node)"

### README design

- **Primary job**: Gateway — short README that answers "what is this" and "how do I get started", then links to the MkDocs docs site for everything else. MkDocs is the single source of truth; README does not duplicate it.
- **Tone**: Open-source community — welcoming, technical, accessible. Assumes a developer/sysadmin who found the repo and wants to quickly assess relevance.
- **CE/EE section**: Explicit section explaining the Open Core model — what's free (CE, Apache 2.0: core orchestrator, nodes, job scheduling, mTLS, RBAC, Foundry, Smelter, CLI) vs what's enterprise (EE, proprietary: SSO, advanced RBAC, enterprise audit). Transparent positioning.
- **Badges**: Standard badge row — Apache 2.0 license badge, version badge (1.0.0-alpha), build status placeholder
- **Structure**: Badge row → What is Axiom → Key capabilities (bullet list) → CE vs EE → Quick start (3-4 commands to get running) → Link to full docs

### CLA model

- **Implicit clause**: No CLA bot, no sign-off requirement. CONTRIBUTING.md includes a paragraph: "By submitting a pull request, you certify that your contribution is your original work (or you have the right to submit it) and you agree to license it under the Apache License 2.0."
- **EE boundary**: Explicit section in CONTRIBUTING.md stating that the `/ee` directory contains proprietary Axiom Enterprise Edition code and that community contributions to `/ee` are not accepted. Contributions must stay outside `/ee`.
- **Content of CONTRIBUTING.md**:
  - CLA clause (above)
  - EE boundary statement
  - Code style: Black/Ruff for Python (config in pyproject.toml), ESLint for TypeScript
  - Testing requirements: all PRs must include tests; pytest for backend, vitest for frontend
  - PR workflow: branch naming convention, PR title format, review expectations
  - Issue reporting: how to file bugs/features (points to GitHub templates)

### GitHub templates

- **Issue templates**: Bug report + Feature request (two templates in `.github/ISSUE_TEMPLATE/`)
- **PR template**: Single PR template (`.github/pull_request_template.md`)
- Claude's Discretion: exact field structure of each template

### CHANGELOG format & start

- **Format**: Keep a Changelog (keepachangelog.com) — sections per version: Added / Changed / Deprecated / Removed / Fixed / Security
- **Starting point**: Retroactive milestone summaries — brief entries for v7.0 (Foundry + Smelter), v8.0 (mop-push + OAuth + Job Staging), v9.0 (MkDocs documentation site), then v1.0.0-alpha as the Axiom launch entry
- **v1.0.0-alpha entry**: Feature summary of what Axiom CE includes at launch — lists the core capabilities present in the initial public release (mTLS enrollment, Ed25519 job signing, container isolation, RBAC, Foundry, Smelter Registry, Package Mirroring, axiom-push CLI, OAuth device flow, Job Staging, MkDocs docs)

### Claude's Discretion

- Exact wording of issue/PR template fields and prompts
- Number and ordering of FAQ-style sections in CONTRIBUTING.md
- Exact badge URLs and shield styles (colour, shape)
- Whether to include a CODE_OF_CONDUCT.md (standard Contributor Covenant) alongside CONTRIBUTING.md
- Exact wording of retroactive milestone summaries in CHANGELOG

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets

- `README.md`: Exists but uses MoP branding — full rewrite needed
- `LEGAL.md`: Already uses Axiom branding and Open Core framing — can be referenced for CE/EE language
- `LICENSE`: Apache 2.0 in place ✓
- `pyproject.toml`: Already `axiom-sdk` / `1.0.0-alpha` — update scripts entry from `mop-push` to `axiom-push`
- `docs/mkdocs.yml`: Site title and nav will need Axiom naming pass
- `docs/docs/`: All .md files need MoP/Puppeteer/Puppet → Axiom naming pass

### Established Patterns

- No `.github/` directory exists — create from scratch
- MkDocs docs use admonition pattern (`!!! warning`, `!!! danger`) — maintain this if any CONTRIBUTING.md sections are cross-referenced from docs
- `<PLACEHOLDER>` pattern for sensitive values in code blocks

### Integration Points

- `pyproject.toml`: `[project.scripts]` entry rename (`mop-push` → `axiom-push`)
- `.github/`: Create directory with `ISSUE_TEMPLATE/bug_report.md`, `ISSUE_TEMPLATE/feature_request.md`, `pull_request_template.md`
- Root-level files: `README.md` (rewrite), `CONTRIBUTING.md` (new), `CHANGELOG.md` (new)
- `docs/` directory: naming pass across all markdown files

</code_context>

<specifics>
## Specific Ideas

- README should be short enough to read in 2 minutes — resist the urge to put architecture diagrams in it (those are in the docs site)
- The CE/EE section in README should be a simple table or two-column list, not prose
- CHANGELOG retroactive summaries should be brief (3-5 bullets per milestone) — not full changelogs, just enough to show the project's development arc for new contributors

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 26-axiom-branding-community-foundation*
*Context gathered: 2026-03-17*
