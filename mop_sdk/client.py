import httpx
import json
import logging
import base64
import time
import os
from typing import List, Dict, Optional, Any
from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography.hazmat.primitives import serialization

logger = logging.getLogger("mop_sdk")

class MOPClient:
    def __init__(
        self, 
        base_url: str, 
        api_key: Optional[str] = None, 
        username: Optional[str] = None, 
        password: Optional[str] = None,
        verify_ssl: bool = True
    ):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.username = username
        self.password = password
        self.verify_ssl = verify_ssl
        self.token: Optional[str] = None
        self._client = httpx.Client(verify=self.verify_ssl)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._client.close()

    def _get_headers(self) -> Dict[str, str]:
        headers = {}
        if self.api_key:
            headers["X-API-Key"] = self.api_key
        elif self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        return headers

    def _authenticate(self):
        """Handles JWT login if username/password are provided."""
        if not self.username or not self.password:
            return

        resp = self._client.post(
            f"{self.base_url}/auth/login",
            data={"username": self.username, "password": self.password}
        )
        if resp.status_code == 200:
            self.token = resp.json().get("access_token")
            logger.info("Successfully authenticated with JWT")
        else:
            raise Exception(f"Authentication failed: {resp.status_code} - {resp.text}")

    def request(self, method: str, endpoint: str, **kwargs) -> httpx.Response:
        """Central request wrapper with auto-auth and header management."""
        if not self.api_key and not self.token:
            self._authenticate()

        url = f"{self.base_url}{endpoint}"
        headers = {**self._get_headers(), **kwargs.pop("headers", {})}
        
        resp = self._client.request(method, url, headers=headers, **kwargs)
        
        # Auto-retry once on 401 if using JWT
        if resp.status_code == 401 and self.username and self.password:
            self._authenticate()
            headers = {**self._get_headers(), **kwargs.pop("headers", {})}
            resp = self._client.request(method, url, headers=headers, **kwargs)
            
        return resp

    # --- Resource Methods ---

    def list_jobs(self, skip: int = 0, limit: int = 50, status: Optional[str] = None) -> List[Dict]:
        """Lists jobs with optional filtering."""
        params = {"skip": skip, "limit": limit}
        if status:
            params["status"] = status
        
        resp = self.request("GET", "/jobs", params=params)
        resp.raise_for_status()
        return resp.json()

    def list_job_definitions(self) -> List[Dict]:
        """Lists all job definitions."""
        resp = self.request("GET", "/jobs/definitions")
        resp.raise_for_status()
        return resp.json()

    def get_job_definition(self, id: str) -> Dict:
        """Retrieves a single job definition."""
        resp = self.request("GET", f"/jobs/definitions/{id}")
        resp.raise_for_status()
        return resp.json()

    def push_job(
        self,
        script_content: str,
        signature: str,
        signature_id: str,
        name: Optional[str] = None,
        id: Optional[str] = None
    ) -> Dict:
        """Pushes a job definition (DRAFT) to the backend."""
        payload = {
            "script_content": script_content,
            "signature": signature,
            "signature_id": signature_id
        }
        if name:
            payload["name"] = name
        if id:
            payload["id"] = id
            
        resp = self.request("POST", "/api/jobs/push", json=payload)
        resp.raise_for_status()
        return resp.json()

    def create_job_definition(
        self,
        name: str,
        script_content: str,
        signature: str,
        signature_id: str,
        schedule_cron: Optional[str] = None,
        target_node_id: Optional[str] = None,
        target_tags: Optional[List[str]] = None
    ) -> Dict:
        """Creates a fully-scheduled ACTIVE job definition."""
        payload = {
            "name": name,
            "script_content": script_content,
            "signature": signature,
            "signature_id": signature_id,
            "schedule_cron": schedule_cron,
            "target_node_id": target_node_id,
            "target_tags": target_tags,
            "is_active": True
        }
        resp = self.request("POST", "/jobs/definitions", json=payload)
        resp.raise_for_status()
        return resp.json()

    @classmethod
    def from_store(cls, store: Optional[Any] = None, verify_ssl: bool = True):
        """Initializes MOPClient from CredentialStore."""
        if store is None:
            from .auth import CredentialStore
            store = CredentialStore()
        
        creds = store.load()
        if not creds:
            raise Exception("Not logged in. Run 'mop-push login' first.")
        
        client = cls(base_url=creds["base_url"], verify_ssl=verify_ssl)
        client.token = creds["access_token"]
        return client

    def get_job(self, guid: str) -> Dict:
        """Retrieves details for a specific job."""
        # Note: We might need a specific detail endpoint if /jobs doesn't return full payload
        resp = self.request("GET", f"/jobs") # Filtering logic usually handled by params in existing main.py
        resp.raise_for_status()
        jobs = resp.json()
        for j in jobs:
            if j['guid'] == guid:
                return j
        raise Exception(f"Job {guid} not found")

    def list_nodes(self) -> List[Dict]:
        """Lists all registered nodes."""
        resp = self.request("GET", "/nodes")
        resp.raise_for_status()
        return resp.json()

    def fire_signal(self, name: str, payload: Optional[Dict] = None) -> Dict:
        """Fires a reactive orchestration signal."""
        resp = self.request("POST", f"/api/signals/{name}", json={"payload": payload})
        resp.raise_for_status()
        return resp.json()

    def fire_trigger(self, slug: str, trigger_key: str, payload: Optional[Dict] = None) -> Dict:
        """Fires a headless automation trigger using its dedicated key."""
        headers = {"X-MOP-Trigger-Key": trigger_key}
        url = f"{self.base_url}/api/trigger/{slug}"
        resp = self._client.post(url, json=payload or {}, headers=headers)
        resp.raise_for_status()
        return resp.json()

    # --- Advanced Orchestration ---

    def submit_python_job(
        self, 
        script: str, 
        private_key_path: str, 
        name: str = "SDK Job", 
        tags: Optional[List[str]] = None,
        memory_limit: Optional[str] = None
    ) -> Dict:
        """Signs and submits a python_script job."""
        if not os.path.exists(private_key_path):
            raise FileNotFoundError(f"Signing key not found: {private_key_path}")

        # 1. Sign Script
        with open(private_key_path, "rb") as f:
            key_bytes = f.read()
            private_key = serialization.load_pem_private_key(key_bytes, password=None)
        
        if not isinstance(private_key, ed25519.Ed25519PrivateKey):
            raise TypeError("Only Ed25519 keys are supported for job signing")

        signature = private_key.sign(script.encode('utf-8'))
        signature_b64 = base64.b64encode(signature).decode('utf-8')

        # 2. Build Payload
        job_data = {
            "task_type": "python_script",
            "payload": {
                "script": script,
                "signature": signature_b64
            },
            "target_tags": tags,
            "memory_limit": memory_limit
        }

        resp = self.request("POST", "/jobs", json=job_data)
        resp.raise_for_status()
        return resp.json()

    def wait_for_job(self, guid: str, timeout: int = 300, interval: int = 5) -> Dict:
        """Polls for job completion with a timeout."""
        start_time = time.time()
        logger.info(f"Waiting for job {guid} to complete...")

        while (time.time() - start_time) < timeout:
            job = self.get_job(guid)
            status = job.get("status", "").upper()
            
            if status in ["COMPLETED", "FAILED", "CANCELLED", "DEAD_LETTER", "SECURITY_REJECTED"]:
                logger.info(f"Job {guid} reached terminal state: {status}")
                return job
            
            time.sleep(interval)

        raise TimeoutError(f"Job {guid} did not complete within {timeout} seconds")
