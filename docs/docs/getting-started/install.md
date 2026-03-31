# Install

This guide uses Docker Compose (v2) — the recommended path for both homelab and production deployments.

!!! note "Windows support"
    This guide has been documented against Docker Desktop 4.x with the WSL2 backend on Windows 10 21H1+ and Windows 11. Windows-specific commands are shown in tabbed blocks wherever the syntax differs from Linux/macOS. If you encounter issues not covered here, see the [FAQ](../runbooks/faq.md) or open a GitHub issue.

---

## Step 1: Get the source

=== "Git Clone"

    === "Linux / macOS"

        ```bash
        git clone https://github.com/your-org/master-of-puppets.git
        cd master-of-puppets
        ```

    === "Windows (PowerShell)"

        ```powershell
        git clone https://github.com/your-org/master-of-puppets.git
        cd master-of-puppets
        ```

        Git for Windows and the `git` command in WSL2 both work. If you use WSL2, run all subsequent commands inside the WSL2 shell for the best compatibility.

=== "GHCR Pull (no git required)"

    Download the compose file directly and pull all images — no git installation needed:

    === "Linux / macOS"

        ```bash
        curl -sSLO https://raw.githubusercontent.com/axiom-laboratories/axiom/main/puppeteer/compose.cold-start.yaml
        docker compose -f compose.cold-start.yaml pull
        ```

    === "Windows (PowerShell)"

        ```powershell
        Invoke-WebRequest -Uri https://raw.githubusercontent.com/axiom-laboratories/axiom/main/puppeteer/compose.cold-start.yaml -OutFile compose.cold-start.yaml
        docker compose -f compose.cold-start.yaml pull
        ```

        Alternatively, open the URL in a browser and save the file manually.

    Then continue with Step 2 to create your `.env` file before starting the stack.

---

## Step 2: Configure environment variables

=== "Server Install"

    Create `puppeteer/secrets.env` with the required variables:

    === "Linux / macOS"

        ```bash
        # puppeteer/secrets.env

        # JWT signing secret — generate with:
        # python -c "import secrets; print(secrets.token_hex(32))"
        SECRET_KEY=<random-64-char-hex>

        # Fernet key for encrypting secrets at rest — generate with:
        # python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
        ENCRYPTION_KEY=<fernet-key>

        # Shared API key for legacy API key auth
        API_KEY=<arbitrary-string>

        # Initial admin password — seeds the admin user on first start only
        ADMIN_PASSWORD=<initial-admin-password>
        ```

    === "Windows (PowerShell)"

        Create the file with your preferred text editor (Notepad, VS Code, etc.) or from PowerShell:

        ```powershell
        # Generate the required secret values
        $SECRET_KEY     = python -c "import secrets; print(secrets.token_hex(32))"
        $ENCRYPTION_KEY = python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
        $API_KEY        = python -c "import secrets; print(secrets.token_urlsafe(32))"

        # Write secrets.env
        @"
        SECRET_KEY=$SECRET_KEY
        ENCRYPTION_KEY=$ENCRYPTION_KEY
        API_KEY=$API_KEY
        ADMIN_PASSWORD=<choose-a-strong-password>
        "@ | Set-Content -Encoding UTF8 puppeteer\secrets.env
        ```

        !!! warning "Line endings"
            If you create or edit `secrets.env` (or any config file that will be bind-mounted into a Linux container) with Windows Notepad, save it as **UTF-8** and ensure line endings are **LF** (Unix-style), not **CRLF** (Windows-style). VS Code and most modern editors let you set this in the status bar. Mixed line endings can cause silent failures inside containers.

    !!! danger "API_KEY is required"
        If `API_KEY` is missing from `secrets.env`, the agent service **crashes at startup with no useful log message** — the process exits silently at import time. Set it to any non-empty string.

    !!! warning "ADMIN_PASSWORD is first-start only"
        `ADMIN_PASSWORD` is only read when the admin user does not yet exist in the database. After the first start, changing this value in `secrets.env` has **no effect**. Use the dashboard **Users** page to change the admin password on existing deployments.

=== "Quick Start"

    Create a `.env` file in the same directory as `compose.cold-start.yaml`:

    === "Linux / macOS"

        ```bash
        # .env — place in same directory as compose.cold-start.yaml

        # Initial admin password — seeds the admin user on first start only
        ADMIN_PASSWORD=<choose-a-password>
        ```

    === "Windows (PowerShell)"

        ```powershell
        @"
        ADMIN_PASSWORD=<choose-a-password>
        "@ | Set-Content -Encoding UTF8 .env
        ```

    !!! warning "ADMIN_PASSWORD is first-start only"
        `ADMIN_PASSWORD` is only read when the admin user does not yet exist in the database. After the first start, changing this value has **no effect**. Use the dashboard **Users** page to change the admin password.

    !!! note "ENCRYPTION_KEY is optional for Quick Start"
        If `ENCRYPTION_KEY` is not set, the agent generates one automatically on first start and persists it to the `secrets-data` volume. It will be reused on all subsequent restarts. For production server installs where you need to back up or rotate the key, set it explicitly.

---

## Step 3: Start the stack

Docker Compose works identically on Windows, Linux, and macOS. The commands below are the same on all platforms — run them from PowerShell, Command Prompt, Git Bash, or a WSL2 shell.

