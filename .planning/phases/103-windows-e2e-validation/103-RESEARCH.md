# Phase 103: Windows E2E Validation - Research

**Researched:** 2026-03-31
**Domain:** Windows E2E validation — paramiko SSH orchestration, PowerShell job signing, Windows docs gap-fill, friction cataloguing
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Windows docs pre-audit:**
- Pre-audit all getting-started docs before the first validation run — add PowerShell tabs/sections where missing, then validate
- Scope: enroll-node.md, first-job.md, prerequisites.md at minimum; Claude audits the full getting-started directory and fills any other gaps found
- No separate Windows guide — same pages as Linux, Windows tabs alongside the existing Linux/macOS tabs
- All Windows shell interactions use PowerShell (pwsh) throughout — no CMD, no WSL2 bash

**Orchestration method:**
- paramiko SSH to drive Dwight (pattern already established in test_ssh.py; Dwight creds in secrets.env)
- New file: `mop_validation/scripts/run_windows_scenario.py` with `dwight_exec()`, `dwight_push()`, `wait_for_stack_dwight()` helpers — parallel structure to run_ce_scenario.py
- Dashboard state verification (node ONLINE, job COMPLETED) via API calls from the Linux host: `requests.get('https://192.168.50.149:8443/...')` — no Playwright needed

**Stack architecture on Dwight:**
- Full Axiom orchestrator stack runs on Dwight (not just the node) — compose.cold-start.yaml started on Dwight via SSH
- Node connects back to the orchestrator via `host.docker.internal:8001` (Docker Desktop Windows standard networking)
- AGENT_URL in node config: `https://host.docker.internal:8001`

**Validation method (carried from Phase 102):**
- Claude subagent runs the validation (not Gemini)
- Persona: pure docs-follower — no prior Axiom knowledge; if the docs don't say it, the agent doesn't do it
- Golden path: install → forced password change → enroll node → first PowerShell job → verify output
- Blocker handling: stop at first blocker, fix (docs AND code/config), full restart from top
- Iterations continue until golden path completes cleanly end-to-end

**PowerShell job signing:**
- Signing keypair: reuse existing signing key from the Linux host (mop_validation/secrets/) — no new key gen needed on Dwight
- Signing method: Python via pip (cryptography library) — same approach as Linux docs; Python is available on Windows
- First job content: a simple PowerShell Hello World — `Write-Host 'Hello from Axiom on Windows'` — keeps it minimal, proves PowerShell execution on the node

**Friction report:**
- File: `mop_validation/reports/FRICTION-WIN-103.md`
- Format: synthesise_friction.py compatible (same as prior FRICTION files)
- At phase close: run synthesise_friction.py to produce the synthesised summary as sign-off artifact

### Claude's Discretion
- Exact paramiko invocation for running pwsh commands (exec_command syntax for PowerShell on Windows SSH server)
- Whether to use password auth or key-based auth for Dwight SSH (both are in secrets.env)
- Exact structure of dwight_exec() / dwight_push() helpers
- How to handle Windows line endings (CRLF) when pushing files to Dwight via paramiko

### Deferred Ideas (OUT OF SCOPE)

None — discussion stayed within phase scope
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| WIN-01 | Fresh Windows cold-start deployment completes on Dwight (SSH, credentials from `mop_validation/secrets.env`) via Docker stack, following the Quick Start (Windows) guide | Covered by: paramiko SSH pattern, compose.cold-start.yaml analysis, Docker Desktop Windows networking |
| WIN-02 | Windows stack uses PowerShell (PWSH) — not CMD — for all shell interactions | Covered by: Windows OpenSSH default shell research, pwsh exec_command patterns, docs gap analysis |
| WIN-03 | Admin/admin first login triggers forced password change prompt, which completes successfully | Covered by: Phase 102 research carries forward — same API mechanism, same PowerShell curl equivalent (Invoke-WebRequest) |
| WIN-04 | Node enrollment succeeds on Dwight following documentation | Covered by: enroll-node.md Windows gap analysis, host.docker.internal AGENT_URL confirmation, PowerShell Join-Token copy steps |
| WIN-05 | First PowerShell job dispatches, executes, and shows output | Covered by: first-job.md Windows gap analysis, PowerShell signing approach, node image PowerShell capability confirmation |
| WIN-06 | All friction found during the Windows run is catalogued and fixed | Covered by: FRICTION file format, synthesise_friction.py --files patch from Phase 102 |
</phase_requirements>

---

## Summary

Phase 103 is structurally identical to Phase 102 (Linux E2E) but replaces LXC/incus with paramiko SSH to Dwight (a Windows machine at 192.168.50.149), and replaces bash with PowerShell throughout. The orchestration pattern is: pre-audit docs to add missing PowerShell tabs, then SSH into Dwight to reset the Docker stack, invoke a Claude subagent persona via SSH that follows the Windows docs from first principles, verify state via API calls from the Linux host, and iterate until the golden path passes cleanly.

