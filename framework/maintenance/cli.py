"""Command-line interface for maintenance operations."""

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from .health_monitor import CIHealthMonitor
from .scheduler import MaintenanceScheduler


def create_parser() -> argparse.ArgumentParser:
    """Create the command-line argument parser."""
    parser = argparse.ArgumentParser(
        description="Hummingbot Strategy Sandbox - Maintenance Tools",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s health --summary                    # Show health summary
  %(prog)s health --collect                    # Collect health metrics
  %(prog)s health --diagnostics                # Run diagnostics

  %(prog)s tasks --list                        # List all maintenance tasks
  %(prog)s tasks --run health_check            # Run specific task
  %(prog)s tasks --run-pending                 # Run all pending tasks

  %(prog)s maintenance --perform               # Perform full maintenance
  %(prog)s maintenance --perform --dry-run     # Preview maintenance actions

  %(prog)s config --show                       # Show current configuration
        """,
    )

    parser.add_argument("--config", type=str, help="Path to maintenance configuration file")

    parser.add_argument(
        "--project-path",
        type=str,
        default=".",
        help="Path to project root directory (default: current directory)",
    )

    parser.add_argument(
        "--output-format",
        choices=["json", "text"],
        default="text",
        help="Output format (default: text)",
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Health monitoring commands
    health_parser = subparsers.add_parser("health", help="Health monitoring operations")
    health_group = health_parser.add_mutually_exclusive_group(required=True)
    health_group.add_argument(
        "--collect", action="store_true", help="Collect current health metrics"
    )
    health_group.add_argument("--summary", action="store_true", help="Show health summary")
    health_group.add_argument("--diagnostics", action="store_true", help="Run system diagnostics")

    # Task management commands
    tasks_parser = subparsers.add_parser("tasks", help="Maintenance task operations")
    tasks_group = tasks_parser.add_mutually_exclusive_group(required=True)
    tasks_group.add_argument("--list", action="store_true", help="List all maintenance tasks")
    tasks_group.add_argument("--run", type=str, metavar="TASK_NAME", help="Run specific task")
    tasks_group.add_argument("--run-pending", action="store_true", help="Run all pending tasks")
    tasks_group.add_argument("--status", type=str, metavar="TASK_NAME", help="Show task status")
    tasks_group.add_argument("--history", action="store_true", help="Show execution history")

    # Maintenance operations
    maintenance_parser = subparsers.add_parser(
        "maintenance", help="Comprehensive maintenance operations"
    )
    maintenance_parser.add_argument(
        "--perform", action="store_true", help="Perform maintenance operations"
    )
    maintenance_parser.add_argument(
        "--dry-run", action="store_true", help="Preview actions without executing"
    )

    # Configuration commands
    config_parser = subparsers.add_parser("config", help="Configuration management")
    config_group = config_parser.add_mutually_exclusive_group(required=True)
    config_group.add_argument("--show", action="store_true", help="Show current configuration")
    config_group.add_argument("--validate", action="store_true", help="Validate configuration file")

    return parser


def format_output(data: Any, format_type: str) -> str:
    """Format output data based on the specified format."""
    if format_type == "json":
        return json.dumps(data, indent=2, default=str)
    else:
        return format_text_output(data)


def format_text_output(data: Any) -> str:
    """Format data as human-readable text."""
    if isinstance(data, dict):
        lines = []
        for key, value in data.items():
            if isinstance(value, dict):
                lines.append(f"{key.replace('_', ' ').title()}:")
                for subkey, subvalue in value.items():
                    lines.append(f"  {subkey.replace('_', ' ').title()}: {subvalue}")
            elif isinstance(value, list):
                lines.append(f"{key.replace('_', ' ').title()}:")
                for item in value:
                    lines.append(f"  - {item}")
            else:
                lines.append(f"{key.replace('_', ' ').title()}: {value}")
        return "\n".join(lines)
    elif isinstance(data, list):
        return "\n".join(str(item) for item in data)
    else:
        return str(data)


def handle_health_command(args, monitor: CIHealthMonitor) -> int:
    """Handle health monitoring commands."""
    try:
        if args.collect:
            result = monitor.collect_health_metrics()
            print(format_output(result, args.output_format))

        elif args.summary:
            result = monitor.get_health_summary()
            print(format_output(result, args.output_format))

        elif args.diagnostics:
            result = monitor.run_diagnostics()
            print(format_output(result, args.output_format))

            # Return appropriate exit code based on overall status
            overall_status = result.get("overall_status", "unknown")
            if overall_status == "critical":
                return 2
            elif overall_status in ["warning", "error"]:
                return 1

        return 0

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


def handle_tasks_command(args, scheduler: MaintenanceScheduler) -> int:
    """Handle task management commands."""
    try:
        if args.list:
            result = scheduler.get_task_status()
            if args.output_format == "text":
                print("Maintenance Tasks:")
                print("=" * 50)
                for task in result["tasks"]:
                    status_icon = "✓" if task["enabled"] else "✗"
                    print(f"{status_icon} {task['name']} ({task['schedule']})")
                    print(f"   {task['description']}")
                    if task["last_run"]:
                        print(f"   Last run: {task['last_run']}")
                    if task["next_run"]:
                        print(f"   Next run: {task['next_run']}")
                    print()

                print(f"Total: {result['total_tasks']} tasks, {result['enabled_tasks']} enabled")
            else:
                print(format_output(result, args.output_format))

        elif args.run:
            result = scheduler.run_task(args.run)
            print(format_output(result, args.output_format))
            return 0 if result.get("success", False) else 1

        elif args.run_pending:
            results = scheduler.run_pending_tasks()
            if args.output_format == "text":
                print(f"Executed {len(results)} pending tasks:")
                for result in results:
                    status_icon = "✓" if result["success"] else "✗"
                    print(f"{status_icon} {result['task']}: {result['message']}")
            else:
                print(format_output(results, args.output_format))

        elif args.status:
            result = scheduler.get_task_status(args.status)
            print(format_output(result, args.output_format))

        elif args.history:
            history = scheduler.get_execution_history()
            print(format_output(history, args.output_format))

        return 0

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


def handle_maintenance_command(args, scheduler: MaintenanceScheduler) -> int:
    """Handle maintenance operations."""
    try:
        if args.perform:
            dry_run = args.dry_run if hasattr(args, "dry_run") else False
            result = scheduler.perform_maintenance(dry_run=dry_run)

            if args.output_format == "text":
                print(f"Maintenance {'Preview' if dry_run else 'Results'}:")
                print("=" * 50)
                print(f"Start time: {result['start_time']}")

                for operation in result["operations"]:
                    status_icon = {"success": "✓", "error": "✗", "skipped": "-"}.get(
                        operation["status"], "?"
                    )
                    print(
                        f"{status_icon} {operation['operation']}: {operation.get('details', operation.get('error', 'OK'))}"
                    )

                summary = result["summary"]
                print(
                    f"\nSummary: {summary['successful_operations']}/{summary['total_operations']} operations successful"
                )

                if summary["failed_operations"] > 0:
                    return 1
            else:
                print(format_output(result, args.output_format))

        return 0

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


def handle_config_command(args, scheduler: MaintenanceScheduler) -> int:
    """Handle configuration commands."""
    try:
        if args.show:
            print(format_output(scheduler.config, args.output_format))

        elif args.validate:
            # Basic configuration validation
            required_sections = ["data_retention", "health_thresholds", "update_schedule"]
            missing_sections = [
                section for section in required_sections if section not in scheduler.config
            ]

            if missing_sections:
                print(f"Configuration validation failed: Missing sections: {missing_sections}")
                return 1
            else:
                print("Configuration validation passed")

        return 0

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


def main() -> int:
    """Main entry point for the maintenance CLI."""
    parser = create_parser()
    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 1

    # Initialize components
    try:
        project_path = Path(args.project_path).resolve()
        config_path = args.config

        if args.command in ["health"]:
            monitor = CIHealthMonitor(config_path=config_path, project_path=project_path)
            return handle_health_command(args, monitor)

        else:
            scheduler = MaintenanceScheduler(config_path=config_path, project_path=project_path)

            if args.command == "tasks":
                return handle_tasks_command(args, scheduler)
            elif args.command == "maintenance":
                return handle_maintenance_command(args, scheduler)
            elif args.command == "config":
                return handle_config_command(args, scheduler)

    except Exception as e:
        print(f"Initialization error: {e}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
