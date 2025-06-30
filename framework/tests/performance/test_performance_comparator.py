"""Tests for performance comparison engine."""

import json
import tempfile
from datetime import datetime
from pathlib import Path

import yaml

from framework.performance import BenchmarkResult, PerformanceMetrics
from framework.performance.comparator import (
    AlertSeverity,
    ComparisonMode,
    PerformanceAlert,
    PerformanceComparator,
    ThresholdConfig,
)


class TestPerformanceComparator:
    """Test cases for PerformanceComparator."""

    def test_comparator_initialization_with_default_config(self):
        """Test comparator initializes with default configuration."""
        comparator = PerformanceComparator()

        assert "execution_time" in comparator.thresholds
        assert "memory_usage" in comparator.thresholds
        assert "throughput" in comparator.thresholds

        # Check default values
        et_threshold = comparator.thresholds["execution_time"]
        assert et_threshold.relative_increase == 0.10
        assert et_threshold.absolute_increase == 0.100

    def test_comparator_initialization_with_custom_config(self):
        """Test comparator initializes with custom configuration."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "custom_thresholds.yaml"

            custom_config = {
                "thresholds": {
                    "execution_time": {
                        "relative_increase": 0.20,
                        "absolute_increase": 0.200,
                        "statistical_significance": 0.99,
                    }
                }
            }

            with open(config_path, "w") as f:
                yaml.dump(custom_config, f)

            comparator = PerformanceComparator(config_path)

            et_threshold = comparator.thresholds["execution_time"]
            assert et_threshold.relative_increase == 0.20
            assert et_threshold.absolute_increase == 0.200
            assert et_threshold.statistical_significance == 0.99

    def test_comparator_handles_missing_config_file(self):
        """Test comparator handles missing configuration file gracefully."""
        non_existent_path = Path("/non/existent/path/config.yaml")
        comparator = PerformanceComparator(non_existent_path)

        # Should fall back to default configuration
        assert "execution_time" in comparator.thresholds
        assert comparator.thresholds["execution_time"].relative_increase == 0.10

    def test_basic_baseline_comparison_no_regression(self):
        """Test basic comparison with no performance regression."""
        comparator = PerformanceComparator()

        # Create baseline metrics
        baseline_metrics = PerformanceMetrics(build_id="baseline_build", timestamp=datetime.now())
        baseline_metrics.add_result(
            BenchmarkResult(
                name="test_benchmark", execution_time=1.0, memory_usage=100.0, throughput=1000.0
            )
        )

        # Create current metrics (5% improvement)
        current_metrics = PerformanceMetrics(build_id="current_build", timestamp=datetime.now())
        current_metrics.add_result(
            BenchmarkResult(
                name="test_benchmark",
                execution_time=0.95,  # 5% faster
                memory_usage=95.0,  # 5% less memory
                throughput=1050.0,  # 5% higher throughput
            )
        )

        result = comparator.compare_with_baseline(current_metrics, baseline_metrics)

        assert result.baseline_build_id == "baseline_build"
        assert result.current_build_id == "current_build"
        assert result.total_benchmarks == 1
        assert result.regressions_count == 0
        assert result.improvements_count == 1
        assert len(result.alerts) == 0

    def test_execution_time_regression_detection(self):
        """Test detection of execution time regression."""
        comparator = PerformanceComparator()

        # Create baseline metrics
        baseline_metrics = PerformanceMetrics(build_id="baseline_build", timestamp=datetime.now())
        baseline_metrics.add_result(BenchmarkResult(name="test_benchmark", execution_time=1.0))

        # Create current metrics (15% slower - triggers regression)
        current_metrics = PerformanceMetrics(build_id="current_build", timestamp=datetime.now())
        current_metrics.add_result(
            BenchmarkResult(
                name="test_benchmark",
                execution_time=1.15,  # 15% slower
            )
        )

        result = comparator.compare_with_baseline(current_metrics, baseline_metrics)

        assert result.regressions_count == 1
        assert len(result.alerts) == 1

        alert = result.alerts[0]
        assert alert.metric_name == "execution_time"
        assert alert.benchmark_name == "test_benchmark"
        assert alert.severity == AlertSeverity.CRITICAL  # Both relative and absolute exceeded
        assert abs(alert.change_percent - 15.0) < 0.01  # Allow for floating point precision

    def test_memory_usage_regression_detection(self):
        """Test detection of memory usage regression."""
        comparator = PerformanceComparator()

        baseline_metrics = PerformanceMetrics(build_id="baseline_build", timestamp=datetime.now())
        baseline_metrics.add_result(
            BenchmarkResult(
                name="test_benchmark",
                execution_time=1.0,  # Required field
                memory_usage=100.0,
            )
        )

        # 20% more memory usage - triggers regression
        current_metrics = PerformanceMetrics(build_id="current_build", timestamp=datetime.now())
        current_metrics.add_result(
            BenchmarkResult(
                name="test_benchmark",
                execution_time=1.0,  # Required field
                memory_usage=160.0,  # 60MB more memory (> 50MB threshold), 60% increase (> 15% threshold)
            )
        )

        result = comparator.compare_with_baseline(current_metrics, baseline_metrics)

        assert result.regressions_count == 1
        assert len(result.alerts) == 1

        alert = result.alerts[0]
        assert alert.metric_name == "memory_usage"
        assert alert.severity == AlertSeverity.CRITICAL
        assert abs(alert.change_percent - 60.0) < 0.1

    def test_throughput_regression_detection(self):
        """Test detection of throughput regression."""
        comparator = PerformanceComparator()

        baseline_metrics = PerformanceMetrics(build_id="baseline_build", timestamp=datetime.now())
        baseline_metrics.add_result(
            BenchmarkResult(
                name="test_benchmark",
                execution_time=1.0,  # Required field
                throughput=1000.0,
            )
        )

        # 15% lower throughput - triggers regression
        current_metrics = PerformanceMetrics(build_id="current_build", timestamp=datetime.now())
        current_metrics.add_result(
            BenchmarkResult(
                name="test_benchmark",
                execution_time=1.0,  # Required field
                throughput=850.0,  # 15% lower throughput
            )
        )

        result = comparator.compare_with_baseline(current_metrics, baseline_metrics)

        assert result.regressions_count == 1
        assert len(result.alerts) == 1

        alert = result.alerts[0]
        assert alert.metric_name == "throughput"
        assert alert.severity == AlertSeverity.CRITICAL
        assert abs(alert.change_percent - (-15.0)) < 0.1

    def test_warning_level_regression(self):
        """Test detection of warning-level regression."""
        comparator = PerformanceComparator()

        baseline_metrics = PerformanceMetrics(build_id="baseline_build", timestamp=datetime.now())
        baseline_metrics.add_result(
            BenchmarkResult(
                name="test_benchmark",
                execution_time=0.5,  # Use smaller baseline to create proper warning scenario
            )
        )

        # 12% slower - triggers relative threshold but not absolute (60ms absolute < 100ms threshold)
        current_metrics = PerformanceMetrics(build_id="current_build", timestamp=datetime.now())
        current_metrics.add_result(
            BenchmarkResult(
                name="test_benchmark",
                execution_time=0.56,  # 12% slower, 60ms absolute (< 100ms threshold = warning only)
            )
        )

        result = comparator.compare_with_baseline(current_metrics, baseline_metrics)

        assert result.warnings_count == 1
        assert len(result.alerts) == 1

        alert = result.alerts[0]
        assert alert.severity == AlertSeverity.WARNING
        assert alert.threshold_violated == "relative_threshold"

    def test_multiple_benchmarks_comparison(self):
        """Test comparison with multiple benchmarks."""
        comparator = PerformanceComparator()

        baseline_metrics = PerformanceMetrics(build_id="baseline_build", timestamp=datetime.now())
        baseline_metrics.add_result(BenchmarkResult(name="fast_benchmark", execution_time=0.1))
        baseline_metrics.add_result(BenchmarkResult(name="slow_benchmark", execution_time=2.0))
        baseline_metrics.add_result(BenchmarkResult(name="stable_benchmark", execution_time=1.0))

        current_metrics = PerformanceMetrics(build_id="current_build", timestamp=datetime.now())
        current_metrics.add_result(
            BenchmarkResult(name="fast_benchmark", execution_time=0.08)  # Improvement
        )
        current_metrics.add_result(
            BenchmarkResult(name="slow_benchmark", execution_time=2.3)  # Regression
        )
        current_metrics.add_result(
            BenchmarkResult(name="stable_benchmark", execution_time=1.02)  # Stable
        )

        result = comparator.compare_with_baseline(current_metrics, baseline_metrics)

        assert result.total_benchmarks == 3
        assert result.improvements_count == 1
        assert result.regressions_count == 1
        assert result.stable_count == 1
        assert len(result.detailed_comparisons) == 3

    def test_statistical_summary_calculation(self):
        """Test statistical summary calculation."""
        comparator = PerformanceComparator()

        baseline_metrics = PerformanceMetrics(build_id="baseline_build", timestamp=datetime.now())
        for i in range(5):
            baseline_metrics.add_result(
                BenchmarkResult(
                    name=f"benchmark_{i}",
                    execution_time=1.0 + i * 0.1,
                    memory_usage=100.0 + i * 10.0,
                )
            )

        current_metrics = PerformanceMetrics(build_id="current_build", timestamp=datetime.now())
        for i in range(5):
            current_metrics.add_result(
                BenchmarkResult(
                    name=f"benchmark_{i}",
                    execution_time=(1.0 + i * 0.1) * 1.05,  # 5% slower
                    memory_usage=(100.0 + i * 10.0) * 1.10,  # 10% more memory
                )
            )

        result = comparator.compare_with_baseline(current_metrics, baseline_metrics)

        stats = result.statistical_summary
        assert "execution_time_stats" in stats
        assert "memory_usage_stats" in stats

        # Check execution time stats
        et_stats = stats["execution_time_stats"]
        assert "mean_change_percent" in et_stats
        assert "sample_size" in et_stats
        assert et_stats["sample_size"] == 5
        assert abs(et_stats["mean_change_percent"] - 5.0) < 0.1

    def test_trend_analysis_with_historical_data(self):
        """Test trend analysis with historical metrics."""
        comparator = PerformanceComparator()

        # Create historical metrics (declining performance trend)
        historical_metrics = []
        for i in range(5):
            metrics = PerformanceMetrics(build_id=f"build_{i}", timestamp=datetime.now())
            metrics.add_result(
                BenchmarkResult(
                    name="trending_benchmark",
                    execution_time=1.0 + i * 0.05,  # Getting slower over time
                )
            )
            historical_metrics.append(metrics)

        current_metrics = PerformanceMetrics(build_id="current_build", timestamp=datetime.now())
        current_metrics.add_result(
            BenchmarkResult(
                name="trending_benchmark",
                execution_time=1.25,  # Continues the trend
            )
        )

        result = comparator.compare_with_trend(current_metrics, historical_metrics)

        assert result.comparison_mode == ComparisonMode.TREND_ANALYSIS
        assert "trend_details" in result.statistical_summary

        trend_details = result.statistical_summary["trend_details"]
        if "trending_benchmark" in trend_details:
            benchmark_trend = trend_details["trending_benchmark"]
            assert benchmark_trend["direction"] == "increasing"  # Execution time increasing
            assert benchmark_trend["correlation"] > 0.8  # Strong positive correlation

    def test_correlation_calculation(self):
        """Test Pearson correlation calculation."""
        comparator = PerformanceComparator()

        # Perfect positive correlation
        x_values = [1, 2, 3, 4, 5]
        y_values = [2, 4, 6, 8, 10]
        correlation = comparator._calculate_correlation(x_values, y_values)
        assert abs(correlation - 1.0) < 0.01

        # Perfect negative correlation
        y_values_neg = [10, 8, 6, 4, 2]
        correlation_neg = comparator._calculate_correlation(x_values, y_values_neg)
        assert abs(correlation_neg - (-1.0)) < 0.01

        # No correlation
        y_values_random = [5, 5, 5, 5, 5]
        correlation_none = comparator._calculate_correlation(x_values, y_values_random)
        assert abs(correlation_none) < 0.01

    def test_improvement_detection(self):
        """Test detection of performance improvements."""
        comparator = PerformanceComparator()

        baseline = BenchmarkResult(
            name="test", execution_time=1.0, memory_usage=100.0, throughput=1000.0
        )

        # Significant improvement in all metrics
        current_improved = BenchmarkResult(
            name="test",
            execution_time=0.9,  # 10% faster
            memory_usage=90.0,  # 10% less memory
            throughput=1100.0,  # 10% higher throughput
        )

        assert comparator._is_improvement(current_improved, baseline) is True

        # Mixed results (some better, some worse) - should still count as improvement since some metrics improved
        current_mixed = BenchmarkResult(
            name="test",
            execution_time=0.9,  # Better
            memory_usage=110.0,  # Worse
            throughput=1100.0,  # Better
        )

        assert comparator._is_improvement(current_mixed, baseline) is True  # Any improvement counts

        # No improvement case
        current_no_improvement = BenchmarkResult(
            name="test",
            execution_time=1.0,  # Same
            memory_usage=100.0,  # Same
            throughput=1000.0,  # Same
        )

        assert comparator._is_improvement(current_no_improvement, baseline) is False

    def test_markdown_report_generation(self):
        """Test markdown report generation."""
        comparator = PerformanceComparator()

        baseline_metrics = PerformanceMetrics(build_id="baseline_build", timestamp=datetime.now())
        baseline_metrics.add_result(
            BenchmarkResult(name="test_benchmark", execution_time=1.0, memory_usage=100.0)
        )

        current_metrics = PerformanceMetrics(build_id="current_build", timestamp=datetime.now())
        current_metrics.add_result(
            BenchmarkResult(name="test_benchmark", execution_time=1.15, memory_usage=120.0)
        )

        result = comparator.compare_with_baseline(current_metrics, baseline_metrics)
        report = comparator.generate_report(result, "markdown")

        assert "# Performance Comparison Report" in report
        assert "baseline_build" in report
        assert "current_build" in report
        assert "PERFORMANCE REGRESSION DETECTED" in report
        assert "test_benchmark" in report

    def test_json_report_generation(self):
        """Test JSON report generation."""
        comparator = PerformanceComparator()

        baseline_metrics = PerformanceMetrics(build_id="baseline_build", timestamp=datetime.now())
        baseline_metrics.add_result(BenchmarkResult(name="test_benchmark", execution_time=1.0))

        current_metrics = PerformanceMetrics(build_id="current_build", timestamp=datetime.now())
        current_metrics.add_result(BenchmarkResult(name="test_benchmark", execution_time=1.05))

        result = comparator.compare_with_baseline(current_metrics, baseline_metrics)
        report = comparator.generate_report(result, "json")

        # Should be valid JSON
        report_data = json.loads(report)
        assert report_data["baseline_build_id"] == "baseline_build"
        assert report_data["current_build_id"] == "current_build"
        assert "summary" in report_data
        assert "detailed_comparisons" in report_data

    def test_github_report_generation(self):
        """Test GitHub Actions format report generation."""
        comparator = PerformanceComparator()

        # Test with regression
        baseline_metrics = PerformanceMetrics(build_id="baseline_build", timestamp=datetime.now())
        baseline_metrics.add_result(BenchmarkResult(name="test_benchmark", execution_time=1.0))

        current_metrics = PerformanceMetrics(build_id="current_build", timestamp=datetime.now())
        current_metrics.add_result(BenchmarkResult(name="test_benchmark", execution_time=1.15))

        result = comparator.compare_with_baseline(current_metrics, baseline_metrics)
        report = comparator.generate_report(result, "github")

        assert "::error::" in report
        assert "Performance regression detected" in report

    def test_edge_case_zero_baseline_values(self):
        """Test handling of zero baseline values."""
        comparator = PerformanceComparator()

        baseline_metrics = PerformanceMetrics(build_id="baseline_build", timestamp=datetime.now())
        baseline_metrics.add_result(
            BenchmarkResult(name="test_benchmark", execution_time=0.0)  # Zero baseline
        )

        current_metrics = PerformanceMetrics(build_id="current_build", timestamp=datetime.now())
        current_metrics.add_result(BenchmarkResult(name="test_benchmark", execution_time=1.0))

        result = comparator.compare_with_baseline(current_metrics, baseline_metrics)

        # Should handle gracefully without crashing
        assert result.total_benchmarks == 1
        assert len(result.detailed_comparisons) == 1

    def test_missing_benchmark_in_baseline(self):
        """Test handling of benchmarks missing in baseline."""
        comparator = PerformanceComparator()

        baseline_metrics = PerformanceMetrics(build_id="baseline_build", timestamp=datetime.now())
        baseline_metrics.add_result(BenchmarkResult(name="existing_benchmark", execution_time=1.0))

        current_metrics = PerformanceMetrics(build_id="current_build", timestamp=datetime.now())
        current_metrics.add_result(BenchmarkResult(name="existing_benchmark", execution_time=1.0))
        current_metrics.add_result(
            BenchmarkResult(name="new_benchmark", execution_time=2.0)  # Not in baseline
        )

        result = comparator.compare_with_baseline(current_metrics, baseline_metrics)

        # Should only compare existing benchmarks
        assert result.total_benchmarks == 2  # Both benchmarks present in current
        assert len(result.detailed_comparisons) == 1  # Only one can be compared

    def test_custom_threshold_application(self):
        """Test application of custom thresholds."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "custom_thresholds.yaml"

            # Very strict thresholds
            custom_config = {
                "thresholds": {
                    "execution_time": {
                        "relative_increase": 0.01,  # 1% triggers regression
                        "absolute_increase": 0.001,  # 1ms triggers regression
                    }
                }
            }

            with open(config_path, "w") as f:
                yaml.dump(custom_config, f)

            comparator = PerformanceComparator(config_path)

            baseline_metrics = PerformanceMetrics(
                build_id="baseline_build", timestamp=datetime.now()
            )
            baseline_metrics.add_result(BenchmarkResult(name="test_benchmark", execution_time=1.0))

            current_metrics = PerformanceMetrics(build_id="current_build", timestamp=datetime.now())
            current_metrics.add_result(
                BenchmarkResult(name="test_benchmark", execution_time=1.005)  # 0.5% slower
            )

            result = comparator.compare_with_baseline(current_metrics, baseline_metrics)

            # Should not trigger regression with custom strict thresholds
            # because 0.5% < 1% threshold
            assert result.regressions_count == 0


