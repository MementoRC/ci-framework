"""
Tests for package detection functionality.
"""

import json
import tempfile
import os
from pathlib import Path
import pytest
import sys

# Add scripts directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "scripts" / "local-ci"))

try:
    from package_detection import PackageDetector
except ImportError:
    pytest.skip("package-detection.py not available", allow_module_level=True)


class TestPackageDetector:
    """Test package detection functionality."""
    
    def test_init(self):
        """Test PackageDetector initialization."""
        detector = PackageDetector()
        assert detector.root_dir == Path.cwd()
        
        detector = PackageDetector("/tmp")
        assert detector.root_dir == Path("/tmp")
    
    def test_pixi_detection(self, tmp_path):
        """Test detection of pixi projects."""
        # Create a pyproject.toml with pixi configuration
        pyproject_content = """
[tool.pixi.project]
name = "test-project"
version = "0.1.0"

[tool.pixi.dependencies]
python = "3.11.*"
"""
        pyproject_file = tmp_path / "pyproject.toml"
        pyproject_file.write_text(pyproject_content)
        
        detector = PackageDetector(str(tmp_path))
        packages = detector.detect_packages({"pixi"})
        
        assert "pixi" in packages
        assert len(packages["pixi"]) == 1
        
        package = packages["pixi"][0]
        assert package["name"] == "test-project"
        assert package["type"] == "pixi"
        assert package["path"] == "."
        assert "test" in package["commands"]
        assert "lint" in package["commands"]
    
    def test_poetry_detection(self, tmp_path):
        """Test detection of poetry projects."""
        pyproject_content = """
[tool.poetry]
name = "test-poetry-project"
version = "0.1.0"

[tool.poetry.dependencies]
python = "^3.11"
"""
        pyproject_file = tmp_path / "pyproject.toml"
        pyproject_file.write_text(pyproject_content)
        
        detector = PackageDetector(str(tmp_path))
        packages = detector.detect_packages({"poetry"})
        
        assert "poetry" in packages
        assert len(packages["poetry"]) == 1
        
        package = packages["poetry"][0]
        assert package["name"] == "test-poetry-project"
        assert package["type"] == "poetry"
        assert "install" in package["commands"]
    
    def test_npm_detection(self, tmp_path):
        """Test detection of npm projects."""
        package_json_content = """
{
  "name": "test-npm-project",
  "version": "1.0.0",
  "scripts": {
    "test": "jest",
    "lint": "eslint ."
  }
}
"""
        package_file = tmp_path / "package.json"
        package_file.write_text(package_json_content)
        
        detector = PackageDetector(str(tmp_path))
        packages = detector.detect_packages({"npm"})
        
        assert "npm" in packages
        assert len(packages["npm"]) == 1
        
        package = packages["npm"][0]
        assert package["name"] == "test-npm-project"
        assert package["type"] == "npm"
        assert "test" in package["commands"]
        assert "lint" in package["commands"]
    
    def test_pip_detection(self, tmp_path):
        """Test detection of pip projects."""
        requirements_content = """
pytest>=7.0.0
ruff>=0.1.0
"""
        req_file = tmp_path / "requirements.txt"
        req_file.write_text(requirements_content)
        
        detector = PackageDetector(str(tmp_path))
        packages = detector.detect_packages({"pip"})
        
        assert "pip" in packages
        assert len(packages["pip"]) == 1
        
        package = packages["pip"][0]
        assert package["type"] == "pip"
        assert "install" in package["commands"]
    
    def test_test_detection(self, tmp_path):
        """Test detection of test directories."""
        # Create test directory
        test_dir = tmp_path / "tests"
        test_dir.mkdir()
        (test_dir / "test_example.py").write_text("# test file")
        
        # Create pyproject.toml
        pyproject_content = """
[tool.pixi.project]
name = "test-project"
"""
        (tmp_path / "pyproject.toml").write_text(pyproject_content)
        
        detector = PackageDetector(str(tmp_path))
        packages = detector.detect_packages({"pixi"})
        
        package = packages["pixi"][0]
        assert package["has_tests"] is True
    
    def test_no_tests_detection(self, tmp_path):
        """Test when no tests are detected."""
        pyproject_content = """
[tool.pixi.project]
name = "test-project"
"""
        (tmp_path / "pyproject.toml").write_text(pyproject_content)
        
        detector = PackageDetector(str(tmp_path))
        packages = detector.detect_packages({"pixi"})
        
        package = packages["pixi"][0]
        assert package["has_tests"] is False
    
    def test_nested_packages(self, tmp_path):
        """Test detection of nested packages."""
        # Create nested structure
        api_dir = tmp_path / "src" / "api"
        api_dir.mkdir(parents=True)
        web_dir = tmp_path / "src" / "web"
        web_dir.mkdir(parents=True)
        
        # Create package configs
        api_package = """
{
  "name": "api-service",
  "version": "1.0.0"
}
"""
        (api_dir / "package.json").write_text(api_package)
        
        web_pyproject = """
[tool.pixi.project]
name = "web-frontend"
"""
        (web_dir / "pyproject.toml").write_text(web_pyproject)
        
        detector = PackageDetector(str(tmp_path))
        packages = detector.detect_packages()
        
        # Should find both packages
        assert "npm" in packages
        assert "pixi" in packages
        assert len(packages["npm"]) == 1
        assert len(packages["pixi"]) == 1
        
        npm_package = packages["npm"][0]
        assert npm_package["name"] == "api-service"
        assert npm_package["path"] == "src/api"
        
        pixi_package = packages["pixi"][0]
        assert pixi_package["name"] == "web-frontend"
        assert pixi_package["path"] == "src/web"
    
    def test_no_packages_found(self, tmp_path):
        """Test when no packages are found."""
        detector = PackageDetector(str(tmp_path))
        packages = detector.detect_packages()
        
        # Should return empty dict or dict with empty lists
        assert isinstance(packages, dict)
        for pkg_type, pkg_list in packages.items():
            assert len(pkg_list) == 0
    
    def test_exclude_patterns(self, tmp_path):
        """Test that certain directories are excluded."""
        # Create excluded directories
        excluded_dirs = [
            "node_modules", "__pycache__", ".venv", "venv",
            "build", "dist", "htmlcov", ".pytest_cache"
        ]
        
        for excluded_dir in excluded_dirs:
            excluded_path = tmp_path / excluded_dir
            excluded_path.mkdir()
            # Add a package.json that should be ignored
            (excluded_path / "package.json").write_text('{"name": "excluded"}')
        
        # Add a valid package in root
        (tmp_path / "package.json").write_text('{"name": "valid-package"}')
        
        detector = PackageDetector(str(tmp_path))
        packages = detector.detect_packages({"npm"})
        
        # Should only find the root package
        assert "npm" in packages
        assert len(packages["npm"]) == 1
        assert packages["npm"][0]["name"] == "valid-package"


