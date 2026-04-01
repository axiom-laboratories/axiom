# Phase 102: Linux E2E Validation - Research

**Researched:** 2026-03-31
**Domain:** E2E validation orchestration — LXC provisioning, cold-start Docker stack, docs-driven test agent, friction cataloguing
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Validation method:**
- A Claude subagent runs the validation (not Gemini — lower overhead, paid tier already available)
- Persona: pure docs-follower — no prior Axiom knowledge; if the docs don't say it, the agent doesn't do it
- Scope: full golden path only — Install → login (forced password change) → enroll node → dispatch first job (Python) → verify output in dashboard
- Blocker handling: agent stops at the first blocker, reports what it found; orchestrator fixes it, then re-runs from the top (full restart, not resume)
- Phase iterates until the golden path completes end-to-end with no friction

**LXC environment:**
- Start from a fresh provision of `axiom-coldstart` — delete and reprovision via `provision_coldstart_lxc.py` before each run
- Stack: `compose.cold-start.yaml` (the file the Quick Start guide tells new users to pull)
- Internet access: live during the run — Docker pulls images from registry at runtime (accurate to real new-user experience)

**Fix strategy:**
- Scope: fix whatever caused the friction — docs AND code/config, whichever applies
- After each fix, full restart: reprovision LXC and run the golden path from the top
- No fixed cap on iterations — phase is done when the golden path completes cleanly end-to-end

**Report format:**
- Match v14.0 FRICTION file format (synthesise_friction.py compatible)
- File: `mop_validation/reports/FRICTION-LNX-102.md` (one file covering the Linux run)
- At phase close: run `synthesise_friction.py` to produce a synthesised summary as the sign-off artifact

### Claude's Discretion
- Exact structure of the validation subagent prompt / persona setup
- How to pass the LXC container name and workspace paths to the subagent
- Whether to use Playwright or API calls to verify dashboard states (e.g., node appears ONLINE, job shows COMPLETED)
- Structure of FRICTION-LNX-102.md within the v14.0 format constraints

### Deferred Ideas (OUT OF SCOPE)

None — discussion stayed within phase scope
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| LNX-01 | Fresh Linux cold-start deployment completes inside an LXC container without deviating from the Quick Start guide | Covered by: cold-start compose analysis, known blockers from v14.0, docs review |
| LNX-02 | Admin/admin first login triggers forced password change prompt, which completes successfully | Covered by: `must_change_password` mechanism in main.py + ForceChangeModal in frontend |
| LNX-03 | Node enrollment succeeds following the documentation steps | Covered by: enroll-node.md current state, AGENT_URL matrix, mTLS bootstrap analysis |
| LNX-04 | First job (Python or Bash) dispatches, executes, and shows output in the dashboard | Covered by: first-job.md analysis, Ed25519 signing path, guided dispatch form |
| LNX-05 | All documented CE features are accessible and functional from the dashboard | Covered by: Phase 101 completion (CE/EE tab gating), Admin.tsx CE tab analysis |
| LNX-06 | All friction found during the Linux run is catalogued and fixed | Covered by: FRICTION file format analysis, synthesise_friction.py compatibility research |
</phase_requirements>

---

## Summary

Phase 102 is a practical validation loop, not a feature implementation. The core pattern is: provision a clean LXC, instruct a Claude subagent to follow the published Quick Start docs from first principles, observe where it gets stuck, fix the underlying issue (docs or code), and restart the LXC loop until the golden path completes end-to-end with no friction.

The v14.0 run (March 2026) revealed 12 open product BLOCKERs. Several of those are already fixed in v18.0 of the codebase — the compose file now uses `admin/admin` defaults with no `.env` required, the docs have a working CLI path for JOIN_TOKEN generation, the node image in Option B is now correct (`localhost/master-of-puppets-node:latest`), `EXECUTION_MODE=direct` has been removed from docs, and the first-job.md has both CLI and dashboard paths with full signing instructions. What remains unknown is whether _all_ these fixes are properly reflected in the GHCR images that the cold-start compose pulls, and whether any new friction has been introduced since v14.0.

