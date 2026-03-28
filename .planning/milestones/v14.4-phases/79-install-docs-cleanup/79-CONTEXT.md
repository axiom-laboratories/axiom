# Phase 79: Install Docs Cleanup - Context

**Gathered:** 2026-03-27
**Status:** Ready for planning

<domain>
## Phase Boundary

Remove `puppet-node-1` and `puppet-node-2` from `compose.cold-start.yaml` and update `install.md` atomically to eliminate all references to bundled JOIN tokens. No backend code changes. Pure YAML deletion + doc prose update.

</domain>

<decisions>
## Implementation Decisions

### install.md — tab label rename
- All "Cold-Start Install" tab labels throughout `install.md` renamed to **"Quick Start"**
- Applies to every tabbed section: Step 2 (Configure env vars), Step 3 (Start the stack), Step 4 (Verify)

### install.md — Step 3 Quick Start prose
- Current line 97: "This starts: Caddy (reverse proxy + TLS, port 8443), the Agent Service (port 8001), and PostgreSQL. The two built-in puppet nodes start automatically but require JOIN_TOKEN_1 and JOIN_TOKEN_2 to be set in your `.env` before they can enroll."
- Replace with: "This starts: Caddy (reverse proxy + TLS, port 8443), the Agent Service (port 8001), and PostgreSQL." — truncate cleanly, no forward pointer (users follow the "Next: Enroll a Node →" link already at the bottom)
- Mirror the parallel structure of the Server Install tab description

### compose.cold-start.yaml — services removed
- Delete `puppet-node-1` service block entirely
- Delete `puppet-node-2` service block entirely

### compose.cold-start.yaml — volumes cleaned up
- Remove `node1-secrets` from the volumes block
- Remove `node2-secrets` from the volumes block
- Tidy the `secrets-data` inline comment if it references nodes (currently says "# Agent secrets persistence (boot.log, licence.key) across restarts" — review and keep/update as appropriate)

### compose.cold-start.yaml — header comment
- Remove steps 3–4 from the "Quick start:" numbered comment (the steps that say "Generate JOIN tokens..." and "Set JOIN_TOKEN_1 and JOIN_TOKEN_2 in your .env file...")
- Also clean up the Usage block below: remove any JOIN_TOKEN env var references from the example `docker compose up` commands
- After cleanup, the header comment's Quick start section should have only 2 steps: (1) create .env, (2) docker compose up

### Claude's Discretion
- Exact wording of any updated inline comments in the YAML volumes section
- Whether to re-number the header "Quick start:" steps after removing steps 3–4 (they become 2 steps, no numbering needed or simple 1–2)

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- No code assets — pure doc/YAML changes

### Established Patterns
- `install.md` uses MkDocs Material tabbed sections (`=== "Tab Name"`) — same syntax for all tab renames
- Tab labels are string literals in `=== "..."` markers — global find-and-replace of "Cold-Start Install" → "Quick Start" covers all instances

### Integration Points
- `compose.cold-start.yaml` is referenced by name in `install.md` — the filename itself does not change
- `enroll-node.md` already handles the full JOIN token workflow — no changes needed there
- "Next: Enroll a Node →" link at the bottom of `install.md` remains as the natural next step

</code_context>

<specifics>
## Specific Ideas

- No specific styling or reference requirements — standard cleanup

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 79-install-docs-cleanup*
*Context gathered: 2026-03-27*
