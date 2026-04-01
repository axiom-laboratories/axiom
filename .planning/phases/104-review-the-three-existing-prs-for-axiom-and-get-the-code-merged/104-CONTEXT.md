# Phase 104: Review the Three Existing PRs for Axiom and Get the Code Merged - Context

**Gathered:** 2026-04-01
**Status:** Ready for planning

<domain>
## Phase Boundary

Review, clean up, and merge three open PRs (#17 WebSocket fix, #18 Phase 103 Windows E2E, #19 Phase 102 Linux E2E) into `main`. Fix pre-existing test failures (History.test.tsx). Update STATE.md and ROADMAP.md to close milestone v18.0.

</domain>

<decisions>
## Implementation Decisions

### Merge order
- #17 (WebSocket fix) first — smallest blast radius, self-contained bug fix
- #19 (Phase 102: Linux E2E) second — current working branch
- #18 (Phase 103: Windows E2E) last — largest PR, most recent changes
- Rebase each PR after the prior merge lands

### PR #17 scope cleanup
- Strip .planning/ files from PR #17 before merging — cherry-pick only the useWebSocket.ts change onto a clean branch
- Planning files belong in #19 and #18, not the bug fix PR

### Conflict resolution
- Accept incoming for .planning/ files (STATE.md, ROADMAP.md, REQUIREMENTS.md) — the later branch has the most up-to-date snapshot
- Manually verify final STATE.md is coherent after all three merge

### Merge style
- Squash merge all three PRs — one commit per PR on main, clean history

### Review depth
- Full code review for code changes (main.py, deps.py, compose files, useWebSocket.ts, release.yml)
- Skim .planning/ and docs files — already reviewed during phase execution

### Test gate
- New code must pass; pre-existing failures (History.test.tsx) accepted as non-blocking for the PR merges
- After all PRs merge: fix History.test.tsx failures in a separate commit on main

### Blocker handling
- Issues found during review: fix in-branch before merge (push fix commits, re-review, then merge)
- Code changes in #19 (main.py, deps.py, compose.cold-start.yaml): Claude assesses risk and decides whether Docker stack verification is needed or code review suffices

### Post-merge cleanup
- Delete all three remote branches (fix/ws-memory-leak, worktree-phase-103, phase/102-linux-e2e-validation)
- Clean up local worktree directories and local tracking branches
- Update both STATE.md and ROADMAP.md — mark Phase 104 complete, reflect v18.0 milestone completion
- Final STATE.md update as a separate commit on main (not part of any PR)

### Milestone completion
- Merging all three PRs + test fix completes milestone v18.0
- After phase close: run /gsd:complete-milestone to archive and prepare for v19.0

### Claude's Discretion
- Exact cherry-pick / rebase commands for cleaning PR #17
- Whether to run Docker stack tests for specific code changes based on risk assessment
- Conflict resolution details within the "accept incoming" strategy
- Sequence of git operations for the rebase-after-merge workflow

</decisions>

<specifics>
## Specific Ideas

- PR #17 body describes the WebSocket bugs well — the fix is clean (onerror becomes no-op, pingRef tracked). Review should confirm the logic matches the description.
- PR #19 has actual code changes (deps.py, main.py, compose.cold-start.yaml) unlike the mostly-docs PRs — these deserve the closest review.
- PR #18 has a release.yml change (.github/workflows/) — verify it doesn't break CI.
- History.test.tsx has 4 pre-existing failures on main — fix these after all PRs merge as a separate commit.

</specifics>

<code_context>
## Existing Code Insights

### Reusable Assets
- `gh pr merge --squash` — GitHub CLI handles squash merge directly
- `git worktree list` / `git worktree remove` — for cleaning up Phase 103's worktree

### Established Patterns
- Prior merged PRs (#10, #11, #16) used standard merge commits from axiom-laboratories branches
- .planning/ files are updated on every phase — expect conflicts in STATE.md, ROADMAP.md, REQUIREMENTS.md between any two phase branches

### Integration Points
- CI: `.github/workflows/release.yml` modified in PR #18 — verify workflow syntax
- Docker stack: `compose.cold-start.yaml` modified in PR #19 — may need stack verification
- Backend: `deps.py` (new file) and `main.py` changes in PR #19 — code review required

</code_context>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 104-review-the-three-existing-prs-for-axiom-and-get-the-code-merged*
*Context gathered: 2026-04-01*
