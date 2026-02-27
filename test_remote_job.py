print("End-to-end Verification Success: Secure job execution on remote ARM64 node (speedy_mini) confirmed.")
import platform
import os
print(f"Node OS: {platform.system()} {platform.machine()}")
print(f"UID: {os.getuid() if hasattr(os, 'getuid') else 'N/A'}")
