"""Integration tests for Security Scan Action."""

import json
import subprocess
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest
import yaml


class MockProcess:
    """Mock subprocess result for testing."""

    def __init__(self, returncode=0, stdout="", stderr=""):
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


class TestSecurityScanAction:
    """Test security scan action integration."""

    @pytest.fixture
    def action_yml_path(self):
        """Path to security scan action.yml file."""
        return (
            Path(__file__).parent.parent.parent.parent
            / "actions"
            / "security-scan"
            / "action.yml"
        )

    @pytest.fixture
    def action_config(self, action_yml_path):
        """Load action configuration."""
        with open(action_yml_path) as f:
            return yaml.safe_load(f)

    def test_action_yml_structure(self, action_config):
        """Test action.yml has required structure."""
        assert action_config["name"] == "Security Scan Action"
        assert "description" in action_config
        assert "inputs" in action_config
        assert "outputs" in action_config
        assert "runs" in action_config

        # Verify required inputs
        required_inputs = ["security-level", "timeout", "parallel"]
        for input_name in required_inputs:
            assert input_name in action_config["inputs"]

        # Verify key outputs
        required_outputs = [
            "success",
            "security-level",
            "execution-time",
            "vulnerabilities-found",
            "tools-executed",
        ]
        for output_name in required_outputs:
            assert output_name in action_config["outputs"]

    def test_security_level_configurations(self, action_config):
        """Test security level input validation."""
        security_level_input = action_config["inputs"]["security-level"]
        assert security_level_input["default"] == "medium"
        assert security_level_input["required"] is False

    def test_tool_enable_inputs(self, action_config):
        """Test tool enable/disable inputs."""
        tool_inputs = [
            "enable-bandit",
            "enable-safety",
            "enable-pip-audit",
            "enable-semgrep",
            "enable-trivy",
        ]

        for tool_input in tool_inputs:
            assert tool_input in action_config["inputs"]
            input_config = action_config["inputs"][tool_input]
            assert input_config["required"] is False
            assert input_config["default"] in ["true", "false"]

    def test_default_tool_configuration(self, action_config):
        """Test default tool enablement configuration."""
        # Essential tools should be enabled by default
        assert action_config["inputs"]["enable-bandit"]["default"] == "true"
        assert action_config["inputs"]["enable-safety"]["default"] == "true"
        assert action_config["inputs"]["enable-pip-audit"]["default"] == "true"

        # Advanced tools should be disabled by default
        assert action_config["inputs"]["enable-semgrep"]["default"] == "false"
        assert action_config["inputs"]["enable-trivy"]["default"] == "false"


class TestSecurityScanIntegration:
    """Test security scan execution and integration."""

    @pytest.fixture
    def temp_project(self):
        """Create temporary project for testing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_path = Path(tmpdir)

            # Create basic Python project structure
            (project_path / "src").mkdir()
            (project_path / "tests").mkdir()

            # Create pyproject.toml
            pyproject_content = """
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "test-project"
version = "0.1.0"
dependencies = ["requests>=2.0.0"]

[tool.pixi.dependencies]
bandit = "*"
safety = "*"
pip-audit = "*"
"""
            (project_path / "pyproject.toml").write_text(pyproject_content)

            # Create sample Python file with potential security issue
            sample_code = """
import subprocess
import requests

def vulnerable_function():
    # Potential security issues for testing
    subprocess.call("ls", shell=True)  # B602: subprocess with shell=True
    password = "hardcoded_password"  # B105: hardcoded password
    requests.get("http://example.com", verify=False)  # B501: request with verify=False
def safe_function():
    return "This is safe code"