The plan must allocate: (1) a setup task that verifies the LXC and images are current, (2) a subagent validation task that runs the golden path, and (3) a friction fix task that is conditionally executed if blockers are found. The phase loops until clean.

**Primary recommendation:** Write a single tightly-scoped orchestrator script that provisions the LXC, runs the Claude docs-follower subagent, collects the FRICTION file, and fixes any blockers before rerunning — using the existing `run_ce_scenario.py` helper infrastructure but adapted for Claude (not Gemini) as the validation agent.

---

## Standard Stack

### Core Infrastructure
| Tool | Version | Purpose | Why Standard |
|------|---------|---------|--------------|
| Incus | host-installed | LXC container lifecycle | Already established by `provision_coldstart_lxc.py` |
| `provision_coldstart_lxc.py` | existing | Provision `axiom-coldstart` (Ubuntu 24.04, Docker-in-LXC, Node.js 20) | Reusable asset from prior sprint |
| `run_ce_scenario.py` | existing | `incus_exec`, `incus_push`, `incus_pull`, `wait_for_stack`, `reset_stack` helpers | Reusable asset from prior sprint |
| `synthesise_friction.py` | existing (needs patch) | Reads FRICTION files, produces summary report | Sign-off artifact per CONTEXT.md |
| Python Playwright | host-installed in LXC | Dashboard state verification (ONLINE node, COMPLETED job) | Per CLAUDE.md guidance |

### Compose and Images
| Asset | Location | Purpose |
|-------|----------|---------|
| `compose.cold-start.yaml` | `puppeteer/compose.cold-start.yaml` in repo | The cold-start stack under test |
| GHCR images | `ghcr.io/axiom-laboratories/axiom:latest`, `ghcr.io/axiom-laboratories/axiom-dashboard:latest`, etc. | Live-pulled from registry during LXC run |
| `localhost/master-of-puppets-node:latest` | Built on host, piped into LXC | Node agent image (DinD execution requires host build + reload) |

### Existing Docs Under Test
| Doc | Path | Golden Path Step |
|-----|------|-----------------|
| Install | `docs/docs/getting-started/install.md` | LNX-01: cold-start deploy |
| Enroll Node | `docs/docs/getting-started/enroll-node.md` | LNX-03: node enrollment |
| First Job | `docs/docs/getting-started/first-job.md` | LNX-04: job dispatch and output |

---

## Architecture Patterns

### Recommended Project Structure (for new scripts)

```
mop_validation/scripts/
├── run_linux_e2e.py           # Phase 102 orchestrator (new)
├── linux_validation_prompt.md # Subagent persona + golden path instructions (new)
├── provision_coldstart_lxc.py # Reuse as-is
└── run_ce_scenario.py         # Reuse helpers: incus_exec, incus_push, wait_for_stack

mop_validation/reports/
└── FRICTION-LNX-102.md        # Output from validation run (created by subagent or orchestrator)
```

### Pattern 1: LXC Reset Before Each Run

**What:** Before each golden path attempt, delete and reprovision the LXC to guarantee a truly clean state.

**When to use:** Every validation iteration — no exceptions. Resuming from a partially-configured LXC masks friction.

**How:**
```bash
# Delete existing container
python3 /home/thomas/Development/mop_validation/scripts/provision_coldstart_lxc.py --stop
# Reprovision fresh
python3 /home/thomas/Development/mop_validation/scripts/provision_coldstart_lxc.py
```

The provisioner installs: Docker CE, Node.js 20, Python/pip, Playwright, ripgrep.

**Important:** The LXC does NOT have the GHCR images cached after a fresh provision. The first `docker compose up -d` pulls from `ghcr.io` over live internet — this is intentional (accurate to real new-user experience per CONTEXT.md).

### Pattern 2: Claude Docs-Follower Subagent

**What:** A Claude subagent is spawned with a persona prompt that establishes it as a first-time user with no prior Axiom knowledge. It reads the published docs, executes only what the docs say, and writes a FRICTION file when it encounters a blocker or anomaly.

