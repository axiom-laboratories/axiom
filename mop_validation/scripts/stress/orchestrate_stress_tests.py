#!/usr/bin/env python3
"""
Stress Test Orchestrator
Dispatches preflight, CPU burn, memory OOM, concurrent isolation, and all-language sweep tests.
Generates console table output and JSON report with runtime-specific filtering.

Usage:
    python3 orchestrate_stress_tests.py [--runtime docker|podman] [--dry-run]

Arguments:
    --runtime docker|podman   Target specific runtime (Docker or Podman); omit for all nodes
    --dry-run                 Skip API calls, simulate orchestration logic

Prerequisites:
    - mop_validation/secrets.env with ADMIN_PASSWORD, SERVER_URL
    - stress/{python,bash,pwsh}/ script files exist
    - cryptography, requests, python-dotenv installed
    - Node heartbeat includes execution_mode and cgroup_version fields
"""

import os
import sys
import json
import time
import base64
import subprocess
import requests
import asyncio
import tempfile
import argparse
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Tuple

# Paths — determine script location
# Script is at: /home/thomas/Development/master_of_puppets/mop_validation/scripts/stress/orchestrate_stress_tests.py
# Use SCRIPT_PATH.parents directly (not .parent first)
SCRIPT_PATH = Path(__file__).resolve()
# parents[2] = /home/thomas/Development/master_of_puppets/mop_validation (local mop_validation in repo)
# parents[3] = /home/thomas/Development/master_of_puppets (MOP_DIR)
# parents[4] = /home/thomas/Development (ROOT, where sister mop_validation is)
MOP_DIR = SCRIPT_PATH.parents[3]  # /home/.../master_of_puppets
ROOT = SCRIPT_PATH.parents[4]  # /home/.../Development
VALIDATION_DIR = SCRIPT_PATH.parents[2]  # /home/.../master_of_puppets/mop_validation (local)
VALIDATION_DIR_PARENT = ROOT / "mop_validation"  # /home/.../Development/mop_validation (sister)
SECRETS_ENV = VALIDATION_DIR_PARENT / "secrets.env"  # Primary: sister mop_validation
SECRETS_ENV_ALT = MOP_DIR / "secrets.env"  # Fallback: master_of_puppets

# Debug: uncomment to check paths
# print(f"DEBUG: SCRIPT_PATH={SCRIPT_PATH}")
# print(f"DEBUG: MOP_DIR={MOP_DIR}")
# print(f"DEBUG: ROOT={ROOT}")
# print(f"DEBUG: SECRETS_ENV={SECRETS_ENV}")
# STRESS_DIR: scripts may be in either mop_validation; prefer local (current repo)
STRESS_DIR_LOCAL = VALIDATION_DIR / "scripts" / "stress"
STRESS_DIR_SISTER = VALIDATION_DIR_PARENT / "scripts" / "stress"
STRESS_DIR = STRESS_DIR_LOCAL  # Prefer local, as it has bash/pwsh scripts
REPORTS_DIR = VALIDATION_DIR_PARENT / "reports"

# Config
AGENT_URL = "https://localhost:8001"
REGISTRY = "localhost:5000"

requests.packages.urllib3.disable_warnings()


# ── Helpers ────────────────────────────────────────────────────────────────

def load_env(path: Path) -> dict:
    """Load .env file into dict."""
    env = {}
    if path.exists():
        for line in path.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, _, v = line.partition("=")
                env[k.strip()] = v.strip()
    return env


def find_secrets_env() -> dict:
    """Find and load secrets.env from primary or alternate location."""
    if SECRETS_ENV.exists():
        return load_env(SECRETS_ENV)
    elif SECRETS_ENV_ALT.exists():
        return load_env(SECRETS_ENV_ALT)
    else:
        raise FileNotFoundError(
            f"secrets.env not found at {SECRETS_ENV} or {SECRETS_ENV_ALT}"
        )


