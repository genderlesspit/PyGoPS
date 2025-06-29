param (
    # Hardcoded GO LAUNCHER config only
    [switch]$force_go_install,
    [string]$go_version = "latest",
    [switch]$check_ports,
    [switch]$stop_existing,
    [switch]$background = $true,
    [int]$timeout_seconds = 0,
    [switch]$verbose,

    # Everything else is kwargs for Go
    [Parameter(ValueFromRemainingArguments=$true)]
    [string[]]$kwargs
)

$ErrorActionPreference = "Stop"

function Write-Log {
    param([string]$Message, [string]$Color = "White")
    if ($verbose) {
        Write-Host "[GO-LAUNCHER] $Message" -ForegroundColor $Color
    }
}

function Install-GoIfNeeded {
    if ($force_go_install -or -not (Get-Command go -ErrorAction SilentlyContinue)) {
        Write-Log "Installing Go..." "Yellow"

        try {
            if ($go_version -eq "latest") {
                $response = Invoke-RestMethod "https://api.github.com/repos/golang/go/tags" -UseBasicParsing
                $version = ($response | Where-Object { $_.name -match "^go\d+\.\d+\.\d+$" } | Select-Object -First 1).name -replace "go", ""
            } else {
                $version = $go_version
            }

            $downloadUrl = "https://go.dev/dl/go$version.windows-amd64.msi"
            $tempFile = "$env:TEMP\go$version.msi"

            Invoke-WebRequest $downloadUrl -OutFile $tempFile -UseBasicParsing
            Start-Process msiexec -ArgumentList "/i", $tempFile, "/quiet" -Wait

            $env:PATH += ";C:\Program Files\Go\bin"
            Remove-Item $tempFile -ErrorAction SilentlyContinue

            Write-Log "Go installed successfully" "Green"
        } catch {
            throw "Failed to install Go: $_"
        }
    }
}

function Test-PortAvailable {
    param([int]$Port)

    try {
        $listener = [System.Net.Sockets.TcpListener]::new([System.Net.IPAddress]::Any, $Port)
        $listener.Start()
        $listener.Stop()
        return $true
    } catch {
        return $false
    }
}

function Find-AvailablePort {
    param([int]$StartPort = 3000)

    for ($p = $StartPort; $p -le 9999; $p++) {
        if (Test-PortAvailable $p) {
            return $p
        }
    }
    throw "No available ports found"
}

function Parse-KwargsToGoArgs {
    param([string[]]$RawKwargs)

    $goArgs = @()
    $i = 0

    while ($i -lt $RawKwargs.Length) {
        $arg = $RawKwargs[$i]

        if ($arg.StartsWith("-")) {
            # This is a flag
            $flag = $arg

            # Check if next arg is a value (doesn't start with -)
            if (($i + 1) -lt $RawKwargs.Length -and -not $RawKwargs[$i + 1].StartsWith("-")) {
                $value = $RawKwargs[$i + 1]
                $goArgs += $flag, $value
                $i += 2
            } else {
                # Boolean flag
                $goArgs += $flag
                $i += 1
            }
        } else {
            # Standalone value
            $goArgs += $arg
            $i += 1
        }
    }

    return $goArgs
}

# Main execution
try {
    Write-Log "Starting Go launcher..." "Cyan"

    # Install Go if needed (launcher responsibility)
    Install-GoIfNeeded

    # Parse all kwargs into Go arguments
    $goArgs = Parse-KwargsToGoArgs $kwargs

    Write-Log "Parsed Go args: $($goArgs -join ' ')" "Gray"

    # Handle port management if requested (launcher responsibility)
    if ($check_ports) {
        # Extract port from kwargs if present
        $portIndex = [array]::IndexOf($goArgs, "-port")
        if ($portIndex -ge 0 -and ($portIndex + 1) -lt $goArgs.Length) {
            $port = [int]$goArgs[$portIndex + 1]

            if (-not (Test-PortAvailable $port)) {
                if ($stop_existing) {
                    Write-Log "Stopping existing process on port $port..." "Yellow"
                    $proc = Get-NetTCPConnection -LocalPort $port -ErrorAction SilentlyContinue
                    if ($proc) {
                        Stop-Process -Id $proc.OwningProcess -Force -ErrorAction SilentlyContinue
                    }
                } else {
                    $newPort = Find-AvailablePort $port
                    Write-Log "Port $port unavailable, using $newPort" "Yellow"
                    $goArgs[$portIndex + 1] = $newPort.ToString()
                }
            }
        }
    }

    # Build final Go command: go run + all kwargs
    $goCmd = @("run") + $goArgs

    Write-Log "Running: go $($goCmd -join ' ')" "Green"

    # Execute Go command
    if ($background) {
        $proc = Start-Process -FilePath "go" -ArgumentList $goCmd -PassThru -NoNewWindow
        Write-Host "✓ Go server started (PID: $($proc.Id))" -ForegroundColor Green

        # Keep the process alive
        $proc.WaitForExit()
    } else {
        Start-Process -FilePath "go" -ArgumentList $goCmd -Wait -NoNewWindow
    }

} catch {
    Write-Host "❌ Failed to start Go server: $_" -ForegroundColor Red
    exit 1
}