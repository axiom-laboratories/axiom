# Pitfalls Research

**Domain:** CE/EE Cold-Start Validation Framework — Gemini CLI agent inside Ubuntu 24.04 LXC (Incus), Docker-in-LXC with EXECUTION_MODE=direct, Python Playwright (--no-sandbox), file-based checkpoint steering, Ed25519 licence gating, and self-signed TLS (Caddy)
**Researched:** 2026-03-24
**Confidence:** HIGH (based on direct codebase inspection of `puppeteer/cert-manager/entrypoint.sh`, `puppeteer/Caddyfile`, `puppeteer/compose.server.yaml`, `puppets/environment_service/runtime.py`, PROJECT.md v14.0 milestone definition, confirmed Playwright/Chromium cert-store behaviour from upstream GitHub issues, and Gemini CLI non-interactive mode issue tracker)

---

## Critical Pitfalls

### Pitfall 1: Caddy TLS SAN Mismatch — Playwright Hits Wrong Hostname and Gets ERR_CERT_AUTHORITY_INVALID

**What goes wrong:**
The cert-manager generates Caddy's TLS certificate with SANs `localhost,127.0.0.1` plus optionally `SERVER_HOSTNAME` (see `puppeteer/cert-manager/entrypoint.sh` lines 17-19). Inside the LXC container, the Docker bridge gives the Caddy container an IP (e.g. `172.17.0.3`) and the host stack is accessible from the LXC at whatever IP Incus assigns to the Docker host interface — typically `172.17.0.1` or the bridge gateway. Neither of these IPs is `localhost` from the LXC perspective.

When the Gemini agent or Playwright opens `https://<docker-bridge-ip>:8443`, Chromium's TLS stack checks the presented certificate. The cert's SANs are `localhost` and `127.0.0.1`, not the actual IP used. TLS fails with `ERR_CERT_AUTHORITY_INVALID` (SAN mismatch). Playwright crashes. The agent is unable to load the dashboard at all.

