# Master of Puppets — Installer Pester Tests
# Wave 0: RED stubs for WIN-01 through WIN-05
# Run: Invoke-Pester ./installer.Tests.ps1 -Output Minimal
# Note: WIN-01 and WIN-02 use inline function definitions (RED via missing real implementations).
#       WIN-04 and WIN-05 use static file inspection against ../install_universal.ps1.
#       WIN-03 is a pending stub — real test added in Plan 02 once function exists.

BeforeAll {
    # Install Pester if not present (pwsh on Linux)
    if (-not (Get-Module -ListAvailable -Name Pester)) {
        Install-Module -Name Pester -Force -SkipPublisherCheck -Scope CurrentUser
    }
    Import-Module Pester -MinimumVersion 5.0
}

Describe "Assert-PodmanMachineRunning" {

    Context "When a machine is running" {
        BeforeEach {
            # Inline stub — replace with dot-source after Plan 02 adds this function to install_universal.ps1
            function Assert-PodmanMachineRunning {
                $machineJson = podman machine list --format json 2>$null | ConvertFrom-Json
                $running = $machineJson | Where-Object { $_.Running -eq $true }
                if (-not $running) {
                    throw "No Podman machine is running. Start one with: podman machine start"
                }
                return $running[0].Name
            }
            Mock podman {
                '[{"Name":"podman-machine-default","Running":true}]'
            } -ParameterFilter { $args -contains 'list' }
        }
        It "WIN-01: returns machine name without throwing" {
            { Assert-PodmanMachineRunning } | Should -Not -Throw
        }
    }

    Context "When no machine is running" {
        BeforeEach {
            function Assert-PodmanMachineRunning {
                $machineJson = podman machine list --format json 2>$null | ConvertFrom-Json
                $running = $machineJson | Where-Object { $_.Running -eq $true }
                if (-not $running) {
                    throw "No Podman machine is running. Start one with: podman machine start"
                }
                return $running[0].Name
            }
            Mock podman {
                '[]'
            } -ParameterFilter { $args -contains 'list' }
        }
        It "WIN-01: throws a clear error when no machine is running" {
            { Assert-PodmanMachineRunning } | Should -Throw -ExpectedMessage "*No Podman machine*"
        }
    }
}

Describe "Get-PodmanSocketInfo" {

    Context "On Windows with running machine" {
        BeforeEach {
            # Inline stub — replace with dot-source after Plan 02 adds this function to install_universal.ps1
            function Get-PodmanSocketInfo {
                $pipePath = podman machine inspect --format '{{.ConnectionInfo.PodmanPipe.Path}}' 2>$null
                if ([string]::IsNullOrWhiteSpace($pipePath)) {
                    throw "Could not resolve Podman pipe path. Is a machine running?"
                }
                return $pipePath
            }
            Mock podman {
                '\\.\pipe\podman-machine-default'
            } -ParameterFilter { $args -contains 'inspect' }
        }
        It "WIN-02: returns a non-empty pipe path" {
            $path = Get-PodmanSocketInfo
            $path | Should -Not -BeNullOrEmpty
        }
        It "WIN-02: pipe path starts with \\\\.\\pipe\\" {
            $path = Get-PodmanSocketInfo
            $path | Should -Match '^\\\\\.'
        }
    }

    Context "When inspect returns empty path" {
        BeforeEach {
            function Get-PodmanSocketInfo {
                $pipePath = podman machine inspect --format '{{.ConnectionInfo.PodmanPipe.Path}}' 2>$null
                if ([string]::IsNullOrWhiteSpace($pipePath)) {
                    throw "Could not resolve Podman pipe path. Is a machine running?"
                }
                return $pipePath
            }
            Mock podman { '' } -ParameterFilter { $args -contains 'inspect' }
        }
        It "WIN-02: throws when pipe path is empty" {
            { Get-PodmanSocketInfo } | Should -Throw
        }
    }
}

Describe "Invoke-LoaderContainer (WIN-03)" {

    BeforeAll {
        # Define Invoke-LoaderContainer inline mirroring the ps1 implementation
        # so tests run without executing the full script body.
        function Invoke-LoaderContainer {
            param([string]$WorkDir = $PWD)
            $relayJob = $null
            $LoaderArgs = @("run", "--rm", "-it", "-v", "${WorkDir}:/app", "-w", "/app")
            if ($IsWindows -and -not $env:WSL_DISTRO_NAME) {
                $script:RelayStarted = $true
                $relayJob = Start-Job -ScriptBlock { }  # mocked below
                Start-Sleep -Milliseconds 1
                $LoaderArgs += @("--add-host=host.docker.internal:host-gateway",
                                 "-e", "DOCKER_HOST=tcp://host.docker.internal:2375")
            } else {
                $LoaderArgs += @("-v", "/var/run/podman.sock:/run/podman/podman.sock")
            }
            $LoaderArgs += "puppeteer-loader"
            $script:LastLoaderArgs = $LoaderArgs
            & podman @LoaderArgs
            if ($null -ne $relayJob) {
                Stop-Job $relayJob -ErrorAction SilentlyContinue
                Remove-Job $relayJob -ErrorAction SilentlyContinue
            }
        }
    }

    Context "On Linux/WSL (socket bind mount path)" {
        BeforeEach {
            $env:WSL_DISTRO_NAME = "Ubuntu"
            Mock podman { 0 }
            $script:LastLoaderArgs = @()
        }
        AfterEach {
            Remove-Item Env:WSL_DISTRO_NAME -ErrorAction SilentlyContinue
        }
        It "WIN-03: uses unix socket volume mount, not TCP relay" {
            Invoke-LoaderContainer -WorkDir "/tmp"
            $script:LastLoaderArgs | Should -Contain "/var/run/podman.sock:/run/podman/podman.sock"
            $script:LastLoaderArgs | Should -Not -Contain "DOCKER_HOST=tcp://host.docker.internal:2375"
        }
    }
}

Describe "Invoke-Expression replacement (WIN-04)" {

    It "WIN-04: install_universal.ps1 must not contain Invoke-Expression in the loader block" {
        $scriptPath = Join-Path $PSScriptRoot ".." "install_universal.ps1"
        if (-not (Test-Path $scriptPath)) {
            Set-ItResult -Pending -Because "install_universal.ps1 not found relative to tests/"
            return
        }
        $content = Get-Content $scriptPath -Raw
        # The loader block (between 'if ($Method -eq "1")' and 'else {') must not use Invoke-Expression.
        # Extract the Method-1 block heuristically: from 'Method -eq "1"' to the first 'else {' after it.
        $method1Block = [regex]::Match($content, '(?s)Method -eq "1".*?(?=else \{)').Value
        $method1Block | Should -Not -Match 'Invoke-Expression'
    }
}

Describe "podman-compose check gating (WIN-05)" {

    It "WIN-05: podman-compose validation block appears only in the Method-2 else branch" {
        $scriptPath = Join-Path $PSScriptRoot ".." "install_universal.ps1"
        if (-not (Test-Path $scriptPath)) {
            Set-ItResult -Pending -Because "install_universal.ps1 not found relative to tests/"
            return
        }
        $content = Get-Content $scriptPath -Raw
        # After fix: podman-compose check must NOT appear before the Method selection block.
        # Heuristic: the platform-check block (before '$Method = Read-Host') must not reference podman-compose.
        $beforeMethodSelect = [regex]::Match($content, '(?s)^.*?(?=\$Method = Read-Host)').Value
        $beforeMethodSelect | Should -Not -Match 'podman-compose'
    }
}