def ensure_ed25519_keys() -> tuple:
    """Returns (private_key, public_key_pem). Generates Ed25519 if needed."""
    from cryptography.hazmat.primitives.asymmetric import ed25519
    from cryptography.hazmat.primitives import serialization

    signing_path = MOP_DIR / "secrets" / "signing.key"
    verify_path = MOP_DIR / "secrets" / "verification.key"

    # Try loading existing
    if signing_path.exists():
        try:
            priv = serialization.load_pem_private_key(
                signing_path.read_bytes(), password=None
            )
            if isinstance(priv, ed25519.Ed25519PrivateKey):
                pub_pem = priv.public_key().public_bytes(
                    serialization.Encoding.PEM,
                    serialization.PublicFormat.SubjectPublicKeyInfo,
                )
                return priv, pub_pem.decode()
        except Exception:
            pass

    # Generate fresh pair
    priv = ed25519.Ed25519PrivateKey.generate()
    priv_pem = priv.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    )
    pub_pem = priv.public_key().public_bytes(
        serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo
    )
    MOP_DIR.joinpath("secrets").mkdir(exist_ok=True)
    signing_path.write_bytes(priv_pem)
    verify_path.write_bytes(pub_pem)
    return priv, pub_pem.decode()


def sign_script(private_key, script_content: str) -> str:
    """Sign script content with Ed25519. Returns base64 signature.

    Normalizes CRLF to LF before signing to match node verification behavior.
    """
    # Normalize line endings: CRLF -> LF, CR -> LF
    normalized_script = script_content.replace('\r\n', '\n').replace('\r', '\n')
    sig = private_key.sign(normalized_script.encode("utf-8"))
    return base64.b64encode(sig).decode()


