# Phase 174: mop_validation Repo Migration — Context

**Gathered:** 2026-04-21
**Status:** Ready for planning

<domain>
## Phase Boundary

Transfer the `mop_validation` repository from the personal GitHub account
(`github.com/Bambibanners/mop_validation`) to the `axiom-laboratories` GitHub organisation
as a private repo (`github.com/axiom-laboratories/mop_validation`). Update the local git
remote and add the new GitHub URL to the Sister Repositories sections of `CLAUDE.md` and
`GEMINI.md`.

**Not in scope:** any changes to scripts, test files, or secrets inside `mop_validation`;
any axiom-ee or master_of_puppets repo migrations; licence architecture analysis (Phase 175).

</domain>

<decisions>
## Implementation Decisions

### Target Organisation

- **D-01:** The target GitHub org is `axiom-laboratories`, NOT `axiom`.
  Full destination: `github.com/axiom-laboratories/mop_validation` (private).
  The ROADMAP.md uses `axiom` — this is a naming error; all plans must use
  `axiom-laboratories` throughout.
- **D-02:** The org already exists and the user has admin rights.
  174-01 goes directly to initiating the repo transfer — no org creation step needed.

### Verification (MIG-02)

- **D-03:** "Scripts work post-migration" is satisfied by **git operations only**:
  - `git fetch origin` succeeds from the new remote URL
  - `git push origin` succeeds (or at minimum `git remote -v` confirms the updated URL)
  No script-level smoke tests required — scripts reference `~/Development/mop_validation/`
  local paths which are unaffected by the GitHub remote change.

### Documentation Updates (MIG-04)

- **D-04:** Add the new GitHub URL to the **Sister Repositories** section of both
  `CLAUDE.md` and `GEMINI.md` in `master_of_puppets`. The existing local path reference
  (`~/Development/mop_validation`) stays as-is — the clone location does not move.
- **D-05:** The ROADMAP.md `axiom` → `axiom-laboratories` naming correction should be
  fixed in 174-02 alongside the other reference updates.

### Claude's Discretion

- Whether to update `project_axiom_ee.md` memory file to note the org name correction —
  Claude decides (low priority, not a MIG requirement).
- Whether to update the memory MEMORY.md entry for the axiom-ee sister repo org name
  while touching documentation — Claude decides.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Requirements
- `.planning/REQUIREMENTS.md` §MIG — MIG-01, MIG-02, MIG-03, MIG-04 definitions

### Files to Update
- `CLAUDE.md` (repo root) — Sister Repositories section: add GitHub URL for mop_validation
- `GEMINI.md` (repo root) — Sister Repositories section: add GitHub URL for mop_validation
- `.planning/ROADMAP.md` — Phase 174 goal text: `axiom` → `axiom-laboratories`

### mop_validation Repo State
- Current remote: `https://github.com/Bambibanners/mop_validation.git`
  (confirmed via `git remote -v` in `~/Development/mop_validation`)
- No `.github/` directory — no CI workflows to update
- No hardcoded GitHub URLs in scripts — all scripts use local `~/Development/mop_validation/` paths

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- None — this is an operational (non-code) phase

### Established Patterns
- GitHub repo transfer initiated via: GitHub Settings → Danger Zone → Transfer Ownership
  (manual UI step; cannot be scripted without org-level API token)
- Local remote update: `git remote set-url origin https://github.com/axiom-laboratories/mop_validation.git`

### Integration Points
- `CLAUDE.md` Sister Repositories section (search: `### \`~/Development/mop_validation\``)
- `GEMINI.md` Sister Repositories section (search: `~/Development/mop_validation`)

</code_context>

<specifics>
## Specific Ideas

- Destination URL: `https://github.com/axiom-laboratories/mop_validation` (private)
- Local clone location (`~/Development/mop_validation`) does not change post-transfer
- The GitHub transfer is a manual step (UI or gh CLI) — the plan should provide the
  exact gh CLI command or UI steps so the user can execute it directly

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 174-mop-validation-repo-migration*
*Context gathered: 2026-04-21*