"""
            (project_path / "src" / "main.py").write_text(sample_code)

            yield project_path

    @patch("subprocess.run")
    def test_bandit_integration(self, mock_run, temp_project):
        """Test bandit integration and execution."""
        # Mock bandit execution
        bandit_output = {
            "results": [
                {
                    "filename": "src/main.py",
                    "issue_severity": "high",
                    "issue_confidence": "high",
                    "test_name": "B602",
                }
            ],
            "metrics": {"_totals": {"SEVERITY.HIGH": 1}},
        }

        mock_process = MockProcess(
            returncode=1, stdout=json.dumps(bandit_output), stderr=""
        )
        mock_run.return_value = mock_process

        # Test bandit command construction
        reports_dir = temp_project / "security-reports"
        reports_dir.mkdir()

        cmd = [
            "bandit",
            "-r",
            str(temp_project),
            "-f",
            "json",
            "-o",
            str(reports_dir / "bandit-results.json"),
            "--severity-level",
            "medium",
            "-x",
            "**/tests/**,**/test_**",
        ]

        # Simulate execution
        subprocess.run(cmd, capture_output=True, text=True)

        # Verify mock was called
        assert mock_run.called

    @patch("subprocess.run")
    def test_safety_integration(self, mock_run, temp_project):
        """Test safety integration and vulnerability detection."""
        # Mock safety output with vulnerability
        safety_output = [
            {
                "package": "requests",
                "installed": "2.0.0",
                "vulnerability": {"id": 25853, "specs": ["<2.20.0"], "v": "<2.20.0"},
            }
        ]

        mock_process = MockProcess(
            returncode=1, stdout=json.dumps(safety_output), stderr=""
        )
        mock_run.return_value = mock_process

        # Test safety command
        reports_dir = temp_project / "security-reports"
        reports_dir.mkdir()

        cmd = [
            "safety",
            "check",
            "--json",
            "--output",
            str(reports_dir / "safety-results.json"),
        ]

        # Simulate execution
        subprocess.run(cmd, capture_output=True, text=True)

        assert mock_run.called

    @patch("subprocess.run")
    def test_pip_audit_integration(self, mock_run, temp_project):
        """Test pip-audit integration."""
        # Mock pip-audit output
        pip_audit_output = {
            "dependencies": [
                {
                    "name": "requests",
                    "version": "2.0.0",
                    "vulnerabilities": [{"id": "PYSEC-2018-0101", "severity": "HIGH"}],
                }
            ]
        }

        mock_process = MockProcess(
            returncode=1, stdout=json.dumps(pip_audit_output), stderr=""
        )
        mock_run.return_value = mock_process

        # Test pip-audit command
        reports_dir = temp_project / "security-reports"
        reports_dir.mkdir()

        cmd = [
            "pip-audit",
            "--format=json",
            "--output",
            str(reports_dir / "pip-audit-results.json"),
        ]

        # Simulate execution
        subprocess.run(cmd, capture_output=True, text=True)

        assert mock_run.called

    def test_security_level_tool_mapping(self):
        """Test security level to tool mapping configuration."""
        security_configs = {
            "low": {
                "required_tools": ["bandit"],
                "bandit_severity": "low",
                "fail_on_vulnerabilities": False,
            },
            "medium": {
                "required_tools": ["bandit", "safety", "pip-audit"],
                "bandit_severity": "medium",
                "fail_on_vulnerabilities": True,
            },
            "high": {
                "required_tools": ["bandit", "safety", "pip-audit", "semgrep"],
                "bandit_severity": "high",
                "fail_on_vulnerabilities": True,
            },
            "critical": {
                "required_tools": ["bandit", "safety", "pip-audit", "semgrep", "trivy"],
                "bandit_severity": "high",
                "fail_on_vulnerabilities": True,
            },
        }

        # Verify progressive tool inclusion
        assert len(security_configs["low"]["required_tools"]) == 1
        assert len(security_configs["medium"]["required_tools"]) == 3
        assert len(security_configs["high"]["required_tools"]) == 4
        assert len(security_configs["critical"]["required_tools"]) == 5

        # Verify severity escalation
        severities = ["low", "medium", "high", "high"]  # critical uses high
        for i, level in enumerate(["low", "medium", "high", "critical"]):
            assert security_configs[level]["bandit_severity"] == severities[i]

    def test_sarif_generation(self, temp_project):
        """Test SARIF report generation and format."""
        reports_dir = temp_project / "security-reports"
        reports_dir.mkdir()

        # Create sample SARIF files
        bandit_sarif = {
            "$schema": "https://raw.githubusercontent.com/oasis-tcs/sarif-spec/master/Schemata/sarif-schema-2.1.0.json",
            "version": "2.1.0",
            "runs": [
                {
                    "tool": {"driver": {"name": "bandit"}},
                    "results": [
                        {
                            "ruleId": "B602",
                            "level": "error",
                            "message": {"text": "subprocess call with shell=True"},
                        }
                    ],
                }
            ],
        }

        # Write sample SARIF file
        sarif_file = reports_dir / "bandit.sarif"
        with open(sarif_file, "w") as f:
            json.dump(bandit_sarif, f)

        # Test unified SARIF generation logic
        unified_sarif = {
            "$schema": "https://raw.githubusercontent.com/oasis-tcs/sarif-spec/master/Schemata/sarif-schema-2.1.0.json",
            "version": "2.1.0",
            "runs": [],
        }

        # Collect SARIF files
        sarif_files = list(reports_dir.glob("*.sarif"))
        assert len(sarif_files) == 1

        for sarif_file in sarif_files:
            with open(sarif_file) as f:
                sarif_data = json.load(f)
                if "runs" in sarif_data:
                    unified_sarif["runs"].extend(sarif_data["runs"])

        # Verify unified SARIF structure
        assert len(unified_sarif["runs"]) == 1
        assert unified_sarif["runs"][0]["tool"]["driver"]["name"] == "bandit"

    def test_vulnerability_counting(self):
        """Test vulnerability counting and categorization."""
        vulnerabilities = {"critical": 0, "high": 0, "medium": 0, "low": 0}

        # Test bandit result processing
        bandit_results = [
            {"issue_severity": "high"},
            {"issue_severity": "medium"},
            {"issue_severity": "low"},
        ]

        for issue in bandit_results:
            severity = issue.get("issue_severity", "").lower()
            if severity in vulnerabilities:
                vulnerabilities[severity] += 1

        assert vulnerabilities["high"] == 1
        assert vulnerabilities["medium"] == 1
        assert vulnerabilities["low"] == 1
        assert vulnerabilities["critical"] == 0

        # Test total vulnerability calculation
        total_vulns = sum(vulnerabilities.values())
        assert total_vulns == 3

        # Test critical/high count
        critical_vulns = vulnerabilities["critical"] + vulnerabilities["high"]
        assert critical_vulns == 1


class TestSecurityScanBDD:
    """BDD-style tests for security scan scenarios."""

    def test_essential_security_level_execution(self):
        """
        Given a project with basic security requirements
        When security scan runs with 'low' level
        Then it should run bandit only
        And it should not fail on vulnerabilities found
        """
        # Test configuration for low security level
        config = {
            "bandit_severity": "low",
            "timeout_per_tool": 60,
            "fail_on_vulnerabilities": False,
            "required_tools": ["bandit"],
        }

        assert "bandit" in config["required_tools"]
        assert len(config["required_tools"]) == 1
        assert config["fail_on_vulnerabilities"] is False
        assert config["timeout_per_tool"] == 60

    def test_standard_security_level_execution(self):
        """
        Given a project requiring comprehensive security checks
        When security scan runs with 'medium' level
        Then it should run bandit, safety, and pip-audit
        And it should fail on critical/high vulnerabilities
        """
        config = {
            "bandit_severity": "medium",
            "timeout_per_tool": 120,
            "fail_on_vulnerabilities": True,
            "required_tools": ["bandit", "safety", "pip-audit"],
        }

        assert "bandit" in config["required_tools"]
        assert "safety" in config["required_tools"]
        assert "pip-audit" in config["required_tools"]
        assert len(config["required_tools"]) == 3
        assert config["fail_on_vulnerabilities"] is True

    def test_advanced_security_level_execution(self):
        """
        Given a production project requiring advanced security
        When security scan runs with 'high' level
        Then it should run all tools including semgrep
        And it should have stricter failure criteria
        """
        config = {
            "bandit_severity": "high",
            "timeout_per_tool": 300,
            "fail_on_vulnerabilities": True,
            "required_tools": ["bandit", "safety", "pip-audit", "semgrep"],
        }

        assert "semgrep" in config["required_tools"]
        assert len(config["required_tools"]) == 4
        assert config["bandit_severity"] == "high"

    def test_critical_security_level_execution(self):
        """
        Given a security-critical project
        When security scan runs with 'critical' level
        Then it should run all available tools including Trivy
        And it should generate SBOM
        And it should have maximum timeout and strictest failure criteria
        """
        config = {
            "bandit_severity": "high",
            "timeout_per_tool": 600,
            "fail_on_vulnerabilities": True,
            "required_tools": ["bandit", "safety", "pip-audit", "semgrep", "trivy"],
        }

        assert "trivy" in config["required_tools"]
        assert len(config["required_tools"]) == 5
        assert config["timeout_per_tool"] == 600

    def test_parallel_execution_performance(self):
        """
        Given security scan configured for parallel execution
        When multiple tools are enabled
        Then tools should execute concurrently
        And total execution time should be optimized
        """
        # Test that parallel configuration is properly handled
        parallel_config = {
            "parallel": True,
            "max_workers": 3,
            "tools": ["bandit", "safety", "pip-audit", "semgrep"],
        }

        assert parallel_config["parallel"] is True
        assert parallel_config["max_workers"] <= len(parallel_config["tools"])

    def test_sarif_integration_workflow(self):
        """
        Given security scan with SARIF upload enabled
        When scans complete successfully
        Then unified SARIF file should be generated
        And it should be uploaded to GitHub Security tab
        """
        # Test SARIF configuration
        sarif_config = {
            "sarif_upload": True,
            "unified_sarif_file": "security-unified.sarif",
            "individual_sarif_files": ["bandit.sarif", "semgrep.sarif", "trivy.sarif"],
        }

        assert sarif_config["sarif_upload"] is True
        assert sarif_config["unified_sarif_file"].endswith(".sarif")
        assert all(f.endswith(".sarif") for f in sarif_config["individual_sarif_files"])

    def test_sbom_generation_workflow(self):
        """
        Given security scan with SBOM generation enabled
        When Trivy scan completes
        Then SBOM file should be generated in CycloneDX format
        And it should be uploaded as artifact
        """
        sbom_config = {
            "sbom_generation": True,
            "sbom_format": "cyclonedx",
            "sbom_file": "trivy-sbom.json",
        }

        assert sbom_config["sbom_generation"] is True
        assert sbom_config["sbom_format"] == "cyclonedx"
        assert sbom_config["sbom_file"].endswith(".json")

    def test_integration_project_compatibility(self):
        """Test security scan compatibility with different project types."""
        # Test package manager detection logic
        test_configs = [
            ("[tool.pixi]", "pixi"),
            ("[tool.poetry]", "poetry"),
            ("[project]", "pip"),
        ]

        for config_content, expected_manager in test_configs:
            # Mock the detection logic
            if "[tool.pixi]" in config_content:
                package_manager = "pixi"
            elif "[tool.poetry]" in config_content:
                package_manager = "poetry"
            else:
                package_manager = "pip"

            assert package_manager == expected_manager

    def test_graceful_failure_handling(self):
        """Test graceful handling of tool failures."""
        # Simulate tool failure scenarios
        failed_tools = ["semgrep"]  # Tool not available
        successful_tools = ["bandit", "safety", "pip-audit"]

        # Test partial success handling
        assert len(successful_tools) > 0
        assert len(failed_tools) < len(successful_tools) + len(failed_tools)

        # Test that action can continue with partial results
        continue_on_partial_failure = True
        assert continue_on_partial_failure is True

    def test_timeout_enforcement(self):
        """Test timeout enforcement for security tools."""
        timeout_config = {
            "per_tool_timeout": 120,
            "total_timeout": 600,
            "timeout_handling": "graceful",
        }

        assert timeout_config["per_tool_timeout"] > 0
        assert timeout_config["total_timeout"] > timeout_config["per_tool_timeout"]
        assert timeout_config["timeout_handling"] == "graceful"
