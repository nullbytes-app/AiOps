#!/usr/bin/env python3
"""
CI/CD Baseline Enforcement Script - Story 12.1, Updated Story 12.6

Compares current test results against baseline to detect regressions.
Fails CI/CD pipeline if new test failures are introduced.

Story 12.6 Update: Now reads thresholds from ci-baseline-config.yaml for
configurable quality gate enforcement.

Usage:
    python scripts/ci-baseline-check.py [--config PATH] [--results PATH]

Enforcement Rules (Story 12.6):
1. CRITICAL: Block merge if pass rates below critical_min thresholds
2. WARNING: Merge allowed if pass rates between critical_min and warning_min
3. PASS: All thresholds met

Exits:
- 0: All checks passed (or warnings only)
- 1: Critical threshold violations (blocks merge)
"""

import argparse
import json
import sys
import subprocess
from pathlib import Path
from typing import Dict, Set, List, Tuple, Any
import yaml


def run_pytest_and_get_results() -> Dict[str, Any]:
    """Run pytest and return JSON results."""
    result_file = Path("current-test-results.json")

    subprocess.run(
        [
            "python",
            "-m",
            "pytest",
            "tests/",
            "-q",
            "--tb=no",
            "--json-report",
            f"--json-report-file={result_file}",
        ],
        capture_output=True,
    )

    with open(result_file, "r") as f:
        data: Dict[str, Any] = json.load(f)
        return data


def load_baseline(baseline_path: Path) -> Dict[str, Any]:
    """Load baseline test results."""
    with open(baseline_path, "r") as f:
        data: Dict[str, Any] = json.load(f)
        return data


def load_config(config_path: Path) -> Dict[str, Any]:
    """
    Load CI baseline configuration from YAML file (Story 12.6).

    Args:
        config_path: Path to ci-baseline-config.yaml

    Returns:
        Dict with baseline thresholds and enforcement rules
    """
    with open(config_path, "r") as f:
        config: Dict[str, Any] = yaml.safe_load(f)
        return config


def extract_test_statuses(report: Dict[str, Any]) -> Dict[str, str]:
    """
    Extract test name → status mapping from pytest JSON report.

    Args:
        report: Pytest JSON report

    Returns:
        Dict mapping test nodeid → status (passed, failed, skipped, error)
    """
    statuses = {}

    for test in report.get("tests", []):
        nodeid = test.get("nodeid", "")
        outcome = test.get("outcome", "unknown")  # passed, failed, skipped, etc.
        statuses[nodeid] = outcome

    return statuses


def compare_to_baseline(
    baseline: Dict[str, Any], current: Dict[str, Any]
) -> Tuple[List[str], List[str], Dict[str, Any]]:
    """
    Compare current test results to baseline.

    Args:
        baseline: Baseline test results
        current: Current test results

    Returns:
        Tuple of (new_failures, new_passes, metrics)
    """
    baseline_statuses = extract_test_statuses(baseline)
    current_statuses = extract_test_statuses(current)

    new_failures = []
    new_passes = []

    # Check for regressions (tests that passed in baseline now fail)
    for test, baseline_status in baseline_statuses.items():
        current_status = current_statuses.get(test, "missing")

        if baseline_status == "passed" and current_status in ("failed", "error"):
            new_failures.append(test)

        if baseline_status in ("failed", "error") and current_status == "passed":
            new_passes.append(test)

    # Calculate metrics
    baseline_summary = baseline.get("summary", {})
    current_summary = current.get("summary", {})

    baseline_total = baseline_summary.get("total", 0)
    current_total = current_summary.get("total", 0)

    baseline_passed = baseline_summary.get("passed", 0)
    current_passed = current_summary.get("passed", 0)

    baseline_skipped = baseline_summary.get("skipped", 0)
    current_skipped = current_summary.get("skipped", 0)

    baseline_pass_rate = (
        (baseline_passed / (baseline_total - baseline_skipped) * 100)
        if (baseline_total - baseline_skipped) > 0
        else 0
    )
    current_pass_rate = (
        (current_passed / (current_total - current_skipped) * 100)
        if (current_total - current_skipped) > 0
        else 0
    )

    metrics = {
        "baseline_total": baseline_total,
        "current_total": current_total,
        "baseline_passed": baseline_passed,
        "current_passed": current_passed,
        "baseline_pass_rate": round(baseline_pass_rate, 2),
        "current_pass_rate": round(current_pass_rate, 2),
        "new_failures_count": len(new_failures),
        "new_passes_count": len(new_passes),
        "test_count_delta": current_total - baseline_total,
    }

    return new_failures, new_passes, metrics


