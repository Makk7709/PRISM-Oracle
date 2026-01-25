# ╔══════════════════════════════════════════════════════════════════════════════╗
# ║                    PRISM + ORACLE — Portable Start (Windows)                 ║
# ║                                                                              ║
# ║  Démarrage en mode portable (sans Docker)                                    ║
# ║  Usage: .\start.ps1 [-Port PORT]                                             ║
# ║                                                                              ║
# ╚══════════════════════════════════════════════════════════════════════════════╝

param(
    [int]$Port = 5050
)

$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectDir = Split-Path -Parent (Split-Path -Parent $ScriptDir)
$VenvDir = Join-Path $ProjectDir "venv"
$DataDir = Join-Path $ProjectDir "data"
$LogsDir = Join-Path $ProjectDir "logs"
$AuditDir = Join-Path $ProjectDir "audit"
$PidFile = Join-Path $ProjectDir "oracle.pid"

function Write-Log {
    param([string]$Level, [string]$Message)
    $colors = @{
        "INFO" = "Cyan"
        "OK" = "Green"
        "WARN" = "Yellow"
        "ERROR" = "Red"
    }
    Write-Host "[$Level] $Message" -ForegroundColor $colors[$Level]
}

function Test-Python {
    $pythonCmd = $null
    
    if (Get-Command "python" -ErrorAction SilentlyContinue) {
        $pythonCmd = "python"
    } elseif (Get-Command "python3" -ErrorAction SilentlyContinue) {
        $pythonCmd = "python3"
    } else {
        Write-Log "ERROR" "Python not found"
        exit 1
    }
    
    $version = & $pythonCmd --version 2>&1
    Write-Log "OK" "Python found: $version"
    return $pythonCmd
}

function Setup-Venv {
    param([string]$PythonCmd)
    
    if (-not (Test-Path $VenvDir)) {
        Write-Log "INFO" "Creating virtual environment..."
        & $PythonCmd -m venv $VenvDir
        Write-Log "OK" "Virtual environment created"
    }
    
    # Activate venv
    $activateScript = Join-Path $VenvDir "Scripts\Activate.ps1"
    . $activateScript
    
    # Install dependencies if needed
    $installedFlag = Join-Path $VenvDir ".installed"
    if (-not (Test-Path $installedFlag)) {
        Write-Log "INFO" "Installing dependencies..."
        pip install --upgrade pip wheel
        pip install -r (Join-Path $ProjectDir "requirements.txt")
        New-Item $installedFlag -ItemType File | Out-Null
        Write-Log "OK" "Dependencies installed"
    }
}

function Setup-Directories {
    @($DataDir, $LogsDir, $AuditDir) | ForEach-Object {
        if (-not (Test-Path $_)) {
            New-Item $_ -ItemType Directory | Out-Null
        }
    }
    Write-Log "OK" "Directories created"
}

function Test-AlreadyRunning {
    if (Test-Path $PidFile) {
        $pid = Get-Content $PidFile
        $process = Get-Process -Id $pid -ErrorAction SilentlyContinue
        if ($process) {
            Write-Log "WARN" "Oracle is already running (PID: $pid)"
            Write-Log "INFO" "Use .\stop.ps1 to stop it first"
            exit 1
        } else {
            Remove-Item $PidFile
        }
    }
}

function Start-Oracle {
    Write-Log "INFO" "Starting Oracle on port $Port..."
    
    Set-Location $ProjectDir
    
    # Set environment
    $env:DATA_DIR = $DataDir
    $env:LOGS_DIR = $LogsDir
    $env:AUDIT_DIR = $AuditDir
    $env:ORACLE_ENV = "production"
    $env:OFFLINE_MODE = if ($env:OFFLINE_MODE) { $env:OFFLINE_MODE } else { "true" }
    
    # Start in background
    $logFile = Join-Path $LogsDir "oracle.log"
    $process = Start-Process -FilePath "python" -ArgumentList "run_ui.py", "--port", $Port `
        -RedirectStandardOutput $logFile -RedirectStandardError $logFile `
        -WindowStyle Hidden -PassThru
    
    $process.Id | Out-File $PidFile
    
    Write-Log "OK" "Oracle started (PID: $($process.Id))"
}

function Wait-ForReady {
    Write-Log "INFO" "Waiting for Oracle to be ready..."
    
    $maxAttempts = 30
    $attempt = 0
    
    while ($attempt -lt $maxAttempts) {
        try {
            $response = Invoke-WebRequest -Uri "http://127.0.0.1:$Port/healthz" -TimeoutSec 2 -ErrorAction SilentlyContinue
            if ($response.StatusCode -eq 200) {
                Write-Log "OK" "Oracle is ready"
                return $true
            }
        } catch {}
        
        $attempt++
        Write-Host "." -NoNewline
        Start-Sleep -Seconds 1
    }
    
    Write-Host ""
    Write-Log "ERROR" "Oracle did not start in time"
    return $false
}

function Show-Info {
    Write-Host ""
    Write-Host "═══════════════════════════════════════════════════════════════════════" -ForegroundColor Green
    Write-Host "ORACLE STARTED (Portable Mode)" -ForegroundColor Green
    Write-Host "═══════════════════════════════════════════════════════════════════════" -ForegroundColor Green
    Write-Host ""
    Write-Host "  URL:      http://127.0.0.1:$Port"
    Write-Host "  Health:   http://127.0.0.1:$Port/healthz"
    Write-Host "  Logs:     $LogsDir\oracle.log"
    Write-Host ""
    Write-Host "  Stop:     .\stop.ps1"
    Write-Host "  Status:   .\status.ps1"
    Write-Host ""
    Write-Host "═══════════════════════════════════════════════════════════════════════" -ForegroundColor Green
}

# Main
Write-Host ""
Write-Host "╔══════════════════════════════════════════════════════════════════════╗"
Write-Host "║              PRISM + ORACLE — Portable Mode (Windows)                ║"
Write-Host "╚══════════════════════════════════════════════════════════════════════╝"
Write-Host ""

$pythonCmd = Test-Python
Test-AlreadyRunning
Setup-Venv -PythonCmd $pythonCmd
Setup-Directories
Start-Oracle

if (Wait-ForReady) {
    Show-Info
} else {
    exit 1
}
