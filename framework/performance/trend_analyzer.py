"""Advanced trend analysis and alerting system for performance data."""

import json
import os
import statistics
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, TypedDict

import yaml

from .comparator import AlertSeverity, PerformanceAlert
from .models import PerformanceMetrics


class BenchmarkData(TypedDict):
    """Type definition for benchmark data storage."""

    values: list[float]
    timestamps: list[datetime]


@dataclass
class TrendData:
    """Historical trend data for a specific metric."""

    metric_name: str
    benchmark_name: str
    values: list[float] = field(default_factory=list)
    timestamps: list[datetime] = field(default_factory=list)
    correlation: float = 0.0
    trend_direction: str = "stable"  # "increasing", "decreasing", "stable"
    moving_average: list[float] = field(default_factory=list)
    anomaly_scores: list[float] = field(default_factory=list)


@dataclass
class AlertCooldown:
    """Cooldown tracking for alert generation."""

    benchmark_name: str
    metric_name: str
    last_alert_time: datetime
    severity: AlertSeverity


@dataclass
class TrendAlert(PerformanceAlert):
    """Extended performance alert with trend analysis data."""

    trend_direction: str = "unknown"
    trend_strength: float = 0.0
    anomaly_score: float = 0.0
    historical_context: str = ""
    root_cause_indicators: list[str] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)


