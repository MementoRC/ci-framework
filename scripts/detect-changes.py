#!/usr/bin/env python3
"""
Change Detection Script for CI Workflow Template
Minimal implementation for TDD green phase

This script analyzes git changes to determine which CI stages should run.
"""
import subprocess
import sys
import json
from pathlib import Path
from typing import Dict, List, Set


def run_git_command(cmd: List[str]) -> str:
    """Run git command and return output"""
    try:
        result = subprocess.run(
            ["git"] + cmd,
            capture_output=True,
            text=True,
            check=True
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError:
        return ""


def get_changed_files() -> List[str]:
    """Get list of changed files from git"""
    # For minimal implementation, use simple git diff
    changed_files = run_git_command(["diff", "--name-only", "HEAD~1..HEAD"])
    if not changed_files:
        # Fallback to staged files
        changed_files = run_git_command(["diff", "--name-only", "--cached"])
    
    return [f for f in changed_files.split("\n") if f.strip()]


def analyze_changes(changed_files: List[str] = None) -> Dict[str, any]:
    """
    Analyze file changes and determine which CI stages should run
    
    Returns:
        Dict with CI stage decisions and metadata
    """
    if changed_files is None:
        changed_files = get_changed_files()
    
    # Initialize results
    result = {
        "run_tests": False,
        "run_security": False,
        "run_performance": False,
        "changed_modules": [],
        "docs_only": False,
        "dependencies_changed": False
    }
    
    # Analyze each changed file
    python_files = []
    test_files = []
    doc_files = []
    config_files = []
    
    for file_path in changed_files:
        path = Path(file_path)
        
        # Python source files
        if path.suffix == ".py":
            python_files.append(file_path)
            if "test" in path.name or "tests" in path.parts:
                test_files.append(file_path)
        
        # Documentation files
        elif path.suffix in [".md", ".rst", ".txt"] or path.name in ["README", "CHANGELOG"]:
            doc_files.append(file_path)
        
        # Configuration files that affect dependencies
        elif path.name in ["pyproject.toml", "pixi.toml", "requirements.txt", "environment.yml"]:
            config_files.append(file_path)
    
    # Determine CI stage execution
    if python_files:
        result["run_tests"] = True
        result["run_performance"] = True
        # Extract modules from Python file paths
        modules = set()
        for py_file in python_files:
            parts = Path(py_file).parts
            if len(parts) > 1:
                modules.add(parts[1])  # Second level directory
        result["changed_modules"] = list(modules)
    
    if config_files:
        result["dependencies_changed"] = True
        result["run_security"] = True
        result["run_tests"] = True  # Dependencies might affect tests
        result["run_performance"] = True  # Dependencies might affect performance
    
    if doc_files and not python_files and not config_files:
        result["docs_only"] = True
    
    return result


def main():
    """Main entry point for change detection script"""
    try:
        changed_files = get_changed_files()
        analysis = analyze_changes(changed_files)
        
        # Output results in JSON format for GitHub Actions
        print(json.dumps(analysis, indent=2))
        
        # Set GitHub Actions outputs if running in CI
        if "GITHUB_OUTPUT" in os.environ:
            with open(os.environ["GITHUB_OUTPUT"], "a") as f:
                f.write(f"run-tests={str(analysis['run_tests']).lower()}\n")
                f.write(f"run-security={str(analysis['run_security']).lower()}\n")
                f.write(f"run-performance={str(analysis['run_performance']).lower()}\n")
                f.write(f"changed-modules={','.join(analysis['changed_modules'])}\n")
        
        return 0
        
    except Exception as e:
        print(f"Error in change detection: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    import os
    sys.exit(main())