# Master of Puppets - Universal Installer (v0.9)
# Usage:
#   iex (irm https://server:8001/api/installer) -Role Node -Token "eyJ..."
#   ./install_universal.ps1 -Role Node -Token "eyJ..." -Count 3

param(
    [Parameter(Mandatory = $false)]
    [ValidateSet("Agent", "Node")]
    [string]$Role = "Node",

    [Parameter(Mandatory = $false)]
    [string]$Token,

    [Parameter(Mandatory = $false)]
    [string]$ServerUrl = "https://localhost:8001",

    [Parameter(Mandatory = $false)]
    [int]$Count = 1,

    [Parameter(Mandatory = $false)]
    [ValidateSet("Podman", "Docker")]
    [string]$Platform = "Podman"
)

$ErrorActionPreference = "Stop"

function Write-Log {
    param([string]$Message, [string]$Color = "White")
    Write-Host "[Installer] $Message" -ForegroundColor $Color
}

Write-Log "Initializing Universal Installer ($Role on $Platform)..." "Cyan"

# 0. Environment Checks
if ($Platform -eq "Podman") {
    if (-not (Get-Command podman -ErrorAction SilentlyContinue)) {
        Write-Error "Podman is not installed. Please install Podman first."
    }
    if (-not (Get-Command podman-compose -ErrorAction SilentlyContinue)) {
        # Try to find it in likely python paths
        $PotentialPaths = @(
            "$env:APPDATA\Python\Python312\Scripts",
            "$env:APPDATA\Python\Python311\Scripts",
            "$env:LOCALAPPDATA\Programs\Python\Python312\Scripts"
        )
        foreach ($Path in $PotentialPaths) {
            if (Test-Path "$Path\podman-compose.exe") {
                $env:Path += ";$Path"
                Write-Log "Found podman-compose in $Path, added to PATH." "Green"
                break
            }
        }
    }
}
elseif ($Platform -eq "Docker") {
    if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
        Write-Error "Docker is not installed."
    }
    # Check for 'docker compose' (plugin) or 'docker-compose' (standalone)
    $DockerComposePlugin = (docker compose version) 2>$null
    if (-not $DockerComposePlugin -and -not (Get-Command docker-compose -ErrorAction SilentlyContinue)) {
        Write-Error "Docker Compose is not found (checked 'docker compose' and 'docker-compose')."
    }
}

# 1. Token & Trust Bootstrapping
if ($Role -eq "Node") {
    if (-not $Token) {
        $Token = Read-Host "Enter Join Token"
    }

    Write-Log "Parsing Token..." "Cyan"
    try {
        # Base64 Decode Token
        $JsonBytes = [System.Convert]::FromBase64String($Token)
        $JsonStr = [System.Text.Encoding]::UTF8.GetString($JsonBytes)
        $Payload = $JsonStr | ConvertFrom-Json
        
        $RealToken = $Payload.t # Used for debug if needed, keeping for clarity
        $CaContent = $Payload.ca
        
        # Format CA Content (Ensure newlines)
        $CaContent = $CaContent -replace "`r`n", "`n"
        $CaContent = $CaContent -replace "`n", "`n"
        $CaContent = $CaContent.Trim() + "`n"
        
        # Write Trusted Root CA
        [System.IO.File]::WriteAllText("$PWD/bootstrap_ca.crt", $CaContent, [System.Text.Encoding]::ASCII)
        Write-Log "✅ Trust Root extracted to bootstrap_ca.crt" "Green"

        # 3b. Trust the Root (Auto-Import to CurrentUser)
        try {
            Write-Log "Importing CA to Trust Store (CurrentUser)..."
            Import-Certificate -FilePath "$PWD/bootstrap_ca.crt" -CertStoreLocation "Cert:\CurrentUser\Root" -ErrorAction Stop | Out-Null
            Write-Log "✅ CA Trust Established." "Green"
        }
        catch {
            Write-Log "Warning: Failed to auto-import CA. Strictly secure fetches might fail. Error: $_" "Yellow"
        }
        
    }
    catch {
        Write-Error "Invalid Token Format. Ensure you are using a v0.8+ Token."
    }
}

# 2. Configuration Fetch (Strict SSL)
if ($Role -eq "Node") {
    Write-Log "Fetching Node Configuration (Strict SSL)..." "Cyan"
    
    # We use the extracted CA to verify the server identity
    $ComposeUrl = "$ServerUrl/api/node/compose?token=$Token&platform=$Platform"
    
    # Security Hardening:
    # We rely on the CA being trusted (Step 1). 
    # We use --ssl-no-revoke ...
    $CurlArgs = @("--ssl-no-revoke", "--fail", "-v", "$ComposeUrl", "-o", "node-compose.yaml")
    
    Write-Log "Executing: curl $($CurlArgs -join ' ')" "Gray"
    
    & curl.exe @CurlArgs
    
    if ($LASTEXITCODE -ne 0) {
        Write-Error "Failed to download configuration. Verify Token and Server URL."
    }
    
    Write-Log "✅ node-compose.yaml downloaded." "Green"
}
elseif ($Role -eq "Agent") {
    Write-Log "Agent (Server) deployment not yet fully automated via script (Use git clone + podman-compose)." "Yellow"
    # Placeholder for potential server-in-a-box logic
    exit 0
}

# 3. Mount Setup (Optional/Auto)
# Note: Network mounts are handled by the Server config response injection into compose.

# 4. Deployment
Write-Log "Starting Containers (x$Count) using $Platform..." "Cyan"

if ($Platform -eq "Podman") {
    podman-compose -f node-compose.yaml up -d --scale node=$Count
}
elseif ($Platform -eq "Docker") {
    # Prefer 'docker compose' (plugin) over 'docker-compose'
    # We check if 'docker compose' command works by silencing error output
    $DockerComposeStr = $(try { docker compose version 2>&1 } catch { $null })
    if ($DockerComposeStr -match "Docker Compose") {
        docker compose -f node-compose.yaml up -d --scale node=$Count
    }
    else {
        docker-compose -f node-compose.yaml up -d --scale node=$Count
    }
}

if ($LASTEXITCODE -eq 0) {
    Write-Log "🚀 Deployment Complete!" "Green"
    if ($Platform -eq "Podman") {
        Write-Log "Run 'podman logs -f <container_name>' to view status." "White"
    }
    else {
        Write-Log "Run 'docker logs -f <container_name>' to view status." "White"
    }
}
else {
    Write-Error "Deployment failed."
}
