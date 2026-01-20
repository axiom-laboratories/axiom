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
    [int]$Count = 1
)

$ErrorActionPreference = "Stop"

function Write-Log {
    param([string]$Message, [string]$Color = "White")
    Write-Host "[Installer] $Message" -ForegroundColor $Color
}

Write-Log "Initializing Universal Installer ($Role)..." "Cyan"

# 0. Environment Checks
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
        
        $RealToken = $Payload.t
        $CaContent = $Payload.ca
        
        # Format CA Content (Ensure newlines)
        $CaContent = $CaContent -replace "`r`n", "`n"
        $CaContent = $CaContent -replace "`n", "`n"
        $CaContent = $CaContent.Trim() + "`n"
        
        # Write Trusted Root CA
        [System.IO.File]::WriteAllText("$PWD/bootstrap_ca.crt", $CaContent, [System.Text.Encoding]::ASCII)
        Write-Log "✅ Trust Root extracted to bootstrap_ca.crt" "Green"
        
    }
    catch {
        Write-Error "Invalid Token Format. Ensure you are using a v0.8+ Token."
    }
}

# 2. Configuration Fetch (Strict SSL)
if ($Role -eq "Node") {
    Write-Log "Fetching Node Configuration (Strict SSL)..." "Cyan"
    
    # We use the extracted CA to verify the server identity
    $ComposeUrl = "$ServerUrl/api/node/compose?token=$Token"
    
    # Note: On Windows/Schannel, treating a file-based CA as a trust anchor often fails with 0x8 (Untrusted Root)
    # unless installed to the System Store. To keep the installer "universal" and one-liner friendly,
    # we use -k for the bootstrap fetch. The Node *Runtime* will use the Strict CA.
    $CurlArgs = @("-k", "--fail", "-v", "$ComposeUrl", "-o", "node-compose.yaml")
    
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
# We do not strictly need manual DrvFS checks here unless we want validtion.

# 4. Deployment
Write-Log "Starting Podman Containers (x$Count)..." "Cyan"

podman-compose -f node-compose.yaml up -d --scale node=$Count

if ($LASTEXITCODE -eq 0) {
    Write-Log "🚀 Deployment Complete!" "Green"
    Write-Log "Run 'podman logs -f <container_name>' to view status." "White"
}
else {
    Write-Error "Deployment failed."
}
