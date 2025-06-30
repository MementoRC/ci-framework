"""Tests for CI health monitoring functionality."""

import tempfile
import time
from datetime import datetime
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
import yaml

from framework.maintenance.health_monitor import CIHealthMonitor


class TestCIHealthMonitor:
    """Test cases for CIHealthMonitor class."""

    @pytest.fixture
    def temp_project_dir(self):
        """Create a temporary project directory for testing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_path = Path(temp_dir)

            # Create necessary subdirectories
            (project_path / "performance_data" / "baselines").mkdir(parents=True)
            (project_path / "performance_data" / "history").mkdir(parents=True)
            (project_path / "artifacts" / "reports").mkdir(parents=True)
            (project_path / "strategy_sandbox" / "maintenance").mkdir(parents=True)

            yield project_path

    @pytest.fixture
    def sample_config(self, temp_project_dir):
        """Create a sample configuration file."""
        config_data = {
            "data_retention": {"performance_data": 90, "security_scans": 30, "reports": 60},
            "health_thresholds": {
                "max_execution_time": 3600,
                "max_storage_usage": 5,
                "min_disk_space": 10,
            },
            "update_schedule": {"security_databases": "daily"},
        }

        config_path = (
            temp_project_dir / "strategy_sandbox" / "maintenance" / "maintenance_config.yaml"
        )
        with open(config_path, "w") as f:
            yaml.dump(config_data, f)

        return config_path

    def test_init_with_config(self, temp_project_dir, sample_config):
        """Test CIHealthMonitor initialization with config file."""
        monitor = CIHealthMonitor(config_path=sample_config, project_path=temp_project_dir)

        assert monitor.project_path == temp_project_dir
        assert monitor.config_path == sample_config
        assert "data_retention" in monitor.config
        assert monitor.config["health_thresholds"]["max_execution_time"] == 3600

    def test_init_without_config(self, temp_project_dir):
        """Test CIHealthMonitor initialization without config file."""
        monitor = CIHealthMonitor(project_path=temp_project_dir)

        assert monitor.project_path == temp_project_dir
        assert "data_retention" in monitor.config  # Should have default config
        assert monitor.config["health_thresholds"]["max_execution_time"] == 3600

    @patch("framework.maintenance.health_monitor.psutil")
    def test_collect_system_metrics(self, mock_psutil, temp_project_dir):
        """Test system metrics collection."""
        # Mock psutil methods
        mock_memory = Mock()
        mock_memory.percent = 75.0
        mock_memory.available = 4 * (1024**3)  # 4GB
        mock_memory.total = 16 * (1024**3)  # 16GB

        mock_psutil.virtual_memory.return_value = mock_memory
        mock_psutil.cpu_percent.return_value = 25.5
        mock_psutil.getloadavg.return_value = [1.0, 1.5, 2.0]
        mock_psutil.boot_time.return_value = time.time() - 3600  # 1 hour uptime

        monitor = CIHealthMonitor(project_path=temp_project_dir)
        metrics = monitor._collect_system_metrics()

        assert metrics["cpu_usage_percent"] == 25.5
        assert metrics["memory_usage_percent"] == 75.0
        assert metrics["memory_available_gb"] == 4.0
        assert metrics["memory_total_gb"] == 16.0
        assert "uptime_seconds" in metrics

    @patch("shutil.disk_usage")
    def test_collect_storage_metrics(self, mock_disk_usage, temp_project_dir):
        """Test storage metrics collection."""
        # Mock disk usage
        mock_usage = Mock()
        mock_usage.total = 100 * (1024**3)  # 100GB total
        mock_usage.used = 50 * (1024**3)  # 50GB used
        mock_usage.free = 50 * (1024**3)  # 50GB free
        mock_disk_usage.return_value = mock_usage

        monitor = CIHealthMonitor(project_path=temp_project_dir)
        metrics = monitor._collect_storage_metrics()

        assert "project_root" in metrics
        assert metrics["project_root"]["total_gb"] == 100.0
        assert metrics["project_root"]["used_gb"] == 50.0
        assert metrics["project_root"]["usage_percent"] == 50.0

    def test_collect_health_metrics(self, temp_project_dir):
        """Test comprehensive health metrics collection."""
        with (
            patch.object(CIHealthMonitor, "_collect_system_metrics") as mock_system,
            patch.object(CIHealthMonitor, "_collect_storage_metrics") as mock_storage,
            patch.object(CIHealthMonitor, "_check_component_health") as mock_component,
            patch.object(CIHealthMonitor, "_check_performance_status") as mock_perf,
            patch.object(CIHealthMonitor, "_check_security_status") as mock_security,
        ):
            # Setup mocks
            mock_system.return_value = {"cpu_usage_percent": 25.0}
            mock_storage.return_value = {"project_root": {"usage_percent": 50.0}}
            mock_component.return_value = {"performance": {"status": "healthy"}}
            mock_perf.return_value = {"status": "healthy"}
            mock_security.return_value = {"status": "healthy"}

            monitor = CIHealthMonitor(project_path=temp_project_dir)
            metrics = monitor.collect_health_metrics()

            assert "timestamp" in metrics
            assert "system_info" in metrics
            assert "storage_usage" in metrics
            assert "component_health" in metrics
            assert "performance_status" in metrics
            assert "security_status" in metrics
            assert monitor.last_health_check is not None

    def test_check_component_health(self, temp_project_dir):
        """Test component health checking."""
        # Create some test files in reports directory
        reports_dir = temp_project_dir / "artifacts" / "reports"
        (reports_dir / "test_report.json").write_text('{"test": "data"}')

        monitor = CIHealthMonitor(project_path=temp_project_dir)

        with (
            patch.object(monitor.performance_collector, "get_recent_history") as mock_history,
            patch.object(monitor.dependency_analyzer, "detect_package_managers") as mock_pkg_mgr,
        ):
            mock_history.return_value = [Mock(timestamp=datetime.now())]
            mock_pkg_mgr.return_value = ["pip", "pixi"]

            health = monitor._check_component_health()

            assert "performance" in health
            assert "security" in health
            assert "reporting" in health

            assert health["performance"]["status"] == "healthy"
            assert health["security"]["status"] == "healthy"
            assert health["reporting"]["status"] == "healthy"

    def test_check_performance_status_no_data(self, temp_project_dir):
        """Test performance status check with no data."""
        monitor = CIHealthMonitor(project_path=temp_project_dir)

        with patch.object(monitor.performance_collector, "get_recent_history") as mock_history:
            mock_history.return_value = []

            status = monitor._check_performance_status()

            assert status["status"] == "no_data"
            assert "No recent performance data found" in status["message"]

    def test_check_performance_status_with_data(self, temp_project_dir):
        """Test performance status check with data."""
        monitor = CIHealthMonitor(project_path=temp_project_dir)

        # Create mock metrics with results
        mock_result = Mock()
        mock_result.execution_time = 100.0

        mock_metrics = Mock()
        mock_metrics.results = [mock_result]

        with patch.object(monitor.performance_collector, "get_recent_history") as mock_history:
            mock_history.return_value = [mock_metrics] * 5

            status = monitor._check_performance_status()

            assert status["status"] == "healthy"
            assert status["avg_execution_time"] == 100.0
            assert status["recent_runs"] == 5

    def test_check_security_status(self, temp_project_dir):
        """Test security status checking."""
        monitor = CIHealthMonitor(project_path=temp_project_dir)

        # Mock dependencies with vulnerabilities - need more than 5 high to trigger warning
        mock_vulns = []
        for _ in range(6):  # Create 6 high severity vulnerabilities
            mock_vuln = Mock()
            mock_vuln.severity = "high"
            mock_vulns.append(mock_vuln)

        mock_dep = Mock()
        mock_dep.has_vulnerabilities = True
        mock_dep.vulnerabilities = mock_vulns

        with patch.object(monitor.dependency_analyzer, "scan_dependencies") as mock_scan:
            mock_scan.return_value = [mock_dep]

            status = monitor._check_security_status()

            assert status["status"] == "warning"  # More than 5 high severity should trigger warning
            assert status["total_dependencies"] == 1
            assert status["vulnerable_dependencies"] == 1
            assert status["severity_breakdown"]["high"] == 6

    def test_calculate_performance_trend(self, temp_project_dir):
        """Test performance trend calculation."""
        monitor = CIHealthMonitor(project_path=temp_project_dir)

        # Create mock metrics with degrading performance
        metrics_list = []
        for _, exec_time in enumerate([100, 105, 110, 115, 120]):
            mock_result = Mock()
            mock_result.execution_time = exec_time

            mock_metrics = Mock()
            mock_metrics.results = [mock_result]
            metrics_list.append(mock_metrics)

        trend = monitor._calculate_performance_trend(metrics_list)
        assert trend == "degrading"

    def test_run_diagnostics(self, temp_project_dir):
        """Test comprehensive diagnostics."""
        monitor = CIHealthMonitor(project_path=temp_project_dir)

        with (
            patch.object(monitor, "_diagnose_performance_component") as mock_perf,
            patch.object(monitor, "_diagnose_security_component") as mock_security,
            patch.object(monitor, "_diagnose_reporting_component") as mock_reporting,
            patch.object(monitor, "_diagnose_storage_health") as mock_storage,
        ):
            mock_perf.return_value = {"status": "healthy"}
            mock_security.return_value = {"status": "warning"}
            mock_reporting.return_value = {"status": "healthy"}
            mock_storage.return_value = {"status": "healthy"}

            diagnostics = monitor.run_diagnostics()

            assert "timestamp" in diagnostics
            assert diagnostics["performance"]["status"] == "healthy"
            assert diagnostics["security"]["status"] == "warning"
            assert diagnostics["overall_status"] == "warning"  # Should match worst component

    def test_diagnose_performance_component_no_data(self, temp_project_dir):
        """Test performance component diagnosis with missing data."""
        # Don't create performance_data directory
        monitor = CIHealthMonitor(project_path=temp_project_dir)

        # Remove the performance_data directory to simulate missing data
        import shutil

        shutil.rmtree(temp_project_dir / "performance_data")

        diagnosis = monitor._diagnose_performance_component()

        assert diagnosis["status"] == "warning"
        assert "Performance data directory not found" in diagnosis["message"]

    def test_diagnose_security_component(self, temp_project_dir):
        """Test security component diagnosis."""
        monitor = CIHealthMonitor(project_path=temp_project_dir)

        with patch.object(monitor.dependency_analyzer, "detect_package_managers") as mock_detect:
            mock_detect.return_value = ["pip", "pixi"]

            diagnosis = monitor._diagnose_security_component()

            assert diagnosis["status"] in ["healthy", "warning"]
            assert diagnosis["package_managers"] == ["pip", "pixi"]

    def test_diagnose_reporting_component(self, temp_project_dir):
        """Test reporting component diagnosis."""
        # Create a test report file
        reports_dir = temp_project_dir / "artifacts" / "reports"
        report_file = reports_dir / "test_report.json"
        report_file.write_text('{"test": "data"}')

        monitor = CIHealthMonitor(project_path=temp_project_dir)
        diagnosis = monitor._diagnose_reporting_component()

        assert diagnosis["status"] == "healthy"
        assert diagnosis["total_reports"] >= 1

    def test_get_health_summary(self, temp_project_dir):
        """Test health summary generation."""
        monitor = CIHealthMonitor(project_path=temp_project_dir)

        with (
            patch.object(monitor, "collect_health_metrics") as mock_collect,
            patch.object(monitor, "_determine_overall_status") as mock_status,
            patch.object(monitor, "_get_component_summary") as mock_summary,
            patch.object(monitor, "_generate_health_recommendations") as mock_recommendations,
        ):
            mock_collect.return_value = {"test": "data"}
            mock_status.return_value = "healthy"
            mock_summary.return_value = {"performance": "healthy"}
            mock_recommendations.return_value = ["No issues found"]

            monitor.last_health_check = datetime.now()
            monitor.metrics = {"test": "data"}

            summary = monitor.get_health_summary()

            assert summary["overall_status"] == "healthy"
            assert "last_check" in summary
            assert "component_summary" in summary
            assert "recommendations" in summary

    def test_determine_overall_status_critical(self, temp_project_dir):
        """Test overall status determination with critical conditions."""
        monitor = CIHealthMonitor(project_path=temp_project_dir)
        monitor.metrics = {
            "system_info": {"cpu_usage_percent": 95},  # Critical CPU usage
            "component_health": {"performance": {"status": "healthy"}},
            "performance_status": {"status": "healthy"},
            "security_status": {"status": "healthy"},
        }

        status = monitor._determine_overall_status()
        assert status == "critical"

    def test_generate_health_recommendations(self, temp_project_dir):
        """Test health recommendations generation."""
        monitor = CIHealthMonitor(project_path=temp_project_dir)
        monitor.metrics = {
            "system_info": {"cpu_usage_percent": 85, "memory_usage_percent": 90},
            "performance_status": {"status": "no_data"},
            "security_status": {"status": "critical", "severity_breakdown": {"critical": 2}},
            "storage_usage": {"project_root": {"usage_percent": 90}},
        }

        recommendations = monitor._generate_health_recommendations()

        assert any("CPU usage" in rec for rec in recommendations)
        assert any("memory usage" in rec for rec in recommendations)
        assert any("performance benchmarks" in rec for rec in recommendations)
        assert any("Critical security vulnerabilities" in rec for rec in recommendations)
        assert any("storage usage" in rec for rec in recommendations)
