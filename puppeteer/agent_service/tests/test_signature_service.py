import pytest
import base64
from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography.hazmat.primitives import serialization
from agent_service.services.signature_service import SignatureService
from agent_service.models import SignatureCreate
from agent_service.db import User

@pytest.fixture
def test_user():
    return User(username="testadmin")

@pytest.mark.anyio
async def test_upload_and_list_signatures(db_session, test_user):
    # 1. Generate a real key for testing
    private_key = ed25519.Ed25519PrivateKey.generate()
    public_key = private_key.public_key()
    pub_pem = public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo
    ).decode()

    # 2. Upload
    sig_req = SignatureCreate(name="Test Sig", public_key=pub_pem)
    upload_res = await SignatureService.upload_signature(sig_req, test_user, db_session)
    assert upload_res.name == "Test Sig"
    sig_id = upload_res.id

    # 3. List
    sigs = await SignatureService.list_signatures(db_session)
    assert len(sigs) > 0
    assert any(s.id == sig_id for s in sigs)

    # 4. Verify (Internal Helper)
    message = "hello world"
    signature = private_key.sign(message.encode())
    sig_b64 = base64.b64encode(signature).decode()
    
    # Should not raise exception
    SignatureService.verify_payload_signature(pub_pem, sig_b64, message)

@pytest.mark.anyio
async def test_verify_invalid_signature():
    private_key = ed25519.Ed25519PrivateKey.generate()
    public_key = private_key.public_key()
    pub_pem = public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo
    ).decode()

    message = "valid message"
    wrong_message = "invalid message"
    signature = private_key.sign(message.encode())
    sig_b64 = base64.b64encode(signature).decode()

    with pytest.raises(Exception):
        SignatureService.verify_payload_signature(pub_pem, sig_b64, wrong_message)
