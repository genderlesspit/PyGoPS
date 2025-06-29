#Requires -Version 5.1

[CmdletBinding()]
param (
    [Parameter(Mandatory=$true, Position=0, HelpMessage="Path to the Go file to execute")]
    [ValidateScript({
        if (-not (Test-Path $_)) { throw "Go file not found: $_" }
        if (-not $_.EndsWith(".go")) { throw "File must have .go extension" }
        return $true
    })]
    [string]$GoFile,

    [Parameter(HelpMessage="Go arguments as JSON array (e.g., '[`"--port`", `"8080`", `"--verbose`"]')")]
    [string]$GoArgs = "[]",

    [Parameter(HelpMessage="Go version to install (default: latest)")]
    [string]$GoVersion = "latest",

    [Parameter(HelpMessage="Force Go installation even if already present")]
    [switch]$ForceGoInstall,

    [Parameter(HelpMessage="Enable server mode with port management")]
    [switch]$ServerMode,

    [Parameter(HelpMessage="Port for server mode (auto-detected from GoArgs if not specified)")]
    [ValidateRange(1, 65535)]
    [int]$Port = 0,

    [Parameter(HelpMessage="Kill existing processes on the target port")]
    [switch]$StopExisting,

    [Parameter(HelpMessage="Dry run - show what would be executed without running")]
    [switch]$DryRun
)

# Global script variables
$script:VerboseEnabled = $VerbosePreference -ne 'SilentlyContinue'

function Write-Log {
    param(
        [string]$Message,
        [ValidateSet("INFO", "SUCCESS", "WARNING", "ERROR", "DEBUG")]
        [string]$Level = "INFO"
    )

    if (-not $script:VerboseEnabled -and $Level -eq "DEBUG") {
        return
    }

    $colors = @{
        "INFO"    = "White"
        "SUCCESS" = "Green"
        "WARNING" = "Yellow"
        "ERROR"   = "Red"
        "DEBUG"   = "Gray"
    }

    $timestamp = Get-Date -Format "HH:mm:ss"
    $prefix = "[$timestamp] [$Level]"
    Write-Host "$prefix $Message" -ForegroundColor $colors[$Level]
}

function Test-PortAvailable {
    param([int]$PortNumber)

    try {
        $listener = [System.Net.Sockets.TcpListener]::new([System.Net.IPAddress]::Any, $PortNumber)
        $listener.Start()
        $listener.Stop()
        $listener.Dispose()
        return $true
    }
    catch {
        return $false
    }
}

function Find-AvailablePort {
    param([int]$StartPort = 3000)

    for ($p = $StartPort; $p -le 65535; $p++) {
        if (Test-PortAvailable -PortNumber $p) {
            Write-Log "Found available port: $p" -Level "SUCCESS"
            return $p
        }
    }
    throw "No available ports found in range $StartPort-65535"
}

function Stop-PortProcess {
    param([int]$PortNumber)

    Write-Log "Stopping processes on port $PortNumber" -Level "WARNING"

    try {
        $connections = Get-NetTCPConnection -LocalPort $PortNumber -State Listen -ErrorAction SilentlyContinue
        if (-not $connections) {
            Write-Log "No processes found on port $PortNumber" -Level "DEBUG"
            return
        }

        foreach ($conn in $connections) {
            $process = Get-Process -Id $conn.OwningProcess -ErrorAction SilentlyContinue
            if ($process) {
                Write-Log "Killing process: $($process.ProcessName) (PID: $($process.Id))" -Level "WARNING"
                if (-not $DryRun) {
                    Stop-Process -Id $process.Id -Force -ErrorAction SilentlyContinue
                }
            }
        }
    }
    catch {
        Write-Log "Error stopping port processes: $($_.Exception.Message)" -Level "ERROR"
    }
}

