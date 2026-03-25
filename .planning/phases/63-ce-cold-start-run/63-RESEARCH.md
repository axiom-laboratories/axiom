# Phase 63: CE Cold-Start Run - Research

**Researched:** 2026-03-25
**Domain:** Agent orchestration — Gemini tester execution, LXC/Docker lifecycle, checkpoint relay, friction evidence capture
**Confidence:** HIGH

## Summary

Phase 63 executes two pre-scripted Gemini tester scenarios (`ce-install.md` and `ce-operator.md`) against the `axiom-coldstart` LXC using all scaffolding built in Phase 62. The work is purely orchestration: reset the LXC Docker stack to a clean state, push fresh assets, launch Gemini with HOME isolation, monitor for checkpoints, collect FRICTION files, and pull them to `mop_validation/reports/`. No new scaffolding is needed — everything is already proven working.

The key planning risk is the operator-approval gate between scenarios: the planner must use the GSD human-verify checkpoint pattern so the operator can review `FRICTION-CE-INSTALL.md` before the operator scenario begins. The second major concern is the stack-readiness polling step — the compose stack requires build time on first launch inside the LXC (images have not been built yet; only `hello-world:latest` is present). The plan must account for the Docker build phase taking several minutes.

**Primary recommendation:** Three plans — (1) stack reset + readiness verification, (2) `ce-install` Gemini run with checkpoint monitoring, (3) operator-approved `ce-operator` Gemini run and FRICTION pull.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Scenario sequencing:**
- Two separate operator-confirmed invocations — `ce-install` first, then `ce-operator`
- After `ce-install` completes, operator reviews `FRICTION-CE-INSTALL.md` and confirms the pass/fail checklist shows node enrolled and dashboard reachable — no FAIL items on those criteria — before proceeding
- Claude triggers the second invocation via `incus exec` automatically after operator approval (operator types "approved" or similar, not the command)
- `ce-operator.md` begins with a re-verification step (curl -k to dashboard + docker ps) before attempting any job dispatch

**Stack reset approach:**
- Phase 63 always begins with an explicit clean-slate reset: `docker compose down -v` then `docker compose up -d` inside the LXC — no assumption about prior state
- Before the Gemini run, Claude pushes the current `compose.cold-start.yaml` from the repo into the LXC at `/workspace/compose.cold-start.yaml` — guarantees the latest version is used, not a stale copy from Phase 62
- Claude polls `curl -k -s -o /dev/null -w "%{http_code}" https://172.17.0.1:8443` every 5 seconds with a 120-second timeout; only proceeds to Gemini invocation when the response is 200 or 301

**Checkpoint intervention policy:**
- Always ask operator before pushing `RESPONSE.md` — Claude drafts a steering response using the Claude API, presents it to the operator for approval, then pushes via `incus file push`
- Hard cap of 3 checkpoint interventions per scenario; if Gemini requires a 4th, the scenario is declared a BLOCKER and stopped
- On abort at the 3-intervention limit: Gemini is instructed to write a partial `FRICTION-CE-*.md` up to the point of failure, with the final blocker noted — partial findings are captured and preserved

**CE-05 acceptance gate:**
- Auto-accept if neither FRICTION.md contains a BLOCKER-classified finding; operator only reviews if a BLOCKER appears
- If a BLOCKER is found: Phase 63 still completes — FRICTION evidence is captured and the BLOCKER is noted in `VERIFICATION.md` as a gap for Phase 65 synthesis or a follow-on fix phase
- FRICTION files pulled from inside the LXC (`/workspace/checkpoint/`) to `mop_validation/reports/` on the host via `incus file pull` at the end of each scenario

### Claude's Discretion
- Exact polling implementation for stack readiness check (subprocess vs incus exec bash loop)
- How Claude surfaces the draft RESPONSE.md to the operator (print inline, or write to a temp file for review)
- Whether the stack reset step also re-pushes the static docs snapshot to `/workspace/docs/` or assumes it's still valid from Phase 62

