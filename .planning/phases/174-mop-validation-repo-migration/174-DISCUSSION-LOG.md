# Phase 174: mop_validation Repo Migration — Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-21
**Phase:** 174-mop-validation-repo-migration
**Areas discussed:** Axiom org status, Verification scope, Doc update scope

---

## Axiom Org Status

| Option | Description | Selected |
|--------|-------------|----------|
| Doesn't exist yet | Need to create github.com/axiom before transfer | |
| Exists, I'm an admin | Org is up, user has admin rights | ✓ |
| Different org name | Target org has a different name | ✓ |

**User's choice:** Org exists and user is admin, but the org name is `axiom-laboratories` (not `axiom` as written in ROADMAP.md).

**Notes:** Target URL is `github.com/axiom-laboratories/mop_validation`. The ROADMAP.md naming error (`axiom` vs `axiom-laboratories`) should be corrected in 174-02.

---

## Verification Scope

| Option | Description | Selected |
|--------|-------------|----------|
| Git ops only | git fetch + git push to new remote succeed | ✓ |
| Git ops + smoke test | Remote verification plus one lightweight script run | |
| Full Phase 173 suite | Run pytest tests/test_173_*.py | |

**User's choice:** Git operations only (fetch + push to new remote).

**Notes:** Scripts use local `~/Development/mop_validation/` paths so the GitHub remote URL change doesn't affect script execution directly.

---

## Doc Update Scope

| Option | Description | Selected |
|--------|-------------|----------|
| Add GitHub URL only | Add new URL to Sister Repos sections; keep local path | ✓ |
| Replace local path + add URL | Update ~/Development paths if clone moves | |
| GitHub URL + memory file | Also update project_axiom_ee.md memory | |

**User's choice:** Add GitHub URL to Sister Repositories sections in CLAUDE.md and GEMINI.md. Local path reference unchanged — clone stays at `~/Development/mop_validation`.

---

## Claude's Discretion

- Whether to update project_axiom_ee.md memory file with org name correction
- Whether to update MEMORY.md axiom-ee entry with org name

## Deferred Ideas

None.
