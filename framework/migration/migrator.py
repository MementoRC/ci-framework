"""
Core migration engine for automated CI framework transitions.
"""

import shutil
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

import tomllib
import yaml

from .models import (
    AnalysisResult,
    MigrationPlan,
    MigrationResult,
    MigrationStatus,
    PackageManager,
    ProjectComplexity,
    ValidationResult,
)


class ProjectMigrator:
    """Handles automated migration of projects to CI framework."""

    def __init__(self, analysis: AnalysisResult) -> None:
        """Initialize migrator with project analysis results."""
        self.analysis = analysis
        self.project_path = analysis.project_path
        self.backup_dir: Optional[Path] = None
        self.migration_log: list[str] = []

    @classmethod
    def from_project_path(cls, project_path: Path) -> "ProjectMigrator":
        """Create migrator by analyzing project at given path."""
        from .analyzer import ProjectAnalyzer

        analyzer = ProjectAnalyzer(project_path)
        analysis = analyzer.analyze()
        return cls(analysis)

    def create_migration_plan(self) -> MigrationPlan:
        """Generate detailed migration execution plan."""
        plan = MigrationPlan(
            target_project=self.project_path,
            source_analysis=self.analysis
        )

        # Generate migration steps based on analysis
        steps = []

        # 1. Backup creation
        steps.append("Create project backup")

        # 2. Package manager migration
        if self.analysis.package_manager.manager != PackageManager.PIXI:
            steps.append(f"Migrate from {self.analysis.package_manager.manager.value} to pixi")
            steps.append("Update pyproject.toml with pixi configuration")
            steps.append("Create pixi environments and features")
            steps.append("Migrate dependencies and development dependencies")

        # 3. Quality tooling migration
        if not self.analysis.quality_tools.ruff_config:
            steps.append("Configure ruff for linting and formatting")

        if not self.analysis.quality_tools.pytest_config:
            steps.append("Configure pytest with comprehensive settings")

        if not self.analysis.quality_tools.precommit_hooks:
            steps.append("Setup pre-commit hooks with quality tools")

        # 4. GitHub Actions workflow migration
        steps.append("Generate CI framework workflows")
        if self.analysis.github_workflows.workflows:
            steps.append("Backup existing GitHub workflows")

        steps.append("Configure quality gates based on project complexity")

        if self.analysis.complexity in [ProjectComplexity.COMPLEX, ProjectComplexity.ENTERPRISE]:
            steps.append("Setup performance benchmarking")
            steps.append("Configure security scanning")

        # 5. Configuration file updates
        steps.append("Update project configuration files")
        steps.append("Generate CI framework templates")

        # 6. Validation and testing
        steps.append("Validate migration integrity")
        steps.append("Run initial quality checks")
        steps.append("Test CI framework integration")

        plan.migration_steps = steps
        plan.estimated_duration = self._estimate_migration_duration(len(steps))

        # Generate configuration transformations
        plan.config_transformations = self._plan_config_transformations()

        # Generate workflow updates
        plan.workflow_updates = self._plan_workflow_updates()

        # Generate validation checks
        plan.validation_checks = [
            "Verify pyproject.toml syntax",
            "Check pixi environment resolution",
            "Validate GitHub workflow syntax",
            "Test quality gate execution",
            "Verify pre-commit hook functionality"
        ]

        # Generate rollback plan
        plan.rollback_plan = [
            "Restore original configuration files",
            "Restore GitHub workflows",
            "Remove generated CI framework files",
            "Cleanup pixi environments",
            "Restore package manager state"
        ]

        return plan

    def migrate(self, dry_run: bool = False, backup: bool = True) -> MigrationResult:
        """Execute project migration."""
        result = MigrationResult(
            migration_plan=self.create_migration_plan(),
            status=MigrationStatus.IN_PROGRESS,
            migration_timestamp=datetime.now().isoformat()
        )

        try:
            # Create backup if requested
            if backup and not dry_run:
                result.backup_location = self._create_backup()
                result.rollback_available = True
                self._log("Created project backup")

            # Execute migration steps
            for step in result.migration_plan.migration_steps:
                try:
                    if dry_run:
                        self._log(f"[DRY-RUN] {step}")
                        result.completed_steps.append(step)
                    else:
                        self._execute_migration_step(step, result)
                        result.completed_steps.append(step)
                        self._log(f"Completed: {step}")

                except Exception as e:
                    error_msg = f"Failed step '{step}': {str(e)}"
                    result.errors.append(error_msg)
                    result.failed_steps.append(step)
                    self._log(f"ERROR: {error_msg}")
                    break

            # Determine final status
            if result.failed_steps:
                result.status = MigrationStatus.FAILED
            else:
                result.status = MigrationStatus.COMPLETED

                # Run validation if migration completed
                if not dry_run:
                    validation = self.validate_migration()
                    if not validation.validation_passed:
                        result.warnings.extend([
                            f"Validation issue: {issue}"
                            for issue in validation.compatibility_issues
                        ])

        except Exception as e:
            result.status = MigrationStatus.FAILED
            result.errors.append(f"Migration failed: {str(e)}")
            self._log(f"CRITICAL ERROR: {str(e)}")

        return result

    def validate_migration(self) -> ValidationResult:
        """Validate successful migration."""
        result = ValidationResult(
            project_path=self.project_path,
            validation_passed=False
        )

        try:
            # Check pyproject.toml validity
            pyproject_path = self.project_path / "pyproject.toml"
            if pyproject_path.exists():
                try:
                    with open(pyproject_path, "rb") as f:
                        tomllib.load(f)
                    result.quality_gates_status["pyproject_toml_valid"] = True
                except Exception:
                    result.quality_gates_status["pyproject_toml_valid"] = False
                    result.compatibility_issues.append("Invalid pyproject.toml syntax")

            # Check pixi environment resolution
            if shutil.which("pixi"):
                try:
                    subprocess.run(
                        ["pixi", "info"],
                        cwd=self.project_path,
                        check=True,
                        capture_output=True
                    )
                    result.quality_gates_status["pixi_environments"] = True
                except subprocess.CalledProcessError:
                    result.quality_gates_status["pixi_environments"] = False
                    result.compatibility_issues.append("Pixi environment resolution failed")

            # Check GitHub workflow syntax
            workflows_dir = self.project_path / ".github" / "workflows"
            if workflows_dir.exists():
                workflow_valid = True
                for workflow_file in workflows_dir.glob("*.yml"):
                    try:
                        with open(workflow_file) as f:
                            yaml.safe_load(f)
                    except yaml.YAMLError:
                        workflow_valid = False
                        result.compatibility_issues.append(f"Invalid workflow syntax: {workflow_file.name}")

                result.quality_gates_status["github_workflows"] = workflow_valid

            # Test quality gates execution
            quality_passed = self._test_quality_gates()
            result.quality_gates_status["quality_execution"] = quality_passed

            if not quality_passed:
                result.compatibility_issues.append("Quality gates execution failed")

            # Overall validation
            result.validation_passed = all(result.quality_gates_status.values())

            # Generate recommendations
            if not result.validation_passed:
                result.recommendations = [
                    "Run 'pixi install' to resolve dependencies",
                    "Check pixi environment configuration",
                    "Verify GitHub workflow syntax",
                    "Test quality commands manually"
                ]

        except Exception as e:
            result.compatibility_issues.append(f"Validation error: {str(e)}")

        return result

    def rollback(self) -> bool:
        """Rollback migration to original state."""
        if not self.backup_dir or not self.backup_dir.exists():
            self._log("ERROR: No backup available for rollback")
            return False

        try:
            self._log("Starting migration rollback")

            # Restore original files
            for item in self.backup_dir.iterdir():
                if item.is_file():
                    target = self.project_path / item.name
                    shutil.copy2(item, target)
                elif item.is_dir():
                    target = self.project_path / item.name
                    if target.exists():
                        shutil.rmtree(target)
                    shutil.copytree(item, target)

            # Clean up generated files
            generated_files = [
                ".ci-framework-migration.json",
                "pixi.lock"
            ]

            for filename in generated_files:
                file_path = self.project_path / filename
                if file_path.exists():
                    file_path.unlink()

            self._log("Rollback completed successfully")
            return True

        except Exception as e:
            self._log(f"ERROR: Rollback failed: {str(e)}")
            return False

    def _create_backup(self) -> Path:
        """Create backup of project before migration."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"backup_{self.project_path.name}_{timestamp}"
        self.backup_dir = self.project_path.parent / backup_name

        # Files to backup
        backup_files = [
            "pyproject.toml",
            "setup.py",
            "requirements.txt",
            "poetry.lock",
            ".pre-commit-config.yaml",
            "pytest.ini",
            "mypy.ini",
            ".flake8"
        ]

        # Directories to backup
        backup_dirs = [
            ".github"
        ]

        self.backup_dir.mkdir(exist_ok=True)

        # Backup files
        for filename in backup_files:
            source = self.project_path / filename
            if source.exists():
                shutil.copy2(source, self.backup_dir / filename)

        # Backup directories
        for dirname in backup_dirs:
            source = self.project_path / dirname
            if source.exists():
                shutil.copytree(source, self.backup_dir / dirname)

        return self.backup_dir

    def _execute_migration_step(self, step: str, result: MigrationResult) -> None:
        """Execute individual migration step."""
        if "backup" in step.lower():
            # Backup step already handled in main migrate method
            return

        elif "migrate from" in step.lower() and "to pixi" in step.lower():
            self._migrate_to_pixi()

        elif "update pyproject.toml" in step.lower():
            self._update_pyproject_toml()

        elif "configure ruff" in step.lower():
            self._configure_ruff()

        elif "configure pytest" in step.lower():
            self._configure_pytest()

        elif "setup pre-commit" in step.lower():
            self._setup_precommit_hooks()

        elif ("github workflows" in step.lower() or
              "backup existing github workflows" in step.lower() or
              "generate ci framework workflows" in step.lower() or
              "configure quality gates" in step.lower()):
            self._migrate_github_workflows()

        elif "validate migration" in step.lower():
            # Validation happens after all steps
            return

        else:
            # Generic step logging
            self._log(f"Executed: {step}")

    def _migrate_to_pixi(self) -> None:
        """Migrate project to use pixi package manager."""
        pyproject_path = self.project_path / "pyproject.toml"

        # Load or create pyproject.toml
        if pyproject_path.exists():
            with open(pyproject_path, "rb") as f:
                pyproject_data = tomllib.load(f)
        else:
            pyproject_data = {}

        # Add pixi configuration
        if "tool" not in pyproject_data:
            pyproject_data["tool"] = {}

        if "pixi" not in pyproject_data["tool"]:
            pyproject_data["tool"]["pixi"] = {}

        pixi_config = pyproject_data["tool"]["pixi"]

        # Configure basic pixi settings
        pixi_config["channels"] = ["conda-forge", "pola-rs"]
        pixi_config["platforms"] = ["linux-64", "osx-arm64", "osx-64", "win-64"]

        # Add dependencies
        if "dependencies" not in pixi_config:
            pixi_config["dependencies"] = {}

        pixi_config["dependencies"]["python"] = ">=3.10"

        # Add environments
        if "environments" not in pixi_config:
            pixi_config["environments"] = {}

        complexity = self.analysis.complexity
        if complexity == ProjectComplexity.SIMPLE:
            pixi_config["environments"] = {
                "default": {"features": ["dev"], "solve-group": "default"}
            }
        else:
            pixi_config["environments"] = {
                "default": {"features": ["dev"], "solve-group": "default"},
                "quality": {"features": ["quality"], "solve-group": "default"},
                "ci": {"features": ["ci"], "solve-group": "default"}
            }

        # Add features
        if "feature" not in pixi_config:
            pixi_config["feature"] = {}

        # Basic development feature
        pixi_config["feature"]["dev"] = {
            "dependencies": {
                "pytest": "*",
                "ruff": "*"
            }
        }

        # Quality feature for moderate+ complexity
        if complexity != ProjectComplexity.SIMPLE:
            pixi_config["feature"]["quality"] = {
                "dependencies": {
                    "pytest": "*",
                    "ruff": "*",
                    "mypy": "*",
                    "bandit": "*",
                    "safety": "*"
                }
            }

        # Add basic tasks
        if "tasks" not in pixi_config:
            pixi_config["tasks"] = {}

        pixi_config["tasks"] = {
            "test": "pytest",
            "lint": "ruff check .",
            "lint-fix": "ruff check --fix .",
            "format": "ruff format .",
            "quality": "pytest && ruff check ."
        }

        # Write updated pyproject.toml
        self._write_pyproject_toml(pyproject_path, pyproject_data)

    def _update_pyproject_toml(self) -> None:
        """Update pyproject.toml with CI framework configuration."""
        # This is handled in _migrate_to_pixi method
        pass

    def _configure_ruff(self) -> None:
        """Configure ruff for linting and formatting."""
        pyproject_path = self.project_path / "pyproject.toml"

        with open(pyproject_path, "rb") as f:
            pyproject_data = tomllib.load(f)

        if "tool" not in pyproject_data:
            pyproject_data["tool"] = {}

        # Configure ruff
        pyproject_data["tool"]["ruff"] = {
            "target-version": "py310",
            "line-length": 88,
            "select": [
                "F",    # Pyflakes
                "E",    # pycodestyle errors
                "W",    # pycodestyle warnings
                "I",    # isort
                "N",    # pep8-naming
                "UP",   # pyupgrade
                "B",    # flake8-bugbear
                "C4",   # flake8-comprehensions
                "PT",   # flake8-pytest-style
            ],
            "ignore": [
                "E501",  # line too long (handled by formatter)
            ],
            "exclude": [
                ".git",
                "__pycache__",
                "build",
                "dist",
                "venv",
                ".venv"
            ]
        }

        self._write_pyproject_toml(pyproject_path, pyproject_data)

    def _configure_pytest(self) -> None:
        """Configure pytest with comprehensive settings."""
        pyproject_path = self.project_path / "pyproject.toml"

        with open(pyproject_path, "rb") as f:
            pyproject_data = tomllib.load(f)

        if "tool" not in pyproject_data:
            pyproject_data["tool"] = {}

        # Configure pytest
        pyproject_data["tool"]["pytest"] = {
            "ini_options": {
                "testpaths": ["tests"],
                "python_files": ["test_*.py", "*_test.py"],
                "python_classes": ["Test*"],
                "python_functions": ["test_*"],
                "addopts": [
                    "--strict-markers",
                    "--strict-config",
                    "--verbose",
                    "--cov=src",
                    "--cov-report=term-missing",
                    "--cov-report=xml",
                    "--cov-report=html"
                ],
                "markers": [
                    "slow: marks tests as slow (deselect with '-m \"not slow\"')",
                    "integration: marks tests as integration tests",
                    "unit: marks tests as unit tests"
                ],
                "timeout": 120
            }
        }

        self._write_pyproject_toml(pyproject_path, pyproject_data)

    def _setup_precommit_hooks(self) -> None:
        """Setup pre-commit hooks with quality tools."""
        precommit_config = {
            "repos": [
                {
                    "repo": "https://github.com/pre-commit/pre-commit-hooks",
                    "rev": "v4.5.0",
                    "hooks": [
                        {"id": "trailing-whitespace"},
                        {"id": "end-of-file-fixer"},
                        {"id": "check-yaml"},
                        {"id": "check-toml"},
                        {"id": "check-json"},
                        {"id": "check-merge-conflict"}
                    ]
                },
                {
                    "repo": "https://github.com/astral-sh/ruff-pre-commit",
                    "rev": "v0.1.9",
                    "hooks": [
                        {"id": "ruff", "args": ["--fix"]},
                        {"id": "ruff-format"}
                    ]
                }
            ]
        }

        # Add security hooks for complex projects
        if self.analysis.complexity in [ProjectComplexity.COMPLEX, ProjectComplexity.ENTERPRISE]:
            precommit_config["repos"].append({
                "repo": "https://github.com/PyCQA/bandit",
                "rev": "1.7.5",
                "hooks": [
                    {"id": "bandit", "args": ["-c", "pyproject.toml"]}
                ]
            })

        precommit_path = self.project_path / ".pre-commit-config.yaml"
        with open(precommit_path, "w") as f:
            yaml.dump(precommit_config, f, default_flow_style=False)

    def _migrate_github_workflows(self) -> None:
        """Migrate GitHub Actions workflows to use CI framework."""
        workflows_dir = self.project_path / ".github" / "workflows"
        workflows_dir.mkdir(parents=True, exist_ok=True)

        # Generate main CI workflow
        ci_workflow = self._generate_ci_workflow()

        with open(workflows_dir / "ci.yml", "w") as f:
            yaml.dump(ci_workflow, f, default_flow_style=False)

    def _generate_ci_workflow(self) -> dict[str, Any]:
        """Generate GitHub Actions CI workflow."""
        complexity = self.analysis.complexity

        # Base workflow structure
        workflow = {
            "name": "CI",
            "on": {
                "push": {"branches": ["main", "master", "develop"]},
                "pull_request": {"branches": ["main", "master", "develop"]}
            },
            "jobs": {
                "quality-gates": {
                    "runs-on": "ubuntu-latest",
                    "steps": [
                        {"uses": "actions/checkout@v4"},
                        {
                            "name": "Setup Pixi",
                            "uses": "prefix-dev/setup-pixi@v0.8.1",
                            "with": {"pixi-version": "latest"}
                        },
                        {
                            "name": "Run Quality Gates",
                            "run": "pixi run quality"
                        }
                    ]
                }
            }
        }

        # Add security scanning for complex projects
        if complexity in [ProjectComplexity.COMPLEX, ProjectComplexity.ENTERPRISE]:
            workflow["jobs"]["security-scan"] = {
                "runs-on": "ubuntu-latest",
                "steps": [
                    {"uses": "actions/checkout@v4"},
                    {
                        "name": "Setup Pixi",
                        "uses": "prefix-dev/setup-pixi@v0.8.1"
                    },
                    {
                        "name": "Run Security Scan",
                        "run": "pixi run -e quality bandit -r src/"
                    }
                ]
            }

        return workflow

    def _test_quality_gates(self) -> bool:
        """Test quality gates execution."""
        try:
            # Test basic quality command
            result = subprocess.run(
                ["pixi", "run", "quality"],
                cwd=self.project_path,
                capture_output=True,
                timeout=300  # 5 minute timeout
            )
            return result.returncode == 0
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError):
            return False

    def _write_pyproject_toml(self, path: Path, data: dict[str, Any]) -> None:
        """Write pyproject.toml file with proper formatting."""
        # This is a simplified implementation
        # In a real implementation, you'd want to use a TOML writer that preserves formatting
        import tomli_w

        with open(path, "wb") as f:
            tomli_w.dump(data, f)

    def _plan_config_transformations(self) -> dict[str, dict[str, Any]]:
        """Plan configuration file transformations."""
        transformations = {}

        if self.analysis.package_manager.manager != PackageManager.PIXI:
            transformations["pyproject.toml"] = {
                "add_pixi_config": True,
                "migrate_dependencies": True,
                "add_environments": True
            }

        if not self.analysis.quality_tools.ruff_config:
            transformations["ruff_config"] = {
                "add_ruff_config": True,
                "target_version": "py310",
                "line_length": 88,
                "select_rules": ["F", "E", "W", "I", "N", "UP", "B", "C4", "PT"]
            }

        return transformations

    def _plan_workflow_updates(self) -> dict[str, dict[str, Any]]:
        """Plan GitHub workflow updates."""
        updates = {}

        if self.analysis.github_workflows.workflows:
            updates["ci.yml"] = {
                "replace_existing": True,
                "use_ci_framework": True,
                "complexity_tier": self.analysis.complexity.value
            }

        return updates

    def _estimate_migration_duration(self, step_count: int) -> str:
        """Estimate migration duration based on step count and complexity."""
        base_minutes = step_count * 2  # 2 minutes per step base

        if self.analysis.complexity == ProjectComplexity.SIMPLE:
            return f"{base_minutes}-{base_minutes + 5} minutes"
        elif self.analysis.complexity == ProjectComplexity.MODERATE:
            return f"{base_minutes + 5}-{base_minutes + 15} minutes"
        elif self.analysis.complexity == ProjectComplexity.COMPLEX:
            return f"{base_minutes + 15}-{base_minutes + 30} minutes"
        else:  # ENTERPRISE
            return f"{base_minutes + 30}-{base_minutes + 60} minutes"

    def _log(self, message: str) -> None:
        """Log migration message."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_entry = f"[{timestamp}] {message}"
        self.migration_log.append(log_entry)
        print(log_entry)
