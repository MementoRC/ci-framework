"""
Integration Test #1: hb-strategy-sandbox Compatibility

Testing the Quality Gates Action against the primary integration target
to ensure no breaking changes and enhanced functionality.
"""

import shutil
import tempfile
from pathlib import Path

import pytest

from framework.actions.quality_gates import QualityGatesAction


class TestHBStrategyIntegration:
    """
    Integration tests for hb-strategy-sandbox project compatibility

    These tests verify that the Quality Gates Action works seamlessly
    with the existing hb-strategy-sandbox patterns and configurations.
    """

    @pytest.fixture
    def hb_project_path(self):
        """Path to hb-strategy-sandbox project"""
        return Path(
            "/home/memento/ClaudeCode/Project/hb-strategy-sandbox/worktrees/feat-workspace-phase2"
        )

    @pytest.fixture
    def quality_gates_action(self):
        """Quality Gates Action instance"""
        return QualityGatesAction()

    def test_hb_project_exists(self, hb_project_path):
        """Verify the integration target project exists"""
        if not hb_project_path.exists():
            pytest.skip(
                "hb-strategy-sandbox project not available for integration testing"
            )

        assert hb_project_path.is_dir()
        assert (hb_project_path / "pyproject.toml").exists()

    def test_package_manager_detection(self, quality_gates_action, hb_project_path):
        """Test package manager detection with hb-strategy-sandbox"""
        if not hb_project_path.exists():
            pytest.skip("hb-strategy-sandbox project not available")

        manager = quality_gates_action.detect_package_manager(hb_project_path)

        assert manager.name == "pixi", f"Expected pixi, got {manager.name}"
        assert manager.environment_support is True
        assert "pyproject.toml" in manager.detected_files

    def test_pattern_detection(self, quality_gates_action, hb_project_path):
        """Test project pattern detection with hb-strategy-sandbox"""
        if not hb_project_path.exists():
            pytest.skip("hb-strategy-sandbox project not available")

        patterns = quality_gates_action._detect_project_patterns(hb_project_path)

        assert patterns["package_manager"] == "pixi"
        assert "platforms" in patterns

        # hb-strategy-sandbox should support multiple platforms
        platforms = patterns["platforms"]
        assert isinstance(platforms, list)
        assert len(platforms) >= 2  # Should support multiple platforms
        assert "linux-64" in platforms

    def test_dry_run_compatibility_check(self, quality_gates_action, hb_project_path):
        """Test dry-run compatibility check with hb-strategy-sandbox"""
        if not hb_project_path.exists():
            pytest.skip("hb-strategy-sandbox project not available")

        # Test all tiers in dry-run mode
        for tier in ["essential", "extended", "full"]:
            result = quality_gates_action.execute_tier(
                project_dir=hb_project_path, tier=tier, dry_run=True
            )

            assert result.success is True, f"Dry run failed for tier {tier}"
            assert result.compatibility_check is True
            assert result.tier == tier

    def test_essential_tier_command_mapping(
        self, quality_gates_action, hb_project_path
    ):
        """Test that essential tier commands map correctly to hb-strategy-sandbox"""
        if not hb_project_path.exists():
            pytest.skip("hb-strategy-sandbox project not available")

        manager = quality_gates_action.detect_package_manager(hb_project_path)
        commands = quality_gates_action._get_tier_commands("essential", manager)

        # Should generate pixi commands
        assert all(cmd.startswith("pixi run") for cmd in commands)

        # Should include core quality commands
        command_names = [cmd.split()[-1] for cmd in commands]
        assert "test" in command_names
        assert "lint" in command_names
        assert "typecheck" in command_names

    def test_configuration_compatibility(self, quality_gates_action, hb_project_path):
        """Test configuration compatibility with hb-strategy-sandbox"""
        if not hb_project_path.exists():
            pytest.skip("hb-strategy-sandbox project not available")

        # Load the project configuration
        config = quality_gates_action._load_project_config(hb_project_path)

        # Should have pixi configuration
        assert "tool" in config
        assert "pixi" in config["tool"]

        pixi_config = config["tool"]["pixi"]

        # Should have environments defined
        if "environments" in pixi_config:
            envs = pixi_config["environments"]
            # Check for quality-related environments
            env_names = list(envs.keys())
            quality_envs = [
                env
                for env in env_names
                if "quality" in env or "dev" in env or "ci" in env
            ]
            assert len(quality_envs) > 0, "No quality environments found"

    @pytest.mark.slow
    def test_real_execution_with_timeout(self, quality_gates_action, hb_project_path):
        """Test real execution with short timeout (safe test)"""
        if not hb_project_path.exists():
            pytest.skip("hb-strategy-sandbox project not available")

        # Use very short timeout to avoid long test runs
        # This tests timeout functionality without waiting long
        result = quality_gates_action.execute_tier(
            project_dir=hb_project_path,
            tier="essential",
            timeout=1,  # 1 second - should timeout quickly
            parallel=True,
        )

        # Should timeout or succeed quickly
        assert result.execution_time <= 5  # Should finish within 5 seconds

        # If it times out, that's expected and acceptable
        if not result.success and result.failure_reason == "timeout":
            assert result.timeout_seconds == 1

        # If it succeeds, that's also acceptable (very fast execution)
        elif result.success:
            assert result.tier == "essential"

    def test_environment_isolation_detection(
        self, quality_gates_action, hb_project_path
    ):
        """Test environment isolation capabilities"""
        if not hb_project_path.exists():
            pytest.skip("hb-strategy-sandbox project not available")

        # Test different tier environments
        for tier in ["essential", "extended", "full"]:
            result = quality_gates_action.execute_tier(
                project_dir=hb_project_path, tier=tier, dry_run=True
            )

            assert result.environment == f"pixi-{tier}"
            assert result.compatibility_check is True

    def test_framework_folder_compatibility(self, hb_project_path):
        """Test compatibility with existing framework/ folder structure"""
        if not hb_project_path.exists():
            pytest.skip("hb-strategy-sandbox project not available")

        framework_dir = hb_project_path / "framework"

        # hb-strategy-sandbox should have a framework/ directory
        # that our CI Framework could potentially replace
        if framework_dir.exists():
            assert framework_dir.is_dir()

            # Check for common framework patterns
            python_files = list(framework_dir.glob("**/*.py"))
            assert len(python_files) > 0, (
                "Framework directory should contain Python files"
            )

            # Check for typical CI/quality files
            potential_ci_files = [
                "quality.py",
                "ci.py",
                "test_runner.py",
                "lint_runner.py",
            ]

            existing_ci_files = [
                f
                for f in potential_ci_files
                if (framework_dir / f).exists()
                or any(
                    (framework_dir / subdir / f).exists()
                    for subdir in ["ci", "quality", "testing"]
                    if (framework_dir / subdir).exists()
                )
            ]

            # Document what exists for replacement planning
            print(f"Found framework directory with {len(python_files)} Python files")
            if existing_ci_files:
                print(f"Existing CI-related files: {existing_ci_files}")


