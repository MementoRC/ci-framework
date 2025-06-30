"""Command-line interface for performance data collection."""

import argparse
import json
import sys

from .collector import PerformanceCollector
from .comparator import ComparisonMode, PerformanceComparator


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(description="Performance data collection and analysis tool")

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Collect command
    collect_parser = subparsers.add_parser("collect", help="Collect performance metrics")
    collect_parser.add_argument(
        "--results", required=True, help="Path to benchmark results file (JSON)"
    )
    collect_parser.add_argument(
        "--storage-path",
        default="performance_data",
        help="Directory for storing performance data (default: performance_data)",
    )
    collect_parser.add_argument(
        "--store-baseline", action="store_true", help="Store the collected metrics as a baseline"
    )
    collect_parser.add_argument(
        "--baseline-name", default="default", help="Name for the baseline (default: default)"
    )
    collect_parser.add_argument("--compare-baseline", help="Compare with existing baseline")
    collect_parser.add_argument("--output", help="Output file for results (JSON format)")

    # Compare command (enhanced with PerformanceComparator)
    compare_parser = subparsers.add_parser(
        "compare", help="Compare performance metrics with advanced analysis"
    )
    compare_parser.add_argument(
        "--current", required=True, help="Path to current benchmark results"
    )
    compare_parser.add_argument(
        "--baseline", default="default", help="Baseline name to compare against (default: default)"
    )
    compare_parser.add_argument(
        "--storage-path", default="performance_data", help="Directory containing performance data"
    )
    compare_parser.add_argument(
        "--threshold-config", help="Path to custom threshold configuration file"
    )
    compare_parser.add_argument(
        "--mode",
        choices=["single", "trend"],
        default="single",
        help="Comparison mode: single baseline or trend analysis (default: single)",
    )
    compare_parser.add_argument(
        "--format",
        choices=["markdown", "json", "github"],
        default="markdown",
        help="Report output format (default: markdown)",
    )
    compare_parser.add_argument("--output", help="Output file for comparison results")
    compare_parser.add_argument(
        "--fail-on-regression",
        action="store_true",
        help="Exit with non-zero code if performance regression detected",
    )
    compare_parser.add_argument(
        "--history-limit",
        type=int,
        default=10,
        help="Number of historical builds to include for trend analysis (default: 10)",
    )

    # Baseline command
    baseline_parser = subparsers.add_parser("baseline", help="Manage baselines")
    baseline_parser.add_argument(
        "action", choices=["create", "list", "delete"], help="Baseline action"
    )
    baseline_parser.add_argument(
        "--results", help="Path to benchmark results file (for create action)"
    )
    baseline_parser.add_argument("--name", default="default", help="Baseline name")
    baseline_parser.add_argument(
        "--storage-path", default="performance_data", help="Directory for storing performance data"
    )

    # History command
    history_parser = subparsers.add_parser("history", help="View performance history")
    history_parser.add_argument(
        "--storage-path", default="performance_data", help="Directory containing performance data"
    )
    history_parser.add_argument(
        "--limit", type=int, default=10, help="Number of recent entries to show (default: 10)"
    )
    history_parser.add_argument("--output", help="Output file for history data")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    try:
        if args.command == "collect":
            handle_collect(args)
        elif args.command == "compare":
            handle_compare(args)
        elif args.command == "baseline":
            handle_baseline(args)
        elif args.command == "history":
            handle_history(args)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


def handle_collect(args):
    """Handle collect command."""
    collector = PerformanceCollector(args.storage_path)

    # Collect metrics
    metrics = collector.collect_metrics(args.results)

    # Store in history
    history_file = collector.store_history(metrics)
    print(f"Stored performance metrics: {history_file}")

    # Store as baseline if requested
    if args.store_baseline:
        baseline_file = collector.store_baseline(metrics, args.baseline_name)
        print(f"Stored baseline: {baseline_file}")

    # Compare with baseline if requested
    comparison_result = None
    if args.compare_baseline:
        comparison_result = collector.compare_with_baseline(metrics, args.compare_baseline)
        if "error" not in comparison_result:
            print(f"Comparison with baseline '{args.compare_baseline}':")
            print_comparison_summary(comparison_result)

    # Output results
    output_data = {"metrics": metrics.to_dict(), "comparison": comparison_result}

    if args.output:
        with open(args.output, "w") as f:
            json.dump(output_data, f, indent=2)
        print(f"Results written to: {args.output}")
    else:
        print(f"Build ID: {metrics.build_id}")
        print(f"Timestamp: {metrics.timestamp}")
        print(f"Benchmark results: {len(metrics.results)}")

        # Print summary stats
        stats = metrics.calculate_summary_stats()
        if stats:
            print("\nSummary Statistics:")
            for key, value in stats.items():
                print(f"  {key}: {value:.4f}")


