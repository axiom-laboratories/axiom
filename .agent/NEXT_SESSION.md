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
- **Cross-Platform Support (`v1.1`)**:
    - Updated `install_universal.ps1` with `-Platform [Podman|Docker]`.
    - Updated `main.py` Config API to inject `host.docker.internal` vs `host.containers.internal`.
    - Verified functionality on Podman (Windows) and Docker (Simulated).

## Verification
- **SSL**: Host machine trusts the internal CA. `curl https://localhost:8001` works.
- **Node Isolation**: Node connects successfully in Bridge mode.
- **Mounts**: Validated Node can write to a specific Host directory via DrvFS/Podman mount while in Bridge mode.
- **Docker**: Config API returns correct Host URL when `platform=Docker` is requested.

## Next Objectives
**Remote Environment Validation**
- [ ] **Remote Connect**: SSH into User-provided Debian environment.
- [ ] **Deploy Stack**: Clone repo and deploy Server stack (Docker/Podman).
- [ ] **Deploy Node**: Test Universal Installer on Linux (Bash equivalent needed or adapt PS1 if pwsh available).
- [ ] **Validation**: Verify Node -> Server connectivity in a true remote Linux context.
