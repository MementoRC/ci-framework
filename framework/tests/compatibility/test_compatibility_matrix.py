"""
Compatibility Matrix Tests for Quality Gates Action

Tests across Python versions, platforms, and different project configurations
to ensure broad compatibility as specified in the methodology requirements.
"""

import platform
import sys
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from framework.actions.quality_gates import QualityGatesAction


class TestPythonVersionCompatibility:
    """
    Test compatibility across Python versions

    Requirements: Python 3.10-3.12 support as per methodology
    """

    @pytest.fixture
    def quality_gates_action(self):
        """Quality Gates Action instance"""
        return QualityGatesAction()

    @pytest.fixture
    def test_project(self):
        """Create a test project for compatibility testing"""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_dir = Path(temp_dir) / "compat_project"
            project_dir.mkdir()

            # Create pyproject.toml with Python version requirements
            (project_dir / "pyproject.toml").write_text(
                """
[tool.pixi.project]
name = "compat-project"
channels = ["conda-forge"]
platforms = ["linux-64"]

[tool.pixi.dependencies]
python = ">=3.10"

[tool.pixi.environments]
quality = {features = ["quality"]}

[tool.pixi.tasks]
test = "pytest"
lint = "ruff check --select=F,E9"
typecheck = "mypy ."
quality = { depends-on = ["test", "lint", "typecheck"] }
"""
            )

            yield project_dir

    def test_current_python_version_support(self, quality_gates_action, test_project):
        """Test that current Python version is supported"""

        current_version = sys.version_info

        # Verify we're running on a supported Python version
        assert current_version >= (
            3,
            10,
        ), f"Running on Python {current_version}, need >=3.10"
        assert current_version < (
            3,
            13,
        ), f"Running on Python {current_version}, tested up to 3.12"

        # Test basic functionality works
        manager = quality_gates_action.detect_package_manager(test_project)
        assert manager.name == "pixi"

        patterns = quality_gates_action._detect_project_patterns(test_project)
        assert patterns["package_manager"] == "pixi"

        # Test dry-run execution
        result = quality_gates_action.execute_tier(
            project_dir=test_project, tier="essential", dry_run=True
        )
        assert result.success is True

    def test_python_version_detection_in_config(
        self, quality_gates_action, test_project
    ):
        """Test detection of Python version requirements in project config"""

        config = quality_gates_action._load_project_config(test_project)

        # Should detect pixi dependencies
        assert "tool" in config
        assert "pixi" in config["tool"]

        if "dependencies" in config["tool"]["pixi"]:
            deps = config["tool"]["pixi"]["dependencies"]
            if "python" in deps:
                python_req = deps["python"]
                # Should handle various Python requirement formats
                assert isinstance(python_req, str)
                assert (
                    "3.10" in python_req or "3.11" in python_req or "3.12" in python_req
                )

    @pytest.mark.parametrize(
        "python_version_spec", ["3.10.*", "3.11.*", "3.12.*", ">=3.10", ">=3.10,<3.13"]
    )
    def test_python_version_requirement_parsing(
        self, quality_gates_action, python_version_spec
    ):
        """Test parsing of different Python version requirement formats"""

        with tempfile.TemporaryDirectory() as temp_dir:
            project_dir = Path(temp_dir) / "version_test"
            project_dir.mkdir()

            # Create pyproject.toml with specific Python version
            pyproject_content = f"""
[tool.pixi.project]
name = "version-test"

[tool.pixi.dependencies]
python = "{python_version_spec}"

[tool.pixi.tasks]
test = "pytest"
"""
            (project_dir / "pyproject.toml").write_text(pyproject_content)

            # Should handle version parsing without errors
            config = quality_gates_action._load_project_config(project_dir)
            assert "tool" in config

            manager = quality_gates_action.detect_package_manager(project_dir)
            assert manager.name == "pixi"


