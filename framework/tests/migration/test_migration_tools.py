"""
Comprehensive tests for CI framework migration tools.
"""

import json
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
import yaml

from framework.migration.analyzer import ProjectAnalyzer
from framework.migration.migrator import ProjectMigrator
from framework.migration.models import (
    AnalysisResult,
    MigrationStatus,
    PackageManager,
    ProjectComplexity,
    ProjectType,
)


@pytest.fixture
def temp_project():
    """Create a temporary project directory for testing."""
    with tempfile.TemporaryDirectory() as temp_dir:
        project_path = Path(temp_dir)

        # Create basic project structure
        (project_path / "src").mkdir()
        (project_path / "tests").mkdir()
        (project_path / "src" / "__init__.py").write_text("")
        (project_path / "tests" / "__init__.py").write_text("")

        yield project_path


@pytest.fixture
def simple_pyproject_toml():
    """Sample simple pyproject.toml content."""
    return """
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "test-project"
version = "0.1.0"
description = "Test project"
dependencies = ["requests"]

[project.optional-dependencies]
dev = ["pytest"]
"""


@pytest.fixture
def pixi_pyproject_toml():
    """Sample pixi-enabled pyproject.toml content."""
    return """
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "test-project"
version = "0.1.0"

[tool.pixi]
channels = ["conda-forge"]
platforms = ["linux-64", "osx-arm64"]

[tool.pixi.dependencies]
python = ">=3.10"
requests = "*"

[tool.pixi.feature.dev.dependencies]
pytest = "*"
ruff = "*"

[tool.pixi.environments]
default = {features = ["dev"], solve-group = "default"}

[tool.pixi.tasks]
test = "pytest"
lint = "ruff check ."
"""


@pytest.fixture
def github_workflow():
    """Sample GitHub workflow configuration."""
    return {
        "name": "CI",
        "on": {
            "push": {"branches": ["main"]},
            "pull_request": {"branches": ["main"]}
        },
        "jobs": {
            "test": {
                "runs-on": "ubuntu-latest",
                "steps": [
                    {"uses": "actions/checkout@v4"},
                    {"name": "Setup Python", "uses": "actions/setup-python@v4"},
                    {"name": "Run tests", "run": "pytest"}
                ]
            }
        }
    }


