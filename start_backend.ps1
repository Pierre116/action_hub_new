# Start ActionHub backend with auto-restart watchdog.
# Safe, user-level. No admin required.
#
# Usage (from repo root):
#   powershell -ExecutionPolicy Bypass -File .\start_backend.ps1
#
# Optional: minimize the window manually after launch.

$ErrorActionPreference = 'Stop'

$Root       = Split-Path -Parent $MyInvocation.MyCommand.Definition
$VenvPython = Join-Path $Root '.venv\Scripts\python.exe'
$Watchdog   = Join-Path $Root 'run_backend_watchdog.py'

if (-not (Test-Path $VenvPython)) {
    Write-Error "venv python not found at $VenvPython. Run rebuild_and_launch.py --no-launch first."
    exit 1
}
if (-not (Test-Path $Watchdog)) {
    Write-Error "Watchdog script not found at $Watchdog"
    exit 1
}

Set-Location $Root
Write-Host "Starting ActionHub backend watchdog..."
& $VenvPython $Watchdog
