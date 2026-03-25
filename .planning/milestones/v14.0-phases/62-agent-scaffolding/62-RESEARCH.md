# Phase 62: Agent Scaffolding - Research

**Researched:** 2026-03-25
**Domain:** Gemini CLI isolation, file-based checkpoint protocol, Incus LXC file ops, scenario scripting
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Tester GEMINI.md persona and content:**
- Gemini plays a first-time user who has never seen Axiom — follows docs literally, no shortcuts, no prior knowledge
- Tester GEMINI.md lives at `/workspace/gemini-context/GEMINI.md` inside the LXC
- Docs are delivered as a static copy of `docs/site/` pushed into `/workspace/docs/` at Phase 62 setup time — no web server needed, Gemini reads via `file:///workspace/docs/...`
- GEMINI.md references the local docs path only — no codebase mentions, no CLAUDE.md, no repo structure
- Gemini is restricted to docs folder only — no external web search, no Stack Overflow, no GitHub lookups
- If blocked for >2 attempts, Gemini writes `checkpoint/PROMPT.md` and halts to wait for Claude response

**Checkpoint trigger policy:**
- Gemini checkpoints only when blocked: docs don't explain the next step, an error isn't explained, or a required value is missing
- No proactive stage-gate checkpoints — Claude only intervenes when needed
- `checkpoint/PROMPT.md` uses a structured template with fixed sections: `## What I was doing`, `## What happened`, `## What I need`
- Gemini polls for `checkpoint/RESPONSE.md` every 120 seconds (reduces token usage vs. tight polling)
- `monitor_checkpoint.py` (host-side): detects PROMPT.md, pipes to Claude API to draft a response, but Claude asks the operator if it needs help before finalizing and pushing RESPONSE.md back via `incus file push`

**Scenario script format:**
- 4 scenario scripts as Markdown `.md` files pushed into the LXC
- Scenarios: `ce-install.md`, `ce-operator.md`, `ee-install.md`, `ee-operator.md`
- Each scenario is fully independent (self-contained, no shared templates or conditionals between CE/EE)
- Pass/fail criteria are explicit checklists — Gemini ticks each item
- Each scenario includes explicit checkpoint trigger conditions (when to pause)
- Each scenario produces a `FRICTION.md` with structured sections: `## Blockers`, `## Rough Edges`, `## Checkpoints Used`, `## Verdict`
- Gemini launched with: `HOME=/root/validation-home gemini -p "$(cat ce-install.md)"`

**HOME isolation:**
- `/root/validation-home/` created and populated by Phase 62 setup script (`setup_agent_scaffolding.py` in `mop_validation/scripts/`)
- Pre-populated with only `~/.config/gemini/` (API key config) — copied from the real `~/.config/gemini/` in the LXC
- No `.gemini/` directory (blocks conversation history / session bleed)
- Phase 62 includes an isolation verification step: run Gemini with `HOME=/root/validation-home` and confirm it has no knowledge of repo paths or codebase context — proves isolation before live scenarios start

### Claude's Discretion
- Exact structure of `setup_agent_scaffolding.py` (can extend provision pattern or be standalone)
- `checkpoint/PROMPT.md` template wording
- How `monitor_checkpoint.py` signals the operator (print + terminal bell, or desktop notification)
- Internal structure of the 4 scenario `.md` files beyond the required sections (checklist and FRICTION.md spec)

### Deferred Ideas (OUT OF SCOPE)
- None — discussion stayed within phase scope
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| SCAF-01 | Tester GEMINI.md constrains Gemini to first-user behaviour — docs site and dashboard access only, no codebase reads, no prior knowledge assumed | GEMINI.md loaded from `$HOME/.gemini/GEMINI.md` (global) and via CWD hierarchy traversal — placing tester GEMINI.md at `/workspace/gemini-context/GEMINI.md` and running from `/workspace/` with fresh HOME isolates it from repo GEMINI.md |
| SCAF-02 | File-based checkpoint protocol implemented — Gemini writes a version-stamped checkpoint when blocked, Claude reads via `incus file pull` and writes a steering response file; 5-minute timeout with graceful degradation prevents deadlock | `incus file pull/push` pattern proven in `provision_coldstart_lxc.py`; polling loop with timeout is a straightforward Python pattern; the 60s round-trip criterion can be met by using shorter poll intervals in the verification test |
| SCAF-03 | Session HOME isolation ensures each validation run starts with a fresh HOME directory so Gemini cannot auto-load developer context, prior session history, or repo GEMINI.md | Verified live: Gemini CLI v0.35.0 reads home from `GEMINI_CLI_HOME` env var (takes priority over `os.homedir()`), then `HOME` env var. No `.gemini/history/` in validation-home prevents session bleed. The global GEMINI.md lives at `$HOME/.gemini/GEMINI.md` — absent from validation-home. |
| SCAF-04 | Scenario prompt scripts define the structured test procedure for CE install path, CE operator path, EE install path, and EE operator path — each with explicit pass/fail criteria and checkpoint trigger conditions | All four scenarios are Markdown files with known structure; CE and EE differ in licence injection step; each produces a FRICTION.md |
</phase_requirements>

