# Master of Puppets - Orchestration Toolkit

> **Status**: Production-Ready / Zero-Trust / Observable
> **Current Version**: v0.8 (Refactored Backend & Self-Healing Quality Loop)

## Overview
**Master of Puppets** is a secure, scalable, and containerized orchestration framework designed for executing defined automation tasks with strict security and observability. It features a Pull-based architecture, Zero-Trust security (mTLS/JWT/Signatures), a comprehensive React Dashboard, and is fully deployable via Docker/Podman.

## Recent Updates (v0.8)
- **Backend Refactor**: `agent_service/main.py` has been split into `models.py` and `security.py` for improved maintainability.
- **Automated Quality**: Introduced a "Self-Healing Quality Loop" workflow that maps features, identifies test gaps, and generates `pytest` coverage.
- **Documentation**: New automated asset generation pipeline (in progress) and comprehensive Feature Manifests.

## System Architecture

### 1. The Puppeteer (Control Plane)
*   **Directory**: `/puppeteer`
*   **Port**: `8001` (HTTPS, mTLS Required)
*   **Components**: Agent Service, Model Service, Database, Dashboard.
*   **Role**: The brain. Manages Job Queue, Node Registration, Authentication (JWT), PKI (CA), and State.
*   **Security**: Enforces strict mutual TLS. Rejects any connection without a valid client certificate signed by the internal Root CA.

### 2. The Puppet (Execution Node)
*   **Directory**: `/puppets`
*   **Role**: The efficient worker. Proactively heartbeats (stats) and polls for work from the Puppeteer. Executes tasks in isolated subprocesses.
*   **Security**: 
    *   **Self-Bootstrapping**: Bootstraps trust via a secure `JOIN_TOKEN` (embedded Root CA).
    *   **Signature Verification**: Verifies digital signatures (RSA-2048) of all jobs before execution.
    *   **Strict mTLS**: Refuses to connect to an unverified Puppeteer.

### 3. Dashboard Health Centre
*   **Directory**: `/puppeteer/dashboard` (Built into Puppeteer stack)
*   **Port**: `5173` (HTTP)
*   **Tech**: React, Vite, TypeScript, TanStack Query, Recharts, Shadcn/ui.
*   **Role**: Real-time telemetry and control.

## Deployment & Operations

### 1. Puppeteer (Server) Deployment
The control plane is designed to be run as a containerized stack.
*   **Deploy**: `docker compose -f compose.server.yaml up -d`
*   **Config**: Ensure `secrets.env` (see `.env.example`) and necessary certificates are present in `/puppeteer/secrets`.

### 2. Verified Workflows
New agentic workflows have been added to `.agent/workflows`:
*   `full_audit.md`: Runs a complete 9-step audit (Security, Backend, Frontend, Docs, etc.).
*   `self_healing_quality_loop.md`: Automatically finds missing tests and fills the gaps.

## Development
- **Puppeteer (Central)**: `puppeteer/agent_service` (Backend), `puppeteer/dashboard` (Frontend)
- **Puppets (Nodes)**: `puppets/environment_service`
- **Validation**: `mop_validation/` (Tests & Reports)

### Local Dev Setup
1.  `pip install -r requirements.txt`
2.  `cd puppeteer/dashboard && npm install`
3.  `pytest` (Now enabled for backend!)
