@echo off
REM ActionHub backend watchdog (pure batch).
REM No admin. No Python supervisor. Auto-restarts the backend if it exits.
REM Place a shortcut to this file in the user's Startup folder for reboot survival
REM (requires Windows auto-logon to actually trigger after reboot).

setlocal
set "ROOT=%~dp0"
set "ROOT=%ROOT:~0,-1%"
set "PY=%ROOT%\.venv\Scripts\python.exe"
set "WSGI=%ROOT%\action_hub\wsgi.py"
set "LOG=%ROOT%\logs\backend_watchdog.log"

if not exist "%ROOT%\logs" mkdir "%ROOT%\logs"
if not exist "%PY%"   ( echo [FATAL] venv python missing: %PY% >> "%LOG%" & exit /b 1 )
if not exist "%WSGI%" ( echo [FATAL] wsgi missing: %WSGI%      >> "%LOG%" & exit /b 1 )

:loop
echo [%date% %time%] Launching backend... >> "%LOG%"
pushd "%ROOT%\action_hub"
"%PY%" "%WSGI%" >> "%LOG%" 2>&1
set "RC=%ERRORLEVEL%"
popd
echo [%date% %time%] Backend exited code=%RC%. Restarting in 5s... >> "%LOG%"
timeout /t 5 /nobreak > nul
goto loop