### Deferred Ideas (OUT OF SCOPE)
- None — discussion stayed within phase scope
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| CE-01 | Gemini agent follows CE getting-started docs to install Axiom CE from scratch — stack running, nodes enrolled, dashboard accessible | `ce-install.md` scenario script is ready; stack reset procedure + polling pattern established |
| CE-02 | Gemini agent dispatches and verifies a Python job via the guided dispatch form; execution confirmed in job history | `ce-operator.md` scenario covers Python job dispatch; guided form tested in Phase 62 scaffolding |
| CE-03 | Gemini agent dispatches and verifies a Bash job via the guided dispatch form; execution confirmed in job history | `ce-operator.md` scenario covers Bash job dispatch |
| CE-04 | Gemini agent dispatches and verifies a PowerShell job via the guided dispatch form; execution confirmed in job history | `ce-operator.md` scenario covers PowerShell; `Containerfile.node` includes PS 7.6.0 from GitHub releases |
| CE-05 | CE FRICTION.md produced with verbatim doc quotes for every friction point, full step log, checkpoint steering interventions disclosed, and BLOCKER/NOTABLE/MINOR classification per finding | `tester-gemini.md` mandates FRICTION.md format; scenarios output to uniquely named files (FRICTION-CE-INSTALL.md, FRICTION-CE-OPERATOR.md) |
</phase_requirements>

---

## Standard Stack

### Core

| Library / Tool | Version | Purpose | Why Standard |
|----------------|---------|---------|--------------|
| Incus CLI | System-installed | LXC container lifecycle and file transfer | Phase 61/62 established; `axiom-coldstart` container uses Incus |
| Gemini CLI | 0.35.0 (in LXC) | First-user tester agent | SCAF-01 through SCAF-04 all built around this version |
| Docker Compose | System Docker | Cold-start stack lifecycle | `compose.cold-start.yaml` is the delivery vehicle |
| Python 3 (subprocess) | System | Orchestration scripts | All Phase 61/62 scripts use this pattern |

### Supporting

| Library / Tool | Version | Purpose | When to Use |
|----------------|---------|---------|-------------|
| `monitor_checkpoint.py` | Phase 62 | Host-side checkpoint watcher | Run in background during each Gemini scenario |
| `setup_agent_scaffolding.py` | Phase 62 | Workspace reset (HOME isolation + docs push) | Before each Gemini invocation |
| `provision_coldstart_lxc.py` | Phase 61 | LXC container management | Reference for `incus exec` and `incus file push` patterns |

### Installation

The LXC is already provisioned and running (`Running` status confirmed). No new tool installation is needed. All scripts are in `mop_validation/scripts/`.

---

## Architecture Patterns

### Recommended Phase Structure

```
Plan 63-01: Stack Reset and Readiness
  - Push compose.cold-start.yaml into LXC
  - docker compose down -v (hard reset)
  - docker compose up -d (fresh start — triggers image builds)
  - Poll https://172.17.0.1:8443 with 120s+ timeout
  - Run setup_agent_scaffolding.py to re-initialize workspace

Plan 63-02: CE Install Scenario (ce-install.md)
  - Push ce-install.md into LXC
  - Invoke Gemini with HOME isolation
  - Monitor checkpoints (max 3 interventions)
  - Wait for FRICTION-CE-INSTALL.md
  - Pull FRICTION file to mop_validation/reports/
  - Human-verify checkpoint: operator reviews and types "approved"

Plan 63-03: CE Operator Scenario (ce-operator.md)
  - Push ce-operator.md into LXC
  - Re-verify stack still up (curl + docker ps)
  - Invoke Gemini with HOME isolation
  - Monitor checkpoints (max 3 interventions)
  - Wait for FRICTION-CE-OPERATOR.md
  - Pull FRICTION file to mop_validation/reports/
  - CE-05 acceptance gate check
```

