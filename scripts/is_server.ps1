param (
    [switch]$check_ports = $true,
    [switch]$stop_existing = $true,
    [switch]$verbose,
    [string[]]$go_args
)

$ErrorActionPreference = "Stop"

function Write-Log {
    param([string]$Message, [string]$Color = "White")
    if ($verbose) {
        Write-Host "[IS-SERVER] $Message" -ForegroundColor $Color
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

function Stop-PortProcess {
    param([int]$Port)

    Write-Log "Stopping existing process on port $Port..." "Yellow"

    try {
        # Get TCP connections on the port
        $connections = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue

        foreach ($conn in $connections) {
            $processId = $conn.OwningProcess
            $process = Get-Process -Id $processId -ErrorAction SilentlyContinue

            if ($process) {
                Write-Log "Killing process: $($process.ProcessName) (PID: $processId)" "Red"
                Stop-Process -Id $processId -Force -ErrorAction SilentlyContinue
                Start-Sleep -Milliseconds 500  # Give it time to die
            }
        }

        # Double-check with netstat and taskkill as backup
        $netstatOutput = netstat -ano | Select-String ":$Port "
        foreach ($line in $netstatOutput) {
            if ($line -match "\s+(\d+)$") {
                $pid = $matches[1]
                Write-Log "Backup kill PID: $pid" "Red"
                Start-Process taskkill -ArgumentList "/F", "/PID", $pid -NoNewWindow -Wait -ErrorAction SilentlyContinue
            }
        }

        Write-Log "Port $Port cleared" "Green"
    } catch {
        Write-Log "Warning: Could not clear port $Port`: $_" "Yellow"
    }
}

# Main server logic
try {
    Write-Log "Server-specific processing..." "Cyan"

    # Handle port management for servers
    if ($check_ports) {
        # Extract port from Go args if present
        $portIndex = [array]::IndexOf($go_args, "-port")
        if ($portIndex -ge 0 -and ($portIndex + 1) -lt $go_args.Length) {
            $port = [int]$go_args[$portIndex + 1]

            Write-Log "Checking port $port availability..." "Blue"

            if (-not (Test-PortAvailable $port)) {
                if ($stop_existing) {
                    Stop-PortProcess $port

                    # Verify port is now available
                    Start-Sleep -Seconds 1
                    if (-not (Test-PortAvailable $port)) {
                        throw "Failed to clear port $port"
                    }
                } else {
                    $newPort = Find-AvailablePort $port
                    Write-Log "Port $port unavailable, using $newPort" "Yellow"
                    $go_args[$portIndex + 1] = $newPort.ToString()
                }
            } else {
                Write-Log "Port $port is available" "Green"
            }
        }
    }

    # Build final Go server command
    $goCmd = @("run")

    # Find the Go file to run
    $goFileFound = $false
    foreach ($arg in $go_args) {
        if ($arg -like "*.go") {
            $goCmd += $arg
            $goFileFound = $true
            break
        }
    }

    # If no .go file specified, search for common files
    if (-not $goFileFound) {
        $searchPaths = @("main.go", "cmd/main.go", "server/main.go", "./go_dummy.go")
        foreach ($path in $searchPaths) {
            if (Test-Path $path) {
                $goCmd += $path
                Write-Log "Found Go file: $path" "Green"
                $goFileFound = $true
                break
            }
        }
    }

    if (-not $goFileFound) {
        throw "No Go file specified and none found in common locations"
    }

    # Add remaining args (excluding the .go file we already added)
    foreach ($arg in $go_args) {
        if ($arg -notlike "*.go") {
            $goCmd += $arg
        }
    }

    Write-Log "Running server: go $($goCmd -join ' ')" "Green"

    # Execute Go server
    $proc = Start-Process -FilePath "go" -ArgumentList $goCmd -PassThru -NoNewWindow

    Write-Host "🚀 Go server started (PID: $($proc.Id))" -ForegroundColor Green

    # Extract and display server URL
    $portIndex = [array]::IndexOf($go_args, "-port")
    if ($portIndex -ge 0 -and ($portIndex + 1) -lt $go_args.Length) {
        $serverPort = $go_args[$portIndex + 1]
        $hostIndex = [array]::IndexOf($go_args, "-host")
        $serverHost = if ($hostIndex -ge 0 -and ($hostIndex + 1) -lt $go_args.Length) {
            $go_args[$hostIndex + 1]
        } else {
            "localhost"
        }

        Write-Host "🌐 Server URL: http://${serverHost}:${serverPort}" -ForegroundColor Cyan
        Write-Host "💚 Health check: http://${serverHost}:${serverPort}/health" -ForegroundColor Green
    }

    # Keep the process alive
    $proc.WaitForExit()

} catch {
    Write-Host "❌ Server failed: $_" -ForegroundColor Red
    exit 1
}