The key differences from Phase 102 that require research and planning attention are: (1) the SSH transport to Dwight must invoke `pwsh -Command "..."` rather than `bash -c`, which requires understanding Windows OpenSSH's default shell behaviour and the correct paramiko invocation; (2) file pushes to Dwight must use paramiko SFTP and must ensure LF line endings in any config files that will be bind-mounted into Linux containers; (3) the docs have significant PowerShell gaps — enroll-node.md and first-job.md currently have no PowerShell tabs, and first-job.md has no Windows signing path at all; and (4) Dwight's secrets.env credentials are not yet present in mop_validation/secrets.env and must be added as a Wave 0 task.

The signing keys already exist on the Linux host (`/home/thomas/Development/master_of_puppets/secrets/signing.key` and `verification.key`) — they will be pushed to Dwight via paramiko SFTP and reused. The Claude subagent running inside the Dwight SSH session will sign jobs using Python's `cryptography` library with these pre-existing keys.

**Primary recommendation:** Write `run_windows_scenario.py` as a thin paramiko wrapper parallel to `run_ce_scenario.py`, pre-audit and fix the three docs files before the first validation run, then invoke the same Claude subagent pattern used in Phase 102 with a Windows-adapted prompt that uses PowerShell commands throughout.

---

## Standard Stack

### Core Infrastructure

| Tool | Version | Purpose | Why Standard |
|------|---------|---------|--------------|
| paramiko | system package (pip) | SSH transport to Dwight — `exec_command`, SFTP file push/pull | Already established in `test_ssh.py`; no alternative for SSH-over-Python |
| `test_ssh.py` | existing | `read_secrets()` helper, paramiko connection pattern | Reusable as-is; parse Dwight creds from secrets.env |
| `run_ce_scenario.py` | existing | Structural template: wait loop, friction pull, reset pattern | `run_windows_scenario.py` mirrors this structure |
| `run_linux_e2e.py` | existing | Exact orchestrator template — pre-flight, push, subagent, pull, summary | Mirror this structure for Windows |
| `synthesise_friction.py` | existing (needs `--files` patch from Phase 102) | Reads FRICTION-WIN-103.md and produces summary report | Sign-off artifact per CONTEXT.md |
| Python `cryptography` | pip | Ed25519 signing for PowerShell job on Dwight | Already used in test_local_stack.py; same approach documented for Linux |
| `requests` | pip | API verification from Linux host against `https://192.168.50.149:8443` | Already used across validation scripts |

### Docs Under Test (Pre-Audit Scope)

| Doc | Current Windows Coverage | Gap Identified |
|-----|--------------------------|----------------|
| `docs/docs/getting-started/install.md` | Comprehensive — PowerShell tabs on all steps, Windows troubleshooting section | No gap |
| `docs/docs/getting-started/prerequisites.md` | Complete — Docker Desktop, WSL2, port check, PowerShell version | No gap |
| `docs/docs/getting-started/enroll-node.md` | CLI tab uses `bash` only; Option B YAML only; no PowerShell equivalent | **GAP: add PowerShell tabs to CLI step and Option B** |
| `docs/docs/getting-started/first-job.md` | Step 0 uses Python heredoc (`python3 - <<'EOF'`) and `openssl` — no PowerShell path; Manual Setup uses bash `curl` | **GAP: add PowerShell signing + dispatch tab** |

### Existing Signing Keys

| File | Path | Usage |
|------|------|-------|
| `signing.key` | `/home/thomas/Development/master_of_puppets/secrets/signing.key` | Private key — push to Dwight via SFTP |
| `verification.key` | `/home/thomas/Development/master_of_puppets/secrets/verification.key` | Public key — push to Dwight, register in Axiom |

---

## Architecture Patterns

### Recommended Project Structure (new files for Phase 103)

```
mop_validation/scripts/
├── run_windows_e2e.py              # Phase 103 orchestrator (new)
├── windows_validation_prompt.md   # Subagent persona + golden path (new)
└── run_windows_scenario.py        # paramiko helper library (new)

mop_validation/reports/
└── FRICTION-WIN-103.md            # Output from validation run
```

### Pattern 1: paramiko SSH to Dwight — `dwight_exec()`

**What:** Thin wrapper around `paramiko.SSHClient.exec_command()` that connects to Dwight and runs a PowerShell command.

**Critical detail — Windows OpenSSH default shell:** Windows OpenSSH Server defaults to `cmd.exe` as the default shell, not PowerShell. This means `exec_command("docker ps")` will invoke cmd.exe. To guarantee PowerShell is used, always prefix commands explicitly:

```python
# Source: Windows OpenSSH documentation + paramiko docs
# CORRECT — explicitly invoke pwsh for every command
stdin, stdout, stderr = client.exec_command('pwsh -Command "docker ps"')

# WRONG — relies on default shell being pwsh (cmd.exe is the default)
stdin, stdout, stderr = client.exec_command("docker ps")
```

**Alternative — change default shell on Dwight via registry:** If Dwight has been configured with PowerShell as default shell (via `New-ItemProperty -Path 'HKLM:\SOFTWARE\OpenSSH' -Name DefaultShell -Value 'C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe'`), bare commands work. But the orchestrator must NOT rely on this — always prefix `pwsh -Command`.

