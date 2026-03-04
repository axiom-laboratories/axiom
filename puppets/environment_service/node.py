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
from cryptography.hazmat.primitives.asymmetric import ed25519, rsa
from cryptography.hazmat.primitives import serialization, hashes
from cryptography import x509
from cryptography.x509.oid import NameOID
from aiohttp import web
import runtime

from dotenv import load_dotenv


def parse_bytes(s: str) -> int:
    """Convert memory string like '300m', '2g', '1024k' to bytes."""
    s = s.strip().lower()
    if s.endswith('g'):
        return int(s[:-1]) * 1024 ** 3
    elif s.endswith('m'):
        return int(s[:-1]) * 1024 ** 2
    elif s.endswith('k'):
        return int(s[:-1]) * 1024
    return int(s)

load_dotenv()

AGENT_URL = os.getenv("AGENT_URL", "https://localhost:8001")
API_KEY_NAME = "X-API-KEY"
API_KEY = os.getenv("API_KEY", "master-secret-key")
JOIN_TOKEN = os.getenv("JOIN_TOKEN") 
def _load_or_generate_node_id() -> str:
    """Reuse an existing enrolled identity if present, otherwise generate a fresh one."""
    os.makedirs("secrets", exist_ok=True)
    existing = sorted(f[:-4] for f in os.listdir("secrets") if f.endswith(".crt") and f.startswith("node-"))
    return existing[0] if existing else f"node-{uuid.uuid4().hex[:8]}"

NODE_ID = _load_or_generate_node_id()
ROOT_CA_PATH = os.getenv("ROOT_CA_PATH", "c:/Development/Repos/master_of_puppets/ca/certs/root_ca.crt")
CERT_FILE = f"secrets/{NODE_ID}.crt"
KEY_FILE = f"secrets/{NODE_ID}.key"
NODE_SECRET_PATH = os.getenv("NODE_SECRET_PATH", "/run/secrets/node_secret")
HOST_ID_PATH = os.getenv("HOST_ID_PATH", "/run/secrets/host_id")

import urllib3
urllib3.disable_warnings()

# Verify SSL?
VERIFY_SSL = os.getenv("VERIFY_SSL", "true").lower() == "true"
if VERIFY_SSL:
    VERIFY_SSL = str(ROOT_CA_PATH) if ROOT_CA_PATH and os.path.exists(ROOT_CA_PATH) else False
else:
    VERIFY_SSL = False

def get_machine_id() -> str:
    """Reads the host's unique machine-id."""
    paths = [HOST_ID_PATH, "/etc/machine-id", "/var/lib/dbus/machine-id"]
    for p in paths:
        if os.path.exists(p):
            try:
                with open(p, "r") as f:
                    return f.read().strip()
            except:
                pass
    return "unknown-host"

def get_node_secret_hash() -> str:
    """Reads the host-bound secret and returns its SHA256 hash."""
    if os.path.exists(NODE_SECRET_PATH):
        try:
            with open(NODE_SECRET_PATH, "r") as f:
                secret = f.read().strip()
                h = hashes.Hash(hashes.SHA256())
                h.update(secret.encode())
                return h.finalize().hex()
        except:
            pass
    return ""

def get_capabilities() -> Dict[str, str]:
    """Gather environment capabilities (tool versions)."""
    caps = {}
    try:
        # Python
        caps["python"] = f"{socket.sys.version_info.major}.{socket.sys.version_info.minor}.{socket.sys.version_info.micro}"
        
        # PowerShell
        try:
            res = subprocess.run(["pwsh", "-Version"], capture_output=True, text=True)
            if res.returncode == 0:
                caps["powershell"] = res.stdout.strip().split()[-1]
        except:
            pass

        # Podman/Docker
        try:
            res = subprocess.run(["podman", "--version"], capture_output=True, text=True)
            if res.returncode == 0:
                caps["podman"] = res.stdout.strip().split()[-1]
        except:
            try:
                res = subprocess.run(["docker", "--version"], capture_output=True, text=True)
                if res.returncode == 0:
                    caps["docker"] = res.stdout.strip().split()[-1]
            except:
                pass
    except Exception as e:
        print(f"[Capabilities] Error gathering: {e}")
    return caps

