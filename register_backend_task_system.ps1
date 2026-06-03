# Register the ActionHub backend as a SYSTEM-startup Scheduled Task.
# REQUIRES ADMIN. Run from an elevated PowerShell.
#
# Effect: at every machine boot, Windows launches the watchdog under the
# SYSTEM account (no interactive logon needed). The watchdog keeps the
# backend running and auto-restarts it on crash.
#
# Usage (elevated PowerShell, from repo root):
#   powershell -ExecutionPolicy Bypass -File .\register_backend_task_system.ps1
#
# Manage:
#   Start now:    Start-ScheduledTask  -TaskName 'ActionHubBackendSystem'
#   Stop:         Stop-ScheduledTask   -TaskName 'ActionHubBackendSystem'
#   Status:       Get-ScheduledTask    -TaskName 'ActionHubBackendSystem' | Get-ScheduledTaskInfo
#   Remove:       Unregister-ScheduledTask -TaskName 'ActionHubBackendSystem' -Confirm:$false

$ErrorActionPreference = 'Stop'

# Verify elevation
$current = [Security.Principal.WindowsIdentity]::GetCurrent()
$principal = New-Object Security.Principal.WindowsPrincipal($current)
if (-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    Write-Error "This script must be run from an elevated (Administrator) PowerShell."
    exit 1
}

$TaskName   = 'ActionHubBackendSystem'
$Root       = Split-Path -Parent $MyInvocation.MyCommand.Definition
$VenvPython = Join-Path $Root '.venv\Scripts\python.exe'
$Watchdog   = Join-Path $Root 'run_backend_watchdog.py'

if (-not (Test-Path $VenvPython)) { Write-Error "venv python not found at $VenvPython"; exit 1 }
if (-not (Test-Path $Watchdog))   { Write-Error "Watchdog not found at $Watchdog";       exit 1 }

$Action = New-ScheduledTaskAction `
    -Execute $VenvPython `
    -Argument ('"{0}"' -f $Watchdog) `
    -WorkingDirectory $Root

$Trigger = New-ScheduledTaskTrigger -AtStartup

$Settings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -StartWhenAvailable `
    -RestartCount 999 `
    -RestartInterval (New-TimeSpan -Minutes 1) `
    -ExecutionTimeLimit (New-TimeSpan -Days 0) `
    -MultipleInstances IgnoreNew

# Run as SYSTEM so it works without anyone logged in
$Principal = New-ScheduledTaskPrincipal `
    -UserId 'SYSTEM' `
    -LogonType ServiceAccount `
    -RunLevel Highest

$existing = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
if ($existing) {
    Write-Host "Removing existing task '$TaskName'..."
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
}

Register-ScheduledTask `
    -TaskName $TaskName `
    -Action $Action `
    -Trigger $Trigger `
    -Settings $Settings `
    -Principal $Principal `
    -Description 'ActionHub backend (waitress) supervised by watchdog. Starts at boot under SYSTEM. Auto-restarts on failure.'

Write-Host ""
Write-Host "Registered SYSTEM-level task '$TaskName'. It will run at every boot."
Write-Host "Start it now with:   Start-ScheduledTask -TaskName '$TaskName'"
Write-Host "Inspect logs at:     $Root\logs\backend_watchdog.log"