**Complete `dwight_exec()` pattern:**

```python
# Source: paramiko documentation, test_ssh.py established pattern
import paramiko
import time

def _connect_dwight(secrets: dict) -> paramiko.SSHClient:
    """Open a paramiko SSH connection to Dwight. Caller is responsible for .close()."""
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    ip = secrets["dwight_ip"]           # 192.168.50.149
    username = secrets["dwight_username"]  # dwight\drear (or just drear)

    # Try key-based auth first, fall back to password
    key_path = "/home/thomas/Development/mop_validation/external_client_ed25519"
    try:
        client.connect(ip, username=username, key_filename=key_path, timeout=15)
    except Exception:
        password = secrets["dwight_password"]
        client.connect(ip, username=username, password=password, timeout=15)
    return client


def dwight_exec(cmd: str, timeout: int = 60, secrets: dict = None) -> tuple:
    """
    Run a PowerShell command on Dwight via SSH.

    cmd is the PowerShell command body — do NOT include 'pwsh -Command' prefix.
    Returns (stdout_text, stderr_text, exit_code).

    Example:
        stdout, stderr, rc = dwight_exec("docker compose -f C:\\workspace\\compose.cold-start.yaml ps")
    """
    client = _connect_dwight(secrets)
    try:
        # Always explicitly invoke pwsh — Windows SSH defaults to cmd.exe
        full_cmd = f'pwsh -NoProfile -NonInteractive -Command "{cmd}"'
        stdin, stdout, stderr = client.exec_command(full_cmd, timeout=timeout)
        stdout_text = stdout.read().decode("utf-8", errors="replace")
        stderr_text = stderr.read().decode("utf-8", errors="replace")
        exit_code = stdout.channel.recv_exit_status()
        return stdout_text, stderr_text, exit_code
    finally:
        client.close()
```

**For multi-line PowerShell or commands with embedded quotes**, pass via stdin instead of the command string to avoid quoting hell:

```python
# For complex multi-line scripts — use invoke_shell or pass as script file
# Preferred: push the script to Dwight as a .ps1 file, then execute it
client.exec_command('pwsh -NoProfile -File C:\\workspace\\validate.ps1', timeout=timeout)
```

### Pattern 2: File Push to Dwight — `dwight_push()`

**What:** SFTP file transfer from Linux host to Dwight.

**CRLF warning:** paramiko SFTP transfers files as binary — no line ending conversion. Config files that will be bind-mounted into Linux containers (e.g., `compose.cold-start.yaml`, `signing.key`) must have LF endings. Python strings use `\n` by default, so files written with `open(..., 'w')` on Linux will have LF. If pushing pre-existing files, verify they have LF endings before transfer.

```python
# Source: paramiko SFTP documentation
def dwight_push(local_path: str, remote_path: str, secrets: dict) -> None:
    """
    Push a local file to Dwight via SFTP.

    remote_path: Windows-style path (e.g., r'C:\workspace\compose.cold-start.yaml')
    """
    client = _connect_dwight(secrets)
    try:
        sftp = client.open_sftp()
        sftp.put(local_path, remote_path)
        sftp.close()
    finally:
        client.close()
```

**Important:** Remote paths on Windows over paramiko SFTP use forward slashes in the SFTP protocol, even on Windows hosts. Use forward slashes or raw strings: `'/workspace/compose.cold-start.yaml'` resolves relative to the user's home drive on Windows SSH.

### Pattern 3: Stack Readiness Polling — `wait_for_stack_dwight()`

**What:** Poll the Axiom dashboard on Dwight from the Linux host using requests.

**Dashboard URL from Linux host:** `https://192.168.50.149:8443` (Caddy TLS port — same as compose.cold-start.yaml `8443:443` mapping). Use `verify=False` (self-signed cert).

```python
# Source: established pattern from mop_validation scripts
import requests
import time

def wait_for_stack_dwight(timeout: int = 600) -> bool:
    """
    Poll https://192.168.50.149:8443 from the Linux host until HTTP 200/301 or timeout.

    Returns True when reachable, False on timeout.
    """
    import urllib3
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    deadline = time.time() + timeout
    attempt = 0
    while time.time() < deadline:
        attempt += 1
        try:
            resp = requests.get("https://192.168.50.149:8443", verify=False, timeout=10)
            if resp.status_code in (200, 301):
                print(f"Attempt {attempt}: {resp.status_code} — stack ready.")
                return True
            print(f"Attempt {attempt}: {resp.status_code} — waiting 5s")
        except requests.exceptions.ConnectionError:
            print(f"Attempt {attempt}: connection refused — waiting 5s")
        time.sleep(5)
    return False
```

### Pattern 4: API Verification from Linux Host

**What:** After the subagent run, verify node ONLINE and job COMPLETED by calling the Dwight API directly from the Linux host — no Playwright, no SSH needed for verification.