def heartbeat_loop():
    """
    Background thread to send telemetry to Agent.
    """
    print(f"[{NODE_ID}] 💓 Heartbeat Thread Started")
    # Separate client for thread safety
    # Wait for certs to exist (Node init does this)
    while not os.path.exists(CERT_FILE):
        time.sleep(1)
        
    with httpx.Client(
        verify=VERIFY_SSL, 
        cert=(CERT_FILE, KEY_FILE)
    ) as client:
        while True:
            try:
                stats = {
                    "cpu": psutil.cpu_percent(interval=None),
                    "ram": psutil.virtual_memory().percent
                }
                tags_str = os.getenv("NODE_TAGS", "")
                tags = [t.strip() for t in tags_str.split(",") if t.strip()]
                
                caps = get_capabilities()
                secret_hash = get_node_secret_hash()

                payload = {
                    "node_id": NODE_ID,
                    "hostname": socket.gethostname(),
                    "stats": stats,
                    "tags": tags,
                    "capabilities": caps
                }

                # Use X-Node-ID header if we have one, or just let server use IP
                # We send NODE_ID to allow detailed tracking
                headers = {
                    "X-Node-ID": NODE_ID, 
                    API_KEY_NAME: API_KEY,
                    "X-Node-Secret-Hash": secret_hash,
                    "X-Machine-ID": get_machine_id()
                }
                
                client.post(
                    f"{AGENT_URL}/heartbeat", 
                    json=payload, 
                    headers=headers,
                    timeout=5.0
                )
            except Exception as e:
                print(f"[Heartbeat] Failed: {e}")
            
            time.sleep(30)

