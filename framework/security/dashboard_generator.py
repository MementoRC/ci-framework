"""Security dashboard generator for comprehensive vulnerability and dependency reporting."""

from datetime import datetime
from typing import Any

from ..reporting.github_reporter import GitHubReporter
from .sbom_generator import SBOMGenerator


class SecurityDashboardGenerator:
    """Generates comprehensive security dashboards combining SBOM and vulnerability data."""

    def __init__(self, sbom_generator: SBOMGenerator, github_reporter: GitHubReporter):
        """Initialize the security dashboard generator.

        Args:
            sbom_generator: SBOMGenerator instance for SBOM and vulnerability data.
            github_reporter: GitHubReporter instance for step summary integration.
        """
        self.sbom_generator = sbom_generator
        self.github_reporter = github_reporter

    def generate_security_dashboard(self) -> dict[str, Any]:
        """Generate comprehensive security dashboard.

        Returns:
            Dictionary containing dashboard data and generation results.
        """
        # Generate SBOM and vulnerability data
        sbom_data = self.sbom_generator.generate_sbom()
        vulnerability_data = self.sbom_generator.generate_vulnerability_report()

        # Calculate security metrics
        security_score = self._calculate_security_score(vulnerability_data)
        dependency_health = self._analyze_dependency_health(sbom_data)
        recommendations = self._generate_recommendations(vulnerability_data)

        # Create dashboard content
        dashboard_data = {
            "security_score": security_score,
            "vulnerability_summary": self._summarize_vulnerabilities(vulnerability_data),
            "dependency_health": dependency_health,
            "recommendations": recommendations,
            "generated_at": datetime.now().isoformat(),
        }

        # Format dashboard for GitHub step summary
        dashboard_content = self._format_dashboard(dashboard_data)

        # Add to GitHub step summary
        summary_added = self.github_reporter.add_to_summary(dashboard_content)

        # Create detailed artifact
        artifact_path = self.github_reporter.create_detailed_report_artifact(
            "security_dashboard", dashboard_data
        )

        return {
            "dashboard_data": dashboard_data,
            "summary_added": summary_added,
            "artifact_created": artifact_path,
            "dashboard_content": dashboard_content,
        }

    def _calculate_security_score(self, vulnerability_data: dict[str, Any]) -> dict[str, Any]:
        """Calculate overall security score based on vulnerabilities.

        Args:
            vulnerability_data: Vulnerability report data.

        Returns:
            Security score information including score, trend, and breakdown.
        """
        severity_breakdown = vulnerability_data["summary"]["severity_breakdown"]
        total_vulnerabilities = vulnerability_data["summary"]["total_vulnerabilities"]

        # Calculate weighted score (100 = perfect, 0 = critical issues)
        # Weight vulnerabilities by severity: critical=40, high=20, medium=10, low=5
        severity_weights = {"critical": 40, "high": 20, "medium": 10, "low": 5}

        penalty_score = 0
        for severity, count in severity_breakdown.items():
            if severity in severity_weights:
                penalty_score += count * severity_weights[severity]

        # Calculate base score out of 100
        base_score = max(0, 100 - penalty_score)

        # Additional factors
        vulnerable_deps = vulnerability_data["summary"]["vulnerable_dependencies"]
        total_deps = vulnerability_data["summary"]["total_dependencies"]

        # Adjust for proportion of vulnerable dependencies
        if total_deps > 0:
            vuln_ratio = vulnerable_deps / total_deps
            vulnerability_factor = max(0.5, 1 - vuln_ratio)  # Don't go below 50% of base score
            final_score = int(base_score * vulnerability_factor)
        else:
            final_score = base_score

        # Determine score category
        if final_score >= 90:
            score_category = "excellent"
            score_trend = "🟢"
        elif final_score >= 70:
            score_category = "good"
            score_trend = "🟡"
        elif final_score >= 50:
            score_category = "fair"
            score_trend = "🟠"
        else:
            score_category = "poor"
            score_trend = "🔴"

        return {
            "score": final_score,
            "category": score_category,
            "trend": score_trend,
            "total_vulnerabilities": total_vulnerabilities,
            "severity_breakdown": severity_breakdown,
            "vulnerable_dependencies": vulnerable_deps,
            "total_dependencies": total_deps,
        }

    def _analyze_dependency_health(self, sbom_data: dict[str, Any]) -> dict[str, Any]:
        """Analyze dependency health based on SBOM data.

        Args:
            sbom_data: SBOM data structure.

        Returns:
            Dependency health analysis.
        """
        components = sbom_data.get("components", [])
        total_components = len(components)

        # Analyze license compliance
        licensed_components = len([c for c in components if c.get("licenses")])
        license_compliance = (
            (licensed_components / total_components * 100) if total_components > 0 else 100
        )

        # Analyze vulnerability exposure
        vulnerable_components = 0
        if "vulnerabilities" in sbom_data:
            affected_refs = set()
            for vuln in sbom_data["vulnerabilities"]:
                for affect in vuln.get("affects", []):
                    affected_refs.add(affect.get("ref"))
            vulnerable_components = len(affected_refs)

        vulnerability_exposure = (
            (vulnerable_components / total_components * 100) if total_components > 0 else 0
        )

        # Calculate overall health score
        health_score = int((license_compliance * 0.3) + ((100 - vulnerability_exposure) * 0.7))

        return {
            "health_score": health_score,
            "total_components": total_components,
            "licensed_components": licensed_components,
            "license_compliance_percent": round(license_compliance, 1),
            "vulnerable_components": vulnerable_components,
            "vulnerability_exposure_percent": round(vulnerability_exposure, 1),
            "health_category": self._get_health_category(health_score),
        }

    def _get_health_category(self, score: int) -> str:
        """Get health category based on score.

        Args:
            score: Health score (0-100).

        Returns:
            Health category string.
        """
        if score >= 90:
            return "excellent"
        elif score >= 70:
            return "good"
        elif score >= 50:
            return "fair"
        else:
            return "poor"

    def _generate_recommendations(self, vulnerability_data: dict[str, Any]) -> list[str]:
        """Generate actionable security recommendations.

        Args:
            vulnerability_data: Vulnerability report data.

        Returns:
            List of actionable recommendations.
        """
        recommendations = []
        severity_breakdown = vulnerability_data["summary"]["severity_breakdown"]

        # Critical vulnerabilities
        if severity_breakdown.get("critical", 0) > 0:
            recommendations.append(
                f"🚨 **URGENT**: Address {severity_breakdown['critical']} critical vulnerabilities immediately"
            )

        # High severity vulnerabilities
        if severity_breakdown.get("high", 0) > 0:
            recommendations.append(
                f"⚠️ **HIGH PRIORITY**: Resolve {severity_breakdown['high']} high-severity vulnerabilities"
            )

        # Medium severity vulnerabilities
        if severity_breakdown.get("medium", 0) > 0:
            recommendations.append(
                f"⚡ **MEDIUM PRIORITY**: Plan fixes for {severity_breakdown['medium']} medium-severity vulnerabilities"
            )

        # Specific package recommendations from vulnerability data
        existing_recommendations = vulnerability_data.get("recommendations", [])
        for rec in existing_recommendations[:5]:  # Limit to top 5 specific recommendations
            if rec not in recommendations:
                recommendations.append(f"📦 {rec}")

        # General security recommendations
        if vulnerability_data["summary"]["total_vulnerabilities"] > 0:
            recommendations.append(
                "🔄 **Enable automated security updates** for dependencies where possible"
            )
            recommendations.append("📊 **Set up regular security scans** in your CI/CD pipeline")

        if len(recommendations) == 0:
            recommendations.append(
                "✅ **Excellent security posture!** Continue monitoring for new vulnerabilities"
            )

        return recommendations

    def _summarize_vulnerabilities(
        self, vulnerability_data: dict[str, Any]
    ) -> list[dict[str, Any]]:
        """Create vulnerability summary for dashboard table.

        Args:
            vulnerability_data: Vulnerability report data.

        Returns:
            List of vulnerability summary entries for table display.
        """
        severity_breakdown = vulnerability_data["summary"]["severity_breakdown"]

        summary = []
        for severity in ["critical", "high", "medium", "low"]:
            count = severity_breakdown.get(severity, 0)

            # Count how many have fixes available
            fixed_available = 0
            for package in vulnerability_data.get("vulnerable_packages", []):
                for vuln in package.get("vulnerabilities", []):
                    if vuln.get("severity", "").lower() == severity and vuln.get("fix_versions"):
                        fixed_available += 1

            summary.append(
                {
                    "severity": severity.capitalize(),
                    "count": count,
                    "fixed_available": fixed_available,
                    "emoji": self._get_severity_emoji(severity),
                }
            )

        return summary

    def _get_severity_emoji(self, severity: str) -> str:
        """Get emoji for severity level.

        Args:
            severity: Severity level string.

        Returns:
            Appropriate emoji for severity.
        """
        severity_emojis = {
            "critical": "🔴",
            "high": "🟠",
            "medium": "🟡",
            "low": "🟢",
        }
        return severity_emojis.get(severity.lower(), "⚪")

    def _format_dashboard(self, dashboard_data: dict[str, Any]) -> str:
        """Format dashboard data as markdown for GitHub step summary.

        Args:
            dashboard_data: Dashboard data to format.

        Returns:
            Formatted markdown dashboard content.
        """
        security_score = dashboard_data["security_score"]
        dependency_health = dashboard_data["dependency_health"]
        vulnerability_summary = dashboard_data["vulnerability_summary"]
        recommendations = dashboard_data["recommendations"]

        # Build markdown dashboard
        dashboard = f"""## 🛡️ Security Dashboard

### Security Score: {security_score["score"]}/100 {security_score["trend"]} ({security_score["category"]})

**Overview**: {security_score["total_vulnerabilities"]} vulnerabilities found across {security_score["vulnerable_dependencies"]}/{security_score["total_dependencies"]} dependencies

### 📊 Vulnerability Summary

| Severity | Count | Fixed Available | Status |
|----------|-------|----------------|--------|"""

        for vuln in vulnerability_summary:
            dashboard += f"\n| {vuln['emoji']} {vuln['severity']} | {vuln['count']} | {vuln['fixed_available']} | {'✅' if vuln['count'] == 0 else '❌'} |"

        dashboard += f"""

### 🏥 Dependency Health: {dependency_health["health_score"]}/100 ({dependency_health["health_category"]})

- **Total Components**: {dependency_health["total_components"]}
- **License Compliance**: {dependency_health["license_compliance_percent"]}% ({dependency_health["licensed_components"]}/{dependency_health["total_components"]})
- **Vulnerability Exposure**: {dependency_health["vulnerability_exposure_percent"]}% ({dependency_health["vulnerable_components"]} vulnerable)

### 🎯 Top Security Recommendations

"""

        for i, rec in enumerate(recommendations[:8], 1):  # Limit to top 8 recommendations
            dashboard += f"{i}. {rec}\n"

        dashboard += f"""
### 📈 Security Metrics

- **Security Score**: {security_score["score"]}/100
- **Health Score**: {dependency_health["health_score"]}/100
- **Total Vulnerabilities**: {security_score["total_vulnerabilities"]}
- **Vulnerable Dependencies**: {security_score["vulnerable_dependencies"]}/{security_score["total_dependencies"]}

---
*Dashboard generated at {dashboard_data["generated_at"]} by Security Dashboard Generator*
"""

        return dashboard

    def generate_security_trend_data(
        self, historical_data: list[dict[str, Any]] | None = None
    ) -> dict[str, Any]:
        """Generate security trend analysis over time.

        Args:
            historical_data: List of historical security dashboard data.

        Returns:
            Security trend analysis.
        """
        if not historical_data:
            historical_data = []

        # Get current data
        current_data = self.generate_security_dashboard()["dashboard_data"]

        trend_data = {
            "current_score": current_data["security_score"]["score"],
            "current_vulnerabilities": current_data["security_score"]["total_vulnerabilities"],
            "historical_scores": [],
            "historical_vulnerabilities": [],
            "trend_analysis": {},
        }

        # Process historical data
        for data_point in historical_data[-10:]:  # Last 10 data points
            if "security_score" in data_point:
                trend_data["historical_scores"].append(
                    {
                        "score": data_point["security_score"]["score"],
                        "timestamp": data_point.get("generated_at", ""),
                    }
                )
                trend_data["historical_vulnerabilities"].append(
                    {
                        "count": data_point["security_score"]["total_vulnerabilities"],
                        "timestamp": data_point.get("generated_at", ""),
                    }
                )

        # Calculate trends
        if len(trend_data["historical_scores"]) >= 2:
            recent_scores = [point["score"] for point in trend_data["historical_scores"][-3:]]
            score_trend = (
                "improving"
                if recent_scores[-1] > recent_scores[0]
                else "declining"
                if recent_scores[-1] < recent_scores[0]
                else "stable"
            )

            recent_vulns = [
                point["count"] for point in trend_data["historical_vulnerabilities"][-3:]
            ]
            vuln_trend = (
                "decreasing"
                if recent_vulns[-1] < recent_vulns[0]
                else "increasing"
                if recent_vulns[-1] > recent_vulns[0]
                else "stable"
            )

            trend_data["trend_analysis"] = {
                "score_trend": score_trend,
                "vulnerability_trend": vuln_trend,
                "trend_summary": f"Security score is {score_trend}, vulnerabilities are {vuln_trend}",
            }

        return trend_data