class TestProjectAnalyzer:
    """Test suite for ProjectAnalyzer."""

    def test_analyzer_initialization(self, temp_project):
        """Test analyzer initialization with valid project path."""
        analyzer = ProjectAnalyzer(temp_project)
        assert analyzer.project_path == temp_project.resolve()

    def test_analyzer_initialization_invalid_path(self):
        """Test analyzer initialization with invalid path."""
        with pytest.raises(FileNotFoundError):
            ProjectAnalyzer(Path("/nonexistent/path"))

    def test_analyzer_initialization_file_path(self, temp_project):
        """Test analyzer initialization with file instead of directory."""
        file_path = temp_project / "test_file.txt"
        file_path.write_text("test")

        with pytest.raises(ValueError):
            ProjectAnalyzer(file_path)

    def test_analyze_simple_project(self, temp_project, simple_pyproject_toml):
        """Test analysis of simple project."""
        (temp_project / "pyproject.toml").write_text(simple_pyproject_toml)

        analyzer = ProjectAnalyzer(temp_project)
        result = analyzer.analyze()

        assert isinstance(result, AnalysisResult)
        assert result.project_path == temp_project
        assert result.project_type in [ProjectType.LIBRARY, ProjectType.APPLICATION]
        assert result.complexity == ProjectComplexity.SIMPLE
        assert result.package_manager.manager in [PackageManager.PIP, PackageManager.UNKNOWN]

    def test_analyze_pixi_project(self, temp_project, pixi_pyproject_toml):
        """Test analysis of pixi-enabled project."""
        (temp_project / "pyproject.toml").write_text(pixi_pyproject_toml)

        analyzer = ProjectAnalyzer(temp_project)
        result = analyzer.analyze()

        assert result.package_manager.manager == PackageManager.PIXI
        assert len(result.package_manager.environments) > 0
        assert result.complexity in [ProjectComplexity.SIMPLE, ProjectComplexity.MODERATE]

    def test_analyze_project_structure(self, temp_project):
        """Test project structure analysis."""
        # Create additional directories
        (temp_project / "docs").mkdir()
        (temp_project / "Dockerfile").write_text("FROM python:3.10")
        (temp_project / ".github" / "workflows").mkdir(parents=True)

        analyzer = ProjectAnalyzer(temp_project)
        result = analyzer.analyze()

        structure = result.project_structure
        assert len(structure.source_dirs) >= 1
        assert len(structure.test_dirs) >= 1
        assert len(structure.doc_dirs) >= 1
        assert structure.has_dockerfile
        assert not structure.has_setup_py

    def test_analyze_github_workflows(self, temp_project, github_workflow):
        """Test GitHub workflow analysis."""
        workflows_dir = temp_project / ".github" / "workflows"
        workflows_dir.mkdir(parents=True)

        with open(workflows_dir / "ci.yml", "w") as f:
            yaml.dump(github_workflow, f)

        analyzer = ProjectAnalyzer(temp_project)
        result = analyzer.analyze()

        assert len(result.github_workflows.workflows) == 1
        assert "ci" in result.github_workflows.workflows

    def test_detect_python_versions(self, temp_project, pixi_pyproject_toml):
        """Test Python version detection."""
        (temp_project / "pyproject.toml").write_text(pixi_pyproject_toml)

        analyzer = ProjectAnalyzer(temp_project)
        result = analyzer.analyze()

        assert len(result.python_versions) >= 1
        assert all(version.startswith("3.") for version in result.python_versions)

    def test_complexity_assessment(self, temp_project):
        """Test project complexity assessment."""
        # Create complex project structure
        complex_pyproject = """
[tool.pixi]
channels = ["conda-forge"]
platforms = ["linux-64", "osx-arm64", "win-64"]

[tool.pixi.dependencies]
python = ">=3.10"

[tool.pixi.feature.dev.dependencies]
pytest = "*"
ruff = "*"
mypy = "*"

[tool.pixi.feature.security.dependencies]
bandit = "*"
safety = "*"

[tool.pixi.environments]
default = {features = ["dev"], solve-group = "default"}
security = {features = ["dev", "security"], solve-group = "default"}

[tool.pixi.tasks]
test = "pytest"
lint = "ruff check ."
security = "bandit -r src/"
"""

        (temp_project / "pyproject.toml").write_text(complex_pyproject)

        # Add multiple workflows
        workflows_dir = temp_project / ".github" / "workflows"
        workflows_dir.mkdir(parents=True)

        for workflow_name in ["ci.yml", "security.yml", "deploy.yml"]:
            with open(workflows_dir / workflow_name, "w") as f:
                yaml.dump({"name": workflow_name.replace(".yml", "")}, f)

        analyzer = ProjectAnalyzer(temp_project)
        result = analyzer.analyze()

        # Should be classified as moderate or complex
        assert result.complexity in [
            ProjectComplexity.MODERATE,
            ProjectComplexity.COMPLEX,
            ProjectComplexity.ENTERPRISE
        ]

    def test_migration_recommendations(self, temp_project, simple_pyproject_toml):
        """Test migration recommendations generation."""
        (temp_project / "pyproject.toml").write_text(simple_pyproject_toml)

        analyzer = ProjectAnalyzer(temp_project)
        result = analyzer.analyze()

        # Should recommend pixi migration for non-pixi project
        recommendations = [rec.lower() for rec in result.migration_recommendations]
        assert any("pixi" in rec for rec in recommendations)

    def test_potential_issues_identification(self, temp_project):
        """Test potential issues identification."""
        # Create project with conflicting configurations
        conflicting_config = """
[tool.poetry]
name = "test-project"

[tool.ruff]
line-length = 88

[tool.black]
line-length = 100
"""
        (temp_project / "pyproject.toml").write_text(conflicting_config)
        (temp_project / "poetry.lock").write_text("")

        analyzer = ProjectAnalyzer(temp_project)
        result = analyzer.analyze()

        # Should identify poetry migration and potential conflicts
        issues = [issue.lower() for issue in result.potential_issues]
        assert any("poetry" in issue for issue in issues)


