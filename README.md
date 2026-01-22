# Master of Puppets - Orchestration Toolkit

> **Status**: Production-Ready / Zero-Trust / Observable
> **Current Version**: 1.2.0 (Strict mTLS & Health Centre)

## Overview
**Master of Puppets** is a secure, scalable, and containerized orchestration framework designed for executing defined automation tasks with strict security and observability. It features a Pull-based architecture, Zero-Trust security (mTLS/JWT/Signatures), a comprehensive React Dashboard, and is fully deployable via Docker/Podman.

## System Architecture

### 1. Control Plane (`agent_service`)
*   **Port**: `8001` (HTTPS, mTLS Required)
*   **Tech**: FastAPI, SQLAlchemy (Async), PostgreSQL.
*   **Role**: The brain. Manages Job Queue, Node Registration, Authentication (JWT), PKI (CA), and State.
*   **Security**: Enforces strict mutual TLS. Rejects any connection without a valid client certificate signed by the internal Root CA.

### 2. Environment Node (`environment_service`)
*   **Tech**: Python, httpx, psutil.
*   **Role**: The efficient worker. Proactively heartbeats (stats) and polls for work. Executes tasks in isolated subprocesses.
*   **Security**: 
    *   **Self-Bootstrapping**: Bootstraps trust via a secure `JOIN_TOKEN` (embedded Root CA).
    *   **Signature Verification**: Verifies digital signatures (RSA-2048) of all jobs before execution.
    *   **Strict mTLS**: Refuses to connect to an unverified server.

### 3. Dashboard Health Centre (`dashboard`)
*   **Port**: `5173` (HTTP)
*   **Tech**: React, Vite, TypeScript, TanStack Query, Recharts, Shadcn/ui.
*   **Role**: Real-time telemetry and control.
    *   **Live Metrics**: CPU/RAM sparklines for every node.
    *   **Status Indicators**: Instant feedback on Node health (Online/Offline/Busy).
    *   **Secure Integration**: Connects directly to the backend API via HTTPS.

## Deployment & Operations

### Prerequisites
*   **Docker** (or Podman)
*   **Python 3.12+** (for automation scripts)
*   **SSH Access** to the target server (e.g., `speedy_mini`).

### 1. Server Deployment
Deploys the backend services (Agent, Model, DB) and updates the dashboard.
```bash
python deploy_server_update.py
```
*   Updates codebase.
*   Regenerates/Uploads Certificates (Server Certs, Verification Keys).
*   Restarts the Docker stack remotely.

### 2. Dashboard Deployment
Builds the frontend and deploys the static assets.
```bash
python deploy_dashboard.py
```
*   Builds React app (Vite).
*   Deploys to Nginx container.

### 3. Node Cluster Deployment
Updates the worker nodes with the latest trust anchors.
```bash
python sync_and_rebuild.py
```

## Verification

### Quick Health Check
Run diagnostics to check container status and logs.
```bash
python diagnostic_v2.py
```

### End-to-End Test (Signed Job)
Dispatch a real, cryptographically signed job to the cluster.
```bash
python run_signed_job.py
```
*   **Success**: Returns HTTP 200 and confirms execution in logs.
*   **Failure**: HTTP 403/401 or Signature Verification Error (if keys mismatch).

## Security Architecture (Zero-Trust)
1.  **Transport**: All communication is TLS 1.3.
2.  **Identity**: Nodes are identified by Client Certificates (CN=NodeID).
3.  **Execution**: Jobs are signed by the Developer/Admin (Private Key) and verified by the Node (Public Key). The Server is a pass-through and cannot forge jobs.

## Development
- **Backend**: `agent_service/`
- **Frontend**: `dashboard/`
- **Nodes**: `environment_service/`
- **Tooling**: Root directory scripts (`deploy_*.py`, `check_*.py`).

### Local Dev Setup
1.  `pip install -r requirements.txt`
2.  `cd dashboard && npm install`
3.  Create `secrets.env` based on `.env.example`.



