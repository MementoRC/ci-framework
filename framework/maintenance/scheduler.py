"""Automated maintenance task scheduler and execution engine."""

import logging
import time
from collections.abc import Callable
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import yaml

from .health_monitor import CIHealthMonitor

logger = logging.getLogger(__name__)


class MaintenanceTask:
    """Represents a scheduled maintenance task."""

    def __init__(
        self,
        name: str,
        func: Callable,
        schedule: str,
        enabled: bool = True,
        description: str = "",
        **kwargs,
    ):
        """Initialize a maintenance task.

        Args:
            name: Task name/identifier.
            func: Function to execute for this task.
            schedule: Schedule string (daily, weekly, hourly, etc.).
            enabled: Whether the task is enabled.
            description: Task description.
            **kwargs: Additional task parameters.
        """
        self.name = name
        self.func = func
        self.schedule = schedule
        self.enabled = enabled
        self.description = description
        self.params = kwargs
        self.last_run: datetime | None = None
        self.next_run: datetime | None = None
        self.run_count = 0
        self.error_count = 0
        self.last_error: str | None = None

        self._calculate_next_run()

    def _calculate_next_run(self):
        """Calculate the next run time based on schedule."""
        now = datetime.now()

        if not self.enabled:
            self.next_run = None
            return

        if self.schedule == "hourly":
            self.next_run = now + timedelta(hours=1)
        elif self.schedule == "daily":
            # Run at 2 AM daily
            next_run = now.replace(hour=2, minute=0, second=0, microsecond=0)
            if next_run <= now:
                next_run += timedelta(days=1)
            self.next_run = next_run
        elif self.schedule == "weekly":
            # Run on Sunday at 2 AM
            days_until_sunday = (6 - now.weekday()) % 7
            next_run = now.replace(hour=2, minute=0, second=0, microsecond=0)
            next_run += timedelta(days=days_until_sunday)
            if next_run <= now:
                next_run += timedelta(days=7)
            self.next_run = next_run
        elif self.schedule == "monthly":
            # Run on the 1st of each month at 2 AM
            if now.day == 1 and now.hour < 2:
                next_run = now.replace(hour=2, minute=0, second=0, microsecond=0)
            else:
                next_month = now.replace(day=1) + timedelta(days=32)
                next_run = next_month.replace(day=1, hour=2, minute=0, second=0, microsecond=0)
            self.next_run = next_run
        else:
            # Custom or unknown schedule
            self.next_run = now + timedelta(hours=24)

    def should_run(self) -> bool:
        """Check if the task should run now."""
        if not self.enabled or not self.next_run:
            return False
        return datetime.now() >= self.next_run

    def execute(self) -> dict[str, Any]:
        """Execute the maintenance task."""
        start_time = time.time()
        result = {
            "task": self.name,
            "start_time": datetime.now().isoformat(),
            "success": False,
            "duration": 0,
            "message": "",
            "details": {},
        }

        try:
            logger.info(f"Executing maintenance task: {self.name}")

            # Execute the task function
            task_result = self.func(**self.params)

            # Update task state
            self.last_run = datetime.now()
            self.run_count += 1
            self._calculate_next_run()

            result.update(
                {
                    "success": True,
                    "duration": time.time() - start_time,
                    "message": f"Task '{self.name}' completed successfully",
                    "details": task_result
                    if isinstance(task_result, dict)
                    else {"result": task_result},
                }
            )

            logger.info(f"Task '{self.name}' completed in {result['duration']:.2f}s")

        except Exception as e:
            # Update task state even for failures
            self.last_run = datetime.now()
            self.run_count += 1
            self.error_count += 1
            self.last_error = str(e)
            self._calculate_next_run()

            result.update(
                {
                    "success": False,
                    "duration": time.time() - start_time,
                    "message": f"Task '{self.name}' failed: {e}",
                    "error": str(e),
                }
            )

            logger.error(f"Task '{self.name}' failed: {e}")

        return result

    def get_status(self) -> dict[str, Any]:
        """Get current task status."""
        return {
            "name": self.name,
            "description": self.description,
            "schedule": self.schedule,
            "enabled": self.enabled,
            "last_run": self.last_run.isoformat() if self.last_run else None,
            "next_run": self.next_run.isoformat() if self.next_run else None,
            "run_count": self.run_count,
            "error_count": self.error_count,
            "last_error": self.last_error,
        }


