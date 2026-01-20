# SSL & Security Guide

## default Security (Internal PKI)
Master of Puppets defaults to a "Secure by Default" architecture using an Internal Certificate Authority (CA).

1.  **Bootstrap**: On first run, the Server generates a Root CA (`ca/certs/root_ca.crt`).
2.  **Server Cert**: It issues a leaf certificate for `localhost`, `127.0.0.1`, `host.containers.internal`.
3.  **Trust Distribution**:
    *   **Nodes**: The Join Token contains the Root CA. Nodes trust it automatically.
    *   **Admins**: Run `installer/install_ca.ps1` (or use the Universal Installer) to import the Root CA into your Windows Trust Store.

## Hardening (Production/External Certs)
You can provide your own SSL certificates (e.g., from Let's Encrypt, DigiCert, or an Enterprise PKI).

### "Bring Your Own Cert" (Split-Horizon)
To use your own keys, replace the following files in the `volumes` (or mapped directories):

1.  `secrets/server.crt`: Your Server Certificate.
2.  `secrets/server.key`: Your Private Key.
3.  `ca/certs/root_ca.crt`: The CA Bundle that signed your cert (e.g., the Intermediate + Root).

**Important**:
*   Restart the Server after replacing files.
*   **Tokens**: Existing tokens will still work *if* the CA in them matches the server's issuer. If you change the CA, you must generate **NEW Tokens** for new nodes.
*   **Existing Nodes**: Will lose connectivity if the Server Cert issuer changes and they don't trust the new CA. You must update their `root_ca.crt` manually or re-enroll them.

## Troubleshooting
**Curl / Browser Errors:**
*   `SEC_E_UNTRUSTED_ROOT`: Run `install_universal.ps1` or `install_ca.ps1` to trust the CA.
*   `CERT_TRUST_REVOCATION_STATUS_UNKNOWN`: The Internal CA has no CRL. Our tools use `--ssl-no-revoke` to safely handle this while maintaining strict signature validation.
