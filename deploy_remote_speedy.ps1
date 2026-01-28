$RemoteHost = "192.168.50.128"
$User = "speedygit"
$TargetDir = "/home/speedygit/puppeteer_stack"

Write-Host "Deploying Puppeteer Stack to $RemoteHost..." -ForegroundColor Cyan
Write-Host "NOTE: You will be prompted for the SSH password multiple times (mkdir, scp copy, scp secrets)." -ForegroundColor Yellow

# 1. Create Directory
Write-Host "[1/3] Creating target directory ($TargetDir)..."
ssh $User@$RemoteHost "mkdir -p $TargetDir"

# 2. Copy Puppeteer Directory
Write-Host "[2/3] Copying Puppeteer files (this may take a moment)..."
# Using -r to copy recursively. 
# We explicitly copy the contents of puppeteer/ to the target dir.
scp -r .\puppeteer\* $User@$RemoteHost:$TargetDir

# 3. Copy Secrets (Critical)
if (Test-Path "secrets.env") {
    Write-Host "[3/3] Copying secrets.env..."
    scp .\secrets.env $User@$RemoteHost:$TargetDir/secrets.env
}
else {
    Write-Warning "secrets.env not found locally. You will need to enter secrets interactively on the remote."
}

Write-Host "----------------------------------------------------------------" -ForegroundColor Green
Write-Host "Deployment Complete. Now it is time to install!" -ForegroundColor Green
Write-Host "----------------------------------------------------------------"
Write-Host "1. SSH into the remote machine:"
Write-Host "   ssh $User@$RemoteHost"
Write-Host ""
Write-Host "2. Go to the directory:"
Write-Host "   cd $TargetDir"
Write-Host ""
Write-Host "3. Run the Loader (Automatic Install):"
Write-Host "   podman build -t puppeteer-loader -f loader/Containerfile ."
Write-Host "   podman run --privileged --rm -it -v /var/run/podman.sock:/run/podman/podman.sock -v `.`:/app puppeteer-loader"
Write-Host ""
Write-Host "   # The loader will pick up the secrets.env we just copied and start the stack."