There is a second layer: even if the agent accesses via `https://localhost:8443` (forwarded into the LXC from the host), Chromium inside the LXC does not trust the Axiom Root CA because Chromium has its own certificate store. Installing the Root CA into `/etc/ssl/certs/` via `update-ca-certificates` is confirmed to be insufficient — Chromium ignores the system store (Playwright GitHub issue #4785, status: closed/confirmed). The cert must be trusted via Playwright launch options or Chromium's NSS DB directly.

**Why it happens:**
Two compounding assumptions:
1. "localhost will work from inside the LXC" — false: LXC networking routes to the Docker bridge IP, not loopback.
2. "system CA install will make Chromium trust our self-signed cert" — false: Chromium uses its own NSS-based trust store, not the OS store.

**How to avoid:**
Do all of the following at LXC setup time, before Playwright tests run:

1. Set `SERVER_HOSTNAME` in the compose env to the LXC-accessible IP or hostname of the Docker host before starting the Axiom stack. This causes cert-manager to include that IP/hostname in the SAN list. Example: `SERVER_HOSTNAME=172.17.0.1` (or the host's LXC bridge IP).

2. Export the Root CA PEM from the running stack:
   ```bash
   docker exec puppeteer-cert-manager-1 cat /etc/certs/root_ca.crt > /tmp/axiom_root_ca.pem
   ```

3. Pass the Root CA to Playwright launch via the `ca_certs` option (Playwright Python) or `--ignore-certificate-errors` for expediency:
   ```python
   browser = p.chromium.launch(
       args=['--no-sandbox'],
       # Option A: ignore all TLS errors (acceptable in isolated test LXC)
       ignore_https_errors=True
   )
   # Option B: trusted CA — launch a persistent browser context
   context = browser.new_context(
       ignore_https_errors=False,  # prefer this
       # Playwright Python does not expose ca_certs at browser level;
       # use --ignore-certificate-errors or the certutil approach below
   )
   ```
   Or add the Root CA to Chromium's NSS DB before the test:
   ```bash
   certutil -d sql:$HOME/.pki/nssdb -A -t "C,," -n axiom-root-ca -i /tmp/axiom_root_ca.pem
   ```

4. For Gemini CLI HTTP calls that hit the Axiom API directly (not via Playwright), set `NODE_EXTRA_CA_CERTS=/tmp/axiom_root_ca.pem` in the environment before invoking `gemini`. This makes Node.js trust the Axiom Root CA.

**Warning signs:**
- Playwright test exits immediately with `ERR_CERT_AUTHORITY_INVALID` or `net::ERR_SSL_PROTOCOL_ERROR`.
- `curl https://<stack-host>:8443/` from inside the LXC returns `SSL certificate problem: self-signed certificate in certificate chain`.
- Gemini CLI HTTP tool calls return `certificate has expired` or `self-signed cert` errors.
- Dashboard never loads; Playwright screenshot shows browser's "Your connection is not private" page.

**Phase to address:** Phase 1 (LXC environment setup) — add SERVER_HOSTNAME injection, Root CA export, and Playwright TLS bypass to the LXC provisioning script. This must be done before any Gemini agent session starts.

---

### Pitfall 2: Gemini CLI Rate Limit (429) Stalls the Agent Mid-Test Run

**What goes wrong:**
On the free tier, Gemini 2.5 Flash has a limit of approximately 10 RPM and 250 RPD (requests per day). A cold-start validation run — which involves the Gemini agent reading docs, navigating the dashboard via Playwright, dispatching multiple jobs, and synthesizing findings — can easily exceed 250 API calls over a multi-hour session. When the daily quota is exhausted, Gemini CLI returns `RESOURCE_EXHAUSTED (429)` and the agent stops responding. The validation run is incomplete, the checkpoint file is stuck, and Claude's orchestration session is waiting for an output that will never arrive.

Additionally, even within the RPM window, bursts of activity (e.g. the agent reads 20 doc pages back-to-back) can hit the per-minute limit, causing silent hangs — the CLI does not always surface 429s clearly; it sometimes just stalls (confirmed: Gemini CLI GitHub issue #10722, #16567).

**Why it happens:**
Multi-step validation tasks involve many rapid sequential model calls. The free tier is designed for exploratory development, not sustained automated test runs. A full CE + EE cold-start pass (install path + operator path + friction report) is likely to consume 100-250 model calls across both runs.

**How to avoid:**
- Use a paid API key (Tier 1 minimum, 300 RPM / 1M TPD) for the validation runs. The cost of a single validation run at Tier 1 is negligible (< $0.10 at Flash pricing) compared to the iteration cost of a stalled run.
- If using the free tier, break the validation into separate Gemini sessions: one session per phase (install, CE operator, EE operator, friction synthesis). Export checkpoint files between sessions to preserve state.
- Implement a retry wrapper around the Gemini CLI invocation in the orchestration script:
  ```bash
  for attempt in 1 2 3; do
    timeout 300 gemini -p "$PROMPT" && break
    sleep $((attempt * 60))  # back off 1min, 2min, 3min
  done
  ```
- Set `GEMINI_MODEL=gemini-2.0-flash` in the environment as a fallback (lower quota pressure than 2.5 Flash).
- Monitor quota consumption: after each agent phase, check remaining quota before starting the next.

**Warning signs:**
- Gemini CLI output stops mid-sentence with no error message (429 silent stall).
- `gemini` process is still running but producing no output for > 2 minutes.
- `RESOURCE_EXHAUSTED` appears in Gemini CLI stderr.
- The checkpoint file has not been updated for > 5 minutes during an expected active phase.

**Phase to address:** Phase 1 (LXC environment setup) and Phase 2 (Gemini agent scaffolding) — configure the API key tier and add retry/backoff logic before the first agent run.

---

### Pitfall 3: Gemini CLI Hangs in Non-Interactive/Headless Mode Inside LXC

**What goes wrong:**
Gemini CLI has confirmed bugs with non-interactive execution — particularly when running shell commands via its tool executor in headless mode. Issues confirmed in the GitHub tracker (issues #16567, #12362, #20433) include:

- CLI hangs for up to 300 seconds during initialization on headless Linux (Debian/Ubuntu Server) due to a `ripgrep` (`rg`) missing dependency. If `rg` is not installed in the LXC container, `gemini` hangs silently at "Initializing..." for the duration of the dbus timeout before falling back.
- The CLI can hang indefinitely when executing certain shell commands (curl, git) in non-interactive mode. This was partially fixed in v0.23.0 (PR #20893), but older versions remain affected.
- When running inside a container (Podman noted, likely also Docker-in-LXC), the interactive mode spin-lock busy-loop manifests (issue #17275).

**Why it happens:**
Gemini CLI was designed for interactive terminal use. Headless/piped mode is a secondary use case with fewer test cycles. The dbus secret service dependency causes a blocking wait when running on a server without a desktop environment.

**How to avoid:**
- Pin Gemini CLI to a version >= 0.23.0 (post-PR #20893 fix).
- Install `ripgrep` (`apt install ripgrep`) in the LXC container before running Gemini CLI.
- Set `GEMINI_API_KEY` in the environment and also set `KEYRING_BACKEND=null` (or `SECRET_SERVICE_AVAILABLE=false` if the env var is supported) to bypass dbus secret service lookup. Alternatively, pre-configure `~/.gemini/settings.json` with the API key so Gemini CLI does not query the keyring.
- Run Gemini with an explicit timeout wrapper: `timeout 600 gemini -p "$PROMPT"`. Never let the orchestrator wait indefinitely for Gemini output.
- Test headless mode explicitly during Phase 1 with a minimal prompt before the full validation run. Confirm Gemini CLI returns within 30 seconds before proceeding.

**Warning signs:**
- Gemini CLI prints "Initializing..." and then nothing for > 30 seconds.
- `ps aux` shows `gemini` process at 0% CPU but not exiting.
- Checkpoint file never receives the Gemini output file.
- `strace` shows `gemini` blocking on a dbus socket call.

**Phase to address:** Phase 1 (LXC environment setup) — test headless Gemini CLI operation as an explicit acceptance criterion before any validation scenario runs.

---

### Pitfall 4: Docker-in-LXC Networking — Caddy Binds to Container IP, Gemini Agent Cannot Reach Dashboard

**What goes wrong:**
Inside the LXC, Docker creates a bridge network (default `172.17.0.0/16`). The Caddy container binds port 443 to the bridge IP. From within the LXC (outside Docker's network namespace), the Axiom dashboard is at `https://172.17.0.X:443` — not `https://localhost:443`.

The Gemini agent's system prompt says "navigate to the dashboard at https://localhost:8443" (or whatever the doc says). Inside the LXC, `localhost` is the LXC itself — not the Docker host bridge. The agent hits a connection refused. If the Axiom compose maps host port 8443 to Caddy's 443 (`"8443:443"` is confirmed in `compose.server.yaml`), then `localhost:8443` from within the LXC **does** work for TCP — but only if the LXC's loopback resolves to the Docker host's published port. On a standard Incus bridge setup, this requires IP forwarding to be enabled on the host and the LXC's network interface to route to the host's loopback.

A more reliable pattern: the Axiom stack port 8443 is published to the LXC host's IP. The Gemini agent should be given the LXC host's `incusbr0` IP address (e.g. `10.77.183.1`) as the target, not `localhost`. This IP is stable across LXC restarts.

Additionally, Incus with `security.nesting=true` (required for Docker-in-LXC) on Ubuntu 24.04 with kernel 6.8.x can have AppArmor denial issues that break Docker networking inside the LXC (confirmed: Incus GitHub issue #791). The `pivot_root: permission denied` error prevents Docker containers from starting at all, which means no Axiom stack inside the LXC.

**Why it happens:**
Docker bridge networking creates an isolated L2 domain. LXC containers are not inside this domain. Addresses that look like "localhost" are scoped to the LXC's network namespace, not Docker's internal network. The AppArmor issue is Ubuntu 24.04-kernel-specific and not obvious from Incus documentation.

**How to avoid:**
- Enable Docker port publishing explicitly in the compose file (already done: `"8443:443"`) and verify from inside the LXC that `curl https://$(ip route show default | awk '{print $3}'):8443/` works. Use the gateway IP, not `localhost`.
- Set `SERVER_HOSTNAME` in the Axiom compose environment to the LXC's default gateway IP so Caddy's cert SAN includes it.
- In the Gemini agent's system prompt / GEMINI.md context, provide the correct `AXIOM_URL=https://<gateway-ip>:8443` rather than localhost.
- For the AppArmor/Ubuntu 24.04 issue:
  - Check: `incus config show <container> | grep security.nesting`
  - If Docker containers fail to start with `pivot_root: permission denied`, run `incus config set <container> raw.apparmor "pivot_root,"` to add the missing AppArmor rule, or upgrade to the mainline kernel (6.8.0-060800-generic) which does not block this.
- Test Docker container startup inside the LXC as an explicit Phase 1 acceptance criterion.

**Warning signs:**
- Gemini agent reports "connection refused" when navigating to the dashboard URL.
- `curl https://localhost:8443` from inside the LXC returns `Connection refused` even though Docker is running.
- Docker containers inside the LXC fail to start with `pivot_root: permission denied` in journalctl.
- `docker ps` inside the LXC shows all containers as `Exiting (1)` on startup.

**Phase to address:** Phase 1 (LXC environment setup) — verify Docker-in-LXC networking from the LXC's perspective before any Gemini session starts. Determine the correct reachable IP and put it in the agent's context.

---

### Pitfall 5: Gemini Agent Shortcuts Via Codebase Knowledge — "First User" Validity Fails

**What goes wrong:**
The v14.0 milestone requires Gemini to act as a "first-time user" who discovers the product solely through documentation and the UI. The validity of the cold-start test depends on Gemini not having access to the codebase, internal API structure, or secrets.

Failure modes:
1. **GEMINI.md contamination**: If the validation LXC contains a clone of the full master_of_puppets repository, Gemini CLI automatically reads `GEMINI.md` in the working directory. `GEMINI.md` references internal architecture, key file paths, and known limitations. The agent immediately has codebase knowledge and cannot act as a first-time user.
2. **`.gemini/` history bleed**: Gemini CLI stores conversation history in `~/.gemini/history/<project_hash>`. If the same user account runs both development sessions and validation sessions, prior context (codebase exploration, bug fixes) leaks into the validation session.
3. **System prompt injection**: If the orchestration script injects internal codebase details (file paths, admin credentials from `secrets.env`) into the Gemini prompt to "help it set up", it bypasses the first-user constraint.

**Why it happens:**
Convenience. The easiest way to give Gemini the Axiom stack is to clone the full repo into the LXC. This is correct for the install step but wrong for the operator-path validation step.

**How to avoid:**
- Structure the LXC working directory as two isolated zones:
  - `/root/axiom-install/` — contains only the installer artifacts (compose file, env template). No GEMINI.md, no source code. Gemini runs from here during install validation.
  - `/root/axiom-docs/` — contains a checked-out copy of `docs/site/` only. Gemini reads docs from here during operator validation.
- Use a fresh `~/.gemini/` directory for each validation session: `export HOME=/root/validation-home` before invoking `gemini`, ensuring no history contamination.
- The Gemini agent's starting prompt must be explicit: "You are a first-time operator. You have access only to the documentation at `/root/axiom-docs/`. You do not have access to the source code. Do not assume any knowledge beyond what the documentation provides."
- Admin credentials (JOIN_TOKEN, ADMIN_PASSWORD) needed for setup are provided via the checkpoint/steering mechanism, not pre-loaded into the Gemini context. The agent must discover the login UI, not have credentials injected.

**Warning signs:**
- Gemini references internal file paths like `puppeteer/agent_service/main.py` or mentions `DATABASE_URL` format without reading docs.
- Gemini uses API paths or parameter names not documented in the public docs site.
- Gemini skips steps that a real first-user would need (e.g., skips TLS bootstrap because it "knows" the cert is in `certs-volume`).
- `ls ~/.gemini/history/` shows entries from prior development sessions in the same HOME.

**Phase to address:** Phase 2 (Gemini agent scaffolding) — define the LXC directory structure and HOME isolation before the first agent session. Test that Gemini cannot read source code files from within its working directory.

---

### Pitfall 6: Ed25519 Licence Expires During the EE Validation Run

**What goes wrong:**
The EE licence key is signed with an expiry timestamp. If the licence was pre-generated with a short validity window (e.g. 30 days, as used in v11.1 testing), there is a risk that:
1. The licence expires between the CE run and the EE run if the validation takes multiple days.
2. The licence expires mid-run if the EE validation covers a long test sequence (licence check is startup-only per PROJECT.md, but any stack restart during EE testing re-validates and will fail).
3. A licence generated with a clock-skewed host has a start time in the future (appears invalid immediately) or expiry in the past (valid only on the clock-skewed host).

Axiom's licence validation is described as "startup-only" (DIST-05 is deferred), so a running EE stack continues operating even after licence expiry — but any restart during the test run will gate on the expired licence and refuse to start EE features.

**Why it happens:**
Test licences are generated once and stored. The connection between "licence generation date" and "validation run date" is easy to lose track of across milestones.

**How to avoid:**
- Generate the EE test licence immediately before each validation run, not during stack setup days earlier. Use a validity window of 72 hours minimum from generation time.
- Store the licence generation command and the test keypair in the LXC provisioning script so they are always fresh: `python generate_ee_licence.py --days 7 > /root/axiom_ee_licence.key`.
- Before starting the EE run, verify the licence is valid and its expiry is at least 2 hours away: decode the base64 payload and check the `exp` field.
- Avoid restarting the Axiom stack during the EE operator validation phase once it is confirmed running with EE features loaded. Schedule any required restarts for before EE operator testing begins.
- Add a pre-flight check to the EE validation script: `GET /api/admin/features` must return `ee_status: loaded` before the EE operator tests begin.

**Warning signs:**
- `GET /api/admin/features` returns `ee_status: not_loaded` on a stack that should have EE.
- EE-gated routes return 402 even though the `axiom-ee` dev wheel is installed.
- Stack startup logs show `Licence expired` or `Licence not yet valid`.
- The `exp` field in the decoded licence JSON is in the past.

**Phase to address:** Phase 3 (EE test infrastructure setup) — add licence freshness check as a pre-flight step. Regenerate the licence in the LXC provisioning script, not manually.

---

### Pitfall 7: PowerShell Jobs Fail — pwsh Not in Docker Node Image

**What goes wrong:**
v12.0 unified the `script` task type to support Python, Bash, and PowerShell via container temp-file mounts. The node runtime executes PowerShell scripts with `pwsh -File <tempfile>`. This requires `pwsh` (PowerShell Core) to be present in the Docker image the node container runs.

The base node image (`localhost/master-of-puppets-node:latest`, built from `puppets/Containerfile.node`) likely does not include `pwsh` — PowerShell is a 200MB+ install that would significantly bloat the base image. If a cold-start validation test dispatches a PowerShell job to a node using the base image, the job will fail with exit code 127 (`pwsh: command not found`). The failure looks identical to a crashed script (exit code, no stdout), making it hard to distinguish from a logic error in the test script.

Additionally, the Microsoft Container Registry deprecated the standalone PowerShell Docker images in 2025 (confirmed by search results). The correct approach is `mcr.microsoft.com/dotnet/sdk:8.0` or installing `pwsh` via APT from the Microsoft package feed.

**Why it happens:**
PowerShell support is tested with custom Foundry-built images in development. Cold-start validation uses whatever the base node image provides. The PowerShell test is added to the validation matrix without verifying the base image has `pwsh`.

**How to avoid:**
- Build a dedicated PowerShell-capable node image for the cold-start validation: start from the base node image and add `pwsh` via the Microsoft APT feed. Use this image for the PowerShell job test node.
- Alternatively, create a Foundry blueprint that adds PowerShell and build the validation node image via Foundry as part of the EE operator path test (this simultaneously validates Foundry and PowerShell support).
- Verify `pwsh` availability before dispatching the PowerShell test job: `docker exec <node_container> which pwsh` must return `/usr/bin/pwsh`.
- If using a pre-built Foundry image, tag and push it to the local registry before the validation run starts.

**Warning signs:**
- PowerShell job returns exit code 127 with stderr `pwsh: not found`.
- The node's execution log shows `OSError: [Errno 2] No such file or directory: 'pwsh'`.
- `docker exec <node_container> pwsh --version` returns "command not found".
- All Python and Bash jobs succeed, only PowerShell jobs fail.

**Phase to address:** Phase 3 (LXC node provisioning and Docker image preparation) — include `pwsh` installation in the node image build step for the PowerShell test scenario.

---

### Pitfall 8: Checkpoint File Deadlock — Agent Waits for Steering, Claude Session Times Out

**What goes wrong:**
The file-based checkpoint protocol works as follows: Gemini writes a checkpoint file requesting a decision, Claude reads it and writes a steering file, Gemini reads the steering file and continues. If either side stalls:

1. **Claude session timeout**: If the Claude orchestration session is idle (waiting for Gemini to produce a checkpoint) for more than the session idle timeout, the Claude session is terminated. When the checkpoint arrives, there is no Claude session to read it and provide steering. Gemini waits indefinitely for a steering response that will never come.

2. **Gemini rate-limited while writing checkpoint**: Gemini hits a 429 error while in the middle of composing the checkpoint file. The file is written partially. Claude reads a malformed checkpoint JSON, cannot parse it, and either crashes or writes invalid steering. Gemini receives garbage steering and produces nonsense output.

3. **Stale checkpoint from prior run**: The checkpoint directory from a previous partial run still contains a `CHECKPOINT_COMPLETE` file. Gemini reads it at startup, believes the session is already complete, and exits without running any tests.

4. **File locking on the shared volume**: If the checkpoint directory is on a volume shared between the LXC and the host, and the LXC uses a filesystem without proper POSIX fcntl locks (e.g., 9p/virtio), file write visibility may be delayed. Gemini writes the checkpoint, the delay means Claude reads stale content.

**Why it happens:**
File-based IPC is simple to implement but brittle. Race conditions between the writer finishing and the reader polling are inherent. Long-lived agent sessions are vulnerable to session timeouts on either side.

**How to avoid:**
- Use atomic writes for checkpoint files: Gemini writes to a `.tmp` file first, then renames atomically. Claude polls for the final filename, not the `.tmp` file.
- Define a maximum wait time on both sides: Gemini waits at most 10 minutes for a steering file; Claude checks for checkpoint files every 60 seconds with a 30-minute maximum.
- Clear the checkpoint directory at the start of each validation run. The provisioning script should `rm -f /root/checkpoints/*` before invoking Gemini.
- Use a local filesystem for checkpoints (not a shared 9p/virtio volume). Write checkpoints to a path inside the LXC's native ext4 filesystem.
- If the Claude session times out, restart it with the last checkpoint file as context: the orchestrator should save the last checkpoint path so the session can resume rather than restart.

**Warning signs:**
- Checkpoint file exists but has no corresponding steering file after > 15 minutes.
- Checkpoint file is 0 bytes or truncated (partial write during rate-limit error).
- Multiple checkpoint files with the same name from prior runs.
- Gemini exits 0 (success) but no validation output was produced (read stale COMPLETE checkpoint).

**Phase to address:** Phase 2 (Gemini agent scaffolding and checkpoint protocol) — implement atomic write + cleanup procedures before the first validation run. Test the checkpoint round-trip explicitly with a mock Gemini session.

---

## Technical Debt Patterns

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| Using `ignore_https_errors=True` in Playwright instead of injecting Root CA | Simpler setup, no cert export step | Any TLS error (not just self-signed) is silently bypassed; network attacks undetected | Acceptable for isolated validation LXC only — never in production or shared environments |
| Using free-tier Gemini API key for validation | Zero cost | 429 rate limit stops the run at any point; 250 RPD makes a full CE+EE pass infeasible | Never for a full validation run — use paid tier or split into multiple sessions |
| Running Gemini in a HOME directory with prior dev history | No setup required | Prior codebase knowledge leaks into "first user" test; invalidates the test premise | Never — always use a fresh HOME for validation sessions |
| Pre-generating EE licence key weeks before the run | Simpler pre-staging | Licence may expire before or during the run | Never — generate within 24h of the planned run |
| Skipping PowerShell node image build | Faster test setup | PowerShell jobs always fail with exit 127; PowerShell test path is untested | Never — PowerShell is an explicit validation requirement |
| Sharing the checkpoint directory on a 9p/virtio volume | Convenient access from host | File visibility delays cause stale reads; POSIX lock semantics not guaranteed | Never — use native LXC filesystem for checkpoints |
| Running Gemini CLI without pinning to a specific version | Always gets latest features | Non-interactive hangs and 429-silent-stall behaviour vary by version; untested versions introduce flakiness | Never for automated runs — pin to a tested version |

---

## Integration Gotchas

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|------------------|
| Playwright + Caddy self-signed TLS | Trust Root CA via `update-ca-certificates` and expect Chromium to respect it | Install Root CA into Chromium's NSS DB via `certutil`, or use `ignore_https_errors=True` at browser launch |
| Gemini CLI + LXC headless Linux | Run without installing `ripgrep` | `apt install ripgrep` before running `gemini`; prevents 300s initialization hang |
| Gemini CLI + non-interactive API calls | Assume the CLI returns promptly for all shell commands | Wrap all `gemini` invocations with `timeout 300`; never wait indefinitely |
| Gemini CLI + API key | Store key in keyring (system default) | Set `GEMINI_API_KEY` env var explicitly; configure `~/.gemini/settings.json` to bypass dbus/keyring lookup |
| Docker-in-LXC + Axiom port binding | Access Axiom via `localhost:8443` inside LXC | Use the LXC's default gateway IP (Docker host bridge IP); verify with `ip route show default | awk '{print $3}'` |
| Caddy TLS SAN + LXC networking | Generate cert without `SERVER_HOSTNAME` and expect `localhost` to work from inside LXC | Set `SERVER_HOSTNAME` to the LXC-accessible IP before starting the stack; regenerate cert if SANs were already written to the volume |
| Ed25519 EE licence + clock skew | Pre-generate licence on a system with incorrect clock | Generate licence on the same host that will run the validation; verify system time before generation |
| PowerShell jobs + base node image | Assume the base image has `pwsh` | Build a dedicated PowerShell-capable node image or use a Foundry blueprint that includes `pwsh` |
| Checkpoint files + shared volumes | Write checkpoints to a 9p/virtio-shared directory | Write to native LXC ext4 filesystem; share results with host via `incus file pull` after validation |
| Gemini "first user" + GEMINI.md | Clone full repo into LXC working directory | Separate install artifacts from source; use an isolated HOME for the Gemini session |

---

## Performance Traps

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|----------------|
| Gemini CLI context saturation | Agent stops referencing earlier findings; starts repeating initial setup steps | Break validation into scoped sessions (install, CE operator, EE operator); each session < 30 turns | After ~50 turns in a single session on a large codebase |
| Playwright screenshot on every navigation | Test script accumulates 100+ 2MB PNGs; disk fills inside LXC | Save screenshots only on assertion failure; use `page.screenshot(path=...)` selectively | After ~50 navigations in a test that captures every step |
| Docker image pull inside LXC on every test run | Each run re-pulls `pwsh` base image (400MB+) | Pre-pull and tag all images before the validation run; use `docker image ls` to verify | On networks with < 10 Mbps; or when Docker Hub rate limits apply (100 pulls/6h for free accounts) |
| Axiom stack startup race inside LXC | Gemini agent tries to access dashboard while Caddy/agent are still starting | Add a health-check wait loop in the provisioning script: `until curl -sk https://<host>:8443/api/health; do sleep 2; done` | Immediately on first run without startup gate |
| Concurrent Playwright + Gemini API calls | 429 errors triggered by combined RPM usage if both hit the API simultaneously | Run Playwright scripts synchronously from within the Gemini session; never in parallel threads | Any time Playwright test runs while Gemini is also making API calls |

---

## Security Mistakes

| Mistake | Risk | Prevention |
|---------|------|------------|
| Storing EE test private key alongside production keys in `toms_home/.agents/tools/secrets/` | Test key mixed with production keys; risk of signing production licences with test key | Store EE test keypair in a dedicated directory inside the validation LXC only; never commit test private keys to any repository |
| Running Playwright with `ignore_https_errors=True` against a production stack | TLS errors from a genuine MITM attack would be silently ignored | Restrict `ignore_https_errors=True` to validation LXC only; confirm with `incus list` that the stack IP is inside the LXC network range |
| Embedding ADMIN_PASSWORD in the Gemini system prompt | Admin credential exposed in prompt history stored at `~/.gemini/history/` | Inject ADMIN_PASSWORD only via the checkpoint/steering mechanism, not the initial prompt; clear `~/.gemini/history/` after the validation run |
| Using the same Gemini API key for development and validation | Validation run exhausts the daily quota needed for development work | Use a separate API key for validation runs; set a spend limit on the validation key |
| Leaving the EE dev wheel installed in the production stack after validation | Production stack accepts test licences signed with the dev key | Use a separate Docker compose override for EE validation; never install the dev wheel into the production named volume |

---

## UX Pitfalls

(These apply to the friction report quality and agent experience design, not end-user UX.)

| Pitfall | Impact | Better Approach |
|---------|--------|-----------------|
| Gemini agent given too broad a mandate per session | Agent context saturates; later findings are lower quality than early findings | Scope each Gemini session to one workflow (install, CE operator, EE features); combine findings in the friction report |
| Friction report captures "agent got confused" as a product issue | Misattributes Gemini CLI limitations (rate limits, context saturation) as Axiom UX problems | Distinguish agent environment issues from genuine product friction in the report template |
| No baseline comparison in friction report | Cannot tell if findings are regressions vs. long-standing issues | Reference the v11.1 gap report findings when writing the friction synthesis; note which findings are new vs. known |
| Agent success defined as "no errors" | A smooth but silent run does not validate EE features were actually exercised | Define per-scenario acceptance criteria: specific API responses, dashboard state changes, or execution records that confirm the feature was used |
| Checkpoint steering injects too much help | Agent succeeds because the orchestrator compensated for every friction point | Checkpoint steering is for unblocking (e.g. providing credentials); it must not substitute for features the product should provide |

---

## "Looks Done But Isn't" Checklist

- [ ] **TLS trust verified**: `curl -v https://<gateway-ip>:8443/` from inside the LXC returns 200 without `--insecure`. If using `ignore_https_errors=True` instead, confirm the browser can reach the login page and the page renders correctly (not a blank HTTPS error page).
- [ ] **Gemini CLI headless confirmed**: `timeout 30 gemini -p "Say hello"` from the validation HOME returns a response within 30 seconds. Hang here means ripgrep missing or keyring blocking.
- [ ] **Docker networking verified**: `docker ps` inside the LXC shows all Axiom containers as `Up`. `curl http://localhost:8080/+api` (devpi) and `curl -sk https://<gateway>:8443/api/health` both succeed.
- [ ] **EE dev wheel active**: `GET /api/admin/features` returns `ee_status: loaded`. Verify before starting any EE scenario.
- [ ] **EE licence freshness**: Decode the licence payload and check `exp` field is at least 2 hours in the future.
- [ ] **PowerShell node image ready**: `docker exec <ps_node_container> which pwsh` returns a path. Dispatch a trivial PowerShell job (`Write-Host "ok"`) and verify it reaches COMPLETED before starting the full test matrix.
- [ ] **Gemini working directory isolated**: `ls <gemini-working-dir>` shows no `CLAUDE.md`, `GEMINI.md`, or `puppeteer/` source directories. Gemini cannot read source code.
- [ ] **Checkpoint directory clean**: `ls /root/checkpoints/` is empty before each validation run. No stale files from prior runs.
- [ ] **API key tier confirmed**: `echo $GEMINI_API_KEY` is set and the key's tier is confirmed via AI Studio. Free tier requires multi-session approach. Paid tier confirmed before starting.
- [ ] **AppArmor / Docker nesting verified**: `docker run --rm hello-world` inside the LXC completes successfully. If this fails, AppArmor pivot_root issue needs resolution before any Axiom stack testing.

---

## Recovery Strategies

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|----------------|
| TLS SAN mismatch blocks Playwright | LOW | Set `SERVER_HOSTNAME` in compose env; `docker compose down; docker compose up -d`; Root CA and cert are regenerated on next start; re-export Root CA |
| 429 rate limit exhausted mid-run | LOW-MEDIUM | Wait for quota reset (midnight UTC for daily limits); resume from last checkpoint file; switch to paid tier for remainder |
| Gemini CLI hangs in headless mode | LOW | Install `ripgrep`; clear `~/.gemini/history/`; upgrade CLI version; restart with `timeout` wrapper |
| Docker-in-LXC AppArmor blocks pivot_root | MEDIUM | Check Ubuntu kernel version; if 6.8.x with broken AppArmor: `incus config set <container> raw.apparmor "pivot_root,"` and restart LXC; or upgrade to mainline kernel |
| Gemini first-user contamination discovered mid-run | HIGH | Invalidate the run; reset to fresh HOME; clear source code from working directory; restart from Phase 1 |
| EE licence expired before/during run | LOW | Regenerate licence with `python generate_ee_licence.py --days 7`; restart Axiom stack to load new licence; verify `ee_status: loaded` |
| PowerShell node has no pwsh | LOW | `docker exec <node> apt-get install -y powershell` (if network available) or rebuild node image with pwsh; re-enroll node if image changed |
| Checkpoint deadlock (no steering response) | LOW-MEDIUM | Kill `gemini` process; read checkpoint file to determine what decision was needed; write steering file manually; restart Gemini from last state |

---

## Pitfall-to-Phase Mapping

| Pitfall | Prevention Phase | Verification |
|---------|------------------|--------------|
| Caddy TLS SAN mismatch + Chromium cert trust (P1) | Phase 1 — LXC environment setup | `curl -v https://<gateway>:8443/api/health` succeeds without `--insecure` from inside the LXC |
| Gemini 429 rate limit stalls run (P2) | Phase 1+2 — API key tier confirmation + retry wrapper | `gemini -p "hello"` succeeds 10 times in 1 minute without 429 errors |
| Gemini CLI headless hang (P3) | Phase 1 — headless smoke test | `timeout 30 gemini -p "Say hello"` returns within 30 seconds |
| Docker-in-LXC networking + AppArmor (P4) | Phase 1 — Docker nesting verification | `docker run --rm hello-world` succeeds inside LXC; Axiom stack ports reachable from LXC network namespace |
| First-user codebase contamination (P5) | Phase 2 — agent scaffolding and HOME isolation | `ls $GEMINI_HOME` shows no source code; Gemini cannot access GEMINI.md or CLAUDE.md |
| EE licence expiry (P6) | Phase 3 — EE test infrastructure | Licence decoded `exp` > now + 2h; `ee_status: loaded` confirmed before EE tests |
| PowerShell node missing pwsh (P7) | Phase 3 — node image preparation | `docker exec <ps_node> which pwsh` returns a path; trivial PowerShell job completes |
| Checkpoint protocol deadlock (P8) | Phase 2 — checkpoint design and testing | Mock round-trip (write checkpoint → write steering → Gemini reads steering) completes in < 60 seconds |

---

## Sources

- Direct inspection: `puppeteer/cert-manager/entrypoint.sh` — SANs are `localhost,127.0.0.1` plus optional `SERVER_HOSTNAME`; cert signed by Axiom Root CA (not a public CA)
- Direct inspection: `puppeteer/Caddyfile` — TLS via `/etc/certs/caddy.crt`; port 443/80 binding
- Direct inspection: `puppeteer/compose.server.yaml` — port `"8443:443"` published; `cert-manager` container generates TLS
- PROJECT.md v14.0 milestone — confirms: Gemini CLI as first-user agent, file-based checkpoint steering, CE+EE cold-start, PowerShell job runtime, Ed25519 licence gating
- Playwright GitHub issue #4785 — "Playwright Chromium ignores root CA certificates installed manually" — confirmed: `update-ca-certificates` is insufficient; Chromium uses NSS store
- Gemini CLI GitHub issue #16567 — "Gemini CLI consistently hangs when running a command in non-interactive mode" — fixed in v0.23.0 (PR #20893)
- Gemini CLI GitHub issue #20433 — "CLI hangs on 'Initializing...' for 3-5 minutes in headless Linux due to ripgrep (rg) missing"
- Gemini CLI GitHub issue #17275 — "Interactive mode hangs in a busy-loop when run inside a Podman container"
- Incus GitHub issue #791 — "Nesting (docker) in containers broken on Ubuntu 24.04" — AppArmor `pivot_root: permission denied`; workaround: mainline kernel or `raw.apparmor` override
- Gemini API rate limits: free tier Gemini 2.5 Flash ~10 RPM / 250 RPD — https://ai.google.dev/gemini-api/docs/rate-limits
- Gemini CLI 429 issues: https://github.com/google-gemini/gemini-cli/issues/10722
- Microsoft PowerShell in Docker (2025): standalone images deprecated; current path is `mcr.microsoft.com/dotnet/sdk:8.0` — https://learn.microsoft.com/en-us/powershell/scripting/install/powershell-in-docker
- Playwright TLS workarounds: https://www.browserstack.com/guide/playwright-ignore-certificate-errors

---
*Pitfalls research for: Axiom v14.0 CE/EE Cold-Start Validation — Gemini CLI agent, Python Playwright, Docker-in-LXC (Incus), file-based checkpoint protocol, Ed25519 EE licence gating, self-signed Caddy TLS*
*Researched: 2026-03-24*
