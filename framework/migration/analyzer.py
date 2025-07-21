"""
Project analysis engine for CI migration detection and planning.
"""

import re
from datetime import datetime
from pathlib import Path
from typing import Any

import tomllib
import yaml

from .models import (
    AnalysisResult,
    GitHubWorkflowConfig,
    PackageManager,
    PackageManagerConfig,
    ProjectComplexity,
    ProjectStructure,
    ProjectType,
    QualityToolConfig,
)


class ProjectAnalyzer:
    """Analyzes existing Python projects for CI framework migration."""

    def __init__(self, project_path: Path) -> None:
        """Initialize analyzer for specified project path."""
        self.project_path = Path(project_path).resolve()
        if not self.project_path.exists():
            raise FileNotFoundError(f"Project path not found: {project_path}")

        if not self.project_path.is_dir():
            raise ValueError(f"Project path must be a directory: {project_path}")

    def analyze(self) -> AnalysisResult:
        """Perform comprehensive project analysis."""
        print(f"🔍 Analyzing project: {self.project_path}")

        # Core analysis components
        project_structure = self._analyze_project_structure()
        package_manager = self._analyze_package_manager()
        quality_tools = self._analyze_quality_tools()
        github_workflows = self._analyze_github_workflows()

        # Classification and recommendations
        project_type = self._classify_project_type(project_structure, package_manager)
        complexity = self._assess_complexity(package_manager, quality_tools, github_workflows)
        python_versions = self._detect_python_versions(package_manager)
        platforms = self._detect_platforms(package_manager, github_workflows)

        # Generate recommendations and identify issues
        recommendations = self._generate_migration_recommendations(
            project_type, complexity, package_manager, quality_tools
        )
        issues = self._identify_potential_issues(
            package_manager, quality_tools, github_workflows
        )

        return AnalysisResult(
            project_path=self.project_path,
            project_type=project_type,
            complexity=complexity,
            package_manager=package_manager,
            quality_tools=quality_tools,
            github_workflows=github_workflows,
            project_structure=project_structure,
            python_versions=python_versions,
            platforms=platforms,
            migration_recommendations=recommendations,
            potential_issues=issues,
            analysis_timestamp=datetime.now().isoformat()
        )

    def _analyze_project_structure(self) -> ProjectStructure:
        """Analyze project directory structure and key files."""
        structure = ProjectStructure(root_path=self.project_path)

        # Find source directories
        for potential_src in ["src", "lib", self.project_path.name]:
            src_path = self.project_path / potential_src
            if src_path.exists() and src_path.is_dir():
                structure.source_dirs.append(src_path)

        # Find test directories
        for test_pattern in ["test", "tests", "testing"]:
            test_paths = list(self.project_path.rglob(f"{test_pattern}*/"))
            structure.test_dirs.extend([p for p in test_paths if p.is_dir()])

        # Find documentation directories
        for doc_pattern in ["doc", "docs", "documentation"]:
            doc_paths = list(self.project_path.rglob(f"{doc_pattern}*/"))
            structure.doc_dirs.extend([p for p in doc_paths if p.is_dir()])

        # Find configuration files
        config_patterns = [
            "pyproject.toml", "setup.py", "setup.cfg", "requirements*.txt",
            "poetry.lock", "pixi.lock", "Pipfile", ".pre-commit-config.yaml",
            "pytest.ini", "mypy.ini", ".flake8", "ruff.toml", "bandit.yaml"
        ]

        for pattern in config_patterns:
            config_files = list(self.project_path.rglob(pattern))
            structure.config_files.extend(config_files)

        # Find GitHub workflow files
        workflows_dir = self.project_path / ".github" / "workflows"
        if workflows_dir.exists():
            structure.workflow_files.extend(
                list(workflows_dir.glob("*.yml")) + list(workflows_dir.glob("*.yaml"))
            )

        # Check for key files
        structure.has_dockerfile = (self.project_path / "Dockerfile").exists()
        structure.has_pyproject_toml = (self.project_path / "pyproject.toml").exists()
        structure.has_setup_py = (self.project_path / "setup.py").exists()

        return structure

    def _analyze_package_manager(self) -> PackageManagerConfig:
        """Detect and analyze package manager configuration."""
        pyproject_path = self.project_path / "pyproject.toml"

        # Check for pixi first (priority)
        if pyproject_path.exists():
            try:
                with open(pyproject_path, "rb") as f:
                    pyproject_data = tomllib.load(f)

                if "tool" in pyproject_data and "pixi" in pyproject_data["tool"]:
                    return self._analyze_pixi_config(pyproject_data)
                elif "tool" in pyproject_data and "poetry" in pyproject_data["tool"]:
                    return self._analyze_poetry_config(pyproject_data)
                elif "tool" in pyproject_data and "hatch" in pyproject_data["tool"]:
                    return self._analyze_hatch_config(pyproject_data)
            except Exception as e:
                print(f"⚠️ Error reading pyproject.toml: {e}")

        # Check for poetry.lock
        if (self.project_path / "poetry.lock").exists():
            return PackageManagerConfig(manager=PackageManager.POETRY)

        # Check for conda environment
        if (self.project_path / "environment.yml").exists() or (self.project_path / "conda.yml").exists():
            return PackageManagerConfig(manager=PackageManager.CONDA)

        # Default to pip if requirements.txt exists
        if any(self.project_path.glob("requirements*.txt")):
            return self._analyze_pip_config()

        return PackageManagerConfig(manager=PackageManager.UNKNOWN)

    def _analyze_pixi_config(self, pyproject_data: dict[str, Any]) -> PackageManagerConfig:
        """Analyze pixi configuration from pyproject.toml."""
        pixi_config = pyproject_data["tool"]["pixi"]

        config = PackageManagerConfig(
            manager=PackageManager.PIXI,
            config_file=self.project_path / "pyproject.toml"
        )

        # Extract environments
        if "environments" in pixi_config:
            config.environments = list(pixi_config["environments"].keys())

        # Extract features
        if "feature" in pixi_config:
            config.features = list(pixi_config["feature"].keys())

        # Extract dependencies
        config.dependencies = pixi_config.get("dependencies", {})

        # Extract tasks
        if "tasks" in pixi_config:
            config.tasks = pixi_config["tasks"]

        return config

    def _analyze_poetry_config(self, pyproject_data: dict[str, Any]) -> PackageManagerConfig:
        """Analyze poetry configuration from pyproject.toml."""
        poetry_config = pyproject_data["tool"]["poetry"]

        return PackageManagerConfig(
            manager=PackageManager.POETRY,
            config_file=self.project_path / "pyproject.toml",
            dependencies=poetry_config.get("dependencies", {}),
            dev_dependencies=poetry_config.get("group", {}).get("dev", {}).get("dependencies", {})
        )

    def _analyze_hatch_config(self, pyproject_data: dict[str, Any]) -> PackageManagerConfig:
        """Analyze hatch configuration from pyproject.toml."""
        hatch_config = pyproject_data["tool"]["hatch"]

        config = PackageManagerConfig(
            manager=PackageManager.HATCH,
            config_file=self.project_path / "pyproject.toml"
        )

        # Extract environments
        if "envs" in hatch_config:
            config.environments = list(hatch_config["envs"].keys())

        return config

    def _analyze_pip_config(self) -> PackageManagerConfig:
        """Analyze pip-based configuration."""
        requirements_files = list(self.project_path.glob("requirements*.txt"))

        config = PackageManagerConfig(manager=PackageManager.PIP)

        if requirements_files:
            config.config_file = requirements_files[0]  # Use first requirements file

        return config

    def _analyze_quality_tools(self) -> QualityToolConfig:
        """Analyze quality tooling configuration."""
        config = QualityToolConfig()

        # Check pyproject.toml for tool configurations
        pyproject_path = self.project_path / "pyproject.toml"
        if pyproject_path.exists():
            try:
                with open(pyproject_path, "rb") as f:
                    pyproject_data = tomllib.load(f)

                if "tool" in pyproject_data:
                    tools = pyproject_data["tool"]
                    config.pytest_config = tools.get("pytest", {}).get("ini_options", {})
                    config.ruff_config = tools.get("ruff", {})
                    config.mypy_config = tools.get("mypy", {})
                    config.bandit_config = tools.get("bandit", {})
                    config.coverage_config = tools.get("coverage", {})
            except Exception as e:
                print(f"⚠️ Error reading tool configurations: {e}")

        # Check for pre-commit configuration
        precommit_path = self.project_path / ".pre-commit-config.yaml"
        if precommit_path.exists():
            try:
                with open(precommit_path) as f:
                    precommit_data = yaml.safe_load(f)
                config.precommit_hooks = precommit_data.get("repos", [])
            except Exception as e:
                print(f"⚠️ Error reading pre-commit config: {e}")

        return config

    def _analyze_github_workflows(self) -> GitHubWorkflowConfig:
        """Analyze GitHub Actions workflow configurations."""
        config = GitHubWorkflowConfig()

        workflows_dir = self.project_path / ".github" / "workflows"
        if not workflows_dir.exists():
            return config

        workflow_files = list(workflows_dir.glob("*.yml")) + list(workflows_dir.glob("*.yaml"))

        for workflow_file in workflow_files:
            try:
                with open(workflow_file) as f:
                    workflow_data = yaml.safe_load(f)

                workflow_name = workflow_file.stem
                config.workflows[workflow_name] = workflow_data

                # Extract secrets and permissions
                if "jobs" in workflow_data:
                    for job_name, job_config in workflow_data["jobs"].items():
                        # Extract secrets
                        if "with" in job_config:
                            for key, value in job_config["with"].items():
                                if isinstance(value, str) and "${{ secrets." in value:
                                    secret_match = re.search(r"secrets\.(\w+)", value)
                                    if secret_match:
                                        config.secrets.add(secret_match.group(1))

                        # Extract matrix strategies
                        if "strategy" in job_config and "matrix" in job_config["strategy"]:
                            config.matrix_strategies.append(job_config["strategy"]["matrix"])

            except Exception as e:
                print(f"⚠️ Error reading workflow {workflow_file}: {e}")

        return config

    def _classify_project_type(
        self,
        structure: ProjectStructure,
        package_manager: PackageManagerConfig
    ) -> ProjectType:
        """Classify the type of Python project."""

        # Check for MCP server indicators
        mcp_indicators = [
            "mcp", "server", "claude", "anthropic"
        ]
        if any(indicator in str(self.project_path).lower() for indicator in mcp_indicators):
            return ProjectType.MCP_SERVER

        # Check for CLI tool indicators
        cli_indicators = [
            "cli", "command", "tool", "bin"
        ]
        if any(indicator in str(self.project_path).lower() for indicator in cli_indicators):
            return ProjectType.CLI_TOOL

        # Check for framework indicators
        framework_indicators = [
            "framework", "platform", "core", "base"
        ]
        if any(indicator in str(self.project_path).lower() for indicator in framework_indicators):
            return ProjectType.FRAMEWORK

        # Check for monorepo patterns
        if len(structure.source_dirs) > 3:
            return ProjectType.MONOREPO

        # Check for application vs library
        if structure.has_setup_py or (
            package_manager.manager != PackageManager.UNKNOWN and
            len(structure.source_dirs) == 1
        ):
            return ProjectType.LIBRARY

        return ProjectType.APPLICATION

    def _assess_complexity(
        self,
        package_manager: PackageManagerConfig,
        quality_tools: QualityToolConfig,
        github_workflows: GitHubWorkflowConfig
    ) -> ProjectComplexity:
        """Assess project complexity for migration planning."""
        complexity_score = 0

        # Package manager complexity
        if package_manager.manager == PackageManager.PIXI:
            complexity_score += len(package_manager.environments) * 2
            complexity_score += len(package_manager.features) * 1
            complexity_score += len(package_manager.tasks) // 10

        # Quality tooling complexity
        tool_count = sum([
            bool(quality_tools.pytest_config),
            bool(quality_tools.ruff_config),
            bool(quality_tools.mypy_config),
            bool(quality_tools.bandit_config),
            bool(quality_tools.coverage_config),
            bool(quality_tools.precommit_hooks)
        ])
        complexity_score += tool_count * 3

        # GitHub workflow complexity
        complexity_score += len(github_workflows.workflows) * 5
        complexity_score += len(github_workflows.matrix_strategies) * 3
        complexity_score += len(github_workflows.secrets) * 2

        # Classify based on score
        if complexity_score < 10:
            return ProjectComplexity.SIMPLE
        elif complexity_score < 25:
            return ProjectComplexity.MODERATE
        elif complexity_score < 50:
            return ProjectComplexity.COMPLEX
        else:
            return ProjectComplexity.ENTERPRISE

    def _detect_python_versions(self, package_manager: PackageManagerConfig) -> list[str]:
        """Detect supported Python versions."""
        versions = []

        # Look for version constraints in package manager config
        if package_manager.dependencies.get("python"):
            python_constraint = package_manager.dependencies["python"]
            if isinstance(python_constraint, str):
                # Extract version numbers from constraint
                version_matches = re.findall(r"3\.\d+", python_constraint)
                versions.extend(version_matches)

        # Default supported versions if none found
        if not versions:
            versions = ["3.10", "3.11", "3.12"]

        return sorted(list(set(versions)))

    def _detect_platforms(
        self,
        package_manager: PackageManagerConfig,
        github_workflows: GitHubWorkflowConfig
    ) -> list[str]:
        """Detect supported platforms."""
        platforms = []

        # Check GitHub workflow matrix strategies
        for matrix in github_workflows.matrix_strategies:
            if "os" in matrix:
                platforms.extend(matrix["os"])

        # Default platforms if none found
        if not platforms:
            platforms = ["ubuntu-latest", "macos-latest", "windows-latest"]

        return sorted(list(set(platforms)))

    def _generate_migration_recommendations(
        self,
        project_type: ProjectType,
        complexity: ProjectComplexity,
        package_manager: PackageManagerConfig,
        quality_tools: QualityToolConfig
    ) -> list[str]:
        """Generate migration recommendations based on analysis."""
        recommendations = []

        # Package manager recommendations
        if package_manager.manager != PackageManager.PIXI:
            recommendations.append(f"Migrate from {package_manager.manager.value} to pixi for better environment management")

        # Quality tooling recommendations
        if not quality_tools.ruff_config:
            recommendations.append("Add ruff configuration for modern Python linting and formatting")

        if not quality_tools.pytest_config:
            recommendations.append("Configure pytest with comprehensive test settings")

        if not quality_tools.precommit_hooks:
            recommendations.append("Add pre-commit hooks for automated quality checks")

        # Complexity-based recommendations
        if complexity == ProjectComplexity.SIMPLE:
            recommendations.append("Start with essential tier quality gates")
        elif complexity == ProjectComplexity.MODERATE:
            recommendations.append("Implement extended tier with security scanning")
        else:
            recommendations.append("Deploy full tier with performance monitoring and container scanning")

        return recommendations

    def _identify_potential_issues(
        self,
        package_manager: PackageManagerConfig,
        quality_tools: QualityToolConfig,
        github_workflows: GitHubWorkflowConfig
    ) -> list[str]:
        """Identify potential migration issues."""
        issues = []

        # Package manager migration issues
        if package_manager.manager == PackageManager.POETRY:
            issues.append("Poetry lock file migration requires dependency resolution")

        if package_manager.manager == PackageManager.CONDA:
            issues.append("Conda environment migration may have platform compatibility issues")

        # Quality tooling conflicts
        if quality_tools.ruff_config and quality_tools.precommit_hooks:
            # Check for conflicting linters in pre-commit
            for repo in quality_tools.precommit_hooks:
                hooks = repo.get("hooks", [])
                for hook in hooks:
                    if hook.get("id") in ["black", "flake8", "isort"]:
                        issues.append(f"Pre-commit hook '{hook['id']}' conflicts with ruff configuration")

        # GitHub workflow migration issues
        if len(github_workflows.workflows) > 5:
            issues.append("Complex workflow structure may require manual intervention")

        if github_workflows.secrets:
            issues.append("GitHub secrets configuration requires manual verification")

        return issues
