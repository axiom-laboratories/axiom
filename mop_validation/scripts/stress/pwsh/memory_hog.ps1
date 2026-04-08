#!/usr/bin/env pwsh
# stress/pwsh/memory_hog.ps1
# Memory OOM Validation (PowerShell)
#
# Allocates a configurable amount of RSS memory (page-touching prevents overcommit
# from deferring the commit) and holds it for 30 seconds. On a node configured
# with a memory_limit less than the allocation, the container runtime should
# OOM-kill the process before the hold completes.
#
# Required env:
#   AXIOM_CAPABILITIES   Capability string. Must contain "resource_limits_supported".
#   MEMORY_SIZE_MB       Memory to allocate in MB (default 256)
#
# Exit codes:
#   0  Unreachable under normal operation (job should be OOM-killed).
#   1  resource_limits_supported capability is missing — abort safely.
#   2  Sentinel: process was NOT killed during the 30-second hold window.
#      This indicates resource limits are not enforced on this node.

param()

# Read AXIOM_CAPABILITIES and MEMORY_SIZE_MB from environment
$capsRaw = $env:AXIOM_CAPABILITIES
$memorySizeEnv = $env:MEMORY_SIZE_MB
[int]$memorySizeMB = if ($memorySizeEnv) { [int]$memorySizeEnv } else { 256 }

# Check for resource_limits_supported capability
if (-not $capsRaw -or -not $capsRaw.Contains("resource_limits_supported")) {
    # Output JSON for capability missing case
    $failJson = @{
        type = "memory_hog"
        language = "powershell"
        memory_size_mb = $memorySizeMB
        allocated = $false
        pass = $false
        error = "resource_limits_supported capability missing"
    } | ConvertTo-Json
    Write-Output $failJson
    Write-Output "FAIL: resource limits are not supported on this node (resource_limits_supported capability missing)"
    exit 1
}

Write-Output "resource_limits_supported: present — proceeding with memory allocation test"
Write-Output "Allocating $memorySizeMB MB ..."

# Calculate size in bytes
[long]$sizeBytes = [long]$memorySizeMB * 1024 * 1024

# Allocate byte array
try {
    $chunk = [byte[]]::new($sizeBytes)
}
catch {
    # Allocation itself failed
    $failJson = @{
        type = "memory_hog"
        language = "powershell"
        memory_size_mb = $memorySizeMB
        allocated = $false
        pass = $false
        error = "Allocation failed: $_"
    } | ConvertTo-Json
    Write-Output $failJson
    Write-Output "ERROR: Memory allocation failed"
    exit 2
}

# Touch every page (4096-byte stride) to force RSS commitment
# This defeats Linux memory overcommit and forces the kernel to allocate physical RAM
Write-Output "Page-touching allocation to force RSS commitment ..."
for ([long]$i = 0; $i -lt $chunk.Length; $i += 4096) {
    $chunk[$i] = 0
}

Write-Output "Allocation complete — container should be OOM-killed or exceed memory limit"
Write-Output "Holding for 30 seconds..."

# Sleep for 30 seconds. If process is not killed by OOM, we reach the line below.
Start-Sleep -Seconds 30

# If the process reaches this line, the container runtime did not enforce limits.
# Output JSON and exit code 2
$failJson = @{
    type = "memory_hog"
    language = "powershell"
    memory_size_mb = $memorySizeMB
    allocated = $true
    pass = $false
    error = "Process was not OOM-killed during hold window"
} | ConvertTo-Json
Write-Output $failJson
Write-Output "ERROR: should have been killed before reaching this line (enforcement not detected)"

exit 2
