# Master of Puppets - Node Bootstrap (Podman)
param(
    [string]$ServerUrl = "https://localhost:8001",
    [string]$JoinToken,
    [string]$Mounts
)

Write-Host "Bootstrapping Environment Node (Podman)..." -ForegroundColor Cyan

if (-not (Get-Command podman -ErrorAction SilentlyContinue)) {
    Write-Error "Podman is not installed."
    exit 1
}

if (-not $JoinToken) {
    $JoinToken = Read-Host "Enter Join Token"
}

# 1. Download Configuration
Write-Host "Fetching configuration from Hub..."
$Uri = "$ServerUrl/api/node/compose?token=$JoinToken&mounts=$Mounts"
# Use curl.exe for robust SSL bypass
Write-Host "Fetching configuration using curl.exe..."
curl.exe -k -o "node-compose.yaml" $Uri

if (-not (Test-Path "node-compose.yaml")) {
    Write-Error "Failed to download configuration."
    exit 1
}

# 2. Start
Write-Host "Starting Node..."

# Ensure podman-compose is in path (User Install Location)
$env:Path = "$env:Path;C:\Users\thoma\AppData\Roaming\Python\Python312\Scripts"

if (-not (Get-Command podman-compose -ErrorAction SilentlyContinue)) {
    Write-Error "podman-compose found. Please install it: pip install podman-compose"
    exit 1
}

podman-compose -f node-compose.yaml up -d

Write-Host "Node Started!" -ForegroundColor Green
