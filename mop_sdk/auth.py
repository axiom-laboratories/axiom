import httpx
import time
import os
import json
import shutil
import webbrowser
import logging
from pathlib import Path
from typing import Optional, Dict

logger = logging.getLogger("mop_sdk.auth")

class CredentialStore:
    def __init__(self, config_dir: Optional[str] = None):
        if config_dir:
            self.config_path = Path(config_dir) / "credentials.json"
        else:
            new_path = Path.home() / ".axiom" / "credentials.json"
            old_path = Path.home() / ".mop" / "credentials.json"
            # One-time migration: move ~/.mop/credentials.json to ~/.axiom/
            if old_path.exists() and not new_path.exists():
                new_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.move(str(old_path), str(new_path))
                print("Migrated credentials from ~/.mop/ to ~/.axiom/")
            self.config_path = new_path
        
    def save(self, data: Dict[str, str]):
        """Saves credentials to ~/.mop/credentials.json with 0600 permissions."""
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Write file
        with open(self.config_path, "w") as f:
            json.dump(data, f, indent=2)
        
        # Set permissions to 0600 (read/write by owner only)
        os.chmod(self.config_path, 0o600)
        logger.debug(f"Saved credentials to {self.config_path}")

    def load(self) -> Optional[Dict[str, str]]:
        """Loads credentials from disk."""
        if not self.config_path.exists():
            return None
        
        try:
            with open(self.config_path, "r") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load credentials: {e}")
            return None

    def clear(self):
        """Removes credentials file."""
        if self.config_path.exists():
            self.config_path.unlink()

class DeviceFlowHandler:
    def __init__(self, base_url: str, verify_ssl: bool = True):
        self.base_url = base_url.rstrip("/")
        self.verify_ssl = verify_ssl
        self._client = httpx.Client(verify=self.verify_ssl)

    def start_flow(self) -> Dict[str, str]:
        """Initiates the device flow."""
        resp = self._client.post(f"{self.base_url}/auth/device")
        resp.raise_for_status()
        return resp.json()

    def poll_for_token(self, device_code: str, interval: int, expires_in: int) -> Optional[Dict[str, str]]:
        """Polls the token endpoint until approved, denied, or expired."""
        start_time = time.time()
        current_interval = interval

        while (time.time() - start_time) < expires_in:
            resp = self._client.post(
                f"{self.base_url}/auth/device/token",
                json={"device_code": device_code}
            )
            
            if resp.status_code == 200:
                return resp.json()
            
            if resp.status_code == 400:
                error = resp.json().get("detail", {}).get("error")
                if error == "authorization_pending":
                    pass # Keep polling
                elif error == "slow_down":
                    current_interval += 5
                elif error == "access_denied":
                    print("\nAccess denied by user.")
                    return None
                elif error == "expired_token":
                    print("\nDevice code expired.")
                    return None
                else:
                    raise Exception(f"Unexpected error: {error}")
            else:
                resp.raise_for_status()

            time.sleep(current_interval)
        
        print("\nTimed out waiting for approval.")
        return None