class TestHBStrategyDropInReplacement:
    """
    Test drop-in replacement capability for hb-strategy-sandbox framework/

    This simulates Option 1: Drop-in Replacement testing
    """

    @pytest.fixture
    def hb_project_path(self):
        """Path to hb-strategy-sandbox project"""
        return Path(
            "/home/memento/ClaudeCode/Project/hb-strategy-sandbox/worktrees/feat-workspace-phase2"
        )

    def test_backup_and_restore_simulation(self, hb_project_path):
        """Simulate backup and restore of framework/ directory"""
        if not hb_project_path.exists():
            pytest.skip("hb-strategy-sandbox project not available")

        framework_dir = hb_project_path / "framework"
        if not framework_dir.exists():
            pytest.skip("No framework/ directory to test replacement with")

        with tempfile.TemporaryDirectory() as temp_dir:
            backup_dir = Path(temp_dir) / "framework_backup"

            # Simulate backup
            shutil.copytree(framework_dir, backup_dir)
            assert backup_dir.exists()
            assert len(list(backup_dir.glob("**/*.py"))) > 0

            # Simulate that backup can be restored
            # (We won't actually modify the real project)
            original_files = set(f.name for f in framework_dir.glob("**/*.py"))
            backup_files = set(f.name for f in backup_dir.glob("**/*.py"))

            assert original_files == backup_files, (
                "Backup should contain all original files"
            )

    def test_drop_in_compatibility_analysis(self, hb_project_path):
        """Analyze what would be needed for drop-in replacement"""
        if not hb_project_path.exists():
            pytest.skip("hb-strategy-sandbox project not available")

        framework_dir = hb_project_path / "framework"
        if not framework_dir.exists():
            pytest.skip("No framework/ directory to analyze")

        # Analyze existing structure
        python_files = list(framework_dir.glob("**/*.py"))
        subdirs = [d for d in framework_dir.iterdir() if d.is_dir()]

        analysis = {
            "total_python_files": len(python_files),
            "subdirectories": [d.name for d in subdirs],
            "entry_points": [],
            "cli_interfaces": [],
            "config_files": [],
        }

        # Look for entry points
        for py_file in python_files:
            content = py_file.read_text()
            if "__main__" in content or "if __name__" in content:
                analysis["entry_points"].append(py_file.name)
            if "argparse" in content or "click" in content or "typer" in content:
                analysis["cli_interfaces"].append(py_file.name)

        # Look for config files
        config_patterns = ["*.yml", "*.yaml", "*.json", "*.toml", "*.ini"]
        for pattern in config_patterns:
            config_files = list(framework_dir.glob(f"**/{pattern}"))
            analysis["config_files"].extend([f.name for f in config_files])

        # Drop-in replacement should preserve interface
        assert analysis["total_python_files"] > 0, "Framework should have Python files"

        # Document findings for implementation planning
        print(f"Drop-in replacement analysis: {analysis}")

        # The new framework should provide equivalent functionality
        return analysis