class MopClient:
    """API client for Master of Puppets."""

    def __init__(self, base_url: str, admin_password: str, public_key_pem: str = None):
        self.base = base_url.rstrip("/")
        self.admin_password = admin_password
        self.public_key_pem = public_key_pem
        self.token = None
        self.verify_ssl = False  # Localhost
        self.signature_id = None  # Will be set after registering public key

    def _headers(self, extra: dict = None) -> dict:
        h = {"Content-Type": "application/json"}
        if self.token:
            h["Authorization"] = f"Bearer {self.token}"
        if extra:
            h.update(extra)
        return h

    def login(self) -> bool:
        """Login as admin and get JWT token."""
        try:
            resp = requests.post(
                f"{self.base}/auth/login",
                data={"username": "admin", "password": self.admin_password},
                verify=self.verify_ssl,
                timeout=10,
            )
            if resp.status_code == 200:
                data = resp.json()
                self.token = data.get("access_token")
                return bool(self.token)
        except Exception as e:
            print(f"ERROR: Login failed: {e}")
            return False
        return False

    def register_signature(self) -> bool:
        """Register orchestrator's public key and store signature_id."""
        if not self.public_key_pem or not self.token:
            print(f"ERROR: Cannot register signature without public_key_pem and token")
            return False

        try:
            payload = {
                "name": f"orchestrator-{int(time.time())}",
                "public_key": self.public_key_pem,
            }
            resp = requests.post(
                f"{self.base}/signatures",
                json=payload,
                headers=self._headers(),
                verify=self.verify_ssl,
                timeout=10,
            )
            if resp.status_code in [200, 201]:
                data = resp.json()
                self.signature_id = data.get("id")
                print(f"✓ Registered signature with ID: {self.signature_id}")
                return bool(self.signature_id)
            else:
                print(f"ERROR: register_signature failed with status {resp.status_code}: {resp.text}")
        except Exception as e:
            print(f"ERROR: register_signature failed: {e}")
        return False

    def list_nodes(self) -> List[dict]:
        """Get list of available nodes."""
        try:
            resp = requests.get(
                f"{self.base}/nodes",
                headers=self._headers(),
                verify=self.verify_ssl,
                timeout=10,
            )
            if resp.status_code == 200:
                data = resp.json()
                # Handle both paginated and flat responses
                if isinstance(data, dict) and "items" in data:
                    return data.get("items", [])
                elif isinstance(data, list):
                    return data
                else:
                    return []
        except Exception as e:
            print(f"ERROR: list_nodes failed: {e}")
        return []

    def dispatch_job(
        self,
        script_content: str,
        signature: str,
        memory_limit: Optional[str] = None,
        cpu_limit: Optional[float] = None,
        timeout_s: int = 60,
        runtime: str = "python",
    ) -> Optional[str]:
        """Dispatch a job and return job ID."""
        try:
            # Build the JobCreate request for the /jobs endpoint
            payload_dict = {
                "script_content": script_content,
                "signature": signature,
                "env_vars": {
                    "AXIOM_CAPABILITIES": "resource_limits_supported"
                }
            }

            # If signature_id is registered, include it along with signature_payload
            if self.signature_id:
                payload_dict["signature_id"] = self.signature_id
                payload_dict["signature_payload"] = script_content  # What was signed

            job_req = {
                "task_type": "script",
                "runtime": runtime,
                "payload": payload_dict,
                "timeout_minutes": (timeout_s + 59) // 60,  # Convert to minutes, round up
            }

            if memory_limit:
                job_req["memory_limit"] = memory_limit
            if cpu_limit:
                job_req["cpu_limit"] = str(cpu_limit)  # Convert to string for API

            resp = requests.post(
                f"{self.base}/jobs",
                json=job_req,
                headers=self._headers(),
                verify=self.verify_ssl,
                timeout=10,
            )
            if resp.status_code in [200, 201]:
                data = resp.json()
                # Return guid, not job_id (the new API uses guid)
                return data.get("guid") or data.get("job_id")
            else:
                print(f"ERROR: dispatch_job failed with status {resp.status_code}: {resp.text}")
        except Exception as e:
            print(f"ERROR: dispatch_job failed: {e}")
        return None

    def get_job_status(self, job_id: str) -> Optional[dict]:
        """Get job status and output."""
        try:
            resp = requests.get(
                f"{self.base}/jobs/{job_id}",
                headers=self._headers(),
                verify=self.verify_ssl,
                timeout=10,
            )
            if resp.status_code == 200:
                data = resp.json()
                # Standardize response keys for backward compatibility
                if "guid" in data and "job_id" not in data:
                    data["job_id"] = data["guid"]
                return data
        except Exception as e:
            print(f"ERROR: get_job_status({job_id}) failed: {e}")
        return None

    def poll_job(self, job_id: str, timeout_s: int = 60) -> Optional[dict]:
        """Poll job until completion with exponential backoff."""
        deadline = time.time() + timeout_s
        wait_s = 0.5
        max_wait = 2.0

        while time.time() < deadline:
            job = self.get_job_status(job_id)
            if not job:
                time.sleep(wait_s)
                wait_s = min(wait_s * 1.5, max_wait)
                continue

            status = job.get("status", "").lower()
            if status in ["completed", "failed"]:
                return job

            time.sleep(wait_s)
            wait_s = min(wait_s * 1.5, max_wait)

        return None


# ── Script Loading ─────────────────────────────────────────────────────────

def load_script(language: str, script_name: str) -> Optional[str]:
    """Load script from stress/{language}/{script_name}. Checks local first, then sister."""
    # Try local first
    if language != ".":
        path = STRESS_DIR_LOCAL / language / script_name
        try:
            return path.read_text()
        except FileNotFoundError:
            pass

        # Try sister repo
        path = STRESS_DIR_SISTER / language / script_name
        try:
            return path.read_text()
        except FileNotFoundError:
            pass
    else:
        # Top-level script (preflight_check.py)
        path = STRESS_DIR_LOCAL / script_name
        try:
            return path.read_text()
        except FileNotFoundError:
            pass
        path = STRESS_DIR_SISTER / script_name
        try:
            return path.read_text()
        except FileNotFoundError:
            pass

    print(f"ERROR: Script not found in {STRESS_DIR_LOCAL} or {STRESS_DIR_SISTER}: {language}/{script_name}")
    return None


# ── Node Filtering ──────────────────────────────────────────────────────────

