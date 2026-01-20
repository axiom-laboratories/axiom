# Master of Puppets - Orchestration Toolkit

> **Status**: Industrial-Grade / Containerized / Zero-Trust
> **Current Version**: 0.8.0 (Security & Network Mounts)

## Overview
"Master of Puppets" is a secure, scalable, and containerized orchestration framework designed for executing defined automation tasks with strict security and observability. It features a Pull-based architecture, Zero-Trust security (mTLS/JWT), a comprehensive React Dashboard, and is fully deployable via Podman Containers.

## System Architecture (v0.8)

### Components
1.  **Agent Service (`agent_service`)**: The core orchestrator.
    *   **Port**: `8001` (HTTPS)
    *   **Tech**: FastAPI, SQLAlchemy (Async), PostgreSQL.
    *   **Role**: Manages Job Queue, Node Registration, Authentication (JWT), PKI (CA), and State.
2.  **Model Service (`model_service`)**: The Scheduling Engine.
    *   **Port**: `8000` (HTTPS)
    *   **Tech**: APScheduler, SQLAlchemy.
    *   **Role**: Defines recurring schedules and triggers jobs.
3.  **Environment Node (`environment_service`)**: The Worker.
    *   **Tech**: Python, httpx, psutil.
    *   **Role**: Proactively heartbeats (stats) and polls for work. Executes tasks in isolated subprocesses.
    *   **Security**: **Self-Bootstrapping Trust** (extracts CA from Token), **Strict mTLS** (Client Certs required).
4.  **Dashboard (`dashboard`)**: The Control Plane.
    *   **Port**: `5173`
    *   **Tech**: React, Vite, Recharts, React Router.
    *   **Role**: Visualizes Active Nodes, Job Trends, manages Admin Keys, and **Network Mounts**.

### Key Features
*   **Containerized Stack**: Fully dockerized (Podman) with `compose.server.yaml`.
*   **Database**: Migrated to **PostgreSQL** for robustness and concurrency.
*   **Security (Zero-Trust)**:
    *   **Strict mTLS**: Nodes must present a signed certificate to talk to the Agent.
    *   **Trust Bootstrapping**: Join Tokens contain the Root CA, allowing Nodes to self-initialize trust without host mounts.
    *   **RBAC**: Granular Roles (Viewer, Operator, Admin).
    *   **Secrets**: AES-128 Encryption at Rest + Redaction in UI.
*   **Managed Network Mounts**:
    *   **Host-Passthrough**: Nodes inherit the Host's Windows Authentication (Kerberos/NTLM) to access network shares.
    *   **Central Config**: Define mounts (`\\server\share` -> `/mnt/mop/share`) centrally in the Orchestrator.
    *   **Isolation**: Nodes cannot mount arbitrary paths; only what is provisioned by the Admin.
*   **Observability**:
    *   **Proactive Heartbeats**: Nodes push CPU/RAM stats every 30s.
    *   **Live Dashboard**: Real-time status of the mesh.

## Quick Start (Containerized)

### Prerequisites
*   **Podman** (with `podman-compose`) OR Docker.
*   **Python 3.12+** (for local CLI tools).

### 1. Build & Start Server Stack
This starts Postgres, Agent, Model, and Dashboard.

```powershell
# Windows (PowerShell)
podman-compose -f compose.server.yaml build
podman-compose -f compose.server.yaml up -d
```

Validating:
*   **Dashboard**: `http://localhost:5173` (Login: `admin` / `admin`)
*   **Agent API**: `https://localhost:8001/` (Self-signed cert warning is expected initially, but `install_ca.ps1` can fix this).

### 2. Trust the CA (Optional but Recommended)
To eliminate SSL warnings on your Host:
```powershell
./installer/install_ca.ps1
```

### 3. Deploy a Node (Universal Installer)
Nodes run in **Bridge Mode** and are fully isolated.
Copy the "One-Liner" from the Dashboard (Admin -> Generate Token), or run:

```powershell
iex (irm https://localhost:8001/api/installer) -Role Node -Token "..." -Count 3
```

## Release Notes

### v0.9: Hardening & Isolation (Current)
*   **Network Hardening**: Database and Model ports are now locked down (Internal-Only).
*   **Node Isolation**: Nodes run in **Bridge Mode** (no longer Host mode) but maintain SMB/DrvFS mount capabilities.
*   **SSL Hardening**:
    *   **Auto-Trust**: Installer automatically imports the Root CA to the Windows Trust Store.
    *   **Split-Horizon PKI**: Support for "Bring Your Own Certs" (external SSL).
    *   **Strict Verification**: All internal communication enforces strict SSL signature validation.
*   **Universal Installer**: Single PowerShell script (`install_universal.ps1`) for bootstrapping nodes.

### v0.8: Security & Connectivity
*   **Managed Network Mounts**: Centralized "Host-Passthrough" SMB mounting.
*   **Native mTLS**: Nodes generate their own keys and request certs (CSR) from the Agent.
*   **Trust Bootstrapping**: Zero-config deployment; Token carries the Root CA.

### v0.7: Observability & Containers
*   **PostgreSQL**: Replaced SQLite for production-grade storage.
*   **Containerization**: Full support for Podman/Docker.
*   **RBAC**: Added User/Role models and JWT authentication.

## Next Steps / Roadmap
1.  **Cross-Platform Validation**: Verify stack on Docker Desktop (in progress).
2.  **Orchestration**: Deploy to Kubernetes (Helm Charts).