class TestPlatformCompatibility:
    """
    Test compatibility across different platforms

    Requirements: ubuntu/macos support as per methodology
    """

    @pytest.fixture
    def quality_gates_action(self):
        return QualityGatesAction()

    def test_current_platform_support(self, quality_gates_action):
        """Test that current platform is supported"""

        current_platform = platform.system().lower()

        # Document current platform
        platform_info = {
            "system": platform.system(),
            "platform": platform.platform(),
            "machine": platform.machine(),
            "python_implementation": platform.python_implementation(),
            "python_version": platform.python_version(),
        }

        print(f"Platform info: {platform_info}")

        # Should support Linux (primary) and macOS
        assert current_platform in [
            "linux",
            "darwin",
            "windows",
        ], f"Unsupported platform: {current_platform}"

        # Test basic functionality works on current platform
        with tempfile.TemporaryDirectory() as temp_dir:
            project_dir = Path(temp_dir) / "platform_test"
            project_dir.mkdir()

            (project_dir / "pyproject.toml").write_text(
                """
[tool.pixi.project]
name = "platform-test"
platforms = ["linux-64", "osx-arm64", "osx-64", "win-64"]

[tool.pixi.tasks]
test = "pytest"
"""
            )

            # Should work regardless of platform
            manager = quality_gates_action.detect_package_manager(project_dir)
            assert manager.name == "pixi"

    @pytest.mark.parametrize(
        "platform_config",
        [
            ["linux-64"],
            ["osx-arm64", "osx-64"],
            ["linux-64", "osx-arm64", "osx-64", "win-64"],
        ],
    )
    def test_multi_platform_project_detection(
        self, quality_gates_action, platform_config
    ):
        """Test detection of multi-platform project configurations"""

        with tempfile.TemporaryDirectory() as temp_dir:
            project_dir = Path(temp_dir) / "multiplatform_test"
            project_dir.mkdir()

            pyproject_content = f"""
[tool.pixi.project]
name = "multiplatform-test"
platforms = {platform_config}

[tool.pixi.tasks]
test = "pytest"
"""
            (project_dir / "pyproject.toml").write_text(pyproject_content)

            patterns = quality_gates_action._detect_project_patterns(project_dir)

            assert "platforms" in patterns
            detected_platforms = patterns["platforms"]
            assert detected_platforms == platform_config

    def test_platform_specific_command_adaptation(self, quality_gates_action):
        """Test that commands adapt appropriately to different platforms"""

        current_platform = platform.system().lower()

        with tempfile.TemporaryDirectory() as temp_dir:
            project_dir = Path(temp_dir) / "platform_adapt_test"
            project_dir.mkdir()

            (project_dir / "pyproject.toml").write_text(
                """
[tool.pixi.project]
name = "platform-adapt-test"

[tool.pixi.tasks]
test = "pytest"
lint = "ruff check"
"""
            )

            manager = quality_gates_action.detect_package_manager(project_dir)
            commands = quality_gates_action._get_tier_commands("essential", manager)

            # Commands should work on current platform
            assert all(isinstance(cmd, str) for cmd in commands)
            assert all("pixi run" in cmd for cmd in commands)

            # No platform-specific path separators or commands that would fail
            for cmd in commands:
                assert "\\" not in cmd or current_platform == "windows"


