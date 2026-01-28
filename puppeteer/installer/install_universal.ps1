# Master of Puppets - Universal Installer (v1.0)
# Usage:
#   iex (irm https://server:8001/api/installer) -Role Node -Token "eyJ..."
#   ./install_universal.ps1 -Role Node -Token "eyJ..." -Count 3
#   ./install_universal.ps1 -Platform Docker  # Force Docker

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
    [ValidateSet("Podman", "Docker", "")]
    [string]$Platform = ""
)

$ErrorActionPreference = "Stop"

function Write-Log {
    param([string]$Message, [string]$Color = "White")
    Write-Host "[Installer] $Message" -ForegroundColor $Color
}

# --- Platform Detection ---
$HasDocker = [bool](Get-Command docker -ErrorAction SilentlyContinue)
$HasPodman = [bool](Get-Command podman -ErrorAction SilentlyContinue)

if ($Platform -eq "") {
    # Auto-detect
    if (-not $HasDocker -and -not $HasPodman) {
        Write-Error "Neither Docker nor Podman found. Please install one first."
    }
    elseif ($HasDocker -and $HasPodman) {
        Write-Host ""
        Write-Host "Both Docker and Podman detected. Please choose:" -ForegroundColor Yellow
        Write-Host "  [1] Docker" -ForegroundColor Cyan
        Write-Host "  [2] Podman" -ForegroundColor Cyan
        $Choice = Read-Host "Select runtime [1/2]"
        if ($Choice -eq "2") {
            $Platform = "Podman"
        }
        else {
            $Platform = "Docker"
        }
    }
    elseif ($HasDocker) {
        $Platform = "Docker"
        Write-Log "Auto-detected: Docker" "Green"
    }
    else {
        $Platform = "Podman"
        Write-Log "Auto-detected: Podman" "Green"
    }
}
else {
    Write-Log "Using specified platform: $Platform" "Cyan"
}

Write-Log "Initializing Universal Installer ($Role on $Platform)..." "Cyan"

