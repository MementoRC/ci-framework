"""
CLI interface for CI framework migration tools.
"""

import argparse
import sys
from pathlib import Path

from .analyzer import ProjectAnalyzer
from .migrator import ProjectMigrator
from .models import MigrationStatus


def analyze_command(args: argparse.Namespace) -> int:
    """Execute project analysis command."""
    try:
        analyzer = ProjectAnalyzer(Path(args.project_path))
        result = analyzer.analyze()

        print(f"\n🎯 Project Analysis Complete: {result.project_path}")
        print(f"   📂 Type: {result.project_type.value}")
        print(f"   🏗️  Complexity: {result.complexity.value}")
        print(f"   📦 Package Manager: {result.package_manager.manager.value}")
        print(f"   🐍 Python Versions: {', '.join(result.python_versions)}")
        print(f"   💻 Platforms: {', '.join(result.platforms)}")

        if result.migration_recommendations:
            print(
                f"\n💡 Migration Recommendations ({len(result.migration_recommendations)}):"
            )
            for i, rec in enumerate(result.migration_recommendations, 1):
                print(f"   {i}. {rec}")

        if result.potential_issues:
            print(f"\n⚠️ Potential Issues ({len(result.potential_issues)}):")
            for i, issue in enumerate(result.potential_issues, 1):
                print(f"   {i}. {issue}")

        if args.output:
            output_path = Path(args.output)
            # Save detailed analysis to JSON file
            import json

            def make_serializable(obj, visited=None):
                """Convert non-serializable objects to JSON-serializable format."""
                if visited is None:
                    visited = set()

                obj_id = id(obj)
                if obj_id in visited:
                    return "<circular reference>"

                if isinstance(obj, str | int | float | bool | type(None)):
                    return obj
                elif hasattr(obj, "value"):  # Enum
                    return obj.value
                elif isinstance(obj, Path):
                    return str(obj)
                elif isinstance(obj, list):
                    visited.add(obj_id)
                    result = [make_serializable(item, visited) for item in obj]
                    visited.remove(obj_id)
                    return result
                elif isinstance(obj, dict):
                    visited.add(obj_id)
                    result = {k: make_serializable(v, visited) for k, v in obj.items()}
                    visited.remove(obj_id)
                    return result
                elif hasattr(obj, "__dict__"):
                    visited.add(obj_id)
                    result = {
                        k: make_serializable(v, visited)
                        for k, v in obj.__dict__.items()
                    }
                    visited.remove(obj_id)
                    return result
                else:
                    return str(obj)

            # Convert analysis result to JSON-serializable format
            analysis_dict = make_serializable(result)

            with open(output_path, "w") as f:
                json.dump(analysis_dict, f, indent=2)
            print(f"\n📊 Analysis saved to: {output_path}")

        return 0

    except Exception as e:
        print(f"❌ Analysis failed: {e}")
        return 1


def migrate_command(args: argparse.Namespace) -> int:
    """Execute project migration command."""
    try:
        # First analyze the project
        analyzer = ProjectAnalyzer(Path(args.project_path))
        analysis = analyzer.analyze()

        print(f"🔄 Starting migration for {analysis.project_path}")
        print(f"   📊 Project complexity: {analysis.complexity.value}")

        # Initialize migrator
        migrator = ProjectMigrator(analysis)

        # Create migration plan
        plan = migrator.create_migration_plan()

        print(f"\n📋 Migration Plan ({len(plan.migration_steps)} steps):")
        for i, step in enumerate(plan.migration_steps, 1):
            print(f"   {i}. {step}")

        # Ask for confirmation unless --yes flag is provided
        if not args.yes:
            response = input("\n❓ Proceed with migration? [y/N]: ")
            if response.lower() not in ["y", "yes"]:
                print("🚫 Migration cancelled")
                return 0

        # Execute migration
        print("\n🚀 Executing migration...")
        result = migrator.migrate(dry_run=args.dry_run, backup=not args.no_backup)

        if result.status == MigrationStatus.COMPLETED:
            print("✅ Migration completed successfully!")
            print(f"   📁 Backup location: {result.backup_location}")

            if result.warnings:
                print(f"\n⚠️ Warnings ({len(result.warnings)}):")
                for warning in result.warnings:
                    print(f"   • {warning}")

        elif result.status == MigrationStatus.FAILED:
            print("❌ Migration failed!")
            if result.errors:
                print("\n🔥 Errors:")
                for error in result.errors:
                    print(f"   • {error}")

            if result.rollback_available:
                if not args.no_rollback:
                    print("🔄 Automatic rollback available")
                    migrator.rollback()
                    print("✅ Rollback completed")

        return 0 if result.status == MigrationStatus.COMPLETED else 1

    except Exception as e:
        print(f"❌ Migration failed: {e}")
        return 1


