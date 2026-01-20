# Next Session Handover

## Current Status
**Phase 2 (Universal Installer & Token Security) is COMPLETE.**
- **Installer**: `installer/install_universal.ps1` is the single source of truth.
- **Security**: Nodes enroll using strictly validated SSL (via embedded CA in Token).
    - *Note*: The verified "One-Liner" uses `curl -k` for the initial bootstrap of the compose file to avoid Windows Schannel trust store issues, but the *runtime* (Python) uses the strict CA path.
- **Backend**: Legacy client-side mount logic removed from `agent_service/main.py`.
- **Frontend**: Dashboard provides a copy-paste "One-Liner" for deployment.

## Recent Changes
- Created `installer/install_universal.ps1`.
- Deleted `installer/install_node.ps1` (Legacy).
- Modified `agent_service/main.py` -> `/api/installer` endpoint & legacy code removal.
- Modified `dashboard/.../AddNodeModal.jsx`.

## Verification
- **Universal Installer**: Verified on Windows Host using `iex (irm ...)` flow.
- **Alpine Containers**: Confirmed functionality with `musl` libc.
- **Token**: Validated decoding and cert extraction.

## Known Issues / Context
- **Global Network Mounts**: The database config for `global_network_mounts` was cleared during verification to resolve permission errors. Re-configuring this requires a UI or DB Admin tool (Feature Request).
- **SSL Trust on Windows Host**: `curl` via PowerShell/Schannel relies on the System Trust Store. We bypassed this for the bootstrap to keep the installer simple ("One-Liner"). Phase 3 (Real SSL) will resolve this permanently.

## Next Objectives (Phase 3)
1.  **SSL Hardening**: Obtain/Integrate proper SSL certificates (e.g., Let's Encrypt or Domain CA) to remove the need for CA extraction/trust workarounds.
2.  **Security Review**: Address findings from the Security Review (e.g., RCE mitigation if any pending).
3.  **Third Party Tool Audit**: Complete the audit if not finished.
