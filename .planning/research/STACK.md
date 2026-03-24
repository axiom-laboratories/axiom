# Stack Research

**Domain:** Axiom v14.0 — CE/EE Cold-Start Validation Framework (addendum to v11.1 stack)
**Researched:** 2026-03-24
**Confidence:** HIGH (Gemini CLI install/config verified via official docs; PowerShell confirmed via Microsoft Learn + Containerfile.node source review; Playwright version confirmed via PyPI; existing stack from v11.1 STACK.md remains valid)

---

## Scope

This addendum covers ONLY the net-new tooling for v14.0 CE/EE Cold-Start Validation.
The existing validated stack (Incus 6.22, cryptography 46.0.5, Docker 29.2.1, Python Playwright
with --no-sandbox, Ed25519 signing, LXC provisioning via manage-test-nodes) is NOT re-researched.
See the v11.1 STACK.md entry for the base stack.

---

## Pre-Assessment: What Already Exists

| Requirement | Current State |
|-------------|---------------|
| Incus LXC provisioning | `.agent/skills/manage-test-nodes/scripts/manage_node.py` — functional single-node Ubuntu 24.04 provisioner |
| Python Playwright | Already used in `mop_validation/scripts/test_playwright.py` with `--no-sandbox` and JWT-via-localStorage pattern |
| Ed25519 licence signing | `admin_signer.py`, `generate_test_licence.py` — fully operational from v11.1 |
| CE/EE teardown + install scripts | `mop_validation/scripts/fresh_install.py` — from v11.1 |
| LXC 4-node provisioner | `mop_validation/scripts/provision_test_nodes.py` — from v11.1 |
| PowerShell in node image | `puppets/Containerfile.node` — already attempts `apt-get install -y powershell` via `packages.microsoft.com/config/debian/12/packages-microsoft-prod.deb` with silent fallback |
| Gemini CLI | NOT YET INSTALLED in LXC containers — new for v14.0 |
| File-based checkpoint protocol | NOT YET BUILT — new for v14.0 |

**Conclusion:** v14.0 net-new requirements are:
1. Gemini CLI headless install in Ubuntu 24.04 LXC
2. Model pinning to `gemini-2.0-flash` via env var or config file
3. GEMINI.md constraint file for docs-only access
4. File-based checkpoint steering protocol (plain Python + JSON files)
5. PowerShell fix: switch Containerfile.node from Debian 12 repo to Ubuntu 24.04 repo

---

## Recommended Stack — New Additions for v14.0

### Core Technologies

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| Gemini CLI | latest stable (`npm install -g @google/gemini-cli`) | Headless AI agent inside LXC containers to simulate first-time operator | Official Google CLI; GEMINI_API_KEY env var provides zero-interaction auth; `--prompt` flag enables headless mode; `GEMINI_MODEL` env var pins model; no browser required |
| Node.js | 20.x (LTS) | Runtime requirement for Gemini CLI | Gemini CLI requires Node.js 20.0.0+; Ubuntu 24.04 ships Node.js 18 which is below the minimum; use NodeSource PPA for the correct version |
| Python Playwright | 1.58.0 (`pip install playwright`) | UI smoke tests from validation orchestrator | Already proven working in project (--no-sandbox, JWT via localStorage, form-encoded login — all solved); v1.58.0 is current stable as of 2026-01-30 |
| PowerShell 7.6 | 7.6.0 (via `packages.microsoft.com/config/ubuntu/24.04/packages-microsoft-prod.deb`) | PowerShell job runtime inside node's JOB_IMAGE container | Current LTS; Containerfile.node uses Debian 12 repo which rejects SHA1 keys — switch to Ubuntu 24.04 repo eliminates the silent-fallback issue; `pwsh` already wired in `node.py` RUNTIME_CMD |

### Supporting Libraries

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `json` (stdlib) | Python stdlib | Checkpoint file serialization: write/read `checkpoint.json` for orchestrator-to-agent steering | All checkpoint read/write in the validation harness |
| `pathlib` (stdlib) | Python stdlib | Filesystem checkpoint path management; `.exists()` polling loop without external deps | Preferred over `os.path` for legibility; already used in other project scripts |
| `time` (stdlib) | Python stdlib | Polling loop for checkpoint file arrival (1s sleep between polls) | Checkpoint wait loop in the validation harness |
| `subprocess` (stdlib) | Python stdlib | Shell out to `gemini --prompt` in headless mode from the orchestrator script | Same pattern as existing Incus/Docker exec calls in provision scripts |

### Development Tools

