#!/usr/bin/env python3
"""
Analyze test failures and categorize them.

This script parses pytest output to categorize test failures into:
- Real Bug: Actual application bugs
- Environment Issue: Missing dependencies or configuration
- Flaky Test: Intermittent failures
- Obsolete Test: Tests for removed/refactored code
"""

import re
import subprocess
import sys
from collections import defaultdict
from pathlib import Path


def run_pytest_collect():
    """Run pytest collection to get all test information."""
    result = subprocess.run(
        ["python", "-m", "pytest", "tests/", "--collect-only", "-q"],
        capture_output=True,
        text=True,
        cwd=Path(__file__).parent.parent
    )
    return result.stdout


def analyze_failure_file(filepath: Path) -> dict:
    """
    Analyze a file containing test failures.

    Returns dict with categories and counts.
    """
    if not filepath.exists():
        print(f"Error: {filepath} not found")
        return {}

    failures = filepath.read_text().strip().split("\n")

    categories = {
        "ERROR": [],
        "FAILED": [],
    }

    for line in failures:
        if "ERROR" in line:
            categories["ERROR"].append(line)
        elif "FAILED" in line:
            categories["FAILED"].append(line)

    return categories


def categorize_by_pattern(failures: list) -> dict:
    """Categorize failures by file pattern."""
    by_file = defaultdict(list)

    for failure in failures:
        # Extract file path
        match = re.search(r"tests/([^:]+)::", failure)
        if match:
            file_path = match.group(1)
            by_file[file_path].append(failure)

    return dict(by_file)


def main():
    failures_file = Path(__file__).parent.parent / "failures-list.txt"

    categories = analyze_failure_file(failures_file)

    print("=" * 80)
    print("TEST FAILURE ANALYSIS")
    print("=" * 80)
    print()

    # Summary
    total_errors = len(categories["ERROR"])
    total_failed = len(categories["FAILED"])
    total = total_errors + total_failed

    print(f"Total Failures: {total}")
    print(f"  - ERRORS (collection failures): {total_errors}")
    print(f"  - FAILED (test execution failures): {total_failed}")
    print()

    # Group by file for ERRORs
    print("=" * 80)
    print("ERRORS (Collection Failures) - Likely Environment Issues or Obsolete Tests")
    print("=" * 80)
    error_by_file = categorize_by_pattern(categories["ERROR"])
    for filepath, failures in sorted(error_by_file.items()):
        print(f"\n{filepath}: {len(failures)} errors")
        for f in failures[:3]:  # Show first 3
            print(f"  - {f.split('::')[-1][:60]}")
        if len(failures) > 3:
            print(f"  ... and {len(failures) - 3} more")

    print()
    print("=" * 80)
    print("FAILED (Test Execution Failures) - By Module")
    print("=" * 80)
    failed_by_file = categorize_by_pattern(categories["FAILED"])

    # Group by module
    by_module = defaultdict(int)
    for filepath in failed_by_file:
        module = filepath.split("/")[0]  # admin, integration, unit
        by_module[module] += len(failed_by_file[filepath])

    print("\nFailures by module:")
    for module, count in sorted(by_module.items(), key=lambda x: -x[1]):
        print(f"  {module}: {count} failures")

    print()
    print("=" * 80)
    print("Top 10 Files with Most Failures")
    print("=" * 80)
    top_files = sorted(failed_by_file.items(), key=lambda x: -len(x[1]))[:10]
    for filepath, failures in top_files:
        print(f"\n{filepath}: {len(failures)} failures")

    print()
    print("=" * 80)
    print("NEXT STEPS")
    print("=" * 80)
    print("1. Review ERRORs - likely obsolete tests or missing dependencies")
    print("2. Sample FAILED tests to identify patterns (mocking issues, etc.)")
    print("3. Create detailed audit report with root cause for each failure")
    print()


if __name__ == "__main__":
    main()
