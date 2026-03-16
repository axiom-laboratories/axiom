#!/usr/bin/env python3
import subprocess
import json
import time
import sys
import os
import re

NODE_NAME = "mop-test-node"
IMAGE = "images:ubuntu/24.04"
# Get the absolute path of the workspace root (Development/)
# Based on current knowledge, it's /home/thomas/Development
WORKSPACE_ROOT = "/home/thomas/Development"
SECRETS_FILE = os.path.join(WORKSPACE_ROOT, "mop_validation/secrets.env")

def run(cmd, check=True):
    # If it's an incus command and we are NOT root, we'll try to run it.
    # If it fails with a permission error, we'll give a helpful hint.
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if check and result.returncode != 0:
        if "Permission denied" in result.stderr or "needed permissions" in result.stderr:
            print(f"\n[!] Permission error running: {cmd}")
            print("    Your session doesn't have incus-admin permissions.")
            print("    FIX: Run 'newgrp incus-admin' in your terminal and try again without sudo.")
            print("    Alternatively, run this script with sudo (but you'll be prompted for password).")
        else:
            print(f"Error executing: {cmd}")
            print(result.stderr)
        sys.exit(1)
    return result

def get_node_ip():
    res = run(f"incus list {NODE_NAME} --format json")
    data = json.loads(res.stdout)
    if not data:
        return None
    
    networks = data[0].get("state", {}).get("network", {})
    for net in networks.values():
        for addr in net.get("addresses", []):
            if addr.get("family") == "inet" and addr.get("scope") == "global":
                return addr.get("address")
    return None

def update_secrets(ip):
    if not os.path.exists(SECRETS_FILE):
        print(f"Warning: {SECRETS_FILE} not found. Skipping IP update.")
        return

    with open(SECRETS_FILE, "r") as f:
        content = f.read()

    # Update speedy_mini_ip
    new_content = re.sub(r"speedy_mini_ip=.*", f"speedy_mini_ip={ip}", content)
    # Ensure username is 'ubuntu' for the default Incus image
    new_content = re.sub(r"speedy_mini_username=.*", "speedy_mini_username=ubuntu", new_content)
    # For LXC we typically use SSH keys, but if the script expects a password, 
    # we'll set a default one for the 'ubuntu' user.
    new_content = re.sub(r"speedy_mini_password=.*", "speedy_mini_password=ubuntu", new_content)

    with open(SECRETS_FILE, "w") as f:
        f.write(new_content)
    print(f"Updated {SECRETS_FILE} with IP: {ip} (User: ubuntu)")

def setup_node():
    print(f"--- Launching Incus Node: {NODE_NAME} ---")
    run(f"incus launch {IMAGE} {NODE_NAME} -c security.nesting=true", check=False)
    
    print("Waiting for IP address...")
    ip = None
    for _ in range(15):
        ip = get_node_ip()
        if ip: break
        time.sleep(2)
    
    if not ip:
        print("Failed to get IP address.")
        sys.exit(1)
    
    print(f"Node IP: {ip}")
    
    print("--- Configuring Node (Podman, SSH, Python) ---")
    # Wait for cloud-init/network to be ready inside
    time.sleep(5)
    
    # Create temporary sudoers file on host
    sudoers_path = "/tmp/mop_sudoers"
    with open(sudoers_path, "w") as f:
        f.write("ubuntu ALL=(ALL) NOPASSWD:ALL\n")

    commands = [
        "apt-get update",
        "apt-get install -y podman openssh-server python3 python3-pip sudo",
        "useradd -m -s /bin/bash ubuntu || true",
        "usermod -aG sudo ubuntu || true",
        "mkdir -p /home/ubuntu/.ssh",
        "chown ubuntu:ubuntu /home/ubuntu/.ssh",
        # Ensure /etc/sudoers.d is included
        "grep -q '^#includedir /etc/sudoers.d' /etc/sudoers || echo '#includedir /etc/sudoers.d' >> /etc/sudoers"
    ]
    
    for cmd in commands:
        print(f"Exec: {cmd}")
        run(f"incus exec {NODE_NAME} -- {cmd}")

    print("Injecting sudoers file...")
    # Fix potential permissions on sudoers.d before pushing
    run(f"incus exec {NODE_NAME} -- mkdir -p /etc/sudoers.d")
    run(f"incus file push {sudoers_path} {NODE_NAME}/etc/sudoers.d/ubuntu")
    run(f"incus exec {NODE_NAME} -- chmod 0440 /etc/sudoers.d/ubuntu")
    run(f"incus exec {NODE_NAME} -- chown root:root /etc/sudoers.d/ubuntu")
    os.remove(sudoers_path)

    # Set password separately with a pipe
    print("Exec: setting password for ubuntu...")
    run(f"echo 'ubuntu:ubuntu' | incus exec {NODE_NAME} -- chpasswd")

    # Inject host's public key if it exists
    pub_key_path = os.path.expanduser("~/.ssh/id_rsa.pub")
    if os.path.exists(pub_key_path):
        print("Injecting SSH public key...")
        run(f"incus file push {pub_key_path} {NODE_NAME}/home/ubuntu/.ssh/authorized_keys")
        run(f"incus exec {NODE_NAME} -- chown ubuntu:ubuntu /home/ubuntu/.ssh/authorized_keys")
        run(f"incus exec {NODE_NAME} -- chmod 600 /home/ubuntu/.ssh/authorized_keys")
    
    update_secrets(ip)
    print("\n--- Setup Complete ---")
    print(f"Target: ubuntu@{ip}")
    print(f"Password: ubuntu (if key fails)")
    print("\nYou can now run your deployment scripts!")

def teardown_node():
    print(f"--- Deleting Incus Node: {NODE_NAME} ---")
    run(f"incus delete {NODE_NAME} --force")
    print("Cleanup complete.")

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "stop":
        teardown_node()
    else:
        setup_node()
