"""Hummingbot Development Framework.

Shared development and quality tools for Hummingbot features.
"""

# Import performance tools (migrated)
# Import maintenance tools (migrated)
from .maintenance import CIHealthMonitor, MaintenanceScheduler
from .performance import (
    AlertSeverity,
    BenchmarkResult,
    ComparisonMode,
    PerformanceAlert,
    PerformanceCollector,
    PerformanceComparator,
    PerformanceMetrics,
    TrendAlert,
    TrendAnalyzer,
    TrendData,
    schema,
)

# Import reporting tools (migrated)
from .reporting import ArtifactManager, GitHubReporter, ReportGenerator, TemplateEngine

# Import security tools (migrated)
from .security import (
    DependencyAnalyzer,
    DependencyInfo,
    SBOMGenerator,
    SecurityCollector,
    SecurityMetrics,
    VulnerabilityInfo,
)

__version__ = "1.0.0"
__framework_version__ = "1.0.0"

# Framework components available after migration
# Reporting tools: ReportGenerator, ArtifactManager, TemplateEngine, GitHubReporter (migrated)
# Maintenance tools: CIHealthMonitor, MaintenanceScheduler (migrated)

__all__ = [
    # Performance tools (migrated)
    "PerformanceCollector",
    "PerformanceComparator",
    "PerformanceMetrics",
    "BenchmarkResult",
    "AlertSeverity",
    "ComparisonMode",
    "PerformanceAlert",
    "TrendAnalyzer",
    "TrendAlert",
    "TrendData",
    "schema",
    # Security tools (migrated)
    "DependencyAnalyzer",
    "SecurityCollector",
    "SBOMGenerator",
    "DependencyInfo",
    "SecurityMetrics",
    "VulnerabilityInfo",
    # Reporting tools (migrated)
    "ArtifactManager",
    "GitHubReporter",
    "ReportGenerator",
    "TemplateEngine",
    # Maintenance tools (migrated)
    "CIHealthMonitor",
    "MaintenanceScheduler",
]