### Pattern 1: Gemini Invocation with HOME Isolation

**What:** Launch Gemini inside the LXC with a sandboxed HOME directory that has only `settings.json` — no developer GEMINI.md, no session history.
**When to use:** Every scenario invocation.

```bash
# Source: Phase 62 established pattern
incus exec axiom-coldstart -- bash -c \
  "HOME=/root/validation-home gemini -p \"\$(cat /workspace/ce-install.md)\""
```

**Critical:** The scenario file must be pushed to `/workspace/` before this command. Do not cat from host — the file must be inside the LXC.

### Pattern 2: Stack Reset

**What:** Hard-wipe the Docker compose state (including named volumes for PKI certs and node secrets) and bring it back up fresh.
**When to use:** Plan 63-01 only — ensures no stale cert or token state from Phase 62 testing bleeds into the CE cold-start run.

```bash
# Inside LXC — hard reset
incus exec axiom-coldstart -- bash -c \
  "cd /workspace && docker compose -f compose.cold-start.yaml down -v"

# Fresh start (images need to be built — allow 5-10 min)
incus exec axiom-coldstart -- bash -c \
  "cd /workspace && docker compose -f compose.cold-start.yaml up -d --build"
```

**Important:** `down -v` removes named volumes (pgdata, node-secrets, certs-volume). This is intentional for a true cold start. Images need to be rebuilt on first run because only `hello-world:latest` is currently cached in the LXC.

### Pattern 3: Stack Readiness Polling

**What:** Poll the dashboard HTTPS endpoint inside the LXC until it returns 200 or 301, with timeout.
**When to use:** After every `docker compose up -d` before invoking Gemini.

```bash
# Run on host via incus exec
for i in $(seq 1 48); do
  STATUS=$(incus exec axiom-coldstart -- bash -c \
    "curl -k -s -o /dev/null -w '%{http_code}' https://172.17.0.1:8443 2>/dev/null")
  if [ "$STATUS" = "200" ] || [ "$STATUS" = "301" ]; then
    echo "Stack ready (HTTP $STATUS)"; break
  fi
  echo "Attempt $i: got $STATUS — waiting 5s"
  sleep 5
done
```

**Timeout note:** 48 * 5s = 240 seconds. Use at least 240 seconds for first-run builds. The 120-second figure in CONTEXT.md is for a warm restart (images already built); for a cold build with `--build`, allow longer.

### Pattern 4: FRICTION File Pull

**What:** Pull FRICTION-CE-*.md from the LXC to `mop_validation/reports/` using `incus file pull`.
**When to use:** After each Gemini scenario completes (FRICTION file present in LXC).

```bash
# Source: Phase 62 patterns (provision_coldstart_lxc.py and monitor_checkpoint.py)
incus file pull \
  axiom-coldstart/workspace/FRICTION-CE-INSTALL.md \
  /home/thomas/Development/mop_validation/reports/FRICTION-CE-INSTALL.md

incus file pull \
  axiom-coldstart/workspace/FRICTION-CE-OPERATOR.md \
  /home/thomas/Development/mop_validation/reports/FRICTION-CE-OPERATOR.md
```

**Note:** CONTEXT.md says pull from `/workspace/checkpoint/` but the scenario scripts write to `/workspace/FRICTION-CE-*.md` (not `/workspace/checkpoint/`). The pull path must match the scenario output path.

### Pattern 5: Checkpoint Monitoring During Gemini Run

**What:** Run `monitor_checkpoint.py` in a separate terminal while Gemini is executing. It polls `/workspace/checkpoint/PROMPT.md` every 30 seconds and surfaces it to the operator.
**When to use:** In parallel with every Gemini invocation.

Since `monitor_checkpoint.py` uses `input()` and requires operator interaction, the plan cannot automate the response push — it must use the existing interactive script. The plan documents: "Start `monitor_checkpoint.py` in a second terminal before launching Gemini."