# 0. Environment Checks (Validate selected platform)
if ($Platform -eq "Podman") {
    if (-not $HasPodman) {
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
    if (-not $HasDocker) {
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

    # Fetch Verification Key
    Write-Log "Fetching Validation Key..." "Cyan"
    $KeyUrl = "$ServerUrl/api/verification-key"
    Set-Content -Path "$PWD/verification.key" -Value "" # Create Empty
    
    # We use curl because Invoke-WebRequest with strict SSL on custom CA can be tricky in older PS
    $KeyCurlArgs = @("--ssl-no-revoke", "--fail", "-s", "$KeyUrl", "-o", "verification.key")
    & curl.exe @KeyCurlArgs

    if (Test-Path "$PWD/verification.key") {
        $KeyContent = Get-Content "$PWD/verification.key"
        if ($KeyContent.Length -gt 10) {
            Write-Log "✅ Verification Key downloaded." "Green"
        }
        else {
            Write-Log "Warning: Verification Key seems empty or missing on server." "Yellow"
        }
    }
}
elseif ($Role -eq "Agent") {
    Write-Log "Initializing Server (Agent) Deployment..." "Cyan"
    Write-Host ""
    Write-Host "Select Installation Method:" -ForegroundColor Yellow
    Write-Host "  [1] Automatic (Loader Container) - Recommended" -ForegroundColor Green
    Write-Host "      - Runs installation inside a container."
    Write-Host "      - Requires NO dependencies on host (except Podman)."
    Write-Host ""
    Write-Host "  [2] Manual (Script Execution) - Advanced" -ForegroundColor Gray
    Write-Host "      - Runs directly on host."
    Write-Host "      - Requires Python 3.12+, Pip, Podman-Compose on PATH."
    
    $Method = Read-Host "Select Method [1/2]"
    
    if ($Method -eq "1") {
        # --- PATH 1: LOADER ---
        Write-Log "Launching Puppeteer Loader..." "Cyan"
        
        # Build Loader Image locally first (ensure fresh code)
        # Note: In production we might pull, but here we build from source
        Write-Log "Building Loader Image..." "Gray"
        podman build -t puppeteer-loader -f loader/Containerfile .
        
        if ($LASTEXITCODE -ne 0) {
            Write-Error "Failed to build Loader image."
        }
        
        # Run Loader
        # -v /var/run/podman.sock:/run/podman/podman.sock : Socket access
        # --privileged : Required for socket interaction in some setups
        # -v $PWD:/app : Mount current dir so loader sees compose file and secrets
        # -w /app : Workdir
        
        # Detect socket path based on OS 
        # (Quick check, assuming Linux default keying off the user's Speedy Mini request, 
        # but maintaining Windows compat via magic pipe if needed or just assuming user handles socket mapping)
        
        # For simplicity in this script (Windows host), we assume Podman Desktop/Machine exposes pipe or socket.
        # However, "podman run" on Windows usually handles the socket forwarding if we don't map it explicitly?
        # NO, we must map the control socket so the INSIDE podman can talk to the OUTSIDE podman.
        
        # Linux: /var/run/podman.sock
        # Windows: Pipe is hard to map to file. 
        # BUT: User asked to test on "Speedy Mini" (Remote). That is likely Linux.
        # If running on Windows, we might need a specific flag or accept limitation.
        
        $SocketMount = "-v /var/run/podman.sock:/run/podman/podman.sock"
        if ($IsWindows) {
           Write-Log "Windows detected: Ensure Podman Machine is running. Mapping named pipe might require special setup." "Yellow"
           # Windows Podman usually connects via ssh or pipe. Simple volume mount won't work for Pipe -> File.
           # However, if we are just verifying logic, we'll assume Linux for the "Speedy Mini" target.
           # Or we try to use the user's existing connection.
        }

        Write-Log "Running Loader..." "Cyan"
        $RunCmd = "podman run --privileged --rm -it $SocketMount -v ${PWD}:/app puppeteer-loader"
        Write-Host "Command: $RunCmd"
        Invoke-Expression $RunCmd
        
        exit $LASTEXITCODE
    }
    else {
        # --- PATH 2: MANUAL (EXISTING LOGIC) ---
        Write-Log "Using Manual Installation..." "Cyan"
        # 1. Secrets Management
        $SecretsFile = "secrets.env"
        if (-not (Test-Path $SecretsFile)) {
            # Check parent directory
            if (Test-Path "../$SecretsFile") {
                $SecretsFile = "../$SecretsFile"
                Write-Log "Found secrets in parent directory: $SecretsFile" "Green"
            }
            else {
                Write-Log "Secrets file not found. Interactive Setup:" "Yellow"
                $DuckToken = Read-Host "Enter DuckDNS Token"
                $DuckDomain = Read-Host "Enter DuckDNS Domain (e.g. my-app.duckdns.org)"
                $Email = Read-Host "Enter Admin Email (for Let's Encrypt)"
                
                $Content = @"
DUCKDNS_TOKEN=$DuckToken
DUCKDNS_DOMAIN=$DuckDomain
ACME_EMAIL=$Email
"@
                Set-Content -Path "secrets.env" -Value $Content
                $SecretsFile = "secrets.env"
                Write-Log "✅ Created secrets.env" "Green"
            }
        }

        # 2. Build Cert Manager (Critical for Plugins)
        Write-Log "Building Cert-Manager (Caddy + DNS Plugins)..." "Cyan"
        
        if ($Platform -eq "Podman") {
            podman compose -f compose.server.yaml build cert-manager
        }
        else {
            docker compose -f compose.server.yaml build cert-manager
        }
        
        if ($LASTEXITCODE -ne 0) {
            Write-Error "Failed to build cert-manager image."
        }

        # 3. Launch Stack
        Write-Log "Launching Puppeteer Stack..." "Cyan"
        
        # We must pass --env-file explicitly
        if ($Platform -eq "Podman") {
            podman compose -f compose.server.yaml --env-file $SecretsFile up -d --force-recreate
        }
        else {
            docker compose -f compose.server.yaml --env-file $SecretsFile up -d --force-recreate
        }
        
        if ($LASTEXITCODE -eq 0) {
            Write-Log "🚀 Server Deployed!" "Green"
            
            # Parse Domain from secrets to show URL
            $EnvContent = Get-Content $SecretsFile
            $DomainLine = $EnvContent | Select-String "DUCKDNS_DOMAIN"
            if ($DomainLine) {
                $Domain = ($DomainLine.ToString() -split "=")[1]
                Write-Log "Dashboard: https://$Domain" "Green"
            }
            else {
                 Write-Log "Dashboard: https://localhost (Check domain in secrets)" "Green"
            }
        }
        else {
            Write-Error "Server deployment failed."
        }
        
        exit 0
    }
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
