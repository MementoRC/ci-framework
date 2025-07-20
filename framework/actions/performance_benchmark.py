"""
Performance Benchmark Action Implementation

Standardized performance monitoring with pytest-benchmark integration,
statistical regression detection, and historical trend analysis.
"""

import json
import os
import statistics
import subprocess
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class BenchmarkResult:
    """Individual benchmark result with statistical data"""

    name: str
    mean: float
    stddev: float
    min_value: float
    max_value: float
    rounds: int
    unit: str = "seconds"
    group: str = ""
    params: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class PerformanceMetrics:
    """Performance metrics and comparison data"""

    benchmarks: list[BenchmarkResult] = field(default_factory=list)
    execution_time: float = 0.0
    total_benchmarks: int = 0
    baseline_comparison: dict[str, Any] | None = None
    regression_detected: bool = False
    regression_percentage: float = 0.0
    trend_analysis: dict[str, Any] = field(default_factory=dict)
    environment_info: dict[str, Any] = field(default_factory=dict)


@dataclass
class RegressionAnalysis:
    """Statistical regression analysis results"""

    benchmark_name: str
    current_mean: float
    baseline_mean: float
    percentage_change: float
    is_regression: bool
    statistical_significance: float
    confidence_interval: tuple[float, float]
    effect_size: str  # "small", "medium", "large"


