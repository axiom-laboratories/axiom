# Axiom Hello-World (PowerShell) — JOB-03 reference job.
# Handles Linux where $env:COMPUTERNAME may be empty.
$hostName = if ($env:COMPUTERNAME) { $env:COMPUTERNAME } else { (hostname) }

Write-Host "=== Axiom Hello-World (PowerShell) ==="
Write-Host "Host:    $hostName"
Write-Host "OS:      $([System.Runtime.InteropServices.RuntimeInformation]::OSDescription)"
Write-Host "PS:      $($PSVersionTable.PSVersion)"
Write-Host "Time:    $((Get-Date).ToUniversalTime().ToString('yyyy-MM-ddTHH:mm:ssZ'))"
Write-Host "=== PASS ==="
