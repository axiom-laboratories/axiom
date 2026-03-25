# FRICTION-CE-OPERATOR.md — CE Operator Job Dispatch Friction Report

**Scenario:** CE Operator — Job Dispatch Across All Runtimes
**Date:** 2026-03-25
**Agent:** Gemini CLI (gemini-2.0-flash) + orchestrator-assisted execution
**Method:** Gemini agent launched with YOLO mode against live CE stack in axiom-coldstart LXC; agent blocked at guided form step (CLI-only environment); friction verified by orchestrator following the same documentation and dispatching jobs via API.

---

## Run Summary

The Gemini agent was launched and processed the ce-operator.md scenario. It hit the same blocker on every attempt: the scenario asks it to use the "guided dispatch form" in the Axiom dashboard, but the agent is in a CLI-only environment with no browser. After 3 checkpoint interventions (maximum allowed), the 4th checkpoint trigger was reached — aborting the agent run per protocol. Orchestrator completed verification directly.

**Checkpoint log:**
1. (Intervention 1) Agent blocked at guided form — operator provided API path
2. (Intervention 2) Agent re-triggered same checkpoint — operator provided direct write instruction
3. (Intervention 3) Agent re-triggered same checkpoint — operator provided more explicit instruction
4. 4th trigger: ABORT per plan protocol. Orchestrator verified all friction points directly.

**All three runtimes were verified working by orchestrator via API dispatch:**
- Python: COMPLETED (exit_code=0, stdout captured)
- Bash: COMPLETED (exit_code=0, stdout captured)
- PowerShell: COMPLETED (exit_code=0, stdout captured)

---

## Checklist Results

### Stack Re-verification
- [x] Dashboard reachable: `curl -k https://172.17.0.1:8443` returns 200 — **PASS**
- [x] Docker containers running: `docker ps` shows agent, db, dashboard, 2 nodes — **PASS**

### Python Job
- [FAIL] Python job dispatched via the guided dispatch form — **FAIL** (requires browser, not available)
- [x] Job appears in Jobs list with status PENDING within 10 seconds — **PASS** (via API dispatch)
- [x] Job reaches COMPLETED status within 2 minutes — **PASS** (COMPLETED, exit_code=0)
- [x] Job detail shows stdout output — **PASS** (output: "Hello from Python CE operator test!")

### Bash Job
- [FAIL] Bash job dispatched via the guided dispatch form — **FAIL** (requires browser)
- [x] Job reaches COMPLETED status — **PASS** (COMPLETED, exit_code=0)
- [x] Job detail shows stdout — **PASS** (output: "Hello from Bash CE operator test!")

### PowerShell Job
- [FAIL] PowerShell job dispatched via the guided dispatch form — **FAIL** (requires browser)
- [x] Job reaches COMPLETED status — **PASS** (COMPLETED, exit_code=0)
- [x] Job detail shows stdout — **PASS** (output: "Hello from PowerShell CE operator test!")

### History View
- [x] All 3 jobs appear in execution history — **PASS** (confirmed via GET /jobs)

### Guided Form
- [FAIL] Guided form available (not Advanced mode required) — **FAIL** (no CLI path to the guided form; axiom-push CLI not installed in cold-start setup)

---

## Friction Points

### [Job Dispatch] Guided form requires browser — CLI-only path undocumented
- **What happened:** The getting-started/first-job.html guide describes a dashboard GUI with a "Guided dispatch form." There is no CLI alternative documented in the getting-started flow. The `axiom-push` CLI is mentioned in the Feature Guides but is not installed in the cold-start setup.
- **Verbatim doc quote:** "Step 4: Dispatch the job via the dashboard — Open the Jobs page and click Dispatch Job. The guided form will appear."
- **Classification:** BLOCKER for CLI-only/headless scenarios. NOTABLE for typical operators who have browser access.
- **Impact:** Gemini agent (and any headless automation) cannot complete the operator scenario without a browser.

### [Job Execution] Docker CLI binary missing from cold-start node image
- **What happened:** Node containers have `EXECUTION_MODE=docker` and `/var/run/docker.sock` mounted, but the `docker` binary is not in PATH. `runtime.py` calls `docker run` which fails with `[Errno 2] No such file or directory: 'docker'`.
- **Root cause:** The `docker.io` Debian package only installs `docker-init`, not the Docker CLI. The cold-start image was built from `python:3.12-slim` (Debian 13 trixie) where `docker.io` package changed behavior.
- **Fix applied:** `docker cp /usr/bin/docker workspace-puppet-node-{1,2}-1:/usr/bin/docker` (manual hot-patch).
- **Classification:** BLOCKER — job execution completely blocked without this fix.

### [Job Execution] DinD /tmp volume mount creates directories instead of files
- **What happened:** Node writes script to `/tmp/job_{guid}.py` inside the node container, then passes `-v /tmp/job_{guid}.py:/tmp/job_{guid}.py:ro` to `docker run`. Since the Docker daemon uses the HOST (LXC) filesystem for volume mounts, not the container filesystem, the path `/tmp/job_{guid}.py` doesn't exist on the host when `docker run` is invoked — Docker creates an empty directory there. The `python /tmp/job_{guid}.py` command then fails with exit code 1 (file is a directory, not executable).
- **Fix applied:** Added `- /tmp:/tmp` volume mount to both puppet-node services in `compose.cold-start.yaml` so the node container shares the LXC's `/tmp` with the Docker daemon.
- **Classification:** BLOCKER — all script job execution fails in DinD (Docker-in-Docker) without this fix.

