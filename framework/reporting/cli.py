"""Command-line interface for GitHub reporting integration."""

import argparse
import json
import sys

from .github_reporter import GitHubReporter


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(description="GitHub Actions reporting and step summary tool")

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Build status command
    build_parser = subparsers.add_parser("build-status", help="Generate build status report")
    build_parser.add_argument(
        "--status",
        choices=["success", "failure", "warning"],
        default="success",
        help="Build status (default: success)",
    )
    build_parser.add_argument("--test-results", help="Path to test results JSON file")
    build_parser.add_argument("--performance-results", help="Path to performance results JSON file")
    build_parser.add_argument("--security-bandit", help="Path to bandit security scan results")
    build_parser.add_argument("--security-pip-audit", help="Path to pip-audit results")
    build_parser.add_argument(
        "--artifact-path",
        default="./artifacts",
        help="Path for artifact storage (default: ./artifacts)",
    )

    # Performance report command
    perf_parser = subparsers.add_parser("performance", help="Generate performance report")
    perf_parser.add_argument(
        "--results", required=True, help="Path to performance results JSON file"
    )
    perf_parser.add_argument("--baseline-comparison", help="Path to baseline comparison JSON file")
    perf_parser.add_argument(
        "--artifact-path", default="./artifacts", help="Path for artifact storage"
    )
    perf_parser.add_argument(
        "--summary-only", action="store_true", help="Generate only step summary, no artifacts"
    )

    # Security report command
    security_parser = subparsers.add_parser("security", help="Generate security report")
    security_parser.add_argument("--bandit-results", help="Path to bandit results JSON file")
    security_parser.add_argument("--pip-audit-results", help="Path to pip-audit results JSON file")
    security_parser.add_argument(
        "--artifact-path", default="./artifacts", help="Path for artifact storage"
    )
    security_parser.add_argument(
        "--summary-only", action="store_true", help="Generate only step summary, no artifacts"
    )

    # Environment info command
    subparsers.add_parser("env-info", help="Show GitHub environment information")

    # Artifact management commands
    artifact_parser = subparsers.add_parser("artifacts", help="Manage artifacts")
    artifact_subparsers = artifact_parser.add_subparsers(dest="artifact_command")

    list_parser = artifact_subparsers.add_parser("list", help="List artifacts")
    list_parser.add_argument(
        "--type", choices=["reports", "logs", "data"], help="Filter by artifact type"
    )
    list_parser.add_argument(
        "--artifact-path", default="./artifacts", help="Path to artifacts directory"
    )

    summary_parser = artifact_subparsers.add_parser("summary", help="Show artifact summary")
    summary_parser.add_argument(
        "--artifact-path", default="./artifacts", help="Path to artifacts directory"
    )

    cleanup_parser = artifact_subparsers.add_parser("cleanup", help="Clean up old artifacts")
    cleanup_parser.add_argument(
        "--max-age-days",
        type=int,
        default=7,
        help="Maximum age of artifacts to keep (default: 7 days)",
    )
    cleanup_parser.add_argument(
        "--artifact-path", default="./artifacts", help="Path to artifacts directory"
    )

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    try:
        if args.command == "build-status":
            handle_build_status(args)
        elif args.command == "performance":
            handle_performance(args)
        elif args.command == "security":
            handle_security(args)
        elif args.command == "env-info":
            handle_env_info(args)
        elif args.command == "artifacts":
            handle_artifacts(args)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


def handle_build_status(args):
    """Handle build status report generation."""
    reporter = GitHubReporter(args.artifact_path)

    # Prepare security files dict
    security_files = {}
    if args.security_bandit:
        security_files["bandit"] = args.security_bandit
    if args.security_pip_audit:
        security_files["pip_audit"] = args.security_pip_audit

    # Generate comprehensive build report
    results = reporter.generate_build_report(
        build_status=args.status,
        test_results_file=args.test_results,
        performance_file=args.performance_results,
        security_files=security_files if security_files else None,
    )

    print("Build status report generated:")
    print(f"  Step summary added: {results['summary_added']}")
    if results["artifact_created"]:
        print(f"  Artifact created: {results['artifact_created']}")

    # Show environment info
    env_info = reporter.get_environment_info()
    if env_info["is_github_actions"]:
        print(f"  GitHub Actions: {env_info['workflow_url'] or 'Running'}")
    else:
        print("  Running locally (not in GitHub Actions)")


