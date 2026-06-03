"""Run WF-21 tests and capture output to log file."""
import subprocess
import os
from pathlib import Path

# Change to action_hub directory
os.chdir(Path(__file__).parent)

# Create logs directory
logs_dir = Path(__file__).parent.parent / "logs"
logs_dir.mkdir(exist_ok=True)

# Run pytest
log_file = logs_dir / "wf21_tests.log"
with open(log_file, "w", encoding="utf-8") as f:
    result = subprocess.run(
        [
            r"..\..\.venv\Scripts\python.exe",
            "-m",
            "pytest",
            "tests/test_workflow_workbench.py",
            "-v",
            "--tb=short",
        ],
        stdout=f,
        stderr=subprocess.STDOUT,
    )

print(f"Tests completed with return code: {result.returncode}")
print(f"Log file: {log_file}")

# Show last 50 lines of log
with open(log_file, "r", encoding="utf-8") as f:
    lines = f.readlines()
    print("\n=== Last 50 lines of test output ===")
    print("".join(lines[-50:]))
