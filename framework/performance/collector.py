"""Performance data collection and storage infrastructure."""

import json
import os
import platform
from datetime import datetime
from pathlib import Path
from typing import Any

import psutil

from .models import BenchmarkResult, PerformanceMetrics


class PerformanceCollector:
    """Collects, processes, and stores performance metrics and benchmark results."""

    def __init__(self, storage_path: str | Path = None):
        """Initialize the performance collector.

        Args:
            storage_path: Directory path for storing performance data.
                         Defaults to 'performance_data' in current directory.
        """
        self.storage_path = Path(storage_path or "performance_data")
        self.storage_path.mkdir(exist_ok=True)

        # Initialize baseline storage
        self.baseline_path = self.storage_path / "baselines"
        self.baseline_path.mkdir(exist_ok=True)

        # Initialize history storage
        self.history_path = self.storage_path / "history"
        self.history_path.mkdir(exist_ok=True)

    def collect_system_info(self) -> dict[str, str | int | float]:
        """Collect current system information."""
        try:
            cpu_count = psutil.cpu_count()
            memory = psutil.virtual_memory()
            # Use platform-specific disk path: Unix root or Windows system drive
            disk_path = "/" if os.name != "nt" else os.getcwd()[:3]
            disk = psutil.disk_usage(disk_path)

            return {
                "platform": platform.platform(),
                "python_version": platform.python_version(),
                "cpu_count": cpu_count,
                "cpu_percent": psutil.cpu_percent(interval=1),
                "memory_total_gb": round(memory.total / (1024**3), 2),
                "memory_available_gb": round(memory.available / (1024**3), 2),
                "memory_percent": memory.percent,
                "disk_total_gb": round(disk.total / (1024**3), 2),
                "disk_free_gb": round(disk.free / (1024**3), 2),
                "disk_percent": round((disk.used / disk.total) * 100, 2),
            }
        except Exception as e:
            # Fallback for systems where psutil might not work fully
            return {
                "platform": platform.platform(),
                "python_version": platform.python_version(),
                "error": f"Failed to collect full system info: {e}",
            }

    def collect_environment_info(self) -> dict[str, str]:
        """Collect environment information."""
        env_vars = [
            "CI",
            "GITHUB_ACTIONS",
            "GITHUB_WORKFLOW",
            "GITHUB_RUN_ID",
            "GITHUB_RUN_NUMBER",
            "GITHUB_SHA",
            "GITHUB_REF",
        ]

        env_info = {}
        for var in env_vars:
            value = os.environ.get(var)
            if value:
                env_info[var] = value

        return env_info

    def collect_metrics(self, benchmark_results: str | Path | dict) -> PerformanceMetrics:
        """Process benchmark results and create performance metrics.

        Args:
            benchmark_results: Path to pytest-benchmark JSON file, file contents as dict,
                             or raw benchmark data.

        Returns:
            PerformanceMetrics object with processed data.
        """
        # Load benchmark data
        if isinstance(benchmark_results, str | Path):
            with open(benchmark_results) as f:
                data = json.load(f)
        elif isinstance(benchmark_results, dict):
            data = benchmark_results
        else:
            raise ValueError("benchmark_results must be a file path or dictionary")

        # Generate build ID
        build_id = self._generate_build_id()

        # Create metrics object
        metrics = PerformanceMetrics(
            build_id=build_id,
            timestamp=datetime.now(),
            environment=self.collect_environment_info(),
            system_info=self.collect_system_info(),
        )

        # Process pytest-benchmark format
        if "benchmarks" in data:
            for benchmark in data["benchmarks"]:
                result = self._process_pytest_benchmark(benchmark)
                metrics.add_result(result)

        # Process custom format (like our current benchmark-results.json)
        elif "orders_placed" in data:
            result = self._process_custom_benchmark(data)
            metrics.add_result(result)

        # Process generic format
        else:
            result = self._process_generic_benchmark(data)
            metrics.add_result(result)

        return metrics

    def _process_pytest_benchmark(self, benchmark: dict) -> BenchmarkResult:
        """Process a single pytest-benchmark result."""
        stats = benchmark.get("stats", {})

        return BenchmarkResult(
            name=benchmark.get("name", "unknown"),
            execution_time=stats.get("mean", 0),
            memory_usage=None,  # pytest-benchmark doesn't track memory by default
            throughput=1.0 / stats.get("mean", 1) if stats.get("mean", 0) > 0 else None,
            metadata={
                "min_time": stats.get("min", 0),
                "max_time": stats.get("max", 0),
                "median_time": stats.get("median", 0),
                "stddev": stats.get("stddev", 0),
                "rounds": stats.get("rounds", 0),
                "params": benchmark.get("params", {}),
                "source": "pytest-benchmark",
            },
        )

    def _process_custom_benchmark(self, data: dict) -> BenchmarkResult:
        """Process our custom benchmark format."""
        return BenchmarkResult(
            name="order_processing_benchmark",
            execution_time=data.get("duration_seconds", 0),
            memory_usage=self._parse_memory_string(data.get("memory_usage", "0MB")),
            throughput=data.get("orders_per_second", 0),
            metadata={
                "orders_placed": data.get("orders_placed", 0),
                "avg_order_time_ms": data.get("avg_order_time_ms", 0),
                "avg_response_time": data.get("avg_response_time", ""),
                "change_response_time": data.get("change_response_time", ""),
                "change_memory": data.get("change_memory", ""),
                "change_throughput": data.get("change_throughput", ""),
                "source": "custom_benchmark",
            },
        )

    def _process_generic_benchmark(self, data: dict) -> BenchmarkResult:
        """Process generic benchmark data."""
        return BenchmarkResult(
            name=data.get("name", "generic_benchmark"),
            execution_time=data.get("execution_time", 0),
            memory_usage=data.get("memory_usage"),
            throughput=data.get("throughput"),
            cpu_usage=data.get("cpu_usage"),
            metadata={**data, "source": "generic"},
        )

    def _parse_memory_string(self, memory_str: str) -> float | None:
        """Parse memory string like '50MB' to float in MB."""
        if not memory_str or not isinstance(memory_str, str):
            return None

        memory_str = memory_str.strip().upper()
        try:
            if memory_str.endswith("MB"):
                return float(memory_str[:-2])
            elif memory_str.endswith("GB"):
                return float(memory_str[:-2]) * 1024
            elif memory_str.endswith("KB"):
                return float(memory_str[:-2]) / 1024
            else:
                # Assume MB if no unit
                return float(memory_str)
        except ValueError:
            return None

    def _generate_build_id(self) -> str:
        """Generate a unique build identifier."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # Use GitHub info if available
        github_run_id = os.environ.get("GITHUB_RUN_ID")
        github_sha = os.environ.get("GITHUB_SHA", "")[:8]

        if github_run_id:
            return f"gh_{github_run_id}_{github_sha}_{timestamp}"
        else:
            return f"local_{timestamp}"

    def store_baseline(self, metrics: PerformanceMetrics, baseline_name: str = "default") -> Path:
        """Store performance metrics as a baseline.

        Args:
            metrics: Performance metrics to store as baseline.
            baseline_name: Name for the baseline (default: "default").

        Returns:
            Path to the stored baseline file.
        """
        baseline_file = self.baseline_path / f"{baseline_name}_baseline.json"

        with open(baseline_file, "w") as f:
            json.dump(metrics.to_dict(), f, indent=2)

        return baseline_file

    def load_baseline(self, baseline_name: str = "default") -> PerformanceMetrics | None:
        """Load a baseline for comparison.

        Args:
            baseline_name: Name of the baseline to load.

        Returns:
            PerformanceMetrics object or None if baseline doesn't exist.
        """
        baseline_file = self.baseline_path / f"{baseline_name}_baseline.json"

        if not baseline_file.exists():
            return None

        with open(baseline_file) as f:
            data = json.load(f)

        return PerformanceMetrics.from_dict(data)

    def store_history(self, metrics: PerformanceMetrics) -> Path:
        """Store performance metrics in history.

        Args:
            metrics: Performance metrics to store.

        Returns:
            Path to the stored history file.
        """
        history_file = self.history_path / f"{metrics.build_id}.json"

        with open(history_file, "w") as f:
            json.dump(metrics.to_dict(), f, indent=2)

        return history_file

    def get_recent_history(self, limit: int = 10) -> list[PerformanceMetrics]:
        """Get recent performance history.

        Args:
            limit: Maximum number of recent entries to return.

        Returns:
            List of PerformanceMetrics objects sorted by timestamp (newest first).
        """
        history_files = list(self.history_path.glob("*.json"))
        history_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)

        history = []
        for file_path in history_files[:limit]:
            try:
                with open(file_path) as f:
                    data = json.load(f)
                metrics = PerformanceMetrics.from_dict(data)
                history.append(metrics)
            except Exception as e:
                print(f"Warning: Failed to load history file {file_path}: {e}")

        return history

    def compare_with_baseline(
        self, current_metrics: PerformanceMetrics, baseline_name: str = "default"
    ) -> dict[str, Any]:
        """Compare current metrics with a baseline.

        Args:
            current_metrics: Current performance metrics.
            baseline_name: Name of the baseline to compare against.

        Returns:
            Dictionary containing comparison results.
        """
        baseline = self.load_baseline(baseline_name)
        if not baseline:
            return {"error": f"Baseline '{baseline_name}' not found"}

        comparison: dict[str, Any] = {
            "baseline_build_id": baseline.build_id,
            "current_build_id": current_metrics.build_id,
            "baseline_timestamp": baseline.timestamp.isoformat(),
            "current_timestamp": current_metrics.timestamp.isoformat(),
            "comparisons": [],
        }

        # Compare individual benchmark results
        for current_result in current_metrics.results:
            baseline_result = baseline.get_result(current_result.name)
            if baseline_result:
                comp = self._compare_benchmark_results(current_result, baseline_result)
                comparison["comparisons"].append(comp)

        return comparison

    def _compare_benchmark_results(
        self, current: BenchmarkResult, baseline: BenchmarkResult
    ) -> dict[str, Any]:
        """Compare two benchmark results."""

        def calc_change_percent(current_val, baseline_val):
            if baseline_val == 0:
                return float("inf") if current_val > 0 else 0
            return ((current_val - baseline_val) / baseline_val) * 100

        comparison = {
            "name": current.name,
            "execution_time": {
                "current": current.execution_time,
                "baseline": baseline.execution_time,
                "change_percent": calc_change_percent(
                    current.execution_time, baseline.execution_time
                ),
                "change_direction": "regression"
                if current.execution_time > baseline.execution_time
                else "improvement",
            },
        }

        if current.memory_usage is not None and baseline.memory_usage is not None:
            comparison["memory_usage"] = {
                "current": current.memory_usage,
                "baseline": baseline.memory_usage,
                "change_percent": calc_change_percent(current.memory_usage, baseline.memory_usage),
                "change_direction": "regression"
                if current.memory_usage > baseline.memory_usage
                else "improvement",
            }

        if current.throughput is not None and baseline.throughput is not None:
            comparison["throughput"] = {
                "current": current.throughput,
                "baseline": baseline.throughput,
                "change_percent": calc_change_percent(current.throughput, baseline.throughput),
                "change_direction": "improvement"
                if current.throughput > baseline.throughput
                else "regression",
            }

        return comparison
