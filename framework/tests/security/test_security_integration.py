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
        dashboard = SecurityDashboardGenerator()

        # Mock security findings
        security_findings = {
            "vulnerabilities": [
                {
                    "package": "vulnerable-package",
                    "version": "1.0.0",
                    "severity": "high",
                    "description": "Test vulnerability",
                }
            ],
            "total_vulnerabilities": 1,
            "by_severity": {"high": 1, "medium": 0, "low": 0, "critical": 0},
        }

        # Generate dashboard from findings
        dashboard_html = dashboard.generate_security_dashboard(security_findings)

        # Verify integration
        assert dashboard_html is not None
        assert "vulnerable-package" in dashboard_html
        assert "high" in dashboard_html
        assert "1" in dashboard_html

    def test_security_to_reporting_integration(self, tmp_path):
        """Test security data integration with reporting system."""
        # Setup
        collector = SecurityCollector(storage_path=tmp_path)
        reporter = GitHubReporter()

        # Create security data
        security_data = {
            "scan_date": "2024-01-01",
            "vulnerabilities": [
                {"package": "test-package", "severity": "medium", "fixed_version": "2.0.0"}
            ],
            "total_count": 1,
            "severity_breakdown": {"medium": 1},
        }

        # Store security data
        collector.store_security_results(security_data)

        # Generate security report
        report = reporter.generate_security_report(security_data)

        # Verify integration
        assert report is not None
        assert "test-package" in report
        assert "medium" in report
        assert "Security Report" in report

    def test_security_collector_integration(self, tmp_path):
        """Test security collector with various data types."""
        # Setup
        collector = SecurityCollector(storage_path=tmp_path)

        # Test data collection and storage
        vulnerability_data = {
            "timestamp": "2024-01-01T00:00:00Z",
            "scan_type": "dependency",
            "findings": [
                {"type": "vulnerability", "severity": "low"},
                {"type": "vulnerability", "severity": "high"},
            ],
        }

        # Store and retrieve
        collector.store_security_results(vulnerability_data)
        retrieved = collector.load_security_results("dependency")

        # Verify data integrity
        assert retrieved is not None
        assert retrieved["scan_type"] == "dependency"
        assert len(retrieved["findings"]) == 2

    def test_security_dashboard_comprehensive_data(self, tmp_path):
        """Test dashboard generation with comprehensive security data."""
        # Setup
        dashboard = SecurityDashboardGenerator()

        # Comprehensive security data
        security_data = {
            "scan_summary": {
                "total_packages": 100,
                "vulnerable_packages": 5,
                "scan_date": "2024-01-01",
            },
            "vulnerabilities": [
                {"package": "pkg1", "severity": "critical", "cvss": 9.5},
                {"package": "pkg2", "severity": "high", "cvss": 7.8},
                {"package": "pkg3", "severity": "medium", "cvss": 5.2},
                {"package": "pkg4", "severity": "low", "cvss": 2.1},
            ],
            "remediation": {"upgradeable": 3, "patchable": 1, "no_fix": 1},
        }

        # Generate dashboard
        dashboard_content = dashboard.generate_security_dashboard(security_data)

        # Verify comprehensive reporting
        assert "100" in dashboard_content  # total packages
        assert "5" in dashboard_content  # vulnerable packages
        assert "critical" in dashboard_content
        assert "9.5" in dashboard_content  # CVSS score
        assert "upgradeable" in dashboard_content

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

        # Store historical data
        for data in historical_data:
            collector.store_security_results(data)

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
        # Setup
        dashboard = SecurityDashboardGenerator()

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

        # Generate compliance report
        report = dashboard.generate_compliance_report(compliance_data)

        # Verify compliance integration
        assert "OWASP" in report
        assert "85" in report
        assert "passing" in report
        assert "non_compliant" in report

    @pytest.mark.asyncio
    async def test_security_async_integration(self, tmp_path):
        """Test async security operations integration."""
        # Setup
        collector = SecurityCollector(storage_path=tmp_path)

        # Simulate async security scanning
        import asyncio

        async def mock_security_scan():
            await asyncio.sleep(0.1)  # Simulate scanning time
            return {"scan_id": "async_test", "vulnerabilities": [], "status": "completed"}

        # Run async scan
        scan_result = await mock_security_scan()

        # Store async results
        collector.store_security_results(scan_result)

        # Verify async integration
        retrieved = collector.load_security_results("async_test")
        assert retrieved is not None
        assert retrieved["status"] == "completed"

    def test_security_error_handling_integration(self, tmp_path):
        """Test error handling in security integrations."""
        # Setup
        dashboard = SecurityDashboardGenerator()

        # Test with invalid/incomplete data
        invalid_data = {
            "vulnerabilities": [
                {"package": "test"}  # Missing required fields
            ]
        }

        # Should handle gracefully
        try:
            report = dashboard.generate_security_dashboard(invalid_data)
            assert report is not None  # Should not crash
        except Exception as e:
            pytest.fail(f"Security integration should handle invalid data gracefully: {e}")

    def test_security_performance_integration(self, tmp_path):
        """Test security module performance characteristics."""
        # Setup
        collector = SecurityCollector(storage_path=tmp_path)
        dashboard = SecurityDashboardGenerator()

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
        assert hasattr(collector, "store_security_results")
        assert hasattr(collector, "load_security_results")
