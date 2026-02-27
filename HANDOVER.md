# Master of Puppets - Handover Document

## Overview
This document serves as a comprehensive handover guide for the **Master of Puppets** project, allowing a developer to pick up development easily on a new machine.

The project is split into two primary repositories:
1. **`master_of_puppets`**: The core application, including the Puppeteer control plane, Dashboard, and Worker Node (Puppet) environments.
2. **`mop_validation`**: The private repository containing all validation, security scanning scripts, end-to-end test runners, and generated audit reports.

---

## Getting Started on a New Machine

### Prerequisites
- Python 3.12+ 
- Node.js 20+ (for Dashboard)
- Docker / Docker Compose (for running the server and node locally)
- Git

### 1. Clone Repositories
Ensure both repositories are cloned side-by-side:
```bash
git clone <remote-url>/master_of_puppets
git clone <remote-url>/mop_validation
```

### 2. Setup `master_of_puppets` (Core Application)
1. **Dashboard UI**:
    ```bash
    cd master_of_puppets/puppeteer/dashboard
    npm install
    npm run build
    ```
2. **Puppeteer Control Plane (Server)**:
    ```bash
    cd master_of_puppets/puppeteer
    python -m venv .venv
    source .venv/bin/activate  # On Windows: .venv\Scripts\activate
    pip install -r requirements.txt
    ```
    To start the server using Docker Compose (includes DB):
    ```bash
    docker-compose -f compose.server.yaml up -d
    ```

3. **Puppet Node**:
    Nodes run as sidecar/containers or processes pulling jobs from the control plane.
    To build the node image:
    ```bash
    cd master_of_puppets/puppets
    docker build -f Containerfile.node -t localhost/master-of-puppets-node:latest .
    ```

### 3. Setup `mop_validation` (Testing & Auditing)
1. **Environment Setup**:
    ```bash
    cd mop_validation
    python -m venv .venv
    source .venv/bin/activate  # On Windows: .venv\Scripts\activate
    pip install -r requirements.txt
    ```
2. **Secrets Configuration**:
    Create `secrets.env` based on `secrets.env.example` in this repo to inject keys for GitHub token code scanning and other validation checks.

---

## Current State & Recent Changes

### Architecture & Fixes (Feb 2026)
- **Runtime Environment Update**: Migrated the Puppet Worker Node image from Alpine to a Debian `slim` base (`python:3.12-slim`) for better compatibility with Python extension wheels (like cryptography) via `apt-get` instead of `apk`.
- **E2E Runner**: Upgraded `scripts/e2e_runner.py` in `mop_validation` to use `docker` instead of `podman`, checking logs appropriately for security verification.
- **Dynamic Configuration**: The server now features a dynamic compose generator endpoint (`/api/installer/compose`) allowing nodes to easily pull their configuration.
- **Port Mapping**: Postgres is now exposed on `5432` for easier debugging within `compose.server.yaml`.
- **UI Adjustments**: Applied critical accessibility properties to React components (e.g. `aria-label`, `htmlFor`).

### Outstanding Items / Next Steps
1. **Clean up untracked scripts**: Several diagnostic scripts (`deploy_speedy_mini.py`, `submit_job.py`, etc.) exist in `master_of_puppets` root. These should be moved to `mop_validation` eventually.
2. **Verify the E2E Test Flow**: Run `python e2e_runner.py` in `mop_validation` to ensure RCE signature verification is actively enforced on deployed nodes.