```python
# Source: established pattern from mop_validation scripts
import requests

BASE_URL = "https://192.168.50.149:8443"
API_URL  = "https://192.168.50.149:8001"

def get_token(password: str) -> str:
    """Login to Axiom on Dwight and return JWT."""
    resp = requests.post(
        f"{API_URL}/auth/login",
        data={"username": "admin", "password": password},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        verify=False,
        timeout=15,
    )
    resp.raise_for_status()
    return resp.json()["access_token"]

def verify_node_online(token: str) -> bool:
    """Return True if at least 1 ONLINE node exists."""
    resp = requests.get(
        f"{API_URL}/nodes",
        headers={"Authorization": f"Bearer {token}"},
        verify=False,
        timeout=15,
    )
    nodes = resp.json()
    return any(n["status"] == "ONLINE" for n in nodes)

def verify_job_completed(token: str, job_id: int) -> dict:
    """Return job dict; check status == 'COMPLETED'."""
    resp = requests.get(
        f"{API_URL}/jobs/{job_id}",
        headers={"Authorization": f"Bearer {token}"},
        verify=False,
        timeout=15,
    )
    return resp.json()
```

### Pattern 5: Subagent Persona — Windows Adaptation

**What:** Adapt `linux_validation_prompt.md` for Windows. Key differences:

1. Replace all `curl` with PowerShell `Invoke-WebRequest` / `Invoke-RestMethod`
2. Replace `openssl` with Python cryptography (Windows lacks openssl by default)
3. Replace `python3` with `python` (Windows Python installer creates `python.exe`)
4. Replace LXC `/workspace/` paths with Windows `C:\workspace\`
5. Replace bash heredoc (`<<'EOF'`) with PowerShell multi-line syntax
6. Replace `base64 -w0` with PowerShell `[Convert]::ToBase64String()`
7. Use `\` path separators in Windows commands

**PowerShell equivalents for key operations:**

```powershell
# Login and get JWT
$resp = Invoke-RestMethod -Uri "https://localhost:8001/auth/login" `
    -Method POST -Body "username=admin&password=admin" `
    -ContentType "application/x-www-form-urlencoded" -SkipCertificateCheck
$TOKEN = $resp.access_token

# Check node status
$nodes = Invoke-RestMethod -Uri "https://localhost:8001/nodes" `
    -Headers @{Authorization="Bearer $TOKEN"} -SkipCertificateCheck
$nodes | Where-Object { $_.status -eq 'ONLINE' }

# Sign a script (Python on Windows — cryptography library)
python -c "
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives import serialization
import base64
key = serialization.load_pem_private_key(open(r'C:\workspace\signing.key','rb').read(), password=None)
script = open(r'C:\workspace\hello.ps1','rb').read()
sig = base64.b64encode(key.sign(script)).decode()
print(sig)
"
```

### Pattern 6: Signing a PowerShell Job

**What:** The job content is a `.ps1` script (`Write-Host 'Hello from Axiom on Windows'`). Signing is identical to Python jobs — Ed25519 signature over the raw script bytes.

**Key detail:** The node image has PowerShell 7.6.0 installed (confirmed in `puppets/Containerfile.node` per Phase 102 research). The runtime executes the script as a PowerShell script when it has a `.ps1` extension or when the script content starts with a PowerShell-specific command. Verify this is handled in the dispatch form.

**Signing from Windows (PowerShell + Python):**

```powershell
# On Dwight — sign the PowerShell job script
# Requires: pip install cryptography (pip install works on Windows Python)
$SIG = python -c @"
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives import serialization
import base64
key = serialization.load_pem_private_key(open(r'C:\workspace\signing.key','rb').read(), password=None)
script = open(r'C:\workspace\hello.ps1','rb').read()
print(base64.b64encode(key.sign(script)).decode())
"@
```

### Anti-Patterns to Avoid

- **Using `exec_command("docker ps")` without `pwsh -Command` prefix:** Invokes cmd.exe on Windows OpenSSH, not PowerShell. Always prefix explicitly.
- **Assuming `python3` exists on Windows:** Windows Python installs create `python.exe`, not `python3.exe`. Use `python` in Windows commands.
- **Assuming `openssl` exists on Windows:** Not included in Windows by default. Use Python `cryptography` library for key operations.
- **Pushing files with CRLF endings into containers:** Docker bind-mounts the file as-is; CRLF causes silent failures in config files processed by Linux tools inside the container.
- **Hardcoding `localhost` in the subagent prompt:** On Dwight, the API is reachable at `https://localhost:8001` and dashboard at `https://localhost:8443` from inside the Dwight SSH session, but from the Linux orchestrator host they're at `192.168.50.149:8001 / 8443`.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| SSH connection to Dwight | Custom socket code | paramiko (existing pattern in test_ssh.py) | Established, handles auth fallback, AutoAddPolicy |
| Secrets parsing | Custom parser | `read_secrets()` from test_ssh.py (or copy inline) | Already handles `key=value` format |
| Dashboard readiness polling | Custom retry loop | `wait_for_stack_dwight()` modelled on run_ce_scenario.py's `wait_for_stack()` | 600s timeout, 5s poll, reachability handling |
| API verification | Playwright/UI scraping | `requests.get(verify=False)` from Linux host | Less brittle; Dwight API is reachable directly |
| Ed25519 signing on Windows | Native PowerShell crypto | Python `cryptography` library | Consistent with Linux signing path; no OpenSSL dependency |
| FRICTION synthesis | Ad-hoc report | `synthesise_friction.py --files FRICTION-WIN-103.md` (after Phase 102 adds `--files` flag) | Same format as all other FRICTION reports; sign-off artifact |
| Stack teardown on Dwight | Custom cleanup | `pwsh -Command "docker compose -f C:\workspace\compose.cold-start.yaml down -v"` via `dwight_exec()` | Mirrors `reset_stack()` from run_ce_scenario.py |