class PerformanceBenchmarkAction:
    """
    Performance benchmarking action with pytest-benchmark integration
    and statistical regression detection.
    """

    def __init__(self, config: dict[str, Any] | None = None):
        """Initialize the performance benchmark action."""
        self.config = config or {}
        self.default_config = {
            "regression_threshold": 10.0,
            "significance_level": 0.05,
            "min_rounds": 5,
            "max_rounds": 100,
            "timeout": 1800,
            "warmup_rounds": 3,
            "statistical_analysis": True,
            "trend_analysis": True,
            "store_historical": True,
        }

        # Merge configurations
        self.effective_config = {**self.default_config, **self.config}

    def detect_package_manager(self, project_dir: Path) -> str:
        """Detect the package manager used by the project."""
        if (project_dir / "pyproject.toml").exists():
            pyproject_content = (project_dir / "pyproject.toml").read_text()
            if "[tool.pixi" in pyproject_content:
                return "pixi"
            elif "[tool.poetry]" in pyproject_content:
                return "poetry"
            elif "[tool.hatch]" in pyproject_content:
                return "hatch"

        if (project_dir / "poetry.lock").exists():
            return "poetry"

        if (project_dir / "requirements.txt").exists():
            return "pip"

        return "pip"  # Default fallback

    def setup_benchmark_environment(
        self, project_dir: Path, package_manager: str
    ) -> bool:
        """Setup the benchmark environment with required dependencies."""
        try:
            os.chdir(project_dir)

            if package_manager == "pixi":
                # Check if pytest-benchmark is available in pixi environment
                result = subprocess.run(
                    ["pixi", "run", "python", "-c", "import pytest_benchmark"],
                    capture_output=True,
                    text=True,
                )
                if result.returncode != 0:
                    # Install pytest-benchmark
                    subprocess.run(
                        ["pixi", "run", "pip", "install", "pytest-benchmark"],
                        check=True,
                    )

            elif package_manager == "poetry":
                # Add pytest-benchmark to dev dependencies
                subprocess.run(
                    ["poetry", "add", "pytest-benchmark", "--group", "dev"], check=True
                )

            elif package_manager == "pip":
                # Install directly with pip
                subprocess.run(["pip", "install", "pytest-benchmark"], check=True)

            return True

        except subprocess.CalledProcessError as e:
            print(f"❌ Failed to setup benchmark environment: {e}")
            return False

    def run_benchmarks(
        self,
        project_dir: Path,
        suite: str,
        package_manager: str,
        timeout: int,
        parallel: bool = False,
    ) -> tuple[bool, dict[str, Any]]:
        """Execute pytest-benchmark with specified configuration."""

        results_file = project_dir / "benchmark-results.json"

        # Build pytest command
        cmd = ["python", "-m", "pytest", "--benchmark-only"]
        cmd.extend(["--benchmark-json", str(results_file)])

        # Configure benchmark parameters based on suite
        if suite == "quick":
            cmd.extend(
                [
                    "--benchmark-max-time=30",
                    "--benchmark-min-rounds=3",
                    "--benchmark-warmup-iterations=1",
                ]
            )
        elif suite == "full":
            cmd.extend(
                [
                    "--benchmark-max-time=300",
                    "--benchmark-min-rounds=5",
                    "--benchmark-warmup-iterations=3",
                ]
            )
        elif suite == "load":
            cmd.extend(
                [
                    "--benchmark-max-time=600",
                    "--benchmark-min-rounds=10",
                    "--benchmark-warmup-iterations=5",
                ]
            )

        # Add parallel execution if requested
        if parallel:
            cmd.extend(["-n", "auto"])

        # Execute with package manager wrapper
        if package_manager == "pixi":
            cmd = ["pixi", "run"] + cmd
        elif package_manager == "poetry":
            cmd = ["poetry", "run"] + cmd

        try:
            start_time = time.time()
            result = subprocess.run(
                cmd, cwd=project_dir, capture_output=True, text=True, timeout=timeout
            )
            execution_time = time.time() - start_time

            if result.returncode == 0:
                # Parse benchmark results
                if results_file.exists():
                    with open(results_file) as f:
                        benchmark_data = json.load(f)

                    return True, {
                        "execution_time": execution_time,
                        "benchmark_data": benchmark_data,
                        "stdout": result.stdout,
                        "stderr": result.stderr,
                    }
                else:
                    return False, {
                        "execution_time": execution_time,
                        "error": "No benchmark results file generated",
                        "stdout": result.stdout,
                        "stderr": result.stderr,
                    }
            else:
                return False, {
                    "execution_time": execution_time,
                    "error": f"Benchmark execution failed with code {result.returncode}",
                    "stdout": result.stdout,
                    "stderr": result.stderr,
                }

        except subprocess.TimeoutExpired:
            return False, {
                "execution_time": timeout,
                "error": "Benchmark execution timed out",
                "stdout": "",
                "stderr": "",
            }
        except Exception as e:
            return False, {
                "execution_time": 0,
                "error": f"Unexpected error: {str(e)}",
                "stdout": "",
                "stderr": "",
            }

    def parse_benchmark_results(
        self, benchmark_data: dict[str, Any]
    ) -> list[BenchmarkResult]:
        """Parse pytest-benchmark JSON output into BenchmarkResult objects."""
        results = []

        for benchmark in benchmark_data.get("benchmarks", []):
            stats = benchmark.get("stats", {})

            result = BenchmarkResult(
                name=benchmark.get("name", "unknown"),
                mean=stats.get("mean", 0.0),
                stddev=stats.get("stddev", 0.0),
                min_value=stats.get("min", 0.0),
                max_value=stats.get("max", 0.0),
                rounds=stats.get("rounds", 0),
                unit="seconds",  # pytest-benchmark default
                group=benchmark.get("group", ""),
                params=benchmark.get("params", {}),
                metadata={
                    "fullname": benchmark.get("fullname", ""),
                    "param": benchmark.get("param", None),
                    "ops": stats.get("ops", 0.0),
                    "data": stats.get("data", []),
                },
            )
            results.append(result)

        return results

    def load_baseline_results(
        self, baseline_dir: Path
    ) -> list[BenchmarkResult] | None:
        """Load baseline benchmark results for comparison."""
        baseline_file = baseline_dir / "benchmark-results.json"

        if not baseline_file.exists():
            return None

        try:
            with open(baseline_file) as f:
                baseline_data = json.load(f)

            return self.parse_benchmark_results(baseline_data)

        except Exception as e:
            print(f"⚠️ Failed to load baseline results: {e}")
            return None

    def analyze_regression(
        self,
        current_results: list[BenchmarkResult],
        baseline_results: list[BenchmarkResult],
        threshold: float,
    ) -> tuple[bool, list[RegressionAnalysis], float]:
        """
        Perform statistical regression analysis between current and baseline results.

        Returns:
            - regression_detected: bool indicating if any significant regression found
            - regression_analyses: List of detailed analysis for each benchmark
            - max_regression_percentage: Maximum regression percentage found
        """
        analyses = []
        max_regression = 0.0
        regression_detected = False

        # Create lookup dict for baseline results
        baseline_lookup = {result.name: result for result in baseline_results}

        for current in current_results:
            if current.name not in baseline_lookup:
                continue

            baseline = baseline_lookup[current.name]

            # Calculate percentage change
            if baseline.mean > 0:
                percentage_change = (
                    (current.mean - baseline.mean) / baseline.mean
                ) * 100
            else:
                percentage_change = 0.0

            # Determine if this is a regression (performance got worse)
            is_regression = percentage_change > threshold

            # Statistical significance calculation (simplified)
            # In a full implementation, you'd use proper statistical tests
            pooled_variance = (current.stddev**2 + baseline.stddev**2) / 2
            if pooled_variance > 0:
                t_stat = abs(current.mean - baseline.mean) / (pooled_variance**0.5)
                # Simplified significance (would normally use t-distribution)
                statistical_significance = min(1.0, t_stat / 2.0)
            else:
                statistical_significance = 0.0

            # Effect size classification
            if abs(percentage_change) < 5:
                effect_size = "small"
            elif abs(percentage_change) < 15:
                effect_size = "medium"
            else:
                effect_size = "large"

            # Confidence interval (simplified)
            margin = 1.96 * current.stddev  # 95% confidence
            confidence_interval = (current.mean - margin, current.mean + margin)

            analysis = RegressionAnalysis(
                benchmark_name=current.name,
                current_mean=current.mean,
                baseline_mean=baseline.mean,
                percentage_change=percentage_change,
                is_regression=is_regression,
                statistical_significance=statistical_significance,
                confidence_interval=confidence_interval,
                effect_size=effect_size,
            )

            analyses.append(analysis)

            if is_regression:
                regression_detected = True
                max_regression = max(max_regression, percentage_change)

        return regression_detected, analyses, max_regression

    def generate_trend_analysis(
        self,
        current_results: list[BenchmarkResult],
        historical_data: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Generate performance trend analysis from historical data."""
        if len(historical_data) < 2:
            return {
                "status": "insufficient_data",
                "message": "Need at least 2 data points for trend analysis",
            }

        trends = {}

        for current in current_results:
            benchmark_name = current.name
            historical_means = []
            timestamps = []

            # Extract historical performance for this benchmark
            for data_point in historical_data:
                for historical_benchmark in data_point.get("benchmarks", []):
                    if historical_benchmark.get("name") == benchmark_name:
                        historical_means.append(historical_benchmark.get("mean", 0.0))
                        timestamps.append(data_point.get("timestamp", 0))
                        break

            if len(historical_means) >= 2:
                # Calculate trend
                if len(historical_means) > 1:
                    recent_trend = (
                        (historical_means[-1] - historical_means[-2])
                        / historical_means[-2]
                        * 100
                    )
                else:
                    recent_trend = 0.0

                # Overall trend (linear regression slope approximation)
                n = len(historical_means)
                x_mean = statistics.mean(range(n))
                y_mean = statistics.mean(historical_means)

                numerator = sum(
                    (i - x_mean) * (y - y_mean) for i, y in enumerate(historical_means)
                )
                denominator = sum((i - x_mean) ** 2 for i in range(n))

                if denominator != 0:
                    slope = numerator / denominator
                    overall_trend = slope / y_mean * 100 if y_mean != 0 else 0.0
                else:
                    overall_trend = 0.0

                trends[benchmark_name] = {
                    "recent_trend_percentage": recent_trend,
                    "overall_trend_percentage": overall_trend,
                    "data_points": len(historical_means),
                    "trend_direction": "improving"
                    if overall_trend < 0
                    else "degrading"
                    if overall_trend > 0
                    else "stable",
                }

        return {
            "status": "success",
            "benchmark_trends": trends,
            "analysis_summary": {
                "total_benchmarks": len(trends),
                "improving_count": sum(
                    1 for t in trends.values() if t["trend_direction"] == "improving"
                ),
                "degrading_count": sum(
                    1 for t in trends.values() if t["trend_direction"] == "degrading"
                ),
                "stable_count": sum(
                    1 for t in trends.values() if t["trend_direction"] == "stable"
                ),
            },
        }

    def store_results(
        self,
        results: PerformanceMetrics,
        results_dir: Path,
        suite: str,
        timestamp: float | None = None,
    ) -> bool:
        """Store benchmark results for historical analysis."""
        if timestamp is None:
            timestamp = time.time()

        results_dir.mkdir(parents=True, exist_ok=True)

        # Store current results
        current_file = results_dir / f"benchmark-{suite}-{int(timestamp)}.json"

        data = {
            "timestamp": timestamp,
            "suite": suite,
            "execution_time": results.execution_time,
            "benchmarks": [
                {
                    "name": b.name,
                    "mean": b.mean,
                    "stddev": b.stddev,
                    "min": b.min_value,
                    "max": b.max_value,
                    "rounds": b.rounds,
                    "unit": b.unit,
                    "group": b.group,
                    "params": b.params,
                    "metadata": b.metadata,
                }
                for b in results.benchmarks
            ],
            "regression_analysis": {
                "detected": results.regression_detected,
                "percentage": results.regression_percentage,
            },
            "environment": results.environment_info,
        }

        try:
            with open(current_file, "w") as f:
                json.dump(data, f, indent=2)

            return True

        except Exception as e:
            print(f"⚠️ Failed to store results: {e}")
            return False

    def execute_benchmarks(
        self,
        project_dir: Path,
        suite: str = "quick",
        baseline_branch: str = "main",
        regression_threshold: float = 10.0,
        timeout: int = 1800,
        store_results: bool = True,
        results_dir: Path = Path("benchmark-results"),
        compare_baseline: bool = True,
        parallel: bool = False,
        config_overrides: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Execute performance benchmarks with comprehensive analysis.

        Returns a dictionary with execution results and analysis.
        """

        # Apply config overrides
        if config_overrides:
            self.effective_config.update(config_overrides)

        # Detect package manager
        package_manager = self.detect_package_manager(project_dir)
        print(f"📦 Detected package manager: {package_manager}")

        # Setup environment
        if not self.setup_benchmark_environment(project_dir, package_manager):
            return {
                "success": False,
                "suite": suite,
                "execution_time": 0.0,
                "benchmark_count": 0,
                "regression_detected": False,
                "regression_percentage": 0.0,
                "baseline_comparison": "Environment setup failed",
                "results_path": str(results_dir),
                "performance_report": "Failed to setup benchmark environment",
                "trend_analysis": "Setup failed",
            }

        # Run benchmarks
        success, result_data = self.run_benchmarks(
            project_dir, suite, package_manager, timeout, parallel
        )

        if not success:
            return {
                "success": False,
                "suite": suite,
                "execution_time": result_data.get("execution_time", 0.0),
                "benchmark_count": 0,
                "regression_detected": False,
                "regression_percentage": 0.0,
                "baseline_comparison": result_data.get("error", "Unknown error"),
                "results_path": str(results_dir),
                "performance_report": f"Benchmark execution failed: {result_data.get('error', 'Unknown error')}",
                "trend_analysis": "Execution failed",
            }

        # Parse results
        benchmark_results = self.parse_benchmark_results(result_data["benchmark_data"])

        # Initialize performance metrics
        metrics = PerformanceMetrics(
            benchmarks=benchmark_results,
            execution_time=result_data["execution_time"],
            total_benchmarks=len(benchmark_results),
            environment_info={
                "package_manager": package_manager,
                "suite": suite,
                "parallel": parallel,
            },
        )

        # Baseline comparison
        baseline_comparison = "No baseline available"
        regression_detected = False
        regression_percentage = 0.0

        if compare_baseline:
            baseline_dir = Path("baseline-results")
            baseline_results = self.load_baseline_results(baseline_dir)

            if baseline_results:
                regression_detected, regression_analyses, max_regression = (
                    self.analyze_regression(
                        benchmark_results, baseline_results, regression_threshold
                    )
                )

                regression_percentage = max_regression
                metrics.regression_detected = regression_detected
                metrics.regression_percentage = regression_percentage

                baseline_comparison = (
                    f"Compared against {len(baseline_results)} baseline benchmarks"
                )
                if regression_detected:
                    baseline_comparison += (
                        f", regression detected: {max_regression:.2f}%"
                    )
                else:
                    baseline_comparison += ", no significant regression"

        # Generate performance report
        if regression_detected:
            performance_report = f"Performance regression detected: {regression_percentage:.2f}% slower than baseline"
        else:
            performance_report = f"Successfully executed {len(benchmark_results)} benchmarks without regression"

        # Store results if requested
        if store_results:
            self.store_results(metrics, results_dir, suite)

        # Trend analysis (simplified - would need historical data loading)
        trend_analysis = "Historical data needed for trend analysis"

        return {
            "success": True,
            "suite": suite,
            "execution_time": metrics.execution_time,
            "benchmark_count": metrics.total_benchmarks,
            "regression_detected": regression_detected,
            "regression_percentage": regression_percentage,
            "baseline_comparison": baseline_comparison,
            "results_path": str(results_dir),
            "performance_report": performance_report,
            "trend_analysis": trend_analysis,
        }
