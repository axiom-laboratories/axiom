---
phase: 93-documentation-prs
plan: "02"
subsystem: docs
tags: [mkdocs, runbook, upgrade, migration, docs-validate]

# Dependency graph
requires:
  - phase: 93-01
    provides: PR #11 merged, .planning/ and CI changes on main
provides:
  - docs/docs/runbooks/upgrade.md on main — authoritative operator upgrade guide
  - tools/validate_docs.py ENV_SKIP patched to suppress SYSTEM_STARTUP false positive
  - PR #12 closed
affects: [93-03, release-notes, operator-docs]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Cherry-pick docs-only from a branch to avoid re-merging already-present .planning/ and CI changes"

key-files:
  created:
    - docs/docs/runbooks/upgrade.md
    - .planning/todos/done/2026-03-29-write-upgrade-runbook-covering-migration-sql-workflow-end-to-end.md
  modified:
    - docs/mkdocs.yml
    - docs/docs/runbooks/index.md
    - tools/validate_docs.py

key-decisions:
  - "Cherry-pick only docs files from PR #12 branch — .planning/ and CI files already on main from PR #11"
  - "Migration SQL reference table count verified as 36 (matching disk) — migration.sql row already present, no fix needed"
  - "SYSTEM_STARTUP added to validate_docs ENV_SKIP — it is an audit event type label in docs, not an env var"

patterns-established:
  - "validate_docs ENV_SKIP: add uppercase constants that are not env vars (audit events, status codes) to avoid false WARN"

requirements-completed:
  - DOC-02

# Metrics
duration: 25min
completed: 2026-03-30
---

# Phase 93 Plan 02: Merge PR #12 — Upgrade Runbook Summary

**Upgrade runbook (36-migration-file reference table, pre-flight checklist, rollback procedure) merged to main via cherry-pick PR #15; docs-validate SYSTEM_STARTUP false positive patched in tools/validate_docs.py**

## Performance

- **Duration:** ~25 min
- **Started:** 2026-03-30T16:25:00Z
- **Completed:** 2026-03-30T17:35:00Z
- **Tasks:** 4
- **Files modified:** 5

## Accomplishments

- Verified upgrade runbook content accuracy: all 8 checklist items pass (philosophy, pre-flight, procedure, migration reference, docker exec syntax, post-verification, rollback, nav entry)
- Migration SQL count confirmed: 36 rows in runbook table matches 36 files on disk; `migration.sql` row already present — no fix required
- Cherry-picked docs-only commit onto `fix/93-merge-upgrade-runbook`, created PR #15, merged to main
- Patched `tools/validate_docs.py` to add `SYSTEM_STARTUP` to `ENV_SKIP` — audit event type label in runbook was triggering a false WARN on docs-validate CI
- Closed original PR #12 with comment explaining incorporation path

## Task Commits

1. **Task 1-2: Verify migration count + content accuracy review** — no changes needed (count correct, content complete)
2. **Task 3: Cherry-pick docs file onto main** — `9d297d5` (docs: add upgrade runbook covering migration SQL workflow)
3. **Task 3 fix: docs-validate WARN** — `0e09a22` / `023c5a6` (fix: add SYSTEM_STARTUP to validate_docs ENV_SKIP)
4. **Task 4: Push, merge PR #15, close PR #12** — PR #15 merged, PR #12 closed

## Files Created/Modified

- `docs/docs/runbooks/upgrade.md` — authoritative operator upgrade guide (upgrade philosophy, pre-flight, 5-step procedure, 36-file migration index, post-verification, rollback)
- `docs/mkdocs.yml` — added `Upgrade Guide: runbooks/upgrade.md` nav entry
- `docs/docs/runbooks/index.md` — added upgrade guide cross-reference row
- `tools/validate_docs.py` — `SYSTEM_STARTUP` added to `ENV_SKIP` set
- `.planning/todos/done/2026-03-29-write-upgrade-runbook-covering-migration-sql-workflow-end-to-end.md` — todo closed

## Decisions Made

- Cherry-picked only the docs commit from PR #12 branch — `.planning/` and CI changes were already on main from PR #11; including them would have created conflicts
- Migration count was correct (36 rows, 36 files) — plan anticipated a possible off-by-one but it was not needed
- `SYSTEM_STARTUP` audit event added to `ENV_SKIP` rather than removing it from the runbook — it is a valid operator-facing label instructing what to look for in the audit log; the validator was incorrectly treating it as an env var

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] docs-validate WARN for SYSTEM_STARTUP in upgrade runbook**
- **Found during:** Task 3 (cherry-pick commit pushed, CI ran)
- **Issue:** `tools/validate_docs.py` ENV_RE pattern matched `` `SYSTEM_STARTUP` `` as a potential env var; it's not in source so emitted a WARN, causing CI exit code 1
- **Fix:** Added `"SYSTEM_STARTUP"` to `ENV_SKIP` set with comment noting it is an audit event type constant
- **Files modified:** `tools/validate_docs.py`
- **Verification:** `python tools/validate_docs.py` returns `Summary: 253 PASS, 0 WARN, 0 FAIL`
- **Committed in:** `023c5a6` (pushed directly to main after PR #15 merged)

---

**Total deviations:** 1 auto-fixed (Rule 1 — bug in docs-validate false positive)
**Impact on plan:** Necessary correctness fix. No scope creep. The upgrade runbook content itself required no changes.

## Issues Encountered

- PR #15 was merged by GitHub automation before the validate_docs fix commit was added to the branch — the fix had to be applied as a separate cherry-pick directly to main after the fact. This is a timing issue with the merge queue, not a code problem.

## Next Phase Readiness

- DOC-02 satisfied: `docs/docs/runbooks/upgrade.md` present on main
- PR #12 closed
- Ready for Plan 93-03: review and merge PR #13 (Windows local dev docs)

---
*Phase: 93-documentation-prs*
*Completed: 2026-03-30*