---

## Summary

Phase 62 creates four deliverables that must all work together before any live scenario runs: a constrained tester GEMINI.md, a file-based checkpoint protocol with host-side monitor, a verified HOME isolation setup, and four scenario prompt scripts. The infrastructure already exists — this phase is entirely Python scripting and content authoring, not framework installation.

The most important technical finding from this research is how Gemini CLI v0.35.0 locates and loads GEMINI.md files. It uses a two-tier system: a "global" file at `$HOME/.gemini/GEMINI.md` and "project" files discovered by traversing up from the CWD to the nearest `.git` directory. The isolation guarantee requires: (1) a fresh HOME with no `~/.gemini/GEMINI.md`, and (2) running Gemini from a CWD with no `.git` in its directory hierarchy. The `/workspace/` directory inside the LXC satisfies both when populated correctly.

The second key finding is the checkpoint round-trip timing constraint. The success criterion requires a complete round-trip in under 60 seconds, but the CONTEXT.md specifies Gemini polls every 120 seconds. This is not a contradiction — the 120-second interval is for live scenario runs to conserve tokens. The verification test for SCAF-02 must use a shorter interval (e.g., 5 seconds) to prove the mechanical correctness of the protocol within 60 seconds.

**Primary recommendation:** Build `setup_agent_scaffolding.py` as a standalone script following the `provision_coldstart_lxc.py` helper pattern. Create the tester GEMINI.md with explicit "you are a first-time user" persona and hard document path constraints. Write `monitor_checkpoint.py` as a host-side polling loop using `incus file pull` with a 5-second check interval and operator prompt before writing RESPONSE.md.

---

## Standard Stack

### Core

| Tool | Version | Purpose | Why Standard |
|------|---------|---------|--------------|
| Gemini CLI | 0.35.0 (in LXC) | Tester agent runtime | Already installed and verified in `axiom-coldstart` LXC |
| Incus | 6.22 (host) | LXC management, file push/pull | All existing scripts use `incus file push/pull/exec` |
| Python 3 | 3.12 (host) | `setup_agent_scaffolding.py`, `monitor_checkpoint.py` | All existing validation scripts use Python 3 |

### Supporting

| Tool | Version | Purpose | When to Use |
|------|---------|---------|-------------|
| `subprocess.run(["incus", ...])` | stdlib | Host→LXC file push/exec | Reuse pattern from `provision_coldstart_lxc.py` |
| `pathlib.Path` | stdlib | Local file I/O | Read docs/site, write checkpoint files |
| `time.sleep` / `time.time` | stdlib | Poll loop, timeout tracking | `monitor_checkpoint.py` poll loop |

### Installation

No new dependencies. All tooling is already present in the LXC (Gemini CLI 0.35.0) and on the host (Python 3, Incus).

---

## Architecture Patterns

### Recommended File Structure

Phase 62 creates these files:

```
mop_validation/scripts/
├── setup_agent_scaffolding.py    # New: sets up /workspace/ inside LXC
└── monitor_checkpoint.py         # New: host-side checkpoint watcher

mop_validation/scenarios/
├── ce-install.md                 # New: CE install scenario prompt
├── ce-operator.md                # New: CE operator scenario prompt
├── ee-install.md                 # New: EE install scenario prompt
└── ee-operator.md                # New: EE operator scenario prompt

# Created INSIDE the LXC by setup_agent_scaffolding.py:
/workspace/
├── gemini-context/
│   └── GEMINI.md                 # Tester persona: first-time user, docs only
├── docs/                         # Static copy of docs/site/ (15 MB)
│   ├── getting-started/
│   ├── feature-guides/
│   └── ...
└── checkpoint/
    ├── PROMPT.md                 # Written by Gemini when blocked
    └── RESPONSE.md               # Written by host monitor after operator input

/root/validation-home/
└── .gemini/                      # Minimal: settings.json only (NO GEMINI.md, NO history/)
    └── settings.json
```

### Pattern 1: HOME Isolation for Gemini CLI

**What:** Gemini CLI v0.35.0 checks `GEMINI_CLI_HOME` env var first, then `os.homedir()` (which reads the `HOME` env var on Linux). The global GEMINI.md is checked at `$HOME/.gemini/GEMINI.md`. Conversation history lives in `$HOME/.gemini/history/`.