=== "Server Install"

    ```bash
    docker compose -f puppeteer/compose.server.yaml up -d
    ```

    This starts: Caddy (reverse proxy + TLS), the Agent Service (API on port 8001), the Model Service (port 8000), and PostgreSQL.

=== "Quick Start"

    ```bash
    docker compose -f compose.cold-start.yaml --env-file .env up -d
    ```

    This starts: Caddy (reverse proxy + TLS, port 8443), the Agent Service (port 8001), and PostgreSQL.

!!! tip "Windows: Docker Desktop must be running"
    Unlike Linux where Docker Engine runs as a background service, on Windows Docker Desktop must be open (visible in the system tray) before any `docker` or `docker compose` commands will work. If you see `error during connect: ... Is the docker daemon running?`, open Docker Desktop and wait for it to finish starting.

---

## Step 4: Verify

=== "Server Install"

    Check that all containers are running:

    ```bash
    docker compose -f puppeteer/compose.server.yaml ps
    ```

    All services should show `running` status. Then open `https://localhost/` in a browser — you should see the dashboard login page.

=== "Quick Start"

    Check that all containers are running:

    ```bash
    docker compose -f compose.cold-start.yaml ps
    ```

    All services should show `running` status. Then open `https://localhost:8443/` in a browser — you should see the dashboard login page.

!!! note "TLS certificate warning"
    The Root CA is auto-generated on first start. Your browser will show a certificate warning because it does not trust the self-signed CA yet. To install the CA in your browser and system trust store:

    === "Linux"

        Visit `https://your-host/system/root-ca-installer` and run the downloaded script. The script installs the Root CA into the OS trust store and into Chrome and Firefox's NSS databases.

    === "macOS"

        Visit `https://your-host/system/root-ca-installer` in a browser, download the script, and run it. You may need to approve the Keychain access prompt.

    === "Windows"

        Visit `https://your-host/system/root-ca-installer.ps1` (note the `.ps1` extension). Save the file and run it from an **elevated (Run as Administrator) PowerShell** prompt:

        ```powershell
        Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
        .\root-ca-installer.ps1
        ```

        The script installs the Root CA into the Windows Certificate Store (Trusted Root Certification Authorities). Chrome and Edge pick this up automatically. Firefox uses its own trust store — after running the script, you may need to restart Firefox or manually import the CA under **Settings → Privacy & Security → Certificates → View Certificates**.

!!! tip "Podman Compose"
    The stack is tested under both Docker and Podman. Substitute `podman compose` for `docker compose` in all commands. Everything else in this guide applies unchanged.

---

## Windows troubleshooting

| Symptom | Likely cause | Fix |
|---------|--------------|-----|
| `error during connect: ... Is the docker daemon running?` | Docker Desktop is not running | Open Docker Desktop and wait for it to reach "Docker Desktop is running" status in the system tray |
| `WSL 2 installation is incomplete` on Docker Desktop startup | WSL2 kernel not installed | Run `wsl --update` from an elevated PowerShell, then restart |
| Containers start but immediately exit | Bind-mounted config files have CRLF line endings | Resave config files with LF line endings (VS Code status bar → "CRLF" → click → "LF") |
| `docker compose` not found | Using old Docker Desktop (pre-3.x) | Update to Docker Desktop 4.x; `docker compose` (v2 plugin) is bundled |
| Port 80/443 already in use | IIS or another service is bound to the port | Stop IIS (`iisreset /stop`) or the conflicting service before starting the stack |
| WSL2 integration not enabled for your distribution | Docker Desktop WSL2 integration is per-distro | In Docker Desktop: **Settings → Resources → WSL Integration** → enable your distro |

---

---

## Enterprise Edition

To enable EE features, add your licence key to `secrets.env`:

```bash
AXIOM_LICENCE_KEY=<your-licence-key>
```

The stack reads this at startup — no plugin install required. A valid key enables the following features:

- `foundry` — Docker image builder for custom node environments
- `rbac` — role-based access control with per-role permission management
- `webhooks` — outbound webhook delivery on job events
- `triggers` — event-driven job triggering
- `audit` — persistent audit log for all security-relevant actions
- `resource_limits` — per-job memory and CPU enforcement
- `service_principals` — non-human machine identities for CI/CD
- `api_keys` — long-lived API key authentication
- `executions` — execution history and attestation log

### Verify EE is active

=== "Dashboard"

    Open the dashboard in your browser. The sidebar shows a **CE** or **EE** badge — it switches from **CE** to **EE** once the key is loaded and valid.

=== "CLI"

    === "Linux / macOS"

        ```bash
        curl -sk https://<your-orchestrator>:8001/api/features
        ```

    === "Windows (PowerShell)"

        ```powershell
        Invoke-RestMethod -Uri "https://<your-orchestrator>:8001/api/features" -SkipCertificateCheck
        ```

    !!! note "Expected response when EE is active"
        ```json
        {
          "audit": true,
          "foundry": true,
          "webhooks": true,
          "triggers": true,
          "rbac": true,
          "resource_limits": true,
          "service_principals": true,
          "api_keys": true,
          "executions": true
        }
        ```

        If the key is missing or expired, all values return `false`.

See [Licensing →](../licensing.md) for validation behaviour, expiry handling, and how to check your licence status.

---

**Next:** [Enroll a Node →](enroll-node.md)
