# Phase 62: Agent Scaffolding - Context

**Gathered:** 2026-03-25
**Status:** Ready for planning

<domain>
## Phase Boundary

Create and verify all scaffolding required before any Gemini tester scenario runs: a constrained tester GEMINI.md, a verified checkpoint round-trip protocol, HOME isolation setup, and 4 scenario prompt scripts (CE install, CE operator, EE install, EE operator). Does not run any actual scenario — proves the apparatus works first.

</domain>

<decisions>
## Implementation Decisions

### Tester GEMINI.md persona and content
- Gemini plays a **first-time user** who has never seen Axiom — follows docs literally, no shortcuts, no prior knowledge
- Tester GEMINI.md lives at `/workspace/gemini-context/GEMINI.md` inside the LXC
- Docs are delivered as a **static copy of `docs/site/`** pushed into `/workspace/docs/` at Phase 62 setup time — no web server needed, Gemini reads via `file:///workspace/docs/...`
- GEMINI.md references the local docs path only — no codebase mentions, no CLAUDE.md, no repo structure
- Gemini is restricted to docs folder only — no external web search, no Stack Overflow, no GitHub lookups
- If blocked for >2 attempts, Gemini writes `checkpoint/PROMPT.md` and halts to wait for Claude response

### Checkpoint trigger policy
- Gemini checkpoints **only when blocked**: docs don't explain the next step, an error isn't explained, or a required value is missing
- No proactive stage-gate checkpoints — Claude only intervenes when needed
- `checkpoint/PROMPT.md` uses a **structured template** with fixed sections: `## What I was doing`, `## What happened`, `## What I need`
- Gemini polls for `checkpoint/RESPONSE.md` every **120 seconds** (reduces token usage vs. tight polling)
- `monitor_checkpoint.py` (host-side): detects PROMPT.md, **pipes to Claude API** to draft a response, but **Claude asks the operator** if it needs help before finalizing and pushing RESPONSE.md back via `incus file push`

### Scenario script format
- 4 scenario scripts as **Markdown `.md` files** pushed into the LXC
- Scenarios: `ce-install.md`, `ce-operator.md`, `ee-install.md`, `ee-operator.md`
- Each scenario is **fully independent** (self-contained, no shared templates or conditionals between CE/EE)
- Pass/fail criteria are **explicit checklists** — Gemini ticks each item:
  - e.g. `- [ ] Stack reachable at https://172.17.0.1:8443`
  - e.g. `- [ ] Node enrolled and shows CONNECTED`
  - e.g. `- [ ] Python job dispatched and status is COMPLETED`
- Each scenario includes explicit checkpoint trigger conditions (when to pause)
- Each scenario produces a **`FRICTION.md`** with structured sections: `## Blockers`, `## Rough Edges`, `## Checkpoints Used`, `## Verdict`
- Gemini launched with: `HOME=/root/validation-home gemini -p "$(cat ce-install.md)"`

### HOME isolation
- `/root/validation-home/` created and populated by **Phase 62 setup script** (`setup_agent_scaffolding.py` in `mop_validation/scripts/`)
- Pre-populated with only `~/.config/gemini/` (API key config) — copied from the real `~/.config/gemini/` in the LXC
- No `.gemini/` directory (blocks conversation history / session bleed)
- Phase 62 includes an **isolation verification step**: run Gemini with `HOME=/root/validation-home` and confirm it has no knowledge of repo paths or codebase context — proves isolation before live scenarios start

### Claude's Discretion
- Exact structure of `setup_agent_scaffolding.py` (can extend provision pattern or be standalone)
- `checkpoint/PROMPT.md` template wording
- How `monitor_checkpoint.py` signals the operator (print + terminal bell, or desktop notification)
- Internal structure of the 4 scenario `.md` files beyond the required sections (checklist and FRICTION.md spec)

</decisions>

<specifics>
## Specific Ideas

- `monitor_checkpoint.py` sits on the host (not in the LXC) — watches for PROMPT.md via `incus file pull` in a loop, surfaces to Claude API, asks operator if help is needed, then pushes RESPONSE.md back with `incus file push`
- The checkpoint round-trip success criterion requires full cycle in under 60s — polling at 120s satisfies eventual correctness but the round-trip verification test should use a shorter interval to hit the 60s success criterion in the test
- Docs folder inside LXC mirrors `docs/site/` from the main repo — same HTML that would serve at the docs domain

</specifics>

<code_context>
## Existing Code Insights

### Reusable Assets
- `mop_validation/scripts/provision_coldstart_lxc.py`: Established Incus LXC interaction patterns — `incus file push`, `incus exec`, container IP polling. `setup_agent_scaffolding.py` follows the same patterns.
- `mop_validation/manage_incus_node.py`: Alternative Incus management reference.
- `.agent/skills/manage-test-nodes/scripts/manage_node.py`: Original template for all LXC scripting.

### Established Patterns
- `incus file push <local_path> axiom-coldstart<container_path>` — host-to-LXC file transfer
- `incus exec axiom-coldstart -- bash -c "<command>"` — command execution inside LXC
- `HOME=/root/validation-home gemini -p "..."` — isolation invocation (from Phase 62 success criteria)
- `EXECUTION_MODE=direct` and `GEMINI_MODEL` already set in `/etc/environment` by provision script

### Integration Points
- `mop_validation/secrets.env`: Source of Gemini API key (`GEMINI_API_KEY` or `GOOGLE_API_KEY`) for copying into validation-home config
- `docs/site/`: Source for the static docs snapshot pushed into LXC at `/workspace/docs/`
- `checkpoint/` directory: Lives inside the LXC at `/workspace/checkpoint/` — PROMPT.md written by Gemini, RESPONSE.md pushed by host monitor

</code_context>

<deferred>
## Deferred Ideas

- None — discussion stayed within phase scope

</deferred>

---

*Phase: 62-agent-scaffolding*
*Context gathered: 2026-03-25*