class TestPackageDetectionCLI:
    """Test package detection command-line interface."""
    
    def test_help_option(self, tmp_path):
        """Test --help option."""
        import subprocess
        script_path = Path(__file__).parent.parent.parent.parent / "scripts" / "local-ci" / "package-detection.py"
        
        result = subprocess.run(
            ["python3", str(script_path), "--help"],
            capture_output=True,
            text=True
        )
        
        assert result.returncode == 0
        assert "Package Detection Script" in result.stdout
        assert "--format" in result.stdout
        assert "--type" in result.stdout
    
    def test_json_output(self, tmp_path):
        """Test JSON output format."""
        import subprocess
        
        # Create a test package
        pyproject_content = """
[tool.pixi.project]
name = "cli-test-project"
"""
        (tmp_path / "pyproject.toml").write_text(pyproject_content)
        
        script_path = Path(__file__).parent.parent.parent.parent / "scripts" / "local-ci" / "package-detection.py"
        
        result = subprocess.run(
            ["python3", str(script_path), "--root-dir", str(tmp_path), "--format", "json"],
            capture_output=True,
            text=True
        )
        
        assert result.returncode == 0
        
        # Parse JSON output
        packages = json.loads(result.stdout)
        assert "pixi" in packages
        assert packages["pixi"][0]["name"] == "cli-test-project"
    
    def test_list_output(self, tmp_path):
        """Test list output format."""
        import subprocess
        
        # Create a test package
        pyproject_content = """
[tool.pixi.project]
name = "list-test-project"
"""
        (tmp_path / "pyproject.toml").write_text(pyproject_content)
        
        script_path = Path(__file__).parent.parent.parent.parent / "scripts" / "local-ci" / "package-detection.py"
        
        result = subprocess.run(
            ["python3", str(script_path), "--root-dir", str(tmp_path), "--format", "list"],
            capture_output=True,
            text=True
        )
        
        assert result.returncode == 0
        assert "pixi:.:list-test-project" in result.stdout
    
    def test_type_filter(self, tmp_path):
        """Test package type filtering."""
        import subprocess
        
        # Create multiple package types
        (tmp_path / "pyproject.toml").write_text("""
[tool.pixi.project]
name = "pixi-project"
""")
        
        (tmp_path / "package.json").write_text("""
{"name": "npm-project"}
""")
        
        script_path = Path(__file__).parent.parent.parent.parent / "scripts" / "local-ci" / "package-detection.py"
        
        # Test pixi only
        result = subprocess.run(
            ["python3", str(script_path), "--root-dir", str(tmp_path), "--type", "pixi"],
            capture_output=True,
            text=True
        )
        
        assert result.returncode == 0
        packages = json.loads(result.stdout)
        assert "pixi" in packages
        assert "npm" not in packages
    
    def test_no_packages_exit_code(self, tmp_path):
        """Test exit code when no packages found."""
        import subprocess
        
        script_path = Path(__file__).parent.parent.parent.parent / "scripts" / "local-ci" / "package-detection.py"
        
        result = subprocess.run(
            ["python3", str(script_path), "--root-dir", str(tmp_path)],
            capture_output=True,
            text=True
        )
        
        assert result.returncode == 1
        assert "No packages found" in result.stderr


if __name__ == "__main__":
    pytest.main([__file__, "-v"])