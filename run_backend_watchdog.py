r"""
ActionHub backend watchdog.

Runs the Waitress-backed Flask app (action_hub/wsgi.py) and automatically
restarts it if it exits. Designed for a Windows web server where you may not
have admin rights to install a real service.

Usage:
    .\.venv\Scripts\python.exe .\run_backend_watchdog.py

Behavior:
- Launches the backend via the project venv python.
- If the backend process exits (crash, error, manual kill), waits a short
  cooldown and restarts it.
- If the backend exits too quickly repeatedly (crash loop), backoff grows up
  to MAX_BACKOFF seconds.
- Writes a rolling log under logs/backend_watchdog.log.
- Catches Ctrl+C to perform a clean shutdown of the child process.

This script does NOT rebuild dependencies. Rebuild only when code or deps
change:
    .\.venv\Scripts\python.exe .\rebuild_and_launch.py --no-launch
"""
from __future__ import annotations

import os
import signal
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent
APP_DIR = ROOT / "action_hub"
VENV_PYTHON = ROOT / ".venv" / "Scripts" / "python.exe"
WSGI_SCRIPT = APP_DIR / "wsgi.py"
LOGS_DIR = ROOT / "logs"
LOG_FILE = LOGS_DIR / "backend_watchdog.log"

MIN_HEALTHY_SECONDS = 30  # below this, treat as crash and back off
INITIAL_BACKOFF = 5
MAX_BACKOFF = 120


def log(message: str) -> None:
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{timestamp}] {message}"
    print(line, flush=True)
    try:
        with LOG_FILE.open("a", encoding="utf-8") as f:
            f.write(line + "\n")
    except OSError:
        pass


def resolve_python() -> str:
    if VENV_PYTHON.exists():
        return str(VENV_PYTHON)
    return sys.executable


def main() -> int:
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    if not WSGI_SCRIPT.exists():
        log(f"FATAL: wsgi entry not found: {WSGI_SCRIPT}")
        return 1

    python_exe = resolve_python()
    log(f"Watchdog starting. python={python_exe} wsgi={WSGI_SCRIPT}")

    backoff = INITIAL_BACKOFF
    current: subprocess.Popen | None = None

    def shutdown(signum, frame):  # noqa: ARG001
        log(f"Received signal {signum}, shutting down child process...")
        if current and current.poll() is None:
            try:
                current.terminate()
                try:
                    current.wait(timeout=15)
                except subprocess.TimeoutExpired:
                    current.kill()
            except Exception as exc:  # noqa: BLE001
                log(f"Error stopping child: {exc}")
        log("Watchdog stopped.")
        sys.exit(0)

    signal.signal(signal.SIGINT, shutdown)
    try:
        signal.signal(signal.SIGTERM, shutdown)
    except (AttributeError, ValueError):
        pass

    while True:
        start_time = time.time()
        log("Launching backend...")
        try:
            current = subprocess.Popen(
                [python_exe, str(WSGI_SCRIPT)],
                cwd=str(APP_DIR),
            )
        except Exception as exc:  # noqa: BLE001
            log(f"Failed to spawn backend: {exc}")
            time.sleep(backoff)
            backoff = min(backoff * 2, MAX_BACKOFF)
            continue

        exit_code = current.wait()
        elapsed = time.time() - start_time
        log(f"Backend exited code={exit_code} after {elapsed:.1f}s")

        if elapsed >= MIN_HEALTHY_SECONDS:
            # Ran long enough -> treat as healthy run, reset backoff
            backoff = INITIAL_BACKOFF
        else:
            log(f"Short run detected; backing off {backoff}s before restart")

        time.sleep(backoff)
        if elapsed < MIN_HEALTHY_SECONDS:
            backoff = min(backoff * 2, MAX_BACKOFF)


if __name__ == "__main__":
    raise SystemExit(main())