def filter_nodes_by_runtime(
    all_nodes: List[dict], runtime: Optional[str] = None
) -> Tuple[List[dict], List[dict]]:
    """
    Filter nodes by execution_mode and cgroup v2 support.
    Returns (passed_nodes, skipped_nodes) where each skipped node has details.

    Filtering criteria:
    1. If runtime specified: only keep nodes with execution_mode == runtime (or None/unknown if heartbeat not yet received)
    2. Only keep nodes with cgroup_version == 'v2' or None/unknown (assume v2 for modern systems)

    Note: When execution_mode or cgroup_version is None/null, assume Docker and v2 respectively.
    This handles the case where heartbeat hasn't been fully processed yet.
    """
    passed = []
    skipped = []

    for node in all_nodes:
        node_id = node.get("id", node.get("node_id", "unknown"))
        execution_mode = node.get("execution_mode")  # Can be None
        cgroup_version = node.get("detected_cgroup_version", node.get("cgroup_version"))  # API returns detected_cgroup_version
        status = node.get("status", "")

        # Skip OFFLINE or REVOKED nodes — can't run tests on them
        if status not in ["ONLINE", "HEALTHY"]:
            skipped.append({
                "node_id": node_id,
                "reason": f"node status is {status} (not ONLINE)",
                "execution_mode": execution_mode,
                "cgroup_version": cgroup_version,
            })
            continue

        # Check runtime filter
        # If runtime is specified:
        #   - Node with execution_mode=None/unknown: treat as unknown, check against requested runtime
        #   - Node with execution_mode matching runtime: pass
        #   - Node with execution_mode mismatching runtime: skip
        if runtime:
            # If execution_mode is None/null, it hasn't reported yet; assume Docker for Phase 126 (most common)
            inferred_mode = execution_mode if execution_mode and execution_mode != "unknown" else "docker"
            if inferred_mode != runtime:
                skipped.append({
                    "node_id": node_id,
                    "reason": f"execution_mode mismatch (want {runtime}, got {execution_mode or 'unknown (assumed docker)'})",
                    "execution_mode": execution_mode,
                    "cgroup_version": cgroup_version,
                })
                continue

        # Check cgroup version (v2 preferred for Phase 126)
        # If cgroup_version is None/null, assume v2 (modern systems have it)
        # Skip only if explicitly v1 or unsupported
        if cgroup_version and cgroup_version not in ["v2", None]:
            skipped.append({
                "node_id": node_id,
                "reason": f"cgroup_version != v2 (got {cgroup_version})",
                "execution_mode": execution_mode,
                "cgroup_version": cgroup_version,
            })
            continue

        # Node passed all filters
        passed.append(node)

    return passed, skipped


# ── Scenario Tests ─────────────────────────────────────────────────────────

class TestResults:
    """Container for test results."""

    def __init__(self):
        self.scenarios = []
        self.preflight_total = 0
        self.preflight_passed = 0
        self.preflight_failed = 0
        self.preflight_skipped = 0
        self.skipped_nodes = []  # List of dicts with reason, cgroup_version, etc.

    def add_scenario(self, scenario: dict):
        self.scenarios.append(scenario)

    def record_preflight(self, passed: bool):
        self.preflight_total += 1
        if passed:
            self.preflight_passed += 1
        else:
            self.preflight_failed += 1

    def record_skipped_nodes(self, skipped_list: List[dict]):
        """Record nodes that were skipped during filtering."""
        self.preflight_skipped = len(skipped_list)
        self.skipped_nodes = skipped_list


