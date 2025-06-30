"""Performance comparison engine with regression detection and alerting."""

import json
import statistics
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

import yaml

from .models import BenchmarkResult, PerformanceMetrics


class AlertSeverity(Enum):
    """Alert severity levels for performance regressions."""

    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class ComparisonMode(Enum):
    """Comparison mode for performance analysis."""

    SINGLE_BASELINE = "single_baseline"
    ROLLING_AVERAGE = "rolling_average"
    TREND_ANALYSIS = "trend_analysis"


@dataclass
class ThresholdConfig:
    """Configuration for performance regression thresholds."""

    relative_increase: float  # Percentage increase threshold
    absolute_increase: float  # Absolute increase threshold
    statistical_significance: float = 0.95  # Confidence level for statistical tests


@dataclass
class PerformanceAlert:
    """Performance regression alert."""

    metric_name: str
    benchmark_name: str
    severity: AlertSeverity
    message: str
    current_value: float
    baseline_value: float
    change_percent: float
    threshold_violated: str
    statistical_significance: float | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class ComparisonResult:
    """Result of performance comparison analysis."""

    baseline_build_id: str
    current_build_id: str
    comparison_mode: ComparisonMode
    total_benchmarks: int
    regressions_count: int
    warnings_count: int
    improvements_count: int
    stable_count: int
    alerts: list[PerformanceAlert] = field(default_factory=list)
    detailed_comparisons: list[dict[str, Any]] = field(default_factory=list)
    statistical_summary: dict[str, Any] = field(default_factory=dict)


