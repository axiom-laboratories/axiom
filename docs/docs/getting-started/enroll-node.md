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
    image: docker.io/library/python:3.12-alpine
    environment:
      NODE_TAGS: general,linux
      JOB_IMAGE: docker.io/library/python:3.12-alpine
      AGENT_URL: https://172.17.0.1:8001
      JOIN_TOKEN: <paste-your-enhanced-token-here>
      ROOT_CA_PATH: /app/secrets/root_ca.crt
      EXECUTION_MODE: direct
    volumes:
      - node-secrets:/app/secrets

volumes:
  node-secrets:
```

!!! tip "EXECUTION_MODE=direct"
    When the node container runs inside Docker (as it does here), setting `EXECUTION_MODE=direct` tells the node to execute job scripts as Python subprocesses rather than spawning nested containers.

    Without this, the node attempts to use Docker or Podman inside Docker, which runs into cgroup v2 permission issues and fails silently. Use `direct` mode for all standard deployments.

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
