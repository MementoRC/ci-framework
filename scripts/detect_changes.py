#!/usr/bin/env python3
"""
Change Detection Script for CI Framework
Analyzes git diff to determine which CI stages should run
"""

import subprocess
import sys
from pathlib import Path
from typing import Dict, List


def analyze_changes() -> Dict[str, any]:
    """
    Analyze git changes and determine what CI stages should run
    
    Returns:
        Dict with CI stage flags and metadata
    """
    try:
        # Get changed files from git diff
        result = subprocess.run(
            ["git", "diff", "--name-only", "HEAD~1", "HEAD"],
            capture_output=True,
            text=True,
            check=True
        )
        changed_files = result.stdout.strip().split('\n') if result.stdout.strip() else []
        
    except subprocess.CalledProcessError:
        # Fallback to checking uncommitted changes
        try:
            result = subprocess.run(
                ["git", "diff", "--name-only"],
                capture_output=True,
                text=True,
                check=True
            )
            changed_files = result.stdout.strip().split('\n') if result.stdout.strip() else []
        except subprocess.CalledProcessError:
            # Default to running all tests if git fails
            return {
                "run_tests": True,
                "run_security": True,
                "run_performance": True,
                "changed_modules": ["all"],
                "force_full_pipeline": True
            }
    
    # Analyze the changes
    python_files = [f for f in changed_files if f.endswith('.py')]
    dependency_files = [f for f in changed_files if f in ['pyproject.toml', 'pixi.toml', 'requirements.txt', 'poetry.lock']]
    doc_files = [f for f in changed_files if f.endswith(('.md', '.rst', '.txt')) or f.startswith('docs/')]
    
    # Determine changed modules
    changed_modules = []
    for py_file in python_files:
        parts = Path(py_file).parts
        if len(parts) > 1:
            module = parts[1] if parts[0] == 'framework' else parts[0]
            if module not in changed_modules:
                changed_modules.append(module)
    
    # Build result
    result = {
        "run_tests": len(python_files) > 0,
        "run_security": len(dependency_files) > 0 or len(python_files) > 0,
        "run_performance": len(python_files) > 0,
        "changed_modules": changed_modules if changed_modules else ["none"],
        "force_full_pipeline": len(dependency_files) > 0,
        "docs_only": len(doc_files) > 0 and len(python_files) == 0 and len(dependency_files) == 0
    }
    
    return result


if __name__ == "__main__":
    """Command line interface for change detection"""
    changes = analyze_changes()
    
    # Output GitHub Actions format
    for key, value in changes.items():
        if isinstance(value, bool):
            print(f"{key}={str(value).lower()}")
        elif isinstance(value, list):
            print(f"{key}={','.join(value)}")
        else:
            print(f"{key}={value}")