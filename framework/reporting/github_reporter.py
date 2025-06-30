"""GitHub Actions integration for step summaries and artifact generation."""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any

from .artifact_manager import ArtifactManager
from .template_engine import TemplateEngine


class GitHubReporter:
    """Main class for GitHub Actions reporting integration."""

    def __init__(self, artifact_path: str | None = None):
        """Initialize GitHub reporter with environment detection.

        Args:
            artifact_path: Custom path for artifacts. Defaults to './artifacts'.
        """
        self.summary_path = os.environ.get("GITHUB_STEP_SUMMARY")
        self.artifact_path = Path(artifact_path or "./artifacts")
        self.artifact_path.mkdir(parents=True, exist_ok=True)

        # Initialize components
        self.template_engine = TemplateEngine()
        self.artifact_manager = ArtifactManager(self.artifact_path)

        # GitHub environment info
        self.github_env = self._collect_github_environment()

        # Track if we're in GitHub Actions
        self.is_github_actions = bool(os.environ.get("GITHUB_ACTIONS"))

    def _collect_github_environment(self) -> dict[str, str]:
        """Collect GitHub Actions environment variables."""
        github_vars = [
            "GITHUB_ACTIONS",
            "GITHUB_WORKFLOW",
            "GITHUB_RUN_ID",
            "GITHUB_RUN_NUMBER",
            "GITHUB_JOB",
            "GITHUB_ACTION",
            "GITHUB_SHA",
            "GITHUB_REF",
            "GITHUB_REF_NAME",
            "GITHUB_REPOSITORY",
            "GITHUB_ACTOR",
            "GITHUB_EVENT_NAME",
        ]

        env_info = {}
        for var in github_vars:
            value = os.environ.get(var)
            if value:
                env_info[var] = value

        return env_info

    def add_to_summary(self, markdown_content: str) -> bool:
        """Add content to GitHub step summary.

        Args:
            markdown_content: Markdown content to append.

        Returns:
            True if successful, False otherwise.
        """
        if not self.summary_path:
            print("Warning: GITHUB_STEP_SUMMARY environment variable not set")
            return False

        try:
            with open(self.summary_path, "a", encoding="utf-8") as f:
                f.write(markdown_content + "\n")
            return True
        except Exception as e:
            print(f"Error writing to step summary: {e}")
            return False

    def create_build_status_summary(
        self,
        build_status: str = "success",
        test_results: dict[str, Any] | None = None,
        performance_data: dict[str, Any] | None = None,
        security_data: dict[str, Any] | None = None,
    ) -> str:
        """Create a comprehensive build status summary.

        Args:
            build_status: Overall build status (success, failure, warning).
            test_results: Test execution results.
            performance_data: Performance benchmark data.
            security_data: Security scan results.

        Returns:
            Formatted markdown content.
        """
        context = {
            "build_status": build_status,
            "test_results": test_results or {},
            "performance_data": performance_data or {},
            "security_data": security_data or {},
            "github_env": self.github_env,
            "timestamp": datetime.now().isoformat(),
            "workflow_url": self._get_workflow_url(),
        }

        return self.template_engine.render_build_status(context)

    def create_performance_summary(
        self,
        performance_metrics: dict[str, Any],
        baseline_comparison: dict[str, Any] | None = None,
    ) -> str:
        """Create performance benchmark summary.

        Args:
            performance_metrics: Performance data from PerformanceCollector.
            baseline_comparison: Comparison with baseline if available.

        Returns:
            Formatted markdown content.
        """
        context = {
            "metrics": performance_metrics,
            "comparison": baseline_comparison,
            "github_env": self.github_env,
            "timestamp": datetime.now().isoformat(),
        }

        return self.template_engine.render_performance_summary(context)

    def create_security_summary(
        self,
        bandit_results: dict[str, Any] | None = None,
        pip_audit_results: dict[str, Any] | None = None,
    ) -> str:
        """Create security scan summary.

        Args:
            bandit_results: Bandit security scan results.
            pip_audit_results: pip-audit vulnerability scan results.

        Returns:
            Formatted markdown content.
        """
        context = {
            "bandit_results": bandit_results or {},
            "pip_audit_results": pip_audit_results or {},
            "github_env": self.github_env,
            "timestamp": datetime.now().isoformat(),
        }

        return self.template_engine.render_security_summary(context)

    def create_artifact(
        self, name: str, content: str | dict | list, content_type: str = "text/plain"
    ) -> Path | None:
        """Create an artifact file.

        Args:
            name: Artifact filename.
            content: Content to store.
            content_type: MIME type of content.

        Returns:
            Path to created artifact or None if failed.
        """
        return self.artifact_manager.create_artifact(name, content, content_type)

    def create_detailed_report_artifact(
        self, report_type: str, data: dict[str, Any]
    ) -> Path | None:
        """Create a detailed report artifact.

        Args:
            report_type: Type of report (performance, security, build).
            data: Report data.

        Returns:
            Path to created artifact.
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{report_type}_report_{timestamp}.json"

        enhanced_data = {
            "report_type": report_type,
            "generated_at": datetime.now().isoformat(),
            "github_context": self.github_env,
            "data": data,
        }

        return self.create_artifact(filename, enhanced_data, "application/json")

    def generate_performance_report(
        self,
        performance_metrics: dict[str, Any],
        baseline_comparison: dict[str, Any] | None = None,
        include_summary: bool = True,
        include_artifact: bool = True,
    ) -> dict[str, Any]:
        """Generate comprehensive performance report.

        Args:
            performance_metrics: Performance data.
            baseline_comparison: Baseline comparison data.
            include_summary: Whether to add to step summary.
            include_artifact: Whether to create artifact.

        Returns:
            Report generation results.
        """
        results: dict[str, bool | Path | None] = {"summary_added": False, "artifact_created": None}

        # Generate step summary
        if include_summary:
            summary_content = self.create_performance_summary(
                performance_metrics, baseline_comparison
            )
            results["summary_added"] = self.add_to_summary(summary_content)

        # Create detailed artifact
        if include_artifact:
            artifact_data = {
                "performance_metrics": performance_metrics,
                "baseline_comparison": baseline_comparison,
            }
            results["artifact_created"] = self.create_detailed_report_artifact(
                "performance", artifact_data
            )

        return results

    def generate_security_report(
        self,
        bandit_file: str | None = None,
        pip_audit_file: str | None = None,
        include_summary: bool = True,
        include_artifact: bool = True,
    ) -> dict[str, Any]:
        """Generate comprehensive security report.

        Args:
            bandit_file: Path to bandit report JSON.
            pip_audit_file: Path to pip-audit report JSON.
            include_summary: Whether to add to step summary.
            include_artifact: Whether to create artifact.

        Returns:
            Report generation results.
        """
        results: dict[str, bool | Path | None] = {"summary_added": False, "artifact_created": None}

        # Load security data
        bandit_data = self._load_json_file(bandit_file) if bandit_file else None
        pip_audit_data = self._load_json_file(pip_audit_file) if pip_audit_file else None

        # Generate step summary
        if include_summary:
            summary_content = self.create_security_summary(bandit_data, pip_audit_data)
            results["summary_added"] = self.add_to_summary(summary_content)

        # Create detailed artifact
        if include_artifact:
            artifact_data = {"bandit_results": bandit_data, "pip_audit_results": pip_audit_data}
            results["artifact_created"] = self.create_detailed_report_artifact(
                "security", artifact_data
            )

        return results

    def generate_build_report(
        self,
        build_status: str = "success",
        test_results_file: str | None = None,
        performance_file: str | None = None,
        security_files: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        """Generate comprehensive build status report.

        Args:
            build_status: Overall build status.
            test_results_file: Path to test results JSON.
            performance_file: Path to performance results JSON.
            security_files: Dict of security report file paths.

        Returns:
            Report generation results.
        """
        results: dict[str, bool | Path | None] = {"summary_added": False, "artifact_created": None}

        # Load data files
        test_data = self._load_json_file(test_results_file) if test_results_file else None
        performance_data = self._load_json_file(performance_file) if performance_file else None

        security_data = {}
        if security_files:
            for key, file_path in security_files.items():
                security_data[key] = self._load_json_file(file_path)

        # Generate step summary
        summary_content = self.create_build_status_summary(
            build_status, test_data, performance_data, security_data
        )
        results["summary_added"] = self.add_to_summary(summary_content)

        # Create comprehensive artifact
        artifact_data = {
            "build_status": build_status,
            "test_results": test_data,
            "performance_data": performance_data,
            "security_data": security_data,
        }
        results["artifact_created"] = self.create_detailed_report_artifact("build", artifact_data)

        return results

    def _load_json_file(self, file_path: str) -> dict[str, Any] | None:
        """Load JSON data from file.

        Args:
            file_path: Path to JSON file.

        Returns:
            Loaded data or None if failed.
        """
        try:
            with open(file_path, encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"Warning: Failed to load {file_path}: {e}")
            return None

    def _get_workflow_url(self) -> str | None:
        """Get GitHub workflow run URL.

        Returns:
            Workflow URL or None if not available.
        """
        repo = self.github_env.get("GITHUB_REPOSITORY")
        run_id = self.github_env.get("GITHUB_RUN_ID")

        if repo and run_id:
            return f"https://github.com/{repo}/actions/runs/{run_id}"

        return None

    def get_environment_info(self) -> dict[str, Any]:
        """Get comprehensive environment information.

        Returns:
            Environment information including GitHub context.
        """
        return {
            "is_github_actions": self.is_github_actions,
            "github_env": self.github_env,
            "summary_path": self.summary_path,
            "artifact_path": str(self.artifact_path),
            "workflow_url": self._get_workflow_url(),
        }