function Get-ProcessedArgs {
    param(
        [array]$Arguments,
        [bool]$IsServerMode,
        [int]$ExplicitPort
    )

    if (-not $IsServerMode) {
        return $Arguments
    }

    $args = $Arguments.Clone()
    $targetPort = $ExplicitPort

    # If no explicit port, try to find one in args
    if ($targetPort -eq 0) {
        for ($i = 0; $i -lt $args.Length - 1; $i++) {
            if ($args[$i] -in @("-port", "--port", "-p")) {
                try {
                    $targetPort = [int]$args[$i + 1]
                    break
                }
                catch {
                    Write-Log "Invalid port value in arguments: $($args[$i + 1])" -Level "WARNING"
                }
            }
        }
    }

    if ($targetPort -eq 0) {
        Write-Log "No port specified for server mode" -Level "DEBUG"
        return $args
    }

    Write-Log "Target port: $targetPort" -Level "DEBUG"

    if (-not (Test-PortAvailable -PortNumber $targetPort)) {
        if ($StopExisting) {
            Stop-PortProcess -PortNumber $targetPort
        }
        else {
            $newPort = Find-AvailablePort -StartPort $targetPort
            Write-Log "Replacing port $targetPort with $newPort" -Level "WARNING"

            # Update port in args
            for ($i = 0; $i -lt $args.Length - 1; $i++) {
                if ($args[$i] -in @("-port", "--port", "-p")) {
                    $args[$i + 1] = $newPort.ToString()
                    break
                }
            }
        }
    }

    return $args
}

function Install-GoRuntime {
    param(
        [string]$Version,
        [bool]$Force
    )

    $goInstalled = $null -ne (Get-Command go -ErrorAction SilentlyContinue)

    if ($goInstalled -and -not $Force) {
        $currentVersion = (go version 2>$null) -replace "go version go", "" -replace " .*", ""
        Write-Log "Go already installed: $currentVersion" -Level "SUCCESS"
        return
    }

    if ($DryRun) {
        Write-Log "[DRY RUN] Would install Go version: $Version" -Level "INFO"
        return
    }

    Write-Log "Installing Go..." -Level "INFO"

    try {
        $installVersion = $Version

        if ($installVersion -eq "latest") {
            Write-Log "Resolving latest Go version..." -Level "DEBUG"
            $response = Invoke-RestMethod "https://api.github.com/repos/golang/go/tags" -UseBasicParsing
            $latestTag = $response | Where-Object { $_.name -match "^go\d+\.\d+\.\d+$" } | Select-Object -First 1

            if (-not $latestTag) {
                throw "Could not determine latest Go version"
            }

            $installVersion = $latestTag.name -replace "go", ""
        }

        $downloadUrl = "https://go.dev/dl/go$installVersion.windows-amd64.msi"
        $tempFile = Join-Path $env:TEMP "go$installVersion.msi"

        Write-Log "Downloading Go $installVersion..." -Level "INFO"
        Invoke-WebRequest $downloadUrl -OutFile $tempFile -UseBasicParsing

        Write-Log "Installing Go $installVersion..." -Level "INFO"
        $process = Start-Process msiexec -ArgumentList "/i", $tempFile, "/quiet" -Wait -PassThru

        if ($process.ExitCode -ne 0) {
            throw "Go installation failed with exit code: $($process.ExitCode)"
        }

        # Update PATH for current session
        $goPath = "C:\Program Files\Go\bin"
        if ($env:PATH -notlike "*$goPath*") {
            $env:PATH += ";$goPath"
        }

        Remove-Item $tempFile -ErrorAction SilentlyContinue
        Write-Log "Go $installVersion installed successfully" -Level "SUCCESS"
    }
    catch {
        throw "Go installation failed: $($_.Exception.Message)"
    }
}

# Main execution
$ErrorActionPreference = "Stop"

try {
    # Parse JSON arguments
    try {
        $parsedArgs = ConvertFrom-Json $GoArgs
        if (-not ($parsedArgs -is [array])) {
            throw "GoArgs must be a JSON array"
        }
    }
    catch {
        throw "Invalid JSON in GoArgs parameter: $($_.Exception.Message)"
    }

    # Ensure Go is installed
    Install-GoRuntime -Version $GoVersion -Force $ForceGoInstall.IsPresent

    # Process arguments for server mode
    $processedArgs = Get-ProcessedArgs -Arguments $parsedArgs -IsServerMode $ServerMode.IsPresent -ExplicitPort $Port

    # Build command
    $command = @("run", $GoFile) + $processedArgs
    $commandStr = "go " + ($command -join " ")

    Write-Log "Executing: $commandStr" -Level "INFO"

    if ($DryRun) {
        Write-Log "[DRY RUN] Command would be executed" -Level "INFO"
        exit 0
    }

    # Execute Go command
    & go @command

    if ($LASTEXITCODE -eq 0) {
        Write-Log "Execution completed successfully" -Level "SUCCESS"
    }
    else {
        throw "Go execution failed with exit code: $LASTEXITCODE"
    }
}
catch {
    Write-Log "Error: $($_.Exception.Message)" -Level "ERROR"
    exit 1
}