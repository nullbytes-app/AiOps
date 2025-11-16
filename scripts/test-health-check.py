#!/usr/bin/env python3
"""
Test Health Check Script - Story 12.1

Calculates test metrics and health indicators from pytest results.
Fails with exit code 1 if pass rate falls below 95% threshold.

Usage:
    python scripts/test-health-check.py [--json-report PATH] [--fail-under PERCENT]

Metrics Calculated:
- Pass rate: (passing / non-skipped) * 100
- Skip rate: (skipped / total) * 100
- Failure rate: (failing / total) * 100
- Test counts by status (PASSED, FAILED, ERROR, SKIPPED)

Exits:
- 0: Pass rate ≥ threshold (default: 95%)
- 1: Pass rate < threshold OR test run failed
"""

import argparse
import json
import sys
import subprocess
from pathlib import Path
from datetime import datetime
from typing import Dict, Any


def run_pytest_with_json(output_path: Path) -> int:
    """
    Run pytest and generate JSON report.

    Args:
        output_path: Path to save JSON report

    Returns:
        Exit code from pytest
    """
    result = subprocess.run(
        [
            "python",
            "-m",
            "pytest",
            "tests/",
            "-q",
            "--tb=no",
            f"--json-report",
            f"--json-report-file={output_path}",
        ],
        capture_output=True,
    )
    return result.returncode


def load_pytest_json(json_path: Path) -> Dict[str, Any]:
    """Load pytest JSON report."""
    with open(json_path, "r") as f:
        data: Dict[str, Any] = json.load(f)
        return data


def calculate_metrics(report: Dict[str, Any]) -> Dict[str, Any]:
    """
    Calculate test health metrics from pytest JSON report.

    Args:
        report: Pytest JSON report data

    Returns:
        Dict with calculated metrics
    """
    summary = report.get("summary", {})

    total = summary.get("total", 0)
    passed = summary.get("passed", 0)
    failed = summary.get("failed", 0)
    skipped = summary.get("skipped", 0)
    error = summary.get("error", 0)

    # Calculate rates
    non_skipped = total - skipped
    pass_rate = (passed / non_skipped * 100) if non_skipped > 0 else 0.0
    skip_rate = (skipped / total * 100) if total > 0 else 0.0
    fail_rate = ((failed + error) / total * 100) if total > 0 else 0.0

    # Calculate test type breakdowns (Story 12.5 AC7)
    tests = report.get("tests", [])
    unit_tests = [t for t in tests if "tests/unit/" in t.get("nodeid", "")]
    integration_tests = [t for t in tests if "tests/integration/" in t.get("nodeid", "")]
    e2e_tests = [t for t in tests if "tests/e2e/" in t.get("nodeid", "")]
    security_tests = [t for t in tests if "tests/security/" in t.get("nodeid", "")]

    def count_by_outcome(test_list):
        """Count tests by outcome status."""
        outcomes = {"passed": 0, "failed": 0, "skipped": 0, "error": 0}
        for test in test_list:
            outcome = test.get("outcome", "error")
            if outcome in outcomes:
                outcomes[outcome] += 1
        return outcomes

    unit_counts = count_by_outcome(unit_tests)
    integration_counts = count_by_outcome(integration_tests)
    e2e_counts = count_by_outcome(e2e_tests)
    security_counts = count_by_outcome(security_tests)

    return {
        "timestamp": datetime.now().isoformat(),
        "total_tests": total,
        "passed": passed,
        "failed": failed,
        "error": error,
        "skipped": skipped,
        "pass_rate": round(pass_rate, 2),
        "skip_rate": round(skip_rate, 2),
        "fail_rate": round(fail_rate, 2),
        "duration_seconds": report.get("duration", 0),
        # Test type breakdowns (Story 12.5)
        "unit_tests": {
            "total": len(unit_tests),
            "passed": unit_counts["passed"],
            "failed": unit_counts["failed"],
            "skipped": unit_counts["skipped"],
            "error": unit_counts["error"],
        },
        "integration_tests": {
            "total": len(integration_tests),
            "passed": integration_counts["passed"],
            "failed": integration_counts["failed"],
            "skipped": integration_counts["skipped"],
            "error": integration_counts["error"],
        },
        "e2e_tests": {
            "total": len(e2e_tests),
            "passed": e2e_counts["passed"],
            "failed": e2e_counts["failed"],
            "skipped": e2e_counts["skipped"],
            "error": e2e_counts["error"],
        },
        "security_tests": {
            "total": len(security_tests),
            "passed": security_counts["passed"],
            "failed": security_counts["failed"],
            "skipped": security_counts["skipped"],
            "error": security_counts["error"],
        },
    }