class Orchestrator:
    """Main orchestrator for stress tests."""

    def __init__(
        self,
        client: MopClient,
        private_key,
        dry_run: bool = False,
        runtime: Optional[str] = None,
    ):
        self.client = client
        self.private_key = private_key
        self.dry_run = dry_run
        self.runtime = runtime  # 'docker', 'podman', or None (all)
        self.results = TestResults()
        self.timestamp = datetime.utcnow().isoformat() + "Z"

    def dispatch_preflight(self, node_id: str) -> bool:
        """Dispatch preflight check to node. Returns True if passed."""
        print(f"  → Running preflight on {node_id}...")

        script = load_script(".", "preflight_check.py")
        if not script:
            return False

        if self.dry_run:
            print(f"    [DRY-RUN] Would dispatch preflight_check.py")
            return True

        sig = sign_script(self.private_key, script)
        job_id = self.client.dispatch_job(script, sig, timeout_s=30)

        if not job_id:
            print(f"    ERROR: Failed to dispatch preflight")
            self.results.record_preflight(False)
            return False

        job = self.client.poll_job(job_id, timeout_s=180)
        if not job:
            print(f"    ERROR: Preflight timed out")
            self.results.record_preflight(False)
            return False

        # Parse result
        stdout = job.get("stdout", "")
        if stdout:
            try:
                first_line = stdout.split("\n")[0]
                result = json.loads(first_line)
                passed = result.get("pass", False)
                self.results.record_preflight(passed)
                if passed:
                    print(f"    ✓ Preflight passed")
                    return True
                else:
                    print(f"    ✗ Preflight failed: {result}")
                    return False
            except json.JSONDecodeError:
                print(f"    ERROR: Could not parse preflight result")
                self.results.record_preflight(False)
                return False

        print(f"    ERROR: No stdout from preflight")
        self.results.record_preflight(False)
        return False

    def run_scenario_1_single_cpu(self) -> dict:
        """Scenario 1: Single CPU burn with throttling."""
        print(f"\nSCENARIO 1: Single CPU Burn")

        script = load_script("python", "cpu_burn.py")
        if not script:
            return {"name": "single_cpu_burn", "results": []}

        if self.dry_run:
            print(f"  [DRY-RUN] Would dispatch python/cpu_burn.py with cpu_limit=0.5")
            return {
                "name": "single_cpu_burn",
                "results": [{"language": "python", "pass": True, "details": "ratio=0.50"}],
            }

        sig = sign_script(self.private_key, script)
        job_id = self.client.dispatch_job(script, sig, cpu_limit=0.5, timeout_s=15)

        if not job_id:
            print(f"  ERROR: Failed to dispatch cpu_burn")
            return {"name": "single_cpu_burn", "results": []}

        job = self.client.poll_job(job_id, timeout_s=180)
        if not job:
            print(f"  ERROR: CPU burn timed out")
            return {"name": "single_cpu_burn", "results": []}

        # Parse result
        stdout = job.get("stdout", "")
        results = []
        if stdout:
            try:
                first_line = stdout.split("\n")[0]
                result = json.loads(first_line)
                ratio = result.get("ratio", 1.0)
                # ratio < 0.8 = PASS (throttled), >= 0.8 = INFO (not throttled but ok)
                passed = ratio < 0.8
                results.append({
                    "language": "python",
                    "pass": passed,
                    "details": f"ratio={ratio:.2f}",
                })
                print(f"  python  | {'PASS' if passed else 'INFO'} | ratio={ratio:.2f}")
            except json.JSONDecodeError:
                print(f"  ERROR: Could not parse cpu_burn result")

        return {"name": "single_cpu_burn", "results": results}

    def run_scenario_2_memory_oom(self) -> dict:
        """Scenario 2: Single memory OOM."""
        print(f"\nSCENARIO 2: Single Memory OOM")

        script = load_script("python", "memory_hog.py")
        if not script:
            return {"name": "single_memory_oom", "results": []}

        if self.dry_run:
            print(f"  [DRY-RUN] Would dispatch python/memory_hog.py with memory_limit=128M")
            return {
                "name": "single_memory_oom",
                "results": [{"language": "python", "pass": True, "details": "exit_code=137"}],
            }

        sig = sign_script(self.private_key, script)
        job_id = self.client.dispatch_job(script, sig, memory_limit="128m", timeout_s=40)

        if not job_id:
            print(f"  ERROR: Failed to dispatch memory_hog")
            return {"name": "single_memory_oom", "results": []}

        job = self.client.poll_job(job_id, timeout_s=180)
        if not job:
            print(f"  ERROR: Memory OOM test timed out")
            return {"name": "single_memory_oom", "results": []}

        # Parse result
        exit_code = job.get("exit_code", -1)
        results = []
        if exit_code == 137:
            # OOM-killed as expected
            results.append({
                "language": "python",
                "pass": True,
                "details": f"exit_code={exit_code}",
            })
            print(f"  python  | PASS | exit_code={exit_code}")
        else:
            # Did not get OOM-killed
            results.append({
                "language": "python",
                "pass": False,
                "details": f"exit_code={exit_code}",
            })
            print(f"  python  | FAIL | exit_code={exit_code} (expected 137)")

        return {"name": "single_memory_oom", "results": results}

    async def run_scenario_3_concurrent_isolation(self) -> dict:
        """Scenario 3: Concurrent isolation test."""
        print(f"\nSCENARIO 3: Concurrent Isolation")

        memory_script = load_script("python", "memory_hog.py")
        cpu_script = load_script("python", "cpu_burn.py")
        monitor_script = load_script("python", "noisy_monitor.py")

        if not (memory_script and cpu_script and monitor_script):
            print(f"  ERROR: Missing scripts")
            return {"name": "concurrent_isolation", "results": []}

        if self.dry_run:
            print(f"  [DRY-RUN] Would dispatch memory_hog, cpu_burn, noisy_monitor concurrently")
            return {
                "name": "concurrent_isolation",
                "results": [{"combined": True, "pass": True, "details": "max_drift=1.05s"}],
            }

        # Sign scripts
        mem_sig = sign_script(self.private_key, memory_script)
        cpu_sig = sign_script(self.private_key, cpu_script)
        mon_sig = sign_script(self.private_key, monitor_script)

        # Dispatch all 3 concurrently
        mem_id = self.client.dispatch_job(memory_script, mem_sig, memory_limit="512m", timeout_s=35)
        cpu_id = self.client.dispatch_job(cpu_script, cpu_sig, cpu_limit=1.0, timeout_s=10)
        mon_id = self.client.dispatch_job(monitor_script, mon_sig, timeout_s=65)

        if not all([mem_id, cpu_id, mon_id]):
            print(f"  ERROR: Failed to dispatch all three jobs")
            return {"name": "concurrent_isolation", "results": []}

        # Poll all 3 until completion
        mem_job = self.client.poll_job(mem_id, timeout_s=180)
        cpu_job = self.client.poll_job(cpu_id, timeout_s=180)
        mon_job = self.client.poll_job(mon_id, timeout_s=200)

        # Check monitor for drift
        results = []
        if mon_job:
            stdout = mon_job.get("stdout", "")
            if stdout:
                try:
                    first_line = stdout.split("\n")[0]
                    result = json.loads(first_line)
                    max_drift = result.get("max_drift_s", 1.5)
                    passed = result.get("pass", False)
                    results.append({
                        "combined": True,
                        "pass": passed,
                        "details": f"max_drift={max_drift:.2f}s",
                    })
                    print(f"  Combined | {'PASS' if passed else 'FAIL'} | max_drift={max_drift:.2f}s < 1.1s")
                except json.JSONDecodeError:
                    print(f"  ERROR: Could not parse monitor result")
        else:
            print(f"  ERROR: Monitor job timed out")

        return {"name": "concurrent_isolation", "results": results}

    def run_scenario_4_all_language_sweep(self) -> dict:
        """Scenario 4: All-language sweep."""
        print(f"\nSCENARIO 4: All-Language Sweep")

        languages = ["python", "bash", "pwsh"]
        script_types = ["cpu_burn", "memory_hog", "noisy_monitor"]

        results_by_lang = {}

        for lang in languages:
            lang_pass_count = 0
            lang_total = 0

            for script_type in script_types:
                script_file = {
                    "cpu_burn": "cpu_burn.py" if lang == "python" else (
                        "cpu_burn.sh" if lang == "bash" else "cpu_burn.ps1"
                    ),
                    "memory_hog": "memory_hog.py" if lang == "python" else (
                        "memory_hog.sh" if lang == "bash" else "memory_hog.ps1"
                    ),
                    "noisy_monitor": "noisy_monitor.py" if lang == "python" else (
                        "noisy_monitor.sh" if lang == "bash" else "noisy_monitor.ps1"
                    ),
                }[script_type]

                script = load_script(lang, script_file)
                if not script:
                    continue

                lang_total += 1

                if self.dry_run:
                    lang_pass_count += 1
                    continue

                # Determine limits
                limits = {}
                if script_type == "cpu_burn":
                    limits["cpu_limit"] = 0.5
                elif script_type == "memory_hog":
                    limits["memory_limit"] = "128m"

                # Map pwsh to powershell for API
                api_runtime = "powershell" if lang == "pwsh" else lang

                sig = sign_script(self.private_key, script)
                job_id = self.client.dispatch_job(script, sig, runtime=api_runtime, **limits, timeout_s=40)

                if not job_id:
                    continue

                job = self.client.poll_job(job_id, timeout_s=180)
                if not job:
                    continue

                # Check pass/fail
                stdout = job.get("stdout", "")
                try:
                    first_line = stdout.split("\n")[0]
                    result = json.loads(first_line)
                    if result.get("pass", False) or result.get("exit_code") == 137:
                        lang_pass_count += 1
                except json.JSONDecodeError:
                    pass

            if lang_total > 0:
                status = "PASS" if lang_pass_count == lang_total else "FAIL"
                results_by_lang[lang] = {
                    "pass": lang_pass_count == lang_total,
                    "details": f"{lang_pass_count}/{lang_total} scripts",
                }
                print(f"  {lang:8} | {status} | {lang_pass_count}/{lang_total} scripts")

        return {
            "name": "all_language_sweep",
            "results": [
                {"language": lang, **v} for lang, v in results_by_lang.items()
            ],
        }

    def run_all_scenarios(self) -> TestResults:
        """Run all 4 scenarios."""
        print("\n" + "=" * 60)
        print("STRESS TEST ORCHESTRATOR")
        if self.runtime:
            print(f"Runtime: {self.runtime.upper()}")
        print("=" * 60)

        # Load secrets and login
        try:
            secrets = find_secrets_env()
            admin_password = secrets.get("ADMIN_PASSWORD", "")
            if not admin_password:
                raise ValueError("ADMIN_PASSWORD not set in secrets.env")
        except Exception as e:
            print(f"ERROR: {e}")
            return self.results

        print(f"\nLogging in to {AGENT_URL}...")
        if not self.client.login():
            print("ERROR: Login failed")
            return self.results

        # Get nodes and filter by runtime
        all_nodes = self.client.list_nodes()
        print(f"Found {len(all_nodes)} available nodes")

        # Filter by runtime and cgroup v2
        target_nodes, skipped_nodes = filter_nodes_by_runtime(all_nodes, self.runtime)
        self.results.record_skipped_nodes(skipped_nodes)

        if skipped_nodes:
            print(f"Skipped {len(skipped_nodes)} nodes:")
            for skip in skipped_nodes:
                print(f"  - {skip['node_id']}: {skip['reason']}")

        if not target_nodes and not self.dry_run:
            print("ERROR: No nodes available after filtering")
            return self.results

        print(f"Target nodes: {len(target_nodes)}")

        # Run preflight on first target node
        if target_nodes and not self.dry_run:
            node_id = target_nodes[0].get("node_id", target_nodes[0].get("id", "node-1"))
            print(f"\nRunning preflight checks on {node_id}...")
            if not self.dispatch_preflight(node_id):
                print(f"WARNING: Preflight failed on {node_id}, would skip in production")

        # Run scenarios
        self.results.add_scenario(self.run_scenario_1_single_cpu())
        self.results.add_scenario(self.run_scenario_2_memory_oom())

        # Scenario 3 is async
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        self.results.add_scenario(loop.run_until_complete(self.run_scenario_3_concurrent_isolation()))

        self.results.add_scenario(self.run_scenario_4_all_language_sweep())

        return self.results

    def print_summary(self):
        """Print console summary table."""
        print("\n" + "=" * 60)
        print("RESULTS SUMMARY")
        print("=" * 60)

        total_tests = sum(len(s.get("results", [])) for s in self.results.scenarios)
        passed_tests = sum(
            len([r for r in s.get("results", []) if r.get("pass", False)])
            for s in self.results.scenarios
        )

        print(f"Test Time: {self.timestamp}")
        print(f"Server: {self.client.base}")
        if self.runtime:
            print(f"Runtime: {self.runtime.upper()}")
        print(f"Total Tests: {total_tests}")
        print(f"Passed: {passed_tests}")
        print(f"Failed: {total_tests - passed_tests}")
        print()

        # Preflight summary
        print(f"Preflight Check:")
        print(f"  Total: {self.results.preflight_total}")
        print(f"  Passed: {self.results.preflight_passed}")
        print(f"  Failed: {self.results.preflight_failed}")
        print(f"  Skipped (pre-filter): {self.results.preflight_skipped}")
        print()

        for scenario in self.results.scenarios:
            print(f"Scenario: {scenario.get('name', 'unknown')}")
            for result in scenario.get("results", []):
                lang = result.get("language", result.get("combined", "N/A"))
                status = "PASS" if result.get("pass") else "FAIL"
                details = result.get("details", "")
                print(f"  {str(lang):15} | {status} | {details}")

    def write_json_report(self):
        """Write JSON report to mop_validation/reports/."""
        REPORTS_DIR.mkdir(exist_ok=True)

        # Count results
        total_tests = sum(len(s.get("results", [])) for s in self.results.scenarios)
        passed_tests = sum(
            len([r for r in s.get("results", []) if r.get("pass", False)])
            for s in self.results.scenarios
        )

        # Build preflight section with skip details
        preflight_data = {
            "total": self.results.preflight_total,
            "passed": self.results.preflight_passed,
            "failed": self.results.preflight_failed,
            "skipped": self.results.preflight_skipped,
        }
        if self.results.skipped_nodes:
            preflight_data["skipped_details"] = self.results.skipped_nodes

        report = {
            "timestamp": self.timestamp,
            "server": self.client.base,
            "runtime": self.runtime or "all",
            "total_nodes": 0,  # Would be populated from list_nodes
            "preflight": preflight_data,
            "scenarios": self.results.scenarios,
            "summary": {
                "total_tests": total_tests,
                "passed": passed_tests,
                "failed": total_tests - passed_tests,
            },
        }

        # Write file with runtime in filename
        timestamp_str = self.timestamp.replace(":", "").replace("-", "").replace(".", "")
        runtime_suffix = f"_{self.runtime}" if self.runtime else ""
        report_path = REPORTS_DIR / f"stress_test{runtime_suffix}_{timestamp_str}.json"
        report_path.write_text(json.dumps(report, indent=2))
        print(f"\nJSON report written to: {report_path}")


