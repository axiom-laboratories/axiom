import os
import datetime
import ipaddress
import socket
from cryptography import x509
from cryptography.x509.oid import NameOID
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa, ed25519

class CertificateAuthority:
    def __init__(self, ca_dir="ca"):
        self.ca_dir = ca_dir
        self.key_path = os.path.join(ca_dir, "root_ca.key")
        self.cert_path = os.path.join(ca_dir, "root_ca.crt")
        os.makedirs(ca_dir, exist_ok=True)

    def ensure_root_ca(self):
        """Generates a self-signed Root CA if it doesn't exist."""
        if os.path.exists(self.key_path) and os.path.exists(self.cert_path):
            print("Loading existing Root CA...")
            return

        print("Generating new Root CA...")
        # Generate Private Key
        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=4096,
        )

        # Generate Root Certificate
        subject = issuer = x509.Name([
            x509.NameAttribute(NameOID.COUNTRY_NAME, u"US"),
            x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, u"Cyberspace"),
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, u"Puppet Master Internal CA"),
            x509.NameAttribute(NameOID.COMMON_NAME, u"Puppet Master Root CA"),
        ])

        cert = x509.CertificateBuilder().subject_name(
            subject
        ).issuer_name(
            issuer
        ).public_key(
            private_key.public_key()
        ).serial_number(
            x509.random_serial_number()
        ).not_valid_before(
            datetime.datetime.utcnow()
        ).not_valid_after(
            datetime.datetime.utcnow() + datetime.timedelta(days=3650) # 10 Years
        ).add_extension(
            x509.BasicConstraints(ca=True, path_length=None), critical=True,
        ).sign(private_key, hashes.SHA256())

        # Save to Disk
        with open(self.key_path, "wb") as f:
            f.write(private_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.TraditionalOpenSSL,
                encryption_algorithm=serialization.NoEncryption(),
            ))

        with open(self.cert_path, "wb") as f:
            f.write(cert.public_bytes(serialization.Encoding.PEM))
            
    def get_root_cert_pem(self) -> str:
        with open(self.cert_path, "r") as f:
            return f.read()

    def issue_server_cert(self, output_key_path, output_cert_path, sans: list[str]):
        """
        No-op: Server certificate is now managed by Caddy sidecar.
        This method is kept for compatibility but does nothing active.
        """
        print("Skipping internal server cert generation (Provided by Cert-Manager)")
        return

    def sign_csr(self, csr_pem: str, common_name: str) -> str:
        """Signs a CSR with the Root CA."""
        print(f"Signing CSR for: {common_name}")
        
        # Load Root Key/Cert
        with open(self.key_path, "rb") as f:
            root_key = serialization.load_pem_private_key(f.read(), password=None)
        with open(self.cert_path, "rb") as f:
            root_cert = x509.load_pem_x509_certificate(f.read())
            
        # Load CSR
        csr = x509.load_pem_x509_csr(csr_pem.encode())
        
        # Verify CSR Signature (Security Best Practice)
        if not csr.is_signature_valid:
             raise ValueError("Example: CSR Signature Invalid")
             
        # Build Client Cert
        builder = x509.CertificateBuilder().subject_name(
            csr.subject
        ).issuer_name(
            root_cert.subject
        ).public_key(
            csr.public_key()
        ).serial_number(
            x509.random_serial_number()
        ).not_valid_before(
            datetime.datetime.utcnow()
        ).not_valid_after(
            datetime.datetime.utcnow() + datetime.timedelta(days=365)
        ).add_extension(
            x509.BasicConstraints(ca=False, path_length=None), critical=True,
        ).add_extension(
            x509.KeyUsage(
                digital_signature=True,
                key_encipherment=True, # For RSA
                content_commitment=False,
                data_encipherment=False,
                key_agreement=False,
                key_cert_sign=False,
                crl_sign=False,
                encipher_only=False,
                decipher_only=False
            ),
            critical=True
        ).add_extension(
             x509.ExtendedKeyUsage([x509.OID_CLIENT_AUTH]), critical=True
        )

        signed_cert = builder.sign(root_key, hashes.SHA256())
        
        return signed_cert.public_bytes(serialization.Encoding.PEM).decode()

    def ensure_signing_key(self, secrets_dir="secrets"):
        """Generates Ed25519 Signing Key (Private) and Verification Key (Public) if missing."""
        signing_key_path = os.path.join(secrets_dir, "signing.key")
        verify_key_path = os.path.join(secrets_dir, "verification.key")
        os.makedirs(secrets_dir, exist_ok=True)
        
        if os.path.exists(signing_key_path) and os.path.exists(verify_key_path):
            print("Loading existing Code Signing Keys...")
            return

        print("Generating new Ed25519 Code Signing Keys...")
        private_key = ed25519.Ed25519PrivateKey.generate()
        public_key = private_key.public_key()
        
        # Save Private Key
        with open(signing_key_path, "wb") as f:
            f.write(private_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.NoEncryption()
            ))
            
        # Save Public Key
        with open(verify_key_path, "wb") as f:
            f.write(public_key.public_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PublicFormat.SubjectPublicKeyInfo
            ))
        
        print(f"✅ Code Signing Keys generated in secrets directory")