---

## Common Pitfalls

### Pitfall 1: Windows OpenSSH Default Shell is cmd.exe, Not PowerShell

**What goes wrong:** `dwight_exec("docker compose up -d")` launches cmd.exe, which may have different PATH and environment than PowerShell. Worse, WIN-02 requires all interactions to use PowerShell — using cmd.exe would fail that requirement directly.

**Why it happens:** Windows OpenSSH Server's default shell is cmd.exe unless explicitly configured otherwise via registry (`HKLM:\SOFTWARE\OpenSSH` → `DefaultShell`).

**How to avoid:** Always prefix every `exec_command` call with `pwsh -NoProfile -NonInteractive -Command "..."`. Never rely on the default shell.

**Warning signs:** Commands that should work in PowerShell (e.g., `Invoke-RestMethod`) fail with "command not found" or produce unexpected output.

### Pitfall 2: Dwight Credentials Not in secrets.env

**What goes wrong:** `run_windows_e2e.py` calls `read_secrets()` looking for `dwight_ip`, `dwight_username`, `dwight_password`, `dwight_ssh_key` — none of these keys currently exist in `/home/thomas/Development/mop_validation/secrets.env`.

**Why it happens:** The secrets.env was set up for speedy_mini and the local stack, not Dwight. Dwight is a newly added validation target for Phase 103.

**How to avoid:** Wave 0 must include adding Dwight credentials to secrets.env. The actual values are known (IP: 192.168.50.149, creds per CONTEXT.md), SSH key is at `mop_validation/external_client_ed25519`.

**Warning signs:** `KeyError: 'dwight_ip'` on first run of the orchestrator.

### Pitfall 3: compose.cold-start.yaml Uses `SERVER_HOSTNAME=172.17.0.1`

**What goes wrong:** The cert-manager service in compose.cold-start.yaml sets `SERVER_HOSTNAME=172.17.0.1`. On Linux, `172.17.0.1` is the Docker bridge gateway — containers can reach the host at this IP. On Windows with Docker Desktop, the Docker bridge is managed inside the WSL2 VM; `172.17.0.1` is the WSL2 internal bridge, not the Windows host IP. The Caddy TLS certificate is issued for `172.17.0.1`, but the node will connect via `host.docker.internal`. If `host.docker.internal` is not in the cert's SAN, TLS verification fails on the node.

**Current state:** CONTEXT.md documents `AGENT_URL: https://host.docker.internal:8001` as the right setting for Docker Desktop Windows. This is already in the enroll-node.md table. But the cert may only cover `172.17.0.1`. This is a likely first-run blocker on Windows.

**How to avoid:** During the docs pre-audit, add a Windows-specific note to enroll-node.md that the node must use `host.docker.internal:8001`, and that TLS verification requires the orchestrator to include `host.docker.internal` in its certificate SAN. The cert-manager may need a `SERVER_HOSTNAME=host.docker.internal` env var override on Windows. This is the single highest-risk friction point for the phase.

**Warning signs:** Node logs show `[SSL: CERTIFICATE_VERIFY_FAILED] hostname 'host.docker.internal' doesn't match '172.17.0.1'` or similar.

### Pitfall 4: PowerShell Quoting in exec_command Strings

**What goes wrong:** Nesting quotes inside `pwsh -Command "..."` breaks the command. For example:
```python
dwight_exec('pwsh -Command "docker compose -f "C:\\workspace\\compose.cold-start.yaml" up -d"')
```
The inner quotes break the outer command string.

**How to avoid:** For commands with complex quoting, push a `.ps1` script file to Dwight and execute it:
```python
dwight_push("/tmp/start_stack.ps1", "C:/workspace/start_stack.ps1", secrets)
dwight_exec("C:/workspace/start_stack.ps1")  # default shell will try to run .ps1 directly
# OR:
dwight_exec_raw('pwsh -NoProfile -File C:\\workspace\\start_stack.ps1')
```

### Pitfall 5: `enroll-node.md` and `first-job.md` Have No PowerShell Content

**What goes wrong:** The subagent follows only the docs. If the docs have no PowerShell tab for the JOIN_TOKEN CLI step or the job signing step, the subagent either gets stuck (BLOCKER) or is forced to use bash (violating WIN-02).

**Why it happens:** The docs pre-audit identified these gaps (confirmed by reading the current files). Neither enroll-node.md CLI tab nor first-job.md Manual Setup section has any PowerShell commands.

