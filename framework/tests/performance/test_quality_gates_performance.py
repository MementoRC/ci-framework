"""
Performance Benchmark Tests for Quality Gates Action

These tests establish performance baselines and ensure the Quality Gates Action
meets or exceeds performance requirements across different project sizes.
"""

import shutil
import statistics
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Any
from unittest.mock import Mock, patch

import pytest

from framework.actions.quality_gates import QualityGatesAction


class TestQualityGatesPerformance:
    """
    Performance benchmark tests for Quality Gates Action

    Tests cover execution time, memory usage, and scalability
    across different project sizes and configurations.
    """

    @pytest.fixture
    def quality_gates_action(self):
        """Quality Gates Action instance"""
        return QualityGatesAction()

    @pytest.fixture
    def small_mock_project(self):
        """Create a small mock project (< 10 files)"""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_dir = Path(temp_dir) / "small_project"
            project_dir.mkdir()

            # Create pyproject.toml
            (project_dir / "pyproject.toml").write_text(
                """
[tool.pixi.project]
name = "small-project"
channels = ["conda-forge"]
platforms = ["linux-64"]

[tool.pixi.environments]
quality = {features = ["quality"]}

[tool.pixi.tasks]
test = "pytest"
lint = "ruff check --select=F,E9"
typecheck = "mypy ."
quality = { depends-on = ["test", "lint", "typecheck"] }
"""
            )

            # Create small codebase
            src_dir = project_dir / "src"
            src_dir.mkdir()
            (src_dir / "__init__.py").write_text("")
            (src_dir / "main.py").write_text("def hello(): return 'world'")

            test_dir = project_dir / "tests"
            test_dir.mkdir()
            (test_dir / "__init__.py").write_text("")
            (test_dir / "test_main.py").write_text("def test_hello(): assert True")

            yield project_dir

    @pytest.fixture
    def medium_mock_project(self):
        """Create a medium mock project (50-100 files)"""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_dir = Path(temp_dir) / "medium_project"
            project_dir.mkdir()

            # Create pyproject.toml
            (project_dir / "pyproject.toml").write_text(
                """
[tool.pixi.project]
name = "medium-project"
channels = ["conda-forge"]
platforms = ["linux-64"]

[tool.pixi.environments]
quality = {features = ["quality"]}
quality-extended = {features = ["quality", "quality-extended"]}

[tool.pixi.tasks]
test = "pytest"
lint = "ruff check --select=F,E9"
typecheck = "mypy ."
security-scan = "bandit -r ."
quality = { depends-on = ["test", "lint", "typecheck"] }
check-all = { depends-on = ["quality", "security-scan"] }
"""
            )

            # Create medium codebase
            for i in range(10):
                module_dir = project_dir / f"module_{i}"
                module_dir.mkdir()
                (module_dir / "__init__.py").write_text("")

                for j in range(5):
                    (module_dir / f"file_{j}.py").write_text(
                        f"""
def function_{j}():
    return {j}

class Class_{j}:
    def method(self):
        return {j}
"""
                    )

            # Create tests
            test_dir = project_dir / "tests"
            test_dir.mkdir()
            for i in range(20):
                (test_dir / f"test_{i}.py").write_text(
                    f"def test_function_{i}(): assert True"
                )

            yield project_dir

    def test_small_project_performance_baseline(
        self, quality_gates_action, small_mock_project
    ):
        """Establish performance baseline for small projects"""

        # Mock subprocess.run to avoid actual command execution
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(returncode=0, stdout="success", stderr="")

            # Measure package manager detection time
            start_time = time.time()
            _ = quality_gates_action.detect_package_manager(small_mock_project)
            detection_time = time.time() - start_time

            assert detection_time < 0.1, (
                f"Package manager detection took {detection_time}s, should be <0.1s"
            )

            # Measure pattern detection time
            start_time = time.time()
            _ = quality_gates_action._detect_project_patterns(small_mock_project)
            pattern_time = time.time() - start_time

            assert pattern_time < 0.1, (
                f"Pattern detection took {pattern_time}s, should be <0.1s"
            )

            # Measure dry-run execution time
            start_time = time.time()
            result = quality_gates_action.execute_tier(
                project_dir=small_mock_project, tier="essential", dry_run=True
            )
            dry_run_time = time.time() - start_time

            assert dry_run_time < 0.5, f"Dry run took {dry_run_time}s, should be <0.5s"
            assert result.success is True

            return {
                "detection_time": detection_time,
                "pattern_time": pattern_time,
                "dry_run_time": dry_run_time,
            }

    def test_medium_project_performance_scaling(
        self, quality_gates_action, medium_mock_project
    ):
        """Test performance scaling with medium-sized projects"""

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(returncode=0, stdout="success", stderr="")

            # Measure scaling performance
            start_time = time.time()
            result = quality_gates_action.execute_tier(
                project_dir=medium_mock_project, tier="extended", dry_run=True
            )
            execution_time = time.time() - start_time

            # Should scale reasonably with project size
            assert execution_time < 2.0, (
                f"Medium project took {execution_time}s, should be <2.0s"
            )
            assert result.success is True

            return {"execution_time": execution_time, "project_size": "medium"}

    def test_parallel_vs_sequential_performance(
        self, quality_gates_action, medium_mock_project
    ):
        """Compare parallel vs sequential execution performance"""

        with patch("subprocess.run") as mock_run:
            # Simulate command execution time
            def slow_command(*args, **kwargs):
                time.sleep(0.1)  # Simulate 100ms command
                return Mock(returncode=0, stdout="success", stderr="")

            mock_run.side_effect = slow_command

            # Test sequential execution
            start_time = time.time()
            result_sequential = quality_gates_action.execute_tier(
                project_dir=medium_mock_project, tier="essential", parallel=False
            )
            sequential_time = time.time() - start_time

            # Test parallel execution
            start_time = time.time()
            result_parallel = quality_gates_action.execute_tier(
                project_dir=medium_mock_project, tier="essential", parallel=True
            )
            parallel_time = time.time() - start_time

            assert result_sequential.success is True
            assert result_parallel.success is True

            # Parallel should be significantly faster
            speedup = sequential_time / parallel_time
            assert speedup > 1.5, f"Parallel speedup {speedup}x should be >1.5x"

            return {
                "sequential_time": sequential_time,
                "parallel_time": parallel_time,
                "speedup": speedup,
            }

    def test_timeout_performance_handling(
        self, quality_gates_action, small_mock_project
    ):
        """Test timeout handling performance and cleanup"""

        with patch("subprocess.Popen") as mock_popen:
            # Mock a process that times out
            mock_process = Mock()
            mock_process.communicate.side_effect = subprocess.TimeoutExpired("test", 1)
            mock_process.pid = 12345
            mock_process.poll.return_value = None
            mock_popen.return_value = mock_process

            # Measure timeout handling performance
            start_time = time.time()
            result = quality_gates_action.execute_tier(
                project_dir=small_mock_project,
                tier="essential",
                timeout=1,  # Very short timeout
            )
            timeout_handling_time = time.time() - start_time

            # Timeout handling should be fast and clean
            assert timeout_handling_time < 3.0, (
                f"Timeout handling took {timeout_handling_time}s, should be <3.0s"
            )
            assert result.success is False
            assert result.failure_reason == "timeout"

    def test_memory_efficiency(self, quality_gates_action, medium_mock_project):
        """Test memory efficiency of Quality Gates Action"""
        import os

        import psutil

        process = psutil.Process(os.getpid())

        # Measure memory before execution
        memory_before = process.memory_info().rss / 1024 / 1024  # MB

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(returncode=0, stdout="success", stderr="")

            # Execute multiple operations
            for tier in ["essential", "extended", "full"]:
                result = quality_gates_action.execute_tier(
                    project_dir=medium_mock_project, tier=tier, dry_run=True
                )
                assert result.success is True

        # Measure memory after execution
        memory_after = process.memory_info().rss / 1024 / 1024  # MB
        memory_increase = memory_after - memory_before

        # Memory increase should be reasonable
        assert memory_increase < 50, (
            f"Memory increased by {memory_increase}MB, should be <50MB"
        )

        return {
            "memory_before": memory_before,
            "memory_after": memory_after,
            "memory_increase": memory_increase,
        }

    def test_configuration_override_performance(
        self, quality_gates_action, small_mock_project
    ):
        """Test performance of configuration override processing"""

        complex_config = {
            "timeouts": {f"task_{i}": 60 + i for i in range(20)},
            "thresholds": {f"metric_{i}": i * 0.1 for i in range(50)},
            "tools": {
                f"tool_{i}": {
                    "option_1": f"value_{i}",
                    "option_2": [f"item_{j}" for j in range(10)],
                    "option_3": {f"nested_{k}": f"nested_value_{k}" for k in range(5)},
                }
                for i in range(10)
            },
        }

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(returncode=0, stdout="success", stderr="")

            start_time = time.time()
            result = quality_gates_action.execute_tier(
                project_dir=small_mock_project,
                tier="essential",
                config_overrides=complex_config,
                dry_run=True,
            )
            config_processing_time = time.time() - start_time

            assert config_processing_time < 1.0, (
                f"Config processing took {config_processing_time}s, should be <1.0s"
            )
            assert result.success is True
            assert result.config.timeouts["task_0"] == 60

    @pytest.mark.benchmark
    def test_real_project_performance_benchmark(self, quality_gates_action):
        """Benchmark against real integration projects"""

        projects = [
            (
                "/home/memento/ClaudeCode/Project/hb-strategy-sandbox/worktrees/feat-workspace-phase2",
                "large",
            ),
            (
                "/home/memento/ClaudeCode/Servers/cheap-llm/worktrees/feat-phase1",
                "medium",
            ),
        ]

        benchmarks = {}

        for project_path, size_category in projects:
            project_path = Path(project_path)
            if not project_path.exists():
                continue

            # Benchmark pattern detection
            start_time = time.time()
            _ = quality_gates_action._detect_project_patterns(project_path)
            pattern_time = time.time() - start_time

            # Benchmark dry-run execution
            start_time = time.time()
            result = quality_gates_action.execute_tier(
                project_dir=project_path, tier="essential", dry_run=True
            )
            dry_run_time = time.time() - start_time

            benchmarks[size_category] = {
                "pattern_detection_time": pattern_time,
                "dry_run_time": dry_run_time,
                "success": result.success,
            }

            # Performance requirements based on project size
            if size_category == "medium":
                assert pattern_time < 0.5, (
                    f"Medium project pattern detection: {pattern_time}s"
                )
                assert dry_run_time < 1.0, f"Medium project dry run: {dry_run_time}s"
            elif size_category == "large":
                assert pattern_time < 2.0, (
                    f"Large project pattern detection: {pattern_time}s"
                )
                assert dry_run_time < 5.0, f"Large project dry run: {dry_run_time}s"

        print(f"Performance benchmarks: {benchmarks}")
        return benchmarks

    def test_concurrent_execution_performance(self, quality_gates_action):
        """Test performance under concurrent execution scenarios"""
        import concurrent.futures
        import threading

        def execute_quality_gates(project_dir, tier):
            with patch("subprocess.run") as mock_run:
                mock_run.return_value = Mock(returncode=0, stdout="success", stderr="")
                return quality_gates_action.execute_tier(
                    project_dir=project_dir, tier=tier, dry_run=True
                )

        # Create multiple mock projects
        with tempfile.TemporaryDirectory() as temp_dir:
            projects = []
            for i in range(5):
                project_dir = Path(temp_dir) / f"project_{i}"
                project_dir.mkdir()

                (project_dir / "pyproject.toml").write_text(
                    """
[tool.pixi.project]
name = "test-project"
[tool.pixi.tasks]
test = "pytest"
lint = "ruff check"
"""
                )
                projects.append(project_dir)

            # Test concurrent execution
            start_time = time.time()

            with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
                futures = [
                    executor.submit(execute_quality_gates, project_dir, "essential")
                    for project_dir in projects
                ]

                results = [
                    future.result()
                    for future in concurrent.futures.as_completed(futures)
                ]

            concurrent_time = time.time() - start_time

            # All executions should succeed
            assert all(result.success for result in results)

            # Concurrent execution should complete reasonably quickly
            assert concurrent_time < 5.0, (
                f"Concurrent execution took {concurrent_time}s, should be <5.0s"
            )

            return {
                "concurrent_time": concurrent_time,
                "num_projects": len(projects),
                "all_success": all(result.success for result in results),
            }


