---
name: manage-test-nodes
description: Automates the creation and teardown of ephemeral Incus test nodes for remote deployment testing. Use when you need to spin up a fresh Ubuntu "VM" (system container) to test deployment scripts like remote_deploy.py.
---

# Manage Test Nodes

This skill automates the management of ephemeral test nodes using **Incus** (a snap-free LXD fork). Each node behaves like a real remote server with its own IP, SSH, unique machine-id, and nested Podman support.

## Core Workflow

### 1. Spin up a fresh node
Run the bundled `manage_node.py` script. 

**Pro Tip**: If your user is in the `incus-admin` group, you don't need `sudo`. If you get a permission error, run `newgrp incus-admin` in your terminal once to activate your group membership.

```bash
# Recommended (no sudo needed if group is active)
python3 .agent/skills/manage-test-nodes/scripts/manage_node.py

# Fallback (if group membership isn't working)
sudo python3 .agent/skills/manage-test-nodes/scripts/manage_node.py
```

This will:
- Launch an Ubuntu 24.04 container.
- Install `podman`, `ssh`, and `python`.
- Inject your host's SSH public key (`~/.ssh/id_rsa.pub`) to `ubuntu` user.
- Configure `sudo` for `ubuntu` without a password **(Fix applied: robust sudoers and group membership)**.
- **Auto-update** `mop_validation/secrets.env` with the new node's IP.

### 2. Run remote deployment tests
Once the node is up, your `secrets.env` is already updated. You can immediately run:
```bash
cd mop_validation && python3 dev_tools/remote_deploy.py
```

### 3. Teardown
To save resources and keep the environment clean, always stop the node when finished:
```bash
sudo python3 .agent/skills/manage-test-nodes/scripts/manage_node.py stop
```

## Troubleshooting
- **Permissions**: If `incus` commands fail, ensure you are using `sudo` or that your user is in the `incus-admin` group.
- **IP Address**: The script waits 20s for an IP. If it fails, check `incus list` to see if the container is running but hasn't received an IP from the bridge.
- **SSH Key**: Ensure `~/.ssh/id_rsa.pub` exists on your host before running the script for a seamless connection.

## Bundled Resources
- `scripts/manage_node.py`: The automation script for Incus lifecycle.