**How to avoid:** The pre-audit plan task MUST add PowerShell tabs to:
- `enroll-node.md` CLI tab: PowerShell `Invoke-RestMethod` equivalents for login and token generation
- `first-job.md` Step 0: PowerShell heredoc alternative for key generation
- `first-job.md` Manual Setup: PowerShell equivalents for signing and curl dispatch

**Warning signs:** Subagent writes BLOCKER: "No PowerShell command shown for this step."

### Pitfall 6: synthesise_friction.py Hardcoded to 4 CE/EE Files

**What goes wrong:** Running `python3 synthesise_friction.py` after producing `FRICTION-WIN-103.md` will fail because it only reads `FRICTION-CE-INSTALL.md`, `FRICTION-CE-OPERATOR.md`, `FRICTION-EE-INSTALL.md`, `FRICTION-EE-OPERATOR.md`.

**How to avoid:** Phase 102 research recommended adding `--files` flag to `synthesise_friction.py`. If Phase 102 implemented this patch, Phase 103 benefits automatically. If not, the patch must be included in Phase 103's Wave 0.

---

## Code Examples

### dwight_exec() — Full Paramiko Helper

```python
# Source: paramiko documentation + test_ssh.py established pattern
import paramiko

KEY_PATH = "/home/thomas/Development/mop_validation/external_client_ed25519"

def dwight_exec(cmd: str, timeout: int = 60, secrets: dict = None) -> tuple:
    """
    Run a PowerShell command on Dwight via SSH.
    Returns (stdout_str, stderr_str, exit_code).
    cmd: PowerShell command body (will be wrapped in pwsh -NoProfile -NonInteractive -Command "...")
    """
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    ip       = secrets["dwight_ip"]
    username = secrets["dwight_username"]

    try:
        client.connect(ip, username=username, key_filename=KEY_PATH, timeout=15)
    except Exception:
        client.connect(ip, username=username, password=secrets["dwight_password"], timeout=15)

    try:
        # Escape any double-quotes in cmd before wrapping
        escaped = cmd.replace('"', '\\"')
        full_cmd = f'pwsh -NoProfile -NonInteractive -Command "{escaped}"'
        stdin, stdout, stderr = client.exec_command(full_cmd, timeout=timeout)
        out = stdout.read().decode("utf-8", errors="replace")
        err = stderr.read().decode("utf-8", errors="replace")
        rc  = stdout.channel.recv_exit_status()
        return out, err, rc
    finally:
        client.close()
```

### dwight_push() — SFTP File Transfer

```python
# Source: paramiko SFTP documentation
def dwight_push(local_path: str, remote_path: str, secrets: dict) -> None:
    """
    Push a local file to Dwight via SFTP.
    remote_path: use forward slashes ('/workspace/file.yaml') — SFTP protocol is POSIX.
    On Windows SSH servers, forward slashes resolve relative to the user's home directory.
    For absolute Windows paths, use: '/C:/workspace/file.yaml' or check Dwight SSH config.
    """
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        client.connect(secrets["dwight_ip"], username=secrets["dwight_username"],
                       key_filename=KEY_PATH, timeout=15)
    except Exception:
        client.connect(secrets["dwight_ip"], username=secrets["dwight_username"],
                       password=secrets["dwight_password"], timeout=15)
    try:
        sftp = client.open_sftp()
        sftp.put(local_path, remote_path)
        sftp.close()
    finally:
        client.close()
```

### PowerShell Job Signing (Dwight — via Python)

```powershell
# Executed on Dwight via dwight_exec() or in the subagent prompt
# Sign a PowerShell script using the cryptography library
python -c @"
from cryptography.hazmat.primitives import serialization
import base64
key = serialization.load_pem_private_key(
    open('C:/workspace/signing.key', 'rb').read(), password=None
)
script = open('C:/workspace/hello.ps1', 'rb').read()
sig = base64.b64encode(key.sign(script)).decode()
print(sig)
"@
```

### API Verification from Linux Host

```python
# Source: established pattern from mop_validation scripts
import requests, urllib3
urllib3.disable_warnings()

def get_token_dwight(password: str = "admin") -> str:
    r = requests.post("https://192.168.50.149:8001/auth/login",
                      data={"username": "admin", "password": password},
                      headers={"Content-Type": "application/x-www-form-urlencoded"},
                      verify=False, timeout=15)
    return r.json()["access_token"]
```

### Stack Reset on Dwight

```python
# Equivalent of reset_stack() from run_ce_scenario.py, adapted for Dwight
def reset_stack_dwight(secrets: dict) -> None:
    """Tear down the Axiom stack on Dwight and cold-start fresh."""
    print("Step 1: Pushing compose file to Dwight...")
    dwight_push(
        "/home/thomas/Development/master_of_puppets/puppeteer/compose.cold-start.yaml",
        "/workspace/compose.cold-start.yaml",
        secrets,
    )
    print("Step 2: Tearing down existing stack...")
    out, err, rc = dwight_exec(
        "docker compose -f C:\\workspace\\compose.cold-start.yaml down -v",
        timeout=120, secrets=secrets
    )
    print(f"  down -v: exit {rc}")
    print("Step 3: Starting fresh stack...")
    out, err, rc = dwight_exec(
        "docker compose -f C:\\workspace\\compose.cold-start.yaml up -d",
        timeout=600, secrets=secrets
    )
    print(f"  up -d: exit {rc}")
```

