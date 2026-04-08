#!/usr/bin/env pwsh
# stress/pwsh/cpu_burn.ps1
# CPU Throttling Validation (PowerShell)
#
# Spins a CPU-bound loop for a configurable duration and measures CPU throttling
# by comparing wall time to CPU time. Uses System.Diagnostics.Stopwatch for
# high-resolution timing.
#
# Required env:
#   AXIOM_CAPABILITIES   Capability string. Must contain "resource_limits_supported".
#   CPU_DURATION_S       Duration in seconds (default 5)
#
# Exit codes:
#   0  Measurement complete (throttling detected or not — both are valid exits).
#   1  resource_limits_supported capability is missing — abort safely.

param()

# Read AXIOM_CAPABILITIES and CPU_DURATION_S from environment
$capsRaw = $env:AXIOM_CAPABILITIES
$durationEnv = $env:CPU_DURATION_S
[int]$cpuDurationS = if ($durationEnv) { [int]$durationEnv } else { 5 }

# Check for resource_limits_supported capability
if (-not $capsRaw -or -not $capsRaw.Contains("resource_limits_supported")) {
    # Output JSON for capability missing case
    $failJson = @{
        type = "cpu_burn"
        language = "powershell"
        wall_s = 0.0
        cpu_s = 0.0
        ratio = 0.0
        threshold = 0.8
        pass = $false
        error = "resource_limits_supported capability missing"
    } | ConvertTo-Json
    Write-Output $failJson
    Write-Output "FAIL: resource limits are not supported on this node (resource_limits_supported capability missing)"
    exit 1
}

Write-Output "resource_limits_supported: present — proceeding with CPU spin test"

# Get the current process for CPU time measurement
$currentProcess = Get-Process -Id $PID

# Start high-resolution stopwatch for wall-time measurement
$wallStopwatch = [System.Diagnostics.Stopwatch]::StartNew()

# Record CPU time before spinning
$cpuTimeBefore = $currentProcess.UserProcessorTime.TotalSeconds

# Calculate deadline for CPU spin
$deadline = [DateTime]::UtcNow.AddSeconds($cpuDurationS)

# CPU-bound loop: tight arithmetic operations
while ([DateTime]::UtcNow -lt $deadline) {
    $x = [Math]::Pow(2, 31)
}

# Stop the stopwatch
$wallStopwatch.Stop()

# Get CPU time after spinning and calculate elapsed CPU time
$currentProcess = Get-Process -Id $PID
$cpuTimeAfter = $currentProcess.UserProcessorTime.TotalSeconds
$cpuElapsed = $cpuTimeAfter - $cpuTimeBefore

# Extract measurements
[double]$wallS = $wallStopwatch.Elapsed.TotalSeconds
[double]$cpuS = $cpuElapsed
[double]$ratio = if ($wallS -gt 0) { $cpuS / $wallS } else { 0.0 }
[double]$threshold = 0.8

# Determine pass/fail
$pass = $ratio -lt $threshold

# Output JSON
$jsonOutput = @{
    type = "cpu_burn"
    language = "powershell"
    wall_s = [Math]::Round($wallS, 2)
    cpu_s = [Math]::Round($cpuS, 2)
    ratio = [Math]::Round($ratio, 2)
    threshold = $threshold
    pass = $pass
} | ConvertTo-Json
Write-Output $jsonOutput

# Output human-readable summary
if ($pass) {
    Write-Output "PASS: CPU throttling confirmed (ratio=$([Math]::Round($ratio, 2)) < $threshold threshold)"
} else {
    Write-Output "INFO: No throttling detected (ratio=$([Math]::Round($ratio, 2)) >= $threshold) — either cpu_limit is not set or this node has spare capacity"
}

Write-Output "=== cpu_burn validation complete ==="

exit 0