### Pattern 6: Operator-Approval Human-Verify Checkpoint

**What:** Between ce-install and ce-operator scenarios, present the operator with the pulled `FRICTION-CE-INSTALL.md` and ask for explicit approval before proceeding.
**When to use:** Between Plan 63-02 and Plan 63-03.

This is a standard GSD `## Human-Verify Checkpoint` block in the plan. The operator reviews the FRICTION file and types "approved" (or similar). The plan notes that approval is required only if the install passed on the enrolled-node and dashboard-reachable criteria.

### Anti-Patterns to Avoid

- **Starting the operator scenario without operator approval:** The CONTEXT.md explicitly requires operator review of FRICTION-CE-INSTALL.md. Never auto-proceed.
- **Forgetting `down -v`:** Using `down` without `-v` leaves the PKI certs and node secrets volumes intact, which breaks the cold-start premise (nodes may auto-enroll using stale certs).
- **Polling only 120 seconds when images need building:** The LXC currently has only `hello-world:latest`. The first `docker compose up -d --build` will download and build all images. Allow 300+ seconds for the readiness poll.
- **Pushing RESPONSE.md without operator review:** CONTEXT.md locks this — Claude drafts, operator approves, then push.
- **Continuing past 3 checkpoint interventions:** On the 4th intervention request, abort the scenario and record as BLOCKER.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| LXC file transfer | Custom SSH/SCP tooling | `incus file push/pull` | Already proven in Phase 61/62; axiom-coldstart uses Incus |
| Checkpoint polling | New poller script | `monitor_checkpoint.py --interval 30` | Phase 62 built and SCAF-02 verified this end-to-end |
| HOME isolation setup | Manual HOME manipulation | `setup_agent_scaffolding.py` | SCAF-01/03 verified; already run once and workspace confirmed |
| Stack health checking | Parse docker ps output | `curl -k` HTTP status check | Simpler and reflects what the first-user actually sees |

**Key insight:** The entire Phase 63 infrastructure exists and is verified. The plan tasks are run-sequence steps, not build steps.

---

## Common Pitfalls

### Pitfall 1: FRICTION File Path Mismatch

**What goes wrong:** `incus file pull` fails because the scenario writes `FRICTION-CE-INSTALL.md` to `/workspace/FRICTION-CE-INSTALL.md` but the pull command targets `/workspace/checkpoint/FRICTION-CE-INSTALL.md`.
**Why it happens:** CONTEXT.md mentions `/workspace/checkpoint/` as the pull source, but the scenario scripts (`ce-install.md`, `ce-operator.md`) write to `/workspace/` directly. The checkpoint directory is only for `PROMPT.md`/`RESPONSE.md` exchange.
**How to avoid:** Always pull from `/workspace/FRICTION-CE-*.md`, not `/workspace/checkpoint/FRICTION-CE-*.md`.
**Warning signs:** `incus file pull` returns a non-zero exit code.

### Pitfall 2: Image Build Time Underestimate

**What goes wrong:** The readiness poll times out before the stack is up because the first `docker compose up -d --build` downloads and builds 5+ images (agent, cert-manager, dashboard, docs, node image).
**Why it happens:** LXC Docker image cache currently contains only `hello-world:latest`. All cold-start images must be built from scratch.
**How to avoid:** Use a 300-second polling budget (not 120). Consider `docker compose up -d` logs to estimate progress.
**Warning signs:** Poll loop exits with "Stack not ready after Xs" but `docker ps` shows containers still building.

### Pitfall 3: Stale Workspace After Reset

**What goes wrong:** After `docker compose down -v`, the workspace still has a `FRICTION-CE-INSTALL.md` from a previous run, which Gemini may read and use as prior context.
**Why it happens:** `down -v` only removes Docker named volumes — `/workspace/` on the LXC filesystem is not cleared.
**How to avoid:** Before launching each Gemini scenario, remove old FRICTION and checkpoint files: `incus exec axiom-coldstart -- bash -c "rm -f /workspace/FRICTION-CE-*.md /workspace/checkpoint/*.md"`.
**Warning signs:** Gemini references prior run results in its output.