| Tool | Purpose | Notes |
|------|---------|-------|
| `GEMINI_API_KEY` env var | Non-interactive auth for Gemini CLI inside LXC | Set via `incus exec <node> -- env GEMINI_API_KEY=... gemini --prompt "..."` or inject into node's shell profile; avoids OAuth browser flow entirely |
| `GEMINI_MODEL` env var | Pin model to `gemini-2.0-flash` | Set alongside `GEMINI_API_KEY`; overrides the default model (which may auto-upgrade to Flash or Pro depending on quota); precedence order: CLI arg > env var > config file > default |
| `.gemini/settings.json` (project) | Alternative model pin (persistent across all gemini invocations in the project) | Format: `{"model": {"name": "gemini-2.0-flash"}}`; lives at `.gemini/settings.json` in the working directory; loaded automatically |
| `GEMINI.md` (project root) | Constrain Gemini agent to docs-only behavior | Place in LXC working directory; instructs the agent to act as a first-time user consulting only the Axiom docs site; do not add tool restrictions that block filesystem reads (needed for checkpoint reading) |

---

## Installation

### Gemini CLI in Ubuntu 24.04 LXC

```bash
# Step 1: Install Node.js 20.x (Ubuntu 24.04 ships 18, below Gemini CLI minimum)
curl -fsSL https://deb.nodesource.com/setup_20.x | bash -
apt-get install -y nodejs

# Verify: node --version should be 20.x
# npm comes bundled with Node.js 20.x

# Step 2: Install Gemini CLI globally
npm install -g @google/gemini-cli

# Step 3: Verify headless mode works
GEMINI_API_KEY="<key>" GEMINI_MODEL="gemini-2.0-flash" gemini --prompt "Say hello"
```

Run these steps via `incus exec <container> -- bash -c "..."` from the provisioner script.

### PowerShell in Containerfile.node (Fix)

Replace the existing Debian 12 repo block with the Ubuntu 24.04 repo:

```dockerfile
# Current (broken — SHA1 key rejected on Debian 12 base):
RUN wget -q "https://packages.microsoft.com/config/debian/12/packages-microsoft-prod.deb" \
    && dpkg -i packages-microsoft-prod.deb && apt-get install -y powershell \
    || echo "PowerShell install skipped"

# Fixed (Ubuntu 24.04 repo — no SHA1 issue; image is python:3.12-slim which is Debian-based):
# NOTE: python:3.12-slim is Debian 12, not Ubuntu. For the Ubuntu path use ubuntu:24.04 base.
# Recommended: use the .deb direct download method (version-pinned, no repo key dependency):
RUN wget -q "https://github.com/PowerShell/PowerShell/releases/download/v7.6.0/powershell_7.6.0-1.deb_amd64.deb" \
    && dpkg -i powershell_7.6.0-1.deb_amd64.deb \
    && apt-get install -f -y \
    && rm -f powershell_7.6.0-1.deb_amd64.deb
```

The direct `.deb` download from GitHub releases is the most reliable method regardless of base OS (works on both Debian 12 and Ubuntu 24.04 derived images). No repo key issues. Version-pinned.

### Playwright in Headless LXC (already solved pattern)

```bash
# Inside LXC (Ubuntu 24.04) — run from provisioner via incus exec
pip install playwright==1.58.0
playwright install chromium --with-deps

# --with-deps handles all Ubuntu 24.04 system dependencies in one step
# Chromium bundled binary is used (not system Chrome)
```

The `--with-deps` flag is the canonical single-command approach for Ubuntu 24.04 — it runs `apt-get` internally to install all required system libraries. This is already solved and working from v11.1 testing.

---

## Gemini CLI Configuration Details

### Model Pinning

Use `GEMINI_MODEL` env var. This is the simplest and most reliable method for scripted invocations:

```bash
export GEMINI_API_KEY="<key_from_aistudio.google.com>"
export GEMINI_MODEL="gemini-2.0-flash"
gemini --prompt "Your question here"
```

Configuration precedence (highest wins): CLI `--model` flag > env var `GEMINI_MODEL` > project `.gemini/settings.json` > user `~/.gemini/settings.json` > default.

For persistent configuration inside the LXC container's working directory, use `.gemini/settings.json`:

```json
{
  "model": {
    "name": "gemini-2.0-flash"
  }
}
```

### GEMINI.md Constraint File

Place a `GEMINI.md` in the LXC container's working directory (loaded as project context for all sessions):

```markdown
# Axiom Cold-Start Validation Agent

You are a first-time user of Axiom, an open-source job scheduler.
Your goal is to follow the getting-started documentation at http://<docs_url>/docs/
and attempt to: install the stack, enroll a node, and run a job.

Constraints:
- Only consult the Axiom documentation. Do not use prior knowledge about Axiom internals.
- Report every step you take and every error you encounter.
- Write findings to checkpoint.json in the working directory after each major step.
- Do not modify any source code files.
```

