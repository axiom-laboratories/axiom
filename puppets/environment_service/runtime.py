import shutil
import subprocess
import os
import logging
import asyncio
from typing import Dict, List, Optional

class ContainerRuntime:
    def __init__(self):
        self.runtime = self.detect_runtime()
        logging.info(f"Container Runtime Detected: {self.runtime}")

    def detect_runtime(self) -> str:
        # Preference: Podman > Docker
        if shutil.which("podman"):
            return "podman"
        if shutil.which("docker"):
            return "docker"
        return "subprocess"

    async def run(
        self, 
        image: str, 
        command: List[str], 
        env: Dict[str, str] = {}, 
        mounts: List[str] = [], 
        network_ref: str = None,
        input_data: str = None
    ) -> Dict:
        """
        Executes a containerized job.
        network_ref: ID/Hostname of the container to share network with (for Sidecar access).
        """
        
        if self.runtime == "subprocess":
            return {"exit_code": -1, "stdout": "", "stderr": "Container Runtime not found"}

        cmd = [self.runtime, "run", "--rm"]
        if input_data:
            cmd.append("-i")

        # 1. Network Strategy (Sidecar Access)
        if network_ref:
            cmd.extend([f"--network=container:{network_ref}"])
        else:
            cmd.extend(["--network=host"])

        # 2. Namespace Mapping (Podman specific)
        if self.runtime == "podman":
            cmd.append("--userns=keep-id")
            cmd.extend(["-v", "/etc/localtime:/etc/localtime:ro"])

        # 3. Environment Variables
        for k, v in env.items():
            cmd.extend(["-e", f"{k}={v}"])

        # 4. Mounts
        for m in mounts:
            cmd.extend(["-v", m])

        # 5. Image & Command
        cmd.append(image)
        cmd.extend(command)

        print(f"[Runtime] Executing: {' '.join(cmd)}")
        
        # Async Execution
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdin=asyncio.subprocess.PIPE if input_data else None,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        stdout, stderr = await proc.communicate(input=input_data.encode() if input_data else None)
        
        return {
            "exit_code": proc.returncode,
            "stdout": stdout.decode(),
            "stderr": stderr.decode()
        }