class TestProjectMigrator:
    """Test suite for ProjectMigrator."""

    def test_migrator_initialization(self, temp_project):
        """Test migrator initialization."""
        analyzer = ProjectAnalyzer(temp_project)
        analysis = analyzer.analyze()
        migrator = ProjectMigrator(analysis)

        assert migrator.project_path == temp_project
        assert migrator.analysis == analysis

    def test_from_project_path(self, temp_project):
        """Test migrator creation from project path."""
        migrator = ProjectMigrator.from_project_path(temp_project)

        assert migrator.project_path == temp_project
        assert migrator.analysis is not None

    def test_create_migration_plan(self, temp_project, simple_pyproject_toml):
        """Test migration plan creation."""
        (temp_project / "pyproject.toml").write_text(simple_pyproject_toml)

        migrator = ProjectMigrator.from_project_path(temp_project)
        plan = migrator.create_migration_plan()

        assert len(plan.migration_steps) > 0
        assert plan.target_project == temp_project
        assert plan.estimated_duration is not None
        assert len(plan.validation_checks) > 0
        assert len(plan.rollback_plan) > 0

    def test_migration_dry_run(self, temp_project, simple_pyproject_toml):
        """Test dry run migration."""
        (temp_project / "pyproject.toml").write_text(simple_pyproject_toml)

        migrator = ProjectMigrator.from_project_path(temp_project)
        result = migrator.migrate(dry_run=True)

        assert result.status == MigrationStatus.COMPLETED
        assert len(result.completed_steps) > 0
        assert len(result.failed_steps) == 0
        assert result.backup_location is None  # No backup in dry run

    @patch('shutil.which')
    @patch('subprocess.run')
    def test_migration_execution(self, mock_run, mock_which, temp_project, simple_pyproject_toml):
        """Test actual migration execution."""
        (temp_project / "pyproject.toml").write_text(simple_pyproject_toml)

        # Mock external tools
        mock_which.return_value = "/usr/bin/pixi"
        mock_run.return_value = Mock(returncode=0)

        migrator = ProjectMigrator.from_project_path(temp_project)
        result = migrator.migrate(dry_run=False, backup=True)

        assert result.backup_location is not None
        assert result.rollback_available

        # Check if pyproject.toml was modified
        updated_content = (temp_project / "pyproject.toml").read_text()
        assert "[tool.pixi]" in updated_content

    def test_migration_validation(self, temp_project, pixi_pyproject_toml):
        """Test migration validation."""
        (temp_project / "pyproject.toml").write_text(pixi_pyproject_toml)

        migrator = ProjectMigrator.from_project_path(temp_project)
        validation = migrator.validate_migration()

        assert validation.project_path == temp_project
        assert "pyproject_toml_valid" in validation.quality_gates_status
        assert validation.quality_gates_status["pyproject_toml_valid"]

    def test_rollback_functionality(self, temp_project, simple_pyproject_toml):
        """Test migration rollback."""
        original_content = simple_pyproject_toml
        (temp_project / "pyproject.toml").write_text(original_content)

        with patch('shutil.which', return_value="/usr/bin/pixi"):
            with patch('subprocess.run', return_value=Mock(returncode=0)):
                migrator = ProjectMigrator.from_project_path(temp_project)

                # Perform migration
                result = migrator.migrate(dry_run=False, backup=True)
                assert result.status == MigrationStatus.COMPLETED

                # Verify content changed
                new_content = (temp_project / "pyproject.toml").read_text()
                assert "[tool.pixi]" in new_content

                # Perform rollback
                rollback_success = migrator.rollback()
                assert rollback_success

                # Verify content restored (approximately)
                restored_content = (temp_project / "pyproject.toml").read_text()
                assert "test-project" in restored_content

    @patch('shutil.which')
    @patch('subprocess.run')
    def test_migration_failure_handling(self, mock_run, mock_which, temp_project):
        """Test migration failure handling."""
        # Create invalid pyproject.toml
        (temp_project / "pyproject.toml").write_text("invalid toml content [[[")

        mock_which.return_value = "/usr/bin/pixi"
        mock_run.side_effect = Exception("Migration failed")

        migrator = ProjectMigrator.from_project_path(temp_project)
        result = migrator.migrate(dry_run=False, backup=True)

        assert result.status == MigrationStatus.FAILED
        assert len(result.errors) > 0
        assert result.rollback_available