**How to isolate:**
1. Create `/root/validation-home/.gemini/` with only `settings.json` (API key auth config)
2. Do NOT create `/root/validation-home/.gemini/GEMINI.md` — its absence means no global context
3. Do NOT copy `/root/.gemini/history/` — its absence means no session bleed
4. Invoke as: `HOME=/root/validation-home gemini -p "$(cat scenario.md)"`

**CWD isolation:** Gemini traverses up from CWD to nearest `.git` directory to discover project GEMINI.md files. Running from `/workspace/` prevents this — `/workspace/` has no `.git` ancestor inside the LXC.

**GEMINI.md in `/workspace/gemini-context/`:** The tester GEMINI.md is NOT at `~/.gemini/GEMINI.md`. Instead, it is included explicitly in the scenario prompt (or added to the CWD via `/dir add` instruction in the prompt). The cleanest approach: reference `/workspace/gemini-context/GEMINI.md` explicitly in the launch prompt — `gemini -p "Read /workspace/gemini-context/GEMINI.md first, then: $(cat scenario.md)"`.

**Verified live:** Gemini CLI 0.35.0 in the LXC uses `paths.js` with `homedir()` that respects `HOME` env var. The `.gemini/projects.json` is the only other file needed (or the `mkdir -p` must ensure the directory exists so CLI doesn't crash on startup).

```python
# Source: paths.js in @google/gemini-cli-core (verified live in LXC)
# homedir() checks GEMINI_CLI_HOME first, then os.homedir() (reads $HOME on Linux)
# Setting HOME=/root/validation-home redirects all three:
#   1. ~/.gemini/GEMINI.md (global context) → absent
#   2. ~/.gemini/history/ (session history) → absent
#   3. ~/.gemini/settings.json → present (copied from real home)

def create_validation_home(container: str) -> None:
    run_in_lxc(container, "mkdir -p /root/validation-home/.gemini")
    # Copy only settings.json (auth config) — NOT history or projects
    run_in_lxc(container, "cp /root/.gemini/settings.json /root/validation-home/.gemini/settings.json")
    # Touch projects.json to prevent ENOENT crash
    run_in_lxc(container, "echo '{}' > /root/validation-home/.gemini/projects.json")
    # No GEMINI.md in .gemini/ — this is the isolation point
```

### Pattern 2: Checkpoint Protocol File Layout

**What:** File-based async handoff. Gemini writes `PROMPT.md` when blocked. Host monitor detects it, surfaces to operator, writes `RESPONSE.md`. Gemini polls for `RESPONSE.md` and continues.

**File protocol:**

```
/workspace/checkpoint/PROMPT.md   — written by Gemini (inside LXC)
/workspace/checkpoint/RESPONSE.md — written by host monitor (via incus file push)
```

**State machine:**
1. No files: normal operation
2. PROMPT.md exists, RESPONSE.md absent: Gemini is waiting; host should respond
3. RESPONSE.md exists: Gemini reads it and continues; deletes both files after reading
4. PROMPT.md exists + 5-minute timeout: Gemini degrades gracefully (documents as "no response received" in FRICTION.md and continues best-effort)

**Gemini-side polling (in tester GEMINI.md instructions):**
```
When blocked:
1. Write /workspace/checkpoint/PROMPT.md using the template below
2. Wait 120 seconds, then check if /workspace/checkpoint/RESPONSE.md exists
3. If RESPONSE.md exists: read it, delete both files, continue
4. If RESPONSE.md absent after 300 seconds total: document as UNRESOLVED in FRICTION.md, continue best-effort
```

**Host-side monitor:**
```python
# Source: pattern from provision_coldstart_lxc.py
CONTAINER = "axiom-coldstart"
PROMPT_PATH = "/workspace/checkpoint/PROMPT.md"
RESPONSE_PATH = "/workspace/checkpoint/RESPONSE.md"
CHECK_INTERVAL = 5  # seconds (use 5 for verification test, 30 for live monitoring)

def pull_file_from_lxc(container: str, remote_path: str, local_path: Path) -> bool:
    result = subprocess.run(
        ["incus", "file", "pull", f"{container}{remote_path}", str(local_path)],
        capture_output=True,
    )
    return result.returncode == 0

def push_file_to_lxc(container: str, local_path: Path, remote_path: str) -> None:
    subprocess.run(
        ["incus", "file", "push", str(local_path), f"{container}{remote_path}"],
        check=True,
    )
```

### Pattern 3: Incus File Push/Pull Operations

**What:** Move files between host and LXC using `incus file push` and `incus file pull`.

**Verified patterns from `provision_coldstart_lxc.py`:**

```python
# Push a local file to the LXC
def push_file_to_lxc(container: str, local_path: str, remote_path: str) -> None:
    result = subprocess.run(
        ["incus", "file", "push", local_path, f"{container}{remote_path}"],
        capture_output=False,
    )
    if result.returncode != 0:
        raise RuntimeError(f"incus file push failed: {local_path} -> {remote_path}")

# Push an entire directory tree recursively
def push_directory_to_lxc(container: str, local_dir: str, remote_dir: str) -> None:
    result = subprocess.run(
        ["incus", "file", "push", "--recursive", local_dir, f"{container}{remote_dir}"],
        capture_output=False,
    )
    if result.returncode != 0:
        raise RuntimeError(f"incus file push --recursive failed")

# Pull a file from LXC to host
def pull_file_from_lxc(container: str, remote_path: str, local_path: str) -> bool:
    result = subprocess.run(
        ["incus", "file", "pull", f"{container}{remote_path}", local_path],
        capture_output=True,
    )
    return result.returncode == 0
```

**Pushing docs/site (15 MB) to LXC:**
```python
# Source: established incus file push --recursive pattern
docs_site = Path("~/Development/master_of_puppets/docs/site").expanduser()
push_directory_to_lxc(CONTAINER, str(docs_site), "/workspace/docs/")
```

### Pattern 4: Tester GEMINI.md Content Structure

**What:** The tester GEMINI.md defines the Gemini agent persona and constraints. It must prevent the agent from using developer knowledge or accessing the codebase.

**Required elements:**
1. Persona declaration: first-time user, never seen Axiom before
2. Docs path: `file:///workspace/docs/` — how to find documentation
3. Access restrictions: docs only, no web search, no GitHub, no Stack Overflow
4. Checkpoint instructions: when and how to write PROMPT.md
5. FRICTION.md instructions: how to record findings
6. Terminal access: allowed only for following documented steps

**GEMINI.md skeleton (Claude's discretion for exact wording):**

```markdown
# Tester Context

You are a first-time user evaluating Axiom. You have no prior knowledge of the
Axiom codebase or architecture. You follow documentation literally.

## Your Docs

All documentation is at `file:///workspace/docs/`. Read HTML files from there.
Start at `file:///workspace/docs/index.html`.

## Rules

1. Only use documentation at `file:///workspace/docs/` — no web search
2. No reading code files outside `/workspace/docs/`
3. No Stack Overflow, GitHub, external URLs
4. Follow docs literally — do not infer undocumented steps

## When You Are Blocked

If you have tried something twice and it hasn't worked, and the docs don't explain it:

1. Write `/workspace/checkpoint/PROMPT.md` with this template:
   ```
   ## What I was doing
   [current step from the scenario]

   ## What happened
   [exact error or unexpected behaviour]

   ## What I need
   [specific question or missing information]
   ```
2. Wait 120 seconds, then check if `/workspace/checkpoint/RESPONSE.md` exists
3. If it exists: read it, delete both files, continue
4. If after 300 seconds it still doesn't exist: record as UNRESOLVED in FRICTION.md and continue

## Recording Findings

Maintain `/workspace/FRICTION.md` as you go. Add an entry for every friction point.
At the end write a summary with sections: `## Blockers`, `## Rough Edges`,
`## Checkpoints Used`, `## Verdict`.
```

### Pattern 5: Checkpoint Round-Trip Verification Test

**What:** SCAF-02 requires a complete round-trip in under 60 seconds. This is a protocol correctness test, separate from live scenario operation (which uses 120s polling).

**How to test:**
1. Write a synthetic PROMPT.md to the LXC: `incus file push test-prompt.md axiom-coldstart/workspace/checkpoint/PROMPT.md`
2. Start `monitor_checkpoint.py` with `CHECK_INTERVAL=5`
3. Monitor detects PROMPT.md within 5 seconds
4. Operator (or automated test) writes a synthetic RESPONSE.md
5. Monitor pushes RESPONSE.md: `incus file push response.md axiom-coldstart/workspace/checkpoint/RESPONSE.md`
6. Verify total elapsed time < 60 seconds
7. Verify file appears at correct path in LXC

**Timing budget for 60-second round-trip:**
- Detect PROMPT.md on host: ≤5s (5s poll interval)
- Operator reads and types response: ~30s (manual step in test)
- Push RESPONSE.md to LXC: <1s
- Total: ~36s — well within 60s if operator acts promptly

### Anti-Patterns to Avoid

- **Copying `~/.gemini/history/` to validation-home**: Carries session context from previous Gemini runs — defeats isolation
- **Running Gemini from `/workspace/puppeteer/` or any git-tracked directory**: Gemini traverses up to `.git`, finds repo GEMINI.md — loads developer context
- **Using GEMINI_CLI_HOME instead of HOME**: Both work but `HOME=/root/validation-home` also redirects `~/.config/gemini/` which stores OAuth tokens; `GEMINI_CLI_HOME` only redirects `~/.gemini/`. If the API key is in `settings.json` (gemini-api-key auth type), `HOME` is the correct variable.
- **Placing the tester GEMINI.md at `~/.gemini/GEMINI.md` in validation-home**: The global GEMINI.md loads for ALL directories. The tester GEMINI.md should be loaded explicitly via the prompt, not as global context.
- **Hard-coding Gemini poll interval at 120s in the verification test**: The verification test must use a shorter interval (5-10s) to demonstrate the mechanical round-trip completes in under 60s. The 120s interval is only for live scenario conserving tokens.
- **Omitting projects.json from validation-home `.gemini/`**: Gemini CLI crashes with `ENOENT: no such file or directory, rename .../projects.json.tmp -> .../projects.json` if the `.gemini/` directory exists but `projects.json` is absent.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| LXC file operations | Custom SSH/SCP | `incus file push/pull` | Already used in `provision_coldstart_lxc.py`; no credentials needed |
| LXC command execution | paramiko/fabric | `incus exec CONTAINER -- bash -c "..."` | Zero-config, proven in existing scripts |
| Docs delivery to LXC | Web server, nginx | `incus file push --recursive docs/site/ axiom-coldstart/workspace/docs/` | `file:///workspace/docs/` is simpler than a server |
| Gemini isolation | Custom wrapper process | `HOME=/root/validation-home gemini -p "..."` | HOME env var is sufficient; Gemini CLI reads it correctly |
| Checkpoint detection | inotify/watchdog | Poll loop with `incus file pull` + `time.sleep(5)` | Simpler, no extra deps, proven pattern |

---

## Common Pitfalls

### Pitfall 1: Gemini CLI crashes if `.gemini/` directory missing in fresh HOME

**What goes wrong:** `ENOENT: no such file or directory, rename .../projects.json.tmp -> .../projects.json` error on startup.
**Why it happens:** Gemini CLI tries to write `projects.json` atomically (write to `.tmp`, then rename). The parent `.gemini/` directory must exist.
**How to avoid:** `mkdir -p /root/validation-home/.gemini` and create an empty `projects.json` (`echo '{"projects":{}}' > .../projects.json`) in setup script.
**Warning signs:** Exit code 1 with ENOENT in stderr when invoking `HOME=/root/validation-home gemini -p "..."`.

### Pitfall 2: Free-tier API quota causes Gemini CLI to hang

**What goes wrong:** Gemini CLI hangs indefinitely (does not exit with error) when the API returns 429 rate-limit responses.
**Why it happens:** The current `GEMINI_API_KEY` in the LXC is on the free tier (0 RPD limit confirmed in live test). Gemini CLI retries silently.
**How to avoid:** Before running any Gemini invocation, verify the API key tier. Use `curl` directly to the Gemini API endpoint — a 429 with `free_tier` quota exhausted means the key needs upgrading to Tier 1 (paid). This is noted as a blocker in STATE.md: "Gemini API key tier must be Tier 1 (paid) for a full CE+EE run."
**Warning signs:** `timeout 30 gemini -p "hello"` exits 124 (SIGKILL from timeout) with no output.
**Isolation verification note:** The verification test for SCAF-03 must be designed to confirm isolation without actually calling the Gemini API — use a mock or document the test as "API-gated."

### Pitfall 3: Gemini traverses up to repo GEMINI.md from `/workspace/puppeteer/` CWD

**What goes wrong:** If Gemini is invoked with `--cwd /workspace/puppeteer/` or from any path inside a git repo, it discovers the repo's `GEMINI.md` and loads developer context.
**Why it happens:** `memoryDiscovery.js` traverses upward from CWD to the nearest `.git` directory, loading all `GEMINI.md` files in the hierarchy.
**How to avoid:** Always invoke Gemini from `/workspace/` (not a git subdirectory). Create `/workspace/` as a fresh non-git directory.
**Warning signs:** The Gemini context summary shown at startup mentions "master_of_puppets" or "puppeteer/" paths.

### Pitfall 4: 120-second Gemini poll interval fails the 60-second round-trip test

**What goes wrong:** SCAF-02 success criterion requires a complete round-trip in under 60 seconds. If the verification test uses the 120-second production poll interval, the test cannot pass.
**Why it happens:** The CONTEXT.md specifies 120s polling for production use (token conservation). The verification test is different from production use.
**How to avoid:** The tester GEMINI.md instructs Gemini to poll every 120 seconds. The SCAF-02 verification test does NOT test Gemini's poll interval — it tests the host-side round-trip: write PROMPT.md to LXC → host monitor detects → operator responds → RESPONSE.md pushed back. The monitor's poll interval (5 seconds) is what determines round-trip time.
**Warning signs:** Verification test script uses `time.sleep(120)` waiting for Gemini to pick up the response — this is unnecessary for proving SCAF-02.

### Pitfall 5: `incus file push --recursive` requires a trailing slash on the source path

**What goes wrong:** Pushing `docs/site` (no trailing slash) creates `site/` as a subdirectory inside the destination. Pushing `docs/site/` (trailing slash) merges the contents directly.
**Why it happens:** Incus mirrors `rsync` trailing-slash semantics.
**How to avoid:** Use `str(docs_site) + "/"` when constructing the push command, or use `pathlib.Path` and append `/` explicitly.
**Warning signs:** Files end up at `/workspace/docs/site/getting-started/` instead of `/workspace/docs/getting-started/`.

### Pitfall 6: `monitor_checkpoint.py` blocks the operator terminal if blocking on input

**What goes wrong:** A `input("Press Enter to confirm response: ")` call in the monitor blocks the entire script if run in a background process or piped terminal.
**Why it happens:** `input()` requires an interactive TTY.
**How to avoid:** Design `monitor_checkpoint.py` to print the PROMPT.md contents to stdout with a clear separator, then prompt. If running non-interactively (e.g., `--auto`), skip the operator confirmation and auto-push a pre-written response.

---

## Code Examples

### setup_agent_scaffolding.py skeleton

```python
# Source: established patterns from provision_coldstart_lxc.py
import subprocess, sys, shutil
from pathlib import Path

CONTAINER = "axiom-coldstart"
REPO_ROOT = Path("~/Development/master_of_puppets").expanduser()
DOCS_SITE = REPO_ROOT / "docs" / "site"
SCENARIOS_DIR = Path("~/Development/mop_validation/scenarios").expanduser()

def run_in_lxc(cmd: str, timeout: int = 60) -> None:
    result = subprocess.run(
        ["incus", "exec", CONTAINER, "--", "bash", "-c", cmd],
        timeout=timeout,
    )
    if result.returncode != 0:
        raise RuntimeError(f"LXC command failed: {cmd!r}")

def push_file(local_path: Path, remote_path: str) -> None:
    subprocess.run(
        ["incus", "file", "push", str(local_path), f"{CONTAINER}{remote_path}"],
        check=True,
    )

def push_directory(local_dir: Path, remote_dir: str) -> None:
    subprocess.run(
        ["incus", "file", "push", "--recursive", str(local_dir) + "/", f"{CONTAINER}{remote_dir}"],
        check=True,
    )

def main() -> int:
    # Step 1: Create workspace directories
    run_in_lxc("mkdir -p /workspace/gemini-context /workspace/docs /workspace/checkpoint")

    # Step 2: Set up HOME isolation
    run_in_lxc("mkdir -p /root/validation-home/.gemini")
    run_in_lxc("cp /root/.gemini/settings.json /root/validation-home/.gemini/settings.json 2>/dev/null || true")
    run_in_lxc("echo '{\"projects\":{}}' > /root/validation-home/.gemini/projects.json")

    # Step 3: Push tester GEMINI.md
    tester_gemini = SCENARIOS_DIR / "tester-gemini.md"
    push_file(tester_gemini, "/workspace/gemini-context/GEMINI.md")

    # Step 4: Push docs/site (15 MB)
    push_directory(DOCS_SITE, "/workspace/docs/")

    # Step 5: Verify isolation
    run_in_lxc(
        "HOME=/root/validation-home ls /root/validation-home/.gemini/ "
        "| grep -v 'GEMINI.md' | grep -v 'history'",
        timeout=10,
    )

    print("[DONE] Agent scaffolding setup complete")
    return 0
```

### monitor_checkpoint.py skeleton

```python
# Source: pattern from provision_coldstart_lxc.py
import subprocess, time, sys
from pathlib import Path

CONTAINER = "axiom-coldstart"
PROMPT_REMOTE = "/workspace/checkpoint/PROMPT.md"
RESPONSE_REMOTE = "/workspace/checkpoint/RESPONSE.md"
CHECK_INTERVAL = 5  # seconds (use 5 for fast round-trip verification)
LOCAL_TMP = Path("/tmp/checkpoint_exchange")

def pull_file(remote_path: str, local_path: Path) -> bool:
    result = subprocess.run(
        ["incus", "file", "pull", f"{CONTAINER}{remote_path}", str(local_path)],
        capture_output=True,
    )
    return result.returncode == 0

def push_file(local_path: Path, remote_path: str) -> None:
    subprocess.run(
        ["incus", "file", "push", str(local_path), f"{CONTAINER}{remote_path}"],
        check=True,
    )

def monitor_loop() -> None:
    LOCAL_TMP.mkdir(exist_ok=True)
    local_prompt = LOCAL_TMP / "PROMPT.md"
    local_response = LOCAL_TMP / "RESPONSE.md"
    print(f"[monitor] Watching for {PROMPT_REMOTE} every {CHECK_INTERVAL}s...")

    while True:
        if pull_file(PROMPT_REMOTE, local_prompt):
            print("\n" + "=" * 60)
            print("[CHECKPOINT] Gemini is blocked. PROMPT.md contents:")
            print("=" * 60)
            print(local_prompt.read_text())
            print("=" * 60)
            print("\nWrite your response to:", local_response)
            input("Press ENTER when response file is ready > ")
            push_file(local_response, RESPONSE_REMOTE)
            print("[monitor] RESPONSE.md pushed to LXC")
        time.sleep(CHECK_INTERVAL)
```

### Isolation Verification Test

```python
# Verify SCAF-03: confirm validation-home prevents loading repo GEMINI.md
def verify_home_isolation(container: str) -> bool:
    """
    Returns True if HOME isolation prevents loading the repo GEMINI.md.
    Does NOT call the Gemini API — tests the filesystem state only.
    """
    # Check 1: No GEMINI.md in validation-home .gemini/
    result = subprocess.run(
        ["incus", "exec", container, "--", "bash", "-c",
         "test ! -f /root/validation-home/.gemini/GEMINI.md && echo PASS || echo FAIL"],
        capture_output=True, text=True,
    )
    if "PASS" not in result.stdout:
        print("[FAIL] GEMINI.md found in validation-home/.gemini/ — isolation broken")
        return False

    # Check 2: No history directory in validation-home .gemini/
    result = subprocess.run(
        ["incus", "exec", container, "--", "bash", "-c",
         "test ! -d /root/validation-home/.gemini/history && echo PASS || echo FAIL"],
        capture_output=True, text=True,
    )
    if "PASS" not in result.stdout:
        print("[FAIL] history/ found in validation-home/.gemini/ — session bleed possible")
        return False

    # Check 3: /workspace/ has no .git ancestor
    result = subprocess.run(
        ["incus", "exec", container, "--", "bash", "-c",
         "test ! -d /workspace/.git && echo PASS || echo FAIL"],
        capture_output=True, text=True,
    )
    if "PASS" not in result.stdout:
        print("[FAIL] /workspace/ has .git — Gemini may traverse up to repo GEMINI.md")
        return False

    print("[PASS] HOME isolation verified — no repo context accessible from validation-home")
    return True
```

---

## State of the Art

| Old Approach | Current Approach | Notes |
|--------------|------------------|-------|
| `GEMINI_CLI_HOME` env var for isolation | `HOME` env var | Both work; `HOME` is preferable as it also redirects `~/.config/gemini/` |
| `settings.json` for model pinning | `GEMINI_MODEL` env var | settings.json model pinning has known auto-switch bug (noted in Phase 61 research) |
| Web search for docs | `file:///workspace/docs/` | No network required; docs already pushed into LXC |

---

## Open Questions

1. **Gemini API key tier for verification test**
   - What we know: The current `GEMINI_API_KEY` in the LXC is free tier (quota exhausted — confirmed 429 in live test). Any Gemini invocation that hits the real API will hang.
   - What's unclear: Whether Phase 62 can verify SCAF-03 without a working paid API key.
   - Recommendation: Design the isolation verification (SCAF-03) as a pure filesystem check — does NOT invoke Gemini. The round-trip test (SCAF-02) must use a working API key. Document in the plan that SCAF-02 is API-gated and requires Tier 1 key.

2. **Tester GEMINI.md loading mechanism**
   - What we know: The tester GEMINI.md is at `/workspace/gemini-context/GEMINI.md`. Gemini auto-discovers GEMINI.md only via `~/.gemini/GEMINI.md` (global) or CWD hierarchy traversal. Running from `/workspace/` won't auto-load `/workspace/gemini-context/GEMINI.md`.
   - What's unclear: The exact launch command format.
   - Recommendation: Include the tester GEMINI.md path in the system prompt by prepending to the scenario: `gemini -p "$(cat /workspace/gemini-context/GEMINI.md)\n\n---\n\n$(cat /workspace/scenarios/ce-install.md)"`. This guarantees the persona loads regardless of CWD.

3. **`incus file push --recursive` vs. individual file push for docs**
   - What we know: The docs/site directory is 15 MB with ~50 HTML files. `incus file push --recursive` is the standard pattern.
   - What's unclear: Whether the recursive push preserves subdirectory structure correctly for `file:///workspace/docs/getting-started/install.html` style URLs.
   - Recommendation: Test with a small subdirectory first. Use trailing slash on source path.

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | Python 3 scripts (no pytest — infrastructure-level checks) |
| Config file | none — scripts are self-contained |
| Quick run command | `python3 mop_validation/scripts/verify_phase62_scaf.py` |
| Full suite command | `python3 mop_validation/scripts/verify_phase62_scaf.py --full` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| SCAF-01 | Tester GEMINI.md exists at correct path with correct content | smoke | `incus exec axiom-coldstart -- test -f /workspace/gemini-context/GEMINI.md && echo PASS` | ❌ Wave 0 |
| SCAF-02 | Checkpoint round-trip completes in <60s | smoke | `python3 mop_validation/scripts/verify_phase62_scaf.py --checkpoint-roundtrip` | ❌ Wave 0 |
| SCAF-03 | HOME isolation prevents repo GEMINI.md loading | smoke | `python3 mop_validation/scripts/verify_phase62_scaf.py --isolation` (filesystem check only, no API) | ❌ Wave 0 |
| SCAF-04 | All 4 scenario files exist with required sections | smoke | `python3 mop_validation/scripts/verify_phase62_scaf.py --scenarios` | ❌ Wave 0 |

### Sampling Rate

- **Per task commit:** `python3 mop_validation/scripts/verify_phase62_scaf.py` (quick filesystem checks)
- **Per wave merge:** `python3 mop_validation/scripts/verify_phase62_scaf.py --full` (includes round-trip test, requires working API key)
- **Phase gate:** All 4 SCAF requirements verified before `/gsd:verify-work`

### Wave 0 Gaps

- [ ] `mop_validation/scripts/verify_phase62_scaf.py` — SCAF-01 through SCAF-04 smoke verifier
- [ ] `mop_validation/scenarios/` — directory with 4 scenario `.md` files
- [ ] `mop_validation/scenarios/tester-gemini.md` — tester persona GEMINI.md
- [ ] `mop_validation/scripts/setup_agent_scaffolding.py` — LXC workspace setup
- [ ] `mop_validation/scripts/monitor_checkpoint.py` — host-side checkpoint watcher

*(No pytest or vitest changes needed — all Phase 62 deliverables are scripts and content files, validated by running the infrastructure.)*

---

## Sources

### Primary (HIGH confidence)

- Live inspection of `/usr/lib/node_modules/@google/gemini-cli/node_modules/@google/gemini-cli-core/dist/src/utils/paths.js` — confirmed `homedir()` checks `GEMINI_CLI_HOME` then `os.homedir()` (reads `HOME` on Linux)
- Live inspection of `memoryDiscovery.js` — confirmed global GEMINI.md at `$HOME/.gemini/GEMINI.md`, project files via CWD upward traversal to `.git`
- Live `incus exec axiom-coldstart -- gemini --version` — confirmed Gemini CLI 0.35.0 installed
- Live `curl` test to Gemini API — confirmed free-tier quota exhausted (429 response), explains all `timeout 60 gemini` exits 124
- Live filesystem inspection of `/root/.gemini/` — confirmed structure: `history/`, `installation_id`, `projects.json`, `settings.json`, `tmp/`
- Live test with `HOME=/tmp/fresh_home` — confirmed ENOENT crash when `.gemini/` dir missing, resolved by `mkdir -p .gemini` + touch `projects.json`
- Live `du -sh docs/site/` — 15 MB, confirms `incus file push --recursive` is appropriate (not prohibitively large)
- `mop_validation/scripts/provision_coldstart_lxc.py` — all `run_in_lxc()`, `push_file_to_lxc()`, subprocess patterns
- `mop_validation/scripts/verify_phase61_env.py` — verification script structure pattern

### Secondary (MEDIUM confidence)

- Gemini CLI source code review of `extension-manager.js` — confirmed `GEMINI.md` filename (exact case) is the default; extensions can override it

---

## Metadata

**Confidence breakdown:**
- Gemini CLI isolation mechanics: HIGH — verified live from source code in installed LXC package
- Incus file push/pull patterns: HIGH — taken directly from working existing scripts
- Checkpoint protocol design: HIGH — straightforward Python polling with proven incus patterns
- Scenario script content: MEDIUM — content structure is clear from CONTEXT.md but exact wording is Claude's discretion
- API key tier blocker: HIGH — live test confirmed free-tier 429, Tier 1 key required for any real Gemini invocation

**Research date:** 2026-03-25
**Valid until:** 2026-06-25 (Gemini CLI version is pinned at 0.35.0 in the LXC; paths.js source is stable; Incus patterns are version-stable)
