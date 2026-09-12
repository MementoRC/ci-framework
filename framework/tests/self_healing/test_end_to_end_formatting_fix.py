"""End-to-end integration tests for formatting fix workflow."""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from framework.self_healing.formatting_workflow import FormattingFixWorkflow


@pytest.fixture
def temp_dir():
    """Create a temporary directory for testing."""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield Path(temp_dir)


def test_end_to_end_formatting_fix_ruff(temp_dir):
    """
    End-to-end test for ruff formatting fix workflow.

    This test creates a Python file with known formatting errors,
    runs the main workflow, and asserts that the file is fixed,
    syntax is valid, and a correctly formatted commit is created.
    """
    # Create a Python file with formatting issues
    test_file = temp_dir / "test_file.py"
    test_file.write_text(
        """# File with formatting issues
def hello(  ):
    x=1
    y =  2
    return x+y

def  another_function( a, b ):
    return a+b
"""
    )

    # Mock git operations since we can't use real git in this environment
    with patch("subprocess.run") as mock_run:
        # Mock git status to show the file as modified
        mock_run.side_effect = [
            MagicMock(stdout="M  test_file.py\n", returncode=0),  # git status
            MagicMock(returncode=0),  # git add
            MagicMock(
                stdout="M  test_file.py\n", returncode=0
            ),  # git status for stage_changes
            MagicMock(
                stdout="test_file.py\n", returncode=0
            ),  # git diff --cached --name-only
            MagicMock(
                stdout="[main abc123] fix(format): Auto-fix ruff formatting violations (1 file)\n",
                returncode=0,
            ),  # git commit
        ]

        # Initialize workflow
        workflow = FormattingFixWorkflow(
            working_directory=str(temp_dir), enable_logging=False
        )

        # Simulate ruff output that would trigger a fix
        ruff_output = "Found 5 errors (3 fixable with the `--fix` option)."

        # Mock the command executor to avoid actually running ruff
        with patch.object(
            workflow.command_executor, "execute_formatting_command"
        ) as mock_execute:
            mock_execute.return_value = MagicMock(
                command="ruff check --fix .",
                return_code=0,
                stdout="Fixed 3 errors in test_file.py",
                stderr="",
                execution_time=1.5,
                timed_out=False,
                working_directory=str(temp_dir),
            )

            # Process the workflow
            result = workflow.process_tool_output(
                tool_output=ruff_output,
                dry_run=False,
                verify_syntax=True,
                create_commit=True,
            )

    # Assertions
    assert result.success is True
    assert "Successfully fixed and committed" in result.message
    assert result.pattern_matched == "ruff_fixable_errors"
    assert result.tool_used == "ruff"
    assert result.command_executed == "ruff check --fix ."
    assert "test_file.py" in result.files_fixed[0]  # Should be in committed files
    assert result.commit_result is not None
    assert result.commit_result.success is True
    assert result.execution_time > 0


def test_end_to_end_formatting_fix_black(temp_dir):
    """
    End-to-end test for black formatting fix workflow.
    """
    # Create a Python file with formatting issues
    test_file = temp_dir / "poorly_formatted.py"
    test_file.write_text(
        """def hello():
    x=1+2
    y=3  +4
    return x,y
"""
    )

    # Mock git operations
    with patch("subprocess.run") as mock_run:
        mock_run.side_effect = [
            MagicMock(stdout="M  poorly_formatted.py\n", returncode=0),  # git status
            MagicMock(returncode=0),  # git add
            MagicMock(
                stdout="M  poorly_formatted.py\n", returncode=0
            ),  # git status for stage_changes
            MagicMock(
                stdout="poorly_formatted.py\n", returncode=0
            ),  # git diff --cached --name-only
            MagicMock(
                stdout="[main def456] fix(format): Auto-format code with black (1 file)\n",
                returncode=0,
            ),  # git commit
        ]

        workflow = FormattingFixWorkflow(
            working_directory=str(temp_dir), enable_logging=False
        )

        # Black output indicating files would be reformatted
        black_output = "would reformat 1 files"

        # Mock command execution
        with patch.object(
            workflow.command_executor, "execute_formatting_command"
        ) as mock_execute:
            mock_execute.return_value = MagicMock(
                command="black .",
                return_code=0,
                stdout="reformatted poorly_formatted.py",
                stderr="",
                execution_time=0.8,
                timed_out=False,
                working_directory=str(temp_dir),
            )

            result = workflow.process_tool_output(
                tool_output=black_output,
                dry_run=False,
                verify_syntax=True,
                create_commit=True,
            )

    # Assertions
    assert result.success is True
    assert result.pattern_matched == "black_would_reformat"
    assert result.tool_used == "black"
    assert result.commit_result.success is True


def test_end_to_end_formatting_fix_syntax_error_rollback(temp_dir):
    """
    End-to-end test for handling syntax errors and rollback.

    This test verifies that when automated fixes introduce syntax errors,
    all changes are rolled back properly.
    """
    # Create a Python file that will have syntax errors after "fixing"
    test_file = temp_dir / "syntax_error.py"
    test_file.write_text(
        """def hello():
    return "valid syntax"
"""
    )

    # Create an invalid file that the formatter would "fix" to be broken
    invalid_file = temp_dir / "broken.py"
    invalid_file.write_text("def broken(\n    return 'missing paren'")

    # Mock git operations
    with patch("subprocess.run") as mock_run:
        mock_run.side_effect = [
            # First call: get changed files for syntax verification
            MagicMock(stdout="M  broken.py\n", returncode=0),
            # Rollback operations
            MagicMock(returncode=0),  # git restore --staged .
            MagicMock(returncode=0),  # git restore .
        ]

        workflow = FormattingFixWorkflow(
            working_directory=str(temp_dir), enable_logging=False
        )

        # Simulate tool output that would match a pattern
        tool_output = "Found 2 errors (1 fixable with the `--fix` option)."

        # Mock command execution to "fix" the file
        with patch.object(
            workflow.command_executor, "execute_formatting_command"
        ) as mock_execute:
            mock_execute.return_value = MagicMock(
                command="ruff check --fix .",
                return_code=0,
                stdout="Fixed broken.py",
                stderr="",
                execution_time=1.0,
                timed_out=False,
                working_directory=str(temp_dir),
            )

            result = workflow.process_tool_output(
                tool_output=tool_output,
                dry_run=False,
                verify_syntax=True,
                create_commit=True,
            )

    # Assertions - should fail due to syntax error and rollback
    assert result.success is False
    assert "Syntax errors detected" in result.message
    assert "1 files" in result.message  # Should mention the file with syntax error


