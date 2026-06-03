from __future__ import annotations

import argparse
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path


def run_step(command: list[str], cwd: Path, log_file: Path, title: str) -> None:
    print(f"[RUN] {title}")
    print(f"      cwd={cwd}")
    print(f"      cmd={' '.join(command)}")
    with log_file.open("a", encoding="utf-8") as log:
        log.write(f"\n=== {title} ===\n")
        log.write(f"cwd: {cwd}\n")
        log.write(f"cmd: {' '.join(command)}\n")
        completed = subprocess.run(
            command,
            cwd=str(cwd),
            stdout=log,
            stderr=subprocess.STDOUT,
            check=False,
        )
        log.write(f"exit_code: {completed.returncode}\n")
    if completed.returncode != 0:
        raise RuntimeError(f"Step failed ({title}), exit code {completed.returncode}. See {log_file}")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Rebuild backend/frontend and launch ActionHub by default.",
    )
    parser.add_argument("--skip-backend", action="store_true", help="Skip backend dependency install")
    parser.add_argument("--skip-frontend", action="store_true", help="Skip frontend install/build")
    parser.add_argument("--init-db", action="store_true", help="Run init_db.py")
    parser.add_argument("--seed", action="store_true", help="Run seed_data.py (implies --init-db if DB missing)")
    parser.add_argument("--no-launch", action="store_true", help="Do not launch app.py after rebuild")
    args = parser.parse_args()

    root = Path(__file__).resolve().parent
    app_dir = root / "action_hub"
    frontend_dir = app_dir / "frontend"
    logs_dir = root / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = logs_dir / f"rebuild_{timestamp}.log"

    venv_python = root / ".venv" / "Scripts" / "python.exe"
    python_exe = str(venv_python if venv_python.exists() else Path(sys.executable))

    npm_cmd = "npm.cmd" if os.name == "nt" else "npm"

    try:
        if not args.skip_backend:
            run_step(
                [python_exe, "-m", "pip", "install", "-r", "requirements.txt"],
                app_dir,
                log_file,
                "Install backend dependencies",
            )

        db_file = app_dir / "db" / "actionhub.db"
        should_init_db = args.init_db or (args.seed and not db_file.exists())
        if should_init_db:
            run_step([python_exe, "init_db.py"], app_dir, log_file, "Initialize database")

        if args.seed:
            run_step([python_exe, "seed_data.py"], app_dir, log_file, "Seed database")

        if not args.skip_frontend:
            run_step([npm_cmd, "install"], frontend_dir, log_file, "Install frontend dependencies")
            run_step([npm_cmd, "run", "build"], frontend_dir, log_file, "Build frontend")

        if args.no_launch:
            print(f"[OK] Rebuild completed. Log: {log_file}")
            return 0

        print(f"[OK] Rebuild completed. Log: {log_file}")
        print("[RUN] Launch backend app")
        subprocess.run([python_exe, "app.py"], cwd=str(app_dir), check=False)
        return 0
    except Exception as error:
        print(f"[ERROR] {error}")
        print(f"[HINT] Check log: {log_file}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
