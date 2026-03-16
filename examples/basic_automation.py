"""
Master of Puppets - Basic Automation Example
This script demonstrates how to use the MOP SDK to trigger a maintenance task 
across all production nodes and wait for the results.
"""

import sys
import os
from mop_sdk import MOPClient

# Configuration (Ideally from Environment Variables)
MOP_URL = os.getenv("MOP_URL", "https://localhost:8001")
API_KEY = os.getenv("MOP_API_KEY", "mop_your_service_principal_key")
SIGNING_KEY = os.getenv("MOP_SIGNING_KEY", "secrets/signing.key")

def run_maintenance():
    # 1. Initialize the client
    # We use a Service Principal for headless automation
    client = MOPClient(base_url=MOP_URL, api_key=API_KEY, verify_ssl=False)

    print(f"🔗 Connected to {MOP_URL}")

    # 2. Define the maintenance script
    cleanup_script = """
import os
import glob

print("🧹 Starting log maintenance...")
log_files = glob.glob('/tmp/*.log')
for f in log_files:
    print(f"Removing {f}")
    # os.remove(f) # Uncomment to actually perform work

print("✅ Maintenance complete.")
"""

    # 3. Submit the job to all 'prod' tagged nodes
    print("🚀 Dispatching cleanup job to [env:prod] nodes...")
    try:
        job = client.submit_python_job(
            script=cleanup_script,
            private_key_path=SIGNING_KEY,
            tags=["env:prod"]
        )
        guid = job['guid']
        print(f"✅ Job Created: {guid}")

        # 4. Wait for completion
        print("⏳ Waiting for execution...")
        result = client.wait_for_job(guid, timeout=120)
        
        print(f"🏁 Final Status: {result['status']}")
        
        if result['status'] == 'COMPLETED':
            print("✨ Maintenance finished successfully.")
        else:
            print("❌ Maintenance failed. Check logs in dashboard.")

    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    if not os.path.exists(SIGNING_KEY):
        print(f"❌ Error: Signing key not found at {SIGNING_KEY}")
        sys.exit(1)
    run_maintenance()
