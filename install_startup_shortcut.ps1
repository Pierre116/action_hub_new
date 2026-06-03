# Install ActionHub backend auto-start in the current user's Startup folder.
# Pure user-level. No admin rights required.
#
# Effect: at every interactive logon of THIS user, Windows launches the
# watchdog (which keeps the backend running and auto-restarts on crash).
#
# To survive a full server REBOOT without anyone clicking Login, you also
# need Windows auto-logon for this user. Auto-logon is configured via
# Sysinternals 'Autologon.exe' (recommended) or the Netplwiz checkbox
# "Users must enter a user name and password to use this computer".
# Those steps are not scripted here because they store a credential and
# should be done interactively by you.
#
# Usage (from repo root):
#   powershell -ExecutionPolicy Bypass -File .\install_startup_shortcut.ps1
#
# Remove:
#   Remove-Item "$env:APPDATA\Microsoft\Windows\Start Menu\Programs\Startup\ActionHubBackend.lnk"

$ErrorActionPreference = 'Stop'

$Root       = Split-Path -Parent $MyInvocation.MyCommand.Definition
$VenvPython = Join-Path $Root '.venv\Scripts\pythonw.exe'   # pythonw = no console window
if (-not (Test-Path $VenvPython)) {
    $VenvPython = Join-Path $Root '.venv\Scripts\python.exe'
}
$Watchdog   = Join-Path $Root 'run_backend_watchdog.py'

if (-not (Test-Path $VenvPython)) {
    Write-Error "venv python not found at $VenvPython"
    exit 1
}
if (-not (Test-Path $Watchdog)) {
    Write-Error "Watchdog script not found at $Watchdog"
    exit 1
}

$StartupDir = [Environment]::GetFolderPath('Startup')
$LinkPath   = Join-Path $StartupDir 'ActionHubBackend.lnk'

$WScript = New-Object -ComObject WScript.Shell
$Shortcut = $WScript.CreateShortcut($LinkPath)
$Shortcut.TargetPath       = $VenvPython
$Shortcut.Arguments        = '"' + $Watchdog + '"'
$Shortcut.WorkingDirectory = $Root
$Shortcut.WindowStyle      = 7   # minimized
$Shortcut.Description      = 'ActionHub backend watchdog (auto-restart)'
$Shortcut.Save()

Write-Host "Installed startup shortcut: $LinkPath"
Write-Host ""
Write-Host "NEXT STEPS for survival across a full server reboot:"
Write-Host "  1. Configure Windows auto-logon for user '$env:USERNAME' using one of:"
Write-Host "       - Sysinternals Autologon.exe   (recommended, encrypts password)"
Write-Host "       - netplwiz  (uncheck 'Users must enter a user name and password')"
Write-Host "  2. Reboot once and confirm the watchdog window appears minimized."
Write-Host "  3. Check logs/backend_watchdog.log to verify the backend started."
