"""Command line interface for security scanning and vulnerability assessment."""

import argparse
import json
import sys

from .collector import SecurityCollector
from .sbom_generator import SBOMGenerator


def scan_command(args: argparse.Namespace) -> None:
    """Execute security scan command."""
    collector = SecurityCollector(args.storage_path)

    print(f"Starting security scan of {args.project_path}")

    try:
        # Perform security scan
        metrics = collector.scan_project_security(
            project_path=args.project_path,
            build_id=args.build_id,
            package_managers=args.package_managers,
        )

        # Save metrics
        metrics_file = collector.save_metrics(metrics)
        print(f"Security scan completed. Metrics saved to: {metrics_file}")

        # Print summary
        stats = metrics.calculate_summary_stats()
        print("\nScan Summary:")
        print(f"  Total dependencies: {stats.get('total_dependencies', 0)}")
        print(f"  Vulnerable dependencies: {stats.get('vulnerable_dependencies', 0)}")
        print(f"  Total vulnerabilities: {stats.get('total_vulnerabilities', 0)}")
        print(f"  Vulnerability rate: {stats.get('vulnerability_rate', 0)}%")

        if stats.get("vulnerabilities_by_severity"):
            print("\nVulnerabilities by severity:")
            for severity, count in stats["vulnerabilities_by_severity"].items():
                if count > 0:
                    print(f"  {severity.title()}: {count}")

        # Save baseline if requested
        if args.save_baseline:
            baseline_file = collector.save_baseline(metrics, args.baseline_name)
            print(f"Baseline saved to: {baseline_file}")

        # Compare with baseline if requested
        comparison = None
        if args.compare_baseline:
            comparison = collector.compare_with_baseline(metrics, args.baseline_name)
            if comparison:
                print(f"\nBaseline comparison (vs {args.baseline_name}):")
                for key, change_data in comparison.get("changes", {}).items():
                    if "change" in change_data:
                        change = change_data["change"]
                        if change != 0:
                            direction = "increased" if change > 0 else "decreased"
                            print(f"  {key}: {direction} by {abs(change)}")

                new_vulns = comparison.get("new_vulnerabilities", [])
                resolved_vulns = comparison.get("resolved_vulnerabilities", [])

                if new_vulns:
                    print(f"  New vulnerabilities: {len(new_vulns)}")
                if resolved_vulns:
                    print(f"  Resolved vulnerabilities: {len(resolved_vulns)}")
            else:
                print(f"No baseline '{args.baseline_name}' found for comparison")

        # Generate output file if requested
        if args.output:
            output_data = metrics.to_dict()
            if args.compare_baseline and comparison:
                output_data["baseline_comparison"] = comparison

            with open(args.output, "w", encoding="utf-8") as f:
                json.dump(output_data, f, indent=2, default=str)
            print(f"Results saved to: {args.output}")

    except Exception as e:
        print(f"Error during security scan: {e}")
        sys.exit(1)


def report_command(args: argparse.Namespace) -> None:
    """Execute security report generation command."""
    collector = SecurityCollector(args.storage_path)

    print(f"Generating security report for {args.project_path}")

    try:
        # Generate comprehensive report
        collector.generate_security_report(
            project_path=args.project_path,
            output_path=args.output,
            include_baseline_comparison=args.include_baseline,
            baseline_name=args.baseline_name,
        )

        print("Security report generated successfully")

        if args.output:
            print(f"Report saved to: {args.output}")

        # Generate GitHub summary if requested
        if args.github_summary:
            # Note: GitHub reporter integration removed to avoid cross-module dependencies
            # Framework modules should be self-contained
            print("GitHub summary generation disabled in framework version")

    except Exception as e:
        print(f"Error generating security report: {e}")
        sys.exit(1)


def list_command(args: argparse.Namespace) -> None:
    """Execute list metrics command."""
    collector = SecurityCollector(args.storage_path)

    metrics_files = collector.list_saved_metrics()

    if not metrics_files:
        print("No saved security metrics found")
        return

    print(f"Found {len(metrics_files)} security scan results:")
    print()

    for metrics in metrics_files:
        timestamp = metrics.get("timestamp", "Unknown")
        build_id = metrics.get("build_id", "Unknown")
        total_deps = metrics.get("total_dependencies", 0)
        vulnerable_deps = metrics.get("vulnerable_dependencies", 0)

        print(f"Build ID: {build_id}")
        print(f"  Timestamp: {timestamp}")
        print(f"  Dependencies: {total_deps} total, {vulnerable_deps} vulnerable")
        print(f"  File: {metrics.get('file_path', 'Unknown')}")
        print()


