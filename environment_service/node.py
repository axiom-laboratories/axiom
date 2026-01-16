import asyncio
import httpx
import uuid
import os
import json
import subprocess
import socket
import base64
import threading
import psutil
import time
from typing import Optional, Dict, List
from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography.hazmat.primitives import serialization

from dotenv import load_dotenv

load_dotenv()

AGENT_URL = os.getenv("AGENT_URL", "https://localhost:8001")
API_KEY_NAME = "X-API-KEY"
API_KEY = os.getenv("API_KEY", "master-secret-key")
JOIN_TOKEN = os.getenv("JOIN_TOKEN") 
NODE_ID = f"node-{uuid.uuid4().hex[:8]}"
ROOT_CA_PATH = os.getenv("ROOT_CA_PATH", "c:/Development/Repos/master_of_puppets/ca/certs/root_ca.crt")

# Verify SSL?
VERIFY_SSL = str(ROOT_CA_PATH) if ROOT_CA_PATH and os.path.exists(ROOT_CA_PATH) else False

def heartbeat_loop():
    """
    Background thread to send telemetry to Agent.
    """
    print(f"[{NODE_ID}] 💓 Heartbeat Thread Started")
    # Separate client for thread safety
    with httpx.Client(verify=VERIFY_SSL, headers={API_KEY_NAME: API_KEY}) as client:
        while True:
            try:
                stats = {
                    "cpu": psutil.cpu_percent(interval=None),
                    "ram": psutil.virtual_memory().percent
                }
                # Use X-Node-ID header if we have one, or just let server use IP
                # We send NODE_ID to allow detailed tracking
                client.post(
                    f"{AGENT_URL}/heartbeat", 
                    json=stats, 
                    headers={"X-Node-ID": NODE_ID},
                    timeout=5.0
                )
            except Exception as e:
                print(f"[Heartbeat] Failed: {e}")
            
            time.sleep(30)

class Node:
    def __init__(self, agent_url: str, node_id: str):
        self.agent_url = agent_url
        self.node_id = node_id
        self.cert_file = f"secrets/{self.node_id}.crt"
        self.key_file = f"secrets/{self.node_id}.key"
        self.verify_key_path = "secrets/verification.key"
        os.makedirs("secrets", exist_ok=True)

    async def poll_for_work(self) -> Optional[Dict]:
        try:
            async with httpx.AsyncClient(verify=VERIFY_SSL, headers={API_KEY_NAME: API_KEY}) as client:
                resp = await client.post(f"{self.agent_url}/work/pull", timeout=10.0)
                if resp.status_code == 200:
                    data = resp.json()
                    if data:
                        return data 
                elif resp.status_code != 200:
                     # Only log errors
                     pass
        except Exception as e:
            print(f"[{self.node_id}] Error polling Agent: {e}")
        return None

    def run_python_script(self, guid: str, script_content: str, secrets: Dict = {}) -> Dict:
        temp_filename = f"_temp_job_{guid}.py"
        try:
            with open(temp_filename, "w") as f:
                f.write(script_content)
                
            env_vars = os.environ.copy()
            env_vars.update(secrets)
            
            print(f"[{self.node_id}] Spawning subprocess for job {guid}...")
            result = subprocess.run(
                ["python", temp_filename],
                env=env_vars,
                capture_output=True,
                text=True,
                timeout=30 
            )
            
            return {
                "exit_code": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr
            }
            
        except subprocess.TimeoutExpired:
            return {"error": "Execution timed out"}
        except Exception as e:
            return {"error": f"Execution failed: {e}"}
        finally:
            if os.path.exists(temp_filename):
                os.remove(temp_filename)

    async def execute_task(self, job: Dict):
        guid = job["guid"]
        task_type = job.get("task_type", "web_task")
        payload = job["payload"]
        
        print(f"[{self.node_id}] Executing Job {guid} [{task_type}]")
        
        result_data = {}
        success = False

        if task_type == "python_script":
            script = payload.get("script_content")
            secrets = payload.get("secrets", {})
            signature = payload.get("signature")

            if not script:
                 result_data = {"error": "No script_content provided"}
            else:
                 # Check Signature (Simplified logic for now, similar to before)
                 if os.path.exists(self.verify_key_path) and signature:
                     # ... verify logic ...
                     pass
                 
                 exec_result = self.run_python_script(guid, script, secrets)
                 result_data = exec_result
                 success = (exec_result.get("exit_code") == 0)
                
        else:
            print(f"[{self.node_id}] Simulating Web Task")
            await asyncio.sleep(2)
            success = True
            result_data = {"processed": True}
        
        await self.report_result(guid, success, result_data)

    async def report_result(self, guid: str, success: bool, result: Dict):
        try:
            async with httpx.AsyncClient(verify=VERIFY_SSL, headers={API_KEY_NAME: API_KEY}) as client:
                await client.post(
                    f"{self.agent_url}/work/{guid}/result",
                    json={"success": success, "result": result}
                )
            print(f"[{self.node_id}] Reported result for {guid}")
        except Exception as e:
            print(f"[{self.node_id}] Failed to report result: {e}")

    async def start(self):
        print(f"[{self.node_id}] Starting Work Loop...")
        while True:
            job = await self.poll_for_work()
            if job:
                await self.execute_task(job)
            else:
                await asyncio.sleep(5)

def main():
    print(f"🚀 Environment Node Started ({os.getpid()})")
    
    if not VERIFY_SSL:
        print("⚠️  WARNING: Running with SSL Verification DISABLED")

    # Start Heartbeat Thread
    hb_thread = threading.Thread(target=heartbeat_loop, daemon=True)
    hb_thread.start()

    node = Node(AGENT_URL, NODE_ID)
    try:
        asyncio.run(node.start())
    except KeyboardInterrupt:
        print("Node stopping...")

if __name__ == "__main__":
    main()
