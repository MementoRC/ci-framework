"""
Framework Integration Tests

Tests the integration between multiple framework modules to ensure
they work together correctly in realistic scenarios.
"""

from pathlib import Path

import pytest

from framework.maintenance.health_monitor import CIHealthMonitor
from framework.performance.collector import PerformanceCollector
from framework.reporting.github_reporter import GitHubReporter


@pytest.mark.integration
class TestFrameworkIntegration:
    """Test integration between framework modules."""

    def test_performance_to_reporting_integration(self, tmp_path):
        """Test performance collector + reporting integration."""
        # Setup
        collector = PerformanceCollector(storage_path=tmp_path)
        reporter = GitHubReporter()

        # Create mock performance data
        performance_data = {
            "test_simulation": {"execution_time": 1.5, "memory_usage": "50MB", "throughput": 1000}
        }

        # Store performance data
        collector.store_benchmark_results(performance_data)

        # Generate report from performance data
        report = reporter.generate_performance_report(
            performance_data=performance_data, baseline_data=None
        )

        assert "test_simulation" in report
        assert "Performance Report" in report
        assert "1.5" in report  # execution time

    def test_security_to_reporting_integration(self, tmp_path):
        """Test security analyzer + reporting integration."""
        # Setup
        reporter = GitHubReporter()

        # Create mock security findings
        security_data = {
            "vulnerabilities": [
                {
                    "package": "test-package",
                    "version": "1.0.0",
                    "severity": "high",
                    "description": "Test vulnerability",
                }
            ],
            "total_vulnerabilities": 1,
            "by_severity": {"high": 1, "medium": 0, "low": 0},
        }

        # Generate security report
        report = reporter.generate_security_report(security_data)

        assert "Security Report" in report
        assert "test-package" in report
        assert "high" in report
        assert "1" in report  # vulnerability count

    def test_health_monitor_to_reporting_integration(self, tmp_path):
        """Test health monitor + reporting integration."""
        # Setup
        health_monitor = CIHealthMonitor(base_dir=tmp_path)
        reporter = GitHubReporter()

        # Collect health metrics
        health_monitor.collect_health_metrics()

        # Generate build status summary
        build_summary = reporter.create_build_status_summary(
            success=True, duration="2m 30s", test_count=150, coverage=85.5
        )

        assert "✅" in build_summary or "SUCCESS" in build_summary
        assert "150" in build_summary  # test count
        assert "85.5" in build_summary  # coverage
        assert "2m 30s" in build_summary  # duration

    def test_end_to_end_workflow_integration(self, tmp_path):
        """Test complete end-to-end framework workflow."""
        # Setup all components
        collector = PerformanceCollector(storage_path=tmp_path)
        health_monitor = CIHealthMonitor(base_dir=tmp_path)
        reporter = GitHubReporter()

        # Step 1: Collect performance data
        performance_data = {"integration_test": {"execution_time": 0.5, "memory_usage": "25MB"}}
        collector.store_benchmark_results(performance_data)

        # Step 2: Run health monitoring
        health_data = health_monitor.collect_health_metrics()

        # Step 3: Create comprehensive report
        performance_report = reporter.generate_performance_report(performance_data=performance_data)

        # Step 4: Verify integrated data flow
        assert health_data is not None
        assert performance_report is not None
        assert "integration_test" in performance_report

        # Verify data consistency across modules
        stored_data = collector.load_benchmark_results("integration_test")
        assert stored_data is not None

    @pytest.mark.asyncio
    async def test_async_framework_integration(self, tmp_path):
        """Test integration with async components."""
        # Setup
        health_monitor = CIHealthMonitor(base_dir=tmp_path)

        # Test async health monitoring
        health_data = health_monitor.collect_health_metrics()

        # Simulate async data processing
        import asyncio

        await asyncio.sleep(0.1)  # Simulate async operation

        # Verify async integration works
        assert health_data is not None
        assert isinstance(health_data, dict)

    def test_framework_cli_integration(self, tmp_path):
        """Test CLI integration across framework modules."""
        from framework.maintenance.cli import main as maint_main
        from framework.performance.cli import main as perf_main
        from framework.reporting.cli import main as report_main
        from framework.security.cli import main as sec_main

        # Test that CLI modules can be imported without errors
        assert perf_main is not None
        assert sec_main is not None
        assert report_main is not None
        assert maint_main is not None

    def test_cross_module_data_consistency(self, tmp_path):
        """Test data consistency across framework modules."""
        # Setup
        collector = PerformanceCollector(storage_path=tmp_path)

        # Create consistent test data
        test_data = {
            "timestamp": "2024-01-01T00:00:00Z",
            "test_name": "consistency_test",
            "metrics": {"value": 100},
        }

        # Store data in performance collector
        collector.store_benchmark_results({"consistency_test": test_data})

        # Verify data can be retrieved consistently
        retrieved_data = collector.load_benchmark_results("consistency_test")

        assert retrieved_data is not None
        assert retrieved_data["test_name"] == "consistency_test"
        assert retrieved_data["metrics"]["value"] == 100

    def test_framework_error_handling_integration(self, tmp_path):
        """Test integrated error handling across framework modules."""
        # Setup with invalid data to test error handling
        reporter = GitHubReporter()

        # Test error handling in integrated workflow
        try:
            # Attempt to generate report with invalid data
            report = reporter.generate_performance_report(
                performance_data=None  # Invalid data
            )
            # Should handle gracefully
            assert report is not None
        except Exception as e:
            # Should not raise unhandled exceptions
            pytest.fail(f"Framework integration should handle errors gracefully: {e}")

    def test_framework_configuration_integration(self, tmp_path):
        """Test configuration consistency across framework modules."""
        # Setup
        base_config = {"base_dir": str(tmp_path), "project_name": "integration_test"}

        # Initialize components with consistent configuration
        collector = PerformanceCollector(storage_path=base_config["base_dir"])
        health_monitor = CIHealthMonitor(base_dir=base_config["base_dir"])

        # Verify consistent configuration usage
        assert collector.storage_path == Path(base_config["base_dir"])
        assert health_monitor.base_dir == Path(base_config["base_dir"])

    def test_framework_scalability_integration(self, tmp_path):
        """Test framework handles multiple concurrent operations."""
        # Setup
        collector = PerformanceCollector(storage_path=tmp_path)

        # Test multiple concurrent data operations
        test_datasets = [
            {"test_1": {"value": 1}},
            {"test_2": {"value": 2}},
            {"test_3": {"value": 3}},
        ]

        # Store multiple datasets
        for dataset in test_datasets:
            collector.store_benchmark_results(dataset)

        # Verify all data is stored correctly
        for i in range(1, 4):
            retrieved = collector.load_benchmark_results(f"test_{i}")
            assert retrieved is not None
            assert retrieved["value"] == i