### Pitfall 4: JOIN_TOKEN Not Set Before Node Auto-Enroll

**What goes wrong:** Node containers start but fail to enroll because `JOIN_TOKEN_1` and `JOIN_TOKEN_2` env vars are empty (compose file defaults them to `:-`).
**Why it happens:** On a cold start, Gemini follows the install docs and the docs walk through generating a join token from the dashboard. The nodes in `compose.cold-start.yaml` need the token passed via environment variable. If Gemini runs `docker compose up -d` before setting tokens, nodes won't enroll.
**How to avoid:** This is an intentional part of the CE-01 test — the scenario docs must explain the join token workflow. Review `docs/getting-started/enroll-node.html` to confirm this flow is documented before the run.
**Warning signs:** Nodes show `PENDING` or never appear in the dashboard. This is a known possible friction point, not a test failure.

### Pitfall 5: monitor_checkpoint.py Requires a PTY

**What goes wrong:** Running `monitor_checkpoint.py` via `subprocess.Popen` or `incus exec` without a PTY hangs at the `input()` call.
**Why it happens:** The interactive `input()` call requires a real terminal. It cannot be driven programmatically.
**How to avoid:** The plan must document that `monitor_checkpoint.py` runs in a separate operator terminal, not as an automated subprocess. The plan tasks for Gemini invocation should instruct the operator to start the monitor first.

### Pitfall 6: validation-home settings.json Has No API Key

**What goes wrong:** Gemini inside the LXC (with `HOME=/root/validation-home`) cannot authenticate to the API because the copied `settings.json` does not contain the `GEMINI_API_KEY`.
**Why it happens:** Gemini CLI reads the API key from the environment variable `GEMINI_API_KEY`, not from `settings.json`. The `settings.json` only stores the auth *method* (`selectedType: gemini-api-key`), not the key value itself.
**How to avoid:** The `GEMINI_API_KEY` must be available in the LXC environment. It is currently set in `/etc/environment` in the LXC (confirmed: `GEMINI_API_KEY=...` is in `/etc/environment`). The invocation must source `/etc/environment` or pass the key explicitly.
**Warning signs:** Gemini exits immediately with an authentication error.

Verified: `GEMINI_API_KEY` is set in `/etc/environment` in the LXC. `HOME=/root/validation-home gemini -p "..."` will inherit it because `/etc/environment` is read at login. For `incus exec`, pass `--env GEMINI_API_KEY=$KEY` or source `/etc/environment` in the bash invocation.

---

## Code Examples

Verified patterns from existing scripts:

### Full Gemini Scenario Invocation

```bash
# Source: Phase 62 established pattern (62-03-SUMMARY.md)
# Push scenario script to LXC workspace
incus file push \
  /home/thomas/Development/mop_validation/scenarios/ce-install.md \
  axiom-coldstart/workspace/ce-install.md

# Run Gemini with HOME isolation (inherits GEMINI_API_KEY from /etc/environment)
incus exec axiom-coldstart -- bash -c \
  "source /etc/environment && HOME=/root/validation-home gemini -p \"\$(cat /workspace/ce-install.md)\""
```

### Stack Reset Sequence

```bash
# Source: CONTEXT.md locked decision + compose.cold-start.yaml analysis

# 1. Push latest compose file from repo
incus file push \
  /home/thomas/Development/master_of_puppets/puppeteer/compose.cold-start.yaml \
  axiom-coldstart/workspace/compose.cold-start.yaml

# 2. Hard reset (removes volumes)
incus exec axiom-coldstart -- bash -c \
  "cd /workspace && docker compose -f compose.cold-start.yaml down -v 2>&1"

# 3. Fresh start with build
incus exec axiom-coldstart -- bash -c \
  "cd /workspace && docker compose -f compose.cold-start.yaml up -d --build 2>&1"
```