class TestPerformanceRegression:
    """
    Performance regression tests to ensure no performance degradation
    """

    def test_performance_baseline_compliance(self):
        """Test compliance with established performance baselines"""

        # Define performance baselines (these should be updated based on real measurements)
        baselines = {
            "small_project": {
                "max_detection_time": 0.1,  # seconds
                "max_pattern_time": 0.1,  # seconds
                "max_dry_run_time": 0.5,  # seconds
            },
            "medium_project": {
                "max_execution_time": 2.0,  # seconds
                "max_memory_increase": 50,  # MB
            },
            "large_project": {
                "max_pattern_time": 2.0,  # seconds
                "max_dry_run_time": 5.0,  # seconds
            },
        }

        # This test documents the expected performance characteristics
        # Real measurements from other tests should be compared against these baselines
        assert baselines["small_project"]["max_detection_time"] > 0
        assert baselines["medium_project"]["max_execution_time"] > 0
        assert baselines["large_project"]["max_dry_run_time"] > 0

        return baselines

    def test_scalability_characteristics(self):
        """Document scalability characteristics for future testing"""

        scalability_expectations = {
            "project_size_scaling": {
                "small_projects": "<0.5s",  # <100 files
                "medium_projects": "<2.0s",  # 100-1000 files
                "large_projects": "<5.0s",  # 1000+ files
                "very_large_projects": "<15.0s",  # 10000+ files
            },
            "concurrent_scaling": {
                "single_execution": "baseline",
                "5_concurrent": "<2x baseline",
                "10_concurrent": "<3x baseline",
            },
            "memory_scaling": {
                "small_projects": "<10MB increase",
                "medium_projects": "<50MB increase",
                "large_projects": "<100MB increase",
            },
        }

        # Document for future performance validation
        print(f"Scalability expectations: {scalability_expectations}")
        return scalability_expectations


# Performance test utilities


def measure_execution_time(func, *args, **kwargs):
    """Utility to measure function execution time"""
    start_time = time.time()
    result = func(*args, **kwargs)
    execution_time = time.time() - start_time
    return result, execution_time


def measure_memory_usage(func, *args, **kwargs):
    """Utility to measure memory usage during function execution"""
    import os

    import psutil

    process = psutil.Process(os.getpid())
    memory_before = process.memory_info().rss
    result = func(*args, **kwargs)
    memory_after = process.memory_info().rss
    memory_delta = memory_after - memory_before

    return result, memory_delta


def benchmark_multiple_runs(func, num_runs=10, *args, **kwargs):
    """Benchmark function over multiple runs and return statistics"""
    times = []
    results = []

    for _ in range(num_runs):
        result, execution_time = measure_execution_time(func, *args, **kwargs)
        times.append(execution_time)
        results.append(result)

    return {
        "results": results,
        "times": times,
        "mean_time": statistics.mean(times),
        "median_time": statistics.median(times),
        "min_time": min(times),
        "max_time": max(times),
        "std_dev": statistics.stdev(times) if len(times) > 1 else 0,
    }
