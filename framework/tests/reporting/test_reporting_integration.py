"""
Reporting Framework Integration Tests

Tests for reporting module integration with other framework components.
"""

import json
from pathlib import Path

import pytest

from framework.reporting.artifact_manager import ArtifactManager
from framework.reporting.github_reporter import GitHubReporter
from framework.reporting.report_generator import ReportGenerator
from framework.reporting.template_engine import TemplateEngine


@pytest.mark.reporting
@pytest.mark.integration
class TestReportingIntegration:
    """Test reporting module integration with framework."""

    def test_github_reporter_to_artifact_manager_integration(self, tmp_path):
        """Test integration between GitHub reporter and artifact manager."""
        # Setup - ensure no GitHub environment for consistent test behavior
        import os

        original_env = os.environ.get("GITHUB_STEP_SUMMARY")
        if "GITHUB_STEP_SUMMARY" in os.environ:
            del os.environ["GITHUB_STEP_SUMMARY"]

        try:
            reporter = GitHubReporter()
            artifact_manager = ArtifactManager(artifact_path=tmp_path)

            # Generate report
            performance_data = {
                "test_suite": {
                    "execution_time": 2.5,
                    "memory_usage": "75MB",
                    "throughput": 500,
                }
            }

            # Generate performance report (this creates its own artifact)
            report_result = reporter.generate_performance_report(
                performance_metrics=performance_data
            )

            # The report creates its own artifact, so let's test creating another one
            artifact_path = artifact_manager.create_report_artifact(
                report_name="performance_report",
                report_data=performance_data,
                format_type="json",
            )

            # Verify integration
            assert artifact_path.exists()
            stored_content = artifact_path.read_text()
            assert "test_suite" in stored_content

            # Verify the report result
            assert report_result["summary_added"] is False  # No GitHub environment
            assert report_result["artifact_created"] is not None
        finally:
            # Restore original environment
            if original_env is not None:
                os.environ["GITHUB_STEP_SUMMARY"] = original_env

    def test_report_generator_comprehensive_integration(self, tmp_path):
        """Test comprehensive report generation integration."""
        # Setup
        report_generator = ReportGenerator()

        # Comprehensive data from multiple sources
        coverage_data = {
            "line_coverage": 85.5,
            "branch_coverage": 78.2,
            "total_lines": 1000,
            "covered_lines": 855,
        }

        performance_data = {
            "baseline": {"execution_time": 2.0},
            "current": {"execution_time": 1.8},
            "improvement": 10.0,
        }

        # Generate comprehensive report
        report_generator.set_coverage_data(coverage_data)
        report_generator.add_performance_trend(performance_data)

        # Generate comprehensive report with available data
        comprehensive_report = report_generator.generate_comprehensive_report()

        # Verify comprehensive integration
        assert comprehensive_report is not None
        assert "report_sections" in comprehensive_report

        # Check coverage data in report sections
        coverage_section = comprehensive_report["report_sections"].get(
            "coverage_report", ""
        )
        assert "85.5" in coverage_section  # Coverage

        # Check performance data in report sections
        perf_section = comprehensive_report["report_sections"].get(
            "performance_dashboard", ""
        )
        assert (
            "1.8" in perf_section or "performance" in perf_section.lower()
        )  # Performance

        # Verify substantial content across all sections
        total_content = "".join(comprehensive_report["report_sections"].values())
        assert len(total_content) > 1000  # Substantial content

    def test_template_engine_integration(self, tmp_path):
        """Test template engine integration with reporting components."""
        # Setup
        template_engine = TemplateEngine()

        # Test template rendering with various data types
        build_data = {
            "status": "success",
            "duration": 225,  # 3m 45s = 225 seconds
            "test_count": 200,
            "coverage": 92.3,
        }

        # Render using template engine
        build_summary = template_engine.render_build_status(
            {
                "build_status": build_data["status"],
                "test_results": {
                    "total": build_data["test_count"],
                    "passed": 200,
                    "failed": 0,
                    "duration": build_data["duration"],
                },
            }
        )

        # Verify template integration
        assert build_summary is not None
        assert "200" in build_summary  # Total and passed tests
        assert "225.00s" in build_summary  # Duration
        assert "success" in build_summary.lower()  # Status

    def test_artifact_manager_multiple_formats_integration(self, tmp_path):
        """Test artifact manager with multiple report formats."""
        # Setup
        artifact_manager = ArtifactManager(artifact_path=tmp_path)

        # Test data
        test_data = {
            "timestamp": "2024-01-01T00:00:00Z",
            "results": {"tests": 150, "failures": 0},
        }

        # Create artifacts in different formats
        json_artifact = artifact_manager.create_artifact(
            name="test_results.json", content=test_data, content_type="application/json"
        )

        text_artifact = artifact_manager.create_artifact(
            name="summary.txt",
            content="Test Results Summary\n===================\nTests: 150\nFailures: 0",
            content_type="text/plain",
        )

        # Verify multiple format integration
        assert json_artifact.exists()
        assert text_artifact.exists()

        # Verify content integrity
        json_content = json.loads(json_artifact.read_text())
        assert json_content["results"]["tests"] == 150

        text_content = text_artifact.read_text()
        assert "Tests: 150" in text_content

    def test_reporting_with_performance_data_integration(self, tmp_path):
        """Test reporting integration with performance data from framework."""
        # Setup
        reporter = GitHubReporter()
        artifact_manager = ArtifactManager(artifact_path=tmp_path)

        # Mock performance data from framework.performance
        performance_metrics = {
            "benchmarks": {
                "simulation_throughput": {
                    "current": 1500,
                    "baseline": 1200,
                    "improvement": 25.0,
                },
                "memory_efficiency": {
                    "current": "45MB",
                    "baseline": "52MB",
                    "improvement": 13.5,
                },
            },
            "summary": {"total_benchmarks": 2, "improvements": 2, "regressions": 0},
        }

        # Generate performance report (creates internal artifacts)
        reporter.generate_performance_report(performance_metrics=performance_metrics)

        # Store as artifact - pass the performance metrics data, not the result dict
        artifact_path = artifact_manager.create_report_artifact(
            report_name="performance_analysis",
            report_data=performance_metrics,
            format_type="markdown",
        )

        # Verify performance integration
        assert artifact_path.exists()
        content = artifact_path.read_text()
        assert "1500" in content  # Current throughput
        assert "25.0" in content  # Improvement percentage
        assert "45MB" in content  # Memory usage

    def test_reporting_with_security_data_integration(self, tmp_path):
        """Test reporting integration with security data from framework."""
        # Setup
        reporter = GitHubReporter()

        # Mock security data from framework.security
        security_findings = {
            "scan_results": {
                "total_packages": 150,
                "vulnerable_packages": 8,
                "vulnerabilities": [
                    {
                        "package": "requests",
                        "version": "2.25.1",
                        "severity": "medium",
                        "fixed_version": "2.32.4",
                    },
                    {
                        "package": "urllib3",
                        "version": "1.26.5",
                        "severity": "high",
                        "fixed_version": "1.26.19",
                    },
                ],
            },
            "severity_breakdown": {"critical": 0, "high": 1, "medium": 6, "low": 1},
        }

        # Generate security report
        security_report = reporter.generate_security_report(security_findings)

        # Verify security integration
        assert security_report is not None
        assert "artifact_created" in security_report
        assert security_report["artifact_created"].exists()
        # Check that artifact was created successfully
        assert security_report["artifact_created"].stat().st_size > 0

    def test_reporting_error_handling_integration(self, tmp_path):
        """Test error handling in reporting integrations."""
        # Setup
        reporter = GitHubReporter()

        # Test with various invalid inputs
        invalid_inputs = [
            None,
            {},
            {"invalid": "structure"},
            {"missing_required_fields": True},
        ]

        for invalid_input in invalid_inputs:
            try:
                # Should handle gracefully without crashing
                report = reporter.generate_performance_report(
                    performance_metrics=invalid_input
                )
                assert report is not None  # Should return some content
            except Exception as e:
                pytest.fail(f"Reporting should handle invalid input gracefully: {e}")

    def test_reporting_large_dataset_integration(self, tmp_path):
        """Test reporting with large datasets."""
        # Setup
        reporter = GitHubReporter()
        artifact_manager = ArtifactManager(artifact_path=tmp_path)

        # Large performance dataset
        large_dataset = {
            "benchmarks": {
                f"test_{i}": {
                    "execution_time": i * 0.1,
                    "memory_usage": f"{i * 5}MB",
                    "throughput": 1000 + i,
                }
                for i in range(100)  # 100 benchmarks
            }
        }

        # Generate report with large dataset
        import time

        start_time = time.time()

        report = reporter.generate_performance_report(performance_metrics=large_dataset)

        # Store large report
        artifact_path = artifact_manager.create_report_artifact(
            report_name="large_performance_report",
            report_data=report,
            format_type="markdown",
        )

        end_time = time.time()
        processing_time = end_time - start_time

        # Verify large dataset handling
        assert processing_time < 5.0  # Should complete within 5 seconds
        assert artifact_path.exists()
        assert (
            artifact_path.stat().st_size > 100
        )  # Substantial content (realistic size)

    def test_reporting_template_customization_integration(self, tmp_path):
        """Test template customization integration."""
        # Setup
        template_engine = TemplateEngine()

        # Custom template data
        custom_data = {
            "project_name": "Framework Integration Test",
            "build_number": 42,
            "branch": "feature/comprehensive-testing",
            "commit_sha": "abc123def456",
        }

        # Test custom template rendering
        context = {
            "metrics": {
                "results": [
                    {
                        "name": custom_data["project_name"],
                        "execution_time": 2.5,
                        "memory_usage": 512,
                        "throughput": 100,
                    }
                ],
                "summary_stats": {
                    "build_number": custom_data["build_number"],
                    "branch": custom_data["branch"],
                },
            },
            "timestamp": "2024-01-01T12:00:00Z",
        }
        performance_summary = template_engine.render_performance_summary(context)

        # Verify customization integration
        assert custom_data["project_name"] in performance_summary
        assert str(custom_data["build_number"]) in performance_summary
        assert custom_data["branch"] in performance_summary

    @pytest.mark.skip(reason="Async testing requires pytest-asyncio plugin")
    async def test_reporting_async_integration(self, tmp_path):
        """Test async reporting operations integration."""
        # Setup
        artifact_manager = ArtifactManager(artifact_path=tmp_path)

        # Simulate async report generation
        import asyncio

        async def generate_async_report():
            await asyncio.sleep(0.1)  # Simulate async processing
            return {
                "async_report": True,
                "generation_time": "0.1s",
                "status": "completed",
            }

        # Generate async report
        async_data = await generate_async_report()

        # Store async results
        artifact_path = artifact_manager.create_json_artifact(
            data=async_data, filename="async_report.json"
        )

        # Verify async integration
        assert artifact_path.exists()
        stored_data = json.loads(artifact_path.read_text())
        assert stored_data["async_report"] is True
        assert stored_data["status"] == "completed"


