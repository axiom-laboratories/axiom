# Enroll a Node

Nodes self-enroll over mTLS — they generate a certificate signing request and get a signed client cert from the control plane. You provide a JOIN_TOKEN that embeds the Root CA so the node can establish trust automatically.

---

## Step 1: Generate an enrollment token

1. In the dashboard, go to **Nodes**
2. Click **Generate Token**
3. Click **Copy JOIN_TOKEN** — this copies the enhanced token (base64-encoded JSON with the Root CA embedded)

!!! warning "Use the dashboard Copy button"
    The raw API endpoint `POST /api/enrollment-tokens` returns only the token hex string. The **enhanced JOIN_TOKEN** — which includes the Root CA for mTLS bootstrap — is only available via the dashboard **Copy JOIN_TOKEN** button.

    If you give the node the raw hex string, you will see the node failing with a TLS error rather than the expected log line:
    ```
    Detected Enhanced Token. Bootstrapping Trust...
    ```

    **Always copy the JOIN_TOKEN from the dashboard.**

!!! note "CLI / headless alternative"
    If you cannot access the dashboard (headless server, scripted setup), you can generate an enhanced token via the API. First log in to get a JWT:

    ```bash
    TOKEN=$(curl -sk -X POST https://<your-orchestrator>:8001/auth/login \
      -H 'Content-Type: application/x-www-form-urlencoded' \
      -d 'username=admin&password=<your-password>' | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")
    ```

    Then generate and retrieve the enhanced token:

    ```bash
    curl -sk -X POST https://<your-orchestrator>:8001/admin/generate-token \
      -H "Authorization: Bearer $TOKEN" \
      | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('enhanced_token', d.get('join_token', '')))"
    ```

    The `enhanced_token` field contains the full base64-encoded JOIN_TOKEN with the Root CA embedded.

!!! warning "Admin password (cold-start installs)"
    If you started Axiom using `compose.cold-start.yaml` without setting `ADMIN_PASSWORD` in your `.env` file, the admin account was created with a random password. You will not be able to log in.

    Before starting the stack, create a `.env` file in the same directory as `compose.cold-start.yaml`:

    ```bash
    ADMIN_PASSWORD=your-chosen-password
    ENCRYPTION_KEY=$(python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())")
    ```

    Then restart: `docker compose -f compose.cold-start.yaml --env-file .env down -v && docker compose -f compose.cold-start.yaml --env-file .env up -d`

---

## Step 2: Configure node connectivity

Choose the `AGENT_URL` value that matches your deployment topology:

| Scenario | AGENT_URL |
|----------|-----------|
| Docker Desktop (Mac or Windows) | `https://host.docker.internal:8001` |
| Linux Docker (bridge network) | `https://172.17.0.1:8001` |
| Same Docker Compose network as puppeteer | `https://puppeteer-agent-1:8001` |

If `172.17.0.1` is not the correct gateway on your Linux host, find the right address with:

```bash
ip route | awk '/default/ {print $3}'
```

---

## Step 3: Install the node

Choose your installation method:

### Option A: curl installer (recommended)

The one-liner downloads and runs the universal installer script hosted on the orchestrator:

```bash
curl -sSL https://<your-orchestrator>/installer.sh | bash -s -- --token "<JOIN_TOKEN>"
```

Replace `<your-orchestrator>` with your orchestrator's hostname or IP (e.g., `10.0.0.5:8001` or `my-orchestrator.example.com`).

The installer script:

- Detects Docker or Podman on your system
- Downloads a ready-to-run `node-compose.yaml` from the orchestrator
- Starts the node container automatically

!!! tip "Getting the compose file without running it"
    The orchestrator also serves the generated compose file directly if you want to inspect or customise it before running:
    ```bash
    curl -sSL "https://<your-orchestrator>/api/installer/compose?token=<JOIN_TOKEN>" > node-compose.yaml
    docker compose -f node-compose.yaml up -d
    ```

---

### Option B: Docker Compose (power user)

For full control over the configuration, create the compose file manually.

Create `node-compose.yaml` with the following content, substituting your JOIN_TOKEN and AGENT_URL:

```yaml
services:
  puppet-node:
    image: localhost/master-of-puppets-node:latest
    environment:
      NODE_TAGS: general,linux
      JOB_IMAGE: docker.io/library/python:3.12-alpine
      AGENT_URL: https://172.17.0.1:8001
      JOIN_TOKEN: <paste-your-enhanced-token-here>
      ROOT_CA_PATH: /app/secrets/root_ca.crt
      EXECUTION_MODE: docker
    volumes:
      - node-secrets:/app/secrets
      - /var/run/docker.sock:/var/run/docker.sock

volumes:
  node-secrets:
```

!!! tip "EXECUTION_MODE=docker"
    When the node container runs inside Docker, set `EXECUTION_MODE=docker`. This tells the node to spawn job containers using the host's Docker daemon via the mounted socket (`/var/run/docker.sock`).

    You must also add the Docker socket to the node's volumes:

    ```yaml
    volumes:
      - node-secrets:/app/secrets
      - /var/run/docker.sock:/var/run/docker.sock
    ```

    Then update your compose to mount the socket:

    ```yaml
    services:
      puppet-node:
        image: localhost/master-of-puppets-node:latest
        environment:
          ...
          EXECUTION_MODE: docker
        volumes:
          - node-secrets:/app/secrets
          - /var/run/docker.sock:/var/run/docker.sock
    ```

Then start the node:

```bash
docker compose -f node-compose.yaml up -d
```

---

## Step 4: Verify enrollment

Check the node logs:

```bash
docker compose -f node-compose.yaml logs -f
```

On successful enrollment you should see:

```
Detected Enhanced Token. Bootstrapping Trust...
Node enrolled successfully
```

Then check the dashboard — go to **Nodes** and the node should appear with status **ONLINE** within 30 seconds as it begins sending heartbeats.

---

**Next:** [First Job →](first-job.md)