### Readiness Poll (host-side Python)

```python
# Source: provision_coldstart_lxc.py polling pattern
import subprocess, time

def wait_for_stack(timeout: int = 300) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        result = subprocess.run(
            ["incus", "exec", "axiom-coldstart", "--",
             "bash", "-c",
             "curl -k -s -o /dev/null -w '%{http_code}' https://172.17.0.1:8443"],
            capture_output=True, text=True, timeout=15,
        )
        code = result.stdout.strip()
        if code in ("200", "301"):
            return True
        time.sleep(5)
    return False
```

### FRICTION File Detection and Pull

```python
# Source: monitor_checkpoint.py pull pattern
import subprocess
from pathlib import Path

def pull_friction_file(scenario: str, dest_dir: str) -> bool:
    """Pull FRICTION-CE-{scenario}.md from LXC to host reports dir."""
    remote = f"/workspace/FRICTION-CE-{scenario.upper()}.md"
    local = Path(dest_dir) / f"FRICTION-CE-{scenario.upper()}.md"
    result = subprocess.run(
        ["incus", "file", "pull", f"axiom-coldstart{remote}", str(local)],
        capture_output=True,
    )
    return result.returncode == 0
```

### Workspace Cleanup Before Scenario

```bash
# Remove previous FRICTION files and checkpoint files before each scenario
incus exec axiom-coldstart -- bash -c \
  "rm -f /workspace/FRICTION-CE-*.md /workspace/checkpoint/PROMPT.md /workspace/checkpoint/RESPONSE.md"
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Manual Gemini invocation with full developer HOME | HOME isolation via `/root/validation-home` | Phase 62 (SCAF-03) | Prevents developer context bleed into tester persona |
| Single FRICTION.md (overwritten each scenario) | Uniquely named `FRICTION-CE-INSTALL.md`, `FRICTION-CE-OPERATOR.md` | Phase 62 (62-agent-scaffolding decision) | Prevents silent data loss when multiple scenarios run sequentially |
| Interactive checkpoint push by operator | `monitor_checkpoint.py` with operator `input()` | Phase 62 (SCAF-02) | Structured relay with timing records |

---

## Open Questions

1. **Does `source /etc/environment` work inside `incus exec -- bash -c`?**
   - What we know: `GEMINI_API_KEY` is in `/etc/environment` in the LXC. `incus exec` does not guarantee login-shell behavior.
   - What's unclear: Whether a non-login `bash -c` invocation reads `/etc/environment` automatically.
   - Recommendation: Explicitly source it: `bash -c "source /etc/environment && HOME=/root/validation-home gemini ..."`. Alternatively pass `--env GEMINI_API_KEY=...` to `incus exec`.

2. **Should `setup_agent_scaffolding.py` be re-run before each scenario or only once before Plan 63-01?**
   - What we know: The workspace was set up in Phase 62 and is confirmed (167 docs files, GEMINI.md present). `docker compose down -v` does not touch `/workspace/`.
   - What's unclear: Whether CONTEXT.md's discretion item ("re-push docs snapshot or assume still valid") should default to re-push or skip.
   - Recommendation: Re-run `setup_agent_scaffolding.py` once at Plan 63-01 to ensure the latest `tester-gemini.md` is in `/workspace/gemini-context/GEMINI.md`. The docs snapshot is already 167 files and valid — no need to re-push. This is Claude's discretion per CONTEXT.md.

3. **How long will the first `docker compose up -d --build` take inside the LXC?**
   - What we know: LXC has internet access. Only `hello-world:latest` is cached. Must build cert-manager, agent, dashboard, docs, and node images.
   - What's unclear: Exact build time depends on network speed inside the LXC.
   - Recommendation: Set polling budget to 600 seconds for first run. Add a note in the plan that 5-10 minutes is expected.

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest (mop_validation) + custom verification scripts |
| Config file | None — scripts are standalone (`python3 script.py`) |
| Quick run command | `python3 /home/thomas/Development/mop_validation/scripts/verify_ce_install.py` |
| Full suite command | Manual — FRICTION files reviewed by operator; no automated pytest suite for CE-01 through CE-05 |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| CE-01 | Stack running, node enrolled, dashboard accessible | Gemini scenario | `incus exec axiom-coldstart -- bash -c "..."` (ce-install.md) | FRICTION-CE-INSTALL.md (generated) |
| CE-02 | Python job dispatched via guided form, COMPLETED with stdout | Gemini scenario | ce-operator.md Python job checklist | FRICTION-CE-OPERATOR.md (generated) |
| CE-03 | Bash job dispatched via guided form, COMPLETED with stdout | Gemini scenario | ce-operator.md Bash job checklist | FRICTION-CE-OPERATOR.md (generated) |
| CE-04 | PowerShell job dispatched via guided form, COMPLETED with stdout | Gemini scenario | ce-operator.md PowerShell job checklist | FRICTION-CE-OPERATOR.md (generated) |
| CE-05 | FRICTION.md contains BLOCKER/NOTABLE/MINOR classification, verbatim quotes, checkpoint disclosure | Manual review | `cat mop_validation/reports/FRICTION-CE-*.md` | ✅ tester-gemini.md mandates format |

### Sampling Rate

- **Per task commit:** Verify FRICTION file exists in LXC before pulling
- **Per wave merge:** Both FRICTION files present in `mop_validation/reports/`
- **Phase gate:** FRICTION files pulled and CE-05 acceptance gate evaluated before `/gsd:verify-work`

### Wave 0 Gaps

None — existing infrastructure covers all phase requirements. The verification script `verify_phase62_scaf.py` already validates scaffolding. CE-specific verification (`verify_ce_install.py`, `verify_ce_job.py`) exists for post-run checks.

---

## Sources

### Primary (HIGH confidence)

- `mop_validation/scenarios/ce-install.md` — CE install scenario structure, pass/fail checklist, output path
- `mop_validation/scenarios/ce-operator.md` — CE operator scenario, 3-runtime job dispatch checklist
- `mop_validation/scenarios/tester-gemini.md` — Gemini persona constraints, FRICTION.md template, checkpoint protocol
- `mop_validation/scripts/monitor_checkpoint.py` — checkpoint relay implementation (verified SCAF-02)
- `mop_validation/scripts/setup_agent_scaffolding.py` — workspace setup patterns
- `mop_validation/scripts/provision_coldstart_lxc.py` — `incus exec`/`incus file push` helper patterns
- `puppeteer/compose.cold-start.yaml` — stack services, JOIN_TOKEN pattern, volume layout
- `.planning/phases/62-agent-scaffolding/62-VERIFICATION.md` — Phase 62 all-green status confirmed
- `.planning/phases/62-agent-scaffolding/62-03-SUMMARY.md` — Phase 62 completion evidence

### Secondary (MEDIUM confidence)

- Live `incus list axiom-coldstart` query — container Running, Docker images cache state (hello-world only)
- `/etc/environment` in LXC — `GEMINI_API_KEY` confirmed present, `GEMINI_MODEL=gemini-2.0-flash`

### Tertiary (LOW confidence)

- Build time estimate (5-10 min) — inferred from image count and typical Docker build speed; not measured

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all tools confirmed present and working from Phase 62
- Architecture: HIGH — execution patterns are direct copies/adaptations of Phase 61/62 scripts
- Pitfalls: HIGH — FRICTION file path mismatch and JOIN_TOKEN flow are deterministic findings from reading scenario scripts; image build time is MEDIUM
- Validation: HIGH — requirement mapping is straightforward (each CE-0N requirement is one Gemini scenario checklist item)

**Research date:** 2026-03-25
**Valid until:** 2026-04-25 (stable infrastructure, 30-day window)