**When to use:** Every validation iteration. The subagent is the oracle — if it gets stuck, there is friction.

**Persona constraints to encode in the prompt:**
- "You are a first-time user with no prior knowledge of Axiom"
- "You may only run commands the documentation explicitly shows"
- "When you encounter a blocker, write it to `/workspace/FRICTION-LNX-102.md` in the v14.0 FRICTION format and stop"
- "Do not attempt workarounds — document what failed and why"
- "Dashboard is reachable at `https://172.17.0.1:8443` from inside the LXC"

**Subagent execution:** Invoked from the host via `incus exec axiom-coldstart` using the Claude CLI. The workspace at `/workspace/` inside the LXC contains the compose file and docs.

### Pattern 3: API-Level Dashboard Verification (Preferred Over Playwright)

**What:** Use `curl` API calls inside the LXC to verify state rather than Playwright for the structured golden path checks (node ONLINE, job COMPLETED).

**Why preferred:** Less brittle for a first-pass validation run. Playwright is available in the LXC (from provisioner) as a fallback for cases where only the UI surface exposes the needed state.

**API checks (all run inside LXC against `https://172.17.0.1:8001`):**
```bash
# Login
TOKEN=$(curl -sk -X POST https://172.17.0.1:8001/auth/login \
  -H 'Content-Type: application/x-www-form-urlencoded' \
  -d 'username=admin&password=<new-password>' \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")

# Verify node ONLINE
curl -sk -H "Authorization: Bearer $TOKEN" https://172.17.0.1:8001/nodes \
  | python3 -c "import sys,json; nodes=json.load(sys.stdin); print([n['status'] for n in nodes])"

# Verify job COMPLETED
curl -sk -H "Authorization: Bearer $TOKEN" https://172.17.0.1:8001/jobs/<job_id> \
  | python3 -c "import sys,json; j=json.load(sys.stdin); print(j['status'], j.get('output',''))"
```

**Playwright pattern** (when needed — must use `--no-sandbox`, JWT injection via localStorage per CLAUDE.md):
```python
# Source: CLAUDE.md project instructions
from playwright.sync_api import sync_playwright
with sync_playwright() as p:
    browser = p.chromium.launch(args=['--no-sandbox'], headless=True)
    page = browser.new_page()
    page.evaluate(f"localStorage.setItem('mop_auth_token', '{token}')")
    page.goto('https://172.17.0.1:8443/nodes')
    # ... assertions
```

### Pattern 4: FRICTION File Format (v14.0)

**What:** Structured markdown format consumed by `synthesise_friction.py`.

**Required structure per friction point:**
```markdown
### [Category] Title of finding

**Classification:** BLOCKER / NOTABLE / ROUGH EDGE / MINOR
**What happened:** One sentence summary.
**Why it happened:** Root cause.
**Fix applied:** What was changed, or "None — requires fix outside this run."
```

**Categories used in prior FRICTION files:** `[Setup]`, `[Install Step N]`, `[Enroll-Node Step N]`, `[Job Dispatch]`, `[Dashboard]`

**IMPORTANT — synthesise_friction.py compatibility:** The synthesiser (`synthesise_friction.py`) is hardcoded to read exactly 4 files: `FRICTION-CE-INSTALL.md`, `FRICTION-CE-OPERATOR.md`, `FRICTION-EE-INSTALL.md`, `FRICTION-EE-OPERATOR.md`. It will FAIL if invoked without those 4 files. Phase 102 only produces `FRICTION-LNX-102.md`. The plan MUST either:
- (a) Update `synthesise_friction.py` to accept a `--files` argument so it can process `FRICTION-LNX-102.md` alone, OR
- (b) Have the orchestrator produce the synthesis manually (count findings, list blockers, print verdict) without invoking `synthesise_friction.py`

