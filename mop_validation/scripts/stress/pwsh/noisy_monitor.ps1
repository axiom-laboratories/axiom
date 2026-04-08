#!/usr/bin/env pwsh
# stress/pwsh/noisy_monitor.ps1
# Noisy-Neighbour Monitor (PowerShell)
#
# Measures sleep latency drift by performing 60 iterations of sleep(1) and
# tracking the actual elapsed time for each iteration using high-resolution
# Stopwatch. Detects if other jobs are stealing CPU time (noisy neighbours).
#
# No capability gating — monitor works without resource_limits_supported.
#
# Required env:
#   DRIFT_THRESHOLD_S    Maximum allowed drift in seconds (default 1.1)
#
# Exit codes:
#   0  Pass: all sleep iterations stayed below threshold.
#   2  Fail: at least one iteration exceeded the threshold (noisy-neighbour detected).

param()

# Read DRIFT_THRESHOLD_S from environment
$thresholdEnv = $env:DRIFT_THRESHOLD_S
[double]$driftThresholdS = if ($thresholdEnv) { [double]$thresholdEnv } else { 1.1 }

Write-Output "Noisy-neighbour monitor: measuring sleep drift over 60 iterations"
Write-Output "Threshold: $driftThresholdS seconds"

# Array to hold measurements
[System.Collections.Generic.List[double]]$measurements = [System.Collections.Generic.List[double]]::new()

# Perform 60 iterations of sleep(1) with per-iteration timing
for ($i = 0; $i -lt 60; $i++) {
    $sw = [System.Diagnostics.Stopwatch]::StartNew()
    Start-Sleep -Seconds 1
    $sw.Stop()

    [double]$elapsedS = $sw.Elapsed.TotalSeconds
    $measurements.Add($elapsedS)

    # Print progress every 10 iterations
    if (($i + 1) % 10 -eq 0) {
        Write-Output "  Iteration $($i + 1)/60: elapsed=$([Math]::Round($elapsedS, 3))s"
    }
}

# Calculate statistics
$maxDrift = $measurements | Measure-Object -Maximum | Select-Object -ExpandProperty Maximum
$minDrift = $measurements | Measure-Object -Minimum | Select-Object -ExpandProperty Minimum
$avgDrift = $measurements | Measure-Object -Average | Select-Object -ExpandProperty Average

# Determine pass/fail: all measurements must be below threshold
$pass = $maxDrift -lt $driftThresholdS

# Convert measurements array to JSON-friendly format
$measurementsArray = @()
foreach ($m in $measurements) {
    $measurementsArray += [Math]::Round($m, 3)
}

# Output JSON with all measurements
$jsonOutput = @{
    type = "noisy_monitor"
    language = "powershell"
    iterations = 60
    threshold_s = $driftThresholdS
    max_drift = [Math]::Round($maxDrift, 3)
    min_drift = [Math]::Round($minDrift, 3)
    mean_drift = [Math]::Round($avgDrift, 3)
    pass = $pass
    measurements = $measurementsArray
} | ConvertTo-Json
Write-Output $jsonOutput

# Output human-readable summary
Write-Output ""
Write-Output "=== Noisy-neighbour Monitor Results ==="
Write-Output "Iterations: 60"
Write-Output "Max drift: $([Math]::Round($maxDrift, 3))s"
Write-Output "Min drift: $([Math]::Round($minDrift, 3))s"
Write-Output "Mean drift: $([Math]::Round($avgDrift, 3))s"
Write-Output "Threshold: $driftThresholdS s"

if ($pass) {
    Write-Output "PASS: All sleep iterations within threshold (max=$([Math]::Round($maxDrift, 3)) < $driftThresholdS)"
    $exitCode = 0
} else {
    Write-Output "FAIL: Sleep drift exceeded threshold (max=$([Math]::Round($maxDrift, 3)) >= $driftThresholdS) — noisy-neighbour activity detected"
    $exitCode = 2
}

Write-Output "=== noisy_monitor validation complete ==="

exit $exitCode
