#!/usr/bin/env python3
"""
File Size Enforcement Script

Validates Python source files against 500-line threshold (Story 12.7).
Supports configurable exclusions for generated code, migrations, and legacy files.

Exit codes:
- 0: All files comply or no violations found
- 1: One or more files exceed threshold
- 2: Configuration file error

References:
- Story 12.7: File Size Refactoring and Code Quality
- 2025 Python Best Practices: 150-500 line sweet spot for AI code editors

Usage:
    python scripts/check-file-size.py [--config FILE] [--max-lines N] [--verbose]

Examples:
    # Use default config (scripts/file-size-config.yaml)
    python scripts/check-file-size.py

    # Custom threshold
    python scripts/check-file-size.py --max-lines 600

    # Verbose output
    python scripts/check-file-size.py --verbose
"""

import argparse
import sys
from pathlib import Path
from typing import List, NamedTuple

import yaml


class FileViolation(NamedTuple):
    """File that exceeds size threshold."""

    path: str
    line_count: int
    excess_lines: int
    percentage_over: float


class FileSizeConfig(NamedTuple):
    """File size checking configuration."""

    max_lines: int
    exclude_patterns: List[str]
    exclude_dirs: List[str]


def load_config(config_path: Path) -> FileSizeConfig:
    """
    Load file size configuration from YAML file.

    Args:
        config_path: Path to config file

    Returns:
        FileSizeConfig with max_lines and exclusion patterns

    Raises:
        FileNotFoundError: If config file doesn't exist
        yaml.YAMLError: If config file is invalid
    """
    if not config_path.exists():
        print(f"⚠️  Config file not found: {config_path}", file=sys.stderr)
        print("Using default configuration: max_lines=500, no exclusions", file=sys.stderr)
        return FileSizeConfig(max_lines=500, exclude_patterns=[], exclude_dirs=[])

    try:
        with open(config_path, "r") as f:
            config = yaml.safe_load(f)

        return FileSizeConfig(
            max_lines=config.get("max_lines", 500),
            exclude_patterns=config.get("exclude_patterns", []),
            exclude_dirs=config.get("exclude_dirs", []),
        )
    except yaml.YAMLError as e:
        print(f"❌ Failed to parse config file: {e}", file=sys.stderr)
        sys.exit(2)


def should_exclude(file_path: Path, config: FileSizeConfig) -> bool:
    """
    Check if file should be excluded from size checking.

    Args:
        file_path: Path to file being checked
        config: Configuration with exclusion patterns

    Returns:
        True if file matches any exclusion pattern or directory
    """
    file_str = str(file_path)

    # Check directory exclusions
    for exclude_dir in config.exclude_dirs:
        if exclude_dir in file_path.parts:
            return True

    # Check pattern exclusions
    for pattern in config.exclude_patterns:
        if pattern in file_str:
            return True

    return False


def count_lines(file_path: Path) -> int:
    """
    Count lines in a file.

    Args:
        file_path: Path to file

    Returns:
        Number of lines in file

    Note:
        Empty files return 0 lines. Counts all lines including blank lines.
    """
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return sum(1 for _ in f)
    except (IOError, UnicodeDecodeError) as e:
        print(f"⚠️  Failed to read {file_path}: {e}", file=sys.stderr)
        return 0


def find_python_files(root_dir: Path) -> List[Path]:
    """
    Recursively find all Python files in directory.

    Args:
        root_dir: Root directory to search

    Returns:
        List of paths to .py files
    """
    return list(root_dir.rglob("*.py"))


def check_files(config: FileSizeConfig, verbose: bool = False) -> List[FileViolation]:
    """
    Check all Python files against size threshold.

    Args:
        config: File size configuration
        verbose: Print detailed progress information

    Returns:
        List of files that exceed threshold
    """
    project_root = Path(__file__).parent.parent
    python_files = find_python_files(project_root)

    violations: List[FileViolation] = []
    checked_count = 0

    for file_path in sorted(python_files):
        # Make path relative to project root for cleaner output
        relative_path = file_path.relative_to(project_root)

        # Skip excluded files
        if should_exclude(relative_path, config):
            if verbose:
                print(f"⏭️  Skipping (excluded): {relative_path}")
            continue

        line_count = count_lines(file_path)
        checked_count += 1

        if line_count > config.max_lines:
            excess_lines = line_count - config.max_lines
            percentage_over = (excess_lines / config.max_lines) * 100

            violations.append(
                FileViolation(
                    path=str(relative_path),
                    line_count=line_count,
                    excess_lines=excess_lines,
                    percentage_over=percentage_over,
                )
            )

            if verbose:
                print(f"❌ {relative_path}: {line_count} lines ({percentage_over:.1f}% over)")
        elif verbose:
            print(f"✅ {relative_path}: {line_count} lines")

    if verbose:
        print(f"\n📊 Checked {checked_count} files, found {len(violations)} violations")

    return violations


def print_report(violations: List[FileViolation], max_lines: int) -> None:
    """
    Print formatted violation report.

    Args:
        violations: List of files exceeding threshold
        max_lines: Maximum allowed lines
    """
    if not violations:
        print(f"✅ All files comply with {max_lines}-line threshold")
        return

    print(f"\n❌ {len(violations)} file(s) exceed {max_lines}-line threshold:\n")

    # Sort by excess lines (most violations first)
    sorted_violations = sorted(violations, key=lambda v: v.excess_lines, reverse=True)

    for v in sorted_violations:
        print(f"  {v.path}")
        print(f"    Lines: {v.line_count} (+{v.excess_lines}, {v.percentage_over:.1f}% over)")
        print()

    print("💡 Refactoring suggestions:")
    print("  1. Extract cohesive modules with single responsibility")
    print("  2. Look for natural split points (classes, function groups)")
    print("  3. Create helper modules in dedicated subdirectories")
    print("  4. Export public API through __init__.py")
    print("  5. Maintain backward compatibility with existing imports")
    print()
    print("📖 See docs/refactoring-guide.md for detailed guidance")


def main() -> None:
    """Main entry point for file size checker."""
    parser = argparse.ArgumentParser(
        description="Check Python files against size threshold",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                          # Use default config
  %(prog)s --max-lines 600          # Custom threshold
  %(prog)s --verbose                # Show detailed output
  %(prog)s --config custom.yaml    # Custom config file
        """,
    )

    parser.add_argument(
        "--config",
        type=Path,
        default=Path(__file__).parent / "file-size-config.yaml",
        help="Path to configuration file (default: scripts/file-size-config.yaml)",
    )

    parser.add_argument(
        "--max-lines",
        type=int,
        help="Maximum lines per file (overrides config)",
    )

    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Print detailed progress information",
    )

    args = parser.parse_args()

    # Load configuration
    config = load_config(args.config)

    # Override max_lines if specified
    if args.max_lines:
        config = config._replace(max_lines=args.max_lines)

    if args.verbose:
        print("📋 Configuration:")
        print(f"  Max lines: {config.max_lines}")
        print(f"  Exclude patterns: {config.exclude_patterns or 'None'}")
        print(f"  Exclude dirs: {config.exclude_dirs or 'None'}")
        print()

    # Check files
    violations = check_files(config, verbose=args.verbose)

    # Print report
    print_report(violations, config.max_lines)

    # Exit with error code if violations found
    if violations:
        sys.exit(1)


if __name__ == "__main__":
    main()
