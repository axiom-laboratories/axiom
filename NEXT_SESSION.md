# Next Session Handover

## Current Status
**v0.9 Hardening Phases Complete.**
1.  **SSL Hardening (Phase 3)**:
    *   **Trust**: `install_universal.ps1` auto-imports the CA to the Windows Trust Store.
    *   **Validation**: `curl` and Node Runtime now use strict SSL verification (no more `-k` flag, except for the internal CA CRL bypass `--ssl-no-revoke`).
    *   **Architecture**: Split-Horizon PKI implemented. Supports "Bring Your Own Certs" (BYOC).
2.  **Network Hardening (Phase 4)**:
    *   **Isolation**: Nodes now run in **Bridge Mode** (previously Host Mode).
    *   **Connectivity**: Nodes connect via `host.containers.internal`.
    *   **Server**: Database and Model ports are now internal-only.
    *   **Mounts**: Fixed `agent_service/main.py` to correctly map `global_network_mounts` to specific Host Paths (e.g., `/mnt/c/Users/...`) even in Bridge Mode.

## Recent Changes
- Modified `compose.server.yaml`: Removed `ports` for `db` and `model`.
- Modified `node-compose.yaml` (via `main.py`): Removed `network_mode: host`.
- Modified `install_universal.ps1`: Added CA import logic and strict `curl` flags.
- Created `docs/ssl_guide.md`.

## Verification
- **SSL**: Host machine trusts the internal CA. `curl https://localhost:8001` works.
- **Node Isolation**: Node connects successfully in Bridge mode.
- **Mounts**: Validated Node can write to a specific Host directory via DrvFS/Podman mount while in Bridge mode.

## Next Objectives
**Cross-Platform Validation**
- [ ] **Docker Desktop**: Validate the Universal Installer and Stack on a Docker Desktop environment (ensure `host.docker.internal` vs `host.containers.internal` logic holds or adapts).
- [ ] **Alpine Optimization**: Review image sizes (optional).
