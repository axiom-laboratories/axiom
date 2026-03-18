import shutil
import subprocess
import os
import logging
import asyncio
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

class ContainerRuntime:
    def __init__(self):
        self.runtime = self.detect_runtime()
        logging.info(f"Container Runtime Detected: {self.runtime}")

    def detect_runtime(self) -> str:
        mode = os.environ.get("EXECUTION_MODE", "auto").lower()
        if mode in ("docker", "podman"):
            logger.info(f"EXECUTION_MODE={mode} (explicit)")
            return mode
        # auto: probe available runtimes, no silent fallback
        if os.path.exists("/var/run/docker.sock") and shutil.which("docker"):
            return "docker"
        if shutil.which("podman"):
            return "podman"
        if shutil.which("docker"):
            return "docker"
        raise RuntimeError(
            "No container runtime found and EXECUTION_MODE=auto. "
            "Install docker/podman or set EXECUTION_MODE=docker or EXECUTION_MODE=podman."
        )

    async def run(
        self,
        image: str,
        command: List[str],
        env: Dict[str, str] = {},
        mounts: List[str] = [],
        network_ref: str = None,
        input_data: str = None,
        memory_limit: Optional[str] = None,
        cpu_limit: Optional[str] = None,
        timeout: Optional[int] = 30,
    ) -> Dict:
        """
        Executes a containerized job.
        network_ref: ID/Hostname of the container to share network with (for Sidecar access).
        timeout: Maximum seconds to wait for execution (default 30s).
        """

        cmd = [self.runtime, "run", "--rm"]
        if input_data:
            cmd.append("-i")

        # 1. Resource Limits
        if memory_limit:
            cmd.extend(["--memory", memory_limit])
        if cpu_limit:
            cmd.extend(["--cpus", str(cpu_limit)])

        # 2. Network Strategy
        if os.name != 'nt':
            cmd.extend(["--network=host"])

        # 3. Namespace Mapping (Podman specific)
        if self.runtime == "podman":
            cmd.append("--userns=keep-id")
            cmd.append("--storage-driver=vfs")
            cmd.append("--cgroup-manager=cgroupfs")
            cmd.append("--events-backend=none")
            cmd.extend(["-v", "/etc/localtime:/etc/localtime:ro"])
        elif self.runtime == "docker":
            cmd.extend(["-v", "/etc/localtime:/etc/localtime:ro"])

        # 4. Environment Variables
        for k, v in env.items():
            cmd.extend(["-e", f"{k}={v}"])

        # 5. Mounts
        for m in mounts:
            cmd.extend(["-v", m])

        # 6. Image & Command
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

        try:
            stdout, stderr = await asyncio.wait_for(
                proc.communicate(input=input_data.encode() if input_data else None),
                timeout=timeout,
            )
        except asyncio.TimeoutError:
            proc.kill()
            await proc.communicate()
            return {
                "exit_code": -1,
                "stdout": "",
                "stderr": f"Execution timed out after {timeout}s",
            }

        return {
            "exit_code": proc.returncode,
            "stdout": stdout.decode(),
            "stderr": stderr.decode()
        }
