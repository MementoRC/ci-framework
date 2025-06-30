"""Dynamic report generation system for comprehensive CI pipeline reporting."""

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from .github_reporter import GitHubReporter


@dataclass
class CoverageData:
    """Test coverage data structure."""

    overall_coverage: float
    line_coverage: float
    branch_coverage: float
    function_coverage: float
    modules: list[dict[str, Any]]
    trend_direction: str = "stable"
    trend_percentage: float | None = None


@dataclass
class PerformanceTrend:
    """Performance trend data structure."""

    metric_name: str
    current_value: float
    baseline_value: float | None
    historical_values: list[float]
    trend_direction: str
    change_percentage: float | None
    threshold_status: str  # "within", "warning", "critical"


@dataclass
class BuildInsight:
    """Build insight with actionable recommendations."""

    insight_type: str  # "warning", "recommendation", "success"
    title: str
    description: str
    action_items: list[str]
    priority: str  # "high", "medium", "low"


class ReportGenerator:
    """High-level orchestrator for generating comprehensive CI reports."""

    def __init__(
        self, github_reporter: GitHubReporter | None = None, artifact_path: str | None = None
    ):
        """Initialize report generator.

        Args:
            github_reporter: Existing GitHubReporter instance to use.
            artifact_path: Custom artifact path if not using existing reporter.
        """
        self.github_reporter = github_reporter or GitHubReporter(artifact_path)
        self.template_engine = self.github_reporter.template_engine
        self.artifact_manager = self.github_reporter.artifact_manager

        # Data aggregation storage
        self._coverage_data: CoverageData | None = None
        self._performance_trends: list[PerformanceTrend] = []
        self._build_insights: list[BuildInsight] = []

    def set_coverage_data(self, coverage_data: dict[str, Any] | CoverageData) -> None:
        """Set test coverage data for report generation.

        Args:
            coverage_data: Coverage data as dict or CoverageData instance.
        """
        if isinstance(coverage_data, dict):
            self._coverage_data = self._parse_coverage_data(coverage_data)
        else:
            self._coverage_data = coverage_data

    def add_performance_trend(self, trend: dict[str, Any] | PerformanceTrend) -> None:
        """Add performance trend data.

        Args:
            trend: Trend data as dict or PerformanceTrend instance.
        """
        trend_obj = self._parse_performance_trend(trend) if isinstance(trend, dict) else trend

        self._performance_trends.append(trend_obj)

    def add_build_insight(self, insight: dict[str, Any] | BuildInsight) -> None:
        """Add build insight with actionable recommendations.

        Args:
            insight: Insight data as dict or BuildInsight instance.
        """
        insight_obj = BuildInsight(**insight) if isinstance(insight, dict) else insight

        self._build_insights.append(insight_obj)

    def generate_coverage_report(self, include_trends: bool = True) -> str:
        """Generate comprehensive test coverage report with visualizations.

        Args:
            include_trends: Whether to include trend analysis.

        Returns:
            Formatted markdown content for coverage report.
        """
        if not self._coverage_data:
            return "*No coverage data available for report generation.*\n"

        coverage = self._coverage_data

        # Generate coverage report with enhanced formatting
        markdown = "# 📊 Test Coverage Report\n\n"

        # Overall coverage summary with visual indicator
        coverage_emoji = self._get_coverage_emoji(coverage.overall_coverage)
        markdown += f"## {coverage_emoji} Overall Coverage: {coverage.overall_coverage:.1f}%\n\n"

        # Coverage breakdown table
        markdown += "| Coverage Type | Percentage | Status |\n"
        markdown += "|---------------|------------|--------|\n"
        markdown += f"| Line Coverage | {coverage.line_coverage:.1f}% | {self._get_coverage_status(coverage.line_coverage)} |\n"
        markdown += f"| Branch Coverage | {coverage.branch_coverage:.1f}% | {self._get_coverage_status(coverage.branch_coverage)} |\n"
        markdown += f"| Function Coverage | {coverage.function_coverage:.1f}% | {self._get_coverage_status(coverage.function_coverage)} |\n\n"

        # Trend analysis
        if include_trends and coverage.trend_percentage is not None:
            trend_icon = self._get_trend_icon(coverage.trend_direction)
            markdown += f"**Trend**: {trend_icon} {coverage.trend_direction.title()} "
            markdown += f"({coverage.trend_percentage:+.1f}% from baseline)\n\n"

        # Module-level coverage
        if coverage.modules:
            markdown += "## Module Coverage Details\n\n"
            markdown += "| Module | Coverage | Lines | Branches |\n"
            markdown += "|--------|----------|-------|----------|\n"

            # Sort modules by coverage (lowest first for attention)
            sorted_modules = sorted(coverage.modules, key=lambda x: x.get("coverage", 0))

            for module in sorted_modules:
                name = module.get("name", "Unknown")
                cov = module.get("coverage", 0)
                lines = module.get("lines_covered", 0)
                total_lines = module.get("total_lines", 0)
                branches = module.get("branches_covered", 0)

                status = self._get_coverage_status(cov)
                markdown += (
                    f"| {name} | {cov:.1f}% {status} | {lines}/{total_lines} | {branches} |\n"
                )

        # Coverage insights and recommendations
        insights = self._generate_coverage_insights(coverage)
        if insights:
            markdown += "\n## 🎯 Coverage Insights\n\n"
            for insight in insights:
                markdown += f"- **{insight['title']}**: {insight['description']}\n"

        return markdown

    def generate_performance_dashboard(self, baseline_days: int = 30) -> str:
        """Generate performance trends dashboard with regression analysis.

        Args:
            baseline_days: Number of days to consider for baseline comparison.

        Returns:
            Formatted markdown content for performance dashboard.
        """
        if not self._performance_trends:
            return "*No performance trend data available for dashboard generation.*\n"

        markdown = "# ⚡ Performance Trends Dashboard\n\n"

        # Performance summary section
        critical_count = sum(
            1 for t in self._performance_trends if t.threshold_status == "critical"
        )
        warning_count = sum(1 for t in self._performance_trends if t.threshold_status == "warning")

        if critical_count > 0:
            markdown += f"🚨 **{critical_count} Critical Performance Issues Detected**\n\n"
        elif warning_count > 0:
            markdown += f"⚠️ **{warning_count} Performance Warnings**\n\n"
        else:
            markdown += "✅ **All Performance Metrics Within Acceptable Range**\n\n"

        # Trend analysis table
        markdown += "## Performance Metrics Overview\n\n"
        markdown += "| Metric | Current | Baseline | Change | Status | Trend |\n"
        markdown += "|--------|---------|----------|--------|--------|---------|\n"

        for trend in self._performance_trends:
            current_str = self._format_metric_value(trend.metric_name, trend.current_value)
            baseline_str = (
                self._format_metric_value(trend.metric_name, trend.baseline_value)
                if trend.baseline_value
                else "N/A"
            )
            change_str = f"{trend.change_percentage:+.1f}%" if trend.change_percentage else "N/A"
            status_icon = self._get_threshold_status_icon(trend.threshold_status)
            trend_icon = self._get_trend_icon(trend.trend_direction)

            markdown += f"| {trend.metric_name} | {current_str} | {baseline_str} | {change_str} | {status_icon} | {trend_icon} |\n"

        # Detailed trend analysis for critical metrics
        critical_trends = [t for t in self._performance_trends if t.threshold_status == "critical"]
        if critical_trends:
            markdown += "\n## 🚨 Critical Performance Issues\n\n"
            for trend in critical_trends:
                markdown += f"### {trend.metric_name}\n\n"
                markdown += f"- **Current Value**: {self._format_metric_value(trend.metric_name, trend.current_value)}\n"
                if trend.baseline_value:
                    markdown += f"- **Baseline**: {self._format_metric_value(trend.metric_name, trend.baseline_value)}\n"
                    markdown += f"- **Regression**: {trend.change_percentage:+.1f}%\n"

                # Add specific recommendations
                recommendations = self._get_performance_recommendations(trend)
                if recommendations:
                    markdown += "- **Recommendations**:\n"
                    for rec in recommendations:
                        markdown += f"  - {rec}\n"
                markdown += "\n"

        return markdown

    def generate_build_dashboard(
        self,
        test_results: dict[str, Any] | None = None,
        performance_data: dict[str, Any] | None = None,
        security_data: dict[str, Any] | None = None,
    ) -> str:
        """Generate comprehensive build status dashboard with actionable insights.

        Args:
            test_results: Test execution results.
            performance_data: Performance benchmark data.
            security_data: Security scan results.

        Returns:
            Formatted markdown content for build dashboard.
        """
        markdown = "# 🎯 Build Status Dashboard\n\n"

        # Overall health indicator
        overall_status = self._calculate_overall_status(
            test_results, performance_data, security_data
        )
        status_icon = self._get_status_icon(overall_status)

        markdown += f"## {status_icon} Overall Build Health: {overall_status.title()}\n\n"

        # Quick metrics summary
        markdown += "## Quick Metrics\n\n"
        markdown += "| Component | Status | Details |\n"
        markdown += "|-----------|--------|---------|\n"

        # Test results summary
        if test_results:
            test_status = "✅ Passing" if test_results.get("failed", 0) == 0 else "❌ Failing"
            test_details = f"{test_results.get('passed', 0)}/{test_results.get('total', 0)} tests"
            markdown += f"| Tests | {test_status} | {test_details} |\n"

        # Coverage summary
        if self._coverage_data:
            cov_status = self._get_coverage_status(self._coverage_data.overall_coverage)
            markdown += (
                f"| Coverage | {cov_status} | {self._coverage_data.overall_coverage:.1f}% |\n"
            )

        # Performance summary
        if self._performance_trends:
            perf_critical = sum(
                1 for t in self._performance_trends if t.threshold_status == "critical"
            )
            perf_status = "❌ Issues" if perf_critical > 0 else "✅ Good"
            perf_details = f"{len(self._performance_trends)} metrics tracked"
            markdown += f"| Performance | {perf_status} | {perf_details} |\n"

        # Security summary
        if security_data:
            sec_issues = self._count_security_issues(security_data)
            sec_status = "❌ Issues" if sec_issues > 0 else "✅ Clean"
            markdown += f"| Security | {sec_status} | {sec_issues} issues found |\n"

        markdown += "\n"

        # Actionable insights section
        if self._build_insights:
            markdown += "## 💡 Actionable Insights\n\n"

            # Group insights by priority
            high_priority: list[BuildInsight] = [
                i for i in self._build_insights if i.priority == "high"
            ]
            medium_priority: list[BuildInsight] = [
                i for i in self._build_insights if i.priority == "medium"
            ]

            if high_priority:
                markdown += "### 🔥 High Priority\n\n"
                for insight in high_priority:
                    markdown += self._format_insight(insight)

            if medium_priority:
                markdown += "### ⚠️ Medium Priority\n\n"
                for insight in medium_priority:
                    markdown += self._format_insight(insight)

        # Auto-generated insights based on data
        auto_insights = self._generate_auto_insights(test_results, performance_data, security_data)
        if auto_insights:
            markdown += "## 🤖 Auto-Generated Recommendations\n\n"
            for auto_insight in auto_insights:
                markdown += f"- **{auto_insight['title']}**: {auto_insight['description']}\n"

        return markdown

    def generate_comprehensive_report(
        self,
        test_results: dict[str, Any] | None = None,
        performance_data: dict[str, Any] | None = None,
        security_data: dict[str, Any] | None = None,
        include_artifacts: bool = True,
    ) -> dict[str, Any]:
        """Generate comprehensive report combining all data sources.

        Args:
            test_results: Test execution results.
            performance_data: Performance benchmark data.
            security_data: Security scan results.
            include_artifacts: Whether to create detailed artifacts.

        Returns:
            Dictionary containing report generation results.
        """
        results: dict[str, Any] = {
            "summary_added": False,
            "artifacts_created": [],
            "report_sections": {},
        }

        # Generate individual report sections
        build_dashboard = self.generate_build_dashboard(
            test_results, performance_data, security_data
        )
        results["report_sections"]["build_dashboard"] = build_dashboard

        if self._coverage_data:
            coverage_report = self.generate_coverage_report()
            results["report_sections"]["coverage_report"] = coverage_report

        if self._performance_trends:
            performance_dashboard = self.generate_performance_dashboard()
            results["report_sections"]["performance_dashboard"] = performance_dashboard

        # Combine into master summary
        master_summary = self._create_master_summary(results["report_sections"])

        # Add to GitHub step summary
        summary_success = self.github_reporter.add_to_summary(master_summary)
        results["summary_added"] = summary_success

        # Create detailed artifacts if requested
        if include_artifacts:
            # Create individual section artifacts
            for section_name, content in results["report_sections"].items():
                artifact_path = self._create_section_artifact(section_name, content)
                if artifact_path:
                    results["artifacts_created"].append(artifact_path)

            # Create comprehensive data artifact
            comprehensive_data = {
                "coverage_data": self._coverage_data.__dict__ if self._coverage_data else None,
                "performance_trends": [t.__dict__ for t in self._performance_trends],
                "build_insights": [i.__dict__ for i in self._build_insights],
                "test_results": test_results,
                "performance_data": performance_data,
                "security_data": security_data,
                "generated_at": datetime.now().isoformat(),
            }

            data_artifact = self.github_reporter.create_detailed_report_artifact(
                "comprehensive_report", comprehensive_data
            )
            if data_artifact:
                results["artifacts_created"].append(data_artifact)

        return results

    def _parse_coverage_data(self, data: dict[str, Any]) -> CoverageData:
        """Parse raw coverage data into structured format."""
        return CoverageData(
            overall_coverage=data.get("overall_coverage", 0.0),
            line_coverage=data.get("line_coverage", 0.0),
            branch_coverage=data.get("branch_coverage", 0.0),
            function_coverage=data.get("function_coverage", 0.0),
            modules=data.get("modules", []),
            trend_direction=data.get("trend_direction", "stable"),
            trend_percentage=data.get("trend_percentage"),
        )

    def _parse_performance_trend(self, data: dict[str, Any]) -> PerformanceTrend:
        """Parse raw performance trend data into structured format."""
        return PerformanceTrend(
            metric_name=data.get("metric_name", "Unknown"),
            current_value=data.get("current_value", 0.0),
            baseline_value=data.get("baseline_value"),
            historical_values=data.get("historical_values", []),
            trend_direction=data.get("trend_direction", "stable"),
            change_percentage=data.get("change_percentage"),
            threshold_status=data.get("threshold_status", "within"),
        )

    def _get_coverage_emoji(self, coverage: float) -> str:
        """Get emoji for coverage percentage."""
        if coverage >= 90:
            return "🟢"
        elif coverage >= 80:
            return "🟡"
        elif coverage >= 70:
            return "🟠"
        else:
            return "🔴"

    def _get_coverage_status(self, coverage: float) -> str:
        """Get status indicator for coverage percentage."""
        if coverage >= 90:
            return "✅ Excellent"
        elif coverage >= 80:
            return "🟡 Good"
        elif coverage >= 70:
            return "🟠 Fair"
        else:
            return "❌ Poor"

    def _get_trend_icon(self, direction: str) -> str:
        """Get icon for trend direction."""
        trend_icons = {
            "improvement": "📈",
            "regression": "📉",
            "stable": "➡️",
            "increasing": "📈",
            "decreasing": "📉",
        }
        return trend_icons.get(direction, "➡️")

    def _get_threshold_status_icon(self, status: str) -> str:
        """Get icon for threshold status."""
        status_icons = {"within": "✅", "warning": "⚠️", "critical": "🚨"}
        return status_icons.get(status, "❓")

    def _get_status_icon(self, status: str) -> str:
        """Get icon for overall status."""
        status_icons = {"success": "✅", "warning": "⚠️", "failure": "❌", "unknown": "❓"}
        return status_icons.get(status, "❓")

    def _format_metric_value(self, metric_name: str, value: float | None) -> str:
        """Format metric value based on metric type."""
        if value is None:
            return "N/A"

        # Format based on metric type
        if "time" in metric_name.lower() or "latency" in metric_name.lower():
            return f"{value:.4f}s"
        elif (
            "throughput" in metric_name.lower()
            or "ops" in metric_name.lower()
            or "per_sec" in metric_name.lower()
        ):
            return f"{value:.0f} ops/sec"
        elif "memory" in metric_name.lower():
            return f"{value:.1f} MB"
        elif "cpu" in metric_name.lower():
            return f"{value:.1f}%"
        else:
            return f"{value:.2f}"

    def _generate_coverage_insights(self, coverage: CoverageData) -> list[dict[str, str]]:
        """Generate actionable insights from coverage data."""
        insights = []

        if coverage.overall_coverage < 80:
            insights.append(
                {
                    "title": "Coverage Below Recommended Threshold",
                    "description": f"Current coverage is {coverage.overall_coverage:.1f}%. Consider adding tests to reach 80%+ coverage.",
                }
            )

        if coverage.branch_coverage < coverage.line_coverage - 10:
            insights.append(
                {
                    "title": "Branch Coverage Gap",
                    "description": f"Branch coverage ({coverage.branch_coverage:.1f}%) significantly lower than line coverage. Focus on testing conditional logic.",
                }
            )

        # Find modules with poor coverage
        poor_modules = [m for m in coverage.modules if m.get("coverage", 0) < 70]
        if poor_modules:
            module_names = [m.get("name", "Unknown") for m in poor_modules[:3]]
            insights.append(
                {
                    "title": "Low Coverage Modules",
                    "description": f"Modules with <70% coverage: {', '.join(module_names)}. Prioritize testing these areas.",
                }
            )

        return insights

    def _get_performance_recommendations(self, trend: PerformanceTrend) -> list[str]:
        """Get performance recommendations for a specific trend."""
        recommendations = []

        if "execution_time" in trend.metric_name.lower():
            recommendations.extend(
                [
                    "Profile the code to identify bottlenecks",
                    "Consider optimizing database queries or API calls",
                    "Review algorithm complexity and data structures",
                ]
            )
        elif "memory" in trend.metric_name.lower():
            recommendations.extend(
                [
                    "Check for memory leaks or excessive object creation",
                    "Optimize data structures and caching strategies",
                    "Review garbage collection settings",
                ]
            )
        elif "throughput" in trend.metric_name.lower():
            recommendations.extend(
                [
                    "Optimize concurrent processing and parallelization",
                    "Review resource contention and locking",
                    "Consider scaling strategies",
                ]
            )

        return recommendations

    def _calculate_overall_status(
        self,
        test_results: dict[str, Any] | None,
        performance_data: dict[str, Any] | None,
        security_data: dict[str, Any] | None,
    ) -> str:
        """Calculate overall build status from all data sources."""
        # Check for critical failures
        if test_results and test_results.get("failed", 0) > 0:
            return "failure"

        critical_perf = sum(1 for t in self._performance_trends if t.threshold_status == "critical")
        if critical_perf > 0:
            return "failure"

        if security_data and self._count_security_issues(security_data) > 0:
            return "warning"

        warning_perf = sum(1 for t in self._performance_trends if t.threshold_status == "warning")
        if warning_perf > 0:
            return "warning"

        return "success"

    def _count_security_issues(self, security_data: dict[str, Any]) -> int:
        """Count total security issues from security data."""
        total_issues = 0

        # Count bandit issues
        if "bandit_results" in security_data:
            bandit = security_data["bandit_results"]
            metrics = bandit.get("metrics", {})
            if "_totals" in metrics:
                totals = metrics["_totals"]
                total_issues += totals.get("SEVERITY.HIGH", 0)
                total_issues += totals.get("SEVERITY.MEDIUM", 0)

        # Count vulnerability issues
        if "pip_audit_results" in security_data:
            audit = security_data["pip_audit_results"]
            dependencies = audit.get("dependencies", [])
            vulnerable = [dep for dep in dependencies if dep.get("vulns")]
            total_issues += len(vulnerable)

        return total_issues

    def _format_insight(self, insight: BuildInsight) -> str:
        """Format a build insight for markdown display."""
        priority_icon = "🔥" if insight.priority == "high" else "⚠️"

        markdown = f"#### {priority_icon} {insight.title}\n\n"
        markdown += f"{insight.description}\n\n"

        if insight.action_items:
            markdown += "**Action Items:**\n"
            for item in insight.action_items:
                markdown += f"- {item}\n"
            markdown += "\n"

        return markdown

    def _generate_auto_insights(
        self,
        test_results: dict[str, Any] | None,
        performance_data: dict[str, Any] | None,
        security_data: dict[str, Any] | None,
    ) -> list[dict[str, str]]:
        """Generate automatic insights based on data analysis."""
        insights = []

        # Test insights
        if test_results:
            failed = test_results.get("failed", 0)
            if failed > 0:
                insights.append(
                    {
                        "title": "Test Failures Detected",
                        "description": f"{failed} tests are failing. Review failure logs and fix issues before deployment.",
                    }
                )

        # Performance insights
        critical_trends = [t for t in self._performance_trends if t.threshold_status == "critical"]
        if critical_trends:
            insights.append(
                {
                    "title": "Performance Regression Alert",
                    "description": f"{len(critical_trends)} performance metrics have exceeded critical thresholds.",
                }
            )

        # Coverage insights
        if self._coverage_data and self._coverage_data.overall_coverage < 80:
            insights.append(
                {
                    "title": "Coverage Improvement Needed",
                    "description": "Test coverage is below the recommended 80% threshold. Consider adding more comprehensive tests.",
                }
            )

        return insights

    def _create_master_summary(self, sections: dict[str, str]) -> str:
        """Create master summary combining all report sections."""
        summary = "# 📊 Comprehensive Build Report\n\n"

        # Add timestamp
        summary += f"*Generated at {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}*\n\n"

        # Add each section
        for _section_name, content in sections.items():
            summary += content + "\n\n---\n\n"

        return summary

    def _create_section_artifact(self, section_name: str, content: str) -> Path | None:
        """Create artifact for individual report section."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{section_name}_{timestamp}.md"

        return self.artifact_manager.create_artifact(filename, content, "text/markdown")
