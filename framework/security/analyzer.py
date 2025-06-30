"""Core dependency analysis and vulnerability scanning functionality."""

import json
import subprocess
import time
from pathlib import Path
from typing import Any

from .models import DependencyInfo, VulnerabilityInfo


class DependencyAnalyzer:
    """Analyzes project dependencies and scans for vulnerabilities."""

    def __init__(self, project_path: str | Path):
        """Initialize the dependency analyzer.

        Args:
            project_path: Path to the project root directory.
        """
        self.project_path = Path(project_path)
        self.supported_package_managers = ["pip", "pixi", "conda"]

    def detect_package_managers(self) -> list[str]:
        """Detect which package managers are used in the project.

        Returns:
            List of detected package manager names.
        """
        detected = []

        # Check for pip (requirements.txt, pyproject.toml)
        if (
            (self.project_path / "requirements.txt").exists()
            or (self.project_path / "pyproject.toml").exists()
            or (self.project_path / "setup.py").exists()
        ):
            detected.append("pip")

        # Check for pixi (pixi.toml, pixi.lock)
        if (self.project_path / "pixi.toml").exists() or (self.project_path / "pixi.lock").exists():
            detected.append("pixi")

        # Check for conda (environment.yml, conda-lock.yml)
        if (self.project_path / "environment.yml").exists() or (
            self.project_path / "conda-lock.yml"
        ).exists():
            detected.append("conda")

        return detected or ["pip"]  # Default to pip if nothing detected

    def scan_pip_dependencies(self) -> list[DependencyInfo]:
        """Scan pip dependencies for the project.

        Returns:
            List of dependency information from pip.
        """
        dependencies = []

        try:
            # Use pip-audit to get vulnerability information
            result = subprocess.run(
                ["pip-audit", "--format=json", "--progress-spinner=off"],
                cwd=self.project_path,
                capture_output=True,
                text=True,
                timeout=300,
            )

            if result.returncode == 0:
                audit_data = json.loads(result.stdout)
                dependencies.extend(self._parse_pip_audit_output(audit_data))
            else:
                print(f"Warning: pip-audit failed with return code {result.returncode}")
                print(f"Error: {result.stderr}")

        except subprocess.TimeoutExpired:
            print("Warning: pip-audit scan timed out")
        except FileNotFoundError:
            print("Warning: pip-audit not found, using pip list instead")
            dependencies.extend(self._scan_pip_fallback())
        except Exception as e:
            print(f"Warning: pip-audit scan failed: {e}")
            dependencies.extend(self._scan_pip_fallback())

        return dependencies

    def _scan_pip_fallback(self) -> list[DependencyInfo]:
        """Fallback method to scan pip dependencies without vulnerability info.

        Returns:
            List of dependency information without vulnerability data.
        """
        dependencies = []

        try:
            result = subprocess.run(
                ["pip", "list", "--format=json"],
                cwd=self.project_path,
                capture_output=True,
                text=True,
                timeout=60,
            )

            if result.returncode == 0:
                pip_data = json.loads(result.stdout)
                for package in pip_data:
                    dep = DependencyInfo(
                        name=package["name"],
                        version=package["version"],
                        package_manager="pip",
                        vulnerabilities=[],  # No vulnerability data in fallback
                    )
                    dependencies.append(dep)

        except Exception as e:
            print(f"Warning: pip list fallback failed: {e}")

        return dependencies

    def scan_pixi_dependencies(self) -> list[DependencyInfo]:
        """Scan pixi dependencies for the project.

        Returns:
            List of dependency information from pixi.
        """
        dependencies = []

        try:
            # Get pixi environment information
            result = subprocess.run(
                ["pixi", "list", "--json"],
                cwd=self.project_path,
                capture_output=True,
                text=True,
                timeout=60,
            )

            if result.returncode == 0:
                pixi_data = json.loads(result.stdout)
                dependencies.extend(self._parse_pixi_output(pixi_data))
            else:
                print(f"Warning: pixi list failed with return code {result.returncode}")

        except subprocess.TimeoutExpired:
            print("Warning: pixi list timed out")
        except FileNotFoundError:
            print("Warning: pixi not found")
        except Exception as e:
            print(f"Warning: pixi scan failed: {e}")

        return dependencies

    def scan_dependencies(self, package_managers: list[str] | None = None) -> list[DependencyInfo]:
        """Scan dependencies for specified package managers.

        Args:
            package_managers: List of package managers to scan. If None, auto-detect.

        Returns:
            List of all dependency information.
        """
        if package_managers is None:
            package_managers = self.detect_package_managers()

        all_dependencies = []

        for pm in package_managers:
            if pm == "pip":
                all_dependencies.extend(self.scan_pip_dependencies())
            elif pm == "pixi":
                all_dependencies.extend(self.scan_pixi_dependencies())
            elif pm == "conda":
                # For now, conda scanning follows similar pattern to pixi
                # In practice, you might integrate with conda-audit or similar tools
                print("Warning: conda scanning not fully implemented")

        return all_dependencies

    def _parse_pip_audit_output(self, audit_data: dict[str, Any]) -> list[DependencyInfo]:
        """Parse pip-audit JSON output into DependencyInfo objects.

        Args:
            audit_data: JSON data from pip-audit.

        Returns:
            List of dependency information.
        """
        dependencies = []

        # pip-audit output format: {"dependencies": [...]}
        for dep_data in audit_data.get("dependencies", []):
            vulnerabilities = []

            # Parse vulnerabilities if present
            for vuln_data in dep_data.get("vulns", []):
                vuln = VulnerabilityInfo(
                    id=vuln_data.get("id", ""),
                    package_name=dep_data.get("name", ""),
                    package_version=dep_data.get("version", ""),
                    severity=self._normalize_severity(vuln_data.get("severity", "unknown")),
                    description=vuln_data.get("description", ""),
                    fix_versions=vuln_data.get("fix_versions", []),
                    aliases=vuln_data.get("aliases", []),
                    advisory_url=vuln_data.get("advisory_url"),
                )
                vulnerabilities.append(vuln)

            dep = DependencyInfo(
                name=dep_data.get("name", ""),
                version=dep_data.get("version", ""),
                package_manager="pip",
                vulnerabilities=vulnerabilities,
            )
            dependencies.append(dep)

        return dependencies

    def _parse_pixi_output(self, pixi_data: dict[str, Any]) -> list[DependencyInfo]:
        """Parse pixi list JSON output into DependencyInfo objects.

        Args:
            pixi_data: JSON data from pixi list.

        Returns:
            List of dependency information.
        """
        dependencies = []

        # Note: pixi list format may vary, adjust based on actual output
        for _env_name, env_data in pixi_data.items():
            if isinstance(env_data, dict) and "dependencies" in env_data:
                for dep_name, dep_info in env_data["dependencies"].items():
                    dep = DependencyInfo(
                        name=dep_name,
                        version=dep_info.get("version", "unknown"),
                        package_manager="pixi",
                        source=dep_info.get("channel"),
                        dependencies=dep_info.get("depends", []),
                    )
                    dependencies.append(dep)

        return dependencies

    def _normalize_severity(self, severity: str) -> str:
        """Normalize severity levels to standard values.

        Args:
            severity: Raw severity string.

        Returns:
            Normalized severity (low, medium, high, critical).
        """
        severity_lower = severity.lower().strip()

        if severity_lower in ["low", "minor"]:
            return "low"
        elif severity_lower in ["medium", "moderate"]:
            return "medium"
        elif severity_lower in ["high", "major"]:
            return "high"
        elif severity_lower in ["critical", "severe"]:
            return "critical"
        else:
            return "medium"  # Default to medium for unknown

    def generate_dependency_tree(self) -> dict[str, Any]:
        """Generate a dependency tree structure.

        Returns:
            Dictionary representing the dependency tree.
        """
        package_managers = self.detect_package_managers()
        dependencies = self.scan_dependencies(package_managers)

        # Calculate package manager distribution
        pm_distribution: dict[str, int] = {}
        for dep in dependencies:
            pm = dep.package_manager
            pm_distribution[pm] = pm_distribution.get(pm, 0) + 1

        # Build dependency tree
        tree = {
            "project_path": str(self.project_path),
            "package_managers": package_managers,
            "scan_time": time.time(),
            "dependencies": {dep.name: dep.to_dict() for dep in dependencies},
            "summary": {
                "total_dependencies": len(dependencies),
                "vulnerable_dependencies": len([d for d in dependencies if d.has_vulnerabilities]),
                "package_manager_distribution": pm_distribution,
            },
        }

        return tree