**Recommended:** Option (a) — add a `--files` flag to `synthesise_friction.py` so it accepts an explicit list of FRICTION files to process. This generalises the tool for all future phase-specific runs.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| LXC container lifecycle | Custom incus wrapper | `provision_coldstart_lxc.py` (existing) | Already handles provision, Docker install, Playwright deps, idempotency |
| File push/pull to LXC | Raw subprocess calls | `incus_push` / `incus_pull` from `run_ce_scenario.py` | Tested, handles edge cases |
| Stack readiness polling | Custom wait loop | `wait_for_stack()` from `run_ce_scenario.py` | Polls `https://172.17.0.1:8443` with 600s timeout |
| Dashboard JWT auth in Playwright | Custom login form interaction | `localStorage.setItem('mop_auth_token', token)` per CLAUDE.md | React controlled inputs don't respond reliably to `fill()` |
| Node image rebuild and reload | Manual docker commands | `reload_node_image()` from `run_ce_scenario.py` | Handles host build + docker save + incus pipe + docker load |

**Key insight:** All heavy lifting infra already exists in `run_ce_scenario.py` and `provision_coldstart_lxc.py`. Phase 102 work is writing the orchestrator glue and the Claude persona prompt — not reinventing infrastructure.

---

## Common Pitfalls

### Pitfall 1: GHCR Images Not Available in LXC After Fresh Provision

**What goes wrong:** After `provision_coldstart_lxc.py` creates a fresh LXC, there are no Docker images cached. The compose file references `ghcr.io/axiom-laboratories/axiom:latest` etc. If `ghcr.io` is unreachable or the images haven't been published, `docker compose up -d` will fail silently.

**Why it happens:** The provisioner only installs Docker daemon, not images. CONTEXT.md says "Internet access: live during the run" — this is intentional, but requires `ghcr.io` to have the current images.

**How to avoid:** Before running the validation, verify that the GHCR images are published and reachable. The orchestrator should check `docker pull ghcr.io/axiom-laboratories/axiom:latest` succeeds before proceeding.

**Warning signs:** `compose up -d` takes unusually long (normal for first pull) or exits with `Unable to find image`.

### Pitfall 2: The LXC axiom-coldstart May Have Stale State from v14.0

**What goes wrong:** The LXC container exists and is running (confirmed by research). It contains old v14.0 compose files, old docker images with the `localhost/` prefix, and v14.0 FRICTION files. Running the new test against this stale LXC will give misleading results.

**Why it happens:** The provisioner's idempotency check skips provisioning if the container already exists. The `--stop` flag is needed to delete it first.

**How to avoid:** The orchestrator MUST run `provision_coldstart_lxc.py --stop` then `provision_coldstart_lxc.py` before the first validation run. Never reuse the existing container for Phase 102.

### Pitfall 3: `synthesise_friction.py` Will Fail on a Single LNX FRICTION File

**What goes wrong:** Calling `python3 synthesise_friction.py` after producing `FRICTION-LNX-102.md` will exit with `ERROR: Missing required FRICTION files` because it looks for all 4 CE/EE files.

**Why it happens:** The script is hardcoded with `REQUIRED_FILES = ["FRICTION-CE-INSTALL.md", ...]`.

**How to avoid:** Patch `synthesise_friction.py` to accept `--files FILE1 FILE2 ...` before the phase close step. This is a small, safe change (the parsing/rendering logic is file-agnostic once inputs are loaded).

### Pitfall 4: Node Enrollment Via `AGENT_URL: https://172.17.0.1:8001` — TLS SAN Mismatch

**What goes wrong:** This was a v14.0 blocker. The enroll-node.md now documents `https://agent:8001` for nodes in the same compose network (Option B) and the cold-start compose has the node in the same network as the agent service. If the validation subagent uses `172.17.0.1:8001` (the bridge IP), TLS verification fails.

**Current state:** The docs have been updated to show `https://agent:8001` as the AGENT_URL for cold-start compose. The fix is in the docs. The validation run will confirm whether this is sufficient.

**Warning signs:** Node logs show `[SSL: CERTIFICATE_VERIFY_FAILED]` or `certificate verify failed: IP address mismatch`.

### Pitfall 5: Job Signing — New Users Must Generate Keys Before Dispatch