@pytest.mark.reporting
@pytest.mark.unit
class TestReportingModuleUnits:
    """Unit tests specific to reporting framework components."""

    def test_github_reporter_initialization(self):
        """Test GitHub reporter proper initialization."""
        reporter = GitHubReporter()

        assert hasattr(reporter, "generate_performance_report")
        assert hasattr(reporter, "generate_security_report")
        assert hasattr(reporter, "create_build_status_summary")

    def test_report_generator_initialization(self):
        """Test report generator proper initialization."""
        generator = ReportGenerator()

        assert hasattr(generator, "set_coverage_data")
        assert hasattr(generator, "add_performance_trend")
        assert hasattr(generator, "generate_comprehensive_report")

    def test_artifact_manager_initialization(self, tmp_path):
        """Test artifact manager proper initialization."""
        manager = ArtifactManager(artifact_path=tmp_path)

        assert manager.artifact_path == Path(tmp_path)
        assert hasattr(manager, "create_artifact")
        assert hasattr(manager, "create_report_artifact")
        assert hasattr(manager, "create_log_artifact")
        assert hasattr(manager, "create_data_artifact")

    def test_template_engine_initialization(self):
        """Test template engine proper initialization."""
        engine = TemplateEngine()

        assert hasattr(engine, "render_build_status")
        assert hasattr(engine, "render_performance_summary")
        assert hasattr(engine, "render_security_summary")
