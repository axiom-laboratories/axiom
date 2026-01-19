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
# Note: Ensure you have built the dashboard first if developing locally
# cd dashboard; npm install; cd ..

podman-compose -f compose.server.yaml build
podman-compose -f compose.server.yaml up -d
```

Validating:
*   **Dashboard**: `http://localhost:5173` (Login: `admin` / `admin`)
*   **Agent API**: `https://localhost:8001/` (Self-signed cert warning is expected)

### 2. Deploy a Node
Nodes are designed to run on separate machines (or separate terminals).

**Windows Node:**
```powershell
# In a new PowerShell terminal
# Usage: .\install_node.ps1 -JoinToken "..." [-Count N]
./installer/install_node.ps1
```
*   **Join Token**: Generate one from the Dashboard (Admin -> Generate Token).
*   **Scaling**: Use `-Count 5` to spin up 5 nodes on one machine.

**Linux Node:**
```bash
./installer/install_node.sh
```

## Dashboard Guide

### 📊 Dashboard
*   **KPI Cards**: Shows Active Nodes count, Running Jobs, and Success Rate.
*   **Failure Trends**: 7-Day bar chart of job failures.
*   **Recent Activity**: Scrolling feed of latest jobs.

### 🖥 Nodes
*   **Live Grid**: Visual representation of all enrolled nodes.
*   **Badges**: `ONLINE` (Green), `OFFLINE` (Red).
*   **Stats**: Real-time CPU/RAM progress bars (Green -> Yellow -> Orange).

### ⚙ Admin
*   **Node Onboarding**: Generate Join Tokens.
*   **Network Mounts**: Configure global SMB/CIFS paths for Nodes.
*   **Code Signing**: upload new public keys for script verification.

## Release Notes

### v0.8: Security & Connectivity (Current)
*   **Managed Network Mounts**: Centralized "Host-Passthrough" SMB mounting.
*   **Native mTLS**: Nodes generate their own keys and request certs (CSR) from the Agent.
*   **Trust Bootstrapping**: Zero-config deployment; Token carries the Root CA.
*   **Security Fixes**: Restored RCE Signature Verification, fixed CRL check issues on Windows.

### v0.7: Observability & Containers
*   **PostgreSQL**: Replaced SQLite for production-grade storage.
*   **Containerization**: Full support for Podman/Docker.
*   **RBAC**: Added User/Role models and JWT authentication.
*   **Heartbeats**: Added proactive node telemetry.
*   **Dashboard**: Complete UI overhaul with separate views.

### v0.6: Infrastructure
*   **Containerfiles**: Dockerfiles created for all services.
*   **Installers**: Cross-platform deployment scripts (`.ps1`, `.sh`).

### v0.5: RCE Prevention
*   **Code Signing**: Ed25519 signature verification for python scripts.

## Next Steps / Roadmap
1.  **Documentation Wiki**: Integrated documentation system in the Dashboard.
2.  **Production Hardening**: Replace internal PKI with Step CA / Let's Encrypt options.
3.  **Orchestration**: Deploy to Kubernetes (Helm Charts).