**What goes wrong:** Job dispatch fails with 422 if no Ed25519 public key is registered. The first-job.md now documents Step 0 (generate keypair) and the Signatures dashboard step, but this is a multi-step prerequisite that's easy to miss.

**Current state:** `first-job.md` covers this in Step 0 and the Manual Setup section. The guided dashboard form requires selecting a registered key. The signing step uses `openssl pkeyutl` or the Python `cryptography` library.

**Warning signs:** Job dispatch returns 422 with `signature validation error`.

### Pitfall 6: Docker Socket Mounting for Node Job Execution

**What goes wrong:** With `EXECUTION_MODE=docker`, the node container spawns job containers via the Docker socket. If `/var/run/docker.sock` is not mounted in the node container, jobs fail at execution time (not enrollment time — enrollment succeeds but the first job hangs or fails).

**Current state:** The enroll-node.md Option B now includes `- /var/run/docker.sock:/var/run/docker.sock` in the volumes section. The cold-start compose includes the socket mount for node services. The validation confirms this is wired correctly.

---

## Code Examples

### Starting the Stack (from docs, Quick Start path)

```bash
# Source: docs/docs/getting-started/install.md (Quick Start tab)
docker compose -f compose.cold-start.yaml --env-file .env up -d
```

No `.env` required — stack starts with `admin/admin` by default. Optional `.env` to override password.

### CLI Path for JOIN_TOKEN Generation

```bash
# Source: docs/docs/getting-started/enroll-node.md (CLI tab)
TOKEN=$(curl -sk -X POST https://<your-orchestrator>:8001/auth/login \
  -H 'Content-Type: application/x-www-form-urlencoded' \
  -d 'username=admin&password=<your-password>' \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")

curl -sk -X POST https://<your-orchestrator>:8001/admin/generate-token \
  -H "Authorization: Bearer $TOKEN" \
  | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['token'])"
```

### Signing and Dispatching a Job (Manual Setup path)

```bash
# Source: docs/docs/getting-started/first-job.md (Manual Setup section)
openssl genpkey -algorithm ed25519 -out signing.key
openssl pkey -in signing.key -pubout -out verification.key

# Register verification.key in Signatures dashboard, note KEY_ID

SIG=$(openssl pkeyutl -sign -inkey signing.key -rawin -in hello.py | base64 -w0)
curl -sk -X POST https://<your-orchestrator>:8001/jobs \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{\"script_content\": \"...\", \"signature\": \"$SIG\", \"signature_key_id\": \"<key-id>\"}"
```

### Incus Exec Pattern (for orchestrator scripts)

```python
# Source: mop_validation/scripts/run_ce_scenario.py
import subprocess
result = subprocess.run(
    ["incus", "exec", "axiom-coldstart", "--", "bash", "-c", "your command here"],
    capture_output=True, text=True, timeout=30,
)
# result.returncode, result.stdout, result.stderr
```

---

## State of the Art

### What Has Changed Since v14.0 (issues confirmed fixed in current repo)

| v14.0 Blocker | Current State | Evidence |
|---------------|---------------|----------|
| Admin password undiscoverable | Fixed: `compose.cold-start.yaml` now defaults `ADMIN_PASSWORD=admin`; forced change on first login | `main.py` line 150-160: `using_default = admin_password == "admin"` → sets `must_change_password=True` |
| No CLI path for JOIN_TOKEN | Fixed: enroll-node.md now has a full CLI tab with `curl` commands | `enroll-node.md` lines 25-43 |
| Wrong node image in docs (python:3.12-alpine) | Fixed: Option B now shows `localhost/master-of-puppets-node:latest` | `enroll-node.md` line 103 |
| `EXECUTION_MODE=direct` in docs | Fixed: Option B now shows `EXECUTION_MODE: docker` with correct explanation | `enroll-node.md` line 106 |
| TLS cert mismatch on `172.17.0.1:8001` | Fixed in docs: Option B now shows `AGENT_URL: https://172.17.0.1:8001` but with cert warning removed; CLI enroll-node.md shows `https://agent:8001` for compose-network nodes | `enroll-node.md` Step 2 table |
| Docker CLI missing from node image | Fixed: `Containerfile.node` copies Docker CLI binary from `docker:cli` | `puppets/Containerfile.node` line 8 |
| PowerShell not in node image | Fixed: `Containerfile.node` now installs PowerShell 7.6.0 via direct .deb | `puppets/Containerfile.node` |
| Ed25519 signing path undocumented | Fixed: `first-job.md` Step 0 and Manual Setup cover full signing workflow | `first-job.md` throughout |
| Docs path mismatch (harness issue) | Fixed: `provision_coldstart_lxc.py` does not create broken symlinks; the Claude subagent uses the repo docs directly | `provision_coldstart_lxc.py` — docs path symlink logic removed |

