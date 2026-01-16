#!/bin/bash
# Master of Puppets - Linux Server Installer

echo -e "\033[0;36mInstalling Master of Puppets Server...\033[0m"

# Checks
if ! command -v podman &> /dev/null; then
    echo "Error: Podman is not installed."
    exit 1
fi

if ! command -v podman-compose &> /dev/null; then
    echo "Warning: podman-compose not found. Attempting to install via pip..."
    if command -v pip3 &> /dev/null; then
        pip3 install podman-compose
    else
        echo "Error: pip3 not found. Cannot install podman-compose."
        exit 1
    fi
fi

# 1. Generate Secrets if missing
if [ ! -f "secrets/signing.key" ]; then
    echo "[1/3] Generating Keys..."
    mkdir -p secrets
    # We can run a temporary container to generate keys or assume python is local?
    # Requirement: "run a curl command from the repo" -> "One Line Install".
    # If we assume python is NOT local, we should run keygen in container.
    # Let's run a one-off podman command to generate keys using our server image (built first? or use python image)
    
    # Simpler: Assume Python 3 is present as per Prerequisites?
    # User said: "install... by running a curl command". 
    # Let's try to run the admin_signer in a temp python container to be safe and truly "containerized".
    
    echo "Generating keys using temporary container..."
    podman run --rm -v $(pwd)/secrets:/app/secrets -v $(pwd)/tools:/app/tools python:3.12-slim python /app/tools/admin_signer.py --generate
fi

# 2. Build & Start
echo "[2/3] Starting Stack..."
podman-compose -f compose.server.yaml up -d --build

echo -e "\033[0;32mInstallation Complete!\033[0m"
echo "Dashboard: http://localhost:5173"
