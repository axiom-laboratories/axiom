from agent_service.pki import CertificateAuthority
import os
import shutil
import pytest
from cryptography import x509
from cryptography.hazmat.primitives import serialization

@pytest.fixture
def ca_temp(tmp_path):
    ca_dir = tmp_path / "ca"
    ca = CertificateAuthority(ca_dir=str(ca_dir))
    return ca

def test_ca_creation(ca_temp):
    ca_temp.ensure_root_ca()
    assert os.path.exists(ca_temp.key_path)
    assert os.path.exists(ca_temp.cert_path)
    
    cert_pem = ca_temp.get_root_cert_pem()
    assert "-----BEGIN CERTIFICATE-----" in cert_pem

def test_issue_server_cert(ca_temp, tmp_path):
    ca_temp.ensure_root_ca()
    key_out = tmp_path / "server.key"
    cert_out = tmp_path / "server.crt"
    
    ca_temp.issue_server_cert(str(key_out), str(cert_out), ["localhost", "127.0.0.1"])
    
    assert os.path.exists(str(key_out))
    assert os.path.exists(str(cert_out))
    
    with open(str(cert_out), "rb") as f:
        cert = x509.load_pem_x509_certificate(f.read())
        assert cert.subject.get_attributes_for_oid(x509.NameOID.COMMON_NAME)[0].value == "localhost"

def test_ensure_signing_key(ca_temp, tmp_path):
    secrets_dir = tmp_path / "secrets"
    ca_temp.ensure_signing_key(secrets_dir=str(secrets_dir))
    
    assert os.path.exists(secrets_dir / "signing.key")
    assert os.path.exists(secrets_dir / "verification.key")
    
    with open(secrets_dir / "verification.key", "rb") as f:
        pub_key = serialization.load_pem_public_key(f.read())
        # Ed25519 public key should be loadable