class TestMigrationCLI:
    """Test suite for migration CLI."""

    def test_analyze_command_output(self, temp_project, simple_pyproject_toml, capsys):
        """Test analyze command output."""
        import argparse

        from framework.migration.cli import analyze_command

        (temp_project / "pyproject.toml").write_text(simple_pyproject_toml)

        # Mock command line arguments
        args = argparse.Namespace(
            project_path=str(temp_project),
            output=None
        )

        exit_code = analyze_command(args)
        captured = capsys.readouterr()

        assert exit_code == 0
        assert "Project Analysis Complete" in captured.out
        assert "Type:" in captured.out
        assert "Complexity:" in captured.out

    def test_analyze_command_json_output(self, temp_project, simple_pyproject_toml):
        """Test analyze command with JSON output."""
        import argparse

        from framework.migration.cli import analyze_command

        (temp_project / "pyproject.toml").write_text(simple_pyproject_toml)
        output_file = temp_project / "analysis.json"

        args = argparse.Namespace(
            project_path=str(temp_project),
            output=str(output_file)
        )

        exit_code = analyze_command(args)
        assert exit_code == 0
        assert output_file.exists()

        # Verify JSON content
        with open(output_file) as f:
            analysis_data = json.load(f)

        assert "project_path" in analysis_data
        assert "project_type" in analysis_data
        assert "complexity" in analysis_data


class TestMigrationIntegration:
    """Integration tests for migration tools."""

    def test_end_to_end_simple_migration(self, temp_project):
        """Test complete end-to-end migration for simple project."""
        # Create a simple project
        simple_config = """
[build-system]
requires = ["setuptools"]
build-backend = "setuptools.build"

[project]
name = "simple-project"
version = "0.1.0"
dependencies = ["requests"]
"""
        (temp_project / "pyproject.toml").write_text(simple_config)
        (temp_project / "requirements.txt").write_text("requests==2.28.0\npytest==7.0.0")

        with patch('shutil.which', return_value="/usr/bin/pixi"):
            with patch('subprocess.run', return_value=Mock(returncode=0)):
                # Analyze project
                analyzer = ProjectAnalyzer(temp_project)
                analysis = analyzer.analyze()

                # Verify analysis results
                assert analysis.project_type in [ProjectType.LIBRARY, ProjectType.APPLICATION]
                assert analysis.complexity == ProjectComplexity.SIMPLE
                assert analysis.package_manager.manager in [PackageManager.PIP, PackageManager.UNKNOWN]

                # Perform migration
                migrator = ProjectMigrator(analysis)
                result = migrator.migrate(dry_run=False, backup=True)

                # Verify migration success
                assert result.status == MigrationStatus.COMPLETED
                assert result.backup_location is not None

                # Verify pyproject.toml was updated
                updated_content = (temp_project / "pyproject.toml").read_text()
                assert "[tool.pixi]" in updated_content

                # Verify pre-commit config was created
                assert (temp_project / ".pre-commit-config.yaml").exists()

                # Verify GitHub workflow was created
                workflow_file = temp_project / ".github" / "workflows" / "ci.yml"
                assert workflow_file.exists()

                with open(workflow_file) as f:
                    workflow_content = yaml.safe_load(f)
                assert "pixi" in yaml.dump(workflow_content)

                # Test validation
                validation = migrator.validate_migration()
                assert validation.validation_passed or len(validation.compatibility_issues) <= 2

    def test_migration_with_existing_pixi(self, temp_project, pixi_pyproject_toml):
        """Test migration of project that already uses pixi."""
        (temp_project / "pyproject.toml").write_text(pixi_pyproject_toml)

        with patch('subprocess.run', return_value=Mock(returncode=0)):
            # Analyze project
            analyzer = ProjectAnalyzer(temp_project)
            analysis = analyzer.analyze()

            # Should detect pixi
            assert analysis.package_manager.manager == PackageManager.PIXI

            # Migration should still enhance the configuration
            migrator = ProjectMigrator(analysis)
            result = migrator.migrate(dry_run=False, backup=True)

            # Should complete successfully
            assert result.status == MigrationStatus.COMPLETED

            # Should have completed successfully with quality enhancements
            assert len(result.completed_steps) >= 8

    @patch('subprocess.run')
    def test_migration_performance(self, mock_run, temp_project, simple_pyproject_toml):
        """Test migration performance and timing."""
        import time

        (temp_project / "pyproject.toml").write_text(simple_pyproject_toml)
        mock_run.return_value = Mock(returncode=0)

        migrator = ProjectMigrator.from_project_path(temp_project)

        start_time = time.time()
        result = migrator.migrate(dry_run=True)
        end_time = time.time()

        migration_time = end_time - start_time

        # Dry run should complete quickly (under 5 seconds)
        assert migration_time < 5.0
        assert result.status == MigrationStatus.COMPLETED