### Key Concern: GHCR Image Currency

The `compose.cold-start.yaml` in the repo now references `ghcr.io/axiom-laboratories/axiom:latest` (agent), `ghcr.io/axiom-laboratories/axiom-dashboard:latest` (dashboard), `ghcr.io/axiom-laboratories/axiom-docs:latest` (docs), and `ghcr.io/axiom-laboratories/axiom-cert-manager:latest` (cert-manager). These images must be built and published to GHCR before the live internet pull during LXC validation. If the images are stale or unpublished, the validation will fail for infrastructure reasons, not user-experience reasons.

**Critical pre-validation check:** Confirm all 4 GHCR images are published and current before running the LXC validation.

---

## Open Questions

1. **Are GHCR images published?**
   - What we know: `compose.cold-start.yaml` references `ghcr.io/axiom-laboratories/*` images. The LXC currently has `localhost/master-of-puppets-*` images (old v14.0 prefix), not GHCR images.
   - What's unclear: Whether the GHCR images are published, and whether they contain all the v18.0 fixes.
   - Recommendation: The orchestrator plan's Wave 0 task should verify GHCR image availability. If images are not published, the plan must include a task to build and push them before the LXC run. This is the single highest-risk item for the phase.

2. **Does `https://agent:8001` AGENT_URL resolve from the node container in cold-start compose?**
   - What we know: `compose.cold-start.yaml` does not explicitly define a shared network between agent and node services. Docker Compose v3 creates a default network, which means service names resolve by default.
   - What's unclear: Whether the current `compose.cold-start.yaml` puts node services on the same Compose network as the agent service (it appears to based on the current file which has no explicit `networks:` block, so all services share the default network).
   - Recommendation: Verify the compose file has node services and the agent service on the same default Compose network (no `network_mode: host` overrides).

3. **Does `synthesise_friction.py` need to be patched before phase close?**
   - What we know: The script is hardcoded to 4 CE/EE FRICTION files. Phase 102 produces one LNX file.
   - What's unclear: Whether the user wants a full synthesis or just a standalone FRICTION file as the deliverable.
   - Recommendation: Patch `synthesise_friction.py` to accept `--files` so it can process `FRICTION-LNX-102.md`. This is a 10-line change to `check_inputs()` and `main()` and is safer than producing an ad-hoc synthesis.

---

## Validation Architecture

> `nyquist_validation` is `true` in `.planning/config.json` — this section is included.

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest (backend) + vitest (frontend) |
| Config file | `puppeteer/pytest.ini` (backend), `puppeteer/dashboard/vite.config.ts` (frontend) |
| Quick run command | `cd puppeteer && pytest tests/ -x -q` |
| Full suite command | `cd puppeteer && pytest && cd dashboard && npm run test` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| LNX-01 | Cold-start deploy completes via docs | integration / manual | `python3 mop_validation/scripts/run_linux_e2e.py` | ❌ Wave 0 |
| LNX-02 | admin/admin login triggers forced password change | integration / manual | subagent validation run | ❌ Wave 0 |
| LNX-03 | Node enrollment succeeds | integration / manual | subagent validation run | ❌ Wave 0 |
| LNX-04 | First Python job dispatches and completes | integration / manual | subagent validation run | ❌ Wave 0 |
| LNX-05 | All CE dashboard features accessible | integration / manual | subagent validation run | ❌ Wave 0 |
| LNX-06 | Friction catalogued and fixed | report artifact | `FRICTION-LNX-102.md` produced | ❌ Wave 0 |

