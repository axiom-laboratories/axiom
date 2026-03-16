# Master of Puppets — Remote Deployment Guide

This guide explains how to deploy the MOP Server on a remote Linux host and enroll nodes across the network.

## 1. Server Deployment

To deploy the orchestrator on a fresh Linux instance (Debian/Ubuntu/RHEL):

1.  **Clone the Repository**:
    ```bash
    git clone https://github.com/your-repo/master_of_puppets.git
    cd master_of_puppets
    ```

2.  **Run the Deploy Script**:
    ```bash
    # Optionally provide your FQDN or IP
    ./puppeteer/installer/deploy_server.sh puppetmaster.yourdomain.com
    ```
    This script will:
    *   Install Docker and Compose if missing.
    *   Initialize `.env` with random secrets.
    *   Configure Caddy with the correct `SERVER_HOSTNAME` for TLS.
    *   Launch the full stack (Database, Agent, Model, Dashboard, Registry).

3.  **Establish Trust**:
    Visit `http://<your-ip>/system/root-ca-installer` in your browser or run the curl command provided by the script to install the MOP Root CA on your management machine.

## 2. Node Enrollment

Once the server is running:

1.  **Generate a Token**:
    Log in to the Dashboard at `https://<your-ip>`, go to **Nodes**, and click **Generate Join Token**.

2.  **Run the Universal Installer**:
    On your remote node (the "Puppet"):
    ```bash
    curl -sSL http://<server-ip>/installer.sh | sudo bash -s -- --token "YOUR_TOKEN"
    ```
    *Note: Running with `sudo` allows the installer to add the MOP Root CA to the system trust store, enabling secure HTTPS communication for all subsequent operations.*

## 3. Architecture & Ports

| Service | Port | Protocol | Description |
|---------|------|----------|-------------|
| Caddy (Bootstrap) | 80 | HTTP | Used for initial CA download and installer script. |
| Caddy (Secure) | 443 | HTTPS | Main API and Dashboard (mTLS enforced for nodes). |
| Registry | 5000 | HTTP | Internal Docker registry for Foundry images. |

## 4. Troubleshooting

### SSL Errors
If nodes fail to connect with "Certificate Signed by Unknown Authority":
1.  Ensure the node has run the installer with `sudo` or manually installed `bootstrap_ca.crt`.
2.  Check that `SERVER_HOSTNAME` in `.env` matches the address used by the node.

### Connection Timeout
Ensure the server's firewall allows incoming traffic on ports **80** and **443**.