def test_end_to_end_dry_run_mode(temp_dir):
    """
    End-to-end test for dry-run mode.

    This test verifies that dry-run mode correctly identifies issues
    without making actual changes.
    """
    # Create a file with formatting issues
    test_file = temp_dir / "dry_run_test.py"
    test_file.write_text("def test():pass")

    workflow = FormattingFixWorkflow(
        working_directory=str(temp_dir), enable_logging=False
    )

    # Mock dry-run command execution
    with patch.object(workflow.command_executor, "dry_run_command") as mock_dry_run:
        mock_dry_run.return_value = MagicMock(
            command="black --check --diff .",
            return_code=1,  # Non-zero indicates changes would be made
            stdout="--- dry_run_test.py\n+++ dry_run_test.py\n@@ -1 +1,2 @@\n-def test():pass\n+def test():\n+    pass",
            stderr="",
            execution_time=0.5,
            timed_out=False,
            working_directory=str(temp_dir),
        )

        result = workflow.process_tool_output(
            tool_output="would reformat 1 files",
            dry_run=True,
            verify_syntax=False,
            create_commit=False,
        )

    # Assertions
    assert result.success is True
    assert "Dry run completed" in result.message
    assert result.pattern_matched == "black_would_reformat"
    assert result.tool_used == "black"
    assert result.files_fixed == []  # No files should be actually fixed in dry-run
    assert result.commit_result is None  # No commit in dry-run


def test_end_to_end_multiple_tools_workflow(temp_dir):
    """
    End-to-end test for processing multiple different tool outputs.
    """
    # Create files with different formatting issues
    ruff_file = temp_dir / "ruff_issues.py"
    ruff_file.write_text("import os,sys\nprint('hello')")

    black_file = temp_dir / "black_issues.py"
    black_file.write_text("def test():pass")

    workflow = FormattingFixWorkflow(
        working_directory=str(temp_dir), enable_logging=False
    )

    # Mock git operations for both fixes
    with patch("subprocess.run") as mock_run:
        mock_run.side_effect = [
            # First tool (ruff)
            MagicMock(stdout="M  ruff_issues.py\n", returncode=0),  # git status
            MagicMock(returncode=0),  # git add
            MagicMock(
                stdout="M  ruff_issues.py\n", returncode=0
            ),  # git status for stage_changes
            MagicMock(
                stdout="ruff_issues.py\n", returncode=0
            ),  # git diff --cached --name-only
            MagicMock(
                stdout="[main abc123] fix(format): Auto-fix ruff formatting violations (1 file)\n",
                returncode=0,
            ),  # git commit
            # Second tool (black)
            MagicMock(stdout="M  black_issues.py\n", returncode=0),  # git status
            MagicMock(returncode=0),  # git add
            MagicMock(
                stdout="M  black_issues.py\n", returncode=0
            ),  # git status for stage_changes
            MagicMock(
                stdout="black_issues.py\n", returncode=0
            ),  # git diff --cached --name-only
            MagicMock(
                stdout="[main def456] fix(format): Auto-format code with black (1 file)\n",
                returncode=0,
            ),  # git commit
        ]

        # Mock command executions for both tools
        with patch.object(
            workflow.command_executor, "execute_formatting_command"
        ) as mock_execute:
            mock_execute.side_effect = [
                # Ruff execution
                MagicMock(
                    command="ruff check --fix .",
                    return_code=0,
                    stdout="Fixed import sorting in ruff_issues.py",
                    stderr="",
                    execution_time=1.2,
                    timed_out=False,
                    working_directory=str(temp_dir),
                ),
                # Black execution
                MagicMock(
                    command="black .",
                    return_code=0,
                    stdout="reformatted black_issues.py",
                    stderr="",
                    execution_time=0.9,
                    timed_out=False,
                    working_directory=str(temp_dir),
                ),
            ]

            # Process multiple tool outputs
            outputs = [
                "Found 3 errors (2 fixable with the `--fix` option).",
                "would reformat 1 files",
            ]

            results = workflow.process_multiple_outputs(outputs)

    # Assertions
    assert len(results) == 2
    assert all(result.success for result in results)
    assert results[0].tool_used == "ruff"
    assert results[1].tool_used == "black"
    assert all(result.commit_result.success for result in results)


def test_end_to_end_no_fixable_issues():
    """
    End-to-end test for when no fixable issues are found.
    """
    with tempfile.TemporaryDirectory() as temp_dir:
        workflow = FormattingFixWorkflow(
            working_directory=temp_dir, enable_logging=False
        )

        # Tool output that doesn't match any patterns
        result = workflow.process_tool_output(
            tool_output="All checks passed! No issues found.",
            dry_run=False,
            verify_syntax=True,
            create_commit=True,
        )

        # Assertions
        assert result.success is False
        assert "No fixable formatting issues detected" in result.message
        assert result.pattern_matched is None
        assert result.tool_used is None
        assert result.commit_result is None
