# Master of Puppets - Orchestration Toolkit

> **Status**: Industrial-Grade / Zero-Trust Implementation
> **Current Version**: 0.4.0 (Secure Secrets)

## Overview
"Master of Puppets" is a scalable, secure, and resilient orchestration framework designed to execute defined automation tasks on a strict schedule. It employs a pull-based architecture with strict Zero-Trust security principles, ensuring that code execution is authenticated, authorized, and ephemeral.

## System Architecture

### Components
1.  **Agent Service (`agent_service`)**: The central Hub. Manages job queues, state, and node registration.
    *   *Port*: `8001` (HTTPS)
    *   *Database*: SQLite (`jobs.db`) with Fernet Encryption.
2.  **Model Service (`model_service`)**: The "Scheduler". Defines tasks and schedules their execution.
    *   *Port*: `8000` (HTTPS)
3.  **Environment Node (`environment_service`)**: The Worker. Polls for work and executes tasks in isolated processes.
    *   *Dynamic ID*: Auto-enrolled via ACME.
4.  **Dashboard (`dashboard`)**: React-based UI for monitoring and control.
    *   *Port*: `5173`

### Security (Zero-Trust)
-   **mTLS / HTTPS**: All service-to-service communication is encrypted.
-   **ACME (Smallstep)**: Nodes automatically strictly enroll with a private CA (`step-ca`) to obtain unique certificates.
-   **Encryption at Rest**: Sensitive data (Secrets) is encrypted in the DB using AES-128 (Fernet).
-   **Redaction**: API endpoints automatically mask sensitive data.
-   **Process Isolation**: Python scripts are executed in ephemeral subprocesses with environment-variable-only secret injection.

## Setup & Usage

### Prerequisites
-   Python 3.12+
-   Node.js / npm
-   `step` and `step-ca` (Smallstep CLI)

### 1. Initialize Certificate Authority
```powershell
# Initialize CA (Run once)
step ca init --name "Puppet Master CA" --dns "localhost" --address ":9000" --provisioner "admin"
# Start CA
step-ca c:/Development/Repos/master_of_puppets/ca/config/ca.json
```

### 2. Start Services
Run each in a separate terminal:
```powershell
# Agent (Hub)
python agent_service/main.py

# Model (Brain)
python model_service/main.py

# Node (Worker) - Auto-enrolls on start
python environment_service/node.py

# Dashboard (UI)
cd dashboard
npm install
npm run dev
```

### 3. Usage
-   **Dashboard**: Open `http://localhost:5173`.
-   **Node Management**: Use the Dashboard to Generate Join Tokens and Upload Verification Keys.
-   **Trigger Job**:
    *   *Web Task*: Can be triggered via API/Dashboard.
    *   *Python Script*: **MUST** be signed. Use `tools/admin_signer.py` (see [Tools Docs](tools/README.md)).
-   **View Results**: Job cards will update with "ASSIGNED" -> "COMPLETED". Secrets will be redacted in the UI (`******`).

## Design Log & Increments

This log tracks the evolution of the system based on user requirements.

### v0.1: Initial Prototype
-   Basic Pull-Model architecture.
-   HTTP communication.
-   Simple `web_task` execution.

### v0.2: Industrial-Grade Upgrade
-   **HTTPS Enforcement**: Migrated all services to SSL.
-   **ACME Integration**: Implemented `step-ca` for automated Node enrollment.
-   **Agent Registration Endpoint**: Added `/auth/register` for token exchange.

### v0.3: Remote Script Execution
-   **Native Python Support**: Added `python_script` task type.
-   **Pre-flight Checks**: Nodes validate `requirements` (e.g., `dir_exists`) before accepting work.
-   **Process Isolation**: Scripts run in proper subprocesses, not `eval()`.

### v0.4: Secure Secrets Lifecycle (Current)
-   **Requirement**: "Hide all secrets... plain text nowhere."
-   **Encryption at Rest**: Implemented `Fernet` encryption for SQLite storage.
-   **UI Redaction**: APIs modified to return masked (`******`) values.
-   **Safe Logging**: Node logs sanitized to prevent secret leakage.
-   **Ephemeral Injection**: Secrets decrypted only at the edge (Node) and injected into ephemeral environment variables.

### v0.5: RCE Prevention (Current)
-   **Code Signing**: Implemented Ed25519 signature verification on Nodes.
-   **Admin Tooling**: Added `tools/admin_signer.py` for offline signing.
-   **File Hygiene**: Moved all keys and secrets to `secrets/` directory.

## Future Roadmap
-   [ ] PostgreSQL Migration (Persistence).
-   [ ] Docker / Kubernetes Deployment.
-   [ ] Role-Based Access Control (RBAC).
