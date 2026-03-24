# Feature Research

**Domain:** AI-agent cold-start validation framework — first-time user simulation via Gemini CLI inside LXC containers
**Researched:** 2026-03-24
**Confidence:** HIGH (derived from docs-as-tests methodology literature, Gemini CLI capabilities research,
existing Axiom v11.1 test infrastructure review, and PROJECT.md milestone scope)

---

## Context: What This Milestone Covers

v14.0 is not feature development. It is a **docs-fidelity and operator-path validation milestone** that uses
Gemini CLI agents as synthetic first-time users. Agents are given only the Axiom docs site (`/docs/`) and
no codebase access. They follow documented install and operator procedures and report friction.

The core insight borrowed from the Docs-as-Tests methodology: "Each doc is a test suite, each procedure a
test case, each step an assertion." v11.1 validated that the system *works*. v14.0 validates that a new user
can *operate it using only the docs*.

**Two scenarios:**
1. CE cold-start: install path + 3 job types (Python, Bash, PowerShell)
2. EE cold-start: same install path + EE-gated features + same 3 job types

**Infrastructure constraint:** Each scenario runs inside an LXC container (Ubuntu 24.04 via Incus) with the
full Axiom Docker stack. No host machine access. Agent reads from the docs site URL only.

---

## Feature Landscape

### Table Stakes (Users Expect These)

Features that are non-negotiable for the test to be valid. Missing any of these means results cannot be trusted.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| **LXC container per scenario with full Axiom stack** | Agent needs a true clean environment — shared state across scenarios invalidates findings | MEDIUM | Docker-in-LXC (Incus nested containers); CE and EE runs get separate LXC instances; existing `manage_node.py` skill provides the pattern |
| **Docs-only instruction source** | If agent has codebase access, it will shortcut past docs friction — cold-start validity requires docs be the sole reference | LOW | Agent prompt explicitly forbids reading files outside `/docs/`; no codebase path provided; constraint is behavioral, not technical |
| **CE scenario covers all 3 runtimes** | Docs claim Python, Bash, and PowerShell all work — each needs at least one job submitted and verified COMPLETED | LOW | Three sequential job dispatches per scenario; each uses a distinct runtime flag in the guided form |
| **EE scenario activates at least one EE-gated feature** | EE licence validation is a documented path — if it goes untested the run has no EE signal | MEDIUM | Pre-generated licence key provided at scenario start; agent must verify EE badge appears and at least one EE feature is accessible |
| **Checkpoint file protocol for blocked states** | When the agent cannot proceed, it must signal rather than hallucinate a solution — otherwise failures are silently skipped | LOW | Agent writes a structured JSON checkpoint file to a known path; external Claude monitors and provides steering; resumes agent |
| **Pass/fail verdict per documented step** | The output must be auditable — each doc step either succeeded or produced a friction point | LOW | Agent writes a step log throughout execution; PASS/FAIL/BLOCKED per step |
| **Friction points captured with evidence** | A finding without evidence (exact error message, unexpected behaviour, missing doc step) is not actionable | LOW | Each friction point includes: the doc page referenced, the step attempted, the actual outcome, the error text or unexpected result |
| **Separate friction report per scenario** | CE and EE paths have different docs and different failure modes — mixed reports obscure which path broke | LOW | Two report files: `friction_ce.md` and `friction_ee.md`; merged summary is the milestone deliverable |
| **Exit code from each job verified** | Submitting a job is not sufficient — the agent must wait for COMPLETED status and confirm exit_code=0 | LOW | Agent polls job status after dispatch; FAILED or PENDING-stuck are friction points |
| **Scenario reproducibility** | If someone runs the same scenario again, they should hit the same friction points — the environment must be deterministic | MEDIUM | LXC teardown and rebuild between CE and EE runs; Axiom stack re-initialised from scratch each time |

### Differentiators (What Makes This Significantly More Useful)

