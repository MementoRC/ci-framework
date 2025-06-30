"""Tests for maintenance scheduler functionality."""

import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
import yaml

from framework.maintenance.scheduler import MaintenanceScheduler, MaintenanceTask


class TestMaintenanceTask:
    """Test cases for MaintenanceTask class."""

    def test_task_initialization(self):
        """Test maintenance task initialization."""

        def dummy_func():
            return "success"

        task = MaintenanceTask(
            name="test_task", func=dummy_func, schedule="daily", description="Test task"
        )

        assert task.name == "test_task"
        assert task.func == dummy_func
        assert task.schedule == "daily"
        assert task.enabled is True
        assert task.description == "Test task"
        assert task.run_count == 0
        assert task.error_count == 0

    def test_calculate_next_run_hourly(self):
        """Test next run calculation for hourly schedule."""

        def dummy_func():
            return "success"

        task = MaintenanceTask("test", dummy_func, "hourly")

        # Next run should be approximately 1 hour from now
        time_diff = task.next_run - datetime.now()
        assert 3500 <= time_diff.total_seconds() <= 3700  # ~1 hour with some tolerance

    def test_calculate_next_run_daily(self):
        """Test next run calculation for daily schedule."""

        def dummy_func():
            return "success"

        task = MaintenanceTask("test", dummy_func, "daily")

        # Next run should be at 2 AM tomorrow (or today if it's before 2 AM)
        assert task.next_run.hour == 2
        assert task.next_run.minute == 0

    def test_calculate_next_run_weekly(self):
        """Test next run calculation for weekly schedule."""

        def dummy_func():
            return "success"

        task = MaintenanceTask("test", dummy_func, "weekly")

        # Next run should be on Sunday at 2 AM
        assert task.next_run.weekday() == 6  # Sunday
        assert task.next_run.hour == 2

    def test_should_run_enabled_task(self):
        """Test should_run for enabled task."""

        def dummy_func():
            return "success"

        task = MaintenanceTask("test", dummy_func, "hourly")
        # Set next_run to past time
        task.next_run = datetime.now() - timedelta(minutes=1)

        assert task.should_run() is True

    def test_should_run_disabled_task(self):
        """Test should_run for disabled task."""

        def dummy_func():
            return "success"

        task = MaintenanceTask("test", dummy_func, "hourly", enabled=False)

        assert task.should_run() is False

    def test_should_run_future_task(self):
        """Test should_run for task scheduled in future."""

        def dummy_func():
            return "success"

        task = MaintenanceTask("test", dummy_func, "hourly")
        # Set next_run to future time
        task.next_run = datetime.now() + timedelta(hours=1)

        assert task.should_run() is False

    def test_execute_successful_task(self):
        """Test successful task execution."""

        def dummy_func():
            return {"result": "success", "data": 123}

        task = MaintenanceTask("test", dummy_func, "hourly")
        result = task.execute()

        assert result["success"] is True
        assert result["task"] == "test"
        assert "start_time" in result
        assert result["duration"] > 0
        assert result["details"]["result"] == "success"
        assert task.run_count == 1
        assert task.error_count == 0

    def test_execute_failing_task(self):
        """Test failing task execution."""

        def failing_func():
            raise ValueError("Test error")

        task = MaintenanceTask("test", failing_func, "hourly")
        result = task.execute()

        assert result["success"] is False
        assert result["task"] == "test"
        assert "Test error" in result["message"]
        assert "error" in result
        assert task.run_count == 1
        assert task.error_count == 1
        assert task.last_error == "Test error"

    def test_execute_with_parameters(self):
        """Test task execution with parameters."""

        def parameterized_func(param1, param2="default"):
            return {"param1": param1, "param2": param2}

        task = MaintenanceTask(
            "test", parameterized_func, "hourly", param1="value1", param2="value2"
        )
        result = task.execute()

        assert result["success"] is True
        assert result["details"]["param1"] == "value1"
        assert result["details"]["param2"] == "value2"

    def test_get_status(self):
        """Test task status retrieval."""

        def dummy_func():
            return "success"

        task = MaintenanceTask("test", dummy_func, "daily", description="Test task")
        task.run_count = 5
        task.error_count = 1
        task.last_error = "Previous error"

        status = task.get_status()

        assert status["name"] == "test"
        assert status["description"] == "Test task"
        assert status["schedule"] == "daily"
        assert status["enabled"] is True
        assert status["run_count"] == 5
        assert status["error_count"] == 1
        assert status["last_error"] == "Previous error"