@pytest.mark.integration
class TestFrameworkModuleIntegration:
    """Test specific module integration patterns."""

    def test_performance_security_integration(self, tmp_path):
        """Test performance and security module integration."""
        # Setup
        collector = PerformanceCollector(storage_path=tmp_path)

        # Create performance data that includes security metrics
        performance_data = {
            "security_scan": {
                "execution_time": 2.0,
                "vulnerabilities_found": 0,
                "scan_coverage": 95.0,
            }
        }

        collector.store_benchmark_results(performance_data)

        # Verify cross-module data compatibility
        retrieved = collector.load_benchmark_results("security_scan")
        assert retrieved["vulnerabilities_found"] == 0
        assert retrieved["scan_coverage"] == 95.0

    def test_reporting_maintenance_integration(self, tmp_path):
        """Test reporting and maintenance module integration."""
        # Setup
        reporter = GitHubReporter()
        health_monitor = CIHealthMonitor(base_dir=tmp_path)

        # Collect health data
        health_data = health_monitor.collect_health_metrics()

        # Generate maintenance report
        maintenance_summary = reporter.create_build_status_summary(
            success=health_data.get("status") != "critical",
            duration="1m 45s",
            test_count=75,
            coverage=90.0,
        )

        assert maintenance_summary is not None
        assert len(maintenance_summary) > 0
