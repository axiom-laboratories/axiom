# Progress Handover
**Last Updated:** 2026-01-16 (v0.7 Completed)

## Current Status
- **Phase:** v0.7 Implementation (Containerization & RBAC)
- **Active Task:** Verification & Deployment Testing
- **State:** Codebase is fully refactored for PostgreSQL, Podman containers, and JWT Authentication.

## v0.7 Changes (Detailed)
### 1. Containerization (Podman)
- Replaced direct Python execution with `podman-compose`.
- **Files**: `compose.server.yaml`, `Containerfile.server`, `Containerfile.node`, `dashboard/Containerfile`.
- **Scripts**: `install_server.ps1/sh` (Server), `installer/install_node.ps1/sh` (Node).
- **Database**: Migrated from SQLite to **PostgreSQL**.

### 2. Backend (Agent Service)
- **SQLAlchemy ORM**: `agent_service/db.py` defines `User`, `Node`, `Job` models.
- **Authentication**: `auth.py` implements JWT (HS256).
    - Login: `POST /auth/login`
    - Users: Bootstraps `admin` (pw: `admin`) on startup.
- **Node Management**:
    - **Heartbeats**: Proactive PUSH from Node (`POST /heartbeat`).
    - **Enrollment**: Still uses `step-ca` (mocked or CLI based).

### 3. Frontend (Dashboard)
- **Tech**: React + Vite + React Router + Recharts.
- **Routing**:
    - `/` -> Dashboard (KPIs, Active Nodes, Failure Trends).
    - `/nodes` -> Grid view of nodes with CPU/RAM Stats (Live).
    - `/jobs` -> Job History & Submission.
    - `/admin` -> Key Management & Token Generation.
    - `/login` -> Auth Entry.

### 4. Node Agent
- **Proactive Heartbeat**: Runs a background thread sending cpu/ram stats to Agent every 30s.
- **Proactive Polling**: Polls `/work/pull` for jobs.

## Next Steps for Next Agent
1.  **Build & Run**:
    - The code is committed, but the dashboard container image needs building.
    - Run: `cd dashboard && cmd /c "npm install" && cd ..`
    - Run: `podman-compose -f compose.server.yaml build`
    - Run: `podman-compose -f compose.server.yaml up -d`
2.  **Testing**:
    - Verify `admin` login works.
    - Verify `install_node.ps1` correctly bootstraps a Windows node.
    - Verify Heartbeats appear on the Dashboard `/nodes` page.
3.  **Known Issues**:
    - **SSL**: `install_server.ps1` generates self-signed certs. Browsers will warn.
    - **Secrets**: `secrets/` directory is volume mounted. Ensure `api_key` and `encryption_key` match between containers.

## Environment Variables (New)
- `DATABASE_URL`: `postgresql+asyncpg://user:pass@db:5432/jobs`
- `SECRET_KEY`: For JWT signing.
- `ROOT_CA_PATH`: Path to CA crt for mTLS (if enabled).

## Command History
- `npm install` (Dashboard dependencies)
- `git commit -m "feat: v0.7..."`
