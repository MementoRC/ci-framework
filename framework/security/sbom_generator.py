"""SBOM (Software Bill of Materials) generation functionality."""

import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Literal

import yaml  # type: ignore[import-untyped]

from .analyzer import DependencyAnalyzer
from .models import DependencyInfo


class SBOMGenerator:
    """Generates Software Bill of Materials in multiple formats."""

    def __init__(self, dependency_analyzer: DependencyAnalyzer | None = None):
        """Initialize the SBOM generator.

        Args:
            dependency_analyzer: DependencyAnalyzer instance. Created if None.
        """
        self.dependency_analyzer = dependency_analyzer or DependencyAnalyzer(".")
        self.supported_formats = ["cyclonedx", "spdx"]

    def generate_sbom(
        self,
        output_format: Literal["cyclonedx", "spdx"] = "cyclonedx",
        output_type: Literal["json", "xml", "yaml"] = "json",
        include_dev_dependencies: bool = True,
        include_vulnerabilities: bool = True,
    ) -> dict[str, Any]:
        """Generate SBOM in specified format.

        Args:
            output_format: SBOM format (cyclonedx or spdx).
            output_type: Output type (json, xml, yaml).
            include_dev_dependencies: Whether to include dev dependencies.
            include_vulnerabilities: Whether to include vulnerability information.

        Returns:
            SBOM data structure.

        Raises:
            ValueError: If unsupported format or output type specified.
        """
        if output_format not in self.supported_formats:
            raise ValueError(f"Unsupported SBOM format: {output_format}")

        # Validate output type for format
        if output_format == "cyclonedx" and output_type not in ["json", "xml"]:
            raise ValueError(f"CycloneDX supports json and xml, not {output_type}")
        elif output_format == "spdx" and output_type not in ["json", "yaml"]:
            raise ValueError(f"SPDX supports json and yaml, not {output_type}")

        # Scan dependencies
        dependencies = self.dependency_analyzer.scan_dependencies()

        # Generate SBOM based on format
        if output_format == "cyclonedx":
            return self._generate_cyclonedx(
                dependencies, include_dev_dependencies, include_vulnerabilities
            )
        elif output_format == "spdx":
            return self._generate_spdx(
                dependencies, include_dev_dependencies, include_vulnerabilities
            )
        else:
            raise ValueError(f"Unsupported SBOM format: {output_format}")

    def _generate_cyclonedx(
        self,
        dependencies: list[DependencyInfo],
        include_dev_dependencies: bool,
        include_vulnerabilities: bool,
    ) -> dict[str, Any]:
        """Generate CycloneDX 1.4 format SBOM.

        Args:
            dependencies: List of dependency information.
            include_dev_dependencies: Whether to include dev dependencies.
            include_vulnerabilities: Whether to include vulnerability information.

        Returns:
            CycloneDX SBOM structure.
        """
        # CycloneDX 1.4 structure
        sbom: dict[str, Any] = {
            "bomFormat": "CycloneDX",
            "specVersion": "1.4",
            "serialNumber": f"urn:uuid:{uuid.uuid4()}",
            "version": 1,
            "metadata": {
                "timestamp": datetime.now().isoformat() + "Z",
                "tools": [
                    {
                        "vendor": "hb-strategy-sandbox",
                        "name": "SBOMGenerator",
                        "version": "1.0.0",
                    }
                ],
                "component": {
                    "type": "application",
                    "bom-ref": str(self.dependency_analyzer.project_path),
                    "name": self.dependency_analyzer.project_path.name,
                    "version": "unknown",
                    "description": "Hummingbot strategy testing and simulation sandbox",
                },
            },
            "components": [],
        }

        # Add vulnerability data if requested
        if include_vulnerabilities:
            sbom["vulnerabilities"] = []

        # Process dependencies
        for dep in dependencies:
            # Filter dev dependencies if not included
            if not include_dev_dependencies and self._is_dev_dependency(dep):
                continue

            component = {
                "type": "library",
                "bom-ref": f"{dep.package_manager}:{dep.name}@{dep.version}",
                "name": dep.name,
                "version": dep.version,
                "scope": "required",
                "hashes": [],
                "licenses": [],
                "purl": self._generate_purl(dep),
                "externalReferences": [],
            }

            # Add license information if available
            if dep.license:
                component["licenses"].append({"license": {"name": dep.license}})  # type: ignore[attr-defined]

            # Add source information
            if dep.source:
                component["externalReferences"].append(  # type: ignore[attr-defined]
                    {
                        "type": "distribution",
                        "url": dep.source,
                    }
                )

            # Add package manager metadata
            component["properties"] = [
                {"name": "package_manager", "value": dep.package_manager},  # type: ignore[list-item]
            ]

            # Add dependency relationships
            if dep.dependencies:
                component["dependencies"] = [
                    f"{dep.package_manager}:{dep_name}@unknown" for dep_name in dep.dependencies
                ]

            sbom["components"].append(component)

            # Add vulnerabilities
            if include_vulnerabilities and dep.vulnerabilities:
                for vuln in dep.vulnerabilities:
                    vulnerability = {
                        "bom-ref": f"vuln-{vuln.id}",
                        "id": vuln.id,
                        "source": {
                            "name": "pip-audit" if dep.package_manager == "pip" else "unknown",
                        },
                        "ratings": [
                            {
                                "source": {"name": "CVSS"},
                                "severity": vuln.severity.upper(),
                            }
                        ],
                        "description": vuln.description,
                        "detail": vuln.description,
                        "affects": [
                            {
                                "ref": f"{dep.package_manager}:{dep.name}@{dep.version}",
                                "versions": [
                                    {
                                        "version": dep.version,
                                        "status": "affected",
                                    }
                                ],
                            }
                        ],
                    }

                    # Add advisory URL if available
                    if vuln.advisory_url:
                        vulnerability["advisories"] = [{"url": vuln.advisory_url}]

                    # Add fix versions
                    if vuln.fix_versions:
                        vulnerability["recommendations"] = [
                            f"Upgrade to version {ver}" for ver in vuln.fix_versions
                        ]

                    sbom["vulnerabilities"].append(vulnerability)

        return sbom

    def _generate_spdx(
        self,
        dependencies: list[DependencyInfo],
        include_dev_dependencies: bool,
        include_vulnerabilities: bool,
    ) -> dict[str, Any]:
        """Generate SPDX 2.3 format SBOM.

        Args:
            dependencies: List of dependency information.
            include_dev_dependencies: Whether to include dev dependencies.
            include_vulnerabilities: Whether to include vulnerability information.

        Returns:
            SPDX SBOM structure.
        """
        # SPDX 2.3 structure
        document_id = f"SPDXRef-DOCUMENT-{uuid.uuid4().hex[:8]}"

        sbom: dict[str, Any] = {
            "spdxVersion": "SPDX-2.3",
            "dataLicense": "CC0-1.0",
            "SPDXID": document_id,
            "name": f"{self.dependency_analyzer.project_path.name}-SBOM",
            "documentNamespace": f"https://hb-strategy-sandbox/{document_id}",
            "creationInfo": {
                "created": datetime.now().isoformat() + "Z",
                "creators": ["Tool: hb-strategy-sandbox-SBOMGenerator-1.0.0"],
                "licenseListVersion": "3.21",
            },
            "packages": [],
            "relationships": [],
        }

        # Root package
        root_package = {
            "SPDXID": "SPDXRef-Package-Root",
            "name": self.dependency_analyzer.project_path.name,
            "downloadLocation": "NOASSERTION",
            "filesAnalyzed": False,
            "copyrightText": "NOASSERTION",
            "versionInfo": "unknown",
        }
        sbom["packages"].append(root_package)

        # Process dependencies
        for i, dep in enumerate(dependencies):
            # Filter dev dependencies if not included
            if not include_dev_dependencies and self._is_dev_dependency(dep):
                continue

            package_id = f"SPDXRef-Package-{dep.name}-{i}"

            package = {
                "SPDXID": package_id,
                "name": dep.name,
                "versionInfo": dep.version,
                "downloadLocation": dep.source or "NOASSERTION",
                "filesAnalyzed": False,
                "copyrightText": "NOASSERTION",
                "supplier": "NOASSERTION",
            }

            # Add license information
            if dep.license:
                package["licenseConcluded"] = dep.license
                package["licenseDeclared"] = dep.license
            else:
                package["licenseConcluded"] = "NOASSERTION"
                package["licenseDeclared"] = "NOASSERTION"

            # Add external references
            if dep.source:
                package["externalRefs"] = [
                    {
                        "referenceCategory": "PACKAGE-MANAGER",
                        "referenceType": "purl",
                        "referenceLocator": self._generate_purl(dep),
                    }
                ]

            # Add package manager annotation
            if "annotations" not in sbom:
                sbom["annotations"] = []

            sbom["annotations"].append(
                {
                    "spdxId": package_id,
                    "annotationType": "OTHER",
                    "annotator": "Tool: SBOMGenerator",
                    "annotationDate": datetime.now().isoformat() + "Z",
                    "annotationComment": f"Package manager: {dep.package_manager}",
                }
            )

            sbom["packages"].append(package)

            # Add relationship to root
            sbom["relationships"].append(
                {
                    "spdxElementId": "SPDXRef-Package-Root",
                    "relationshipType": "DEPENDS_ON",
                    "relatedSpdxElement": package_id,
                }
            )

            # Add dependency relationships
            for dep_name in dep.dependencies:
                # Find dependency package ID (simplified for now)
                dep_package_id = f"SPDXRef-Package-{dep_name}"
                sbom["relationships"].append(
                    {
                        "spdxElementId": package_id,
                        "relationshipType": "DEPENDS_ON",
                        "relatedSpdxElement": dep_package_id,
                    }
                )

        # Add vulnerability information as annotations if requested
        if include_vulnerabilities:
            for dep in dependencies:
                if dep.vulnerabilities:
                    package_id = f"SPDXRef-Package-{dep.name}"
                    for vuln in dep.vulnerabilities:
                        sbom["annotations"].append(
                            {
                                "spdxId": package_id,
                                "annotationType": "OTHER",
                                "annotator": "Tool: SBOMGenerator",
                                "annotationDate": datetime.now().isoformat() + "Z",
                                "annotationComment": f"Vulnerability: {vuln.id} ({vuln.severity}) - {vuln.description}",
                            }
                        )

        return sbom

    def _generate_purl(self, dependency: DependencyInfo) -> str:
        """Generate Package URL (PURL) for a dependency.

        Args:
            dependency: Dependency information.

        Returns:
            Package URL string.
        """
        # Generate PURL based on package manager
        if dependency.package_manager == "pip":
            return f"pkg:pypi/{dependency.name}@{dependency.version}"
        elif dependency.package_manager == "pixi":
            # Pixi uses conda packages
            return f"pkg:conda/{dependency.name}@{dependency.version}"
        elif dependency.package_manager == "conda":
            return f"pkg:conda/{dependency.name}@{dependency.version}"
        else:
            return f"pkg:generic/{dependency.name}@{dependency.version}"

    def _is_dev_dependency(self, dependency: DependencyInfo) -> bool:
        """Check if a dependency is a development dependency.

        Args:
            dependency: Dependency information.

        Returns:
            True if it's a development dependency.
        """
        # Common development dependency patterns
        dev_patterns = [
            "test",
            "pytest",
            "mock",
            "coverage",
            "lint",
            "ruff",
            "mypy",
            "pre-commit",
            "black",
            "flake8",
            "isort",
            "bandit",
            "safety",
            "sphinx",
            "mkdocs",
            "jupyter",
            "notebook",
            "ipython",
        ]

        name_lower = dependency.name.lower()
        return any(pattern in name_lower for pattern in dev_patterns)

    def save_sbom(
        self,
        sbom_data: dict[str, Any],
        output_path: str | Path,
        output_format: Literal["cyclonedx", "spdx"] = "cyclonedx",
        output_type: Literal["json", "xml", "yaml"] = "json",
    ) -> Path:
        """Save SBOM to file.

        Args:
            sbom_data: SBOM data structure.
            output_path: Path to save the SBOM file.
            output_format: SBOM format for validation.
            output_type: Output file type.

        Returns:
            Path to the saved file.

        Raises:
            ValueError: If unsupported output type for format.
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        if output_type == "json":
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(sbom_data, f, indent=2, ensure_ascii=False)
        elif output_type == "yaml":
            if output_format != "spdx":
                raise ValueError("YAML output only supported for SPDX format")
            with open(output_path, "w", encoding="utf-8") as f:
                yaml.safe_dump(sbom_data, f, default_flow_style=False, allow_unicode=True)
        elif output_type == "xml":
            if output_format != "cyclonedx":
                raise ValueError("XML output only supported for CycloneDX format")
            # For XML output, we'd need to convert the dict to XML
            # This is a simplified implementation
            xml_content = self._dict_to_xml(sbom_data, "bom")
            with open(output_path, "w", encoding="utf-8") as f:
                f.write('<?xml version="1.0" encoding="UTF-8"?>\n')
                f.write(xml_content)
        else:
            raise ValueError(f"Unsupported output type: {output_type}")

        return output_path

    def _dict_to_xml(self, data: dict[str, Any], root_tag: str) -> str:
        """Convert dictionary to simple XML representation.

        Args:
            data: Dictionary to convert.
            root_tag: Root XML tag name.

        Returns:
            XML string representation.
        """

        # Simplified XML conversion - in production, use proper XML library
        def _to_xml(obj: Any, tag: str) -> str:
            if isinstance(obj, dict):
                content = ""
                for key, value in obj.items():
                    content += _to_xml(value, key)
                return f"<{tag}>{content}</{tag}>"
            elif isinstance(obj, list):
                content = ""
                for item in obj:
                    content += _to_xml(item, tag[:-1] if tag.endswith("s") else "item")
                return content
            else:
                return f"<{tag}>{str(obj)}</{tag}>"

        return _to_xml(data, root_tag)

    def generate_vulnerability_report(
        self,
        output_path: str | Path | None = None,
        include_fix_recommendations: bool = True,
    ) -> dict[str, Any]:
        """Generate detailed vulnerability report based on dependency scan.

        Args:
            output_path: Path to save the report. Not saved if None.
            include_fix_recommendations: Whether to include fix recommendations.

        Returns:
            Vulnerability report data.
        """
        dependencies = self.dependency_analyzer.scan_dependencies()

        # Build vulnerability report
        report = {
            "report_type": "vulnerability_analysis",
            "generated_at": datetime.now().isoformat(),
            "project_path": str(self.dependency_analyzer.project_path),
            "summary": {
                "total_dependencies": len(dependencies),
                "vulnerable_dependencies": len([d for d in dependencies if d.has_vulnerabilities]),
                "total_vulnerabilities": sum(len(d.vulnerabilities) for d in dependencies),
                "severity_breakdown": {"low": 0, "medium": 0, "high": 0, "critical": 0},
            },
            "vulnerable_packages": [],
            "recommendations": [],
        }

        # Process vulnerable dependencies
        for dep in dependencies:
            if not dep.has_vulnerabilities:
                continue

            package_info = {
                "name": dep.name,
                "version": dep.version,
                "package_manager": dep.package_manager,
                "vulnerabilities": [],
            }

            for vuln in dep.vulnerabilities:
                # Update severity breakdown
                severity = vuln.severity.lower()
                if severity in report["summary"]["severity_breakdown"]:  # type: ignore[index]
                    report["summary"]["severity_breakdown"][severity] += 1  # type: ignore[index]

                vuln_info = {
                    "id": vuln.id,
                    "severity": vuln.severity,
                    "description": vuln.description,
                    "aliases": vuln.aliases,
                    "advisory_url": vuln.advisory_url,
                }

                if include_fix_recommendations and vuln.fix_versions:
                    vuln_info["fix_versions"] = vuln.fix_versions

                    # Add to recommendations
                    recommendation = f"Update {dep.name} from {dep.version} to {vuln.fix_versions[0]} to fix {vuln.id}"
                    if recommendation not in report["recommendations"]:
                        report["recommendations"].append(recommendation)  # type: ignore[attr-defined]

                package_info["vulnerabilities"].append(vuln_info)  # type: ignore[attr-defined]

            report["vulnerable_packages"].append(package_info)  # type: ignore[attr-defined]

        # Save report if path provided
        if output_path:
            output_path = Path(output_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)

            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(report, f, indent=2, ensure_ascii=False)

        return report

    def generate_compliance_report(
        self,
        compliance_frameworks: list[str] | None = None,
        output_path: str | Path | None = None,
    ) -> dict[str, Any]:
        """Generate compliance status report.

        Args:
            compliance_frameworks: List of frameworks to check (e.g., ['NIST', 'SOX']).
            output_path: Path to save the report.

        Returns:
            Compliance report data.
        """
        if compliance_frameworks is None:
            compliance_frameworks = ["NIST", "SOX", "GDPR", "HIPAA"]

        dependencies = self.dependency_analyzer.scan_dependencies()

        report = {
            "report_type": "compliance_analysis",
            "generated_at": datetime.now().isoformat(),
            "project_path": str(self.dependency_analyzer.project_path),
            "frameworks": compliance_frameworks,
            "compliance_status": {},
            "findings": [],
            "recommendations": [],
        }

        # Analyze compliance for each framework
        for framework in compliance_frameworks:
            status = self._assess_compliance_framework(dependencies, framework)
            report["compliance_status"][framework] = status  # type: ignore[index]

        # General compliance findings
        vulnerable_count = len([d for d in dependencies if d.has_vulnerabilities])
        if vulnerable_count > 0:
            report["findings"].append(  # type: ignore[attr-defined]
                {
                    "type": "security",
                    "severity": "high",
                    "description": f"Found {vulnerable_count} dependencies with known vulnerabilities",
                    "affected_frameworks": compliance_frameworks,
                }
            )

        # License compliance
        unlicensed_count = len([d for d in dependencies if not d.license])
        if unlicensed_count > 0:
            report["findings"].append(  # type: ignore[attr-defined]
                {
                    "type": "license",
                    "severity": "medium",
                    "description": f"Found {unlicensed_count} dependencies without license information",
                    "affected_frameworks": ["GDPR", "SOX"],
                }
            )

        # Add recommendations
        if vulnerable_count > 0:
            report["recommendations"].append("Address all known vulnerabilities in dependencies")  # type: ignore[attr-defined]
        if unlicensed_count > 0:
            report["recommendations"].append("Document license information for all dependencies")  # type: ignore[attr-defined]

        # Save report if path provided
        if output_path:
            output_path = Path(output_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)

            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(report, f, indent=2, ensure_ascii=False)

        return report

    def _assess_compliance_framework(
        self, dependencies: list[DependencyInfo], framework: str
    ) -> dict[str, Any]:
        """Assess compliance for a specific framework.

        Args:
            dependencies: List of dependencies to assess.
            framework: Compliance framework name.

        Returns:
            Compliance assessment for the framework.
        """
        # Simplified compliance assessment
        vulnerable_deps = [d for d in dependencies if d.has_vulnerabilities]
        unlicensed_deps = [d for d in dependencies if not d.license]

        # Framework-specific assessment
        if framework == "NIST":
            # NIST focuses on cybersecurity
            risk_score = min(100, len(vulnerable_deps) * 10)
            compliance_level = "high" if risk_score < 20 else "medium" if risk_score < 50 else "low"
        elif framework == "SOX":
            # SOX focuses on financial controls
            risk_score = min(100, (len(vulnerable_deps) + len(unlicensed_deps)) * 8)
            compliance_level = "high" if risk_score < 25 else "medium" if risk_score < 60 else "low"
        else:
            # Generic assessment
            risk_score = min(100, len(vulnerable_deps) * 12)
            compliance_level = "high" if risk_score < 30 else "medium" if risk_score < 70 else "low"

        return {
            "compliance_level": compliance_level,
            "risk_score": risk_score,
            "vulnerable_dependencies": len(vulnerable_deps),
            "unlicensed_dependencies": len(unlicensed_deps),
            "assessment_date": datetime.now().isoformat(),
        }
