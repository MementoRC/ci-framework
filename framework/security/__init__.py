"""Security scanning and vulnerability assessment infrastructure for CI/CD pipeline."""

from .analyzer import DependencyAnalyzer
from .collector import SecurityCollector
from .models import (
    DependencyInfo,
    SecurityMetrics,
    VulnerabilityInfo,
)
from .sbom_generator import SBOMGenerator

# Note: SecurityDashboardGenerator will be available once reporting module is complete
# from .dashboard_generator import SecurityDashboardGenerator

__all__ = [
    "DependencyAnalyzer",
    "SecurityCollector",
    # "SecurityDashboardGenerator",  # Available after reporting module completion
    "SBOMGenerator",
    "DependencyInfo",
    "SecurityMetrics",
    "VulnerabilityInfo",
]