---

## State of the Art

### What Exists vs What's Missing for Windows

| Area | Linux (Phase 102) | Windows (Phase 103) |
|------|-------------------|---------------------|
| Orchestrator script | `run_linux_e2e.py` ✓ | `run_windows_e2e.py` — must create |
| Transport helpers | `run_ce_scenario.py` (`incus_exec`, `incus_push`) ✓ | `run_windows_scenario.py` (`dwight_exec`, `dwight_push`) — must create |
| Validation prompt | `linux_validation_prompt.md` ✓ | `windows_validation_prompt.md` — must create |
| install.md Windows tabs | Complete ✓ | No gap |
| prerequisites.md Windows | Complete ✓ | No gap |
| enroll-node.md PowerShell | Missing ✗ | Must add CLI tab + Option B PowerShell notes |
| first-job.md PowerShell | Missing ✗ | Must add Step 0 and Manual Setup PowerShell tabs |
| Dwight secrets in secrets.env | N/A | Missing — must add dwight_ip, dwight_username, dwight_password |
| synthesise_friction.py `--files` | Phase 102 patch | Needed if Phase 102 did not implement; share the patch |
| Signing keys | `/home/thomas/Development/master_of_puppets/secrets/` ✓ | Same keys, push to Dwight |

### Docker Desktop Windows — Networking Behaviour (CONFIRMED)

