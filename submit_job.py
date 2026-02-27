import httpx
import json
import base64
from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography.hazmat.primitives import serialization
import os

AGENT_URL = "https://localhost:8001"
SIGNING_KEY_PATH = "secrets/signing.key"

def submit_job():
    # 1. Load Signing Key
    if not os.path.exists(SIGNING_KEY_PATH):
        print(f"❌ Signing key not found at {SIGNING_KEY_PATH}")
        return

    with open(SIGNING_KEY_PATH, "rb") as f:
        key_bytes = f.read()
        signing_key = serialization.load_pem_private_key(key_bytes, password=None)

    # 2. Define Script Content
    script_content = """
import platform
import os
print("--- Job Execution Report ---")
print(f"Node: {platform.node()}")
print(f"Platform: {platform.system()} {platform.release()}")
print(f"Current Directory: {os.getcwd()}")
print("Success: Phase 4 Validation Complete.")
"""

    # 3. Sign Content
    signature = signing_key.sign(script_content.encode('utf-8'))
    signature_b64 = base64.b64encode(signature).decode('utf-8')

    # 4. Prepare Payload
    payload = {
        "script_content": script_content,
        "signature": signature_b64,
        "secrets": {}
    }

    job_data = {
        "task_type": "python_script",
        "payload": payload,
        "target_tags": ["speedy"] # Enrolled node has 'speedy' tag from earlier logs
    }

    # 5. Submit to Agent
    print(f"🚀 Submitting Job to {AGENT_URL}...")
    try:
        with httpx.Client(verify=False) as client:
            resp = client.post(f"{AGENT_URL}/jobs", json=job_data)
            if resp.status_code == 200:
                print(f"✅ Job Created: {resp.json().get('guid')}")
            else:
                print(f"❌ Failed to create job: {resp.status_code} - {resp.text}")
    except Exception as e:
        print(f"❌ Error submitting job: {e}")

if __name__ == "__main__":
    submit_job()
