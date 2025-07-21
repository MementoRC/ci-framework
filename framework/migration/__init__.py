"""
CI Framework Migration Tools

This module provides automated migration capabilities for transitioning existing Python
projects to the new CI framework. It includes project analysis, configuration migration,
workflow transformation, and validation tools.
"""

from .analyzer import AnalysisResult, ProjectAnalyzer
from .cli import main
from .migrator import MigrationResult, ProjectMigrator

__version__ = "1.0.0"
__all__ = ["ProjectAnalyzer", "AnalysisResult", "ProjectMigrator", "MigrationResult", "main"]
