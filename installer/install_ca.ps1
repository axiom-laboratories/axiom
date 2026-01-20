<#
.SYNOPSIS
    Imports the Master of Puppets Internal Root CA into the Windows Trusted Root Store.
    
.DESCRIPTION
    This script downloads the Root CA from the Server (or takes a local file) and imports it
    into the 'CurrentUser' Trusted Root Certification Authorities store. this allows
    Browsers and PowerShell/Curl to trust the server without security warnings.

.PARAMETER ServerUrl
    URL of the Master of Puppets server (default: https://localhost:8001).
    
.PARAMETER CaPath
    Optional path to a local CA file. If not provided, it fetches from the server.
    
.EXAMPLE
    .\install_ca.ps1
    Imports from https://localhost:8001 (requires server to be up and accessible via -k initially).
    
.EXAMPLE
    .\install_ca.ps1 -CaPath .\bootstrap_ca.crt
    Imports a local certificate file.
#>

param(
    [string]$ServerUrl = "https://localhost:8001",
    [string]$CaPath
)

function Write-Log {
    param([string]$Message, [string]$Color = "White")
    Write-Host "[TrustInstaller] $Message" -ForegroundColor $Color
}

$ErrorActionPreference = "Stop"
$CertStoreScope = "CurrentUser" # Use LocalMachine if you need system-wide trust (Requires Admin)
$CertStoreName = "Root"

try {
    # 1. Acquire CA Certificate
    if (-not [string]::IsNullOrWhiteSpace($CaPath)) {
        if (-not (Test-Path $CaPath)) {
            throw "Certificate file not found: $CaPath"
        }
        $CertFilePath = $CaPath
        Write-Log "Using local CA file: $CertFilePath" "Cyan"
    }
    else {
        # Fetch from Server (bootstrapping trust)
        # We assume we can get the CA via the 'installer' flow or a dedicated endpoint?
        # Actually, the CA is embedded in the Token, or we can grab it from a running node.
        # But wait, there is no public endpoint to just "GET /ca.crt" securely without auth?
        # However, for an "Trust Installer", we usually assume the user has the file or we fetch it.
        # Let's try to fetch it from /api/docs (if I exposes it?) No.
        # Let's assume the user has the 'bootstrap_ca.crt' from running install_universal.ps1 or extracted it.
        
        # fallback: Attempt to download if we can (maybe add a public endpoint later).
        # For now, let's require -CaPath OR try to find 'bootstrap_ca.crt' in current dir.
        
        if (Test-Path "bootstrap_ca.crt") {
            $CertFilePath = "bootstrap_ca.crt"
            Write-Log "Found bootstrap_ca.crt in current directory." "Cyan"
        }
        elseif (Test-Path ".\installer\bootstrap_ca.crt") {
            # Repo structure
            $CertFilePath = ".\installer\bootstrap_ca.crt"
            Write-Log "Found bootstrap_ca.crt in installer directory." "Cyan"
        }
        else {
            # If strictly needing to fetch, we'd need a token.
            # Easier to ask user to run install_universal.ps1 first, which saves it.
            throw "CA Certificate not found. Please provide -CaPath or run install_universal.ps1 first to extract it."
        }
    }

    # 2. Import Certificate
    Write-Log "Importing CA to Cert:\$CertStoreScope\$CertStoreName..." "Yellow"
    
    # Load Cert to check details
    $Cert = New-Object System.Security.Cryptography.X509Certificates.X509Certificate2($CertFilePath)
    Write-Log "Subject: $($Cert.Subject)" "Gray"
    Write-Log "Thumbprint: $($Cert.Thumbprint)" "Gray"
    
    # Use Import-Certificate Cmdlet
    Import-Certificate -FilePath $CertFilePath -CertStoreLocation "Cert:\$CertStoreScope\$CertStoreName" -Verbose
    
    Write-Log "Success! The CA is now trusted by $CertStoreScope." "Green"
    Write-Log "You should now be able to access $ServerUrl without warnings." "Green"

}
catch {
    Write-Log "Error: $_" "Red"
    exit 1
}
