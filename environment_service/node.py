import asyncio
import httpx
import uuid
import os
import json
import os
import json
import subprocess
from typing import Optional, Dict

AGENT_URL = os.getenv("AGENT_URL", "https://localhost:8001")
API_KEY = "master-secret-key"
NODE_ID = f"node-{uuid.uuid4().hex[:8]}"

class Node:
    def __init__(self, agent_url: str, node_id: str):
        self.agent_url = agent_url
        self.node_id = node_id
        self.node_id = node_id
        self.running = False
        self.cert_file = f"{self.node_id}.crt"
        self.key_file = f"{self.node_id}.key"
        self.root_ca = "c:/Development/Repos/master_of_puppets/ca/certs/root_ca.crt" # Hardcoded for now

    async def bootstrap_acme(self):
        if os.path.exists(self.cert_file) and os.path.exists(self.key_file):
            print(f"[{self.node_id}] Certs found. Skipping enrollment.")
            return

        print(f"[{self.node_id}] Bootstrapping ACME...")
        
        # 1. Get Enrollment Token from Agent
        # Note: We use verify=False here because Agent uses self-signed (or we can use root_ca if agent reused it).
        # But Agent is currently using 'certs/cert.pem' (self-signed). 
        # So we trust it blindly for bootstrapping.
        try:
            async with httpx.AsyncClient(verify=False) as client:
                resp = await client.post(
                    f"{self.agent_url}/auth/register",
                    json={"client_secret": "enrollment-secret", "hostname": self.node_id} # hostname=node_id
                )
                resp.raise_for_status()
                data = resp.json()
                
                token = data["enrollment_token"]
                ca_url = data["ca_url"]
                fingerprint = data["fingerprint"]
                
                print(f"[{self.node_id}] Obtained enrollment token.")
                
                # 2. Generate Certs using step-cli
                STEP_EXE = r"C:\Users\thoma\AppData\Local\Microsoft\WinGet\Packages\Smallstep.step_Microsoft.Winget.Source_8wekyb3d8bbwe\step_0.28.7\bin\step.exe"
                cmd = [
                    STEP_EXE, "ca", "certificate",
                    self.node_id, self.cert_file, self.key_file,
                    "--token", token,
                    "--ca-url", ca_url,
                    "--root", self.root_ca
                ]
                
                subprocess.run(cmd, check=True)
                print(f"[{self.node_id}] Certificate enrollment successful!")
                
        except Exception as e:
            print(f"[{self.node_id}] Enrollment failed: {e}")
            raise

    async def poll_for_work(self) -> Optional[Dict]:
        try:
            # Authenticate with mTLS (Certificate) + API Key (for App Layer Auth)
            # CAUTION: 'verify=self.root_ca' ensures we trust the server if it uses a cert signed by our CA.
            # But currently Agent uses 'certs/cert.pem' (Self-Signed).
            # To make mTLS work, Agent MUST use a cert signed by our CA.
            # For now, we continue to use key auth, but we try to present certs if strictly needed.
            # Updated: verify=False for now until Agent uses CA certs.
            async with httpx.AsyncClient(verify=False, cert=(self.cert_file, self.key_file)) as client:
                resp = await client.post(f"{self.agent_url}/work/pull", headers={"X-API-KEY": API_KEY})
                if resp.status_code == 200:
                    data = resp.json()
                    if data:
                        return data # {"guid": "...", "payload": {...}}
        except Exception as e:
            print(f"[{self.node_id}] Error polling Agent: {e}")
        return None

    async def execute_task(self, job: Dict):
        guid = job["guid"]
        payload = job["payload"]
        print(f"[{self.node_id}] Executing Job {guid} - Payload: {payload}")
        
        # Simulate work
        await asyncio.sleep(2)
        
        # Result
        success = True
        result_data = {"processed": True, "details": "Task complete"}
        
        await self.report_result(guid, success, result_data)

    async def report_result(self, guid: str, success: bool, result: Dict):
        try:
            async with httpx.AsyncClient(verify=False, cert=(self.cert_file, self.key_file)) as client:
                await client.post(
                    f"{self.agent_url}/work/{guid}/result",
                    json={"success": success, "result": result},
                    headers={"X-API-KEY": API_KEY}
                )
            print(f"[{self.node_id}] Reported result for {guid}")
        except Exception as e:
            print(f"[{self.node_id}] Failed to report result: {e}")

    async def start(self):
        await self.bootstrap_acme()
        print(f"[{self.node_id}] Starting Node Loop...")
        self.running = True
        while self.running:
            job = await self.poll_for_work()
            if job:
                await self.execute_task(job)
            else:
                # Backoff
                await asyncio.sleep(5)

if __name__ == "__main__":
    node = Node(AGENT_URL, NODE_ID)
    try:
        asyncio.run(node.start())
    except KeyboardInterrupt:
        print("Node stopping...")