def validate_command(args: argparse.Namespace) -> int:
    """Execute migration validation command."""
    try:
        migrator = ProjectMigrator.from_project_path(Path(args.project_path))
        result = migrator.validate_migration()

        print(f"🔍 Validation Results for {args.project_path}")
        print(
            f"   ✅ Overall Status: {'PASSED' if result.validation_passed else 'FAILED'}"
        )

        if result.quality_gates_status:
            print("\n🚪 Quality Gates Status:")
            for gate, status in result.quality_gates_status.items():
                status_icon = "✅" if status else "❌"
                print(f"   {status_icon} {gate}")

        if result.compatibility_issues:
            print(f"\n⚠️ Compatibility Issues ({len(result.compatibility_issues)}):")
            for issue in result.compatibility_issues:
                print(f"   • {issue}")

        if result.recommendations:
            print("\n💡 Recommendations:")
            for rec in result.recommendations:
                print(f"   • {rec}")

        return 0 if result.validation_passed else 1

    except Exception as e:
        print(f"❌ Validation failed: {e}")
        return 1


def rollback_command(args: argparse.Namespace) -> int:
    """Execute migration rollback command."""
    try:
        migrator = ProjectMigrator.from_project_path(Path(args.project_path))

        # Ask for confirmation unless --yes flag is provided
        if not args.yes:
            response = input(
                f"❓ Are you sure you want to rollback migration for {args.project_path}? [y/N]: "
            )
            if response.lower() not in ["y", "yes"]:
                print("🚫 Rollback cancelled")
                return 0

        print("🔄 Rolling back migration...")
        success = migrator.rollback()

        if success:
            print("✅ Rollback completed successfully")
            return 0
        else:
            print("❌ Rollback failed")
            return 1

    except Exception as e:
        print(f"❌ Rollback failed: {e}")
        return 1


def main(argv: list | None = None) -> int:
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        prog="ci-migrate", description="CI Framework Migration Tools"
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Analyze command
    analyze_parser = subparsers.add_parser(
        "analyze", help="Analyze project for migration"
    )
    analyze_parser.add_argument("project_path", help="Path to project to analyze")
    analyze_parser.add_argument("-o", "--output", help="Save analysis to JSON file")
    analyze_parser.set_defaults(func=analyze_command)

    # Migrate command
    migrate_parser = subparsers.add_parser("migrate", help="Execute project migration")
    migrate_parser.add_argument("project_path", help="Path to project to migrate")
    migrate_parser.add_argument(
        "--dry-run", action="store_true", help="Preview migration without changes"
    )
    migrate_parser.add_argument(
        "--no-backup", action="store_true", help="Skip creating backup"
    )
    migrate_parser.add_argument(
        "--no-rollback",
        action="store_true",
        help="Disable automatic rollback on failure",
    )
    migrate_parser.add_argument(
        "-y", "--yes", action="store_true", help="Skip confirmation prompts"
    )
    migrate_parser.set_defaults(func=migrate_command)

    # Validate command
    validate_parser = subparsers.add_parser(
        "validate", help="Validate migrated project"
    )
    validate_parser.add_argument("project_path", help="Path to project to validate")
    validate_parser.set_defaults(func=validate_command)

    # Rollback command
    rollback_parser = subparsers.add_parser("rollback", help="Rollback migration")
    rollback_parser.add_argument("project_path", help="Path to project to rollback")
    rollback_parser.add_argument(
        "-y", "--yes", action="store_true", help="Skip confirmation prompts"
    )
    rollback_parser.set_defaults(func=rollback_command)

    # Parse arguments
    args = parser.parse_args(argv)

    if not hasattr(args, "func"):
        parser.print_help()
        return 1

    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
