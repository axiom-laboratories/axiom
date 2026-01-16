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
$Uri = "$ServerUrl/installer/compose?token=$JoinToken&mounts=$Mounts"
Invoke-WebRequest -Uri $Uri -OutFile "node-compose.yaml" -SkipCertificateCheck

if (-not (Test-Path "node-compose.yaml")) {
    Write-Error "Failed to download configuration."
    exit 1
}

# 2. Start
Write-Host "Starting Node..."
podman-compose -f node-compose.yaml up -d

Write-Host "Node Started!" -ForegroundColor Green