def handle_performance(args):
    """Handle performance report generation."""
    reporter = GitHubReporter(args.artifact_path)

    # Load performance data
    try:
        with open(args.results) as f:
            performance_data = json.load(f)
    except Exception as e:
        print(f"Error loading performance results: {e}", file=sys.stderr)
        sys.exit(1)

    # Load baseline comparison if provided
    baseline_data = None
    if args.baseline_comparison:
        try:
            with open(args.baseline_comparison) as f:
                baseline_data = json.load(f)
        except Exception as e:
            print(f"Warning: Could not load baseline comparison: {e}")

    # Generate performance report
    results = reporter.generate_performance_report(
        performance_metrics=performance_data,
        baseline_comparison=baseline_data,
        include_summary=True,
        include_artifact=not args.summary_only,
    )

    print("Performance report generated:")
    print(f"  Step summary added: {results['summary_added']}")
    if results["artifact_created"]:
        print(f"  Artifact created: {results['artifact_created']}")


def handle_security(args):
    """Handle security report generation."""
    reporter = GitHubReporter(args.artifact_path)

    if not args.bandit_results and not args.pip_audit_results:
        print("Error: At least one of --bandit-results or --pip-audit-results must be provided")
        sys.exit(1)

    # Generate security report
    results = reporter.generate_security_report(
        bandit_file=args.bandit_results,
        pip_audit_file=args.pip_audit_results,
        include_summary=True,
        include_artifact=not args.summary_only,
    )

    print("Security report generated:")
    print(f"  Step summary added: {results['summary_added']}")
    if results["artifact_created"]:
        print(f"  Artifact created: {results['artifact_created']}")


def handle_env_info(args):
    """Handle environment information display."""
    reporter = GitHubReporter()
    env_info = reporter.get_environment_info()

    print("GitHub Actions Environment Information:")
    print(f"  Is GitHub Actions: {env_info['is_github_actions']}")
    print(f"  Step Summary Path: {env_info['summary_path'] or 'Not set'}")
    print(f"  Artifact Path: {env_info['artifact_path']}")

    if env_info["workflow_url"]:
        print(f"  Workflow URL: {env_info['workflow_url']}")

    print("\nGitHub Environment Variables:")
    github_env = env_info["github_env"]
    if github_env:
        for key, value in github_env.items():
            print(f"  {key}: {value}")
    else:
        print("  No GitHub environment variables found")


def handle_artifacts(args):
    """Handle artifact management commands."""
    from .artifact_manager import ArtifactManager

    artifact_manager = ArtifactManager(args.artifact_path)

    if args.artifact_command == "list":
        artifacts = artifact_manager.list_artifacts(args.type)

        if not artifacts:
            print("No artifacts found")
            return

        print(f"Found {len(artifacts)} artifacts:")
        print()

        for artifact in artifacts:
            print(f"Name: {artifact['name']}")
            print(f"  Type: {artifact['type']}")
            print(f"  Size: {artifact['size']} bytes")
            print(f"  Created: {artifact['created']}")
            print(f"  Path: {artifact['path']}")
            print()

    elif args.artifact_command == "summary":
        summary = artifact_manager.get_artifact_summary()

        print("Artifact Summary:")
        print(f"  Total artifacts: {summary['total_count']}")
        print(f"  Total size: {summary['total_size']} bytes")
        print()

        print("By type:")
        for artifact_type, stats in summary["by_type"].items():
            print(f"  {artifact_type}: {stats['count']} files, {stats['size']} bytes")

        if summary["recent_artifacts"]:
            print("\nRecent artifacts:")
            for artifact in summary["recent_artifacts"]:
                print(f"  {artifact['name']} ({artifact['type']})")

    elif args.artifact_command == "cleanup":
        cleaned_count = artifact_manager.cleanup_old_artifacts(args.max_age_days)
        print(f"Cleaned up {cleaned_count} artifacts older than {args.max_age_days} days")


if __name__ == "__main__":
    main()