`host.docker.internal` resolves to the Windows host IP from inside Docker Desktop containers on all platforms. This is the standard DNS name for host access and is documented at [Docker Desktop networking](https://docs.docker.com/desktop/features/networking/). Containers on Windows use `host.docker.internal` to reach services on the host. This is why `AGENT_URL: https://host.docker.internal:8001` is the correct value for the node when running on the same Windows machine as the orchestrator.

---

## Open Questions

1. **Does Dwight's TLS cert cover `host.docker.internal`?**
   - What we know: compose.cold-start.yaml cert-manager uses `SERVER_HOSTNAME=172.17.0.1`. On Linux, `172.17.0.1` is the Docker bridge. On Windows, it's a WSL2 internal IP.
   - What's unclear: Whether `host.docker.internal` is in the cert SAN, or whether the node can reach the orchestrator at `https://host.docker.internal:8001` without TLS errors.
   - Recommendation: This is the most likely first-run BLOCKER. The pre-audit task should add a Windows-specific callout in enroll-node.md about this. The planner should include a "fix cert SAN for Windows" task as a conditional item triggered by validation failures.

2. **Is paramiko installed in the mop_validation Python environment?**
   - What we know: `test_ssh.py` exists and imports paramiko, so it must have been installed at some point. But the current host Python environment doesn't have it (`ModuleNotFoundError`).
   - What's unclear: Which Python venv or interpreter is used to run mop_validation scripts; whether `pip install paramiko` is a Wave 0 prerequisite.
   - Recommendation: Wave 0 must include `pip install paramiko requests` or equivalent venv setup.

3. **What Windows username format does Dwight SSH accept?**
   - What we know: CONTEXT.md documents `dwight_username=dwight\drear`. Backslash in usernames (`DOMAIN\user`) is standard for Windows domain accounts, but paramiko typically passes username as-is.
   - What's unclear: Whether paramiko handles `dwight\drear` correctly or whether it should be `drear` (local account) or `.\drear` (explicit local).
   - Recommendation: Claude's discretion per CONTEXT.md. Try `drear` first; if it fails, try the full domain format.

---

## Validation Architecture

> `nyquist_validation` is `true` in `.planning/config.json` — this section is included.

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest (backend) + vitest (frontend) for regression; live E2E run for phase validation |
| Config file | `puppeteer/pytest.ini` (backend), `puppeteer/dashboard/vite.config.ts` (frontend) |
| Quick run command | `cd puppeteer && pytest tests/ -x -q` |
| Full suite command | `cd puppeteer && pytest && cd dashboard && npm run test` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| WIN-01 | Windows cold-start deploy completes via docs | E2E / live SSH | `python3 mop_validation/scripts/run_windows_e2e.py` | ❌ Wave 0 |
| WIN-02 | All shell interactions use PowerShell | E2E / live SSH (verified by prompt constraints) | subagent validation run | ❌ Wave 0 |
| WIN-03 | admin/admin login triggers forced password change | E2E / live API call | subagent validation run + `get_token_dwight("admin")` must return `must_change_password: true` | ❌ Wave 0 |
| WIN-04 | Node enrollment succeeds on Dwight | E2E / live API call | `verify_node_online(token)` returns True | ❌ Wave 0 |
| WIN-05 | First PowerShell job dispatches and completes | E2E / live API call | `verify_job_completed(token, job_id)["status"] == "COMPLETED"` | ❌ Wave 0 |
| WIN-06 | Friction catalogued and fixed | Report artifact | `FRICTION-WIN-103.md` produced; zero BLOCKERs | ❌ Wave 0 |

**Note:** Like Phase 102, all WIN requirements are validated by the live E2E run, not unit/component tests. The "test" is the validation orchestrator and the resulting FRICTION file.

### Sampling Rate
- **Per iteration:** Full Windows golden path run (`python3 mop_validation/scripts/run_windows_e2e.py`)
- **Per wave merge:** Full backend + frontend test suite green (regression protection)
- **Phase gate:** Golden path completes with zero BLOCKER friction points in `FRICTION-WIN-103.md`; `synthesise_friction.py --files FRICTION-WIN-103.md` outputs READY verdict

### Wave 0 Gaps
- [ ] `mop_validation/scripts/run_windows_scenario.py` — paramiko helper library (dwight_exec, dwight_push, wait_for_stack_dwight)
- [ ] `mop_validation/scripts/run_windows_e2e.py` — Phase 103 orchestrator
- [ ] `mop_validation/scripts/windows_validation_prompt.md` — Claude subagent persona + Windows golden path
- [ ] Add Dwight credentials to `mop_validation/secrets.env`: `dwight_ip=192.168.50.149`, `dwight_username=dwight\drear` (or `drear`), `dwight_password`, `dwight_ssh_key=external_client_ed25519`
- [ ] `pip install paramiko requests` — ensure available in the Python environment used to run mop_validation scripts
- [ ] `synthesise_friction.py --files` patch — if not already done in Phase 102
- [ ] PowerShell tabs added to `enroll-node.md` (CLI tab + Option B notes)
- [ ] PowerShell tabs added to `first-job.md` (Step 0 + Manual Setup)

---

## Sources

### Primary (HIGH confidence)
- `/home/thomas/Development/master_of_puppets/.planning/phases/103-windows-e2e-validation/103-CONTEXT.md` — locked decisions, integration points, reusable assets
- `/home/thomas/Development/mop_validation/scripts/test_ssh.py` — existing paramiko pattern, read_secrets() helper
- `/home/thomas/Development/mop_validation/scripts/run_ce_scenario.py` — structural template: wait_for_stack, reset_stack, helper library shape
- `/home/thomas/Development/mop_validation/scripts/run_linux_e2e.py` — exact orchestrator pattern to mirror for Windows
- `/home/thomas/Development/mop_validation/scripts/linux_validation_prompt.md` — subagent persona template to adapt
- `/home/thomas/Development/mop_validation/scripts/synthesise_friction.py` — FRICTION format, REQUIRED_FILES hardcoding (lines 25-30)
- `/home/thomas/Development/master_of_puppets/docs/docs/getting-started/install.md` — confirmed Windows tabs complete
- `/home/thomas/Development/master_of_puppets/docs/docs/getting-started/prerequisites.md` — confirmed Windows coverage complete
- `/home/thomas/Development/master_of_puppets/docs/docs/getting-started/enroll-node.md` — confirmed no PowerShell tabs (gap identified)
- `/home/thomas/Development/master_of_puppets/docs/docs/getting-started/first-job.md` — confirmed no PowerShell signing/dispatch path (gap identified)
- `/home/thomas/Development/master_of_puppets/puppeteer/compose.cold-start.yaml` — SERVER_HOSTNAME=172.17.0.1 (Windows cert SAN concern identified)
- `/home/thomas/Development/master_of_puppets/.planning/phases/102-linux-e2e-validation/102-RESEARCH.md` — Phase 102 findings that carry forward

### Secondary (MEDIUM confidence)
- [Docker Desktop networking docs](https://docs.docker.com/desktop/features/networking/) — confirmed `host.docker.internal` resolves to Windows host IP from inside containers
- [Windows OpenSSH DefaultShell wiki](https://github.com/PowerShell/Win32-OpenSSH/wiki/DefaultShell) — confirmed cmd.exe is default shell; PowerShell must be specified explicitly
- [Microsoft OpenSSH Server Configuration](https://learn.microsoft.com/en-us/windows-server/administration/openssh/openssh-server-configuration) — registry key for DefaultShell override
- [paramiko SFTP docs](https://docs.paramiko.org/en/stable/api/sftp.html) — SFTP transfers are binary, no CRLF conversion

### Tertiary (LOW confidence)
- None for this phase — all critical findings are directly verified from local repository inspection or official docs

---

## Metadata

**Confidence breakdown:**
- Standard stack (paramiko helpers): HIGH — pattern verified in test_ssh.py, docs confirmed
- Docs gaps (enroll-node.md, first-job.md): HIGH — files read directly, gaps confirmed
- Windows OpenSSH shell behaviour: HIGH — official Microsoft docs + Win32-OpenSSH wiki
- Docker Desktop `host.docker.internal` networking: HIGH — official Docker docs
- TLS cert SAN on Windows (Pitfall 3): MEDIUM — reasoned from cert-manager config; actual behaviour on Dwight is unconfirmed until first run
- Dwight credential format (`dwight\drear`): LOW — format from CONTEXT.md but untested in paramiko; flagged as discretion item

**Research date:** 2026-03-31
**Valid until:** 2026-04-14 (14 days — stable infrastructure; Dwight machine state may change)
