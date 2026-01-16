import os
import argparse
import base64
import json
import httpx
from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography.hazmat.primitives import serialization

# Configuration
SIGNING_KEY_PATH = "secrets/signing.key"
VERIFY_KEY_PATH = "secrets/verification.key"
MODEL_SERVICE_URL = "https://localhost:8000"
ROOT_CA_PATH = "../ca/certs/root_ca.crt"

def generate_keys():
    """Generates Ed25519 keypair."""
    private_key = ed25519.Ed25519PrivateKey.generate()
    public_key = private_key.public_key()

    # Save Private Key
    with open(SIGNING_KEY_PATH, "wb") as f:
        f.write(private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        ))
    print(f"Generated {SIGNING_KEY_PATH}")

    # Save Public Key
    with open(VERIFY_KEY_PATH, "wb") as f:
        f.write(public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        ))
    print(f"Generated {VERIFY_KEY_PATH}")

def load_signing_key():
    if not os.path.exists(SIGNING_KEY_PATH):
        raise FileNotFoundError(f"Signing key not found at {SIGNING_KEY_PATH}. Run --generate first.")
    with open(SIGNING_KEY_PATH, "rb") as f:
        return serialization.load_pem_private_key(f.read(), password=None)

def sign_content(content: str) -> str:
    private_key = load_signing_key()
    signature = private_key.sign(content.encode("utf-8"))
    return base64.b64encode(signature).decode("utf-8")

def submit_job(script_path: str, task_type="python_script"):
    # Read Script
    with open(script_path, "r") as f:
        script_content = f.read()
    
    # Sign it
    signature = sign_content(script_content)
    print(f"Signature generated: {signature[:10]}...")

    # Payload
    payload = {
        "script_content": script_content,
        "signature": signature,
        "requirements": [],
        "secrets": {}
    }

    # Submit
    try:
        print(f"Submitting to {MODEL_SERVICE_URL}...")
        resp = httpx.post(
            f"{MODEL_SERVICE_URL}/submit_intent",
            json={
                "task_type": task_type,
                "payload": payload,
                "priority": 10
            },
            verify=ROOT_CA_PATH if os.path.exists(ROOT_CA_PATH) else False
        )
        print(f"Response: {resp.status_code}")
        print(resp.json())
    except Exception as e:
        print(f"Submission Error: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Admin Tool for Code Signing")
    parser.add_argument("--generate", action="store_true", help="Generate new Keypair")
    parser.add_argument("--sign", help="Path to script file to sign and submit")
    
    args = parser.parse_args()

    if args.generate:
        generate_keys()
    elif args.sign:
        submit_job(args.sign)
    else:
        parser.print_help()
