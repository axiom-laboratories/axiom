# Prerequisites

Before installing Axiom, verify your environment meets the following requirements.

## Checklist

- [ ] **Docker 24+ with Docker Compose v2**

    === "Linux / macOS"

        ```bash
        docker --version && docker compose version
        ```

        You need Docker Engine 24.0 or later and the `docker compose` v2 plugin (note: not the legacy `docker-compose` v1 binary). Check that `docker compose version` outputs `v2.x.x` or higher.

    === "Windows"

        Install **Docker Desktop 4.x or later** from [https://www.docker.com/products/docker-desktop/](https://www.docker.com/products/docker-desktop/).

        Docker Desktop bundles Docker Engine and Docker Compose v2 — no separate installation is needed. After installing, verify from PowerShell:

        ```powershell
        docker --version
        docker compose version
        ```

        **WSL2 backend is required.** Docker Desktop 4.x uses WSL2 by default for Linux containers — confirm it is enabled under **Settings → General → Use the WSL 2 based engine**. If the option is greyed out, you may need to enable the **Virtual Machine Platform** and **Windows Subsystem for Linux** Windows features first (see the [Windows Features](#windows-features) note below).

        **Minimum Windows version:** Windows 10 21H1 (build 19043) or Windows 11. Earlier versions of Windows 10 do not support the WSL2 kernel required by Docker Desktop.

- [ ] **4 GB RAM available**

    verify with:
    ```bash
    # Linux
    free -h
    ```

    On Mac, check **Activity Monitor → Memory**. On Windows, open **Task Manager → Performance → Memory**. Ensure at least 4 GB is free before starting the stack.

- [ ] **Ports 80 and 443 available**

    === "Linux"

        ```bash
        ss -tlnp | grep -E ':80|:443'
        ```

        No output means the ports are free. If a service is already listening on 80 or 443, stop it before starting the stack (Caddy needs both ports).

    === "macOS"

        ```bash
        netstat -an | grep LISTEN | grep -E ':80|:443'
        ```

        No output means the ports are free.

    === "Windows"

        ```powershell
        netstat -ano | findstr ":80 :443"
        ```

        No output means the ports are free. If IIS or another web server is listening on these ports, stop it before starting the stack.

- [ ] **Git** (to clone the repository)

    verify with:
    ```bash
    git --version
    ```

    On Windows, Git for Windows ([https://git-scm.com/download/win](https://git-scm.com/download/win)) provides both `git` and a Git Bash environment. Alternatively, use the Windows Subsystem for Linux (WSL2) shell.

- [ ] **PowerShell 5.1+** *(Windows only — for the CA installer)*

    Windows 10 and Windows 11 include PowerShell 5.1 built in. Verify from a PowerShell prompt:

    ```powershell
    $PSVersionTable.PSVersion
    ```

    PowerShell 7.x also works and is recommended for scripting.

---

<span id="windows-features"></span>
!!! note "Windows Features required for WSL2"
    If Docker Desktop's WSL2 option is unavailable, you must enable two Windows features. Open an **elevated PowerShell** prompt and run:

    ```powershell
    dism.exe /online /enable-feature /featurename:VirtualMachinePlatform /all /norestart
    dism.exe /online /enable-feature /featurename:Microsoft-Windows-Subsystem-Linux /all /norestart
    ```

    Restart your machine, then re-open Docker Desktop. If your machine does not support hardware virtualisation (Hyper-V / VT-x), Docker Desktop cannot run Linux containers.

!!! tip "Podman Compose"
    The Axiom stack runs under Podman as a drop-in alternative to Docker. To verify your Podman installation:
    ```bash
    podman-compose --version
    ```
    Substitute `podman compose` for `docker compose` in all commands throughout this guide.

!!! info "Corporate / enterprise proxy"
    If deploying behind a corporate proxy, set the standard proxy environment variables before running `docker compose`:

    === "Linux / macOS"

        ```bash
        export HTTP_PROXY=http://proxy.example.com:8080
        export HTTPS_PROXY=http://proxy.example.com:8080
        export NO_PROXY=localhost,127.0.0.1
        ```

    === "Windows (PowerShell)"

        ```powershell
        $env:HTTP_PROXY  = "http://proxy.example.com:8080"
        $env:HTTPS_PROXY = "http://proxy.example.com:8080"
        $env:NO_PROXY    = "localhost,127.0.0.1"
        ```

        You can also configure the proxy in Docker Desktop under **Settings → Resources → Proxies**.

---

**Next:** [Install →](install.md)
