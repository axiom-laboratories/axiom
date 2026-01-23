import requests
import json
import time
import os
import sys
import base64
import subprocess
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.asymmetric import padding
from dotenv import load_dotenv

# Load Env
load_dotenv("secrets.env")

SERVER_URL = os.getenv("AGENT_URL", "https://localhost:8001")
API_KEY = os.getenv("API_KEY", "master-secret-key")
# Try multiple paths for signing key
POSSIBLE_KEYS = [
    "puppeteer/secrets/signing.key",
    "c:/Development/Repos/master_of_puppets/puppeteer/secrets/signing.key",
    "../puppeteer/secrets/signing.key",
    "secrets/signing.key"
]

def get_signing_key_path():
    for p in POSSIBLE_KEYS:
        if os.path.exists(p):
            return p
    return None

def sign_content(content: str) -> str:
    path = get_signing_key_path()
    if not path:
        raise FileNotFoundError("Signing Key not found. Please ensure puppeteer/secrets/signing.key exists.")
        
    with open(path, "rb") as key_file:
        private_key = serialization.load_pem_private_key(key_file.read(), password=None)
    
    signature = private_key.sign(
        content.encode('utf-8'),
        padding.PSS(mgf=padding.MGF1(hashes.SHA256()), salt_length=padding.PSS.MAX_LENGTH),
        hashes.SHA256()
    )
    return base64.b64encode(signature).decode('utf-8')

JOB_SCRIPT = """
import os
import datetime
import subprocess

# Determine Mount Path (Logic from verify_ping.py or dynamic)
# node.py injects MOUNT_TEST_LOCAL if configured.
mount_path = os.environ.get("MOUNT_TEST_LOCAL", "/mnt/c/Development/Repos/master_of_puppets/test_mount")

if not os.path.exists(mount_path):
    print(f"Mount path {mount_path} does not exist inside container!")
    # Fallback for debugging output
    mount_path = "/tmp"

target_file = os.path.join(mount_path, "verification.txt")

klist_output = "Not Checked"
try:
    # Check Kerberos
    # 'klist' might not be in path for alpine? install krb5-client.
    # Assuming host passed ticket.
    klist_output = subprocess.check_output(["klist"], text=True)
except FileNotFoundError:
    klist_output = "klist command not found"
except Exception as e:
    klist_output = f"Error running klist: {e}"

output = f"Job ID: {os.environ.get('guid', 'unknown')} | Timestamp: {datetime.datetime.now()}\\n"
output += f"Kerberos Check:\\n{klist_output}\\n"
output += "-" * 20 + "\\n"

print(output)

try:
    with open(target_file, "a") as f:
        f.write(output)
    print(f"Verification written to {target_file}")
except Exception as e:
    print(f"Failed to write verification: {e}")
"""

def main():
    print(f"Deploying Job to {SERVER_URL}")
    try:
        sig = sign_content(JOB_SCRIPT)
    except Exception as e:
        print(f"Signing Error: {e}")
        return

    payload = {
        "task_type": "python_script",
        "payload": {
            "script_content": JOB_SCRIPT,
            "signature": sig,
            "secrets": {} 
        }
    }
    
    headers = {"X-API-KEY": API_KEY}
    
    try:
        resp = requests.post(f"{SERVER_URL}/jobs", json=payload, headers=headers, verify=False)
        print(f"Status: {resp.status_code}")
        print(resp.text)
    except Exception as e:
        print(f"Network Error: {e}")

if __name__ == "__main__":
    main()
