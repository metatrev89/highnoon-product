#!/usr/bin/env python3
"""
Run all crawler pings in sequence: Bing (IndexNow) then Google.
Called automatically by GitHub Actions after deploy.

Usage:
    python3 scripts/ping_all.py
"""

import subprocess
import sys
from pathlib import Path

scripts = Path(__file__).parent

for script in ["ping_bing.py", "ping_google.py"]:
    print(f"\n{'='*50}")
    print(f"Running {script}...")
    print('='*50)
    result = subprocess.run([sys.executable, str(scripts / script)])
    if result.returncode != 0:
        print(f"WARNING: {script} exited with code {result.returncode}")

print("\nAll pings complete.")
