"""Tests for performance data collection infrastructure."""

import json
import tempfile
import time
from datetime import datetime
from pathlib import Path

from framework.performance import BenchmarkResult, PerformanceCollector, PerformanceMetrics


class TestPerformanceCollector:
    """Test cases for PerformanceCollector."""

    def test_collector_initialization(self):
        """Test collector initializes correctly."""
        with tempfile.TemporaryDirectory() as temp_dir:
            collector = PerformanceCollector(temp_dir)

            assert collector.storage_path == Path(temp_dir)
            assert collector.baseline_path.exists()
            assert collector.history_path.exists()

    def test_system_info_collection(self):
        """Test system information collection."""
        collector = PerformanceCollector()
        system_info = collector.collect_system_info()

        assert "platform" in system_info
        assert "python_version" in system_info
        assert isinstance(system_info["platform"], str)
        assert isinstance(system_info["python_version"], str)

    def test_environment_info_collection(self):
        """Test environment information collection."""
        collector = PerformanceCollector()
        env_info = collector.collect_environment_info()

        # Should be a dict, might be empty if no CI env vars set
        assert isinstance(env_info, dict)

    def test_pytest_benchmark_processing(self):
        """Test processing pytest-benchmark format."""
        with tempfile.TemporaryDirectory() as temp_dir:
            collector = PerformanceCollector(temp_dir)

            # Mock pytest-benchmark data
            benchmark_data = {
                "benchmarks": [
                    {
                        "name": "test_benchmark",
                        "stats": {
                            "mean": 0.005,
                            "min": 0.003,
                            "max": 0.008,
                            "median": 0.004,
                            "stddev": 0.001,
                            "rounds": 100,
                        },
                        "params": {"param1": "value1"},
                    }
                ]
            }

            metrics = collector.collect_metrics(benchmark_data)

            assert len(metrics.results) == 1
            result = metrics.results[0]
            assert result.name == "test_benchmark"
            assert result.execution_time == 0.005
            assert result.throughput == 200.0  # 1/0.005
            assert result.metadata["source"] == "pytest-benchmark"

    def test_custom_benchmark_processing(self):
        """Test processing custom benchmark format."""
        with tempfile.TemporaryDirectory() as temp_dir:
            collector = PerformanceCollector(temp_dir)

            # Mock our custom format
            benchmark_data = {
                "orders_placed": 1000,
                "duration_seconds": 0.5,
                "orders_per_second": 2000.0,
                "avg_order_time_ms": 0.5,
                "memory_usage": "64MB",
            }

            metrics = collector.collect_metrics(benchmark_data)

            assert len(metrics.results) == 1
            result = metrics.results[0]
            assert result.name == "order_processing_benchmark"
            assert result.execution_time == 0.5
            assert result.throughput == 2000.0
            assert result.memory_usage == 64.0
            assert result.metadata["source"] == "custom_benchmark"

    def test_memory_string_parsing(self):
        """Test memory string parsing."""
        collector = PerformanceCollector()

        assert collector._parse_memory_string("50MB") == 50.0
        assert collector._parse_memory_string("1GB") == 1024.0
        assert collector._parse_memory_string("512KB") == 0.5
        assert collector._parse_memory_string("invalid") is None
        assert collector._parse_memory_string("") is None

    def test_baseline_storage_and_loading(self):
        """Test storing and loading baselines."""
        with tempfile.TemporaryDirectory() as temp_dir:
            collector = PerformanceCollector(temp_dir)

            # Create test metrics
            metrics = PerformanceMetrics(build_id="test_build", timestamp=datetime.now())
            metrics.add_result(
                BenchmarkResult(name="test_benchmark", execution_time=0.1, memory_usage=50.0)
            )

            # Store baseline
            baseline_file = collector.store_baseline(metrics, "test_baseline")
            assert baseline_file.exists()

            # Load baseline
            loaded_metrics = collector.load_baseline("test_baseline")
            assert loaded_metrics is not None
            assert loaded_metrics.build_id == "test_build"
            assert len(loaded_metrics.results) == 1
            assert loaded_metrics.results[0].name == "test_benchmark"

    def test_history_storage_and_retrieval(self):
        """Test storing and retrieving performance history."""
        with tempfile.TemporaryDirectory() as temp_dir:
            collector = PerformanceCollector(temp_dir)

            # Create and store multiple metrics
            for i in range(3):
                metrics = PerformanceMetrics(build_id=f"build_{i}", timestamp=datetime.now())
                metrics.add_result(
                    BenchmarkResult(name="test_benchmark", execution_time=0.1 + i * 0.01)
                )

                collector.store_history(metrics)
                time.sleep(0.01)  # Ensure different timestamps

            # Get history
            history = collector.get_recent_history(limit=2)
            assert len(history) == 2
            # Should be sorted newest first
            assert "build_" in history[0].build_id

    def test_baseline_comparison(self):
        """Test comparing metrics with baseline."""
        with tempfile.TemporaryDirectory() as temp_dir:
            collector = PerformanceCollector(temp_dir)

            # Create baseline
            baseline_metrics = PerformanceMetrics(
                build_id="baseline_build", timestamp=datetime.now()
            )
            baseline_metrics.add_result(
                BenchmarkResult(
                    name="test_benchmark", execution_time=0.1, memory_usage=50.0, throughput=100.0
                )
            )
            collector.store_baseline(baseline_metrics, "test")

            # Create current metrics (10% slower, 20% more memory, 5% less throughput)
            current_metrics = PerformanceMetrics(build_id="current_build", timestamp=datetime.now())
            current_metrics.add_result(
                BenchmarkResult(
                    name="test_benchmark",
                    execution_time=0.11,  # 10% slower
                    memory_usage=60.0,  # 20% more memory
                    throughput=95.0,  # 5% less throughput
                )
            )

            # Compare
            comparison = collector.compare_with_baseline(current_metrics, "test")

            assert "error" not in comparison
            assert len(comparison["comparisons"]) == 1

            comp = comparison["comparisons"][0]
            assert comp["name"] == "test_benchmark"

            # Check execution time comparison
            et = comp["execution_time"]
            assert et["change_direction"] == "regression"
            assert abs(et["change_percent"] - 10.0) < 0.1

            # Check memory comparison
            mem = comp["memory_usage"]
            assert mem["change_direction"] == "regression"
            assert abs(mem["change_percent"] - 20.0) < 0.1

            # Check throughput comparison
            thr = comp["throughput"]
            assert thr["change_direction"] == "regression"
            assert abs(thr["change_percent"] - (-5.0)) < 0.1

    def test_file_based_benchmark_loading(self):
        """Test loading benchmark data from file."""
        with tempfile.TemporaryDirectory() as temp_dir:
            collector = PerformanceCollector(temp_dir)

            # Create test benchmark file
            benchmark_data = {
                "orders_placed": 500,
                "duration_seconds": 0.25,
                "orders_per_second": 2000.0,
                "memory_usage": "32MB",
            }

            benchmark_file = Path(temp_dir) / "test_benchmark.json"
            with open(benchmark_file, "w") as f:
                json.dump(benchmark_data, f)

            # Load from file
            metrics = collector.collect_metrics(benchmark_file)

            assert len(metrics.results) == 1
            result = metrics.results[0]
            assert result.execution_time == 0.25
            assert result.memory_usage == 32.0


