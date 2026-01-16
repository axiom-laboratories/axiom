# Master of Puppets - Server Installer (Podman)
Write-Host "Installing Master of Puppets Server (Podman Stack)..." -ForegroundColor Cyan

# Prequisite Check
if (-not (Get-Command podman -ErrorAction SilentlyContinue)) {
    Write-Error "Podman is not installed."
    exit 1
}

# Check for podman-compose
if (-not (Get-Command podman-compose -ErrorAction SilentlyContinue)) {
    Write-Warning "podman-compose not found. Attempting to install..."
    pip install podman-compose
    if (-not $?) {
        Write-Error "Failed to install podman-compose. Please install it manually."
        exit 1
    }
}

# 1. Generate Secrets
Write-Host "[1/2] Checking Keys..."
if (-not (Test-Path "secrets/signing.key")) {
    mkdir secrets -ErrorAction SilentlyContinue | Out-Null
    Write-Host "Generating keys using temporary container..."
    # Run python container to generate keys
    podman run --rm -v "${PWD}/secrets:/app/secrets" -v "${PWD}/tools:/app/tools" python:3.12-slim python /app/tools/admin_signer.py --generate
}

# 2. Start Stack
Write-Host "[2/2] Launching Stack..."
podman-compose -f compose.server.yaml up -d --build

Write-Host "Installation Complete!" -ForegroundColor Green
Write-Host "Dashboard: http://localhost:5173"
