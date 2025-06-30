"""Integration tests for maintenance system with existing components."""

import json
import tempfile
from datetime import datetime
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from framework.maintenance.health_monitor import CIHealthMonitor
from framework.maintenance.scheduler import MaintenanceScheduler
from framework.performance.collector import PerformanceCollector
from framework.security.analyzer import DependencyAnalyzer


class TestMaintenanceIntegration:
    """Integration tests for the maintenance system."""

    @pytest.fixture
    def temp_project_dir(self):
        """Create a temporary project directory with realistic structure."""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_path = Path(temp_dir)

            # Create project structure
            (project_path / "strategy_sandbox" / "maintenance").mkdir(parents=True)
            (project_path / "performance_data" / "baselines").mkdir(parents=True)
            (project_path / "performance_data" / "history").mkdir(parents=True)
            (project_path / "artifacts" / "reports").mkdir(parents=True)
            (project_path / "artifacts" / "logs").mkdir(parents=True)

            # Create sample pyproject.toml
            pyproject_content = """
[project]
name = "test-project"
dependencies = ["numpy>=1.20.0", "pandas>=1.0.0"]
"""
            (project_path / "pyproject.toml").write_text(pyproject_content)

            # Create sample performance data
            sample_metrics = {
                "build_id": "test_build_123",
                "timestamp": datetime.now().isoformat(),
                "environment": {"CI": "true"},
                "system_info": {"platform": "linux"},
                "results": [
                    {
                        "name": "test_benchmark",
                        "execution_time": 0.5,
                        "memory_usage": 100.0,
                        "throughput": 1000.0,
                        "metadata": {"source": "test"},
                    }
                ],
            }

            (project_path / "performance_data" / "history" / "test_metrics.json").write_text(
                json.dumps(sample_metrics, indent=2)
            )

            # Create sample security report
            security_report = {
                "scan_time": datetime.now().isoformat(),
                "dependencies": 10,
                "vulnerabilities": [],
            }

            (project_path / "artifacts" / "reports" / "security_report.json").write_text(
                json.dumps(security_report, indent=2)
            )

            yield project_path

    def test_health_monitor_with_real_components(self, temp_project_dir):
        """Test health monitor integration with real performance and security components."""
        monitor = CIHealthMonitor(project_path=temp_project_dir)

        # Test that it can initialize with real components
        assert isinstance(monitor.performance_collector, PerformanceCollector)
        assert isinstance(monitor.dependency_analyzer, DependencyAnalyzer)

        # Test health metrics collection
        with (
            patch("psutil.virtual_memory") as mock_memory,
            patch("psutil.cpu_percent") as mock_cpu,
            patch("psutil.boot_time") as mock_boot,
            patch("shutil.disk_usage") as mock_disk,
        ):
            # Mock system metrics
            mock_memory.return_value = Mock(
                percent=50.0, available=8 * (1024**3), total=16 * (1024**3)
            )
            mock_cpu.return_value = 25.0
            mock_boot.return_value = 1000.0
            mock_disk.return_value = Mock(
                total=100 * (1024**3), used=50 * (1024**3), free=50 * (1024**3)
            )

            metrics = monitor.collect_health_metrics()

            assert "timestamp" in metrics
            assert "system_info" in metrics
            assert "component_health" in metrics

            # Check that real components are being checked
            component_health = metrics["component_health"]
            assert "performance" in component_health
            assert "security" in component_health
            assert "reporting" in component_health

    def test_scheduler_with_real_tasks(self, temp_project_dir):
        """Test scheduler integration with real maintenance tasks."""
        scheduler = MaintenanceScheduler(project_path=temp_project_dir)

        # Verify built-in tasks are registered
        assert "health_check" in scheduler.tasks
        assert "data_cleanup" in scheduler.tasks
        assert "security_update" in scheduler.tasks
        assert "performance_baseline" in scheduler.tasks

        # Test running a real health check task
        with (
            patch("psutil.virtual_memory") as mock_memory,
            patch("psutil.cpu_percent") as mock_cpu,
            patch("psutil.boot_time") as mock_boot,
            patch("shutil.disk_usage") as mock_disk,
        ):
            # Mock system metrics
            mock_memory.return_value = Mock(
                percent=50.0, available=8 * (1024**3), total=16 * (1024**3)
            )
            mock_cpu.return_value = 25.0
            mock_boot.return_value = 1000.0
            mock_disk.return_value = Mock(
                total=100 * (1024**3), used=50 * (1024**3), free=50 * (1024**3)
            )

            result = scheduler.run_task("health_check")

            assert result["success"] is True
            assert "details" in result
            assert isinstance(result["details"], dict)

    def test_performance_integration(self, temp_project_dir):
        """Test integration with performance monitoring components."""
        monitor = CIHealthMonitor(project_path=temp_project_dir)

        # Test that it can access performance data
        history = monitor.performance_collector.get_recent_history(limit=5)
        assert isinstance(history, list)

        # Test performance status checking
        status = monitor._check_performance_status()
        assert "status" in status

        # Should find the sample data we created
        if status["status"] != "no_data":
            assert "recent_runs" in status
            assert status["recent_runs"] > 0

    def test_security_integration(self, temp_project_dir):
        """Test integration with security scanning components."""
        monitor = CIHealthMonitor(project_path=temp_project_dir)

        # Test package manager detection
        package_managers = monitor.dependency_analyzer.detect_package_managers()
        assert isinstance(package_managers, list)
        # Should detect pip due to pyproject.toml
        assert "pip" in package_managers

        # Test security status checking
        with patch.object(monitor.dependency_analyzer, "scan_dependencies") as mock_scan:
            # Mock a clean dependency scan
            mock_dep = Mock()
            mock_dep.has_vulnerabilities = False
            mock_dep.vulnerabilities = []
            mock_scan.return_value = [mock_dep]

            status = monitor._check_security_status()
            assert status["status"] == "healthy"
            assert status["total_dependencies"] == 1
            assert status["vulnerable_dependencies"] == 0

    def test_data_cleanup_integration(self, temp_project_dir):
        """Test data cleanup with real file system operations."""
        scheduler = MaintenanceScheduler(project_path=temp_project_dir)

        # Create some old files to clean up
        old_performance_file = temp_project_dir / "performance_data" / "history" / "old_data.json"
        old_performance_file.write_text('{"old": "data"}')

        old_report_file = temp_project_dir / "artifacts" / "reports" / "old_report.json"
        old_report_file.write_text('{"old": "report"}')

        # Mock datetime to make files appear old
        with patch("strategy_sandbox.maintenance.scheduler.datetime") as mock_datetime:
            from datetime import datetime, timedelta

            mock_now = datetime(2024, 6, 15, 12, 0, 0)
            mock_datetime.now.return_value = mock_now
            mock_datetime.fromtimestamp.side_effect = lambda ts: datetime.fromtimestamp(ts)

            # Set file times to be very old using os.utime
            import os

            old_time = (mock_now - timedelta(days=200)).timestamp()
            os.utime(old_performance_file, (old_time, old_time))
            os.utime(old_report_file, (old_time, old_time))

            # Run cleanup
            result = scheduler._cleanup_old_data()

            assert result["files_removed"] >= 2
            assert "space_freed_mb" in result
            assert len(result["directories_processed"]) > 0

    def test_comprehensive_maintenance_workflow(self, temp_project_dir):
        """Test complete maintenance workflow with all components."""
        scheduler = MaintenanceScheduler(project_path=temp_project_dir)

        with (
            patch("psutil.virtual_memory") as mock_memory,
            patch("psutil.cpu_percent") as mock_cpu,
            patch("psutil.boot_time") as mock_boot,
            patch("shutil.disk_usage") as mock_disk,
            patch.object(
                scheduler.health_monitor.dependency_analyzer, "scan_dependencies"
            ) as mock_scan,
        ):
            # Mock system metrics
            mock_memory.return_value = Mock(
                percent=50.0, available=8 * (1024**3), total=16 * (1024**3)
            )
            mock_cpu.return_value = 25.0
            mock_boot.return_value = 1000.0
            mock_disk.return_value = Mock(
                total=100 * (1024**3), used=50 * (1024**3), free=50 * (1024**3)
            )

            # Mock security scan
            mock_dep = Mock()
            mock_dep.has_vulnerabilities = False
            mock_dep.vulnerabilities = []
            mock_scan.return_value = [mock_dep]

            # Run comprehensive maintenance
            result = scheduler.perform_maintenance(dry_run=False)

            assert result["dry_run"] is False
            assert "operations" in result
            assert "summary" in result

            # Check that all operations were attempted
            operations = {op["operation"]: op for op in result["operations"]}
            assert "health_check" in operations
            assert "system_diagnostics" in operations

            # Most operations should succeed
            successful_ops = [op for op in result["operations"] if op["status"] == "success"]
            assert len(successful_ops) >= 2

    def test_health_recommendations_with_real_data(self, temp_project_dir):
        """Test health recommendations with realistic scenarios."""
        monitor = CIHealthMonitor(project_path=temp_project_dir)

        # Simulate high resource usage
        with (
            patch("psutil.virtual_memory") as mock_memory,
            patch("psutil.cpu_percent") as mock_cpu,
            patch("shutil.disk_usage") as mock_disk,
        ):
            # High resource usage scenario
            mock_memory.return_value = Mock(
                percent=90.0, available=1 * (1024**3), total=16 * (1024**3)
            )
            mock_cpu.return_value = 95.0
            mock_disk.return_value = Mock(
                total=100 * (1024**3), used=95 * (1024**3), free=5 * (1024**3)
            )

            monitor.collect_health_metrics()
            recommendations = monitor._generate_health_recommendations()

            assert len(recommendations) > 0
            assert any("CPU usage" in rec for rec in recommendations)
            assert any("memory usage" in rec for rec in recommendations)

    def test_error_handling_and_resilience(self, temp_project_dir):
        """Test error handling and system resilience."""
        # Create broken project directory
        broken_project_dir = temp_project_dir / "nonexistent"
        broken_project_dir.mkdir(parents=True)  # Create the directory first

        # Should not crash even with missing subdirectories
        monitor = CIHealthMonitor(project_path=broken_project_dir)

        with patch("psutil.virtual_memory") as mock_memory, patch("psutil.cpu_percent") as mock_cpu:
            mock_memory.return_value = Mock(
                percent=50.0, available=8 * (1024**3), total=16 * (1024**3)
            )
            mock_cpu.return_value = 25.0

            # Should handle missing directories gracefully
            metrics = monitor._collect_storage_metrics()
            assert isinstance(metrics, dict)

            # Some entries might have errors, but shouldn't crash
            for _, value in metrics.items():
                assert isinstance(value, dict)

    def test_task_execution_history_tracking(self, temp_project_dir):
        """Test that task execution history is properly tracked."""
        scheduler = MaintenanceScheduler(project_path=temp_project_dir)

        # Run a few tasks
        def dummy_task():
            return "success"

        scheduler.register_task("test_task_1", dummy_task, "daily")
        scheduler.register_task("test_task_2", dummy_task, "weekly")

        # Execute tasks
        scheduler.run_task("test_task_1")
        scheduler.run_task("test_task_2")

        # Check execution history
        history = scheduler.get_execution_history()
        assert len(history) >= 2

        task_names = [h["task"] for h in history]
        assert "test_task_1" in task_names
        assert "test_task_2" in task_names

        # Check task status reflects execution
        status = scheduler.get_task_status()
        task_statuses = {t["name"]: t for t in status["tasks"]}

        assert task_statuses["test_task_1"]["run_count"] >= 1
        assert task_statuses["test_task_2"]["run_count"] >= 1

    def test_configuration_loading_and_validation(self, temp_project_dir):
        """Test configuration loading and validation with real files."""
        # Create a custom configuration
        config_content = {
            "data_retention": {"performance_data": 60, "security_scans": 15, "reports": 30},
            "health_thresholds": {"max_execution_time": 1800, "max_storage_usage": 10},
            "update_schedule": {"health_check": "daily", "cleanup_old_data": "monthly"},
        }

        config_path = temp_project_dir / "custom_config.yaml"
        import yaml

        with open(config_path, "w") as f:
            yaml.dump(config_content, f)

        # Test scheduler with custom config
        scheduler = MaintenanceScheduler(config_path=config_path, project_path=temp_project_dir)

        assert scheduler.config["data_retention"]["performance_data"] == 60
        assert scheduler.config["health_thresholds"]["max_execution_time"] == 1800

        # Test that tasks are scheduled according to config
        health_task = scheduler.tasks["health_check"]
        assert health_task.schedule == "daily"