GEMINI.md is loaded hierarchically: `~/.gemini/GEMINI.md` (global), then project root `GEMINI.md`. The project file overrides for per-container scope.

### Headless Mode Invocation

```bash
# Non-interactive prompt (exits after response):
gemini --prompt "Follow the Axiom getting started guide and report what you did"

# Pipe from file (for multi-step prompts):
cat prompt.txt | gemini

# With output to file for checkpoint processing:
gemini --prompt "..." > output.txt 2>&1
```

Headless mode is triggered when `--prompt` / `-p` is provided OR when stdin is not a TTY. Both cases return output to stdout and exit cleanly — suitable for scripted invocation from the validation orchestrator.

---

## File-Based Checkpoint Protocol

No external framework needed. Use plain JSON files on a shared path (host filesystem mounted into LXC via `incus file push` / `incus file pull`, or via SSH + SCP):

```
checkpoint.json         # Written by Gemini agent; read by orchestrator
steering.json           # Written by orchestrator; read by Gemini agent in next prompt
result.json             # Final report written by Gemini agent
```

### Pattern

```python
# Orchestrator side (Python):
import json, time, pathlib

checkpoint_path = pathlib.Path("/tmp/axiom_validation/checkpoint.json")
timeout = 300  # 5 minutes

# Poll for checkpoint
for _ in range(timeout):
    if checkpoint_path.exists():
        data = json.loads(checkpoint_path.read_text())
        if data.get("status") in ("completed", "blocked", "error"):
            break
    time.sleep(1)
```

```bash
# Gemini agent invocation (from orchestrator via subprocess):
gemini --prompt "$(cat prompt.txt)" > /tmp/axiom_validation/output.txt
# After: parse output.txt and write checkpoint.json
```

The orchestrator drives the conversation loop: write a prompt file, invoke `gemini --prompt`, parse the output, write a steering file, repeat. No persistent Gemini session state is required — each `--prompt` invocation is stateless from the CLI's perspective.

---

## Alternatives Considered

| Recommended | Alternative | Why Not |
|-------------|-------------|---------|
| `GEMINI_API_KEY` env var auth | OAuth browser flow | Browser flow requires interactive terminal + browser redirect — impossible inside headless LXC. API key is zero-interaction. |
| `GEMINI_MODEL` env var for model pin | `--model` flag on each invocation | Env var is inherited by all child processes and subshells; less error-prone than repeating a flag. Both work; env var is cleaner for scripted use. |
| Direct `.deb` download for PowerShell | Microsoft APT repo (`packages-microsoft-prod.deb`) | The existing Containerfile.node already shows the APT repo fails silently due to SHA1 key rejection on Debian 12. Direct `.deb` download bypasses the key entirely and is version-pinned. |
| `playwright install --with-deps` | Manual `apt-get install` of individual libraries | `--with-deps` is the Playwright-maintained single-command solution that tracks the correct library list for each Ubuntu version. Manual installs drift. |
| File-based checkpoints (plain JSON) | MCP server / HTTP API between orchestrator and Gemini | Gemini CLI does not have a built-in server mode; adding an HTTP layer introduces unnecessary complexity for a sequential validation workflow. |
| NodeSource PPA for Node.js 20 | `nvm install 20` | `nvm` requires shell sourcing (`.bashrc`) which is not reliable in non-interactive `incus exec` invocations. NodeSource PPA installs via `apt-get` and is available to all users and shells immediately. |

## What NOT to Use