Features that turn a basic pass/fail test into a durable quality signal.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| **Verbatim doc quote per friction point** | Links friction directly to the specific sentence or step that failed, making fixes unambiguous | LOW | Agent records the exact quoted text from the docs page that led to the failed action; not just the page name |
| **Step sequence reconstruction** | Shows whether the agent followed the documented order or had to improvise — improvisation means the docs have an ordering gap | LOW | Agent logs each step as it occurs with a sequence counter; final report shows the actual path taken vs the documented path |
| **Checkpoint steering transcript included in report** | Steering interventions are themselves friction data — they show where a reasonably-capable agent couldn't self-recover | LOW | Each checkpoint intervention (question + answer) is included in the friction report verbatim |
| **Both CE and EE scenarios run against the same docs site build** | Ensures the comparison is valid — docs must not change between runs | LOW | Pin the docs site container image digest before starting; same digest used for both LXC environments |
| **Runtime-specific job assertions** | Python job verifies Python stdout, Bash verifies shell output, PowerShell verifies `Write-Host` output — not just exit_code=0 | LOW | Each job script has a known output string; agent asserts that string appears in the job detail drawer stdout |
| **Severity triage in friction report** | Distinguishes blockers (cannot proceed without steering), slowdowns (takes more steps than documented), and cosmetic issues (wording confusion without impact) | LOW | Three-tier severity: BLOCKER / FRICTION / COSMETIC; each finding tagged |
| **Doc coverage map** | Lists which doc pages and sections were exercised, which were skipped, and which were consulted but produced no action | MEDIUM | Agent records every URL consulted during the run; post-run analysis identifies unvisited pages in the install + operator flow |
| **Comparison table: CE vs EE friction** | Shows which friction points are shared (core docs issues) vs EE-specific (licence + EE feature docs issues) | LOW | Merged summary compares finding lists; shared findings flag core doc gaps; EE-only findings flag EE doc gaps |

### Anti-Features (Commonly Requested, Often Problematic)

Features that seem useful but add complexity without adding validity.

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|-----------------|-------------|
| **Agent has codebase access to "verify" behaviour** | Seems like it would help the agent confirm expected outcomes | Destroys cold-start validity; agent will read source code rather than follow docs; the entire point is docs-only | Hard restrict: no path to codebase in agent prompt; if docs don't explain the expected outcome, that is itself a friction finding |
| **Automated re-run on failure** | Retry loops catch transient failures | Re-runs mask genuine friction — the first-run experience is what matters; retry loops hide friction by eventually succeeding | Use checkpoint protocol instead: block on failure, record it, get human steering, resume exactly once |
| **Full UI automation (Playwright-style) inside the agent** | Precise form interaction | Agents cannot reliably drive React controlled inputs via Playwright inside LXC — known issue from project CLAUDE.md; Playwright inside Docker-in-LXC adds another unreliable layer | Agent uses the REST API (axiom-push CLI and curl) to dispatch jobs; dashboard verification via API not via browser automation |
| **Parallel CE and EE scenarios** | Saves time | Shared host resources cause flaky results; concurrent Docker-in-LXC containers interfere; debugging a flaky parallel run is harder than a 20-minute sequential run | Sequential runs: CE first, EE second; total runtime is bounded and deterministic |
| **Live-streamed friction findings during run** | Real-time visibility into what the agent is doing | Interrupts the agent's flow and introduces observer effect; checkpoint protocol provides async visibility without interrupting | Use checkpoint files as the async signal; review findings only after scenario completion |
| **LLM-as-judge scoring of each finding** | Automated severity classification | LLM scoring of its own outputs is unreliable for novel friction types; adds a latency layer; human review is fast at this scale | Human (or external Claude) triages severity in the merge step; the agent records raw findings without classification |
| **Simulating multiple user personas** | "Junior operator" vs "senior operator" would surface different friction | Out of scope for v14.0; adds significant prompt complexity and scenario management overhead; the target persona (docs-following operator) is already well-defined | Lock persona to: "operator who has read the getting-started guide and follows it literally"; persona expansion is a v15.0+ candidate |
| **Fuzzing the docs (intentionally missing steps)** | Would surface undocumented assumptions | That is a separate test type (mutation testing of docs); conflating it with cold-start validation makes both signals weaker | Keep v14.0 as faithful-follower cold-start; mutation testing is a future research spike |

---

## Feature Dependencies

```
[LXC environment with Docker stack]
    └──required-by──> [All CE and EE scenarios]
    └──required-by──> [Checkpoint file protocol (needs a filesystem path to write to)]

[Pre-generated EE licence key]
    └──required-by──> [EE scenario]
    └──required-by──> [EE badge verification]

[Docs site accessible from inside LXC]
    └──required-by──> [Agent instruction source]
    └──required-by──> [Doc coverage map]

[Checkpoint file protocol]
    └──required-by──> [Blocked state handling]
    └──required-by──> [Steering transcript in friction report]

[CE scenario pass]
    └──enhances──> [CE vs EE friction comparison table]
    └──enhances──> [Shared-finding identification in merged summary]

[Step sequence log]
    └──enhances──> [Friction report severity triage]
    └──enhances──> [Doc coverage map]
```