def handle_compare(args):
    """Handle compare command with enhanced PerformanceComparator."""
    collector = PerformanceCollector(args.storage_path)

    # Initialize comparator with custom threshold config if provided
    comparator = PerformanceComparator(args.threshold_config)

    # Collect current metrics
    current_metrics = collector.collect_metrics(args.current)

    # Load baseline metrics
    baseline_metrics = collector.load_baseline(args.baseline)
    if not baseline_metrics:
        print(f"Error: Baseline '{args.baseline}' not found", file=sys.stderr)
        sys.exit(1)

    # Perform comparison based on mode
    if args.mode == "trend":
        # Get historical metrics for trend analysis
        historical_metrics = collector.get_recent_history(args.history_limit)
        if not historical_metrics:
            print(
                "Warning: No historical data available, falling back to single baseline comparison"
            )
            comparison_result = comparator.compare_with_baseline(
                current_metrics, baseline_metrics, ComparisonMode.SINGLE_BASELINE
            )
        else:
            comparison_result = comparator.compare_with_trend(current_metrics, historical_metrics)
    else:
        comparison_result = comparator.compare_with_baseline(
            current_metrics, baseline_metrics, ComparisonMode.SINGLE_BASELINE
        )

    # Generate and display report
    report = comparator.generate_report(comparison_result, args.format)

    if args.output:
        with open(args.output, "w") as f:
            f.write(report)
        print(f"Comparison report written to: {args.output}")
    else:
        print(report)

    # Check for regressions if requested
    if args.fail_on_regression:
        if comparison_result.regressions_count > 0:
            print(
                f"\nPerformance regression detected: {comparison_result.regressions_count} critical regressions"
            )
            sys.exit(1)
        elif comparison_result.warnings_count > 0:
            print(f"\nPerformance warnings detected: {comparison_result.warnings_count} warnings")
            sys.exit(2)  # Warning exit code


def handle_baseline(args):
    """Handle baseline command."""
    collector = PerformanceCollector(args.storage_path)

    if args.action == "create":
        if not args.results:
            print("Error: --results required for create action", file=sys.stderr)
            sys.exit(1)

        metrics = collector.collect_metrics(args.results)
        baseline_file = collector.store_baseline(metrics, args.name)
        print(f"Created baseline '{args.name}': {baseline_file}")

    elif args.action == "list":
        baseline_dir = collector.baseline_path
        baselines = list(baseline_dir.glob("*_baseline.json"))

        if not baselines:
            print("No baselines found")
        else:
            print("Available baselines:")
            for baseline_file in baselines:
                name = baseline_file.stem.replace("_baseline", "")
                print(f"  {name}")

    elif args.action == "delete":
        baseline_file = collector.baseline_path / f"{args.name}_baseline.json"
        if baseline_file.exists():
            baseline_file.unlink()
            print(f"Deleted baseline '{args.name}'")
        else:
            print(f"Baseline '{args.name}' not found")


def handle_history(args):
    """Handle history command."""
    collector = PerformanceCollector(args.storage_path)
    history = collector.get_recent_history(args.limit)

    if not history:
        print("No performance history found")
        return

    if args.output:
        history_data = [metrics.to_dict() for metrics in history]
        with open(args.output, "w") as f:
            json.dump(history_data, f, indent=2)
        print(f"History data written to: {args.output}")
    else:
        print(f"Performance History (last {len(history)} entries):")
        print()

        for metrics in history:
            print(f"Build ID: {metrics.build_id}")
            print(f"Timestamp: {metrics.timestamp}")
            print(f"Results: {len(metrics.results)}")

            stats = metrics.calculate_summary_stats()
            if stats:
                print(f"Avg execution time: {stats.get('avg_execution_time', 0):.4f}s")
                if "avg_throughput" in stats:
                    print(f"Avg throughput: {stats['avg_throughput']:.2f} ops/s")
            print("-" * 50)


def print_comparison_summary(comparison_result):
    """Print a summary of comparison results."""
    print(f"Baseline: {comparison_result['baseline_build_id']}")
    print(f"Current:  {comparison_result['current_build_id']}")
    print()

    for comp in comparison_result["comparisons"]:
        print(f"Benchmark: {comp['name']}")

        # Execution time
        et = comp["execution_time"]
        print(
            f"  Execution time: {et['current']:.4f}s vs {et['baseline']:.4f}s "
            f"({et['change_percent']:+.1f}% - {et['change_direction']})"
        )

        # Memory usage
        if "memory_usage" in comp:
            mem = comp["memory_usage"]
            print(
                f"  Memory usage: {mem['current']:.1f}MB vs {mem['baseline']:.1f}MB "
                f"({mem['change_percent']:+.1f}% - {mem['change_direction']})"
            )

        # Throughput
        if "throughput" in comp:
            thr = comp["throughput"]
            print(
                f"  Throughput: {thr['current']:.1f} vs {thr['baseline']:.1f} ops/s "
                f"({thr['change_percent']:+.1f}% - {thr['change_direction']})"
            )

        print()


def check_for_regressions(comparison_result, threshold: float) -> bool:
    """Check if there are performance regressions above threshold."""
    for comp in comparison_result["comparisons"]:
        # Check execution time regression
        et = comp["execution_time"]
        if et["change_direction"] == "regression" and abs(et["change_percent"]) > threshold:
            return True

        # Check memory regression
        if "memory_usage" in comp:
            mem = comp["memory_usage"]
            if mem["change_direction"] == "regression" and abs(mem["change_percent"]) > threshold:
                return True

        # Check throughput regression
        if "throughput" in comp:
            thr = comp["throughput"]
            if thr["change_direction"] == "regression" and abs(thr["change_percent"]) > threshold:
                return True

    return False


if __name__ == "__main__":
    main()