class Node:
    def __init__(self, agent_url: str, node_id: str):
        self.agent_url = agent_url
        self.node_id = node_id
        self.join_token = JOIN_TOKEN
        self.cert_file = CERT_FILE
        self.key_file = KEY_FILE
        self.verify_key_path = "secrets/verification.key"
        self.concurrency_limit = 5
        self.job_memory_limit = os.getenv("JOB_MEMORY_LIMIT", "512m")
        self.job_cpu_limit = os.getenv("JOB_CPU_LIMIT")
        self.active_tasks = set()
        self.runtime_engine = runtime.ContainerRuntime()
        os.makedirs("secrets", exist_ok=True)
        
        # Self-Bootstrap Trust from Token (Container-Native)
        self.bootstrap_trust()
        
        # Ensure we have a valid identity (Key + Cert)
        self.ensure_identity()
        
    def bootstrap_trust(self):
        """
        Parses JOIN_TOKEN. If it's an Enhanced Token (JSON), extracts the CA
        and saves it to disk, bypassing the need for host-to-container mounts.
        """
        try:
            # Sanitize token string (remove whitespace/newlines that might creep in via env/yaml)
            top_token = self.join_token.strip()
            print(f"[{self.node_id}] Debug: Checking Token: {top_token[:20]}...")
            
            # Check if it looks like Base64 (Enhanced Token)
            decoded_bytes = base64.b64decode(top_token)
            decoded_str = decoded_bytes.decode('utf-8')
            # strict=False allows control characters like newlines inside strings if they appear
            payload = json.loads(decoded_str, strict=False)
            
            if "t" in payload and "ca" in payload:
                print(f"[{self.node_id}] 📜 Detected Enhanced Token. Bootstrapping Trust...")
                
                # 1. Extract and Save CA
                ca_content = payload["ca"]
                # Ensure it ends with newline
                if not ca_content.endswith("\n"):
                    ca_content += "\n"
                    
                root_ca_dest = "secrets/root_ca.crt"
                with open(root_ca_dest, "w") as f:
                    f.write(ca_content)
                
                # Update Globals/Members
                global ROOT_CA_PATH, VERIFY_SSL
                ROOT_CA_PATH = os.path.abspath(root_ca_dest)
                
                # STRICT mTLS: Always verify against Bootstrap CA (unless explicitly disabled)
                if str(os.getenv("VERIFY_SSL")).lower() != "false":
                    VERIFY_SSL = ROOT_CA_PATH
                print(f"[{self.node_id}] 🔒 Strict mTLS Active. CA: {ROOT_CA_PATH} (Verify={VERIFY_SSL})")
                
                # 2. Extract Real Token
                self.join_token = payload["t"]
                
                print(f"[{self.node_id}] ✅ Trust Bootstrapped to {ROOT_CA_PATH}")
            else:
                 print(f"[{self.node_id}] Token payload missing 't' or 'ca'")
                 
            # 3. Fetch Verification Key (Public Key) for Code Signing
            self.fetch_verification_key()
                 
        except Exception as e:
            # Not an enhanced token or parsing failed. safely ignore.
            print(f"[{self.node_id}] DEBUG: Token parse failed, assuming legacy/simple token: {e}")
            pass
            
    def fetch_verification_key(self):
        """Fetches the Public Verification Key from the Server."""
        try:
            # We can use the generic client (trusting Root CA)
            with httpx.Client(verify=VERIFY_SSL) as client:
                resp = client.get(f"{self.agent_url}/verification-key", timeout=10)
                if resp.status_code == 200:
                    with open(self.verify_key_path, "wb") as f:
                        f.write(resp.content)
                    print(f"[{self.node_id}] 🔑 Verification Key updated.")
                else:
                    print(f"[{self.node_id}] ⚠️ Failed to fetch Verification Key: {resp.status_code}")
        except Exception as e:
             print(f"[{self.node_id}] ⚠️ Error fetching Verification Key: {e}")
        
    def ensure_identity(self):
        """Checks for Client Cert/Key. If missing, registers with Server via CSR."""
        if os.path.exists(self.cert_file) and os.path.exists(self.key_file):
            print(f"[{self.node_id}] Identity loaded: {self.cert_file}")
            return

        print(f"[{self.node_id}] No identity found. Enrolling with Server...")
        
        # 1. Generate Private Key (RSA 2048)
        key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        
        # 2. Generate CSR
        csr = x509.CertificateSigningRequestBuilder().subject_name(x509.Name([
            x509.NameAttribute(NameOID.COMMON_NAME, self.node_id),
        ])).sign(key, hashes.SHA256())
        
        csr_pem = csr.public_bytes(serialization.Encoding.PEM).decode()
        
        # 3. Register with Server (Exchange Token + CSR for Cert)
        try:
             # Use a generic client for registration (Verification CA trusted)
             with httpx.Client(verify=VERIFY_SSL) as client:
                 secret_hash = get_node_secret_hash()
                 payload = {
                     "token": self.join_token,
                     "hostname": self.node_id,
                     "csr_pem": csr_pem,
                     "machine_id": get_machine_id(),
                     "node_secret_hash": secret_hash
                 }
                 resp = client.post(f"{self.agent_url}/api/enroll", json=payload)
                 resp.raise_for_status()
                 data = resp.json()
                 
                 client_cert_pem = data["client_cert_pem"]
                 
                 # 4. Save to Disk
                 with open(self.key_file, "wb") as f:
                     f.write(key.private_bytes(
                         encoding=serialization.Encoding.PEM,
                         format=serialization.PrivateFormat.TraditionalOpenSSL,
                         encryption_algorithm=serialization.NoEncryption()
                     ))
                 with open(self.cert_file, "w") as f:
                     f.write(client_cert_pem)
                     
                 print(f"[{self.node_id}] ✅ Enrollment Successful! Certificate Saved.")
                 
        except Exception as e:
            print(f"[{self.node_id}] ❌ Enrollment Failed: {e}")
            raise e

    async def poll_for_work(self) -> Optional[Dict]:
        try:
            # mTLS Client
            async with httpx.AsyncClient(
                verify=VERIFY_SSL, 
                cert=(self.cert_file, self.key_file)
            ) as client:
                secret_hash = get_node_secret_hash()
                headers = {
                    API_KEY_NAME: API_KEY, 
                    "X-Node-ID": self.node_id,
                    "X-Node-Secret-Hash": secret_hash,
                    "X-Machine-ID": get_machine_id()
                }
                resp = await client.post(f"{self.agent_url}/work/pull", headers=headers, timeout=10.0)
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
        payload = job.get("payload", {})
        memory_limit = job.get("memory_limit")
        cpu_limit = job.get("cpu_limit")

        print(f"[{self.node_id}] Executing Job {guid} [{task_type}]")

        # Secondary admission check
        if memory_limit and self.job_memory_limit:
            try:
                if parse_bytes(memory_limit) > parse_bytes(self.job_memory_limit):
                    print(f"[{self.node_id}] Job {guid} requests {memory_limit}, node limit is {self.job_memory_limit} — skipping")
                    await self.report_result(guid, False, {"error": "Job memory limit exceeds node capacity"})
                    return
            except Exception:
                pass
        
        if task_type == "python_script":
            script = payload.get("script_content")
            secrets = payload.get("secrets", {})
            signature = payload.get("signature")
            
            if not script or not signature:
                 await self.report_result(guid, False, {"error": "Missing script or signature"})
                 return
            
            # Verify Signature
            if not os.path.exists(self.verify_key_path):
                 print(f"[{self.node_id}] ❌ CRITICAL: Verification Key missing. Cannot verify signature.")
                 await self.report_result(guid, False, {"error": "Security Check Failed: Verification Key missing"})
                 return
                 
            try:
                with open(self.verify_key_path, "rb") as f:
                     public_key_bytes = f.read()
                     public_key = serialization.load_pem_public_key(public_key_bytes)
                     
                sig_bytes = base64.b64decode(signature)
                public_key.verify(sig_bytes, script.encode('utf-8'))
                print(f"[{self.node_id}] ✅ Signature Verified for Job {guid}")
            except Exception as e:
                print(f"[{self.node_id}] ❌ Signature Verification FAILED for Job {guid}: {e}")
                await self.report_result(guid, False, {"error": "Signature Verification Failed"})
                return
            
            # Prepare Environment
            krb_ccname = os.environ.get("KRB5CCNAME")
            env = {
                "HTTP_PROXY": "http://localhost:8080",
                "HTTPS_PROXY": "http://localhost:8080",
                "MOP_STATUS_API": "http://localhost:8081",
                "KRB5CCNAME": krb_ccname if krb_ccname else ""
            }
            env.update(secrets)
            
            mounts = []
            # Only mount if it's a file path
            if krb_ccname and krb_ccname.startswith("/") and os.path.exists(krb_ccname):
                mounts.append(f"{krb_ccname}:{krb_ccname}:ro")
            
            # Forward Network Mounts
            for k, v in os.environ.items():
                if k.startswith("MOUNT_"):
                    env[k] = v # Pass Config to Job
                    if os.path.exists(v):
                         mounts.append(f"{v}:{v}")
            
            # Detect Hostname (Container ID) for Sidecar Networking
            hostname = socket.gethostname() 

            try:
                # Use python - to read from stdin
                # Assuming same image for now or configurable
                default_img = "python:3.12-alpine" if os.name == 'nt' else "localhost/master-of-puppets-node:latest"
                image = os.getenv("JOB_IMAGE", default_img)
                
                result = await self.runtime_engine.run(
                   image=image,
                   command=["python", "-"],
                   env=env,
                   mounts=mounts,
                   network_ref=hostname,
                   input_data=script,
                   memory_limit=memory_limit,
                   cpu_limit=cpu_limit,
                )
                
                success = (result["exit_code"] == 0)
                
                runtime_report = {
                    "exit_code": result["exit_code"],
                    "stdout": result["stdout"],
                    "stderr": result["stderr"]
                }
                
                # Check if Sidecar already handled it? 
                # We can't easily know in this stateless flow without global tracking.
                # However, reporting again is usually safe if DB handles it (Update WHERE guid=...)
                # We report the container output.
                
                await self.report_result(guid, success, runtime_report)
                
            except Exception as e:
                 print(f"[{self.node_id}] Runtime Execution Failed: {e}")
                 await self.report_result(guid, False, {"error": str(e)})

        else:
             # Web Task (Simulation)
             await asyncio.sleep(2)
             await self.report_result(guid, True, {"processed": True})

    async def report_result(self, guid: str, success: bool, result: Dict):
        try:
            async with httpx.AsyncClient(
                verify=VERIFY_SSL,
                cert=(self.cert_file, self.key_file)
            ) as client:
                secret_hash = get_node_secret_hash()
                await client.post(
                    f"{self.agent_url}/work/{guid}/result",
                    json={"success": success, "result": result},
                    headers={
                        API_KEY_NAME: API_KEY,
                        "X-Node-ID": self.node_id,
                        "X-Node-Secret-Hash": secret_hash,
                        "X-Machine-ID": get_machine_id()
                    }
                )
            print(f"[{self.node_id}] Reported result for {guid}")
        except Exception as e:
            print(f"[{self.node_id}] Failed to report result: {e}")

    async def start_sidecar(self):
        app = web.Application()
        app.add_routes([web.post('/job/status', self.handle_job_status)])
        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, '0.0.0.0', 8081)
        await site.start()
        print(f"[{self.node_id}] Status Sidecar listening on 8081")

    async def handle_job_status(self, request):
        try:
            data = await request.json()
            guid = data.get("guid")
            success = data.get("success", False)
            result = data.get("result", {})
            print(f"[{self.node_id}] Sidecar received report for {guid}: {success}")
            await self.report_result(guid, success, result)
            return web.Response(text="OK")
        except Exception as e:
            print(f"[{self.node_id}] Sidecar Error: {e}")
            return web.Response(status=500)

    async def start(self):
        print(f"[{self.node_id}] Starting Work Loop...")
        try:
            await self.start_sidecar()
        except Exception as e:
            print(f"[{self.node_id}] Failed to start Sidecar: {e}")
            
        while True:
            try:
                # Check Concurrency
                if len(self.active_tasks) >= self.concurrency_limit:
                    await asyncio.sleep(1)
                    continue

                job_data = await self.poll_for_work()
                
                if job_data:
                    config = job_data.get("config", {})
                    if config:
                         self.concurrency_limit = config.get("concurrency_limit", 5)
                    self.job_memory_limit = config.get("job_memory_limit", self.job_memory_limit)

                    work = job_data.get("job")
                    if work:
                        task = asyncio.create_task(self.execute_task(work))
                        self.active_tasks.add(task)
                        task.add_done_callback(self.active_tasks.discard)
                    else:
                        await asyncio.sleep(5) # No work, just heartbeat/config update
                else:
                    await asyncio.sleep(5)
            except Exception as e:
                print(f"[{self.node_id}] Loop Error: {e}")
                await asyncio.sleep(5)

def main():
    print(f"🚀 Environment Node Started ({os.getpid()})")
    
    if not VERIFY_SSL:
        print("⚠️  WARNING: Running with SSL Verification DISABLED")
    else:
        print(f"🔒 Secure Mode Active. Trust Root: {VERIFY_SSL}")

    # Debug: Print Active Mounts
    mounts = [k for k in os.environ.keys() if k.startswith("MOUNT_")]
    if mounts:
        print(f"📁 Active System Mounts: {', '.join(mounts)}")
    else:
        print("📁 No System Mounts detected.")

    node = Node(AGENT_URL, NODE_ID)

    # Start Heartbeat Thread (After Node init ensures certs)
    hb_thread = threading.Thread(target=heartbeat_loop, daemon=True)
    hb_thread.start()

    try:
        asyncio.run(node.start())
    except KeyboardInterrupt:
        print("Node stopping...")

if __name__ == "__main__":
    main()