### Dependency Notes

- **LXC environment must be provisioned before either scenario starts.** The CE LXC needs the Axiom CE Docker
  stack running. The EE LXC needs the EE stack plus the EE licence key injected as an environment variable.
  Both need the docs site accessible (either via the running docs container or a public URL).

- **CE scenario should run before EE.** CE is the simpler path with less setup. Running it first validates
  the infrastructure works before adding EE complexity. Shared friction findings identified in CE don't need
  to be re-investigated in EE — they carry forward.

- **The checkpoint protocol is infrastructure, not a test feature.** It must exist before any scenario runs.
  Without it, a blocked agent has no recovery mechanism and the run is abandoned.

- **Pre-generated EE licence key is a hard prerequisite for the EE scenario.** The docs describe how to
  obtain a licence key (licence issuance portal, which is not yet built), so the test must skip that step and
  inject the key directly — this is an accepted constraint documented in the EE scenario setup.

---

## MVP Definition

### Launch With (v1 — Minimum for Valid Results)

- [ ] CE scenario: LXC environment + Axiom CE stack, agent runs install path + 3 job types, friction report produced
- [ ] EE scenario: Same setup + EE licence injected, agent runs EE feature check + 3 job types, friction report produced
- [ ] Checkpoint protocol: structured JSON file written on block, external Claude provides steering, agent resumes
- [ ] Per-step pass/fail log: agent records each documented step outcome before proceeding
- [ ] Friction points with evidence: verbatim error messages, exact doc references, step context
- [ ] Severity triage: BLOCKER / FRICTION / COSMETIC per finding
- [ ] Merged summary: CE + EE comparison table, shared-finding identification, fix recommendations

### Add After Validation (v1.x)

- [ ] Doc coverage map — only useful after the first run confirms the basic flow works; adds analytical overhead to the initial scenario
- [ ] Verbatim doc quote per friction point — valuable for pinpointing fixes; defer to after MVP validates the overall signal is useful
- [ ] Runtime-specific stdout assertions — can be added to the job submission steps once basic job dispatch works

### Future Consideration (v2+)

- [ ] Multiple user personas (junior operator, security-conscious operator, etc.)
- [ ] Mutation testing of docs (intentionally incomplete procedures to verify agent detects gaps)
- [ ] Automated re-run regression check (run after each docs update to verify no regressions)
- [ ] Parallel scenario execution (only after sequential runs are stable and LXC resource constraints are understood)

---

## Feature Prioritization Matrix

| Feature | User Value | Implementation Cost | Priority |
|---------|------------|---------------------|----------|
| LXC environment per scenario | HIGH | MEDIUM | P1 |
| Docs-only instruction constraint | HIGH | LOW | P1 |
| 3 runtime job coverage per scenario | HIGH | LOW | P1 |
| Checkpoint file protocol | HIGH | LOW | P1 |
| Per-step pass/fail log | HIGH | LOW | P1 |
| Friction points with evidence | HIGH | LOW | P1 |
| Severity triage | HIGH | LOW | P1 |
| Merged summary with comparison | HIGH | LOW | P1 |
| EE licence pre-injection | HIGH | LOW | P1 |
| Exit code verification per job | MEDIUM | LOW | P1 |
| Verbatim doc quote per finding | MEDIUM | LOW | P2 |
| Step sequence reconstruction | MEDIUM | LOW | P2 |
| Runtime-specific stdout assertions | MEDIUM | LOW | P2 |
| Checkpoint steering transcript | MEDIUM | LOW | P2 |
| Doc coverage map | MEDIUM | MEDIUM | P2 |
| CE vs EE comparison table | MEDIUM | LOW | P2 |
| Docs site image digest pinning | LOW | LOW | P3 |
| Multiple persona simulation | LOW | HIGH | P3 |
| Mutation testing of docs | LOW | HIGH | P3 |

**Priority key:**
- P1: Must have — without this, the test result is invalid or incomplete
- P2: Should have — significantly increases signal quality; add once P1 is working
- P3: Nice to have — deferred until the framework is proven and stable