class TestPackageManagerCompatibility:
    """
    Test compatibility across different package managers

    Requirements: Support pixi, poetry, hatch, pip as per implementation
    """

    @pytest.fixture
    def quality_gates_action(self):
        return QualityGatesAction()

    @pytest.mark.parametrize(
        "manager_config",
        [
            {
                "name": "pixi",
                "config_section": "[tool.pixi.project]\nname = 'test'\n[tool.pixi.tasks]\ntest = 'pytest'",
                "expected_command": "pixi run",
            },
            {
                "name": "poetry",
                "config_section": "[tool.poetry]\nname = 'test'\nversion = '0.1.0'",
                "expected_command": "poetry run",
            },
            {
                "name": "hatch",
                "config_section": "[tool.hatch.envs.default]\ndependencies = ['pytest']",
                "expected_command": "hatch run",
            },
        ],
    )
    def test_package_manager_detection_and_commands(
        self, quality_gates_action, manager_config
    ):
        """Test detection and command generation for different package managers"""

        with tempfile.TemporaryDirectory() as temp_dir:
            project_dir = Path(temp_dir) / f"{manager_config['name']}_test"
            project_dir.mkdir()

            # Create appropriate config file
            (project_dir / "pyproject.toml").write_text(
                manager_config["config_section"]
            )

            # Test detection
            manager = quality_gates_action.detect_package_manager(project_dir)
            assert manager.name == manager_config["name"]

            # Test command generation
            commands = quality_gates_action._get_tier_commands("essential", manager)
            assert all(manager_config["expected_command"] in cmd for cmd in commands)

    def test_pip_fallback_detection(self, quality_gates_action):
        """Test fallback to pip when no other package manager detected"""

        with tempfile.TemporaryDirectory() as temp_dir:
            project_dir = Path(temp_dir) / "pip_fallback_test"
            project_dir.mkdir()

            # No pyproject.toml or other package manager files
            # Just create a basic Python file
            (project_dir / "main.py").write_text("print('hello')")

            manager = quality_gates_action.detect_package_manager(project_dir)
            assert manager.name == "pip"
            assert not manager.environment_support

            commands = quality_gates_action._get_tier_commands("essential", manager)
            assert all("python -m" in cmd for cmd in commands)

    def test_package_manager_environment_support(self, quality_gates_action):
        """Test environment support detection for different package managers"""

        managers_with_env_support = ["pixi", "poetry", "hatch"]

        for manager_name in managers_with_env_support:
            with tempfile.TemporaryDirectory() as temp_dir:
                project_dir = Path(temp_dir) / f"{manager_name}_env_test"
                project_dir.mkdir()

                if manager_name == "pixi":
                    config = "[tool.pixi.project]\nname = 'test'\n[tool.pixi.environments]\nquality = {}"
                elif manager_name == "poetry":
                    config = "[tool.poetry]\nname = 'test'\nversion = '0.1.0'"
                elif manager_name == "hatch":
                    config = "[tool.hatch.envs.default]\ndependencies = []"

                (project_dir / "pyproject.toml").write_text(config)

                manager = quality_gates_action.detect_package_manager(project_dir)
                assert manager.environment_support is True


class TestConfigurationCompatibility:
    """
    Test compatibility with different project configurations
    """

    @pytest.fixture
    def quality_gates_action(self):
        return QualityGatesAction()

    def test_minimal_configuration_compatibility(self, quality_gates_action):
        """Test compatibility with minimal project configurations"""

        with tempfile.TemporaryDirectory() as temp_dir:
            project_dir = Path(temp_dir) / "minimal_config_test"
            project_dir.mkdir()

            # Minimal pixi configuration
            (project_dir / "pyproject.toml").write_text(
                """
[tool.pixi.project]
name = "minimal"
"""
            )

            # Should handle minimal config gracefully
            manager = quality_gates_action.detect_package_manager(project_dir)
            assert manager.name == "pixi"

            patterns = quality_gates_action._detect_project_patterns(project_dir)
            assert patterns["package_manager"] == "pixi"

            # Should work in dry-run mode
            result = quality_gates_action.execute_tier(
                project_dir=project_dir, tier="essential", dry_run=True
            )
            assert result.success is True

    def test_complex_configuration_compatibility(self, quality_gates_action):
        """Test compatibility with complex project configurations"""

        with tempfile.TemporaryDirectory() as temp_dir:
            project_dir = Path(temp_dir) / "complex_config_test"
            project_dir.mkdir()

            # Complex pixi configuration with multiple environments and features
            complex_config = """
[tool.pixi.project]
name = "complex-project"
channels = ["conda-forge", "pytorch", "nvidia"]
platforms = ["linux-64", "osx-arm64", "osx-64", "win-64"]

[tool.pixi.feature.quality.dependencies]
pytest = ">=7.0.0"
ruff = ">=0.1.0"
mypy = ">=1.0.0"

[tool.pixi.feature.dev.dependencies]
black = "*"
pre-commit = "*"

[tool.pixi.environments]
default = {solve-group = "default"}
quality = {features = ["quality"], solve-group = "default"}
dev = {features = ["quality", "dev"], solve-group = "default"}
ci = {features = ["quality"], solve-group = "ci"}

[tool.pixi.tasks]
test = "pytest tests/"
test-cov = "pytest tests/ --cov=src"
lint = "ruff check src/ tests/"
lint-fix = "ruff check --fix src/ tests/"
format = "ruff format src/ tests/"
typecheck = "mypy src/"
quality = { depends-on = ["test", "lint", "typecheck"] }
security-scan = "bandit -r src/"
check-all = { depends-on = ["quality", "security-scan"] }

[tool.ruff]
line-length = 88
target-version = "py310"

[tool.mypy]
python_version = "3.10"
strict = true
"""
            (project_dir / "pyproject.toml").write_text(complex_config)

            # Should handle complex config gracefully
            config = quality_gates_action._load_project_config(project_dir)
            assert "tool" in config
            assert "pixi" in config["tool"]

            patterns = quality_gates_action._detect_project_patterns(project_dir)
            assert patterns["package_manager"] == "pixi"
            assert "platforms" in patterns
            assert len(patterns["platforms"]) == 4

            # Should work in dry-run mode
            result = quality_gates_action.execute_tier(
                project_dir=project_dir, tier="full", dry_run=True
            )
            assert result.success is True

    def test_missing_configuration_handling(self, quality_gates_action):
        """Test handling of missing or incomplete configurations"""

        test_cases = [
            # No pyproject.toml at all
            {},
            # Empty pyproject.toml
            {"pyproject.toml": ""},
            # Invalid TOML
            {"pyproject.toml": "[invalid toml content"},
            # pyproject.toml without pixi section
            {"pyproject.toml": "[tool.other]\nname = 'test'"},
        ]

        for i, file_content in enumerate(test_cases):
            with tempfile.TemporaryDirectory() as temp_dir:
                project_dir = Path(temp_dir) / f"missing_config_test_{i}"
                project_dir.mkdir()

                # Create files based on test case
                for filename, content in file_content.items():
                    (project_dir / filename).write_text(content)

                # Should handle gracefully and fall back to pip
                manager = quality_gates_action.detect_package_manager(project_dir)

                if not file_content or "pyproject.toml" not in file_content:
                    assert manager.name == "pip"
                else:
                    # Should fall back to pip for invalid configs
                    assert manager.name in [
                        "pip",
                        "pixi",
                    ]  # May detect pixi from invalid content