def sbom_command(args: argparse.Namespace) -> None:
    """Execute SBOM generation command."""
    generator = SBOMGenerator()

    print(f"Generating SBOM for {args.project_path}")

    try:
        # Generate SBOM
        sbom_data = generator.generate_sbom(
            output_format=args.format,
            output_type=args.output_type,
            include_dev_dependencies=args.include_dev,
            include_vulnerabilities=args.include_vulns,
        )

        # Save SBOM to file
        if args.output:
            output_path = generator.save_sbom(
                sbom_data=sbom_data,
                output_path=args.output,
                output_format=args.format,
                output_type=args.output_type,
            )
            print(f"SBOM saved to: {output_path}")
        else:
            # Print to stdout if no output file specified
            if args.output_type == "json":
                print(json.dumps(sbom_data, indent=2, ensure_ascii=False))
            else:
                print("Output file required for non-JSON formats")

        # Print summary
        if args.format == "cyclonedx":
            component_count = len(sbom_data.get("components", []))
            vuln_count = len(sbom_data.get("vulnerabilities", []))
            print("\nSBOM Summary (CycloneDX):")
            print(f"  Components: {component_count}")
            if args.include_vulns:
                print(f"  Vulnerabilities: {vuln_count}")
        elif args.format == "spdx":
            package_count = len(sbom_data.get("packages", [])) - 1  # Exclude root package
            print("\nSBOM Summary (SPDX):")
            print(f"  Packages: {package_count}")

    except Exception as e:
        print(f"Error generating SBOM: {e}")
        sys.exit(1)


def vulnerability_report_command(args: argparse.Namespace) -> None:
    """Execute vulnerability report generation command."""
    generator = SBOMGenerator()

    print(f"Generating vulnerability report for {args.project_path}")

    try:
        # Generate vulnerability report
        report = generator.generate_vulnerability_report(
            output_path=args.output,
            include_fix_recommendations=args.include_fixes,
        )

        # Print summary
        summary = report["summary"]
        print("\nVulnerability Report Summary:")
        print(f"  Total dependencies: {summary['total_dependencies']}")
        print(f"  Vulnerable dependencies: {summary['vulnerable_dependencies']}")
        print(f"  Total vulnerabilities: {summary['total_vulnerabilities']}")

        if summary["severity_breakdown"]:
            print("\nVulnerabilities by severity:")
            for severity, count in summary["severity_breakdown"].items():
                if count > 0:
                    print(f"  {severity.title()}: {count}")

        if args.include_fixes and report["recommendations"]:
            print(f"\nRecommendations: {len(report['recommendations'])}")

        if args.output:
            print(f"Full report saved to: {args.output}")

    except Exception as e:
        print(f"Error generating vulnerability report: {e}")
        sys.exit(1)


def compliance_command(args: argparse.Namespace) -> None:
    """Execute compliance report generation command."""
    generator = SBOMGenerator()

    frameworks = args.frameworks or ["NIST", "SOX", "GDPR", "HIPAA"]
    print(f"Generating compliance report for {args.project_path}")
    print(f"Frameworks: {', '.join(frameworks)}")

    try:
        # Generate compliance report
        report = generator.generate_compliance_report(
            compliance_frameworks=frameworks,
            output_path=args.output,
        )

        # Print compliance status
        print("\nCompliance Status:")
        for framework, status in report["compliance_status"].items():
            level = status["compliance_level"]
            risk_score = status["risk_score"]
            print(f"  {framework}: {level.upper()} (Risk Score: {risk_score})")

        # Print findings summary
        if report["findings"]:
            print(f"\nFindings: {len(report['findings'])}")
            for finding in report["findings"]:
                print(f"  - {finding['description']} ({finding['severity']})")

        if args.output:
            print(f"Full compliance report saved to: {args.output}")

    except Exception as e:
        print(f"Error generating compliance report: {e}")
        sys.exit(1)


