# Install a Startup-folder shortcut that runs the BATCH watchdog (no Python supervisor).
# Pure user-level. No admin rights required.
#
# Reboot survival still requires Windows auto-logon for this user
# (Sysinternals Autologon or netplwiz).
#
# Usage:
#   powershell -ExecutionPolicy Bypass -File .\install_startup_shortcut_bat.ps1
#
# Remove:
#   Remove-Item "$env:APPDATA\Microsoft\Windows\Start Menu\Programs\Startup\ActionHubBackend.lnk"

$ErrorActionPreference = 'Stop'

$Root = Split-Path -Parent $MyInvocation.MyCommand.Definition
$Bat  = Join-Path $Root 'run_backend_watchdog.bat'
if (-not (Test-Path $Bat)) { Write-Error "Batch watchdog not found at $Bat"; exit 1 }

$StartupDir = [Environment]::GetFolderPath('Startup')
$LinkPath   = Join-Path $StartupDir 'ActionHubBackend.lnk'

$WScript  = New-Object -ComObject WScript.Shell
$Shortcut = $WScript.CreateShortcut($LinkPath)
$Shortcut.TargetPath       = $Bat
$Shortcut.WorkingDirectory = $Root
$Shortcut.WindowStyle      = 7    # minimized
$Shortcut.Description      = 'ActionHub backend (batch watchdog, auto-restart)'
$Shortcut.Save()

Write-Host "Installed startup shortcut: $LinkPath"
Write-Host "Target: $Bat"
Write-Host ""
Write-Host "For reboot survival without anyone signing in, enable Windows auto-logon"
Write-Host "for user '$env:USERNAME' via Sysinternals Autologon.exe or netplwiz."
