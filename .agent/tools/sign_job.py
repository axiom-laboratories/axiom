import base64
import json
import os
import sys
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.asymmetric import padding

SECRETS_DIR = "secrets"
SIGNING_KEY_PATH = os.path.join(SECRETS_DIR, "signing.key")

def sign_content(content: str) -> str:
    if not os.path.exists(SIGNING_KEY_PATH):
        raise FileNotFoundError(f"Signing key not found at {SIGNING_KEY_PATH}")
        
    with open(SIGNING_KEY_PATH, "rb") as key_file:
        private_key = serialization.load_pem_private_key(
            key_file.read(),
            password=None
        )

    signature = private_key.sign(
        content.encode('utf-8'),
        padding.PSS(
            mgf=padding.MGF1(hashes.SHA256()),
            salt_length=padding.PSS.MAX_LENGTH
        ),
        hashes.SHA256()
    )
    
    return base64.b64encode(signature).decode('utf-8')

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python sign_job.py <content_string_or_file>")
        sys.exit(1)
        
    input_data = sys.argv[1]
    if os.path.exists(input_data):
        with open(input_data, "r") as f:
            content = f.read()
    else:
        content = input_data
        
    sig = sign_content(content)
    print(sig)