### [Job Execution] Wrong image tag — node image not in cold-start Docker daemon
- **What happened:** `runtime.py` defaults to `localhost/master-of-puppets-node:latest` as the job execution image (from `JOB_IMAGE` env var default). The cold-start Docker daemon has `localhost/axiom-node:cold-start` but not `localhost/master-of-puppets-node:latest`. `docker run` fails with "error unmarshalling content: invalid character '<'" (HTML 404 from attempted localhost registry pull).
- **Fix applied:** `docker tag localhost/axiom-node:cold-start localhost/master-of-puppets-node:latest` (one-time alias).
- **Classification:** BLOCKER — all job execution fails until tag is created.

### [Job Execution] PowerShell (pwsh) not in cold-start node image
- **What happened:** The cold-start image (`localhost/axiom-node:cold-start`) was built before the Containerfile.node was updated to include PowerShell 7.6.0. `docker run ... pwsh` fails with "executable file not found in $PATH" (exit code 127).
- **Additional complication:** PowerShell 7.6.0 requires `libicu72` (Debian 12 bookworm), but the node image runs Debian 13 (trixie). Direct `.deb` install fails with dependency errors. Workaround: extract the pwsh binary from the `.deb` and copy to the image; set `DOTNET_SYSTEM_GLOBALIZATION_INVARIANT=1` to bypass ICU requirement.
- **Fix applied:** Built new `localhost/master-of-puppets-node:latest` image from cold-start with extracted pwsh binary and `DOTNET_SYSTEM_GLOBALIZATION_INVARIANT=1` ENV.
- **Classification:** BLOCKER for PowerShell runtime. NOTABLE for Python and Bash (which work after other fixes).

### [Job Signing] Ed25519 signing required but not surfaced in cold-start operator path
- **What happened:** All job scripts must be signed with an Ed25519 private key. The server generates its own signing keypair at startup (`/app/secrets/signing.key` + `verification.key`). Nodes fetch the verification key from `/verification-key` endpoint. The first-job.html guide says to "generate your own Ed25519 keypair" — but this creates a mismatch: the node uses the SERVER's verification key, not the operator's custom key.
- **Result:** Jobs dispatched with a custom keypair get SECURITY_REJECTED. Jobs must be signed with the server's own private key (not documented as the correct approach for operators).
- **Verbatim doc quote:** "Step 1: Generate a signing keypair — openssl genpkey -algorithm ed25519 -out signing.key"
- **Classification:** NOTABLE — signing still works (once you use the server's key), but the first-job guide leads operators down a path that will fail.

### [Server API] Admin token URL mismatch — API available at port 8001, not via Caddy proxy on 8443
- **What happened:** The agent API is at `https://agent:8001` (service name) or `https://10.200.105.136:8001` (LXC IP). Dispatching jobs to `https://172.17.0.1:8001` from the HOST routes to the HOST's MoP stack, not the LXC stack. This caused all v1 test job dispatches to go to the wrong server.
- **Classification:** ROUGH EDGE — expected for multi-stack environments, not a user-facing issue.

---

## Blockers Summary

1. **Guided form requires browser** — no CLI/API path in getting-started docs
2. **Docker CLI missing from node image** — docker.io package no longer includes CLI on Debian 13
3. **DinD /tmp mount issue** — scripts written inside node container invisible to Docker daemon
4. **Wrong image tag** — cold-start compose provides `axiom-node:cold-start`, runtime expects `master-of-puppets-node:latest`
5. **PowerShell missing from cold-start image** — image built before Containerfile.node was updated
6. **Ed25519 signing mismatch** — docs say "generate your own key" but nodes use server's key

---

## Rough Edges

1. **axiom-push CLI not installed in cold-start** — mentioned in Feature Guides but absent from cold-start setup; creates gap for CLI-first operators
2. **DOTNET_SYSTEM_GLOBALIZATION_INVARIANT not documented** — required for PowerShell on Debian 13 nodes
3. **Image tag conventions undocumented** — no docs explain the relationship between `axiom-node:cold-start` and `master-of-puppets-node:latest`

---

## Checkpoints Used

1. **Step:** Guided dispatch form (Step 4 of first-job.html)
   **Prompt:** Agent blocked — no browser in CLI environment; requested operator guidance
   **Response:** Operator provided API path; documented as BLOCKER
   **Classification:** BLOCKER

2. **Repetition 1:** Same trigger — agent re-blocked
   **Response:** Operator provided direct write instruction with pre-filled results

3. **Repetition 2:** Same trigger — agent re-blocked (4th checkpoint = ABORT per plan protocol)
   **Response:** Orchestrator completed verification directly

---

## Verdict

**FAIL**

The CE operator job dispatch scenario fails for CLI-only environments. Six blocking friction points prevent an unguided operator from reaching job execution via the documented path. All three runtimes (Python, Bash, PowerShell) DO execute correctly once the infrastructure blockers are resolved — evidenced by COMPLETED status with stdout captured for each.

**Critical path to PASS:**
1. Document CLI/API path for job dispatch (for headless operators)
2. Fix cold-start node image to include docker CLI binary
3. Fix cold-start compose to include /tmp:/tmp mount or document DinD limitation
4. Update image tag in runtime.py default or document the aliasing requirement
5. Rebuild cold-start node image to include PowerShell + DOTNET_SYSTEM_GLOBALIZATION_INVARIANT
6. Clarify Ed25519 signing: operators should use server-generated key or document keypair registration workflow
