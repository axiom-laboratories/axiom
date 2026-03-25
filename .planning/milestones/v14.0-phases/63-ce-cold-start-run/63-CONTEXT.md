# Phase 63: CE Cold-Start Run - Context

**Gathered:** 2026-03-25
**Status:** Ready for planning

<domain>
## Phase Boundary

Execute the CE Gemini tester run end-to-end: reset the LXC stack to a clean cold start, run `ce-install.md` (Gemini installs Axiom CE from scratch), operator confirms install passed, then run `ce-operator.md` (Gemini dispatches Python/Bash/PowerShell jobs via guided form). Each scenario produces a uniquely named FRICTION file. Pull both FRICTION files to `mop_validation/reports/`. Phase is complete when both scenarios have run and FRICTION files are preserved. Does not synthesise findings — that is Phase 65.

</domain>

<decisions>
## Implementation Decisions

### Scenario sequencing
- Two separate operator-confirmed invocations — `ce-install` first, then `ce-operator`
- After `ce-install` completes, operator reviews `FRICTION-CE-INSTALL.md` and confirms the pass/fail checklist shows node enrolled and dashboard reachable — no FAIL items on those criteria — before proceeding
- Claude triggers the second invocation via `incus exec` automatically after operator approval (operator types "approved" or similar, not the command)
- `ce-operator.md` begins with a re-verification step (curl -k to dashboard + docker ps) before attempting any job dispatch

### Stack reset approach
- Phase 63 always begins with an explicit clean-slate reset: `docker compose down -v` then `docker compose up -d` inside the LXC — no assumption about prior state
- Before the Gemini run, Claude pushes the current `compose.cold-start.yaml` from the repo into the LXC at `/workspace/compose.cold-start.yaml` — guarantees the latest version is used, not a stale copy from Phase 62
- Claude polls `curl -k -s -o /dev/null -w "%{http_code}" https://172.17.0.1:8443` every 5 seconds with a 120-second timeout; only proceeds to Gemini invocation when the response is 200 or 301

### Checkpoint intervention policy
- Always ask operator before pushing `RESPONSE.md` — Claude drafts a steering response using the Claude API, presents it to the operator for approval, then pushes via `incus file push`
- Hard cap of 3 checkpoint interventions per scenario; if Gemini requires a 4th, the scenario is declared a BLOCKER and stopped
- On abort at the 3-intervention limit: Gemini is instructed to write a partial `FRICTION-CE-*.md` up to the point of failure, with the final blocker noted — partial findings are captured and preserved

### CE-05 acceptance gate
- Auto-accept if neither FRICTION.md contains a BLOCKER-classified finding; operator only reviews if a BLOCKER appears
- If a BLOCKER is found: Phase 63 still completes — FRICTION evidence is captured and the BLOCKER is noted in `VERIFICATION.md` as a gap for Phase 65 synthesis or a follow-on fix phase
- FRICTION files pulled from inside the LXC (`/workspace/checkpoint/`) to `mop_validation/reports/` on the host via `incus file pull` at the end of each scenario

### Claude's Discretion
- Exact polling implementation for stack readiness check (subprocess vs incus exec bash loop)
- How Claude surfaces the draft RESPONSE.md to the operator (print inline, or write to a temp file for review)
- Whether the stack reset step also re-pushes the static docs snapshot to `/workspace/docs/` or assumes it's still valid from Phase 62

</decisions>

<specifics>
## Specific Ideas

- The operator approval gate between scenarios is a natural GSD human-verify checkpoint — the plan should use the checkpoint protocol pattern from Phase 62 rather than an ad-hoc wait
- Partial FRICTION.md on abort is still valuable signal — e.g. if Gemini can't get past the install step, that's the most important finding of the whole validation

</specifics>

<code_context>
## Existing Code Insights

### Reusable Assets
- `mop_validation/scripts/provision_coldstart_lxc.py`: Established `incus file push`, `incus exec`, IP polling patterns — Phase 63 run orchestration follows the same primitives
- `mop_validation/scripts/monitor_checkpoint.py`: Already implements PROMPT.md detection, Claude API draft, and `incus file push` for RESPONSE.md — Phase 63 plan invokes this as-is
- `mop_validation/scenarios/ce-install.md` + `ce-operator.md`: Complete scenario scripts from Phase 62 — ready to use, no modification needed
- `mop_validation/scripts/setup_agent_scaffolding.py`: HOME isolation setup — must be run before each Gemini invocation to ensure `/root/validation-home` is clean

### Established Patterns
- `HOME=/root/validation-home gemini -p "$(cat ce-install.md)"` — isolation invocation (locked from Phase 62)
- `incus file push <local> axiom-coldstart<container_path>` — host-to-LXC file transfer
- `incus exec axiom-coldstart -- bash -c "<cmd>"` — command execution inside LXC
- `incus file pull axiom-coldstart/workspace/checkpoint/FRICTION-CE-INSTALL.md ./mop_validation/reports/` — LXC-to-host extraction

### Integration Points
- `mop_validation/secrets.env`: Source of `GEMINI_API_KEY` — must be available in the LXC's `/root/validation-home/.config/gemini/` before each run
- `puppeteer/compose.cold-start.yaml`: Pushed fresh into LXC at run start — CE run uses this with no `AXIOM_LICENCE_KEY` set
- `mop_validation/reports/`: Destination for both `FRICTION-CE-INSTALL.md` and `FRICTION-CE-OPERATOR.md` after pull

</code_context>

<deferred>
## Deferred Ideas

- None — discussion stayed within phase scope

</deferred>

---

*Phase: 63-ce-cold-start-run*
*Context gathered: 2026-03-25*