class PerformanceComparator:
    """Advanced performance comparison engine with regression detection."""

    def __init__(self, threshold_config_path: str | Path | None = None):
        """Initialize the performance comparator.

        Args:
            threshold_config_path: Path to threshold configuration file.
                                 Defaults to 'performance_thresholds.yaml' in package directory.
        """
        if threshold_config_path is None:
            threshold_config_path = Path(__file__).parent / "performance_thresholds.yaml"

        self.threshold_config_path = Path(threshold_config_path)
        self.thresholds = self._load_thresholds()

    def _load_thresholds(self) -> dict[str, ThresholdConfig]:
        """Load regression detection thresholds from configuration."""
        if not self.threshold_config_path.exists():
            return self._get_default_thresholds()

        try:
            with open(self.threshold_config_path) as f:
                config = yaml.safe_load(f)

            thresholds = {}
            for metric_type, threshold_data in config.get("thresholds", {}).items():
                thresholds[metric_type] = ThresholdConfig(
                    relative_increase=threshold_data.get("relative_increase", 0.10),
                    absolute_increase=threshold_data.get("absolute_increase", 0.0),
                    statistical_significance=threshold_data.get("statistical_significance", 0.95),
                )

            return thresholds
        except (yaml.YAMLError, KeyError, TypeError) as e:
            print(
                f"Warning: Failed to load threshold config from {self.threshold_config_path}: {e}"
            )
            return self._get_default_thresholds()

    def _get_default_thresholds(self) -> dict[str, ThresholdConfig]:
        """Get default threshold configuration."""
        return {
            "execution_time": ThresholdConfig(
                relative_increase=0.10,  # 10% increase is regression
                absolute_increase=0.100,  # 100ms absolute increase is regression
            ),
            "memory_usage": ThresholdConfig(
                relative_increase=0.15,  # 15% increase is regression
                absolute_increase=50.0,  # 50MB absolute increase is regression
            ),
            "throughput": ThresholdConfig(
                relative_increase=-0.10,  # 10% decrease is regression for throughput
                absolute_increase=-100.0,  # 100 ops/sec decrease is regression
            ),
        }

    def compare_with_baseline(
        self,
        current_metrics: PerformanceMetrics,
        baseline_metrics: PerformanceMetrics,
        comparison_mode: ComparisonMode = ComparisonMode.SINGLE_BASELINE,
    ) -> ComparisonResult:
        """Compare current metrics with baseline and detect regressions.

        Args:
            current_metrics: Current performance metrics.
            baseline_metrics: Baseline performance metrics.
            comparison_mode: Mode of comparison analysis.

        Returns:
            ComparisonResult with detailed analysis and alerts.
        """
        result = ComparisonResult(
            baseline_build_id=baseline_metrics.build_id,
            current_build_id=current_metrics.build_id,
            comparison_mode=comparison_mode,
            total_benchmarks=len(current_metrics.results),
            regressions_count=0,
            warnings_count=0,
            improvements_count=0,
            stable_count=0,
        )

        # Compare individual benchmark results
        for current_result in current_metrics.results:
            baseline_result = baseline_metrics.get_result(current_result.name)
            if baseline_result:
                comparison = self._compare_benchmark_results(current_result, baseline_result)
                result.detailed_comparisons.append(comparison)

                # Check for regressions and generate alerts
                alerts = self._detect_regressions(current_result, baseline_result)
                result.alerts.extend(alerts)

                # Update counters
                if alerts:
                    critical_alerts = [a for a in alerts if a.severity == AlertSeverity.CRITICAL]
                    warning_alerts = [a for a in alerts if a.severity == AlertSeverity.WARNING]

                    if critical_alerts:
                        result.regressions_count += 1
                    elif warning_alerts:
                        result.warnings_count += 1
                    else:
                        result.stable_count += 1
                else:
                    # Check for improvements
                    if self._is_improvement(current_result, baseline_result):
                        result.improvements_count += 1
                    else:
                        result.stable_count += 1

        # Calculate statistical summary
        result.statistical_summary = self._calculate_statistical_summary(
            current_metrics, baseline_metrics
        )

        return result

    def compare_with_trend(
        self, current_metrics: PerformanceMetrics, historical_metrics: list[PerformanceMetrics]
    ) -> ComparisonResult:
        """Compare current metrics with historical trend.

        Args:
            current_metrics: Current performance metrics.
            historical_metrics: List of historical metrics for trend analysis.

        Returns:
            ComparisonResult with trend-based analysis.
        """
        if not historical_metrics:
            raise ValueError("Historical metrics required for trend analysis")

        # Use most recent as baseline for basic comparison
        baseline_metrics = historical_metrics[-1]

        result = self.compare_with_baseline(
            current_metrics, baseline_metrics, ComparisonMode.TREND_ANALYSIS
        )

        # Enhance with trend analysis
        result.statistical_summary.update(self._analyze_trends(current_metrics, historical_metrics))

        return result

    def _compare_benchmark_results(
        self, current: BenchmarkResult, baseline: BenchmarkResult
    ) -> dict[str, Any]:
        """Compare two benchmark results with detailed analysis."""

        def calc_change_percent(current_val, baseline_val):
            if baseline_val == 0:
                return float("inf") if current_val > 0 else 0
            return ((current_val - baseline_val) / baseline_val) * 100

        def calc_change_absolute(current_val, baseline_val):
            return current_val - baseline_val

        comparison = {
            "name": current.name,
            "execution_time": {
                "current": current.execution_time,
                "baseline": baseline.execution_time,
                "change_percent": calc_change_percent(
                    current.execution_time, baseline.execution_time
                ),
                "change_absolute": calc_change_absolute(
                    current.execution_time, baseline.execution_time
                ),
                "change_direction": (
                    "regression"
                    if current.execution_time > baseline.execution_time
                    else "improvement"
                ),
            },
        }

        if current.memory_usage is not None and baseline.memory_usage is not None:
            comparison["memory_usage"] = {
                "current": current.memory_usage,
                "baseline": baseline.memory_usage,
                "change_percent": calc_change_percent(current.memory_usage, baseline.memory_usage),
                "change_absolute": calc_change_absolute(
                    current.memory_usage, baseline.memory_usage
                ),
                "change_direction": (
                    "regression" if current.memory_usage > baseline.memory_usage else "improvement"
                ),
            }

        if current.throughput is not None and baseline.throughput is not None:
            comparison["throughput"] = {
                "current": current.throughput,
                "baseline": baseline.throughput,
                "change_percent": calc_change_percent(current.throughput, baseline.throughput),
                "change_absolute": calc_change_absolute(current.throughput, baseline.throughput),
                "change_direction": (
                    "improvement" if current.throughput > baseline.throughput else "regression"
                ),
            }

        return comparison

    def _detect_regressions(
        self, current: BenchmarkResult, baseline: BenchmarkResult
    ) -> list[PerformanceAlert]:
        """Detect performance regressions based on configured thresholds."""
        alerts: list[PerformanceAlert] = []

        # Check execution time regression
        if current.execution_time is not None and baseline.execution_time is not None:
            alerts.extend(
                self._check_metric_regression(
                    "execution_time",
                    current.name,
                    current.execution_time,
                    baseline.execution_time,
                )
            )

        # Check memory usage regression
        if current.memory_usage is not None and baseline.memory_usage is not None:
            alerts.extend(
                self._check_metric_regression(
                    "memory_usage",
                    current.name,
                    current.memory_usage,
                    baseline.memory_usage,
                )
            )

        # Check throughput regression
        if current.throughput is not None and baseline.throughput is not None:
            alerts.extend(
                self._check_metric_regression(
                    "throughput",
                    current.name,
                    current.throughput,
                    baseline.throughput,
                )
            )

        return alerts

    def _check_metric_regression(
        self, metric_type: str, benchmark_name: str, current_value: float, baseline_value: float
    ) -> list[PerformanceAlert]:
        """Check if a specific metric has regressed."""
        alerts: list[PerformanceAlert] = []

        threshold = self.thresholds.get(metric_type)
        if not threshold:
            return alerts

        # Calculate changes
        if baseline_value == 0:
            change_percent = float("inf") if current_value > 0 else 0
        else:
            change_percent = ((current_value - baseline_value) / baseline_value) * 100

        change_absolute = current_value - baseline_value

        # For throughput, regression is a decrease (negative change)
        # For execution_time and memory_usage, regression is an increase (positive change)
        if metric_type == "throughput":
            relative_threshold = threshold.relative_increase  # This should be negative
            absolute_threshold = threshold.absolute_increase  # This should be negative
            is_relative_regression = change_percent <= relative_threshold * 100
            is_absolute_regression = change_absolute <= absolute_threshold
        else:
            relative_threshold = threshold.relative_increase
            absolute_threshold = threshold.absolute_increase
            is_relative_regression = change_percent >= relative_threshold * 100
            is_absolute_regression = change_absolute >= absolute_threshold

        # Determine severity and create alerts
        if is_relative_regression and is_absolute_regression:
            severity = AlertSeverity.CRITICAL
            message = f"Critical {metric_type} regression: {change_percent:+.1f}% change, {change_absolute:+.3f} absolute"
            alerts.append(
                PerformanceAlert(
                    metric_name=metric_type,
                    benchmark_name=benchmark_name,
                    severity=severity,
                    message=message,
                    current_value=current_value,
                    baseline_value=baseline_value,
                    change_percent=change_percent,
                    threshold_violated="both_relative_and_absolute",
                )
            )
        elif is_relative_regression:
            severity = AlertSeverity.WARNING
            message = f"Relative {metric_type} regression: {change_percent:+.1f}% change"
            alerts.append(
                PerformanceAlert(
                    metric_name=metric_type,
                    benchmark_name=benchmark_name,
                    severity=severity,
                    message=message,
                    current_value=current_value,
                    baseline_value=baseline_value,
                    change_percent=change_percent,
                    threshold_violated="relative_threshold",
                )
            )
        elif is_absolute_regression:
            severity = AlertSeverity.WARNING
            message = f"Absolute {metric_type} regression: {change_absolute:+.3f} absolute change"
            alerts.append(
                PerformanceAlert(
                    metric_name=metric_type,
                    benchmark_name=benchmark_name,
                    severity=severity,
                    message=message,
                    current_value=current_value,
                    baseline_value=baseline_value,
                    change_percent=change_percent,
                    threshold_violated="absolute_threshold",
                )
            )

        return alerts

    def _is_improvement(self, current: BenchmarkResult, baseline: BenchmarkResult) -> bool:
        """Check if current result shows improvement over baseline."""
        improvements = 0
        total_metrics = 0

        # Check execution time improvement (lower is better)
        if current.execution_time is not None and baseline.execution_time is not None:
            total_metrics += 1
            if current.execution_time <= baseline.execution_time * 0.95:  # 5% improvement threshold
                improvements += 1

        # Check memory usage improvement (lower is better)
        if current.memory_usage is not None and baseline.memory_usage is not None:
            total_metrics += 1
            if current.memory_usage <= baseline.memory_usage * 0.95:  # 5% improvement threshold
                improvements += 1

        # Check throughput improvement (higher is better)
        if current.throughput is not None and baseline.throughput is not None:
            total_metrics += 1
            if current.throughput >= baseline.throughput * 1.05:  # 5% improvement threshold
                improvements += 1

        # Return true if there's any improvement (not requiring all metrics to improve)
        return improvements > 0

    def _calculate_statistical_summary(
        self, current_metrics: PerformanceMetrics, baseline_metrics: PerformanceMetrics
    ) -> dict[str, Any]:
        """Calculate statistical summary of the comparison."""
        summary: dict[str, Any] = {
            "total_benchmarks_compared": 0,
            "execution_time_stats": {},
            "memory_usage_stats": {},
            "throughput_stats": {},
        }

        # Collect changes for statistical analysis
        execution_time_changes = []
        memory_usage_changes = []
        throughput_changes = []

        for current_result in current_metrics.results:
            baseline_result = baseline_metrics.get_result(current_result.name)
            if baseline_result:
                summary["total_benchmarks_compared"] += 1

                # Execution time changes
                if (
                    current_result.execution_time is not None
                    and baseline_result.execution_time is not None
                    and baseline_result.execution_time > 0
                ):
                    change = (
                        (current_result.execution_time - baseline_result.execution_time)
                        / baseline_result.execution_time
                    ) * 100
                    execution_time_changes.append(change)

                # Memory usage changes
                if (
                    current_result.memory_usage is not None
                    and baseline_result.memory_usage is not None
                    and baseline_result.memory_usage > 0
                ):
                    change = (
                        (current_result.memory_usage - baseline_result.memory_usage)
                        / baseline_result.memory_usage
                    ) * 100
                    memory_usage_changes.append(change)

                # Throughput changes
                if (
                    current_result.throughput is not None
                    and baseline_result.throughput is not None
                    and baseline_result.throughput > 0
                ):
                    change = (
                        (current_result.throughput - baseline_result.throughput)
                        / baseline_result.throughput
                    ) * 100
                    throughput_changes.append(change)

        # Calculate statistics for each metric type
        if execution_time_changes:
            summary["execution_time_stats"] = self._calculate_metric_stats(execution_time_changes)

        if memory_usage_changes:
            summary["memory_usage_stats"] = self._calculate_metric_stats(memory_usage_changes)

        if throughput_changes:
            summary["throughput_stats"] = self._calculate_metric_stats(throughput_changes)

        return summary

    def _calculate_metric_stats(self, changes: list[float]) -> dict[str, float]:
        """Calculate statistical metrics for a list of percentage changes."""
        if not changes:
            return {}

        return {
            "mean_change_percent": statistics.mean(changes),
            "median_change_percent": statistics.median(changes),
            "std_dev_change_percent": statistics.stdev(changes) if len(changes) > 1 else 0.0,
            "min_change_percent": min(changes),
            "max_change_percent": max(changes),
            "sample_size": len(changes),
        }

    def _analyze_trends(
        self, current_metrics: PerformanceMetrics, historical_metrics: list[PerformanceMetrics]
    ) -> dict[str, Any]:
        """Analyze performance trends over historical data."""
        trend_analysis: dict[str, Any] = {
            "trend_direction": "stable",
            "trend_strength": 0.0,
            "trend_details": {},
        }

        # For each benchmark, analyze trend over time
        for current_result in current_metrics.results:
            historical_values = []
            for historical_metric in historical_metrics:
                historical_result = historical_metric.get_result(current_result.name)
                if historical_result and historical_result.execution_time is not None:
                    historical_values.append(historical_result.execution_time)

            if len(historical_values) >= 3:  # Need at least 3 points for trend analysis
                # Simple linear trend calculation
                x_values = list(range(len(historical_values)))
                try:
                    # Calculate Pearson correlation coefficient
                    correlation = self._calculate_correlation(x_values, historical_values)
                    trend_analysis["trend_details"][current_result.name] = {
                        "correlation": correlation,
                        "direction": "increasing"
                        if correlation > 0.1
                        else "decreasing"
                        if correlation < -0.1
                        else "stable",
                        "historical_values": historical_values,
                    }
                except (ValueError, ZeroDivisionError):
                    continue

        return trend_analysis

    def _calculate_correlation(self, x_values: list[int], y_values: list[float]) -> float:
        """Calculate Pearson correlation coefficient."""
        if len(x_values) != len(y_values) or len(x_values) < 2:
            return 0.0

        n = len(x_values)
        sum_x = sum(x_values)
        sum_y = sum(y_values)
        sum_xy = sum(x * y for x, y in zip(x_values, y_values, strict=True))
        sum_x2 = sum(x * x for x in x_values)
        sum_y2 = sum(y * y for y in y_values)

        numerator = n * sum_xy - sum_x * sum_y
        denominator = ((n * sum_x2 - sum_x * sum_x) * (n * sum_y2 - sum_y * sum_y)) ** 0.5

        if denominator == 0:
            return 0.0

        return numerator / denominator

    def generate_report(
        self, comparison_result: ComparisonResult, output_format: str = "markdown"
    ) -> str:
        """Generate a formatted report from comparison results.

        Args:
            comparison_result: Result of performance comparison.
            output_format: Format for the report ('markdown', 'json', 'github').

        Returns:
            Formatted report string.
        """
        if output_format == "json":
            return self._generate_json_report(comparison_result)
        elif output_format == "github":
            return self._generate_github_report(comparison_result)
        else:
            return self._generate_markdown_report(comparison_result)

    def _generate_markdown_report(self, result: ComparisonResult) -> str:
        """Generate markdown format report."""
        report = "# Performance Comparison Report\n\n"
        report += f"**Baseline Build**: {result.baseline_build_id}\n"
        report += f"**Current Build**: {result.current_build_id}\n"
        report += f"**Comparison Mode**: {result.comparison_mode.value}\n\n"

        # Summary
        report += "## Summary\n\n"
        report += f"- **Total Benchmarks**: {result.total_benchmarks}\n"
        report += f"- **Regressions**: {result.regressions_count} ❌\n"
        report += f"- **Warnings**: {result.warnings_count} ⚠️\n"
        report += f"- **Improvements**: {result.improvements_count} ✅\n"
        report += f"- **Stable**: {result.stable_count} ➡️\n\n"

        # Overall status
        if result.regressions_count > 0:
            report += "**🚨 Status: PERFORMANCE REGRESSION DETECTED**\n\n"
        elif result.warnings_count > 0:
            report += "**⚠️ Status: PERFORMANCE WARNINGS**\n\n"
        else:
            report += "**✅ Status: PERFORMANCE OK**\n\n"

        # Alerts
        if result.alerts:
            report += "## Alerts\n\n"
            for alert in result.alerts:
                icon = "🚨" if alert.severity == AlertSeverity.CRITICAL else "⚠️"
                report += f"**{icon} {alert.severity.value.upper()}**: {alert.message}\n"
                report += f"- Benchmark: `{alert.benchmark_name}`\n"
                report += f"- Metric: `{alert.metric_name}`\n"
                report += f"- Current: {alert.current_value:.4f}\n"
                report += f"- Baseline: {alert.baseline_value:.4f}\n\n"

        # Detailed results
        if result.detailed_comparisons:
            report += "## Detailed Comparison\n\n"
            report += "| Benchmark | Metric | Current | Baseline | Change | Status |\n"
            report += "|-----------|--------|---------|----------|--------|---------|\n"

            for comparison in result.detailed_comparisons:
                name = comparison["name"]

                # Execution time row
                et = comparison["execution_time"]
                change = f"{et['change_percent']:+.1f}%"
                icon = "❌" if et["change_direction"] == "regression" else "✅"
                report += f"| {name} | execution_time | {et['current']:.4f}s | {et['baseline']:.4f}s | {change} | {icon} |\n"

                # Memory usage row (if available)
                if "memory_usage" in comparison:
                    mem = comparison["memory_usage"]
                    change = f"{mem['change_percent']:+.1f}%"
                    icon = "❌" if mem["change_direction"] == "regression" else "✅"
                    report += f"| {name} | memory_usage | {mem['current']:.1f}MB | {mem['baseline']:.1f}MB | {change} | {icon} |\n"

                # Throughput row (if available)
                if "throughput" in comparison:
                    thr = comparison["throughput"]
                    change = f"{thr['change_percent']:+.1f}%"
                    icon = "✅" if thr["change_direction"] == "improvement" else "❌"
                    report += f"| {name} | throughput | {thr['current']:.1f}/s | {thr['baseline']:.1f}/s | {change} | {icon} |\n"

        return report

    def _generate_github_report(self, result: ComparisonResult) -> str:
        """Generate GitHub Actions format report."""
        if result.regressions_count > 0:
            return f"::error::Performance regression detected in {result.regressions_count} benchmark(s)"
        elif result.warnings_count > 0:
            return f"::warning::Performance warnings in {result.warnings_count} benchmark(s)"
        else:
            return f"::notice::Performance check passed - {result.total_benchmarks} benchmarks analyzed"

    def _generate_json_report(self, result: ComparisonResult) -> str:
        """Generate JSON format report."""
        report_data = {
            "baseline_build_id": result.baseline_build_id,
            "current_build_id": result.current_build_id,
            "comparison_mode": result.comparison_mode.value,
            "summary": {
                "total_benchmarks": result.total_benchmarks,
                "regressions_count": result.regressions_count,
                "warnings_count": result.warnings_count,
                "improvements_count": result.improvements_count,
                "stable_count": result.stable_count,
            },
            "alerts": [
                {
                    "metric_name": alert.metric_name,
                    "benchmark_name": alert.benchmark_name,
                    "severity": alert.severity.value,
                    "message": alert.message,
                    "current_value": alert.current_value,
                    "baseline_value": alert.baseline_value,
                    "change_percent": alert.change_percent,
                    "threshold_violated": alert.threshold_violated,
                }
                for alert in result.alerts
            ],
            "detailed_comparisons": result.detailed_comparisons,
            "statistical_summary": result.statistical_summary,
        }

        return json.dumps(report_data, indent=2)