class TestPerformanceMetrics:
    """Test cases for PerformanceMetrics."""

    def test_metrics_creation(self):
        """Test creating performance metrics."""
        metrics = PerformanceMetrics(build_id="test_build", timestamp=datetime.now())

        assert metrics.build_id == "test_build"
        assert isinstance(metrics.timestamp, datetime)
        assert len(metrics.results) == 0

    def test_adding_results(self):
        """Test adding benchmark results."""
        metrics = PerformanceMetrics(build_id="test_build", timestamp=datetime.now())

        result = BenchmarkResult(name="test_benchmark", execution_time=0.1)
        metrics.add_result(result)

        assert len(metrics.results) == 1
        assert metrics.get_result("test_benchmark") == result

    def test_summary_stats_calculation(self):
        """Test summary statistics calculation."""
        metrics = PerformanceMetrics(build_id="test_build", timestamp=datetime.now())

        # Add multiple results
        for i in range(3):
            metrics.add_result(
                BenchmarkResult(
                    name=f"benchmark_{i}",
                    execution_time=0.1 + i * 0.05,
                    memory_usage=50.0 + i * 10.0,
                    throughput=100.0 - i * 5.0,
                )
            )

        stats = metrics.calculate_summary_stats()

        assert "avg_execution_time" in stats
        assert "max_execution_time" in stats
        assert "min_execution_time" in stats
        assert "avg_memory_usage" in stats
        assert "avg_throughput" in stats

        # Check specific values
        assert abs(stats["avg_execution_time"] - 0.15) < 0.01
        assert stats["max_execution_time"] == 0.2
        assert stats["min_execution_time"] == 0.1

    def test_serialization_roundtrip(self):
        """Test serializing and deserializing metrics."""
        original_metrics = PerformanceMetrics(build_id="test_build", timestamp=datetime.now())
        original_metrics.add_result(
            BenchmarkResult(
                name="test_benchmark",
                execution_time=0.1,
                memory_usage=50.0,
                metadata={"test": "value"},
            )
        )

        # Serialize to dict
        data = original_metrics.to_dict()

        # Deserialize back
        restored_metrics = PerformanceMetrics.from_dict(data)

        assert restored_metrics.build_id == original_metrics.build_id
        assert len(restored_metrics.results) == len(original_metrics.results)
        assert restored_metrics.results[0].name == "test_benchmark"
        assert restored_metrics.results[0].execution_time == 0.1


class TestBenchmarkResult:
    """Test cases for BenchmarkResult."""

    def test_result_creation(self):
        """Test creating benchmark result."""
        result = BenchmarkResult(
            name="test_benchmark", execution_time=0.5, memory_usage=100.0, throughput=200.0
        )

        assert result.name == "test_benchmark"
        assert result.execution_time == 0.5
        assert result.memory_usage == 100.0
        assert result.throughput == 200.0
        assert isinstance(result.timestamp, float)

    def test_result_serialization(self):
        """Test benchmark result serialization."""
        result = BenchmarkResult(
            name="test_benchmark", execution_time=0.5, metadata={"param": "value"}
        )

        data = result.to_dict()
        restored_result = BenchmarkResult.from_dict(data)

        assert restored_result.name == result.name
        assert restored_result.execution_time == result.execution_time
        assert restored_result.metadata == result.metadata
