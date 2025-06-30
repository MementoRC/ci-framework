"""Template engine for generating formatted reports and summaries."""

from datetime import datetime
from typing import Any


class TemplateEngine:
    """Generates formatted content for different types of reports."""

    def __init__(self):
        """Initialize template engine."""
        pass

    def render_build_status(self, context: dict[str, Any]) -> str:
        """Render build status summary.

        Args:
            context: Build context with status, test results, etc.

        Returns:
            Formatted markdown content.
        """
        build_status = context.get("build_status", "unknown")
        test_results = context.get("test_results", {})
        performance_data = context.get("performance_data", {})
        security_data = context.get("security_data", {})
        github_env = context.get("github_env", {})
        timestamp = context.get("timestamp", "")
        workflow_url = context.get("workflow_url")

        # Build status emoji and color
        status_info = self._get_status_info(build_status)

        markdown = f"""# {status_info["emoji"]} Build Status Report

## Overview
- **Status**: {status_info["badge"]}
- **Workflow**: {github_env.get("GITHUB_WORKFLOW", "Unknown")}
- **Run**: #{github_env.get("GITHUB_RUN_NUMBER", "N/A")}
- **Commit**: `{github_env.get("GITHUB_SHA", "N/A")[:8]}`
- **Generated**: {self._format_timestamp(timestamp)}
"""

        if workflow_url:
            markdown += f"- **Details**: [View Run]({workflow_url})\n"

        # Test Results Section
        if test_results:
            markdown += "\n## 🧪 Test Results\n"
            markdown += self._render_test_results(test_results)

        # Performance Section
        if performance_data:
            markdown += "\n## ⚡ Performance Metrics\n"
            markdown += self._render_performance_summary(performance_data)

        # Security Section
        if security_data:
            markdown += "\n## 🔒 Security Scan\n"
            markdown += self._render_security_summary(security_data)

        markdown += f"\n---\n*Report generated at {self._format_timestamp(timestamp)}*"

        return markdown

    def render_performance_summary(self, context: dict[str, Any]) -> str:
        """Render performance benchmark summary.

        Args:
            context: Performance context with metrics and comparison.

        Returns:
            Formatted markdown content.
        """
        metrics = context.get("metrics", {})
        comparison = context.get("comparison")
        timestamp = context.get("timestamp", "")

        markdown = "# ⚡ Performance Benchmark Report\n\n"

        # Check for regression alerts first
        if metrics.get("regressions_detected"):
            markdown += "## 🚨 Performance Regressions Detected\n\n"

            regression_details = metrics.get("regression_details", {})
            for test_name, data in regression_details.items():
                if data.get("status") == "regression":
                    severity = data.get("severity", "unknown")
                    ratio = data.get("ratio", 1.0)
                    markdown += f"- **{test_name}**: {severity} regression ({ratio:.1f}x slower than baseline)\n"
                elif data.get("status") == "warning":
                    severity = data.get("severity", "unknown")
                    ratio = data.get("ratio", 1.0)
                    markdown += f"- **{test_name}**: {severity} performance warning ({ratio:.1f}x baseline)\n"

            markdown += "\n"

        # Basic metrics
        if "results" in metrics:
            markdown += "## Benchmark Results\n\n"

            for result in metrics["results"]:
                name = result.get("name", "Unknown")
                exec_time = result.get("execution_time", 0)
                throughput = result.get("throughput")
                memory = result.get("memory_usage")

                markdown += f"### {name}\n"
                markdown += f"- **Execution Time**: {exec_time:.4f}s\n"

                if throughput:
                    markdown += f"- **Throughput**: {throughput:.0f} ops/sec\n"

                if memory:
                    markdown += f"- **Memory Usage**: {memory:.1f} MB\n"

                markdown += "\n"

        # Summary statistics
        if "summary_stats" in metrics:
            stats = metrics["summary_stats"]
            markdown += "## Summary Statistics\n\n"
            markdown += "| Metric | Value |\n|--------|-------|\n"

            for key, value in stats.items():
                formatted_key = key.replace("_", " ").title()
                if isinstance(value, float):
                    markdown += f"| {formatted_key} | {value:.4f} |\n"
                else:
                    markdown += f"| {formatted_key} | {value} |\n"

            markdown += "\n"

        # Baseline comparison
        if comparison and "comparisons" in comparison:
            markdown += "## 📊 Baseline Comparison\n\n"

            for comp in comparison["comparisons"]:
                name = comp.get("name", "Unknown")
                markdown += f"### {name}\n\n"

                # Execution time comparison
                if "execution_time" in comp:
                    et = comp["execution_time"]
                    change_icon = self._get_performance_icon(et["change_direction"])
                    markdown += f"- **Execution Time**: {change_icon} {et['change_percent']:+.1f}% "
                    markdown += f"({et['current']:.4f}s vs {et['baseline']:.4f}s)\n"

                # Memory comparison
                if "memory_usage" in comp:
                    mem = comp["memory_usage"]
                    change_icon = self._get_performance_icon(mem["change_direction"])
                    markdown += f"- **Memory Usage**: {change_icon} {mem['change_percent']:+.1f}% "
                    markdown += f"({mem['current']:.1f}MB vs {mem['baseline']:.1f}MB)\n"

                # Throughput comparison
                if "throughput" in comp:
                    thr = comp["throughput"]
                    change_icon = self._get_performance_icon(thr["change_direction"])
                    markdown += f"- **Throughput**: {change_icon} {thr['change_percent']:+.1f}% "
                    markdown += f"({thr['current']:.0f} vs {thr['baseline']:.0f} ops/sec)\n"

                markdown += "\n"

        markdown += f"\n---\n*Report generated at {self._format_timestamp(timestamp)}*"

        return markdown

    def render_security_summary(self, context: dict[str, Any]) -> str:
        """Render security scan summary.

        Args:
            context: Security context with scan results.

        Returns:
            Formatted markdown content.
        """
        bandit_results = context.get("bandit_results", {})
        pip_audit_results = context.get("pip_audit_results", {})
        timestamp = context.get("timestamp", "")

        markdown = "# 🔒 Security Scan Report\n\n"

        # Bandit static analysis
        if bandit_results:
            markdown += "## Static Code Analysis (Bandit)\n\n"

            metrics = bandit_results.get("metrics", {})
            if metrics and "_totals" in metrics:
                totals = metrics["_totals"]

                # Summary table
                markdown += "| Severity | Count |\n|----------|-------|\n"
                high = totals.get("SEVERITY.HIGH", 0)
                medium = totals.get("SEVERITY.MEDIUM", 0)
                low = totals.get("SEVERITY.LOW", 0)

                markdown += f"| 🔴 High | {high} |\n"
                markdown += f"| 🟡 Medium | {medium} |\n"
                markdown += f"| 🟢 Low | {low} |\n\n"

                # Overall status
                if high > 0:
                    markdown += "⚠️ **High severity issues found!**\n\n"
                elif medium > 0:
                    markdown += "⚠️ **Medium severity issues found.**\n\n"
                else:
                    markdown += "✅ **No high/medium severity issues found.**\n\n"

            # Individual issues (limit to first 5)
            results = bandit_results.get("results", [])
            if results:
                markdown += "### Issues Found\n\n"
                for i, issue in enumerate(results[:5]):
                    severity = issue.get("issue_severity", "UNKNOWN")
                    confidence = issue.get("issue_confidence", "UNKNOWN")
                    text = issue.get("issue_text", "No description")
                    filename = issue.get("filename", "Unknown file")
                    line_number = issue.get("line_number", 0)

                    severity_icon = self._get_severity_icon(severity)
                    markdown += f"{i + 1}. {severity_icon} **{severity}** - {text}\n"
                    markdown += f"   - File: `{filename}:{line_number}`\n"
                    markdown += f"   - Confidence: {confidence}\n\n"

                if len(results) > 5:
                    markdown += f"*... and {len(results) - 5} more issues*\n\n"

        # Dependency vulnerabilities
        if pip_audit_results:
            markdown += "## Dependency Vulnerabilities (pip-audit)\n\n"

            dependencies = pip_audit_results.get("dependencies", [])
            vulnerable_deps = [dep for dep in dependencies if dep.get("vulns")]

            if vulnerable_deps:
                markdown += f"⚠️ **{len(vulnerable_deps)} vulnerable dependencies found!**\n\n"

                for dep in vulnerable_deps[:5]:  # Limit to first 5
                    name = dep.get("name", "Unknown")
                    version = dep.get("version", "Unknown")
                    vulns = dep.get("vulns", [])

                    markdown += f"### {name} v{version}\n\n"

                    for vuln in vulns:
                        vuln_id = vuln.get("id", "Unknown")
                        description = vuln.get("description", "No description")
                        fix_versions = vuln.get("fix_versions", [])

                        markdown += f"- **{vuln_id}**: {description[:100]}{'...' if len(description) > 100 else ''}\n"
                        if fix_versions:
                            markdown += f"  - Fix available in: {', '.join(fix_versions)}\n"
                        markdown += "\n"

                if len(vulnerable_deps) > 5:
                    markdown += (
                        f"*... and {len(vulnerable_deps) - 5} more vulnerable dependencies*\n\n"
                    )
            else:
                total_deps = len(dependencies)
                markdown += f"✅ **No vulnerabilities found in {total_deps} dependencies.**\n\n"

        markdown += f"\n---\n*Report generated at {self._format_timestamp(timestamp)}*"

        return markdown

    def _render_test_results(self, test_results: dict[str, Any]) -> str:
        """Render test results section."""
        if not test_results:
            return "*No test results available.*\n"

        # Extract common test metrics
        total = test_results.get("total", 0)
        passed = test_results.get("passed", 0)
        failed = test_results.get("failed", 0)
        skipped = test_results.get("skipped", 0)
        duration = test_results.get("duration", 0)

        markdown = f"- **Total Tests**: {total}\n"
        markdown += f"- **Passed**: ✅ {passed}\n"

        if failed > 0:
            markdown += f"- **Failed**: ❌ {failed}\n"

        if skipped > 0:
            markdown += f"- **Skipped**: ⏭️ {skipped}\n"

        if duration > 0:
            markdown += f"- **Duration**: {duration:.2f}s\n"

        # Pass rate
        if total > 0:
            pass_rate = (passed / total) * 100
            markdown += f"- **Pass Rate**: {pass_rate:.1f}%\n"

        return markdown

    def _render_performance_summary(self, performance_data: dict[str, Any]) -> str:
        """Render performance data summary."""
        if not performance_data:
            return "*No performance data available.*\n"

        # Extract key metrics
        results = performance_data.get("results", [])
        if not results:
            return "*No benchmark results available.*\n"

        markdown = ""
        for result in results[:3]:  # Show first 3 results
            name = result.get("name", "Unknown")
            exec_time = result.get("execution_time", 0)
            throughput = result.get("throughput")

            markdown += f"- **{name}**: {exec_time:.4f}s"
            if throughput:
                markdown += f" ({throughput:.0f} ops/sec)"
            markdown += "\n"

        if len(results) > 3:
            markdown += f"- *... and {len(results) - 3} more benchmarks*\n"

        return markdown

    def _render_security_summary(self, security_data: dict[str, Any]) -> str:
        """Render security data summary."""
        if not security_data:
            return "*No security scan data available.*\n"

        markdown = ""

        # Bandit summary
        if "bandit_results" in security_data:
            bandit = security_data["bandit_results"]
            metrics = bandit.get("metrics", {})
            if metrics and "_totals" in metrics:
                totals = metrics["_totals"]
                high = totals.get("SEVERITY.HIGH", 0)
                medium = totals.get("SEVERITY.MEDIUM", 0)
                low = totals.get("SEVERITY.LOW", 0)

                if high > 0:
                    markdown += f"- **Static Analysis**: ⚠️ {high} high, {medium} medium, {low} low severity issues\n"
                elif medium > 0:
                    markdown += (
                        f"- **Static Analysis**: ⚠️ {medium} medium, {low} low severity issues\n"
                    )
                else:
                    markdown += "- **Static Analysis**: ✅ No high/medium severity issues\n"

        # Vulnerability summary
        if "pip_audit_results" in security_data:
            audit = security_data["pip_audit_results"]
            dependencies = audit.get("dependencies", [])
            vulnerable = [dep for dep in dependencies if dep.get("vulns")]

            if vulnerable:
                markdown += f"- **Dependencies**: ⚠️ {len(vulnerable)} vulnerable packages\n"
            else:
                markdown += f"- **Dependencies**: ✅ {len(dependencies)} packages scanned, no vulnerabilities\n"

        return markdown

    def _get_status_info(self, status: str) -> dict[str, str]:
        """Get status display information."""
        status_map = {
            "success": {
                "emoji": "✅",
                "badge": "![Success](https://img.shields.io/badge/build-success-brightgreen)",
            },
            "failure": {
                "emoji": "❌",
                "badge": "![Failure](https://img.shields.io/badge/build-failure-red)",
            },
            "warning": {
                "emoji": "⚠️",
                "badge": "![Warning](https://img.shields.io/badge/build-warning-orange)",
            },
        }

        return status_map.get(
            status,
            {
                "emoji": "❓",
                "badge": f"![{status.title()}](https://img.shields.io/badge/build-{status}-lightgrey)",
            },
        )

    def _get_performance_icon(self, direction: str) -> str:
        """Get performance change icon."""
        if direction == "improvement":
            return "🟢"
        elif direction == "regression":
            return "🔴"
        else:
            return "⚪"

    def _get_severity_icon(self, severity: str) -> str:
        """Get security severity icon."""
        severity_map = {"HIGH": "🔴", "MEDIUM": "🟡", "LOW": "🟢"}
        return severity_map.get(severity, "⚪")

    def _format_timestamp(self, timestamp: str) -> str:
        """Format timestamp for display."""
        if not timestamp:
            return "Unknown"

        try:
            dt = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
            return dt.strftime("%Y-%m-%d %H:%M:%S UTC")
        except Exception:
            return timestamp
