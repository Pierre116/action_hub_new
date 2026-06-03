#!/usr/bin/env python
import subprocess
import os
import sys

# Change to action_hub directory
os.chdir("C:/Users/leung/Documents/Digitalization/actionhub/action_hub")

# Run Flask dev server
python_exe = "../.venv/Scripts/python.exe"

print("Starting Flask dev server on http://localhost:5000")
print("Working directory:", os.getcwd())
print("Python executable:", python_exe)

# Run with shell=True to see output
result = subprocess.run(
    f'"{python_exe}" app.py',
    shell=True,
    capture_output=False
)
