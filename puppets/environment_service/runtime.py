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

        # auto mode: socket-first detection
        if os.path.exists("/var/run/docker.sock"):
            logger.info("Container runtime: docker (socket detected)")
            return "docker"

        if os.path.exists("/run/podman/podman.sock"):
            logger.info("Container runtime: podman (socket detected)")
            return "podman"

        # Fallback: binary detection
        if shutil.which("podman"):
            logger.info("Container runtime: podman (binary in PATH)")
            return "podman"

        if shutil.which("docker"):
            logger.info("Container runtime: docker (binary in PATH)")
            return "docker"

        raise RuntimeError(
            "No container runtime detected. "
            "Ensure Docker or Podman is installed and accessible. "
            "For Docker-in-Docker, mount the host Docker socket at /var/run/docker.sock. "
            "For Podman, ensure /run/podman/podman.sock is mounted or podman binary is in PATH. "
            "See docs/runbooks/faq.md for guidance."
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

        # 2. Network Strategy (DEPRECATED: replaced with jobs_network bridge isolation per Phase 134)
        if os.name != 'nt':
            network = network_ref or "jobs_network"
            cmd.extend([f"--network={network}"])

        # 3. Namespace Mapping (Podman specific)
        if self.runtime == "podman":
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