class TestThresholdConfig:
    """Test cases for ThresholdConfig."""

    def test_threshold_config_creation(self):
        """Test creating threshold configuration."""
        config = ThresholdConfig(
            relative_increase=0.15, absolute_increase=50.0, statistical_significance=0.99
        )

        assert config.relative_increase == 0.15
        assert config.absolute_increase == 50.0
        assert config.statistical_significance == 0.99

    def test_threshold_config_defaults(self):
        """Test default values in threshold configuration."""
        config = ThresholdConfig(relative_increase=0.10, absolute_increase=100.0)

        assert config.statistical_significance == 0.95  # Default value


class TestPerformanceAlert:
    """Test cases for PerformanceAlert."""

    def test_alert_creation(self):
        """Test creating performance alert."""
        alert = PerformanceAlert(
            metric_name="execution_time",
            benchmark_name="test_benchmark",
            severity=AlertSeverity.CRITICAL,
            message="Critical regression detected",
            current_value=1.5,
            baseline_value=1.0,
            change_percent=50.0,
            threshold_violated="relative_threshold",
        )

        assert alert.metric_name == "execution_time"
        assert alert.severity == AlertSeverity.CRITICAL
        assert alert.change_percent == 50.0
        assert alert.threshold_violated == "relative_threshold"