---

## What a Good Friction Report Looks Like

A good friction report is structured, evidence-backed, and immediately actionable. It answers three questions
for each finding: what happened, which doc caused it, and what fix would resolve it.

### Report Structure

```
# Axiom Cold-Start Friction Report — [CE / EE]
Date: [ISO date]
Scenario: [CE / EE]
LXC environment: [incus container name, Axiom version]
Docs site: [URL or container image digest]
Steering interventions: [N]

## Executive Summary
[2-3 sentences: overall result, blocker count, friction count, cosmetic count]
[Pass rate: N of M documented steps completed without friction]

## Step Log
| # | Doc Page | Step Description | Outcome | Notes |
|---|----------|-----------------|---------|-------|
| 1 | /getting-started/install/ | Run docker compose up | PASS | — |
| 2 | /getting-started/install/ | Verify /api/health returns 200 | PASS | — |
| 3 | /getting-started/enroll-node/ | Generate JOIN_TOKEN | BLOCKED | See Finding F-01 |
...

## Findings

### F-01 [BLOCKER] JOIN_TOKEN generation command not in docs
**Doc page:** /getting-started/enroll-node/
**Quoted text:** "Copy the JOIN_TOKEN from the Admin panel"
**Actual outcome:** Admin panel does not have a visible JOIN_TOKEN section; spent 4 minutes searching
**Error / observation:** No JOIN_TOKEN visible in Admin tab; no mention of where exactly in Admin to look
**Steering:** [Question asked to external Claude] [Answer received]
**Recommended fix:** Add a screenshot or precise navigation path ("Admin → Nodes → Join Tokens → Generate")

### F-02 [FRICTION] axiom-push install step references wrong pip package name
**Doc page:** /getting-started/first-job/
**Quoted text:** "Install the CLI: pip install axiom-push"
**Actual outcome:** pip install axiom-push fails with "No matching distribution found"
**Error / observation:** Correct package name is axiom-sdk; docs have not been updated since CLI rename
**Steering:** Not required (agent found correct name from PyPI search)
**Recommended fix:** Update install command to "pip install axiom-sdk"

### F-03 [COSMETIC] PowerShell runtime label inconsistent between docs and dashboard
**Doc page:** /feature-guides/jobs/
**Quoted text:** "Select 'powershell' from the Runtime dropdown"
**Actual outcome:** Dashboard shows 'PowerShell' (capital P); functionally correct but confusing
**Steering:** Not required
**Recommended fix:** Align docs and dashboard label capitalisation

## Checkpoint Interventions
| # | Trigger | Question | Answer | Resolution |
|---|---------|---------|---------|------------|
| 1 | F-01 | "No JOIN_TOKEN visible in Admin..." | "Navigate to Admin → Configuration → Node Enrollment" | Agent resumed and found token |

## CE vs EE Comparison (in merged summary only)
...

## Fix Recommendations (ordered by severity)
1. [BLOCKER findings first, with specific doc page + line or section]
2. ...
```

### Quality Criteria for a Good Friction Report

A valid friction report must satisfy:

1. **Traceability** — Every finding links to an exact doc page and a quoted sentence or instruction.
   Without this, the docs team cannot find what needs fixing.

2. **Reproducibility evidence** — The step log shows exactly what sequence the agent followed so the finding
   can be reproduced by a human. A finding that cannot be reproduced is not actionable.

3. **Steering transparency** — Every checkpoint intervention is disclosed. A finding that was resolved by
   steering is a real friction point — it means the docs were insufficient for self-service recovery.

4. **No inferred fixes in the finding** — The finding records what happened. Fix recommendations are a
   separate section. Mixing them obscures the evidence.

5. **Complete step coverage** — The report must list every documented step, including those that passed.
   A report that only lists failures looks like the product is broken; the PASS steps provide the "this
   worked" context that makes the failures credible.

---

## Dependencies on Existing Axiom Features

The following existing Axiom features are exercised by the cold-start validation and must be working correctly
before the scenarios can produce valid results:

