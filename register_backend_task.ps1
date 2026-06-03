# Register a per-user Scheduled Task that starts the ActionHub backend
# watchdog automatically at user logon. No admin rights required (creates
# the task under the current user's Task Scheduler tree).
#
# Usage (from repo root, in PowerShell):
#   powershell -ExecutionPolicy Bypass -File .\register_backend_task.ps1
#
# After registration:
#   Start now:    Start-ScheduledTask  -TaskName 'ActionHubBackend'
#   Stop:         Stop-ScheduledTask   -TaskName 'ActionHubBackend'
#   Status:       Get-ScheduledTask    -TaskName 'ActionHubBackend'
#   Remove:       Unregister-ScheduledTask -TaskName 'ActionHubBackend' -Confirm:$false
#
# Notes:
# - The task triggers at logon of the current user. It does NOT run while no
#   user is logged in (that would require admin + 'run whether logged on or
#   not'). If the server is always logged in as this user, this is enough.
# - If the watchdog or backend dies, the task scheduler is configured to
#   restart it automatically.

$ErrorActionPreference = 'Stop'

$TaskName   = 'ActionHubBackend'
$Root       = Split-Path -Parent $MyInvocation.MyCommand.Definition
$VenvPython = Join-Path $Root '.venv\Scripts\python.exe'
$Watchdog   = Join-Path $Root 'run_backend_watchdog.py'

if (-not (Test-Path $VenvPython)) {
    Write-Error "venv python not found at $VenvPython"
    exit 1
}
if (-not (Test-Path $Watchdog)) {
    Write-Error "Watchdog script not found at $Watchdog"
    exit 1
}

$Action = New-ScheduledTaskAction `
    -Execute $VenvPython `
    -Argument ('"{0}"' -f $Watchdog) `
    -WorkingDirectory $Root

$Trigger = New-ScheduledTaskTrigger -AtLogOn -User $env:USERNAME

$Settings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -StartWhenAvailable `
    -RestartCount 999 `
    -RestartInterval (New-TimeSpan -Minutes 1) `
    -ExecutionTimeLimit (New-TimeSpan -Days 0) `
    -MultipleInstances IgnoreNew

$Principal = New-ScheduledTaskPrincipal `
    -UserId "$env:USERDOMAIN\$env:USERNAME" `
    -LogonType Interactive `
    -RunLevel Limited

# Remove existing task if present
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
    -Description 'ActionHub backend (waitress) supervised by watchdog. Auto-restarts on failure.'

Write-Host ""
Write-Host "Registered scheduled task '$TaskName' for user $env:USERNAME."
Write-Host "Start now with:   Start-ScheduledTask -TaskName '$TaskName'"
Write-Host "Check status:     Get-ScheduledTask  -TaskName '$TaskName' | Get-ScheduledTaskInfo"
