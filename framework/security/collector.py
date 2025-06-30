"""Security data collection and storage infrastructure."""

import json
import os
import platform
from datetime import datetime
from pathlib import Path
from typing import Any

from .analyzer import DependencyAnalyzer
from .models import SecurityMetrics


class SecurityCollector:
    """Collects, processes, and stores security metrics and vulnerability scan results."""

    def __init__(self, storage_path: str | Path = None):
        """Initialize the security collector.

        Args:
            storage_path: Directory path for storing security data.
                         Defaults to 'security_data' in current directory.
        """
        self.storage_path = Path(storage_path or "security_data")
        self.storage_path.mkdir(exist_ok=True)

        # Initialize baseline storage
        self.baseline_path = self.storage_path / "baselines"
        self.baseline_path.mkdir(exist_ok=True)

        # Initialize history storage
        self.history_path = self.storage_path / "history"
        self.history_path.mkdir(exist_ok=True)

    def collect_environment_info(self) -> dict[str, str]:
        """Collect current environment information."""
        env_info = {
            "platform": platform.platform(),
            "python_version": platform.python_version(),
            "hostname": platform.node(),
        }

        # Add CI environment variables if available
        ci_vars = [
            "GITHUB_ACTIONS",
            "GITHUB_WORKFLOW",
            "GITHUB_RUN_ID",
            "GITHUB_REPOSITORY",
            "CI",
            "BUILD_NUMBER",
        ]

        for var in ci_vars:
            value = os.environ.get(var)
            if value:
                env_info[f"ci_{var.lower()}"] = value

        return env_info

    def scan_project_security(
        self,
        project_path: str | Path,
        build_id: str | None = None,
        package_managers: list[str] | None = None,
    ) -> SecurityMetrics:
        """Perform complete security scan of a project.

        Args:
            project_path: Path to the project to scan.
            build_id: Unique identifier for this build/scan.
            package_managers: List of package managers to scan. Auto-detected if None.

        Returns:
            Complete security metrics for the project.
        """
        project_path = Path(project_path)

        if build_id is None:
            build_id = f"scan_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        # Initialize analyzer
        analyzer = DependencyAnalyzer(project_path)

        # Detect package managers if not specified
        if package_managers is None:
            package_managers = analyzer.detect_package_managers()

        # Record scan start time
        scan_start = datetime.now()

        # Scan dependencies
        dependencies = analyzer.scan_dependencies(package_managers)

        # Record scan duration
        scan_duration = (datetime.now() - scan_start).total_seconds()

        # Create security metrics
        metrics = SecurityMetrics(
            build_id=build_id,
            timestamp=scan_start,
            dependencies=dependencies,
            scan_config={
                "project_path": str(project_path),
                "package_managers": package_managers,
                "scan_duration": scan_duration,
            },
            environment=self.collect_environment_info(),
            scan_duration=scan_duration,
        )

        return metrics

    def save_metrics(self, metrics: SecurityMetrics, filename: str | None = None) -> Path:
        """Save security metrics to storage.

        Args:
            metrics: Security metrics to save.
            filename: Custom filename. Auto-generated if None.

        Returns:
            Path to the saved file.
        """
        if filename is None:
            timestamp = metrics.timestamp.strftime("%Y%m%d_%H%M%S")
            filename = f"security_metrics_{timestamp}_{metrics.build_id}.json"

        file_path = self.history_path / filename

        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(metrics.to_dict(), f, indent=2, default=str)

        return file_path

    def load_metrics(self, file_path: str | Path) -> SecurityMetrics:
        """Load security metrics from file.

        Args:
            file_path: Path to the metrics file.

        Returns:
            Loaded security metrics.
        """
        with open(file_path, encoding="utf-8") as f:
            data = json.load(f)

        return SecurityMetrics.from_dict(data)

    def save_baseline(self, metrics: SecurityMetrics, baseline_name: str = "default") -> Path:
        """Save security metrics as a baseline for comparison.

        Args:
            metrics: Security metrics to save as baseline.
            baseline_name: Name for the baseline.

        Returns:
            Path to the saved baseline file.
        """
        filename = f"baseline_{baseline_name}.json"
        file_path = self.baseline_path / filename

        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(metrics.to_dict(), f, indent=2, default=str)

        return file_path

    def load_baseline(self, baseline_name: str = "default") -> SecurityMetrics | None:
        """Load baseline security metrics for comparison.

        Args:
            baseline_name: Name of the baseline to load.

        Returns:
            Baseline security metrics or None if not found.
        """
        filename = f"baseline_{baseline_name}.json"
        file_path = self.baseline_path / filename

        if not file_path.exists():
            return None

        return self.load_metrics(file_path)

    def compare_with_baseline(
        self, current_metrics: SecurityMetrics, baseline_name: str = "default"
    ) -> dict[str, Any] | None:
        """Compare current metrics with baseline.

        Args:
            current_metrics: Current security metrics.
            baseline_name: Name of the baseline to compare against.

        Returns:
            Comparison results or None if baseline not found.
        """
        baseline = self.load_baseline(baseline_name)
        if baseline is None:
            return None

        current_stats = current_metrics.calculate_summary_stats()
        baseline_stats = baseline.calculate_summary_stats()

        comparison: dict[str, Any] = {
            "baseline_info": {
                "build_id": baseline.build_id,
                "timestamp": baseline.timestamp.isoformat(),
            },
            "current_info": {
                "build_id": current_metrics.build_id,
                "timestamp": current_metrics.timestamp.isoformat(),
            },
            "changes": {},
            "new_vulnerabilities": [],
            "resolved_vulnerabilities": [],
        }

        # Compare summary statistics
        for key in current_stats:
            if key in baseline_stats:
                current_val = current_stats[key]
                baseline_val = baseline_stats[key]

                if isinstance(current_val, int | float) and isinstance(baseline_val, int | float):
                    change = current_val - baseline_val
                    comparison["changes"][key] = {
                        "current": current_val,
                        "baseline": baseline_val,
                        "change": change,
                        "change_percent": (
                            round((change / baseline_val) * 100, 2) if baseline_val != 0 else 0
                        ),
                    }

        # Compare vulnerabilities
        current_vulns = set()
        baseline_vulns = set()

        for dep in current_metrics.dependencies:
            for vuln in dep.vulnerabilities:
                current_vulns.add((dep.name, vuln.id))

        for dep in baseline.dependencies:
            for vuln in dep.vulnerabilities:
                baseline_vulns.add((dep.name, vuln.id))

        # Find new and resolved vulnerabilities
        new_vulns = current_vulns - baseline_vulns
        resolved_vulns = baseline_vulns - current_vulns

        comparison["new_vulnerabilities"] = list(new_vulns)
        comparison["resolved_vulnerabilities"] = list(resolved_vulns)

        return comparison

    def generate_security_report(
        self,
        project_path: str | Path,
        output_path: str | Path | None = None,
        include_baseline_comparison: bool = True,
        baseline_name: str = "default",
    ) -> dict[str, Any]:
        """Generate comprehensive security report for a project.

        Args:
            project_path: Path to the project to scan.
            output_path: Path to save the report. Auto-generated if None.
            include_baseline_comparison: Whether to include baseline comparison.
            baseline_name: Name of baseline to compare against.

        Returns:
            Complete security report data.
        """
        # Perform security scan
        metrics = self.scan_project_security(project_path)

        # Save current metrics
        metrics_file = self.save_metrics(metrics)

        # Prepare report data
        report = {
            "report_type": "security_scan",
            "generated_at": datetime.now().isoformat(),
            "project_path": str(project_path),
            "scan_results": metrics.to_dict(),
            "metrics_file": str(metrics_file),
        }

        # Add baseline comparison if requested
        if include_baseline_comparison:
            comparison = self.compare_with_baseline(metrics, baseline_name)
            report["baseline_comparison"] = comparison

        # Save report if output path specified
        if output_path:
            output_path = Path(output_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)

            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(report, f, indent=2, default=str)

            report["report_file"] = str(output_path)

        return report

    def list_saved_metrics(self) -> list[dict[str, Any]]:
        """List all saved security metrics files.

        Returns:
            List of metric file information.
        """
        metrics_files = []

        for file_path in self.history_path.glob("security_metrics_*.json"):
            try:
                with open(file_path, encoding="utf-8") as f:
                    data = json.load(f)

                metrics_files.append(
                    {
                        "file_path": str(file_path),
                        "build_id": data.get("build_id"),
                        "timestamp": data.get("timestamp"),
                        "total_dependencies": data.get("summary_stats", {}).get(
                            "total_dependencies", 0
                        ),
                        "vulnerable_dependencies": data.get("summary_stats", {}).get(
                            "vulnerable_dependencies", 0
                        ),
                    }
                )
            except Exception as e:
                print(f"Warning: Could not read metrics file {file_path}: {e}")

        # Sort by timestamp (newest first)
        metrics_files.sort(key=lambda x: x.get("timestamp", ""), reverse=True)

        return metrics_files