**Note:** LNX-01 through LNX-06 are validated by the live E2E run in the LXC, not by unit or component tests. The "test" for this phase is the validation orchestrator script and the resulting FRICTION file. There are no backend unit tests to write — the phase is a live integration test.

### Sampling Rate
- **Per iteration:** Full LXC golden path run (`python3 mop_validation/scripts/run_linux_e2e.py`)
- **Per wave merge:** Full backend + frontend test suite green (regression protection)
- **Phase gate:** Golden path completes with zero BLOCKER friction points in `FRICTION-LNX-102.md`

### Wave 0 Gaps
- [ ] `mop_validation/scripts/run_linux_e2e.py` — Phase 102 orchestrator (new script)
- [ ] `mop_validation/scripts/linux_validation_prompt.md` — Claude subagent persona + golden path instructions
- [ ] Verify GHCR images are published for live pull — manual pre-flight check before first run
- [ ] `synthesise_friction.py` patch for `--files` argument — needed for phase close sign-off

---

## Sources

### Primary (HIGH confidence)
- `/home/thomas/Development/master_of_puppets/.planning/phases/102-linux-e2e-validation/102-CONTEXT.md` — locked decisions, reusable assets, integration points
- `/home/thomas/Development/mop_validation/scripts/provision_coldstart_lxc.py` — LXC provisioner, what gets installed, container name, commands
- `/home/thomas/Development/mop_validation/scripts/run_ce_scenario.py` — helper library, `incus_exec`, `wait_for_stack`, `reset_stack`, `reload_node_image`, `pull_friction`
- `/home/thomas/Development/mop_validation/scripts/synthesise_friction.py` — FRICTION format spec, `REQUIRED_FILES` hardcoding, `_classify`, `_parse_friction_file`
- `/home/thomas/Development/master_of_puppets/docs/docs/getting-started/install.md` — current Quick Start install docs
- `/home/thomas/Development/master_of_puppets/docs/docs/getting-started/enroll-node.md` — current enroll-node docs
- `/home/thomas/Development/master_of_puppets/docs/docs/getting-started/first-job.md` — current first-job docs
- `/home/thomas/Development/master_of_puppets/puppeteer/compose.cold-start.yaml` — current cold-start compose (GHCR images, admin/admin default)
- `/home/thomas/Development/master_of_puppets/puppeteer/agent_service/main.py` — forced password change logic, installer endpoints
- `/home/thomas/Development/master_of_puppets/puppets/Containerfile.node` — Docker CLI + PowerShell in node image

### Secondary (MEDIUM confidence)
- `/home/thomas/Development/mop_validation/reports/FRICTION-CE-INSTALL.md` — v14.0 blocker list, used to assess what has been fixed
- `/home/thomas/Development/mop_validation/reports/cold_start_friction_report.md` — v14.0 verdict summary, 12 open product BLOCKERs baseline
- Live incus state check: `axiom-coldstart` container exists and is Running, with stale v14.0 images (`localhost/master-of-puppets-server:v3`) — confirms must be reprovisioned

### Tertiary (LOW confidence)
- None for this domain — all findings are directly from local repository inspection

---

## Metadata

**Confidence breakdown:**
- Standard stack (infra): HIGH — all scripts and compose files read directly
- Architecture (loop pattern): HIGH — locked in CONTEXT.md, consistent with prior sprint patterns
- Pitfalls: HIGH — v14.0 blockers are documented; v18.0 fixes confirmed by code inspection
- GHCR image availability: LOW — cannot verify without attempting a live pull; flagged as open question
- synthesise_friction.py compatibility: HIGH — source code confirms hardcoded 4-file requirement

**Research date:** 2026-03-31
**Valid until:** 2026-04-14 (14 days — stable infrastructure, but GHCR image state may change)
