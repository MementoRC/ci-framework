"""CI pipeline health monitoring and system diagnostics."""

import logging
import shutil
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import psutil
import yaml

from ..performance.collector import PerformanceCollector
from ..security.analyzer import DependencyAnalyzer

logger = logging.getLogger(__name__)


class CIHealthMonitor:
    """Monitors CI pipeline health and performs system diagnostics."""

    def __init__(
        self, config_path: str | Path | None = None, project_path: str | Path | None = None
    ):
        """Initialize the CI health monitor.

        Args:
            config_path: Path to maintenance configuration file.
            project_path: Path to the project root directory.
        """
        self.project_path = Path(project_path or ".")

        # Load configuration
        default_config_path = (
            self.project_path / "framework" / "maintenance" / "maintenance_config.yaml"
        )
        self.config_path = Path(config_path or default_config_path)
        self.config = self._load_config()

        # Initialize monitoring components
        self.performance_collector = PerformanceCollector(
            storage_path=self.project_path / "performance_data"
        )
        self.dependency_analyzer = DependencyAnalyzer(self.project_path)

        # Health metrics storage
        self.metrics: dict[str, Any] = {}
        self.last_health_check: datetime | None = None

    def _load_config(self) -> dict[str, Any]:
        """Load monitoring configuration from YAML file."""
        if not self.config_path.exists():
            # Return default configuration if file doesn't exist
            return {
                "data_retention": {
                    "performance_data": 90,  # days
                    "security_scans": 30,  # days
                    "reports": 60,  # days
                },
                "health_thresholds": {
                    "max_execution_time": 3600,  # seconds
                    "max_storage_usage": 5,  # GB
                    "min_disk_space": 10,  # GB
                },
                "update_schedule": {"security_databases": "daily"},
                "monitoring": {
                    "check_interval": 300,  # seconds
                    "alert_threshold": 0.8,  # percentage
                },
            }

        try:
            with open(self.config_path) as f:
                return yaml.safe_load(f)
        except Exception as e:
            logger.warning(f"Failed to load config from {self.config_path}: {e}")
            return self._load_config()  # Return defaults

    def collect_health_metrics(self) -> dict[str, Any]:
        """Collect comprehensive health metrics about the CI system."""
        logger.info("Collecting CI health metrics")

        self.metrics = {
            "timestamp": datetime.now().isoformat(),
            "system_info": self._collect_system_metrics(),
            "storage_usage": self._collect_storage_metrics(),
            "component_health": self._check_component_health(),
            "performance_status": self._check_performance_status(),
            "security_status": self._check_security_status(),
        }

        self.last_health_check = datetime.now()
        return self.metrics

    def _collect_system_metrics(self) -> dict[str, Any]:
        """Collect system-level metrics."""
        try:
            memory = psutil.virtual_memory()
            cpu_percent = psutil.cpu_percent(interval=1)

            return {
                "cpu_usage_percent": cpu_percent,
                "memory_usage_percent": memory.percent,
                "memory_available_gb": round(memory.available / (1024**3), 2),
                "memory_total_gb": round(memory.total / (1024**3), 2),
                "load_average": psutil.getloadavg() if hasattr(psutil, "getloadavg") else None,
                "uptime_seconds": time.time() - psutil.boot_time(),
            }
        except Exception as e:
            logger.error(f"Failed to collect system metrics: {e}")
            return {"error": str(e)}

    def _collect_storage_metrics(self) -> dict[str, Any]:
        """Collect storage usage metrics for key directories."""
        storage_metrics: dict[str, Any] = {}

        directories_to_check = [
            ("project_root", self.project_path),
            ("performance_data", self.project_path / "performance_data"),
            ("artifacts", self.project_path / "artifacts"),
            ("reports", self.project_path / "reports"),
        ]

        for name, path in directories_to_check:
            try:
                if path.exists():
                    usage = shutil.disk_usage(path)
                    storage_metrics[name] = {
                        "total_gb": round(usage.total / (1024**3), 2),
                        "used_gb": round(usage.used / (1024**3), 2),
                        "free_gb": round(usage.free / (1024**3), 2),
                        "usage_percent": round((usage.used / usage.total) * 100, 2),
                    }
                else:
                    storage_metrics[name] = {"status": "directory_not_found"}
            except Exception as e:
                storage_metrics[name] = {"error": str(e)}

        return storage_metrics

    def _check_component_health(self) -> dict[str, Any]:
        """Check health of individual CI components."""
        component_health: dict[str, Any] = {}

        # Performance component health
        try:
            recent_history = self.performance_collector.get_recent_history(limit=5)
            component_health["performance"] = {
                "status": "healthy" if recent_history else "no_data",
                "recent_runs": len(recent_history),
                "last_run": recent_history[0].timestamp.isoformat() if recent_history else None,
            }
        except Exception as e:
            component_health["performance"] = {"status": "error", "error": str(e)}

        # Security component health
        try:
            package_managers = self.dependency_analyzer.detect_package_managers()
            component_health["security"] = {
                "status": "healthy" if package_managers else "configuration_issue",
                "detected_package_managers": list(package_managers),
            }
        except Exception as e:
            component_health["security"] = {"status": "error", "error": str(e)}

        # Reports directory health
        reports_dir = self.project_path / "artifacts" / "reports"
        if reports_dir.exists():
            report_files = list(reports_dir.glob("*.json"))
            component_health["reporting"] = {
                "status": "healthy",
                "report_count": len(report_files),
                "latest_report": max(report_files, key=lambda x: x.stat().st_mtime).name
                if report_files
                else None,
            }
        else:
            component_health["reporting"] = {"status": "no_reports_directory"}

        return component_health

    def _check_performance_status(self) -> dict[str, Any]:
        """Check performance monitoring status and trends."""
        try:
            recent_metrics = self.performance_collector.get_recent_history(limit=10)

            if not recent_metrics:
                return {"status": "no_data", "message": "No recent performance data found"}

            # Calculate average execution times
            execution_times = [
                result.execution_time
                for metrics in recent_metrics
                for result in metrics.results
                if result.execution_time
            ]

            avg_execution_time = (
                sum(execution_times) / len(execution_times) if execution_times else 0
            )
            max_execution_time = self.config["health_thresholds"]["max_execution_time"]

            status = "healthy"
            if avg_execution_time > max_execution_time * 0.8:
                status = "warning"
            elif avg_execution_time > max_execution_time:
                status = "critical"

            return {
                "status": status,
                "avg_execution_time": avg_execution_time,
                "max_threshold": max_execution_time,
                "recent_runs": len(recent_metrics),
                "trend": self._calculate_performance_trend(recent_metrics),
            }
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def _check_security_status(self) -> dict[str, Any]:
        """Check security scanning status and vulnerability counts."""
        try:
            dependencies = self.dependency_analyzer.scan_dependencies()

            vulnerable_deps = [dep for dep in dependencies if dep.has_vulnerabilities]
            total_vulnerabilities = sum(len(dep.vulnerabilities) for dep in vulnerable_deps)

            # Count by severity
            severity_counts = {"low": 0, "medium": 0, "high": 0, "critical": 0}
            for dep in vulnerable_deps:
                for vuln in dep.vulnerabilities:
                    severity = vuln.severity.lower()
                    if severity in severity_counts:
                        severity_counts[severity] += 1

            status = "healthy"
            if severity_counts["critical"] > 0:
                status = "critical"
            elif severity_counts["high"] > 5 or total_vulnerabilities > 20:
                status = "warning"

            return {
                "status": status,
                "total_dependencies": len(dependencies),
                "vulnerable_dependencies": len(vulnerable_deps),
                "total_vulnerabilities": total_vulnerabilities,
                "severity_breakdown": severity_counts,
            }
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def _calculate_performance_trend(self, metrics_list: list) -> str:
        """Calculate performance trend over recent runs."""
        if len(metrics_list) < 3:
            return "insufficient_data"

        # Get execution times for the first benchmark in each run
        execution_times = []
        for metrics in metrics_list:
            if metrics.results:
                execution_times.append(metrics.results[0].execution_time)

        if len(execution_times) < 3:
            return "insufficient_data"

        # Simple trend calculation: compare first half vs second half
        mid_point = len(execution_times) // 2
        first_half_avg = sum(execution_times[:mid_point]) / mid_point
        second_half_avg = sum(execution_times[mid_point:]) / (len(execution_times) - mid_point)

        if second_half_avg > first_half_avg * 1.1:
            return "degrading"
        elif second_half_avg < first_half_avg * 0.9:
            return "improving"
        else:
            return "stable"

    def run_diagnostics(self) -> dict[str, Any]:
        """Run comprehensive diagnostics on all CI components."""
        logger.info("Running CI diagnostics")

        diagnostics: dict[str, Any] = {
            "timestamp": datetime.now().isoformat(),
            "performance": self._diagnose_performance_component(),
            "security": self._diagnose_security_component(),
            "reporting": self._diagnose_reporting_component(),
            "storage": self._diagnose_storage_health(),
            "overall_status": "healthy",  # Will be updated based on component status
        }

        # Determine overall status
        component_statuses = [
            diagnostics["performance"]["status"],
            diagnostics["security"]["status"],
            diagnostics["reporting"]["status"],
            diagnostics["storage"]["status"],
        ]

        if "critical" in component_statuses:
            diagnostics["overall_status"] = "critical"
        elif "warning" in component_statuses:
            diagnostics["overall_status"] = "warning"
        elif "error" in component_statuses:
            diagnostics["overall_status"] = "error"

        return diagnostics

    def _diagnose_performance_component(self) -> dict[str, Any]:
        """Diagnose performance monitoring component."""
        try:
            performance_dir = self.project_path / "performance_data"
            if not performance_dir.exists():
                return {
                    "status": "warning",
                    "message": "Performance data directory not found",
                    "recommendation": "Run performance benchmarks to initialize data collection",
                }

            baseline_files = list((performance_dir / "baselines").glob("*.json"))
            history_files = list((performance_dir / "history").glob("*.json"))

            status = "healthy"
            issues = []

            if not baseline_files:
                issues.append("No baseline performance data found")
                status = "warning"

            if len(history_files) < 3:
                issues.append("Insufficient historical performance data")
                status = "warning"

            return {
                "status": status,
                "baseline_count": len(baseline_files),
                "history_count": len(history_files),
                "issues": issues,
                "data_directory": str(performance_dir),
            }
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def _diagnose_security_component(self) -> dict[str, Any]:
        """Diagnose security scanning component."""
        try:
            # Check if security scanning tools are available
            package_managers = self.dependency_analyzer.detect_package_managers()

            issues = []
            status = "healthy"

            if not package_managers:
                issues.append("No package managers detected")
                status = "warning"

            # Check for recent security scans
            reports_dir = self.project_path / "artifacts" / "reports"
            if reports_dir.exists():
                security_reports = list(reports_dir.glob("security_*.json"))
                if not security_reports:
                    issues.append("No recent security scan reports found")
                    status = "warning"
            else:
                issues.append("Reports directory not found")
                status = "warning"

            return {
                "status": status,
                "package_managers": package_managers,
                "issues": issues,
                "recommendation": "Run security scans regularly to maintain up-to-date vulnerability data",
            }
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def _diagnose_reporting_component(self) -> dict[str, Any]:
        """Diagnose reporting system component."""
        try:
            artifacts_dir = self.project_path / "artifacts"
            reports_dir = artifacts_dir / "reports"

            if not artifacts_dir.exists():
                return {
                    "status": "warning",
                    "message": "Artifacts directory not found",
                    "recommendation": "Run CI pipeline to generate artifacts",
                }

            if not reports_dir.exists():
                return {
                    "status": "warning",
                    "message": "Reports directory not found",
                    "recommendation": "Run reporting tools to generate reports",
                }

            # Check for recent reports
            report_files = list(reports_dir.glob("*.json"))
            recent_reports = [
                f
                for f in report_files
                if (datetime.now() - datetime.fromtimestamp(f.stat().st_mtime)) < timedelta(days=7)
            ]

            status = "healthy" if recent_reports else "warning"

            return {
                "status": status,
                "total_reports": len(report_files),
                "recent_reports": len(recent_reports),
                "artifacts_directory": str(artifacts_dir),
            }
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def _diagnose_storage_health(self) -> dict[str, Any]:
        """Diagnose storage health and usage."""
        try:
            storage_metrics = self._collect_storage_metrics()

            issues = []
            status = "healthy"

            min_free_space = self.config["health_thresholds"].get("min_disk_space", 10)

            for location, metrics in storage_metrics.items():
                if isinstance(metrics, dict) and "usage_percent" in metrics:
                    if metrics["usage_percent"] > 90:
                        issues.append(
                            f"High storage usage in {location}: {metrics['usage_percent']}%"
                        )
                        status = "critical"
                    elif metrics["free_gb"] < min_free_space:
                        issues.append(f"Low free space in {location}: {metrics['free_gb']}GB")
                        status = "warning"

            return {
                "status": status,
                "storage_details": storage_metrics,
                "issues": issues,
                "recommendation": "Consider cleaning up old data if storage usage is high",
            }
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def get_health_summary(self) -> dict[str, Any]:
        """Get a summary of current system health."""
        if not self.metrics or not self.last_health_check:
            self.collect_health_metrics()

        # Check if metrics are stale (older than 1 hour)
        if self.last_health_check and (datetime.now() - self.last_health_check) > timedelta(
            hours=1
        ):
            self.collect_health_metrics()

        return {
            "overall_status": self._determine_overall_status(),
            "last_check": self.last_health_check.isoformat() if self.last_health_check else None,
            "component_summary": self._get_component_summary(),
            "recommendations": self._generate_health_recommendations(),
        }

    def _determine_overall_status(self) -> str:
        """Determine overall system health status."""
        if not self.metrics:
            return "unknown"

        component_statuses = []

        # Check system thresholds
        system_info = self.metrics.get("system_info", {})
        if system_info.get("cpu_usage_percent", 0) > 90:
            component_statuses.append("critical")
        elif system_info.get("memory_usage_percent", 0) > 85:
            component_statuses.append("warning")

        # Check component health
        component_health = self.metrics.get("component_health", {})
        for _, health in component_health.items():
            if isinstance(health, dict):
                status = health.get("status", "unknown")
                if status == "error":
                    component_statuses.append("critical")
                elif status in ["warning", "configuration_issue"]:
                    component_statuses.append("warning")

        # Check performance and security status
        perf_status = self.metrics.get("performance_status", {}).get("status", "unknown")
        security_status = self.metrics.get("security_status", {}).get("status", "unknown")

        component_statuses.extend([perf_status, security_status])

        if "critical" in component_statuses:
            return "critical"
        elif "warning" in component_statuses:
            return "warning"
        elif "error" in component_statuses:
            return "degraded"
        else:
            return "healthy"

    def _get_component_summary(self) -> dict[str, str]:
        """Get summary of component statuses."""
        if not self.metrics:
            return {}

        summary = {}

        # Component health
        component_health = self.metrics.get("component_health", {})
        for component, health in component_health.items():
            if isinstance(health, dict):
                summary[component] = health.get("status", "unknown")

        # Performance and security
        summary["performance_monitoring"] = self.metrics.get("performance_status", {}).get(
            "status", "unknown"
        )
        summary["security_scanning"] = self.metrics.get("security_status", {}).get(
            "status", "unknown"
        )

        return summary

    def _generate_health_recommendations(self) -> list[str]:
        """Generate health recommendations based on current metrics."""
        recommendations = []

        if not self.metrics:
            recommendations.append("Run health metrics collection to get system status")
            return recommendations

        # System resource recommendations
        system_info = self.metrics.get("system_info", {})
        if system_info.get("cpu_usage_percent", 0) > 80:
            recommendations.append(
                "High CPU usage detected - consider reducing concurrent processes"
            )

        if system_info.get("memory_usage_percent", 0) > 80:
            recommendations.append(
                "High memory usage detected - consider increasing available memory"
            )

        # Component-specific recommendations
        perf_status = self.metrics.get("performance_status", {})
        if perf_status.get("status") == "no_data":
            recommendations.append("Run performance benchmarks to establish baseline metrics")
        elif perf_status.get("trend") == "degrading":
            recommendations.append("Performance degradation detected - investigate recent changes")

        security_status = self.metrics.get("security_status", {})
        if security_status.get("status") == "critical":
            critical_vulns = security_status.get("severity_breakdown", {}).get("critical", 0)
            if critical_vulns > 0:
                recommendations.append(
                    f"Critical security vulnerabilities found ({critical_vulns}) - update dependencies immediately"
                )

        # Storage recommendations
        storage_usage = self.metrics.get("storage_usage", {})
        for location, metrics in storage_usage.items():
            if isinstance(metrics, dict) and metrics.get("usage_percent", 0) > 85:
                recommendations.append(f"High storage usage in {location} - consider data cleanup")

        return recommendations