class TestMaintenanceScheduler:
    """Test cases for MaintenanceScheduler class."""

    @pytest.fixture
    def temp_project_dir(self):
        """Create a temporary project directory for testing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_path = Path(temp_dir)

            # Create necessary subdirectories
            (project_path / "performance_data").mkdir(parents=True)
            (project_path / "artifacts" / "reports").mkdir(parents=True)
            (project_path / "strategy_sandbox" / "maintenance").mkdir(parents=True)

            yield project_path

    @pytest.fixture
    def sample_config(self, temp_project_dir):
        """Create a sample configuration file."""
        config_data = {
            "data_retention": {"performance_data": 90, "security_scans": 30, "reports": 60},
            "health_thresholds": {"max_execution_time": 3600, "max_storage_usage": 5},
            "update_schedule": {
                "health_check": "hourly",
                "cleanup_old_data": "weekly",
                "security_databases": "daily",
            },
            "maintenance_tasks": {
                "health_check": {"enabled": True},
                "data_cleanup": {"enabled": False},
            },
        }

        config_path = (
            temp_project_dir / "strategy_sandbox" / "maintenance" / "maintenance_config.yaml"
        )
        with open(config_path, "w") as f:
            yaml.dump(config_data, f)

        return config_path

    def test_scheduler_initialization(self, temp_project_dir, sample_config):
        """Test MaintenanceScheduler initialization."""
        scheduler = MaintenanceScheduler(config_path=sample_config, project_path=temp_project_dir)

        assert scheduler.project_path == temp_project_dir
        assert scheduler.config_path == sample_config
        assert len(scheduler.tasks) > 0  # Should have built-in tasks
        assert "health_check" in scheduler.tasks

    def test_scheduler_without_config(self, temp_project_dir):
        """Test scheduler initialization without config file."""
        scheduler = MaintenanceScheduler(project_path=temp_project_dir)

        assert scheduler.project_path == temp_project_dir
        assert len(scheduler.tasks) > 0  # Should still have built-in tasks

    def test_register_task(self, temp_project_dir):
        """Test task registration."""
        scheduler = MaintenanceScheduler(project_path=temp_project_dir)

        def custom_task():
            return "custom result"

        scheduler.register_task(
            name="custom_task", func=custom_task, schedule="daily", description="Custom test task"
        )

        assert "custom_task" in scheduler.tasks
        task = scheduler.tasks["custom_task"]
        assert task.name == "custom_task"
        assert task.schedule == "daily"
        assert task.description == "Custom test task"

    def test_register_task_with_config_override(self, temp_project_dir, sample_config):
        """Test task registration with config override."""
        scheduler = MaintenanceScheduler(config_path=sample_config, project_path=temp_project_dir)

        # data_cleanup should be disabled according to config
        assert "data_cleanup" in scheduler.tasks
        assert scheduler.tasks["data_cleanup"].enabled is False

    def test_run_task_success(self, temp_project_dir):
        """Test running a specific task successfully."""
        scheduler = MaintenanceScheduler(project_path=temp_project_dir)

        def test_task():
            return {"status": "completed"}

        scheduler.register_task("test_task", test_task, "daily")
        result = scheduler.run_task("test_task")

        assert result["success"] is True
        assert result["task"] == "test_task"
        assert "completed" in str(result["details"])

    def test_run_task_not_found(self, temp_project_dir):
        """Test running a non-existent task."""
        scheduler = MaintenanceScheduler(project_path=temp_project_dir)
        result = scheduler.run_task("nonexistent_task")

        assert result["success"] is False
        assert "not found" in result["message"]

    def test_run_pending_tasks(self, temp_project_dir):
        """Test running pending tasks."""
        scheduler = MaintenanceScheduler(project_path=temp_project_dir)

        def quick_task():
            return "done"

        # Register a task and set it to run immediately
        scheduler.register_task("quick_task", quick_task, "hourly")
        scheduler.tasks["quick_task"].next_run = datetime.now() - timedelta(minutes=1)

        results = scheduler.run_pending_tasks()

        assert len(results) >= 1
        # Check if our task was executed
        task_results = [r for r in results if r["task"] == "quick_task"]
        assert len(task_results) == 1
        assert task_results[0]["success"] is True

    def test_get_task_status_single_task(self, temp_project_dir):
        """Test getting status for a single task."""
        scheduler = MaintenanceScheduler(project_path=temp_project_dir)

        status = scheduler.get_task_status("health_check")

        assert status["name"] == "health_check"
        assert "schedule" in status
        assert "enabled" in status

    def test_get_task_status_all_tasks(self, temp_project_dir):
        """Test getting status for all tasks."""
        scheduler = MaintenanceScheduler(project_path=temp_project_dir)

        status = scheduler.get_task_status()

        assert "tasks" in status
        assert "total_tasks" in status
        assert "enabled_tasks" in status
        assert status["total_tasks"] > 0

    def test_get_execution_history(self, temp_project_dir):
        """Test getting execution history."""
        scheduler = MaintenanceScheduler(project_path=temp_project_dir)

        def test_task():
            return "result"

        scheduler.register_task("test_task", test_task, "daily")
        scheduler.run_task("test_task")

        history = scheduler.get_execution_history()

        assert len(history) >= 1
        assert history[-1]["task"] == "test_task"

    @patch("framework.maintenance.scheduler.datetime")
    def test_cleanup_old_data(self, mock_datetime, temp_project_dir):
        """Test data cleanup functionality."""
        # Mock datetime to control "now"
        mock_now = datetime(2024, 1, 15, 12, 0, 0)
        mock_datetime.now.return_value = mock_now
        mock_datetime.fromtimestamp.side_effect = lambda ts: datetime.fromtimestamp(ts)

        scheduler = MaintenanceScheduler(project_path=temp_project_dir)

        # Create test files with different ages
        performance_dir = temp_project_dir / "performance_data" / "history"
        performance_dir.mkdir(parents=True, exist_ok=True)

        # Create old file (should be cleaned)
        old_file = performance_dir / "old_file.json"
        old_file.write_text('{"old": "data"}')
        old_time = (mock_now - timedelta(days=100)).timestamp()
        import os

        os.utime(old_file, (old_time, old_time))

        # Create recent file (should be kept)
        recent_file = performance_dir / "recent_file.json"
        recent_file.write_text('{"recent": "data"}')
        recent_time = (mock_now - timedelta(days=10)).timestamp()
        os.utime(recent_file, (recent_time, recent_time))

        result = scheduler._cleanup_old_data()

        assert result["files_removed"] >= 1
        assert not old_file.exists()  # Should be removed
        assert recent_file.exists()  # Should be kept

    def test_update_security_databases(self, temp_project_dir):
        """Test security database update."""
        scheduler = MaintenanceScheduler(project_path=temp_project_dir)

        result = scheduler._update_security_databases()

        assert result["status"] == "success"
        assert "databases_updated" in result
        assert "update_time" in result

    def test_update_performance_baselines_no_data(self, temp_project_dir):
        """Test performance baseline update with no data."""
        scheduler = MaintenanceScheduler(project_path=temp_project_dir)

        with patch.object(
            scheduler.health_monitor.performance_collector, "get_recent_history"
        ) as mock_history:
            mock_history.return_value = []

            result = scheduler._update_performance_baselines()

            assert result["status"] == "no_data"

    def test_update_performance_baselines_with_data(self, temp_project_dir):
        """Test performance baseline update with data."""
        scheduler = MaintenanceScheduler(project_path=temp_project_dir)

        # Mock performance metrics
        mock_metrics = Mock()
        mock_metrics.timestamp = datetime.now()

        with (
            patch.object(
                scheduler.health_monitor.performance_collector, "get_recent_history"
            ) as mock_history,
            patch.object(
                scheduler.health_monitor.performance_collector, "store_baseline"
            ) as mock_store,
        ):
            mock_history.return_value = [mock_metrics]
            mock_store.return_value = Path("/test/baseline.json")

            result = scheduler._update_performance_baselines()

            assert result["status"] == "success"
            assert "baseline_file" in result

    def test_perform_maintenance_dry_run(self, temp_project_dir):
        """Test maintenance with dry run."""
        scheduler = MaintenanceScheduler(project_path=temp_project_dir)

        with (
            patch.object(scheduler.health_monitor, "collect_health_metrics") as mock_health,
            patch.object(scheduler.health_monitor, "run_diagnostics") as mock_diagnostics,
        ):
            mock_health.return_value = {"status": "healthy"}
            mock_diagnostics.return_value = {"overall_status": "healthy"}

            result = scheduler.perform_maintenance(dry_run=True)

            assert result["dry_run"] is True
            assert "operations" in result
            assert "summary" in result

            # Data cleanup should be skipped in dry run
            cleanup_ops = [op for op in result["operations"] if op["operation"] == "data_cleanup"]
            assert len(cleanup_ops) == 1
            assert cleanup_ops[0]["status"] == "skipped"

    def test_perform_maintenance_live(self, temp_project_dir):
        """Test live maintenance execution."""
        scheduler = MaintenanceScheduler(project_path=temp_project_dir)

        with (
            patch.object(scheduler.health_monitor, "collect_health_metrics") as mock_health,
            patch.object(scheduler, "_cleanup_old_data") as mock_cleanup,
            patch.object(scheduler.health_monitor, "run_diagnostics") as mock_diagnostics,
        ):
            mock_health.return_value = {"status": "healthy"}
            mock_cleanup.return_value = {"files_removed": 5}
            mock_diagnostics.return_value = {"overall_status": "healthy"}

            result = scheduler.perform_maintenance(dry_run=False)

            assert result["dry_run"] is False
            assert "operations" in result
            assert result["summary"]["total_operations"] > 0

            # All operations should be attempted
            cleanup_ops = [op for op in result["operations"] if op["operation"] == "data_cleanup"]
            assert len(cleanup_ops) == 1
            assert cleanup_ops[0]["status"] == "success"
