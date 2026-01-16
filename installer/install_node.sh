#!/bin/bash
# Master of Puppets - Linux Node Installer

# Args
HUB_URL="${1:-https://localhost:8001}"
JOIN_TOKEN="$2"
MOUNTS="$3"

echo -e "\033[0;36mBootstrapping Node...\033[0m"

if ! command -v podman &> /dev/null; then
    echo "Error: Podman is not installed."
    exit 1
fi

if [ -z "$JOIN_TOKEN" ]; then
    read -p "Enter Join Token: " JOIN_TOKEN
fi

# 1. Get Compose File
echo "fetching configuration from Hub..."
# Note: Insecure curl (-k) used for self-signed trial. In prod, install CA.
curl -k "$HUB_URL/installer/compose?token=$JOIN_TOKEN&mounts=$MOUNTS" -o node-compose.yaml

if [ ! -s node-compose.yaml ]; then
    echo "Error: Failed to download configuration."
    exit 1
fi

# 2. Start
echo "Starting Node..."
podman-compose -f node-compose.yaml up -d

echo "Node Started!"
