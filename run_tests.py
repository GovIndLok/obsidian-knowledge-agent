#!/usr/bin/env python3
"""
Unified Test and Evaluation Runner.

Runs unit tests, integration tests, and custom evaluations sequentially.
Exits with code 0 if all suites pass, or 1 if any suite fails.
"""

import os
import sys
import subprocess

# Ensure we print with nice colors if supported
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
BOLD = "\033[1m"
RESET = "\033[0m"

def print_header(title: str):
    print(f"\n{BOLD}{YELLOW}======================================================================")
    print(f"  {title}")
    print(f"======================================================================{RESET}\n")

def run_suite(name: str, cmd: list[str]) -> bool:
    print_header(f"Running: {name}")
    print(f"Command: {' '.join(cmd)}\n")
    try:
        # Run subprocess and stream output directly to stdout/stderr
        result = subprocess.run(cmd, check=False)
        if result.returncode == 0:
            print(f"\n{BOLD}{GREEN}✓ {name} passed successfully!{RESET}")
            return True
        else:
            print(f"\n{BOLD}{RED}✗ {name} failed with return code {result.returncode}.{RESET}")
            return False
    except Exception as e:
        print(f"\n{BOLD}{RED}✗ Failed to execute {name}: {e}{RESET}")
        return False

def main():
    # Force output buffering off so prints stream in order
    sys.stdout.reconfigure(line_buffering=True)
    
    python_bin = sys.executable

    # Define the execution stages
    stages = [
        ("Unit Tests", [python_bin, "-m", "pytest", "tests/unit"]),
        ("Integration Tests", [python_bin, "-m", "pytest", "tests/integration"]),
        ("Evaluation Suite", [python_bin, "tests/eval/run_eval.py"]),
    ]

    results = {}
    overall_success = True

    for name, cmd in stages:
        success = run_suite(name, cmd)
        results[name] = success
        if not success:
            overall_success = False
            # We fail-fast as per sequential "one by one" requirements
            break

    print_header("SUMMARY OF RESULTS")
    for name, _ in stages:
        if name in results:
            status = f"{GREEN}PASSED{RESET}" if results[name] else f"{RED}FAILED{RESET}"
        else:
            status = f"{YELLOW}SKIPPED (Prior failure){RESET}"
        print(f"  {name:<20} : {status}")

    print(f"\n{BOLD}======================================================================{RESET}")
    if overall_success:
        print(f"{BOLD}{GREEN}🎉 All tests and evaluations passed successfully!{RESET}")
        sys.exit(0)
    else:
        print(f"{BOLD}{RED}❌ Some tests or evaluations failed. Please check the logs above.{RESET}")
        sys.exit(1)

if __name__ == "__main__":
    main()