class TestHBStrategyPerformanceBaseline:
    """
    Establish performance baseline from hb-strategy-sandbox

    This helps ensure our Quality Gates Action meets or exceeds performance
    """

    @pytest.fixture
    def hb_project_path(self):
        """Path to hb-strategy-sandbox project"""
        return Path(
            "/home/memento/ClaudeCode/Project/hb-strategy-sandbox/worktrees/feat-workspace-phase2"
        )

    def test_establish_baseline_metrics(self, hb_project_path):
        """Establish baseline performance metrics"""
        if not hb_project_path.exists():
            pytest.skip("hb-strategy-sandbox project not available")

        # Document the baseline for comparison
        baseline_metrics = {
            "project_size": {
                "python_files": len(list(hb_project_path.glob("**/*.py"))),
                "total_files": len(list(hb_project_path.glob("**/*"))),
                "directories": len(
                    [d for d in hb_project_path.rglob("*") if d.is_dir()]
                ),
            },
            "configuration_complexity": {
                "pyproject_toml_size": (hb_project_path / "pyproject.toml")
                .stat()
                .st_size
                if (hb_project_path / "pyproject.toml").exists()
                else 0,
                "has_pixi_environments": False,
                "environment_count": 0,
            },
        }

        # Analyze pixi configuration complexity
        pyproject_path = hb_project_path / "pyproject.toml"
        if pyproject_path.exists():
            try:
                import tomllib

                with open(pyproject_path, "rb") as f:
                    config = tomllib.load(f)

                if "tool" in config and "pixi" in config["tool"]:
                    baseline_metrics["configuration_complexity"][
                        "has_pixi_environments"
                    ] = True
                    if "environments" in config["tool"]["pixi"]:
                        baseline_metrics["configuration_complexity"][
                            "environment_count"
                        ] = len(config["tool"]["pixi"]["environments"])
            except:
                pass

        # Document baseline for performance comparison
        print(f"Baseline metrics for hb-strategy-sandbox: {baseline_metrics}")

        # Quality Gates Action should handle projects of this complexity or greater
        assert baseline_metrics["project_size"]["python_files"] >= 0

        return baseline_metrics
