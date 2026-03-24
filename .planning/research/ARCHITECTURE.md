# Architecture Research

**Domain:** CE/EE Cold-Start Validation Framework — LXC + Gemini Agent + Checkpoint Protocol
**Researched:** 2026-03-24
**Confidence:** HIGH — all components derived from direct codebase inspection of existing LXC patterns, Docker bridge networking, and Caddy TLS cert provisioning

---

## Context Note

This file covers v14.0 architecture only. It supersedes the v11.1 validation architecture (LXC node provisioning, job test matrix) for the purposes of the current milestone. v14.0 adds a Gemini CLI tester agent and a file-based checkpoint protocol on top of the established LXC patterns. Where v11.1 components are reused, they are referenced, not re-documented.

---

## System Overview

### Full v14.0 Cold-Start Validation Stack

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                     Host Machine (Thomas's dev box)                          │
│                                                                               │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │  Incus LXC: axiom-cold-start-ce  (Ubuntu 24.04, nesting=true)        │    │
│  │                                                                       │    │
│  │  ┌─────────────────────────────────────────┐  ┌──────────────────┐  │    │
│  │  │    Docker Compose — Axiom Stack          │  │  Gemini Tester   │  │    │
│  │  │    (compose.cold-start.yaml)             │  │  (gemini CLI)    │  │    │
│  │  │                                          │  │                  │  │    │
│  │  │  cert-manager (Caddy) :443 :80           │  │  GEMINI.md       │  │    │
│  │  │    SERVER_HOSTNAME=172.17.0.1            │  │  Playwright      │  │    │
│  │  │  agent (FastAPI)      :8001              │  │  axiom-sdk CLI   │  │    │
│  │  │  model                :8000              │  │  requests (API)  │  │    │
│  │  │  dashboard (React)    (via Caddy)        │  │                  │  │    │
│  │  │  docs (MkDocs)        /docs/             │  └────────┬─────────┘  │    │
│  │  │  db (Postgres)        :5432              │           │             │    │
│  │  │  registry             :5000              │           │ r/w direct  │    │
│  │  │  devpi                :3141              │           │             │    │
│  │  │  pypi / mirror        :8080 :8081        │  ┌────────▼─────────┐  │    │
│  │  │                                          │  │  /workspace/     │  │    │
│  │  │  puppet-node-1                           │  │  checkpoint/     │  │    │
│  │  │    EXECUTION_MODE=direct                 │  │  ├─ PROMPT.md    │  │    │
│  │  │    AGENT_URL=https://172.17.0.1:8001     │  │  ├─ RESPONSE.md  │  │    │
│  │  │    ENV_TAG=DEV                           │  │  ├─ STATUS.md    │  │    │
│  │  │  puppet-node-2                           │  │  └─ FRICTION.md  │  │    │
│  │  │    ENV_TAG=PROD                          │  └─────────────────┘  │    │
│  │  │                                          │                        │    │
│  │  └────────────── Docker bridge 172.17.0.0/16┘                       │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                                                               │
│       incusbr0: 10.x.x.x/24   (LXC ↔ host bridge, NOT used by puppet nodes) │
│                                                                               │
│  Claude (host session)                                                        │
│    ├── monitor_checkpoint.py  ──── incus exec / file read ──── checkpoint/  │
│    └── synthesise_friction.py ──── merges CE+EE FRICTION.md files           │
│                                                                               │
│  (Separate run) axiom-cold-start-ee — identical topology + AXIOM_LICENCE_KEY │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Component Responsibilities

| Component | Responsibility | Lives In |
|-----------|----------------|----------|
| Incus LXC container | Fully isolated test environment; one per CE/EE run | Host (`incus launch`) |
| `compose.cold-start.yaml` | Trimmed Axiom stack: no Cloudflare tunnel, no DuckDNS, `SERVER_HOSTNAME=172.17.0.1` | `puppeteer/` in LXC |
| puppet-node-1 / puppet-node-2 | Job executors enrolled during test run; `EXECUTION_MODE=direct` | Docker containers inside LXC |
| Gemini tester agent | Follows docs site, dispatches jobs, validates outcomes; treats Axiom as a black box | LXC process (not Docker container) |
| checkpoint/ directory | Async comms channel: Gemini writes PROMPT.md; Claude reads and writes RESPONSE.md | `/workspace/checkpoint/` in LXC |
| tester GEMINI.md | Scoped constraints for tester: docs-only, no source code, file comms protocol | `/workspace/gemini-context/` in LXC |
| monitor_checkpoint.py | Host-side: polls PROMPT.md, presents to Claude, writes RESPONSE.md back | `mop_validation/cold_start/` on host |
| synthesise_friction.py | Merges CE + EE FRICTION.md logs into final report | `mop_validation/cold_start/` on host |
| inject_ee_licence.py | Pre-injects `AXIOM_LICENCE_KEY` into LXC `.env` before EE stack launch | `mop_validation/cold_start/` on host |

## Recommended Project Structure

```
mop_validation/
└── cold_start/
    ├── provision_lxc.py          # Launch + configure CE or EE LXC container
    ├── teardown_lxc.py           # Destroy container + clean artifacts
    ├── inject_ee_licence.py      # Pre-inject AXIOM_LICENCE_KEY into LXC .env
    ├── monitor_checkpoint.py     # Poll PROMPT.md, present to Claude, write RESPONSE.md
    └── synthesise_friction.py    # Merge CE + EE FRICTION.md → cold_start_friction_report.md

# Inside each LXC container at /workspace/:
/workspace/
├── axiom/                         # Cloned from host bind-mount or git clone
│   ├── puppeteer/
│   │   ├── compose.cold-start.yaml  # New: trimmed stack (no tunnel, no ddns)
│   │   └── .env                     # Generated per-run; CE has no licence key
│   └── puppets/
├── checkpoint/
│   ├── PROMPT.md                  # Written by Gemini; Claude reads
│   ├── RESPONSE.md                # Written by Claude; Gemini reads
│   ├── STATUS.md                  # Gemini maintains: phase, step, blocked flag
│   └── FRICTION.md                # Gemini appends: friction log entries
└── gemini-context/
    ├── GEMINI.md                  # Tester-scoped constraints
    └── test-signing.key           # Ed25519 private key for axiom-push job signing
```

### Structure Rationale

- **`cold_start/` is separate from sprint scripts:** Cold-start provisioning/monitoring is repeated per CE/EE run and is not test-logic; it belongs in its own subdirectory, not mixed with `test_playwright.py` or `test_local_stack.py`.
- **`compose.cold-start.yaml` is a new file, not a modified production compose:** Production `compose.server.yaml` references DuckDNS tokens, Cloudflare tunnel, and ddns-updater — all of which fail inside LXC. Modifying the production compose for test purposes is an anti-pattern.
- **`/workspace/checkpoint/` is outside the axiom repo tree:** Gemini must not confuse checkpoint files with axiom source files. Keeping them separate enforces the "docs-only, no source code" constraint.
- **`gemini-context/GEMINI.md` is a different file from the repo GEMINI.md:** The repo GEMINI.md is developer-scoped (read code, check sister repos, run deployment scripts). The tester GEMINI.md constrains Gemini to first-time-user behaviour.

## Architectural Patterns

### Pattern 1: Docker Bridge as Puppet Node AGENT_URL Inside LXC

**What:** Puppet nodes are Docker containers launched by Docker Compose inside the LXC container. Their network namespace's gateway to the host Docker network is `172.17.0.1` (the standard Docker bridge host IP). The cert-manager's Caddy TLS certificate must include this IP as a SAN.

**When to use:** Always — for any puppet nodes launched as Docker containers inside an LXC container.

**Trade-offs:** `172.17.0.1` is the default Docker bridge gateway and is consistent across machines unless Docker's bridge CIDR has been customised. The incusbr0 IP (`10.x.x.x`) is NOT used here — that bridge connects the LXC container to the host, not Docker containers to each other.

**Confirmed working:** `lxc-node-compose.yaml` uses `extra_hosts: host.docker.internal:host-gateway` which resolves to `172.17.0.1` inside Docker. The `compose.cold-start.yaml` must set `SERVER_HOSTNAME=172.17.0.1` so the cert-manager generates a Caddy cert with this IP as a SAN.

```yaml
# In compose.cold-start.yaml — cert-manager service
environment:
  - SERVER_HOSTNAME=172.17.0.1   # Caddy cert SAN includes Docker bridge IP
```

```yaml
# Puppet node service in compose.cold-start.yaml
environment:
  - AGENT_URL=https://172.17.0.1:8001
  - EXECUTION_MODE=direct        # Docker-in-Docker: avoid nested cgroup v2 issues
  - VERIFY_SSL=false             # Self-signed cert from Axiom Root CA
```

### Pattern 2: Gemini Agent Accesses Axiom Services via localhost

**What:** The Gemini tester runs as a process directly inside the LXC container (not inside any Docker container). From Gemini's perspective, Caddy (443/80), the agent (8001), and the docs site (/docs/) are all at `localhost` or `127.0.0.1`.

**When to use:** All Gemini HTTP calls, Playwright browser navigation, `axiom-push` CLI invocations target `https://localhost:443` or `https://localhost:8001`.

**Trade-offs:** Caddy's TLS certificate is self-signed (Root CA generated by cert-manager at first start). Playwright must either install the Root CA into the system trust store, or the Playwright session must use `--ignore-certificate-errors`. Installing the Root CA is the cleaner approach and mirrors what a real new user would do.

**CA installation sequence (run once after stack start):**
```bash
# Inside LXC — bootstraps trust before Playwright runs
curl -sk http://localhost:80/system/root-ca -o /tmp/axiom-root.crt
sudo cp /tmp/axiom-root.crt /usr/local/share/ca-certificates/axiom-root.crt
sudo update-ca-certificates
# Playwright then trusts the cert without --ignore-certificate-errors
```

**Key confirmed from prior work:** Python Playwright requires `args=['--no-sandbox']` inside LXC. This is documented in CLAUDE.md and confirmed working in v11.1.

### Pattern 3: File-Based Checkpoint Protocol

**What:** Gemini writes to `checkpoint/PROMPT.md` when it needs human steering, then polls for `checkpoint/RESPONSE.md`. Claude reads the prompt via `monitor_checkpoint.py` and writes the response back. Both parties use a version counter in the file header to prevent stale reads.

**When to use:** When the Gemini agent encounters a decision point it cannot resolve from the docs site alone: ambiguous instructions, missing prerequisite, blocked install step, unexpected UI behaviour.

**File schema:**

```
checkpoint/PROMPT.md
---
# PROMPT v{N}
phase: {install_path|operator_path|ee_features}
question: {one sentence}
context: |
  Last 3 actions taken (free text)
---

checkpoint/RESPONSE.md
---
# RESPONSE v{N}
instruction: {what to do next — one paragraph max}
---

checkpoint/STATUS.md
---
phase: {current phase name}
step: {current step number or name}
last_action: {one sentence}
blocked: {true|false}
---

checkpoint/FRICTION.md
---
## FRICTION ENTRY
phase: {install_path|operator_path|ee_features}
observation: {what was confusing or wrong}
severity: {BLOCKER|NOTABLE|MINOR}
step_ref: {doc page or UI element reference}
---
```

**Polling parameters:**
- Gemini polls `RESPONSE.md` every 15 seconds, up to 20 iterations (5-minute timeout)
- If no response in 5 minutes, Gemini writes `STATUS.md: blocked=true` and continues with a best-effort fallback
- Claude's `monitor_checkpoint.py` polls `PROMPT.md` every 30 seconds

**Handshake protocol:**
1. Gemini writes `PROMPT.md` with version counter `v{N}`
2. Gemini sets `STATUS.md: blocked=true`
3. Claude reads `PROMPT.md`, writes `RESPONSE.md` with matching header `# RESPONSE v{N}`
4. Gemini detects version match, reads instruction, sets `STATUS.md: blocked=false`, continues
5. Gemini archives consumed prompt: `mv checkpoint/PROMPT.md checkpoint/PROMPT.v{N}.md`

**Host-side read/write via incus exec:**
```bash
# Read PROMPT (non-destructive)
incus exec axiom-cold-start-ce -- cat /workspace/checkpoint/PROMPT.md

# Write RESPONSE
incus file push /tmp/response.md axiom-cold-start-ce/workspace/checkpoint/RESPONSE.md
```

### Pattern 4: CE vs EE LXC Provisioning — Single Difference

**What:** CE and EE runs use identically provisioned LXC containers with one explicit difference: the EE container has `AXIOM_LICENCE_KEY` injected into the Axiom `.env` file and the `axiom-ee` package installed into the agent image before `docker compose up`.

**When to use:** Always run CE first. EE run depends on CE baseline being clean.

**CE provisioning (complete):**
1. `incus launch images:ubuntu/24.04 axiom-cold-start-ce -c security.nesting=true`
2. Install Docker, docker-compose-plugin, Python 3, pip, Playwright deps, Gemini CLI
3. Clone axiom repo to `/workspace/axiom/` (or bind-mount from host)
4. Copy `compose.cold-start.yaml` to `/workspace/axiom/puppeteer/`
5. Write `.env` file (no `AXIOM_LICENCE_KEY`)
6. Drop tester context into `/workspace/gemini-context/` (GEMINI.md + test-signing.key)
7. Create `/workspace/checkpoint/` directory with empty seed files
8. Register `test-signing.key` public key with Axiom API (prerequisite for job dispatch)

**EE provisioning — differences from CE only:**
1. Container name: `axiom-cold-start-ee`
2. After copying repo: `echo "AXIOM_LICENCE_KEY=${TEST_LICENCE_KEY}" >> /workspace/axiom/puppeteer/.env`
3. Install `axiom-ee` into the agent image before stack launch:
   - Editable install path: `pip install -e /workspace/axiom-ee/` inside the agent container at build time
   - OR: push dev wheel to devpi inside LXC, rebuild agent image with EE wheel from devpi
4. Tester GEMINI.md includes EE-specific test directives (check licence badge, test EE-gated routes)

## Data Flow

### Install Path (Gemini follows getting-started docs)

```
Gemini reads http://localhost/docs/getting-started/
    |
    v
Step: generate JOIN_TOKEN
    POST /auth/login → JWT
    POST /admin/generate-token → JOIN_TOKEN
    |
    v
Step: enroll a puppet node
    Gemini runs installer script inside LXC (or starts Docker Compose puppet service)
    puppet-node-1 polls GET /work/pull → enrolled via mTLS cert exchange
    puppet-node-1 heartbeats → appears ONLINE in GET /nodes
    |
    v
Gemini verifies via dashboard (Playwright) or API
    If step matches docs exactly → no friction entry
    If step deviates from docs → FRICTION.md entry (NOTABLE or MINOR)
    If step is blocked → PROMPT.md entry (BLOCKER), wait for RESPONSE.md
    |
    v
checkpoint/STATUS.md: install_path COMPLETE
```

### Operator Path (Gemini uses the running system)

```
Gemini reads http://localhost/docs/feature-guides/
    |
    v
Dispatch Python job:
    axiom-push sign script.py --key /workspace/gemini-context/test-signing.key
    POST /api/jobs {..., task_type="script", runtime="python"}
    |
    v
Job: PENDING → ASSIGNED → IN_PROGRESS → COMPLETED
    GET /api/executions?job_id=X → verify stdout captured
    |
    v
Repeat for Bash runtime, then PowerShell runtime
    |
    v
EE path additionally:
    GET /api/licence → assert {"edition": "enterprise"}
    Test EE-gated routes (Foundry, RBAC management, audit log queries)
    |
    v
checkpoint/STATUS.md: operator_path COMPLETE
checkpoint/FRICTION.md: all friction entries written
```

### Checkpoint Communication Flow

```
Gemini encounters blocker or ambiguity
    |
    v
Write checkpoint/PROMPT.md (# PROMPT v{N})
Set STATUS.md: blocked=true
    |
    v
Claude host session (monitor_checkpoint.py)
    polls every 30s → detects new PROMPT version
    reads context + question
    writes checkpoint/RESPONSE.md (# RESPONSE v{N})
    |
    v
Gemini polls every 15s → detects matching RESPONSE version
Reads instruction
Archives PROMPT.v{N}.md
Sets STATUS.md: blocked=false
Continues test
```

### CE vs EE Divergence Report Flow

```
CE run completes:
    checkpoint/FRICTION.md (CE)
    checkpoint/STATUS.md: COMPLETE
    |
    v
EE run completes:
    checkpoint/FRICTION.md (EE)
    checkpoint/STATUS.md: COMPLETE
    |
    v
Host-side: synthesise_friction.py
    incus file pull axiom-cold-start-ce/workspace/checkpoint/FRICTION.md → ce_friction.md
    incus file pull axiom-cold-start-ee/workspace/checkpoint/FRICTION.md → ee_friction.md
    Merge: categorise CE-only, EE-only, and shared friction
    Output: mop_validation/reports/cold_start_friction_report.md
        Sections: install friction, operator friction, CE-vs-EE divergence, severity summary
```

## Integration Points

### New Components

| Component | New or Modified | Location | Communicates With |
|-----------|----------------|----------|-------------------|
| `compose.cold-start.yaml` | New | `puppeteer/` (in LXC) | Docker engine inside LXC |
| `provision_lxc.py` | New | `mop_validation/cold_start/` | Incus CLI on host |
| `teardown_lxc.py` | New | `mop_validation/cold_start/` | Incus CLI on host |
| `inject_ee_licence.py` | New | `mop_validation/cold_start/` | `.env` file in LXC via `incus file push` |
| `monitor_checkpoint.py` | New | `mop_validation/cold_start/` | `incus exec`, `incus file push` on host |
| `synthesise_friction.py` | New | `mop_validation/cold_start/` | FRICTION.md files pulled from both LXC runs |
| tester `GEMINI.md` | New | `/workspace/gemini-context/` in LXC | Gemini agent process constraint |
| `checkpoint/` directory | New | `/workspace/checkpoint/` in LXC | Gemini (writer), Claude (reader via incus) |
| `test-signing.key` | New (test Ed25519 keypair) | `/workspace/gemini-context/` in LXC | `axiom-push` CLI inside LXC |

### Unchanged Components

| Component | Notes |
|-----------|-------|
| `compose.server.yaml` | Production compose, not used in cold-start runs |
| `manage_node.py` | Single-node LXC skill; cold-start uses `provision_lxc.py` instead |
| `test_local_stack.py` | Sprint regression suite; cold-start uses Gemini tester instead |
| All Axiom API routes | Cold-start does black-box testing only; no source code changes |
| `cert-manager/entrypoint.sh` | Already supports `SERVER_HOSTNAME` env var for SAN injection |

### Internal Boundaries

| Boundary | Communication | Notes |
|----------|---------------|-------|
| Gemini → Axiom API | HTTPS to `https://localhost:8001` (agent) or `https://localhost:443` (Caddy) | Root CA installed in LXC system trust store before Playwright runs |
| Gemini → Dashboard | Playwright browser to `https://localhost:443` | `args=['--no-sandbox']` required; confirmed in CLAUDE.md |
| Gemini → Docs site | `http://localhost:80/docs/` or `https://localhost:443/docs/` | MkDocs nginx served via Caddy reverse proxy |
| Gemini → `axiom-push` CLI | Subprocess call; key at `/workspace/gemini-context/test-signing.key` | `axiom-push sign` then `axiom-push create` or `POST /api/jobs` |
| Gemini → checkpoint/ | Posix file write; direct path access | Single writer (Gemini), single reader (Claude); no locking needed |
| Claude → checkpoint/ | `incus exec axiom-cold-start-ce -- cat .../PROMPT.md` | Read; `incus file push` to write RESPONSE.md |
| puppet nodes → agent | `AGENT_URL=https://172.17.0.1:8001` | Docker bridge host IP; `EXECUTION_MODE=direct`; `VERIFY_SSL=false` |
| puppet nodes → job containers | Docker subprocess (EXECUTION_MODE=direct) | No nested container runtime; compatible with Docker-in-LXC |

## CE vs EE Explicit Differences

| Dimension | CE LXC | EE LXC |
|-----------|--------|--------|
| Container name | `axiom-cold-start-ce` | `axiom-cold-start-ee` |
| `.env` file | No `AXIOM_LICENCE_KEY` | `AXIOM_LICENCE_KEY=<signed_test_licence>` injected before `docker compose up` |
| `axiom-ee` package | Not installed | Installed into agent image (editable install or devpi dev wheel) |
| `GET /api/licence` | `{"edition": "community"}` | `{"edition": "enterprise"}` |
| EE stub routes (7) | Return 402 | Return real data |
| Feature flags | All false | All true |
| Tester GEMINI.md | CE directives only | CE directives + EE feature verification section |
| Run order | First | Second (requires clean CE baseline) |
| Gemini first assertion | Stack is healthy and CE edition | `GET /api/licence` returns enterprise before any EE tests |

## Suggested Build Order

Order enforced by hard dependencies. Each phase must complete before the next can start, except where noted.

### Phase 1: compose.cold-start.yaml + LXC Provisioner
**Why first:** Nothing else can be tested without a working Axiom stack inside LXC. This phase is the infrastructure foundation.

**Delivers:**
- `compose.cold-start.yaml`: no Cloudflare tunnel, no DuckDNS, no ddns-updater; `SERVER_HOSTNAME=172.17.0.1` on cert-manager; puppet nodes with `AGENT_URL=https://172.17.0.1:8001` and `EXECUTION_MODE=direct`
- `provision_lxc.py`: launches Ubuntu 24.04 container with `security.nesting=true`, installs Docker + Python + Playwright deps + Gemini CLI, copies axiom repo, starts stack
- `teardown_lxc.py`: destroys container cleanly
- Verified: stack starts, Caddy serves on 443 with Docker bridge IP in SAN, agent responds on 8001, docs at /docs/

**Dependency:** None. First phase.

### Phase 2: Gemini Tester Context + Checkpoint Protocol
**Why second:** Gemini cannot run as a tester without a scoped GEMINI.md, a signing key, and a working checkpoint directory. The checkpoint schema must be agreed before the agent is invoked.

**Delivers:**
- Tester `GEMINI.md` with constraints: docs-only, no source code, file comms protocol, severity definitions for FRICTION.md
- `checkpoint/` directory with seed files and documented schema
- `monitor_checkpoint.py`: host-side poller; reads PROMPT.md via `incus exec`, presents to Claude, writes RESPONSE.md via `incus file push`
- `test-signing.key` Ed25519 keypair generated; public key registered in running stack via `POST /api/signatures`
- Verified: Gemini can authenticate (JWT via `POST /auth/login`), navigate dashboard via Playwright, write to checkpoint/

**Dependency:** Phase 1 (stack running for public key registration).

### Phase 3: CE Cold-Start Run
**Why third:** CE baseline must precede EE. Failures here are unambiguously CE bugs.

**Delivers:**
- Install path: Gemini follows getting-started docs from scratch — generate token, enroll nodes, verify heartbeat
- Operator path: Gemini dispatches Python, Bash, PowerShell jobs; verifies stdout captured in execution history
- CE anti-features: all 7 EE stub routes return 402; licence badge shows "Community Edition"
- `checkpoint/FRICTION.md` from CE run
- `checkpoint/STATUS.md: COMPLETE`

**Dependency:** Phases 1 and 2.

### Phase 4: EE Cold-Start Run
**Why fourth:** Requires clean CE baseline. Adds licence key injection and axiom-ee install.

**Delivers:**
- EE provisioning: `inject_ee_licence.py` writes `AXIOM_LICENCE_KEY` to `.env`; axiom-ee installed; stack restarted
- Install path: same as CE; additional check that licence badge shows "Enterprise Edition" at first login
- Operator path: CE jobs repeated; plus EE-gated features verified
- `GET /api/licence` assertion is first EE check — all EE tests gate on this
- `checkpoint/FRICTION.md` from EE run

**Dependency:** Phase 3 (CE run complete and clean).

### Phase 5: Friction Report Synthesis
**Why last:** Both FRICTION.md files required. Cannot synthesise partial results.

**Delivers:**
- `synthesise_friction.py`: pulls FRICTION.md from both LXC containers via `incus file pull`; categorises by phase, severity, and CE-vs-EE scope
- `mop_validation/reports/cold_start_friction_report.md`: BLOCKER / NOTABLE / MINOR triage; install friction vs operator friction; CE-only vs EE-only vs shared

**Dependency:** Phases 3 and 4.

## Anti-Patterns

### Anti-Pattern 1: Using compose.server.yaml Directly Inside LXC

**What people do:** Copy `compose.server.yaml` unchanged into the LXC container for cold-start testing.

**Why it's wrong:** `compose.server.yaml` references `DUCKDNS_TOKEN`, `CLOUDFLARE_TUNNEL_TOKEN`, `TUNNEL_TOKEN`, and the ddns-updater and cloudflared services. These all crash or hang inside LXC where there is no external DNS or tunnel. The tunnel service will crash-loop and block `depends_on` chains. The DDNS updater will spew repeated errors.

**Do this instead:** Maintain `compose.cold-start.yaml` that strips tunnel, ddns-updater, and DUCKDNS references. Add `SERVER_HOSTNAME=172.17.0.1` to cert-manager. This is a test-only file that is not a modified version of production — it is a separate configuration for a specific purpose.

### Anti-Pattern 2: Puppet Nodes Using localhost as AGENT_URL

**What people do:** Set `AGENT_URL=https://localhost:8001` for puppet nodes in the cold-start compose.

**Why it's wrong:** Puppet nodes are Docker containers. Their `localhost` is their own container namespace, not the LXC container's network. The Axiom agent is reachable at the Docker bridge gateway (`172.17.0.1`), not localhost.

**Do this instead:** `AGENT_URL=https://172.17.0.1:8001`. Confirm `SERVER_HOSTNAME=172.17.0.1` is set in cert-manager so the Caddy TLS cert includes this IP as a SAN. Use `VERIFY_SSL=false` because the cert is self-signed.

### Anti-Pattern 3: Gemini Using the Developer GEMINI.md

**What people do:** Use the existing `/home/thomas/Development/master_of_puppets/GEMINI.md` as the Gemini tester's instruction file.

**Why it's wrong:** The developer GEMINI.md instructs Gemini to read source code, check sister repos, and run deployment scripts. A tester should behave as a first-time user: read only the docs site, use only the UI and CLI, and log friction. Mixing developer context with tester context invalidates the cold-start simulation.

**Do this instead:** Write a separate `/workspace/gemini-context/GEMINI.md` scoped to: "You are a new user of Axiom. You have access to the docs site at `http://localhost/docs/`. You do NOT have access to source code. Use the checkpoint/ directory to communicate blockers. Log all friction observations to checkpoint/FRICTION.md."

### Anti-Pattern 4: Blocking Indefinitely on checkpoint/ Responses

**What people do:** Gemini polls `RESPONSE.md` in an infinite loop, never timing out.

**Why it's wrong:** If Claude's host session is unresponsive (sleeping, tab closed), the tester hangs indefinitely. The run never produces results. The checkpoint protocol is asynchronous and cannot assume real-time monitoring.

**Do this instead:** Gemini times out after 5 minutes (20 polls at 15-second intervals). On timeout: set `STATUS.md: blocked=true`, write a best-effort fallback to `FRICTION.md` ("Unable to complete step X; blocked waiting for steering response"), and move to the next test step. The run degrades gracefully rather than hanging.

### Anti-Pattern 5: Polling checkpoint/ from Host via SSH Instead of incus exec

**What people do:** Install SSH in the LXC container and `ssh ubuntu@<lxc-ip>` to read/write checkpoint files.

**Why it's wrong:** Requires SSH provisioning (extra step, key management). `incus exec` is a first-class Incus operation that works without any network setup; it runs commands directly in the container's process namespace. It is simpler, more reliable, and does not require the container to have a running SSH daemon.

**Do this instead:** `incus exec axiom-cold-start-ce -- cat /workspace/checkpoint/PROMPT.md`. Write files via `incus file push /tmp/response.md axiom-cold-start-ce/workspace/checkpoint/RESPONSE.md`.

### Anti-Pattern 6: EE Tests Before Licence Assertion

**What people do:** Test EE-gated routes immediately after stack start in the EE run, before checking `GET /api/licence`.

**Why it's wrong:** If the licence key is malformed, expired, or the EE public key does not match the signing key, the stack silently falls back to CE mode. All EE route tests then return 402, which looks identical to a CE run. The root cause (licence loading failure) is invisible until `GET /api/licence` is checked.

**Do this instead:** The first assertion in every EE test phase must be `GET /api/licence` → `{"edition": "enterprise"}`. Gate all subsequent EE tests on this. If this assertion fails, stop the EE run and diagnose the licence injection before continuing.

## Scaling Considerations

This is a test harness, not a production service. Scaling means concurrent CE+EE runs, not user load.

| Scale | Architecture Adjustments |
|-------|--------------------------|
| Sequential CE then EE (default) | One LXC at a time; one Claude session monitors; 5–8 hours total per full run |
| Parallel CE + EE | Two LXC containers simultaneously; two checkpoint/ dirs (`-ce` and `-ee`); `monitor_checkpoint.py` watches both |
| CI integration (future) | GitHub Actions runner with Incus; checkpoint polling in Actions step; FRICTION.md uploaded as artefact |

Resource budget for two concurrent LXC containers on the host:
- ~4GB RAM per container (Postgres 512MB + Docker stack + 2 puppet nodes)
- ~8GB total for CE+EE parallel run
- Incus bridge handles 2 containers with no contention

## Sources

- `puppeteer/compose.server.yaml` — full service topology; identifies tunnel, ddns-updater, DuckDNS services that must be stripped in cold-start variant (HIGH, direct inspection)
- `puppeteer/cert-manager/entrypoint.sh` — `SERVER_HOSTNAME` SAN injection: `CADDY_SANS="${CADDY_SANS},${SERVER_HOSTNAME}"` already implemented; `SERVER_HOSTNAME=172.17.0.1` is sufficient (HIGH, direct inspection)
- `puppeteer/cert-manager/Caddyfile` — reverse proxy topology including `/docs/*` → `docs:80` (HIGH, direct inspection)
- `.agent/skills/manage-test-nodes/scripts/manage_node.py` — Incus provisioning pattern: `security.nesting=true`, Ubuntu 24.04, Docker/SSH/Python install, `incus file push` for key injection (HIGH, direct inspection)
- `mop_validation/scripts/test_installer_lxc.py` — established `incus exec`, `incus file push`, `exec_in_container()` helpers; confirmed `INSTALLER_TIMEOUT`, wait-for-heartbeat pattern (HIGH, direct inspection)
- `mop_validation/local_nodes/lxc-node-compose.yaml` — confirmed `host-gateway` extra_hosts, `EXECUTION_MODE=docker` for LXC-hosted nodes; cold-start uses `EXECUTION_MODE=direct` instead to avoid cgroup issues (HIGH, direct inspection)
- `puppets/node-compose.yaml` — confirms `AGENT_URL=https://puppeteer-agent-1:8001` within Docker network; cold-start equivalent is `172.17.0.1` (HIGH, direct inspection)
- `mop_validation/local_nodes/node_alpha/node-compose.yaml` — confirms `extra_hosts: host.docker.internal:172.17.0.1` for Docker-hosted nodes; confirmed pattern for Docker-in-Docker (HIGH, direct inspection)
- `.planning/research/SUMMARY.md` (v11.1) — "LXC containers sit on incusbr0 bridge, not Docker bridge. AGENT_URL must be set to incusbr0-host-ip ... not 172.17.0.1 which is the Docker bridge" — this refers to LXC processes reaching the host. Puppet nodes inside Docker inside LXC still use the Docker bridge gateway. Both are correct in their respective contexts (HIGH, prior validated research)
- `CLAUDE.md` MEMORY — "Python Playwright requires `--no-sandbox`; confirmed working in LXC"; "Auth: inject JWT via localStorage"; "localStorage key is `mop_auth_token`" (HIGH, validated in prior phases)
- `GEMINI.md` (repo root) — developer-scoped; confirms what must NOT be in the tester-scoped version (HIGH, direct inspection)

---

*Architecture research for: Axiom v14.0 CE/EE Cold-Start Validation Framework*
*Researched: 2026-03-24*