| Axiom Feature | Role in Cold-Start | Risk if Broken |
|--------------|-------------------|----------------|
| `docker compose up` CE stack | CE scenario entry point | Scenario cannot start |
| `/api/health` endpoint | First verified step in getting-started guide | Agent has no confirmation of successful install |
| Admin user seeding on first boot | Agent needs to log in | Auth failure blocks entire CE path |
| Ed25519 job signing via `axiom-push` CLI | Required to submit any job | All 3 runtime tests blocked |
| Guided dispatch form (API-level equivalent) | Agent submits jobs via CLI or REST | Job dispatch tests blocked |
| Job status polling (`GET /api/jobs/{id}`) | Agent verifies COMPLETED status | Cannot verify job execution |
| Job detail stdout retrieval | Runtime-specific output assertions | Cannot verify correct runtime executed |
| EE licence key injection (`AXIOM_LICENCE_KEY`) | EE scenario setup step | EE scenario cannot activate |
| CE/EE edition badge in sidebar | Agent verifies EE licence accepted | EE feature confirmation blocked |
| `/api/features` endpoint | Agent verifies all features true on EE | EE functional verification blocked |
| MkDocs docs site at `/docs/` | Agent's sole instruction source | Cannot run any scenario |

---

## Competitor / Prior Art Analysis

There is no direct competitor for AI-agent cold-start validation of self-hosted infrastructure tools.
The relevant prior art is the broader Docs-as-Tests methodology and LLM-agent harness patterns:

| Approach | How It Works | Axiom v14.0 Approach |
|----------|--------------|----------------------|
| **Docs-as-Tests (Doc Detective)** | Tools parse documented procedures and run steps as assertions against live API | Gemini CLI agent reads docs and follows them; agent reasoning substitutes for step parsing |
| **LLM-as-judge evaluation** | LLM grades another LLM's output against a rubric | Not used — human (external Claude) provides steering when agent is blocked; friction is objective (step failed or didn't), not judged |
| **v11.1 scripted validation** | Python scripts run against live stack, assert API responses | Complementary but different: scripted tests verify correctness; cold-start agents verify operator experience |
| **OpenAI Evals / DeepEval** | Framework for evaluating LLM outputs against test cases | Not applicable — the LLM is the user under test, not the system under test |
| **Traditional UAT** | Human users complete task scenarios, report friction | Cold-start agent replaces human user; checkpoint steering replaces facilitator intervention; friction report replaces user feedback session |

The Axiom approach is closest to **documented-procedure fidelity testing**: the test question is "does
following the docs produce a working system?" not "does the system behave correctly?" (which v11.1 already
answers).

---

## Sources

- [Docs as Tests: A Strategy for Resilient Technical Documentation](https://www.docsastests.com/docs-as-tests/concept/2024/01/09/intro-docs-as-tests.html)
  — Core methodology: "each doc is a test suite, each procedure a test case, each step an assertion" — HIGH confidence
- [Never have stale docs again | Docs as Tests](https://www.docsastests.com/) — Docs-as-Tests overview,
  Doc Detective tool pattern — HIGH confidence
- [Gemini CLI open-source AI agent](https://github.com/google-gemini/gemini-cli) — Headless mode confirmed;
  ReAct loop with built-in tools; supports scripted automation — HIGH confidence
- [Automate UI Testing with Gemini CLI, BrowserMCP and Playwright](https://codelabs.developers.google.com/agentic-ui-testing)
  — Confirms Gemini CLI scripted/headless usage patterns — MEDIUM confidence
- [How to Report Usability Test Results for Maximum Impact | Maze](https://maze.co/guides/usability-testing/results/)
  — Friction report structure: executive summary, step log, severity triage, evidence-backed findings — MEDIUM confidence
- [Usability Testing Report | Lyssna](https://www.lyssna.com/guides/usability-testing-guide/usability-testing-report/)
  — Finding format: task, outcome, evidence, recommendation — MEDIUM confidence
- `/home/thomas/Development/master_of_puppets/.planning/PROJECT.md` — v14.0 milestone scope, existing
  validated features list, CE/EE split status — HIGH confidence
- `/home/thomas/Development/master_of_puppets/.agent/skills/manage-test-nodes/scripts/manage_node.py`
  — Incus/LXC container provisioning pattern for this project — HIGH confidence
- `CLAUDE.md` — Known Playwright limitations in Docker-in-LXC context; localStorage auth pattern;
  axiom stack testing rules — HIGH confidence

---

*Feature research for: Axiom v14.0 — CE/EE Cold-Start Validation Framework*
*Researched: 2026-03-24*