def generate_markdown_report(metrics: Dict[str, Any]) -> str:
    """
    Generate Markdown summary report.

    Args:
        metrics: Calculated metrics dictionary

    Returns:
        Markdown formatted report string
    """
    pass_icon = "✅" if metrics["pass_rate"] >= 95.0 else "⚠️"

    report = f"""# Test Health Report

**Generated:** {metrics['timestamp']}

## Summary

| Metric | Value | Status |
|--------|-------|--------|
| **Pass Rate** | {metrics['pass_rate']}% | {pass_icon} |
| **Skip Rate** | {metrics['skip_rate']}% | |
| **Failure Rate** | {metrics['fail_rate']}% | |
| **Total Tests** | {metrics['total_tests']} | |
| **Duration** | {metrics['duration_seconds']:.2f}s | |

## Test Counts

| Status | Count | Percentage |
|--------|-------|------------|
| ✅ PASSED | {metrics['passed']} | {metrics['passed'] / metrics['total_tests'] * 100:.1f}% |
| ❌ FAILED | {metrics['failed']} | {metrics['failed'] / metrics['total_tests'] * 100:.1f}% |
| 🔴 ERROR | {metrics['error']} | {metrics['error'] / metrics['total_tests'] * 100:.1f}% |
| ⏭️  SKIPPED | {metrics['skipped']} | {metrics['skip_rate']:.1f}% |

## Test Type Breakdown (Story 12.5)

"""

    # Add test type breakdown table
    for test_type in ["unit_tests", "integration_tests", "e2e_tests", "security_tests"]:
        if test_type in metrics:
            type_data = metrics[test_type]
            type_name = test_type.replace("_", " ").title()
            total = type_data["total"]
            if total > 0:
                passed = type_data["passed"]
                failed = type_data["failed"]
                error = type_data["error"]
                skipped = type_data["skipped"]
                pass_rate = (passed / (total - skipped) * 100) if (total - skipped) > 0 else 0.0
                report += f"""### {type_name}
| Metric | Count |
|--------|-------|
| Total | {total} |
| ✅ Passed | {passed} ({pass_rate:.1f}%) |
| ❌ Failed | {failed} |
| 🔴 Error | {error} |
| ⏭️ Skipped | {skipped} |

"""

    report += """## Pass Rate Trend

Target: **≥95.0%**
Current: **{pass_rate}%**
Gap: **{gap:.1f}%**

""".format(
        pass_rate=metrics["pass_rate"], gap=95.0 - metrics["pass_rate"]
    )

    if metrics["pass_rate"] >= 95.0:
        report += "✅ **PASS:** Test suite meets quality threshold\n"
    else:
        report += f"⚠️ **FAIL:** Test suite below threshold (need {round((95.0 * (metrics['total_tests'] - metrics['skipped']) / 100) - metrics['passed'])} more passing tests)\n"

    return report


def save_metrics_history(metrics: Dict[str, Any], history_file: Path) -> None:
    """
    Append metrics to historical trend file.

    Args:
        metrics: Current metrics to append
        history_file: Path to metrics history JSON file
    """
    history = []

    if history_file.exists():
        with open(history_file, "r") as f:
            history = json.load(f)

    history.append(metrics)

    # Keep last 100 entries
    history = history[-100:]

    with open(history_file, "w") as f:
        json.dump(history, f, indent=2)


def main() -> int:
    parser = argparse.ArgumentParser(description="Test Health Check")
    parser.add_argument(
        "--json-report",
        type=Path,
        default=Path("test-results.json"),
        help="Path to pytest JSON report (default: test-results.json)",
    )
    parser.add_argument(
        "--fail-under",
        type=float,
        default=95.0,
        help="Minimum pass rate threshold (default: 95.0)",
    )
    parser.add_argument(
        "--run-tests",
        action="store_true",
        help="Run pytest before calculating metrics",
    )
    parser.add_argument(
        "--save-history",
        type=Path,
        help="Save metrics to history file (e.g., test-metrics-history.json)",
    )
    parser.add_argument(
        "--markdown-output",
        type=Path,
        help="Save Markdown report to file",
    )

    args = parser.parse_args()

    # Run tests if requested
    if args.run_tests:
        print("Running pytest with JSON report...")
        exit_code = run_pytest_with_json(args.json_report)
        if exit_code not in (0, 1):  # 1 is acceptable (tests failed but ran)
            print(f"ERROR: pytest exited with code {exit_code}")
            return exit_code

    # Load JSON report
    if not args.json_report.exists():
        print(f"ERROR: JSON report not found: {args.json_report}")
        print("Run with --run-tests or provide existing report path")
        return 1

    report = load_pytest_json(args.json_report)

    # Calculate metrics
    metrics = calculate_metrics(report)

    # Generate and print Markdown report
    markdown = generate_markdown_report(metrics)
    print(markdown)

    # Save Markdown if requested
    if args.markdown_output:
        args.markdown_output.write_text(markdown)
        print(f"\n✅ Markdown report saved to: {args.markdown_output}")

    # Save to history if requested
    if args.save_history:
        save_metrics_history(metrics, args.save_history)
        print(f"✅ Metrics saved to history: {args.save_history}")

    # Check threshold and exit
    if metrics["pass_rate"] < args.fail_under:
        print(f"\n❌ FAIL: Pass rate {metrics['pass_rate']}% below threshold {args.fail_under}%")
        return 1

    print(f"\n✅ PASS: Pass rate {metrics['pass_rate']}% meets threshold {args.fail_under}%")
    return 0


if __name__ == "__main__":
    sys.exit(main())
