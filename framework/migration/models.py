"""
Migration models and data structures.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Optional


class PackageManager(Enum):
    """Supported package managers."""
    PIXI = "pixi"
    POETRY = "poetry"
    HATCH = "hatch"
    PIP = "pip"
    CONDA = "conda"
    UNKNOWN = "unknown"


class ProjectComplexity(Enum):
    """Project complexity classification."""
    SIMPLE = "simple"
    MODERATE = "moderate"
    COMPLEX = "complex"
    ENTERPRISE = "enterprise"


class ProjectType(Enum):
    """Type of Python project."""
    LIBRARY = "library"
    APPLICATION = "application"
    CLI_TOOL = "cli_tool"
    MCP_SERVER = "mcp_server"
    FRAMEWORK = "framework"
    MONOREPO = "monorepo"
    UNKNOWN = "unknown"


class MigrationStatus(Enum):
    """Migration operation status."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"


@dataclass
class PackageManagerConfig:
    """Package manager configuration details."""
    manager: PackageManager
    config_file: Optional[Path] = None
    environments: list[str] = field(default_factory=list)
    features: list[str] = field(default_factory=list)
    dependencies: dict[str, Any] = field(default_factory=dict)
    dev_dependencies: dict[str, Any] = field(default_factory=dict)
    tasks: dict[str, str] = field(default_factory=dict)


@dataclass
class QualityToolConfig:
    """Quality tooling configuration."""
    pytest_config: dict[str, Any] = field(default_factory=dict)
    ruff_config: dict[str, Any] = field(default_factory=dict)
    mypy_config: dict[str, Any] = field(default_factory=dict)
    bandit_config: dict[str, Any] = field(default_factory=dict)
    coverage_config: dict[str, Any] = field(default_factory=dict)
    precommit_hooks: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class GitHubWorkflowConfig:
    """GitHub Actions workflow configuration."""
    workflows: dict[str, dict[str, Any]] = field(default_factory=dict)
    secrets: set[str] = field(default_factory=set)
    permissions: dict[str, str] = field(default_factory=dict)
    matrix_strategies: list[dict[str, Any]] = field(default_factory=list)
    artifacts: list[str] = field(default_factory=list)


@dataclass
class ProjectStructure:
    """Project directory and file structure."""
    root_path: Path
    source_dirs: list[Path] = field(default_factory=list)
    test_dirs: list[Path] = field(default_factory=list)
    doc_dirs: list[Path] = field(default_factory=list)
    config_files: list[Path] = field(default_factory=list)
    workflow_files: list[Path] = field(default_factory=list)
    has_dockerfile: bool = False
    has_pyproject_toml: bool = False
    has_setup_py: bool = False


@dataclass
class AnalysisResult:
    """Complete project analysis results."""
    project_path: Path
    project_type: ProjectType
    complexity: ProjectComplexity
    package_manager: PackageManagerConfig
    quality_tools: QualityToolConfig
    github_workflows: GitHubWorkflowConfig
    project_structure: ProjectStructure
    python_versions: list[str] = field(default_factory=list)
    platforms: list[str] = field(default_factory=list)
    migration_recommendations: list[str] = field(default_factory=list)
    potential_issues: list[str] = field(default_factory=list)
    analysis_timestamp: Optional[str] = None


@dataclass
class MigrationPlan:
    """Detailed migration execution plan."""
    target_project: Path
    source_analysis: AnalysisResult
    migration_steps: list[str] = field(default_factory=list)
    config_transformations: dict[str, dict[str, Any]] = field(default_factory=dict)
    workflow_updates: dict[str, dict[str, Any]] = field(default_factory=dict)
    backup_files: list[Path] = field(default_factory=list)
    validation_checks: list[str] = field(default_factory=list)
    rollback_plan: list[str] = field(default_factory=list)
    estimated_duration: Optional[str] = None


@dataclass
class MigrationResult:
    """Results of a migration operation."""
    migration_plan: MigrationPlan
    status: MigrationStatus
    completed_steps: list[str] = field(default_factory=list)
    failed_steps: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    backup_location: Optional[Path] = None
    rollback_available: bool = False
    performance_impact: Optional[dict[str, Any]] = None
    migration_timestamp: Optional[str] = None


@dataclass
class ValidationResult:
    """Migration validation results."""
    project_path: Path
    validation_passed: bool
    quality_gates_status: dict[str, bool] = field(default_factory=dict)
    performance_comparison: Optional[dict[str, Any]] = None
    compatibility_issues: list[str] = field(default_factory=list)
    success_metrics: dict[str, Any] = field(default_factory=dict)
    recommendations: list[str] = field(default_factory=list)