def generate_report(
    new_failures: List[str],
    new_passes: List[str],
    metrics: Dict[str, Any],
    config: Dict[str, Any]
) -> Tuple[str, bool]:
    """
    Generate baseline comparison report with configurable thresholds (Story 12.6).

    Args:
        new_failures: List of newly failing tests
        new_passes: List of newly passing tests
        metrics: Test metrics dict
        config: Configuration from ci-baseline-config.yaml

    Returns:
        Tuple of (report_string, has_critical_violations)
    """
    report = "=" * 80 + "\n"
    report += "CI/CD BASELINE ENFORCEMENT REPORT (Story 12.6)\n"
    report += "=" * 80 + "\n\n"

    report += "BASELINE COMPARISON\n"
    report += "-" * 80 + "\n"
    report += f"Total Tests: {metrics['baseline_total']} → {metrics['current_total']} "
    report += f"({metrics['test_count_delta']:+d})\n"
    report += f"Passing Tests: {metrics['baseline_passed']} → {metrics['current_passed']} "
    report += f"({metrics['current_passed'] - metrics['baseline_passed']:+d})\n"
    report += f"Pass Rate: {metrics['baseline_pass_rate']}% → {metrics['current_pass_rate']}% "
    report += f"({metrics['current_pass_rate'] - metrics['baseline_pass_rate']:+.1f}%)\n"
    report += "\n"

    # New failures (regressions)
    if new_failures:
        report += f"⚠️  NEW FAILURES DETECTED: {len(new_failures)}\n"
        report += "-" * 80 + "\n"
        for test in new_failures[:10]:  # Show first 10
            report += f"  - {test}\n"
        if len(new_failures) > 10:
            report += f"  ... and {len(new_failures) - 10} more\n"
        report += "\n"

    # New passes (improvements)
    if new_passes:
        report += f"✅ NEW PASSES: {len(new_passes)}\n"
        report += "-" * 80 + "\n"
        for test in new_passes[:10]:
            report += f"  - {test}\n"
        if len(new_passes) > 10:
            report += f"  ... and {len(new_passes) - 10} more\n"
        report += "\n"

    # Enforcement decision with configurable thresholds (Story 12.6)
    report += "ENFORCEMENT DECISION (Configurable Thresholds)\n"
    report += "=" * 80 + "\n"

    baselines = config.get("baselines", {})
    test_pass_rates = baselines.get("test_pass_rates", {})
    test_count_config = baselines.get("test_count", {})

    critical_violations = []
    warnings = []

    # Check overall pass rate
    overall_config = test_pass_rates.get("overall", {})
    critical_min = overall_config.get("critical_min", 85)
    warning_min = overall_config.get("warning_min", 92)

    if metrics["current_pass_rate"] < critical_min:
        critical_violations.append(
            f"❌ CRITICAL: Overall pass rate {metrics['current_pass_rate']}% below "
            f"critical threshold {critical_min}%"
        )
    elif metrics["current_pass_rate"] < warning_min:
        warnings.append(
            f"⚠️  WARNING: Overall pass rate {metrics['current_pass_rate']}% below "
            f"warning threshold {warning_min}%"
        )

    # Check test count regression
    max_decrease = test_count_config.get("max_decrease", 10)
    if metrics["test_count_delta"] < -max_decrease:
        critical_violations.append(
            f"❌ CRITICAL: Test count decreased by {abs(metrics['test_count_delta'])} "
            f"(exceeds max allowed decrease of {max_decrease})"
        )

    # Check for new failures
    if new_failures:
        critical_violations.append(
            f"❌ CRITICAL: {len(new_failures)} new test failures introduced"
        )

    # Print violations and warnings
    if critical_violations:
        for violation in critical_violations:
            report += violation + "\n"
        report += "\n⛔ BLOCKING: Cannot merge to main branch (critical thresholds breached)\n"
    elif warnings:
        for warning in warnings:
            report += warning + "\n"
        report += "\n⚠️  MERGE ALLOWED: Warning thresholds breached (investigation recommended)\n"
    else:
        report += "✅ PASS: All baseline checks passed\n"
        report += "✅ Safe to merge to main branch\n"

    report += "=" * 80 + "\n"

    has_critical = len(critical_violations) > 0
    return report, has_critical


def update_baseline(current: Dict[str, Any], baseline_path: Path) -> None:
    """Update baseline with current results (main branch only)."""
    with open(baseline_path, "w") as f:
        json.dump(current, f, indent=2)
    print(f"✅ Baseline updated: {baseline_path}")


def main() -> int:
    parser = argparse.ArgumentParser(description="CI/CD Baseline Enforcement (Story 12.6)")
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("scripts/ci-baseline-config.yaml"),
        help="Path to baseline config YAML (default: scripts/ci-baseline-config.yaml)",
    )
    parser.add_argument(
        "--baseline",
        type=Path,
        default=Path("test-baseline.json"),
        help="Path to baseline JSON (default: test-baseline.json)",
    )
    parser.add_argument(
        "--results",
        type=Path,
        help="Path to current results JSON (if not provided, will run tests)",
    )
    parser.add_argument(
        "--update-baseline",
        action="store_true",
        help="Update baseline with current results (main branch only)",
    )

    args = parser.parse_args()

    # Load configuration (Story 12.6)
    if not args.config.exists():
        print(f"ERROR: Config file not found: {args.config}")
        print("Story 12.6: ci-baseline-config.yaml required for threshold enforcement")
        return 1

    config = load_config(args.config)

    # Load or run current tests
    if args.results and args.results.exists():
        with open(args.results, "r") as f:
            current = json.load(f)
    else:
        print("Running pytest to get current results...")
        current = run_pytest_and_get_results()

    # Update baseline if requested (main branch workflow)
    if args.update_baseline:
        update_baseline(current, args.baseline)
        return 0

    # Load baseline
    if not args.baseline.exists():
        print(f"ERROR: Baseline file not found: {args.baseline}")
        print("Create baseline first with: --update-baseline")
        return 1

    baseline = load_baseline(args.baseline)

    # Compare
    new_failures, new_passes, metrics = compare_to_baseline(baseline, current)

    # Generate and print report (Story 12.6: uses configurable thresholds)
    report, has_critical = generate_report(new_failures, new_passes, metrics, config)
    print(report)

    # Exit with appropriate code (Story 12.6: 0 for pass/warning, 1 for critical)
    return 1 if has_critical else 0


if __name__ == "__main__":
    sys.exit(main())
