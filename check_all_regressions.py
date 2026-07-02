"""Run all detector regression checks with one command.

Usage:
  .venv\\Scripts\\python.exe check_all_regressions.py
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def run_check(script_name: str) -> int:
    cmd = [sys.executable, script_name]
    print(f"\n=== Running {script_name} ===")
    result = subprocess.run(cmd, cwd=Path(__file__).resolve().parent)
    if result.returncode == 0:
        print(f"=== PASS: {script_name} ===")
    else:
        print(f"=== FAIL: {script_name} (exit {result.returncode}) ===")
    return result.returncode


def main() -> int:
    checks = [
        "check_spam_regression.py",
        "check_phishing_regression.py",
    ]

    failed = []
    for check in checks:
        code = run_check(check)
        if code != 0:
            failed.append(check)

    if failed:
        print("\nOverall result: FAILED")
        print("Failed suites:")
        for name in failed:
            print(f" - {name}")
        return 1

    print("\nOverall result: PASSED")
    print("All regression suites passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
