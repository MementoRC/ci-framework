"""Data models for security metrics and vulnerability results."""

import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class VulnerabilityInfo:
    """Information about a single vulnerability."""

    id: str  # CVE ID or vulnerability identifier
    package_name: str
    package_version: str
    severity: str  # low, medium, high, critical
    description: str
    fix_versions: list[str] = field(default_factory=list)
    aliases: list[str] = field(default_factory=list)
    advisory_url: str | None = None
    timestamp: float = field(default_factory=time.time)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "id": self.id,
            "package_name": self.package_name,
            "package_version": self.package_version,
            "severity": self.severity,
            "description": self.description,
            "fix_versions": self.fix_versions,
            "aliases": self.aliases,
            "advisory_url": self.advisory_url,
            "timestamp": self.timestamp,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "VulnerabilityInfo":
        """Create from dictionary representation."""
        return cls(
            id=data["id"],
            package_name=data["package_name"],
            package_version=data["package_version"],
            severity=data["severity"],
            description=data["description"],
            fix_versions=data.get("fix_versions", []),
            aliases=data.get("aliases", []),
            advisory_url=data.get("advisory_url"),
            timestamp=data.get("timestamp", time.time()),
            metadata=data.get("metadata", {}),
        )


@dataclass
class DependencyInfo:
    """Information about a single dependency."""

    name: str
    version: str
    package_manager: str  # pip, conda, pixi
    source: str | None = None  # package index URL
    license: str | None = None
    vulnerabilities: list[VulnerabilityInfo] = field(default_factory=list)
    dependencies: list[str] = field(default_factory=list)  # list of dependency names
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def has_vulnerabilities(self) -> bool:
        """Check if this dependency has any vulnerabilities."""
        return len(self.vulnerabilities) > 0

    @property
    def vulnerability_count_by_severity(self) -> dict[str, int]:
        """Count vulnerabilities by severity level."""
        counts = {"low": 0, "medium": 0, "high": 0, "critical": 0}
        for vuln in self.vulnerabilities:
            severity = vuln.severity.lower()
            if severity in counts:
                counts[severity] += 1
        return counts

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "name": self.name,
            "version": self.version,
            "package_manager": self.package_manager,
            "source": self.source,
            "license": self.license,
            "vulnerabilities": [vuln.to_dict() for vuln in self.vulnerabilities],
            "dependencies": self.dependencies,
            "metadata": self.metadata,
            "vulnerability_summary": self.vulnerability_count_by_severity,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "DependencyInfo":
        """Create from dictionary representation."""
        return cls(
            name=data["name"],
            version=data["version"],
            package_manager=data["package_manager"],
            source=data.get("source"),
            license=data.get("license"),
            vulnerabilities=[
                VulnerabilityInfo.from_dict(vuln) for vuln in data.get("vulnerabilities", [])
            ],
            dependencies=data.get("dependencies", []),
            metadata=data.get("metadata", {}),
        )


@dataclass
class SecurityMetrics:
    """Collection of security metrics for a build/scan."""

    build_id: str
    timestamp: datetime
    dependencies: list[DependencyInfo] = field(default_factory=list)
    scan_config: dict[str, Any] = field(default_factory=dict)
    environment: dict[str, str] = field(default_factory=dict)
    scan_duration: float | None = None  # seconds

    def add_dependency(self, dependency: DependencyInfo) -> None:
        """Add a dependency to the collection."""
        self.dependencies.append(dependency)

    def get_dependency(self, name: str) -> DependencyInfo | None:
        """Get a specific dependency by name."""
        for dep in self.dependencies:
            if dep.name == name:
                return dep
        return None

    def get_vulnerable_dependencies(self) -> list[DependencyInfo]:
        """Get all dependencies with vulnerabilities."""
        return [dep for dep in self.dependencies if dep.has_vulnerabilities]

    def calculate_summary_stats(self) -> dict[str, Any]:
        """Calculate summary statistics across all dependencies."""
        total_deps = len(self.dependencies)
        vulnerable_deps = len(self.get_vulnerable_dependencies())

        # Count all vulnerabilities by severity
        severity_counts = {"low": 0, "medium": 0, "high": 0, "critical": 0}
        total_vulnerabilities = 0

        for dep in self.dependencies:
            for vuln in dep.vulnerabilities:
                total_vulnerabilities += 1
                severity = vuln.severity.lower()
                if severity in severity_counts:
                    severity_counts[severity] += 1

        # Package manager distribution
        package_managers: dict[str, int] = {}
        for dep in self.dependencies:
            pm = dep.package_manager
            package_managers[pm] = package_managers.get(pm, 0) + 1

        return {
            "total_dependencies": total_deps,
            "vulnerable_dependencies": vulnerable_deps,
            "vulnerability_free_dependencies": total_deps - vulnerable_deps,
            "total_vulnerabilities": total_vulnerabilities,
            "vulnerabilities_by_severity": severity_counts,
            "package_managers": package_managers,
            "vulnerability_rate": round(vulnerable_deps / total_deps * 100, 2)
            if total_deps > 0
            else 0,
        }

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "build_id": self.build_id,
            "timestamp": self.timestamp.isoformat(),
            "dependencies": [dep.to_dict() for dep in self.dependencies],
            "scan_config": self.scan_config,
            "environment": self.environment,
            "scan_duration": self.scan_duration,
            "summary_stats": self.calculate_summary_stats(),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SecurityMetrics":
        """Create from dictionary representation."""
        return cls(
            build_id=data["build_id"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
            dependencies=[DependencyInfo.from_dict(dep) for dep in data.get("dependencies", [])],
            scan_config=data.get("scan_config", {}),
            environment=data.get("environment", {}),
            scan_duration=data.get("scan_duration"),
        )
