import logging
import os
from .. import pki

logger = logging.getLogger(__name__)

class PKIService:
    def __init__(self, ca_dir: str = "secrets/ca"):
        # Check if we have a mounted global CA from cert-manager (Caddy)
        global_ca_dir = "/app/global_certs"
        if os.path.exists(os.path.join(global_ca_dir, "root_ca.crt")):
            logger.info("🛡️ Using global cert-manager CA for PKI operations")
            self.ca_authority = pki.CertificateAuthority(ca_dir=global_ca_dir)
            # Re-map standard filenames used by agent_service to match cert-manager output
            self.ca_authority.cert_path = os.path.join(global_ca_dir, "root_ca.crt")
            self.ca_authority.key_path = os.path.join(global_ca_dir, "root_ca.key")
        else:
            self.ca_authority = pki.CertificateAuthority(ca_dir=ca_dir)

    def get_root_cert_pem(self) -> str:
        """Returns the Root CA certificate in PEM format."""
        return self.ca_authority.get_root_cert_pem()

    def sign_csr(self, csr_pem: str, hostname: str) -> str:
        """Signs a CSR and returns the issued certificate."""
        return self.ca_authority.sign_csr(csr_pem, hostname)

# Global Instance
pki_service = PKIService()
