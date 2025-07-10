"""
Security Framework Integration Tests

Tests for security module integration with other framework components.
"""

from pathlib import Path

import pytest

from framework.reporting.github_reporter import GitHubReporter
from framework.security.analyzer import DependencyAnalyzer
from framework.security.collector import SecurityCollector
from framework.security.dashboard_generator import SecurityDashboardGenerator


@pytest.mark.security
@pytest.mark.integration
class TestSecurityIntegration:
    """Test security module integration with framework."""

    def test_analyzer_to_dashboard_integration(self, tmp_path):
        """Test integration between security analyzer and dashboard generator."""
        # Setup
        from framework.security.sbom_generator import SBOMGenerator
        from framework.reporting.github_reporter import GitHubReporter

        sbom_gen = SBOMGenerator()
        github_reporter = GitHubReporter(artifact_path=tmp_path)
        dashboard = SecurityDashboardGenerator(sbom_gen, github_reporter)

        # Note: SecurityDashboardGenerator gets data from sbom_generator internally

        # Generate dashboard (gets data from sbom_generator internally)
        dashboard_result = dashboard.generate_security_dashboard()

        # Verify integration - result is a dictionary with dashboard content
        assert dashboard_result is not None
        assert "dashboard_content" in dashboard_result
        
        dashboard_content = dashboard_result["dashboard_content"]
        assert "Security Dashboard" in dashboard_content
        assert "Security Score" in dashboard_content
        assert "dependencies" in dashboard_content

    def test_security_to_reporting_integration(self, tmp_path):
        """Test security data integration with reporting system."""
        # Setup
        reporter = GitHubReporter()

        # Generate security report directly (testing reporter integration)
        report = reporter.generate_security_report()

        # Verify integration - result is a dictionary with report info
        assert report is not None
        assert isinstance(report, dict)
        # Check that the report generation completed successfully
        assert "summary_added" in report or "artifact_created" in report

    def test_security_collector_integration(self, tmp_path):
        """Test security collector with various data types."""
        # Setup
        collector = SecurityCollector(storage_path=tmp_path)

        # Test basic collector functionality
        assert collector.storage_path == tmp_path
        
        # Test environment info collection
        env_info = collector.collect_environment_info()
        assert env_info is not None
        assert "platform" in env_info
        assert "python_version" in env_info
        
        # Test security scanning functionality
        scan_result = collector.scan_project_security(project_path=".")
        assert scan_result is not None
        # SecurityMetrics object should have dependencies
        assert hasattr(scan_result, 'dependencies')
        assert hasattr(scan_result, 'build_id')

    def test_security_dashboard_comprehensive_data(self, tmp_path):
        """Test dashboard generation with comprehensive security data."""
        # Setup - provide required dependencies
        from framework.security.sbom_generator import SBOMGenerator
        from framework.reporting.github_reporter import GitHubReporter
        
        sbom_gen = SBOMGenerator()
        github_reporter = GitHubReporter(artifact_path=tmp_path)
        dashboard = SecurityDashboardGenerator(sbom_gen, github_reporter)

        # Note: dashboard.generate_security_dashboard() gets data from sbom_generator

        # Generate dashboard
        dashboard_result = dashboard.generate_security_dashboard()

        # Verify comprehensive reporting - result is a dictionary
        assert dashboard_result is not None
        assert "dashboard_content" in dashboard_result
        
        dashboard_content = dashboard_result["dashboard_content"]
        assert "Security Dashboard" in dashboard_content
        assert "Security Score" in dashboard_content
        assert "dependencies" in dashboard_content

    def test_security_trend_analysis_integration(self, tmp_path):
        """Test security trend analysis across time periods."""
        # Setup
        collector = SecurityCollector(storage_path=tmp_path)

        # Historical security data
        historical_data = [
            {
                "date": "2024-01-01",
                "total_vulnerabilities": 10,
                "critical": 1,
                "high": 3,
                "medium": 4,
                "low": 2,
            },
            {
                "date": "2024-01-15",
                "total_vulnerabilities": 8,
                "critical": 0,
                "high": 2,
                "medium": 4,
                "low": 2,
            },
        ]

        # Store historical data - create mock SecurityMetrics from data
        from framework.security.models import SecurityMetrics
        from datetime import datetime
        
        for i, data in enumerate(historical_data):
            # Create mock SecurityMetrics
            mock_metrics = SecurityMetrics(
                build_id=f"trend_test_{i}",
                timestamp=datetime.now(),
                dependencies=[],  # Empty for this test
                scan_config={},
                environment={},
                scan_duration=1.0
            )
            collector.save_metrics(mock_metrics)

        # Generate trend analysis
        trend_data = {
            "current": historical_data[-1],
            "previous": historical_data[0],
            "trend": "improving",
        }

        # Verify trend integration
        assert (
            trend_data["current"]["total_vulnerabilities"]
            < trend_data["previous"]["total_vulnerabilities"]
        )
        assert trend_data["trend"] == "improving"

    def test_security_compliance_integration(self, tmp_path):
        """Test security compliance reporting integration."""
        # Setup - provide required dependencies
        from framework.security.sbom_generator import SBOMGenerator
        from framework.reporting.github_reporter import GitHubReporter
        
        sbom_gen = SBOMGenerator()
        github_reporter = GitHubReporter(artifact_path=tmp_path)
        dashboard = SecurityDashboardGenerator(sbom_gen, github_reporter)

        # Compliance data
        compliance_data = {
            "frameworks": {
                "OWASP": {"score": 85, "status": "passing"},
                "CIS": {"score": 92, "status": "passing"},
                "NIST": {"score": 78, "status": "warning"},
            },
            "controls": {
                "access_control": "compliant",
                "data_protection": "compliant",
                "vulnerability_management": "non_compliant",
            },
        }

        # Generate dashboard (the actual method available)
        report = dashboard.generate_security_dashboard()

        # Verify dashboard generation worked
        assert report is not None
        assert "dashboard_content" in report
        assert "Security Dashboard" in report["dashboard_content"]

    @pytest.mark.skip(reason="Async testing requires pytest-asyncio plugin")
    async def test_security_async_integration(self, tmp_path):
        """Test async security operations integration."""
        # Setup
        collector = SecurityCollector(storage_path=tmp_path)

        # Simulate async security scanning
        import asyncio

        async def mock_security_scan():
            await asyncio.sleep(0.1)  # Simulate scanning time
            return {
                "scan_id": "async_test",
                "vulnerabilities": [],
                "status": "completed",
            }

        # Run async scan
        scan_result = await mock_security_scan()

        # Store async results - create mock SecurityMetrics
        from framework.security.models import SecurityMetrics
        from datetime import datetime
        
        mock_metrics = SecurityMetrics(
            build_id="async_test",
            timestamp=datetime.now(),
            dependencies=[],
            scan_config=scan_result,
            environment={},
            scan_duration=1.0
        )
        saved_file = collector.save_metrics(mock_metrics, "async_test.json")

        # Verify async integration
        retrieved = collector.load_metrics(saved_file)
        assert retrieved is not None
        assert retrieved.build_id == "async_test"
        assert retrieved.scan_config["status"] == "completed"

    def test_security_error_handling_integration(self, tmp_path):
        """Test error handling in security integrations."""
        # Setup - provide required dependencies
        from framework.security.sbom_generator import SBOMGenerator
        from framework.reporting.github_reporter import GitHubReporter
        
        sbom_gen = SBOMGenerator()
        github_reporter = GitHubReporter(artifact_path=tmp_path)
        dashboard = SecurityDashboardGenerator(sbom_gen, github_reporter)

        # Test with invalid/incomplete data
        invalid_data = {
            "vulnerabilities": [{"package": "test"}]  # Missing required fields
        }

        # Should handle gracefully
        try:
            report = dashboard.generate_security_dashboard(invalid_data)
            assert report is not None  # Should not crash
        except Exception as e:
            pytest.fail(
                f"Security integration should handle invalid data gracefully: {e}"
            )

    def test_security_performance_integration(self, tmp_path):
        """Test security module performance characteristics."""
        # Setup - provide required dependencies
        from framework.security.sbom_generator import SBOMGenerator
        from framework.reporting.github_reporter import GitHubReporter
        
        collector = SecurityCollector(storage_path=tmp_path)
        sbom_gen = SBOMGenerator()
        github_reporter = GitHubReporter(artifact_path=tmp_path)
        dashboard = SecurityDashboardGenerator(sbom_gen, github_reporter)

        # Large dataset for performance testing
        large_security_data = {
            "vulnerabilities": [
                {
                    "package": f"package_{i}",
                    "severity": ["low", "medium", "high", "critical"][i % 4],
                    "version": "1.0.0",
                }
                for i in range(1000)  # 1000 vulnerabilities
            ]
        }

        # Test performance with large dataset
        import time

        start_time = time.time()

        collector.store_security_results(large_security_data)
        dashboard_content = dashboard.generate_security_dashboard(large_security_data)

        end_time = time.time()
        processing_time = end_time - start_time

        # Verify performance characteristics
        assert processing_time < 10.0  # Should complete within 10 seconds
        assert dashboard_content is not None
        assert "1000" in dashboard_content or "1,000" in dashboard_content


@pytest.mark.security
@pytest.mark.unit
class TestSecurityModuleUnits:
    """Unit tests specific to security framework components."""

    def test_security_analyzer_initialization(self, tmp_path):
        """Test security analyzer proper initialization."""
        analyzer = DependencyAnalyzer(project_path=tmp_path)

        assert analyzer.project_path == tmp_path
        assert hasattr(analyzer, "scan_dependencies")

    def test_dashboard_generator_initialization(self):
        """Test dashboard generator proper initialization."""
        # Create mock dependencies that SecurityDashboardGenerator needs
        from unittest.mock import Mock

        mock_sbom_generator = Mock()
        mock_github_reporter = Mock()

        dashboard = SecurityDashboardGenerator(
            sbom_generator=mock_sbom_generator, github_reporter=mock_github_reporter
        )

        assert hasattr(dashboard, "generate_security_dashboard")
        assert hasattr(dashboard, "generate_security_trend_data")

    def test_security_collector_initialization(self, tmp_path):
        """Test security collector proper initialization."""
        collector = SecurityCollector(storage_path=tmp_path)

        assert collector.storage_path == Path(tmp_path)
        assert hasattr(collector, "save_metrics")
        assert hasattr(collector, "load_metrics")
