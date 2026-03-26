# Install

This guide uses Docker Compose (v2) — the recommended path for both homelab and production deployments.

---

## Step 1: Get the source

=== "Git Clone"

    ```bash
    git clone https://github.com/your-org/master-of-puppets.git
    cd master-of-puppets
    ```

=== "GHCR Pull (no git required)"

    Download the compose file directly and pull all images — no git installation needed:

    ```bash
    curl -sSLO https://raw.githubusercontent.com/axiom-laboratories/axiom/main/puppeteer/compose.cold-start.yaml
    docker compose -f compose.cold-start.yaml pull
    ```

    Then continue with Step 2 to create your `.env` file before starting the stack.

---

## Step 2: Configure environment variables

=== "Server Install"

    Create `puppeteer/secrets.env` with the required variables:

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

    !!! danger "API_KEY is required"
        If `API_KEY` is missing from `secrets.env`, the agent service **crashes at startup with no useful log message** — the process exits silently at import time. Set it to any non-empty string.

    !!! warning "ADMIN_PASSWORD is first-start only"
        `ADMIN_PASSWORD` is only read when the admin user does not yet exist in the database. After the first start, changing this value in `secrets.env` has **no effect**. Use the dashboard **Users** page to change the admin password on existing deployments.

=== "Cold-Start Install"

    Create a `.env` file in the same directory as `compose.cold-start.yaml`:

    ```bash
    # .env — place in same directory as compose.cold-start.yaml

    # Initial admin password — seeds the admin user on first start only
    ADMIN_PASSWORD=<choose-a-password>

    # Fernet key for encrypting secrets at rest
    ENCRYPTION_KEY=$(python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())")
    ```

    !!! warning "ADMIN_PASSWORD is first-start only"
        `ADMIN_PASSWORD` is only read when the admin user does not yet exist in the database. After the first start, changing this value has **no effect**. Use the dashboard **Users** page to change the admin password.

    !!! note "Generating ENCRYPTION_KEY"
        Run the `python3 -c "..."` command above in your shell and paste the output as the value. The key must be a valid Fernet key (43 URL-safe base64 characters followed by `=`).

---

## Step 3: Start the stack

```bash
docker compose -f puppeteer/compose.server.yaml up -d
```

This starts: Caddy (reverse proxy + TLS), the Agent Service (API on port 8001), the Model Service (port 8000), and PostgreSQL.

---

## Step 4: Verify

Check that all containers are running:

```bash
docker compose -f puppeteer/compose.server.yaml ps
```

All services should show `running` status. Then open `https://localhost/` in a browser — you should see the dashboard login page.

!!! note "TLS certificate warning"
    The Root CA is auto-generated on first start. Your browser will show a certificate warning because it does not trust the self-signed CA yet. To install the CA in your browser and system trust store:

    - **Linux:** Visit `https://your-host/system/root-ca-installer` and run the downloaded script
    - **Windows:** Visit `https://your-host/system/root-ca-installer.ps1` and run the downloaded script

    This installs the Root CA into your OS and browser (Chrome and Firefox included on Linux).

!!! tip "Podman Compose"
    The stack is tested under both Docker and Podman. Substitute `podman compose` for `docker compose` in all commands. Everything else in this guide applies unchanged.

---

---

## Enterprise Edition

To enable EE features, add your licence key to `secrets.env`:

```bash
AXIOM_LICENCE_KEY=<your-licence-key>
```

The stack reads this at startup — no plugin install required. See [Licensing →](../licensing.md) for validation behaviour, expiry handling, and how to check your licence status.

---

**Next:** [Enroll a Node →](enroll-node.md)