class TrendAnalyzer:
    """Advanced analytics engine for performance data trend analysis and alerting."""

    def __init__(
        self, alert_config_path: str | Path | None = None, github_token: str | None = None
    ):
        """Initialize the trend analyzer.

        Args:
            alert_config_path: Path to alert configuration file.
            github_token: GitHub API token for issue creation.
        """
        if alert_config_path is None:
            alert_config_path = Path(__file__).parent / "alert_config.yaml"

        self.alert_config_path = Path(alert_config_path)
        self.github_token = github_token or os.getenv("GITHUB_TOKEN")
        self.config = self._load_alert_config()
        self.cooldown_data = self._load_cooldown_data()

    def _load_alert_config(self) -> dict[str, Any]:
        """Load alerting configuration from YAML file."""
        if not self.alert_config_path.exists():
            return self._get_default_config()

        try:
            with open(self.alert_config_path) as f:
                return yaml.safe_load(f)
        except (yaml.YAMLError, FileNotFoundError) as e:
            print(f"Warning: Failed to load alert config: {e}")
            return self._get_default_config()

    def _get_default_config(self) -> dict[str, Any]:
        """Get default alert configuration."""
        return {
            "alert_channels": ["step_summary"],
            "alert_thresholds": {"critical": 0.25, "warning": 0.10, "improvement": 0.05},
            "alert_cooldown": 24,
            "trend_analysis": {
                "min_data_points": 5,
                "correlation_threshold": 0.7,
                "anomaly_std_dev_multiplier": 2.0,
                "moving_average_window": 10,
            },
            "templates": {
                "issue_body": "Performance regression detected in {benchmark_name}",
                "step_summary_format": "Performance alert: {severity}",
            },
        }

    def _load_cooldown_data(self) -> dict[str, AlertCooldown]:
        """Load alert cooldown data from storage."""
        cooldown_file = self.config.get("cooldown_storage", ".performance_alerts_cooldown.json")
        cooldown_path = Path(cooldown_file)

        if not cooldown_path.exists():
            return {}

        try:
            with open(cooldown_path) as f:
                data = json.load(f)

            cooldowns = {}
            for key, cooldown_data in data.items():
                cooldowns[key] = AlertCooldown(
                    benchmark_name=cooldown_data["benchmark_name"],
                    metric_name=cooldown_data["metric_name"],
                    last_alert_time=datetime.fromisoformat(cooldown_data["last_alert_time"]),
                    severity=AlertSeverity(cooldown_data["severity"]),
                )

            return cooldowns
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            print(f"Warning: Failed to load cooldown data: {e}")
            return {}

    def _save_cooldown_data(self) -> None:
        """Save alert cooldown data to storage."""
        cooldown_file = self.config.get("cooldown_storage", ".performance_alerts_cooldown.json")
        cooldown_path = Path(cooldown_file)

        data = {}
        for key, cooldown in self.cooldown_data.items():
            data[key] = {
                "benchmark_name": cooldown.benchmark_name,
                "metric_name": cooldown.metric_name,
                "last_alert_time": cooldown.last_alert_time.isoformat(),
                "severity": cooldown.severity.value,
            }

        try:
            with open(cooldown_path, "w") as f:
                json.dump(data, f, indent=2)
        except OSError as e:
            print(f"Warning: Failed to save cooldown data: {e}")

    def analyze_trends(
        self, historical_metrics: list[PerformanceMetrics], time_window: timedelta | None = None
    ) -> dict[str, TrendData]:
        """Analyze historical trends for all benchmarks and metrics.

        Args:
            historical_metrics: List of historical performance metrics.
            time_window: Optional time window to limit analysis scope.

        Returns:
            Dictionary mapping benchmark.metric keys to trend data.
        """
        trends = {}
        min_data_points = self.config["trend_analysis"]["min_data_points"]

        # Filter by time window if specified
        if time_window:
            cutoff_time = datetime.now() - time_window
            historical_metrics = [
                m for m in historical_metrics if m.timestamp and m.timestamp >= cutoff_time
            ]

        # Group data by benchmark and metric
        benchmark_data: dict[str, BenchmarkData] = {}
        for metrics in historical_metrics:
            for result in metrics.results:
                key_exec = f"{result.name}.execution_time"
                if key_exec not in benchmark_data:
                    benchmark_data[key_exec] = {"values": [], "timestamps": []}

                if result.execution_time is not None:
                    benchmark_data[key_exec]["values"].append(result.execution_time)
                    benchmark_data[key_exec]["timestamps"].append(
                        metrics.timestamp or datetime.now()
                    )

                # Memory usage
                if result.memory_usage is not None:
                    key_mem = f"{result.name}.memory_usage"
                    if key_mem not in benchmark_data:
                        benchmark_data[key_mem] = {"values": [], "timestamps": []}
                    benchmark_data[key_mem]["values"].append(result.memory_usage)
                    benchmark_data[key_mem]["timestamps"].append(
                        metrics.timestamp or datetime.now()
                    )

                # Throughput
                if result.throughput is not None:
                    key_thr = f"{result.name}.throughput"
                    if key_thr not in benchmark_data:
                        benchmark_data[key_thr] = {"values": [], "timestamps": []}
                    benchmark_data[key_thr]["values"].append(result.throughput)
                    benchmark_data[key_thr]["timestamps"].append(
                        metrics.timestamp or datetime.now()
                    )

        # Analyze trends for each benchmark/metric combination
        for key, data in benchmark_data.items():
            if len(data["values"]) >= min_data_points:
                benchmark_name, metric_name = key.split(".", 1)
                trend_data = self._analyze_single_trend(
                    benchmark_name, metric_name, data["values"], data["timestamps"]
                )
                trends[key] = trend_data

        return trends

    def _analyze_single_trend(
        self, benchmark_name: str, metric_name: str, values: list[float], timestamps: list[datetime]
    ) -> TrendData:
        """Analyze trend for a single benchmark/metric combination."""
        # Calculate correlation with time sequence
        x_values = list(range(len(values)))
        correlation = self._calculate_correlation(x_values, values)

        # Determine trend direction
        correlation_threshold = self.config["trend_analysis"]["correlation_threshold"]
        if correlation > correlation_threshold:
            trend_direction = "increasing"
        elif correlation < -correlation_threshold:
            trend_direction = "decreasing"
        else:
            trend_direction = "stable"

        # Calculate moving average
        window_size = self.config["trend_analysis"]["moving_average_window"]
        moving_average = self._calculate_moving_average(values, window_size)

        # Calculate anomaly scores
        anomaly_scores = self._calculate_anomaly_scores(values)

        return TrendData(
            metric_name=metric_name,
            benchmark_name=benchmark_name,
            values=values.copy(),
            timestamps=timestamps.copy(),
            correlation=correlation,
            trend_direction=trend_direction,
            moving_average=moving_average,
            anomaly_scores=anomaly_scores,
        )

    def _calculate_correlation(self, x_values: list[int], y_values: list[float]) -> float:
        """Calculate Pearson correlation coefficient."""
        if len(x_values) != len(y_values) or len(x_values) < 2:
            return 0.0

        try:
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
        except (ValueError, ZeroDivisionError):
            return 0.0

    def _calculate_moving_average(self, values: list[float], window_size: int) -> list[float]:
        """Calculate moving average with specified window size."""
        if window_size <= 0 or len(values) < window_size:
            return values.copy()

        moving_avg = []
        for i in range(len(values)):
            start_idx = max(0, i - window_size + 1)
            window_values = values[start_idx : i + 1]
            moving_avg.append(statistics.mean(window_values))

        return moving_avg

    def _calculate_anomaly_scores(self, values: list[float]) -> list[float]:
        """Calculate anomaly scores based on standard deviation."""
        if len(values) < 2:
            return [0.0] * len(values)

        mean_val = statistics.mean(values)
        std_dev = statistics.stdev(values)

        if std_dev == 0:
            return [0.0] * len(values)

        # Calculate z-scores
        return [abs((val - mean_val) / std_dev) for val in values]

    def detect_anomalies(
        self, current_metrics: PerformanceMetrics, trends: dict[str, TrendData]
    ) -> list[TrendAlert]:
        """Detect anomalies in current data compared to historical trends.

        Args:
            current_metrics: Current performance metrics.
            trends: Historical trend data.

        Returns:
            List of trend alerts for detected anomalies.
        """
        alerts = []
        anomaly_threshold = self.config["trend_analysis"]["anomaly_std_dev_multiplier"]

        for result in current_metrics.results:
            # Check execution time
            if result.execution_time is not None:
                key = f"{result.name}.execution_time"
                if key in trends:
                    alert = self._check_metric_anomaly(
                        trends[key], result.execution_time, "execution_time", anomaly_threshold
                    )
                    if alert:
                        alerts.append(alert)

            # Check memory usage
            if result.memory_usage is not None:
                key = f"{result.name}.memory_usage"
                if key in trends:
                    alert = self._check_metric_anomaly(
                        trends[key], result.memory_usage, "memory_usage", anomaly_threshold
                    )
                    if alert:
                        alerts.append(alert)

            # Check throughput
            if result.throughput is not None:
                key = f"{result.name}.throughput"
                if key in trends:
                    alert = self._check_metric_anomaly(
                        trends[key], result.throughput, "throughput", anomaly_threshold
                    )
                    if alert:
                        alerts.append(alert)

        return alerts

    def _check_metric_anomaly(
        self,
        trend_data: TrendData,
        current_value: float,
        metric_type: str,
        anomaly_threshold: float,
    ) -> TrendAlert | None:
        """Check if current value is anomalous based on trend data."""
        if len(trend_data.values) < 2:
            return None

        mean_val = statistics.mean(trend_data.values)
        std_dev = statistics.stdev(trend_data.values) if len(trend_data.values) > 1 else 0.0

        if std_dev == 0:
            return None

        # Calculate z-score
        z_score = abs((current_value - mean_val) / std_dev)

        if z_score >= anomaly_threshold:
            # Determine severity based on change magnitude
            change_percent = ((current_value - mean_val) / mean_val) * 100 if mean_val != 0 else 0

            severity = self._determine_severity(abs(change_percent), metric_type)

            # Generate recommendations and root cause analysis
            recommendations = self._generate_recommendations(
                metric_type, change_percent, trend_data
            )
            root_cause_indicators = self._analyze_root_cause(trend_data, current_value, z_score)

            return TrendAlert(
                metric_name=metric_type,
                benchmark_name=trend_data.benchmark_name,
                severity=severity,
                message=f"Anomaly detected in {metric_type}: {change_percent:+.1f}% deviation from historical average",
                current_value=current_value,
                baseline_value=mean_val,
                change_percent=change_percent,
                threshold_violated="anomaly_detection",
                trend_direction=trend_data.trend_direction,
                trend_strength=abs(trend_data.correlation),
                anomaly_score=z_score,
                historical_context=self._generate_historical_context(trend_data),
                root_cause_indicators=root_cause_indicators,
                recommendations=recommendations,
            )

        return None

    def _determine_severity(self, change_percent: float, metric_type: str) -> AlertSeverity:
        """Determine alert severity based on change magnitude."""
        critical_threshold = self.config["alert_thresholds"]["critical"] * 100
        warning_threshold = self.config["alert_thresholds"]["warning"] * 100

        if change_percent >= critical_threshold:
            return AlertSeverity.CRITICAL
        elif change_percent >= warning_threshold:
            return AlertSeverity.WARNING
        else:
            return AlertSeverity.INFO

    def _generate_recommendations(
        self, metric_type: str, change_percent: float, trend_data: TrendData
    ) -> list[str]:
        """Generate actionable recommendations based on the alert."""
        recommendations = []

        if metric_type == "execution_time" and change_percent > 0:
            recommendations.extend(
                [
                    "Review recent code changes for performance bottlenecks",
                    "Check for inefficient algorithms or database queries",
                    "Consider profiling the affected benchmark",
                    "Verify system resources (CPU, memory) during test execution",
                ]
            )
        elif metric_type == "memory_usage" and change_percent > 0:
            recommendations.extend(
                [
                    "Investigate memory leaks in recent code changes",
                    "Review object allocation patterns",
                    "Check for unclosed resources or connections",
                    "Consider memory profiling tools",
                ]
            )
        elif metric_type == "throughput" and change_percent < 0:
            recommendations.extend(
                [
                    "Review concurrent execution patterns",
                    "Check for blocking operations or contention",
                    "Investigate network or I/O bottlenecks",
                    "Verify system load during benchmark execution",
                ]
            )

        # Add trend-specific recommendations
        if trend_data.trend_direction == "increasing" and metric_type in [
            "execution_time",
            "memory_usage",
        ]:
            recommendations.append(
                "Consider implementing performance monitoring to catch gradual degradation"
            )
        elif trend_data.trend_direction == "decreasing" and metric_type == "throughput":
            recommendations.append(
                "Review recent changes that may have introduced gradual performance degradation"
            )

        return recommendations

    def _analyze_root_cause(
        self, trend_data: TrendData, current_value: float, anomaly_score: float
    ) -> list[str]:
        """Analyze potential root causes for the anomaly."""
        indicators = []

        # Anomaly severity
        if anomaly_score > 3.0:
            indicators.append("Extreme deviation from historical pattern (>3σ)")
        elif anomaly_score > 2.0:
            indicators.append("Significant deviation from historical pattern (>2σ)")

        # Trend analysis
        if trend_data.trend_direction != "stable":
            indicators.append(
                f"Part of {trend_data.trend_direction} trend (correlation: {trend_data.correlation:.2f})"
            )

        # Moving average comparison
        if trend_data.moving_average:
            recent_avg = (
                statistics.mean(trend_data.moving_average[-3:])
                if len(trend_data.moving_average) >= 3
                else trend_data.moving_average[-1]
            )
            if abs(current_value - recent_avg) / recent_avg > 0.1:
                indicators.append("Significant deviation from recent moving average")

        return indicators

    def _generate_historical_context(self, trend_data: TrendData) -> str:
        """Generate historical context description for the trend."""
        context_parts = []

        # Basic statistics
        if trend_data.values:
            min_val = min(trend_data.values)
            max_val = max(trend_data.values)
            avg_val = statistics.mean(trend_data.values)
            context_parts.append(
                f"Historical range: {min_val:.3f} - {max_val:.3f} (avg: {avg_val:.3f})"
            )

        # Trend information
        context_parts.append(
            f"Trend: {trend_data.trend_direction} (correlation: {trend_data.correlation:.2f})"
        )

        # Data points
        context_parts.append(f"Based on {len(trend_data.values)} historical measurements")

        return " | ".join(context_parts)

    def trigger_alerts(self, alerts: list[TrendAlert]) -> dict[str, Any]:
        """Generate and send alerts based on detected issues.

        Args:
            alerts: List of trend alerts to process.

        Returns:
            Summary of alert actions taken.
        """
        alert_summary: dict[str, Any] = {
            "alerts_processed": len(alerts),
            "github_issues_created": 0,
            "step_summaries_added": 0,
            "alerts_suppressed_by_cooldown": 0,
            "errors": [],
        }

        for alert in alerts:
            # Check cooldown
            if self._is_in_cooldown(alert):
                alert_summary["alerts_suppressed_by_cooldown"] += 1
                continue

            try:
                # Send alerts through configured channels
                if "github_issue" in self.config[
                    "alert_channels"
                ] and self._should_create_github_issue(alert):
                    self._create_github_issue(alert)
                    alert_summary["github_issues_created"] += 1

                if "step_summary" in self.config["alert_channels"]:
                    self._add_step_summary(alert)
                    alert_summary["step_summaries_added"] += 1

                # Update cooldown
                self._update_cooldown(alert)

            except Exception as e:
                alert_summary["errors"].append(
                    f"Error processing alert for {alert.benchmark_name}: {e}"
                )

        # Save cooldown data
        self._save_cooldown_data()

        return alert_summary

    def _is_in_cooldown(self, alert: TrendAlert) -> bool:
        """Check if alert is in cooldown period."""
        key = f"{alert.benchmark_name}.{alert.metric_name}"
        if key not in self.cooldown_data:
            return False

        cooldown_hours = self.config["alert_cooldown"]
        cooldown_period = timedelta(hours=cooldown_hours)
        last_alert_time = self.cooldown_data[key].last_alert_time

        return datetime.now() - last_alert_time < cooldown_period

    def _should_create_github_issue(self, alert: TrendAlert) -> bool:
        """Determine if a GitHub issue should be created for this alert."""
        github_config = self.config.get("github", {})

        if alert.severity == AlertSeverity.CRITICAL:
            return github_config.get("create_issues_for_critical", True)
        elif alert.severity == AlertSeverity.WARNING:
            return github_config.get("create_issues_for_warnings", False)

        return False

    def _create_github_issue(self, alert: TrendAlert) -> None:
        """Create a GitHub issue for the alert."""
        if not self.github_token:
            raise ValueError("GitHub token not available for issue creation")

        # This would integrate with GitHub API
        # For now, we'll create a placeholder that could be implemented
        # with the existing GitHubReporter from the reporting module
        print(
            f"GitHub issue would be created: {alert.severity.value.upper()} - {alert.benchmark_name}"
        )

    def _add_step_summary(self, alert: TrendAlert) -> None:
        """Add alert to GitHub Actions step summary."""
        templates = self.config.get("templates", {})
        severity_icons = self.config.get("severity_icons", {})

        summary_format = templates.get("step_summary_format", "Performance alert: {severity}")

        summary = summary_format.format(
            severity_icon=severity_icons.get(alert.severity.value, ""),
            severity=alert.severity.value.upper(),
            benchmark_name=alert.benchmark_name,
            metric_name=alert.metric_name,
            change_percent=alert.change_percent,
            current_value=alert.current_value,
            baseline_value=alert.baseline_value,
            trend_summary=f"Trend: {alert.trend_direction} (strength: {alert.trend_strength:.2f})",
        )

        # Write to GitHub Actions step summary if available
        github_step_summary = os.getenv("GITHUB_STEP_SUMMARY")
        if github_step_summary:
            try:
                with open(github_step_summary, "a") as f:
                    f.write(f"\n{summary}\n")
            except OSError as e:
                print(f"Failed to write step summary: {e}")
        else:
            print(f"Step Summary: {summary}")

    def _update_cooldown(self, alert: TrendAlert) -> None:
        """Update cooldown data for the alert."""
        key = f"{alert.benchmark_name}.{alert.metric_name}"
        self.cooldown_data[key] = AlertCooldown(
            benchmark_name=alert.benchmark_name,
            metric_name=alert.metric_name,
            last_alert_time=datetime.now(),
            severity=alert.severity,
        )
