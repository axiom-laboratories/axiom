# Phase 60: Quick Reference - Context

**Gathered:** 2026-03-24
**Status:** Ready for planning

<domain>
## Phase Boundary

Move two standalone HTML quick-reference files from the repo root to `quick-ref/`, rename them, rebrand the course file, update the operator guide for v12.0 additions, and do a full accuracy review of the course content. No new features — this is relocation, rebranding, and content currency.

</domain>

<decisions>
## Implementation Decisions

### File relocation and naming
- Both files move from repo root to `quick-ref/` directory
- **Filenames change**: `master_of_puppets_course.html` → `quick-ref/course.html`, `master_of_puppets_operator_guide.html` → `quick-ref/operator-guide.html`
- `quick-ref/index.md` is created as an intro page describing what each file is, with links to open them
- A new top-level **'Quick Reference'** section is added to `docs/mkdocs.yml` nav, containing the index page and links to both HTML files
- The old files at the repo root are deleted (moved, not copied)

### Rebranding scope
- Replace all `Master of Puppets` and `MoP` occurrences in `course.html` with `Axiom`
- Add an `Axiom` subtitle to the course hero section (e.g., title becomes "How Axiom Works" or similar)
- Update the HTML `<title>` tag in course.html to reflect "Axiom"
- Operator guide hero meta line (`Stack: FastAPI + React dashboard`) — leave as-is, already accurate

### Scheduling Health in operator guide
- Add a Scheduling Health sub-section inside **Module 4: Scheduling Jobs** (not a new module)
- Full walkthrough depth: explain each metric (LATE, MISSED, `last_fire`, `next_fire`), when to act on them, and how to access `GET /api/health/scheduling`
- Include retention config: explain the retention setting in Admin (how long execution records are kept) and why it matters when investigating LATE/MISSED jobs

### Course content update depth
- **Full accuracy review** — not just a terminology pass
- Verify all file paths and tool names referenced in the course (e.g., `node.py`, `runtime.py`, `admin_signer.py`) against the actual codebase; update any stale references
- Review interactive quiz/challenge content: verify questions and answers are still correct for the current architecture
- Update any examples or descriptions that describe old behaviour (e.g., outdated CLI commands, old task type names)

### Claude's Discretion
- Exact prose for the Scheduling Health walkthrough
- Exact wording for the course hero subtitle
- Structure and formatting of `quick-ref/index.md`
- How mkdocs.yml links to raw HTML files (MkDocs supports `!` prefix for non-markdown pages or direct nav paths)

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `docs/mkdocs.yml`: already has 'Quick Reference' sections implied by the nav structure from Phase 59; new top-level section follows the same pattern
- `docs/docs/stylesheets/extra.css`: Fira Sans + crimson branding applied in Phase 59 — the HTML files have their own self-contained styles, no need to share
- `docs/docs/assets/logo.svg`: available for potential embedding in `quick-ref/index.md` if desired

### Established Patterns
- Both HTML files are **fully self-contained** (inline CSS, inline base64 images, no external dependencies) — no asset path issues after move
- `docs/mkdocs.yml` nav uses indented YAML for sections — new 'Quick Reference' section follows same format
- Phase 59 proved that `mkdocs build --strict` is the verification gate — run it after nav changes

### Integration Points
- `docs/mkdocs.yml` nav: new 'Quick Reference' section added at the top level
- `quick-ref/index.md`: must be inside `docs/docs/` for MkDocs to serve it, but `course.html` and `operator-guide.html` can live at `docs/docs/quick-ref/` or at repo root `quick-ref/` depending on whether MkDocs serves them or they're just linked
- **Note for planner**: MkDocs can serve HTML files placed inside the `docs/` source directory directly. Place all three files under `docs/docs/quick-ref/` for MkDocs to serve them at `/quick-ref/`.

</code_context>

<specifics>
## Specific Ideas

- The course hero should clearly identify this as "Axiom" material — something like "How Axiom Works" as the main title (replacing any "Master of Puppets" hero text)
- `quick-ref/index.md` should describe both files in a sentence or two each so an operator landing there knows which to open
- Scheduling Health section should be honest about what LATE vs MISSED means operationally: LATE = fired but slow to pick up, MISSED = window passed with no fire

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 60-quick-reference*
*Context gathered: 2026-03-24*