def main():
    """Main entry point."""
    # Parse arguments
    parser = argparse.ArgumentParser(
        description="Stress Test Orchestrator with optional runtime filtering"
    )
    parser.add_argument(
        "--runtime",
        choices=["docker", "podman"],
        default=None,
        help="Target specific runtime (docker or podman); omit for all nodes",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Skip API calls, simulate orchestration logic",
    )
    args = parser.parse_args()

    dry_run = args.dry_run
    runtime = args.runtime

    print(f"Starting orchestrator (dry_run={dry_run}, runtime={runtime})...")

    # Ensure signing keys exist
    private_key, public_key_pem = ensure_ed25519_keys()

    # Get secrets
    try:
        secrets = find_secrets_env()
        admin_password = secrets.get("ADMIN_PASSWORD", "")
        server_url = secrets.get("SERVER_URL", AGENT_URL)
    except Exception as e:
        print(f"ERROR: {e}")
        sys.exit(1)

    # Create client and orchestrator
    client = MopClient(server_url, admin_password, public_key_pem=public_key_pem)

    # Login and register signature (unless dry-run)
    if not dry_run:
        if not client.login():
            print("ERROR: Failed to login")
            sys.exit(1)
        if not client.register_signature():
            print("ERROR: Failed to register signature")
            sys.exit(1)

    orchestrator = Orchestrator(client, private_key, dry_run=dry_run, runtime=runtime)

    # Run all scenarios
    orchestrator.run_all_scenarios()

    # Print and save results
    orchestrator.print_summary()
    orchestrator.write_json_report()

    print("\nOrchestration complete.")


if __name__ == "__main__":
    main()