def main() -> None:
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Security scanning and vulnerability assessment tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    # Global arguments
    parser.add_argument(
        "--storage-path",
        type=str,
        default="security_data",
        help="Path to store security data (default: security_data)",
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Scan command
    scan_parser = subparsers.add_parser("scan", help="Perform security scan of a project")
    scan_parser.add_argument("project_path", type=str, help="Path to the project to scan")
    scan_parser.add_argument("--build-id", type=str, help="Unique identifier for this scan")
    scan_parser.add_argument(
        "--package-managers",
        nargs="+",
        choices=["pip", "pixi", "conda"],
        help="Package managers to scan (auto-detected if not specified)",
    )
    scan_parser.add_argument("--output", "-o", type=str, help="Output file for scan results")
    scan_parser.add_argument(
        "--save-baseline",
        action="store_true",
        help="Save scan results as baseline for future comparisons",
    )
    scan_parser.add_argument(
        "--compare-baseline",
        action="store_true",
        help="Compare scan results with existing baseline",
    )
    scan_parser.add_argument(
        "--baseline-name",
        type=str,
        default="default",
        help="Name of baseline to save/compare (default: default)",
    )

    # Report command
    report_parser = subparsers.add_parser("report", help="Generate comprehensive security report")
    report_parser.add_argument("project_path", type=str, help="Path to the project to analyze")
    report_parser.add_argument("--output", "-o", type=str, help="Output file for the report")
    report_parser.add_argument(
        "--include-baseline",
        action="store_true",
        help="Include baseline comparison in report",
    )
    report_parser.add_argument(
        "--baseline-name",
        type=str,
        default="default",
        help="Name of baseline to compare against (default: default)",
    )
    report_parser.add_argument(
        "--github-summary",
        action="store_true",
        help="Generate GitHub Actions step summary (disabled in framework version)",
    )

    # List command
    subparsers.add_parser("list", help="List saved security scan results")

    # SBOM command
    sbom_parser = subparsers.add_parser("sbom", help="Generate Software Bill of Materials")
    sbom_parser.add_argument("project_path", type=str, help="Path to the project to analyze")
    sbom_parser.add_argument(
        "--format",
        choices=["cyclonedx", "spdx"],
        default="cyclonedx",
        help="SBOM format (default: cyclonedx)",
    )
    sbom_parser.add_argument(
        "--output-type",
        choices=["json", "xml", "yaml"],
        default="json",
        help="Output file type (default: json)",
    )
    sbom_parser.add_argument("--output", "-o", type=str, help="Output file for SBOM")
    sbom_parser.add_argument(
        "--include-dev", action="store_true", help="Include development dependencies"
    )
    sbom_parser.add_argument(
        "--include-vulns",
        action="store_true",
        default=True,
        help="Include vulnerability information (default: True)",
    )

    # Vulnerability report command
    vuln_parser = subparsers.add_parser("vulnerabilities", help="Generate vulnerability report")
    vuln_parser.add_argument("project_path", type=str, help="Path to the project to analyze")
    vuln_parser.add_argument(
        "--output", "-o", type=str, help="Output file for vulnerability report"
    )
    vuln_parser.add_argument(
        "--include-fixes",
        action="store_true",
        default=True,
        help="Include fix recommendations (default: True)",
    )

    # Compliance command
    compliance_parser = subparsers.add_parser("compliance", help="Generate compliance report")
    compliance_parser.add_argument("project_path", type=str, help="Path to the project to analyze")
    compliance_parser.add_argument(
        "--output", "-o", type=str, help="Output file for compliance report"
    )
    compliance_parser.add_argument(
        "--frameworks",
        nargs="+",
        choices=["NIST", "SOX", "GDPR", "HIPAA"],
        help="Compliance frameworks to assess (default: all)",
    )

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    # Execute command
    if args.command == "scan":
        scan_command(args)
    elif args.command == "report":
        report_command(args)
    elif args.command == "list":
        list_command(args)
    elif args.command == "sbom":
        sbom_command(args)
    elif args.command == "vulnerabilities":
        vulnerability_report_command(args)
    elif args.command == "compliance":
        compliance_command(args)


if __name__ == "__main__":
    main()