| Avoid | Why | Use Instead |
|-------|-----|-------------|
| `gemini` without `GEMINI_MODEL` set | Default model may auto-switch between Flash and Pro based on quota; model switching mid-run is documented as an active bug (GitHub issue #3485) | Always set `GEMINI_MODEL=gemini-2.0-flash` explicitly for reproducible behaviour |
| OAuth / Google account login in LXC | Requires browser redirect; blocks headless operation permanently | `GEMINI_API_KEY` from aistudio.google.com — free tier allows 1000 requests/day |
| `npm run dev` / Vite dev server for Playwright UI tests | Documented in CLAUDE.md as explicitly forbidden; never use local dev servers for verification | Rebuild and test inside Docker stack containers |
| `EXECUTION_MODE=direct` in node.py | Node.py now raises `RuntimeError` at startup if `EXECUTION_MODE=direct` (removed in v12.0+) | Use `EXECUTION_MODE=docker` or `EXECUTION_MODE=podman`; for LXC test nodes use Docker-in-LXC with nested container support (`security.nesting=true`) |
| Gemini CLI interactive mode (no `--prompt`) for validation | Interactive mode blocks the script waiting for user TTY input; validation harness must be fully automated | Always use `gemini --prompt "..."` or piped stdin |
| `incus launch` in parallel threads for Gemini nodes | Same pitfall as v11.1: bridge IP assignment races; launch sequentially | Sequential `for` loop for launch; parallel for configuration steps after all containers are running |

---

## Stack Patterns by Variant

**If running CE cold-start validation (Gemini agent as first-time user):**
- Provision one LXC container with Gemini CLI + Node.js 20 + Python Playwright
- Set `GEMINI_API_KEY` + `GEMINI_MODEL=gemini-2.0-flash`
- Place `GEMINI.md` in container's working directory constraining agent to Axiom docs only
- Orchestrator invokes `gemini --prompt` in a loop; reads checkpoint.json after each step
- Playwright tests verify the UI state after Gemini completes each operator action

**If running EE cold-start validation (with pre-generated licence):**
- Same container setup as CE
- Pass `AXIOM_LICENCE_KEY` into the Axiom stack's `.env` before container start
- Gemini agent prompt includes instruction to verify EE features via the docs
- Checkpoint protocol is identical — same file paths, same orchestrator loop

**If PowerShell job runtime fails in cold-start test:**
- Root cause is likely the Containerfile.node Debian 12 repo key issue
- Fix: rebuild `localhost/master-of-puppets-node:latest` after switching to direct `.deb` install
- Verify: `docker run --rm localhost/master-of-puppets-node:latest pwsh -Version`
- Expected output: `PowerShell 7.6.0`

---

## Version Compatibility

| Package | Version | Notes |
|---------|---------|-------|
| Gemini CLI | latest (weekly stable) | No pinned version — `npm install -g @google/gemini-cli` always pulls latest stable |
| Node.js | 20.x LTS | Minimum for Gemini CLI; install via NodeSource `setup_20.x` PPA in LXC |
| Python Playwright | 1.58.0 | Current stable as of 2026-01-30; Python 3.9+ required; use `pip install playwright==1.58.0` to pin |
| PowerShell | 7.6.0 | Current LTS; direct `.deb` from GitHub releases; installs to `/opt/microsoft/powershell/7/`; binary: `pwsh` |
| GEMINI_MODEL value | `gemini-2.0-flash` | Stable Flash model; pinning prevents automatic upgrade to 2.5-pro which has different rate limits and cost profile |

---

## Sources

- [Gemini CLI official docs — headless mode](https://google-gemini.github.io/gemini-cli/docs/cli/headless.html) — `--prompt` flag, headless trigger conditions (HIGH confidence)
- [Gemini CLI official docs — configuration](https://google-gemini.github.io/gemini-cli/docs/get-started/configuration.html) — `settings.json` format, `GEMINI_MODEL` env var, config precedence (HIGH confidence)
- [Gemini CLI official docs — GEMINI.md](https://google-gemini.github.io/gemini-cli/docs/cli/gemini-md.html) — context file location, hierarchy, constraint mechanism (HIGH confidence)
- [Gemini CLI installation docs](https://geminicli.com/docs/get-started/installation/) — Node.js 20.0.0+ minimum requirement, `npm install -g @google/gemini-cli` (HIGH confidence)
- [Microsoft Learn — Install PowerShell 7 on Ubuntu](https://learn.microsoft.com/en-us/powershell/scripting/install/install-ubuntu?view=powershell-7.5) — Direct `.deb` method, Ubuntu 24.04 support confirmed, version 7.6.0 current (HIGH confidence — Microsoft official docs, updated 2026-03-12)
- [PyPI — playwright](https://pypi.org/project/playwright/) — Version 1.58.0 confirmed current; Python 3.9+ requirement (HIGH confidence)
- [Playwright Python docs — intro](https://playwright.dev/python/docs/intro) — `playwright install --with-deps` for Ubuntu 24.04 system deps (HIGH confidence)
- `puppets/Containerfile.node` — reviewed directly; PowerShell Debian 12 fallback pattern documented; `python:3.12-slim` base confirmed (HIGH confidence — local source)
- `puppets/environment_service/node.py` — reviewed directly; `RUNTIME_CMD["powershell"]` uses `["pwsh", p]`; `JOB_IMAGE` default is `localhost/master-of-puppets-node:latest` (HIGH confidence — local source)
- GitHub issue `google-gemini/gemini-cli #3485` — model auto-switching bug with `.env` settings; confirms `GEMINI_MODEL` env var is the reliable pin method (MEDIUM confidence — issue thread, not release note)

---

*Stack research for: Axiom v14.0 — CE/EE Cold-Start Validation (Gemini CLI headless, model pinning, PowerShell fix, Playwright in LXC, file-based checkpoints)*
*Researched: 2026-03-24*