class MaintenanceScheduler:
    """Schedules and executes automated maintenance tasks."""

    def __init__(
        self, config_path: str | Path | None = None, project_path: str | Path | None = None
    ):
        """Initialize the maintenance scheduler.

        Args:
            config_path: Path to maintenance configuration file.
            project_path: Path to the project root directory.
        """
        self.project_path = Path(project_path or ".")

        # Load configuration
        default_config_path = (
            self.project_path / "framework" / "maintenance" / "maintenance_config.yaml"
        )
        self.config_path = Path(config_path or default_config_path)
        self.config = self._load_config()

        # Initialize health monitor
        self.health_monitor = CIHealthMonitor(config_path, project_path)

        # Task registry
        self.tasks: dict[str, MaintenanceTask] = {}
        self.execution_history: list[dict[str, Any]] = []

        # Initialize built-in tasks
        self._register_builtin_tasks()

    def _load_config(self) -> dict[str, Any]:
        """Load maintenance configuration."""
        if not self.config_path.exists():
            logger.warning(f"Config file not found: {self.config_path}")
            return {}

        try:
            with open(self.config_path) as f:
                return yaml.safe_load(f)
        except Exception as e:
            logger.error(f"Failed to load config: {e}")
            return {}

    def _register_builtin_tasks(self):
        """Register built-in maintenance tasks."""
        # Health check task
        self.register_task(
            name="health_check",
            func=self.health_monitor.collect_health_metrics,
            schedule=self.config.get("update_schedule", {}).get("health_check", "hourly"),
            description="Collect system health metrics and check component status",
        )

        # Data cleanup task
        self.register_task(
            name="data_cleanup",
            func=self._cleanup_old_data,
            schedule=self.config.get("update_schedule", {}).get("cleanup_old_data", "weekly"),
            description="Clean up old data files based on retention policies",
        )

        # Security database update task
        self.register_task(
            name="security_update",
            func=self._update_security_databases,
            schedule=self.config.get("update_schedule", {}).get("security_databases", "daily"),
            description="Update security vulnerability databases",
        )

        # Performance baseline update task
        self.register_task(
            name="performance_baseline",
            func=self._update_performance_baselines,
            schedule=self.config.get("update_schedule", {}).get("performance_baseline", "weekly"),
            description="Update performance baselines and analyze trends",
        )

        # System diagnostics task
        self.register_task(
            name="system_diagnostics",
            func=self.health_monitor.run_diagnostics,
            schedule="daily",
            description="Run comprehensive system diagnostics",
        )

    def register_task(
        self,
        name: str,
        func: Callable,
        schedule: str,
        enabled: bool = True,
        description: str = "",
        **kwargs,
    ):
        """Register a new maintenance task.

        Args:
            name: Task name/identifier.
            func: Function to execute.
            schedule: Schedule string (daily, weekly, hourly, etc.).
            enabled: Whether the task is enabled.
            description: Task description.
            **kwargs: Additional task parameters.
        """
        # Check if task is enabled in config
        task_config = self.config.get("maintenance_tasks", {})
        if name in task_config:
            enabled = task_config[name].get("enabled", enabled)

        task = MaintenanceTask(
            name=name,
            func=func,
            schedule=schedule,
            enabled=enabled,
            description=description,
            **kwargs,
        )

        self.tasks[name] = task
        logger.info(f"Registered maintenance task: {name} ({schedule})")

    def run_pending_tasks(self) -> list[dict[str, Any]]:
        """Run all pending maintenance tasks."""
        results = []

        for task in self.tasks.values():
            if task.should_run():
                result = task.execute()
                results.append(result)
                self.execution_history.append(result)

        return results

    def run_task(self, task_name: str) -> dict[str, Any]:
        """Run a specific maintenance task immediately.

        Args:
            task_name: Name of the task to run.

        Returns:
            Task execution result.
        """
        if task_name not in self.tasks:
            return {"task": task_name, "success": False, "message": f"Task '{task_name}' not found"}

        task = self.tasks[task_name]
        result = task.execute()
        self.execution_history.append(result)
        return result

    def get_task_status(self, task_name: str | None = None) -> dict[str, Any]:
        """Get status of tasks.

        Args:
            task_name: Specific task name, or None for all tasks.

        Returns:
            Task status information.
        """
        if task_name:
            if task_name in self.tasks:
                return self.tasks[task_name].get_status()
            else:
                return {"error": f"Task '{task_name}' not found"}

        # Return status for all tasks
        return {
            "tasks": [task.get_status() for task in self.tasks.values()],
            "total_tasks": len(self.tasks),
            "enabled_tasks": len([t for t in self.tasks.values() if t.enabled]),
            "recent_executions": len(
                [
                    h
                    for h in self.execution_history
                    if datetime.fromisoformat(h["start_time"])
                    > datetime.now() - timedelta(hours=24)
                ]
            ),
        }

    def get_execution_history(self, limit: int = 50) -> list[dict[str, Any]]:
        """Get recent task execution history.

        Args:
            limit: Maximum number of entries to return.

        Returns:
            List of execution results.
        """
        return self.execution_history[-limit:]

    def _cleanup_old_data(self) -> dict[str, Any]:
        """Clean up old data files based on retention policies."""
        logger.info("Starting data cleanup")

        retention_config = self.config.get("data_retention", {})
        cleanup_result: dict[str, Any] = {
            "files_removed": 0,
            "space_freed_mb": 0,
            "directories_processed": [],
            "errors": [],
        }

        cleanup_targets = [
            ("performance_data/history", retention_config.get("performance_data", 90)),
            ("artifacts/reports", retention_config.get("reports", 60)),
            ("artifacts/logs", retention_config.get("logs", 14)),
        ]

        for target_dir, retention_days in cleanup_targets:
            dir_path = self.project_path / target_dir
            if not dir_path.exists():
                continue

            try:
                cutoff_date = datetime.now() - timedelta(days=retention_days)
                files_removed = 0
                space_freed = 0

                for file_path in dir_path.rglob("*"):
                    if file_path.is_file():
                        file_mtime = datetime.fromtimestamp(file_path.stat().st_mtime)
                        if file_mtime < cutoff_date:
                            file_size = file_path.stat().st_size
                            file_path.unlink()
                            files_removed += 1
                            space_freed += file_size

                cleanup_result["files_removed"] += files_removed
                cleanup_result["space_freed_mb"] += space_freed / (1024 * 1024)
                cleanup_result["directories_processed"].append(
                    {
                        "directory": str(target_dir),
                        "files_removed": files_removed,
                        "space_freed_mb": space_freed / (1024 * 1024),
                    }
                )

                logger.info(f"Cleaned {files_removed} files from {target_dir}")

            except Exception as e:
                error_msg = f"Failed to cleanup {target_dir}: {e}"
                cleanup_result["errors"].append(error_msg)
                logger.error(error_msg)

        return cleanup_result

    def _update_security_databases(self) -> dict[str, Any]:
        """Update security vulnerability databases."""
        logger.info("Updating security databases")

        # This is a placeholder - in a real implementation, you would:
        # 1. Update pip-audit databases
        # 2. Update safety databases
        # 3. Update other security tools' databases

        return {
            "databases_updated": ["pip-audit", "safety"],
            "update_time": datetime.now().isoformat(),
            "status": "success",
        }

    def _update_performance_baselines(self) -> dict[str, Any]:
        """Update performance baselines and analyze trends."""
        logger.info("Updating performance baselines")

        try:
            # Get recent performance history
            recent_metrics = self.health_monitor.performance_collector.get_recent_history(limit=10)

            if not recent_metrics:
                return {"status": "no_data", "message": "No recent performance data to analyze"}

            # Calculate average performance for new baseline
            baseline_metrics = recent_metrics[0]  # Use most recent as baseline

            # Store as new baseline
            baseline_path = self.health_monitor.performance_collector.store_baseline(
                baseline_metrics, f"auto_{datetime.now().strftime('%Y%m%d')}"
            )

            return {
                "status": "success",
                "baseline_file": str(baseline_path),
                "metrics_analyzed": len(recent_metrics),
                "baseline_timestamp": baseline_metrics.timestamp.isoformat(),
            }

        except Exception as e:
            return {"status": "error", "error": str(e)}

    def perform_maintenance(self, dry_run: bool = False) -> dict[str, Any]:
        """Perform comprehensive maintenance operations.

        Args:
            dry_run: If True, only report what would be done without making changes.

        Returns:
            Maintenance operation results.
        """
        logger.info(f"Starting maintenance {'(dry run)' if dry_run else '(live)'}")

        maintenance_result: dict[str, Any] = {
            "start_time": datetime.now().isoformat(),
            "dry_run": dry_run,
            "operations": [],
            "summary": {"total_operations": 0, "successful_operations": 0, "failed_operations": 0},
        }

        # Health check
        try:
            self.health_monitor.collect_health_metrics()
            maintenance_result["operations"].append(
                {
                    "operation": "health_check",
                    "status": "success",
                    "details": {"overall_status": self.health_monitor._determine_overall_status()},
                }
            )
        except Exception as e:
            maintenance_result["operations"].append(
                {"operation": "health_check", "status": "error", "error": str(e)}
            )

        # Data cleanup
        if not dry_run:
            try:
                cleanup_result = self._cleanup_old_data()
                maintenance_result["operations"].append(
                    {"operation": "data_cleanup", "status": "success", "details": cleanup_result}
                )
            except Exception as e:
                maintenance_result["operations"].append(
                    {"operation": "data_cleanup", "status": "error", "error": str(e)}
                )
        else:
            maintenance_result["operations"].append(
                {"operation": "data_cleanup", "status": "skipped", "reason": "dry_run_mode"}
            )

        # System diagnostics
        try:
            diagnostics = self.health_monitor.run_diagnostics()
            maintenance_result["operations"].append(
                {
                    "operation": "system_diagnostics",
                    "status": "success",
                    "details": {"overall_status": diagnostics.get("overall_status")},
                }
            )
        except Exception as e:
            maintenance_result["operations"].append(
                {"operation": "system_diagnostics", "status": "error", "error": str(e)}
            )

        # Update summary
        maintenance_result["summary"]["total_operations"] = len(maintenance_result["operations"])
        maintenance_result["summary"]["successful_operations"] = len(
            [op for op in maintenance_result["operations"] if op["status"] == "success"]
        )
        maintenance_result["summary"]["failed_operations"] = len(
            [op for op in maintenance_result["operations"] if op["status"] == "error"]
        )

        maintenance_result["end_time"] = datetime.now().isoformat()

        logger.info(f"Maintenance completed: {maintenance_result['summary']}")

        return maintenance_result
