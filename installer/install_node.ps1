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

# 1. Parse Token (Token-Embedded Trust)
Write-Host "Parsing Secure Token..."
try {
    # Base64 Decode
    $JsonBytes = [System.Convert]::FromBase64String($JoinToken)
    $JsonStr = [System.Text.Encoding]::UTF8.GetString($JsonBytes)
    $Payload = $JsonStr | ConvertFrom-Json
    
    $RealToken = $Payload.t
    $CaContent = $Payload.ca
    
    # Save CA to disk
    Set-Content -Path "bootstrap_ca.crt" -Value $CaContent -NoNewline
    Write-Host "Trust Root extracted." -ForegroundColor Green
}
catch {
    Write-Error "Invalid Token Format. Ensure you are using a v0.8+ Token."
    exit 1
}

# 2. Download Configuration
Write-Host "Fetching configuration from Hub (Secure)..."
$Uri = "$ServerUrl/api/node/compose?token=$RealToken&mounts=$Mounts"

# Secure Download using extracted CA
# --ssl-no-revoke: Required on Windows because the internal CA has no CRL/OCSP
curl.exe --ssl-no-revoke --cacert bootstrap_ca.crt -o "node-compose.yaml" $Uri

if ($LASTEXITCODE -ne 0 -or -not (Test-Path "node-compose.yaml")) {
    Write-Error "Failed to download configuration. (Exit Code: $LASTEXITCODE)"
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