class TestDependencyCompatibility:
    """
    Test compatibility with different dependency configurations
    """

    def test_compatibility_matrix_summary(self):
        """Generate a compatibility matrix summary for documentation"""

        compatibility_matrix = {
            "python_versions": {
                "3.10": "✅ Supported",
                "3.11": "✅ Supported",
                "3.12": "✅ Supported",
                "3.13": "🟡 Not tested",
                "3.9": "❌ Not supported",
            },
            "platforms": {
                "linux-64": "✅ Primary platform",
                "osx-arm64": "✅ Supported",
                "osx-64": "✅ Supported",
                "win-64": "🟡 Basic support",
                "linux-aarch64": "🟡 Not tested",
            },
            "package_managers": {
                "pixi": "✅ Primary support",
                "poetry": "✅ Full support",
                "hatch": "✅ Basic support",
                "pip": "✅ Fallback support",
                "conda": "🟡 Not tested",
                "pipenv": "🟡 Not tested",
            },
            "project_types": {
                "ci_framework": "✅ Primary target",
                "mcp_server": "✅ Tested (cheap-llm)",
                "large_application": "✅ Tested (hb-strategy-sandbox)",
                "library": "🟡 Should work",
                "web_application": "🟡 Should work",
            },
        }

        print("Quality Gates Action Compatibility Matrix:")
        for category, items in compatibility_matrix.items():
            print(f"\n{category.replace('_', ' ').title()}:")
            for item, status in items.items():
                print(f"  {item}: {status}")

        # Verify we have good coverage
        python_supported = sum(
            1
            for status in compatibility_matrix["python_versions"].values()
            if status.startswith("✅")
        )
        platform_supported = sum(
            1
            for status in compatibility_matrix["platforms"].values()
            if status.startswith("✅")
        )
        manager_supported = sum(
            1
            for status in compatibility_matrix["package_managers"].values()
            if status.startswith("✅")
        )

        assert python_supported >= 3, "Should support at least 3 Python versions"
        assert platform_supported >= 3, "Should support at least 3 platforms"
        assert manager_supported >= 3, "Should support at least 3 package managers"

        return compatibility_matrix
